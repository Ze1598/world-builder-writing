"""Chapter management and relative chronology."""

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import (
    ArtworkEntityKind,
    ChapterInput,
    ChapterView,
    CharacterGroupView,
    CharacterView,
    UniverseView,
)
from world_builder.domain.services.artworks import ArtworkService
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.milestones import MilestoneService
from world_builder.domain.services.stories import StoryService
from world_builder.pages.artwork_links import render_existing_artwork_picker
from world_builder.pages.artwork_previews import (
    render_artwork_gallery,
    render_preview_styles,
)
from world_builder.pages.context import render_universe_filter
from world_builder.pages.milestone_links import render_linked_milestones
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast

SELECTED_CHAPTER_KEY = "selected_chapter_id"


def _values(
    universe_id: str,
    title: str,
    description: str,
    character_ids: list[str],
    group_ids: list[str],
) -> ChapterInput | None:
    if not title.strip():
        show_toast("Chapter title is required.", kind="error")
        return None
    try:
        return ChapterInput(
            universe_id=universe_id,
            title=title,
            description=description,
            character_ids=tuple(character_ids),
            group_ids=tuple(group_ids),
        )
    except ValidationError:
        show_toast("Chapter title must be 200 characters or fewer.", kind="error")
        return None


def _link_fields(
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    *,
    character_ids: tuple[str, ...] = (),
    group_ids: tuple[str, ...] = (),
) -> tuple[list[str], list[str]]:
    characters_by_id = {character.id: character for character in characters}
    groups_by_id = {group.id: group for group in groups}
    selected_characters = st.multiselect(
        "Characters",
        options=list(characters_by_id),
        default=[item_id for item_id in character_ids if item_id in characters_by_id],
        format_func=lambda item_id: characters_by_id[item_id].name,
    )
    selected_groups = st.multiselect(
        "Character groups",
        options=list(groups_by_id),
        default=[item_id for item_id in group_ids if item_id in groups_by_id],
        format_func=lambda item_id: groups_by_id[item_id].name,
    )
    return selected_characters, selected_groups


