"""Character creation, lists, profiles, and artwork galleries."""

from typing import Any

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError, MissingArtworkFileError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkView,
    CharacterInput,
    CharacterView,
    UniverseView,
)
from world_builder.domain.services.characters import CharacterService
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast

SELECTED_CHARACTER_KEY = "selected_character_id"


def _render_preview_styles() -> None:
    st.html(
        """
        <style>
        .st-key-character-profile-image
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] {
            width: 320px !important;
            height: 320px !important;
            max-width: 100%;
            overflow: hidden !important;
            border-radius: 0.5rem;
        }
        [class*="st-key-character-gallery-image-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] {
            width: 240px !important;
            height: 240px !important;
            max-width: 100%;
            overflow: hidden !important;
            border-radius: 0.5rem;
        }
        .st-key-character-profile-image
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] img,
        [class*="st-key-character-gallery-image-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] img {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
        }
        </style>
        """
    )


def _character_values(name: str, summary: str, universe_id: str | None) -> CharacterInput | None:
    if not name.strip():
        show_toast("Character name is required.", kind="error")
        return None
    if not summary.strip():
        show_toast("Character summary is required.", kind="error")
        return None
    try:
        return CharacterInput(name=name, summary=summary, universe_id=universe_id)
    except ValidationError:
        show_toast("Character name must be 200 characters or fewer.", kind="error")
        return None


def _artwork_values(title: str, description: str, uploaded: Any) -> ArtworkDetailsInput | None:
    if not title.strip():
        show_toast("Artwork title is required.", kind="error")
        return None
    if not description.strip():
        show_toast("Artwork description is required.", kind="error")
        return None
    if uploaded is None:
        show_toast("An image file is required.", kind="error")
        return None
    try:
        return ArtworkDetailsInput(
            title=title,
            description=description,
            original_filename=uploaded.name,
        )
    except ValidationError:
        show_toast("Artwork title must be 200 characters or fewer.", kind="error")
        return None


def _render_create_form(service: CharacterService, selected_universe: UniverseView | None) -> None:
    with st.expander("Create character", expanded=False):
        location_options: list[str | None] = [None]
        location_labels: dict[str | None, str] = {None: "Unassigned"}
        if selected_universe is not None:
            location_options.append(selected_universe.id)
            location_labels[selected_universe.id] = f"Universe: {selected_universe.name}"
        with st.form("create-character", clear_on_submit=True):
            st.caption("\\* Required fields")
            location = st.selectbox(
                "Location",
                location_options,
                format_func=location_labels.__getitem__,
            )
            name = st.text_input("Character name *", max_chars=200)
            summary = st.text_area("Character summary *", height=220)
            st.markdown("#### Primary profile artwork")
            artwork_title = st.text_input("Artwork title *", max_chars=200)
            artwork_description = st.text_area("Artwork description *", height=120)
            uploaded = st.file_uploader(
                "Image *",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
            )
            submitted = st.form_submit_button(
                "Create character", type="primary", icon=":material/person_add:"
            )
        if not submitted:
            return
        character = _character_values(name, summary, location)
        if character is None:
            return
        artwork = _artwork_values(artwork_title, artwork_description, uploaded)
        if artwork is None or uploaded is None:
            return
        try:
            created = service.create_character(character, artwork, uploaded)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            st.session_state[SELECTED_CHARACTER_KEY] = created.id
            queue_toast(f'Created character "{created.name}".', kind="success")
            st.rerun()


def _status_filter(label: str) -> bool | None:
    return {"All": None, "Active": True, "Disabled": False}[label]


