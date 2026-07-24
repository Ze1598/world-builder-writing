"""Character group profiles, memberships, and artwork galleries."""

from typing import Any

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkEntityKind,
    CharacterGroupInput,
    CharacterGroupView,
    CharacterView,
    UniverseView,
)
from world_builder.domain.services.artworks import ArtworkService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.stories import StoryService
from world_builder.pages.artwork_links import render_existing_artwork_picker
from world_builder.pages.artwork_previews import (
    render_artwork_gallery,
    render_preview_styles,
)
from world_builder.pages.context import render_universe_filter
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast

SELECTED_GROUP_KEY = "selected_group_id"


def _group_values(universe_id: str, name: str, description: str) -> CharacterGroupInput | None:
    if not name.strip():
        show_toast("Group name is required.", kind="error")
        return None
    try:
        return CharacterGroupInput(
            universe_id=universe_id,
            name=name,
            description=description,
        )
    except ValidationError:
        show_toast("Group name must be 200 characters or fewer.", kind="error")
        return None


def _optional_artwork_values(
    title: str, description: str, uploaded: Any
) -> tuple[ArtworkDetailsInput | None, bool]:
    has_artwork_input = uploaded is not None or bool(title.strip()) or bool(description.strip())
    if not has_artwork_input:
        return None, True
    if uploaded is None:
        show_toast("An image file is required when adding artwork.", kind="error")
        return None, False
    if not title.strip():
        show_toast("Artwork title is required.", kind="error")
        return None, False
    if not description.strip():
        show_toast("Artwork description is required.", kind="error")
        return None, False
    try:
        return (
            ArtworkDetailsInput(
                title=title,
                description=description,
                original_filename=uploaded.name,
            ),
            True,
        )
    except ValidationError:
        show_toast("Artwork title must be 200 characters or fewer.", kind="error")
        return None, False


def _required_artwork_values(
    title: str, description: str, uploaded: Any
) -> ArtworkDetailsInput | None:
    values, valid = _optional_artwork_values(title, description, uploaded)
    if values is None and valid:
        show_toast("An image file is required.", kind="error")
        return None
    return values if valid else None


def _render_create_form(service: CharacterGroupService, selected_universe: UniverseView) -> None:
    with st.expander("Create character group"):
        with st.form("create-character-group", clear_on_submit=True):
            st.caption("\\* Required fields")
            name = st.text_input("Group name *", max_chars=200)
            description = st.text_area("Group description", height=180)
            st.markdown("#### Initial artwork (optional)")
            artwork_title = st.text_input("Artwork title", max_chars=200)
            artwork_description = st.text_area("Artwork description", height=100)
            uploaded = st.file_uploader(
                "Image",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
            )
            submitted = st.form_submit_button(
                "Create group", type="primary", icon=":material/group_add:"
            )
        if not submitted:
            return
        values = _group_values(selected_universe.id, name, description)
        if values is None:
            return
        artwork, artwork_valid = _optional_artwork_values(
            artwork_title, artwork_description, uploaded
        )
        if not artwork_valid:
            return
        try:
            created = service.create_group(values, artwork, uploaded)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            st.session_state[SELECTED_GROUP_KEY] = created.id
            queue_toast(f'Created group "{created.name}".', kind="success")
            st.rerun()


def _select_group(
    service: CharacterGroupService, selected_universe: UniverseView
) -> CharacterGroupView | None:
    groups = service.list_for_universe(selected_universe.id)
    if not groups:
        st.selectbox("Character group", ["No groups in this universe"], disabled=True)
        return None
    groups_by_id = {group.id: group for group in groups}
    selected_id = st.session_state.get(SELECTED_GROUP_KEY)
    if selected_id not in groups_by_id:
        selected_id = groups[0].id
    option_ids = list(groups_by_id)
    selected_id = st.selectbox(
        "Character group",
        options=option_ids,
        index=option_ids.index(selected_id),
        format_func=lambda group_id: groups_by_id[group_id].name,
        key="character-group-selector",
    )
    st.session_state[SELECTED_GROUP_KEY] = selected_id
    return groups_by_id[selected_id]


def _render_edit_group(service: CharacterGroupService, group: CharacterGroupView) -> None:
    with st.form(f"edit-group-{group.id}", border=False):
        st.caption("\\* Required fields")
        name = st.text_input("Group name *", value=group.name, max_chars=200)
        description = st.text_area("Group description", value=group.description, height=200)
        submitted = st.form_submit_button("Save group", type="primary", icon=":material/save:")
    if not submitted:
        return
    values = _group_values(group.universe_id, name, description)
    if values is None:
        return
    try:
        service.update_group(group.id, values)
    except (DomainError, ValueError) as error:
        show_toast(str(error), kind="error")
    else:
        queue_toast("Group updated.", kind="success")
        st.rerun()


def _render_group_details(service: CharacterGroupService, group: CharacterGroupView) -> None:
    st.subheader("Group details")
    _render_edit_group(service, group)


