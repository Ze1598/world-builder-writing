"""Artwork library, ownership, reusable links, usage, and deletion."""

import streamlit as st

from world_builder.domain.errors import DomainError
from world_builder.domain.models import (
    ArtworkDetailView,
    ArtworkEntityKind,
    ArtworkUsageView,
    ArtworkView,
    UniverseView,
)
from world_builder.domain.services.artworks import ArtworkService
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.stories import StoryService
from world_builder.pages.artwork_previews import (
    render_preview_styles,
    render_profile_preview,
)
from world_builder.pages.context import render_universe_filter
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast
from world_builder.persistence.models import ArtworkOwnerKind

SELECTED_ARTWORK_KEY = "selected_artwork_id"


def _owner_label(detail: ArtworkDetailView) -> str:
    artwork = detail.artwork
    if artwork.owner_kind is None:
        return "Unassigned"
    kind = "Character" if artwork.owner_kind is ArtworkOwnerKind.CHARACTER else "Group"
    return f"{kind}: {detail.owner_name or 'Missing owner'}"


def _select_artwork(artworks: list[ArtworkView]) -> ArtworkView | None:
    if not artworks:
        st.selectbox("Artwork", ["No artwork in this location"], disabled=True)
        return None
    by_id = {artwork.id: artwork for artwork in artworks}
    selected_id = st.session_state.get(SELECTED_ARTWORK_KEY)
    if selected_id not in by_id:
        selected_id = artworks[0].id
    options = list(by_id)
    selected_id = st.selectbox(
        "Artwork",
        options,
        index=options.index(selected_id),
        format_func=lambda artwork_id: by_id[artwork_id].title,
        key="artwork-selector",
    )
    st.session_state[SELECTED_ARTWORK_KEY] = selected_id
    return by_id[selected_id]


def _association_targets(
    universe: UniverseView,
    character_service: CharacterService,
    group_service: CharacterGroupService,
    chapter_service: ChapterService,
    story_service: StoryService,
) -> dict[ArtworkEntityKind, dict[str, str]]:
    return {
        ArtworkEntityKind.CHARACTER: {
            item.id: item.name for item in character_service.list_for_universe(universe.id)
        },
        ArtworkEntityKind.GROUP: {
            item.id: item.name for item in group_service.list_for_universe(universe.id)
        },
        ArtworkEntityKind.CHAPTER: {
            item.id: item.title for item in chapter_service.list_for_universe(universe.id)
        },
        ArtworkEntityKind.STORY: {
            item.id: item.title for item in story_service.list_for_universe(universe.id)
        },
    }


def _render_add_association(
    service: ArtworkService,
    detail: ArtworkDetailView,
    targets: dict[ArtworkEntityKind, dict[str, str]],
) -> None:
    with st.expander("Link artwork"):
        kind = st.selectbox(
            "Entity type",
            list(ArtworkEntityKind),
            format_func=lambda value: value.value.capitalize(),
            key=f"artwork-link-kind-{detail.artwork.id}",
        )
        options = targets[kind]
        if not options:
            st.info(f"No {kind.value} records are available in this universe.")
            return
        with st.form(f"add-artwork-link-{detail.artwork.id}-{kind.value}"):
            entity_id = st.selectbox(
                "Entity",
                list(options),
                format_func=options.__getitem__,
            )
            submitted = st.form_submit_button(
                "Add link", type="primary", icon=":material/add_link:"
            )
        if not submitted:
            return
        try:
            service.add_association(detail.artwork.id, kind, entity_id)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Artwork link added.", kind="success")
            st.rerun()


def _render_usages(
    service: ArtworkService,
    artwork: ArtworkView,
    usages: tuple[ArtworkUsageView, ...],
) -> None:
    st.subheader("Usage")
    if not usages:
        st.caption("This artwork has no usage links.")
        return
    for usage in usages:
        with st.container(border=True):
            st.markdown(f"**{usage.entity_name}** · {usage.entity_kind.value.capitalize()}")
            if st.button(
                "Remove link",
                key=(
                    f"remove-artwork-link-{artwork.id}-{usage.entity_kind.value}-{usage.entity_id}"
                ),
                icon=":material/link_off:",
            ):
                service.remove_association(artwork.id, usage.entity_kind, usage.entity_id)
                queue_toast("Artwork link removed.", kind="success")
                st.rerun()


def _owner_options(
    universes: list[UniverseView],
    character_service: CharacterService,
    group_service: CharacterGroupService,
) -> tuple[
    list[str],
    dict[str, tuple[ArtworkOwnerKind | None, str | None]],
    dict[str, str],
]:
    options = ["unassigned"]
    values: dict[str, tuple[ArtworkOwnerKind | None, str | None]] = {"unassigned": (None, None)}
    labels = {"unassigned": "Unassigned"}
    for universe in universes:
        for character in character_service.list_for_universe(universe.id):
            key = f"character:{character.id}"
            options.append(key)
            values[key] = (ArtworkOwnerKind.CHARACTER, character.id)
            labels[key] = f"{universe.name} · Character · {character.name}"
        for group in group_service.list_for_universe(universe.id):
            key = f"group:{group.id}"
            options.append(key)
            values[key] = (ArtworkOwnerKind.GROUP, group.id)
            labels[key] = f"{universe.name} · Group · {group.name}"
    return options, values, labels