def _select_character_sidebar(
    service: CharacterService, selected_universe: UniverseView | None
) -> CharacterView | None:
    st.sidebar.divider()
    st.sidebar.subheader("Character view")
    status_label = st.sidebar.segmented_control(
        "Status filter",
        options=["All", "Active", "Disabled"],
        default="All",
        key="character-status-filter",
    )
    active = _status_filter(status_label or "All")
    selected_id = st.session_state.get(SELECTED_CHARACTER_KEY)
    universe_characters = (
        service.list_for_universe(selected_universe.id, active=active)
        if selected_universe is not None
        else []
    )
    unassigned = service.list_unassigned(active=active)
    filtered_ids = {character.id for character in universe_characters + unassigned}
    if selected_id is not None and selected_id not in filtered_ids:
        selected_character = service.get_character(selected_id)
        if selected_character is not None:
            if selected_character.universe_id is None:
                unassigned.append(selected_character)
            elif (
                selected_universe is not None
                and selected_character.universe_id == selected_universe.id
            ):
                universe_characters.append(selected_character)
    visible = universe_characters + unassigned
    st.sidebar.caption(f"{len(universe_characters)} universe · {len(unassigned)} unassigned")
    if not visible:
        st.sidebar.caption("No characters match this filter.")
        return None

    visible_by_id = {character.id: character for character in visible}
    if selected_id not in visible_by_id:
        selected_id = visible[0].id

    universe_name = selected_universe.name if selected_universe is not None else "Universe"
    labels = {
        character.id: (
            f"Unassigned · {character.name}"
            if character.universe_id is None
            else f"{universe_name} · {character.name}"
        )
        for character in visible
    }
    option_ids = list(visible_by_id)
    selected_id = st.sidebar.selectbox(
        "Character profile",
        options=option_ids,
        index=option_ids.index(selected_id),
        format_func=labels.__getitem__,
        key="character-profile-selector",
    )
    st.session_state[SELECTED_CHARACTER_KEY] = selected_id
    return visible_by_id[selected_id]


def _show_artwork(service: CharacterService, artwork: ArtworkView) -> None:
    try:
        image_url = service.storage.data_uri(artwork.relative_path, artwork.mime_type)
        st.image(
            image_url,
            width="stretch",
        )
    except MissingArtworkFileError as error:
        st.warning(str(error))


def _render_edit_profile(service: CharacterService, character: CharacterView) -> None:
    with st.expander("Edit character"):
        with st.form(f"edit-character-{character.id}"):
            st.caption("\\* Required fields")
            name = st.text_input("Character name *", value=character.name, max_chars=200)
            summary = st.text_area("Character summary *", value=character.summary, height=240)
            submitted = st.form_submit_button(
                "Save character", type="primary", icon=":material/save:"
            )
        if submitted:
            values = _character_values(name, summary, character.universe_id)
            if values is None:
                return
            try:
                service.update_character(character.id, values)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                queue_toast("Character updated.", kind="success")
                st.rerun()

    action = "Disable character" if character.is_active else "Re-enable character"
    if st.button(
        action,
        key=f"character-active-{character.id}",
        icon=":material/person_off:" if character.is_active else ":material/person_check:",
    ):
        service.set_active(character.id, is_active=not character.is_active)
        queue_toast(
            "Character disabled." if character.is_active else "Character re-enabled.",
            kind="success",
        )
        st.rerun()