def _render_add_artwork(service: CharacterGroupService, group: CharacterGroupView) -> None:
    with st.expander("Add group artwork"):
        with st.form(f"add-group-artwork-{group.id}", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Artwork title *", max_chars=200)
            description = st.text_area("Artwork description *", height=120)
            uploaded = st.file_uploader(
                "Image *",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"group-artwork-upload-{group.id}",
            )
            submitted = st.form_submit_button(
                "Add artwork", type="primary", icon=":material/add_photo_alternate:"
            )
        if not submitted:
            return
        values = _required_artwork_values(title, description, uploaded)
        if values is None or uploaded is None:
            return
        try:
            service.add_artwork(group.id, values, uploaded)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Group artwork added.", kind="success")
            st.rerun()


def _render_memberships(
    group_service: CharacterGroupService,
    character_service: CharacterService,
    group: CharacterGroupView,
) -> None:
    memberships = group_service.list_memberships(group.id)
    member_ids = {membership.character_id for membership in memberships}
    candidates = [
        character
        for character in character_service.list_for_universe(group.universe_id)
        if character.id not in member_ids
    ]
    st.subheader("Members")
    if candidates:
        candidates_by_id: dict[str, CharacterView] = {
            character.id: character for character in candidates
        }
        with st.expander("Add member"):
            with st.form(f"add-group-member-{group.id}", clear_on_submit=True):
                character_id = st.selectbox(
                    "Character",
                    options=list(candidates_by_id),
                    format_func=lambda item_id: candidates_by_id[item_id].name,
                )
                description = st.text_area(
                    "Membership description",
                    help="Optional Markdown context for this character's membership.",
                )
                submitted = st.form_submit_button(
                    "Add member", type="primary", icon=":material/person_add:"
                )
            if submitted:
                try:
                    group_service.add_membership(group.id, character_id, description)
                except (DomainError, ValueError) as error:
                    show_toast(str(error), kind="error")
                else:
                    queue_toast("Member added.", kind="success")
                    st.rerun()
    elif not memberships:
        st.info("No characters in this universe are available to add.")

    for membership in memberships:
        status = "Active" if membership.character_is_active else "Disabled"
        with st.expander(f"{membership.character_name} · {status}"):
            with st.form(f"edit-membership-{membership.id}"):
                description = st.text_area(
                    "Membership description",
                    value=membership.description,
                    key=f"membership-description-{membership.id}",
                )
                saved = st.form_submit_button("Save description", icon=":material/save:")
            if saved:
                try:
                    group_service.update_membership(membership.id, description)
                except DomainError as error:
                    show_toast(str(error), kind="error")
                else:
                    queue_toast("Membership updated.", kind="success")
                    st.rerun()
            if st.button(
                "Remove member",
                key=f"remove-membership-{membership.id}",
                icon=":material/person_remove:",
            ):
                try:
                    group_service.remove_membership(membership.id)
                except DomainError as error:
                    show_toast(str(error), kind="error")
                else:
                    queue_toast("Member removed.", kind="success")
                    st.rerun()


def _render_profile(
    group_service: CharacterGroupService,
    character_service: CharacterService,
    group: CharacterGroupView,
    story_service: StoryService | None,
    artwork_service: ArtworkService | None,
) -> None:
    _render_group_details(group_service, group)
    if story_service is not None:
        stories = story_service.list_for_group(group.id)
        with st.expander(f"Linked stories ({len(stories)})"):
            if stories:
                for story in stories:
                    st.markdown(f"- **{story.title}** · {story.chapter_title}")
            else:
                st.caption("No stories link to this group.")
    st.divider()
    _render_memberships(group_service, character_service, group)
    st.divider()
    st.subheader("Artwork gallery")
    _render_add_artwork(group_service, group)
    artworks = (
        artwork_service.list_gallery_for_group(group.id)
        if artwork_service is not None
        else group_service.list_artworks(group.id)
    )
    if artwork_service is not None:
        render_existing_artwork_picker(
            artwork_service,
            universe_id=group.universe_id,
            entity_kind=ArtworkEntityKind.GROUP,
            entity_id=group.id,
            linked_artworks=artworks,
        )
    render_artwork_gallery(
        group_service.storage,
        artworks,
        empty_message="No artwork has been added or linked to this group.",
    )


def render_groups(
    group_service: CharacterGroupService,
    character_service: CharacterService,
    selected_universe: UniverseView | None,
    story_service: StoryService | None = None,
    artwork_service: ArtworkService | None = None,
    universes: list[UniverseView] | None = None,
) -> None:
    """Render universe-scoped group management and the selected profile."""
    render_preview_styles()
    st.title("Character groups")
    render_queued_toast()
    st.subheader("Filters")
    universe_filter, group_filter = st.columns(2, vertical_alignment="bottom")
    with universe_filter:
        selected_universe = render_universe_filter(
            universes or ([selected_universe] if selected_universe is not None else []),
            selected_universe,
        )
    if selected_universe is None:
        st.warning("Create and select a universe before managing character groups.")
        return
    with group_filter:
        selected = _select_group(group_service, selected_universe)
    _render_create_form(group_service, selected_universe)
    if selected is None:
        st.info("Create a character group in this universe to begin.")
        return
    st.divider()
    _render_profile(
        group_service,
        character_service,
        selected,
        story_service,
        artwork_service,
    )