def _render_owner_change(
    service: ArtworkService,
    detail: ArtworkDetailView,
    universes: list[UniverseView],
    character_service: CharacterService,
    group_service: CharacterGroupService,
) -> None:
    with st.expander("Change owner"):
        if detail.artwork.is_primary:
            st.warning(
                "This is a primary character artwork. Select another primary "
                "artwork before changing its owner."
            )
        options, values, labels = _owner_options(universes, character_service, group_service)
        destination = st.selectbox(
            "New owner",
            options,
            format_func=labels.__getitem__,
            key=f"artwork-owner-destination-{detail.artwork.id}",
        )
        kind, owner_id = values[destination]
        try:
            preflight = service.preflight_move(detail.artwork.id, kind, owner_id)
        except (DomainError, ValueError) as error:
            st.warning(str(error))
            return
        if preflight.incompatible_usage_count:
            st.warning(
                f"{preflight.incompatible_usage_count} link(s) from other universes "
                "will be removed."
            )
            confirmed = st.checkbox(
                "I understand that incompatible links will be removed.",
                key=f"confirm-artwork-owner-{detail.artwork.id}",
            )
        else:
            confirmed = True
        if st.button(
            "Change owner",
            type="primary",
            disabled=not confirmed,
            key=f"change-artwork-owner-{detail.artwork.id}",
            icon=":material/drive_file_move:",
        ):
            try:
                result = service.move_owner(detail.artwork.id, kind, owner_id, confirmed=confirmed)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                message = "Artwork owner changed."
                if result.cleanup_warning:
                    message = f"{message} {result.cleanup_warning}"
                queue_toast(message, kind="success")
                st.rerun()


def _render_delete(service: ArtworkService, detail: ArtworkDetailView) -> None:
    with st.expander("Delete artwork"):
        if detail.artwork.is_primary:
            st.warning("This primary artwork cannot be deleted until another primary is selected.")
            return
        st.warning(
            f"Deleting this artwork removes {len(detail.usages)} usage link(s), "
            "its metadata, and its managed image file. This action cannot be undone."
        )
        confirmed = st.checkbox(
            f'I understand that "{detail.artwork.title}" will be deleted.',
            key=f"confirm-delete-artwork-{detail.artwork.id}",
        )
        if st.button(
            "Delete artwork",
            type="primary",
            disabled=not confirmed,
            key=f"delete-artwork-{detail.artwork.id}",
            icon=":material/delete:",
        ):
            try:
                result = service.delete_artwork(detail.artwork.id)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                st.session_state.pop(SELECTED_ARTWORK_KEY, None)
                message = "Artwork deleted."
                if result.cleanup_warning:
                    message = f"{message} {result.cleanup_warning}"
                queue_toast(message, kind="success")
                st.rerun()


def render_artworks(
    service: ArtworkService,
    character_service: CharacterService,
    group_service: CharacterGroupService,
    chapter_service: ChapterService,
    story_service: StoryService,
    universes: list[UniverseView],
    selected_universe: UniverseView | None,
) -> None:
    """Render the universe and global Unassigned artwork libraries."""
    render_preview_styles()
    st.title("Artwork")
    render_queued_toast()
    st.subheader("Filters")
    universe_filter, location_filter, artwork_filter = st.columns(3, vertical_alignment="bottom")
    with universe_filter:
        selected_universe = render_universe_filter(universes, selected_universe)
    with location_filter:
        scope = st.selectbox(
            "Location",
            ["Universe", "Unassigned"],
            key="artwork-location-filter",
        )
    if scope == "Universe":
        if selected_universe is None:
            st.warning("Create and select a universe before viewing its artwork.")
            return
        artworks = service.list_owned_by_universe(selected_universe.id)
    else:
        artworks = service.list_unassigned()
    with artwork_filter:
        selected = _select_artwork(artworks)
    if selected is None:
        st.info(f"No artwork exists in {scope or 'this'} location.")
        return
    detail = service.get_detail(selected.id)
    image, metadata = st.columns([1, 2])
    with image:
        render_profile_preview(service.storage, detail.artwork)
    with metadata:
        st.subheader(detail.artwork.title)
        st.markdown(detail.artwork.description)
        st.markdown(f"**Owner:** {_owner_label(detail)}")
        st.caption(detail.artwork.original_filename)
    association_universe = selected_universe
    if detail.artwork.universe_id is not None:
        association_universe = next(
            (universe for universe in universes if universe.id == detail.artwork.universe_id),
            None,
        )
    if association_universe is not None:
        targets = _association_targets(
            association_universe,
            character_service,
            group_service,
            chapter_service,
            story_service,
        )
        _render_add_association(service, detail, targets)
    _render_usages(service, detail.artwork, detail.usages)
    _render_owner_change(service, detail, universes, character_service, group_service)
    _render_delete(service, detail)