def _render_location_change(
    service: CharacterService,
    character: CharacterView,
    universes: list[UniverseView],
) -> None:
    with st.expander("Change character location"):
        universe_by_id = {universe.id: universe for universe in universes}
        if character.universe_id is None:
            target_options: list[str | None] = list(universe_by_id)
        else:
            target_options = [None] + [
                universe_id
                for universe_id in universe_by_id
                if universe_id != character.universe_id
            ]
        if not target_options:
            st.info("Create a universe before assigning this character.")
            return

        target_labels: dict[str | None, str] = {None: "Unassigned"}
        target_labels.update({universe.id: universe.name for universe in universes})
        target_id = st.selectbox(
            "Destination",
            options=target_options,
            format_func=target_labels.__getitem__,
            key=f"character-move-target-{character.id}",
        )
        try:
            preflight = service.preflight_move(character.id, target_id)
        except DomainError as error:
            st.error(str(error))
            return

        st.markdown(f"**Artwork preserved:** {preflight.artwork_count} file(s)")
        st.markdown("**Non-artwork connections removed:**")
        st.markdown(
            "\n".join(
                [
                    f"- Relationships: {preflight.relationship_count}",
                    f"- Group memberships: {preflight.membership_count}",
                    f"- Story links: {preflight.story_link_count}",
                    f"- Chapter links: {preflight.chapter_link_count}",
                    f"- Milestone links: {preflight.milestone_link_count}",
                ]
            )
        )
        with st.form(f"move-character-{character.id}"):
            confirmed = False
            if preflight.requires_confirmation:
                if preflight.disables_character:
                    st.warning("This character is active. Moving it will disable it.")
                st.warning("Moving this character removes every listed non-artwork connection.")
                confirmed = st.checkbox("I confirm this character can be detached and moved.")
            submitted = st.form_submit_button(
                "Move character" if preflight.requires_confirmation else "Assign character",
                type="primary",
                icon=":material/move_item:",
            )
        if not submitted:
            return
        if preflight.requires_confirmation and not confirmed:
            show_toast("Confirm the detachment before moving this character.", kind="error")
            return
        try:
            result = service.move_character(
                character.id,
                target_id,
                confirmed=confirmed,
            )
        except DomainError as error:
            show_toast(str(error), kind="error")
        else:
            message = f'Moved "{character.name}" to {target_labels[target_id]}.'
            if result.cleanup_warning is not None:
                message = f"{message} {result.cleanup_warning}"
                queue_toast(message, kind="error")
            else:
                queue_toast(message, kind="success")
            st.rerun()


def _render_add_artwork(service: CharacterService, character: CharacterView) -> None:
    with st.expander("Add artwork"):
        with st.form(f"add-character-artwork-{character.id}", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Artwork title *", max_chars=200)
            description = st.text_area("Artwork description *", height=120)
            uploaded = st.file_uploader(
                "Image *",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"character-artwork-upload-{character.id}",
            )
            submitted = st.form_submit_button(
                "Add artwork", type="primary", icon=":material/add_photo_alternate:"
            )
        if submitted:
            values = _artwork_values(title, description, uploaded)
            if values is None or uploaded is None:
                return
            try:
                service.add_artwork(character.id, values, uploaded)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                queue_toast("Artwork added.", kind="success")
                st.rerun()


def _render_profile(
    service: CharacterService,
    character: CharacterView,
    universes: list[UniverseView],
) -> None:
    artworks = service.list_artworks(character.id)
    primary = next((artwork for artwork in artworks if artwork.is_primary), None)
    profile_image, profile_text = st.columns([1, 2])
    with profile_image:
        if primary is not None:
            with st.container(key="character-profile-image"):
                _show_artwork(service, primary)
    with profile_text:
        st.subheader(character.name)
        st.caption(
            ("Active" if character.is_active else "Disabled")
            + (" · Unassigned" if character.universe_id is None else "")
        )
        st.markdown(character.summary)

    _render_edit_profile(service, character)
    _render_location_change(service, character, universes)
    st.divider()
    st.subheader("Artwork gallery")
    _render_add_artwork(service, character)
    columns = st.columns(3)
    for index, artwork in enumerate(artworks):
        with columns[index % 3], st.container(border=True):
            with st.container(key=f"character-gallery-image-{artwork.id}"):
                _show_artwork(service, artwork)
            st.markdown(f"**{artwork.title}**")
            st.markdown(artwork.description)
            if artwork.is_primary:
                st.caption("Primary profile artwork")
            elif st.button(
                "Make primary",
                key=f"make-primary-{artwork.id}",
                icon=":material/account_circle:",
                width="stretch",
            ):
                service.set_primary_artwork(character.id, artwork.id)
                queue_toast("Primary artwork updated.", kind="success")
                st.rerun()


def render_characters(
    service: CharacterService,
    selected_universe: UniverseView | None,
    universes: list[UniverseView],
) -> None:
    """Render character creation and the sidebar-selected profile."""
    _render_preview_styles()
    st.title("Characters")
    render_queued_toast()
    _render_create_form(service, selected_universe)
    st.divider()
    selected = _select_character_sidebar(service, selected_universe)
    if selected is None:
        st.info("No characters match the current sidebar filter.")
        return
    _render_profile(service, selected, universes)