def _render_create(
    service: ChapterService,
    universe: UniverseView,
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
) -> None:
    with st.expander("Create chapter"):
        with st.form("create-chapter", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Chapter title *", max_chars=200)
            description = st.text_area("Chapter description", height=180)
            character_ids, group_ids = _link_fields(characters, groups)
            submitted = st.form_submit_button(
                "Create chapter", type="primary", icon=":material/add:"
            )
        if not submitted:
            return
        values = _values(universe.id, title, description, character_ids, group_ids)
        if values is None:
            return
        try:
            created = service.create_chapter(values)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            st.session_state[SELECTED_CHAPTER_KEY] = created.id
            queue_toast(f'Created chapter "{created.title}".', kind="success")
            st.rerun()


def _select_chapter(chapters: list[ChapterView]) -> ChapterView | None:
    if not chapters:
        st.selectbox("Chapter", ["No chapters in this universe"], disabled=True)
        return None
    by_id = {chapter.id: chapter for chapter in chapters}
    selected_id = st.session_state.get(SELECTED_CHAPTER_KEY)
    if selected_id not in by_id:
        selected_id = chapters[0].id
    options = list(by_id)
    selected_id = st.selectbox(
        "Chapter",
        options,
        index=options.index(selected_id),
        format_func=lambda item_id: by_id[item_id].title,
        key="chapter-selector",
    )
    st.session_state[SELECTED_CHAPTER_KEY] = selected_id
    return by_id[selected_id]


def _render_timeline(chapters: list[ChapterView], selected: ChapterView) -> None:
    st.subheader("Timeline")
    positions = sorted({chapter.sequence_position for chapter in chapters})
    for position in positions:
        cohort = [chapter for chapter in chapters if chapter.sequence_position == position]
        with st.container(border=True):
            st.caption(f"Sequence {position}")
            columns = st.columns(len(cohort))
            for column, chapter in zip(columns, cohort, strict=True):
                with column:
                    marker = " · selected" if chapter.id == selected.id else ""
                    st.markdown(f"**{chapter.title}**{marker}")
                    if len(cohort) > 1:
                        st.caption("Concurrent")


def _render_edit(
    service: ChapterService,
    chapter: ChapterView,
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
) -> None:
    with st.form(f"edit-chapter-{chapter.id}", border=False):
        st.caption("\\* Required fields")
        title = st.text_input("Chapter title *", value=chapter.title, max_chars=200)
        description = st.text_area("Chapter description", value=chapter.description, height=180)
        character_ids, group_ids = _link_fields(
            characters,
            groups,
            character_ids=chapter.character_ids,
            group_ids=chapter.group_ids,
        )
        submitted = st.form_submit_button("Save chapter", type="primary", icon=":material/save:")
    if not submitted:
        return
    values = _values(chapter.universe_id, title, description, character_ids, group_ids)
    if values is None:
        return
    try:
        service.update_chapter(chapter.id, values)
    except (DomainError, ValueError) as error:
        show_toast(str(error), kind="error")
    else:
        queue_toast("Chapter updated.", kind="success")
        st.rerun()


def _render_sequence_controls(
    service: ChapterService, chapter: ChapterView, chapters: list[ChapterView]
) -> None:
    st.subheader("Sequence")
    earlier, later = st.columns(2)
    if earlier.button("Move earlier", icon=":material/arrow_upward:", width="stretch"):
        service.move_earlier(chapter.id)
        queue_toast("Chapter moved earlier.", kind="success")
        st.rerun()
    if later.button("Move later", icon=":material/arrow_downward:", width="stretch"):
        service.move_later(chapter.id)
        queue_toast("Chapter moved later.", kind="success")
        st.rerun()

    targets = {item.id: item for item in chapters if item.id != chapter.id}
    if targets:
        with st.form(f"concurrent-chapter-{chapter.id}"):
            target_id = st.selectbox(
                "Make concurrent with",
                options=list(targets),
                format_func=lambda item_id: targets[item_id].title,
            )
            submitted = st.form_submit_button("Set as concurrent", icon=":material/sync_alt:")
        if submitted:
            try:
                service.mark_concurrent(chapter.id, target_id)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                queue_toast("Chapter timing updated.", kind="success")
                st.rerun()


def _render_remove(service: ChapterService, chapter: ChapterView) -> None:
    with st.expander("Remove chapter"):
        st.warning(
            "Removing this chapter also removes its character and group links. "
            "This action cannot be undone."
        )
        confirmed = st.checkbox(
            f'I understand that "{chapter.title}" will be removed.',
            key=f"confirm-remove-chapter-{chapter.id}",
        )
        if st.button(
            "Remove chapter",
            type="primary",
            disabled=not confirmed,
            key=f"remove-chapter-{chapter.id}",
            icon=":material/delete:",
        ):
            try:
                service.remove_chapter(chapter.id)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                st.session_state.pop(SELECTED_CHAPTER_KEY, None)
                queue_toast("Chapter removed.", kind="success")
                st.rerun()


def render_chapters(
    chapter_service: ChapterService,
    character_service: CharacterService,
    group_service: CharacterGroupService,
    selected_universe: UniverseView | None,
    story_service: StoryService | None = None,
    artwork_service: ArtworkService | None = None,
    universes: list[UniverseView] | None = None,
    milestone_service: MilestoneService | None = None,
) -> None:
    """Render universe-scoped chapter management and relative chronology."""
    render_preview_styles()
    st.title("Chapters")
    render_queued_toast()
    st.subheader("Filters")
    universe_filter, chapter_filter = st.columns(2, vertical_alignment="bottom")
    with universe_filter:
        selected_universe = render_universe_filter(
            universes or ([selected_universe] if selected_universe is not None else []),
            selected_universe,
        )
    if selected_universe is None:
        st.warning("Create and select a universe before managing chapters.")
        return
    characters = character_service.list_for_universe(selected_universe.id)
    groups = group_service.list_for_universe(selected_universe.id)
    chapters = chapter_service.list_for_universe(selected_universe.id)
    with chapter_filter:
        selected = _select_chapter(chapters)
    _render_create(chapter_service, selected_universe, characters, groups)
    if selected is None:
        st.info("Create a chapter in this universe to begin.")
        return
    st.divider()
    _render_timeline(chapters, selected)
    st.subheader("Chapter details")
    _render_edit(chapter_service, selected, characters, groups)
    if artwork_service is not None:
        st.subheader("Artwork")
        chapter_artworks = artwork_service.list_gallery_for_chapter(selected.id)
        render_existing_artwork_picker(
            artwork_service,
            universe_id=selected.universe_id,
            entity_kind=ArtworkEntityKind.CHAPTER,
            entity_id=selected.id,
            linked_artworks=chapter_artworks,
        )
        render_artwork_gallery(
            artwork_service.storage,
            chapter_artworks,
            empty_message="No artwork is linked to this chapter.",
        )
    if story_service is not None:
        stories = story_service.list_for_chapter(selected.id)
        with st.expander(f"Stories ({len(stories)})"):
            if stories:
                for story in stories:
                    st.markdown(f"- **{story.title}**")
            else:
                st.caption("No stories belong to this chapter.")
    if milestone_service is not None:
        render_linked_milestones(milestone_service.list_for_chapter, selected.id)
    _render_sequence_controls(chapter_service, selected, chapters)
    _render_remove(chapter_service, selected)
