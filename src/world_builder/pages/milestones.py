"""Milestone idea inbox and universe-scoped link editor."""

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import (
    ChapterView,
    CharacterGroupView,
    CharacterView,
    MilestoneInput,
    MilestoneView,
    StoryView,
    UniverseView,
)
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.milestones import MilestoneService
from world_builder.domain.services.stories import StoryService
from world_builder.pages.context import render_universe_filter
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast

SELECTED_MILESTONE_KEY = "selected_milestone_id"


def _milestone_values(
    *,
    universe_id: str,
    title: str,
    content: str,
    character_ids: list[str] | tuple[str, ...] = (),
    group_ids: list[str] | tuple[str, ...] = (),
    chapter_ids: list[str] | tuple[str, ...] = (),
    story_ids: list[str] | tuple[str, ...] = (),
) -> MilestoneInput | None:
    if not title.strip():
        show_toast("Milestone title is required.", kind="error")
        return None
    if not content.strip():
        show_toast("Milestone description is required.", kind="error")
        return None
    try:
        return MilestoneInput(
            universe_id=universe_id,
            title=title,
            content=content,
            character_ids=tuple(character_ids),
            group_ids=tuple(group_ids),
            chapter_ids=tuple(chapter_ids),
            story_ids=tuple(story_ids),
        )
    except ValidationError:
        show_toast("Milestone title must be 200 characters or fewer.", kind="error")
        return None


def _render_create_form(
    service: MilestoneService,
    universe: UniverseView,
    *,
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    chapters: list[ChapterView],
    stories: list[StoryView],
) -> None:
    with st.expander("Capture milestone"):
        with st.form("create-milestone", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Title *", max_chars=200)
            content = st.text_area("Description *", height=180)
            st.markdown("#### Optional links")
            character_ids = _render_multiselect(
                "Characters",
                characters,
                (),
                name_attribute="name",
                key="create-milestone-characters",
            )
            group_ids = _render_multiselect(
                "Character groups",
                groups,
                (),
                name_attribute="name",
                key="create-milestone-groups",
            )
            chapter_ids = _render_multiselect(
                "Chapters",
                chapters,
                (),
                name_attribute="title",
                key="create-milestone-chapters",
            )
            story_ids = _render_multiselect(
                "Stories",
                stories,
                (),
                name_attribute="title",
                key="create-milestone-stories",
            )
            submitted = st.form_submit_button(
                "Capture milestone",
                type="primary",
                icon=":material/add_notes:",
            )
        if not submitted:
            return
        values = _milestone_values(
            universe_id=universe.id,
            title=title,
            content=content,
            character_ids=character_ids,
            group_ids=group_ids,
            chapter_ids=chapter_ids,
            story_ids=story_ids,
        )
        if values is None:
            return
        try:
            created = service.create_milestone(values)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            st.session_state[SELECTED_MILESTONE_KEY] = created.id
            queue_toast("Milestone captured in the idea inbox.", kind="success")
            st.rerun()


def _select_milestone(
    service: MilestoneService,
    universe: UniverseView,
    scope_container: st.delta_generator.DeltaGenerator,
    milestone_container: st.delta_generator.DeltaGenerator,
) -> MilestoneView | None:
    with scope_container:
        scope_label = st.selectbox("Scope", ["All milestones", "Unlinked inbox"])
    milestones = service.list_for_universe(universe.id)
    if scope_label == "Unlinked inbox":
        milestones = [milestone for milestone in milestones if milestone.is_unlinked]
    with milestone_container:
        if not milestones:
            st.selectbox("Milestone", ["No matching milestones"], disabled=True)
            return None
        by_id = {milestone.id: milestone for milestone in milestones}
        selected_id = st.session_state.get(SELECTED_MILESTONE_KEY)
        if selected_id not in by_id:
            selected_id = milestones[0].id
        option_ids = list(by_id)
        selected_id = st.selectbox(
            "Milestone",
            options=option_ids,
            index=option_ids.index(selected_id),
            format_func=lambda item_id: by_id[item_id].title,
            key="milestone-selector",
        )
    st.session_state[SELECTED_MILESTONE_KEY] = selected_id
    return by_id[selected_id]


def _render_multiselect(
    label: str,
    records: list[CharacterView] | list[CharacterGroupView] | list[ChapterView] | list[StoryView],
    selected_ids: tuple[str, ...],
    *,
    name_attribute: str,
    key: str,
) -> list[str]:
    names = {record.id: str(getattr(record, name_attribute)) for record in records}
    return st.multiselect(
        label,
        options=list(names),
        default=[item_id for item_id in selected_ids if item_id in names],
        format_func=names.__getitem__,
        key=key,
    )


def _render_editor(
    service: MilestoneService,
    milestone: MilestoneView,
    *,
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    chapters: list[ChapterView],
    stories: list[StoryView],
) -> None:
    st.subheader("Milestone details")
    st.caption("Planning idea · does not alter canonical story or character records")
    with st.form(f"edit-milestone-{milestone.id}", border=False):
        st.caption("\\* Required fields")
        title = st.text_input(
            "Title *",
            value=milestone.title,
            max_chars=200,
        )
        content = st.text_area(
            "Description *",
            value=milestone.content,
            height=240,
        )
        st.markdown("#### Links")
        character_ids = _render_multiselect(
            "Characters",
            characters,
            milestone.character_ids,
            name_attribute="name",
            key=f"milestone-characters-{milestone.id}",
        )
        group_ids = _render_multiselect(
            "Character groups",
            groups,
            milestone.group_ids,
            name_attribute="name",
            key=f"milestone-groups-{milestone.id}",
        )
        chapter_ids = _render_multiselect(
            "Chapters",
            chapters,
            milestone.chapter_ids,
            name_attribute="title",
            key=f"milestone-chapters-{milestone.id}",
        )
        story_ids = _render_multiselect(
            "Stories",
            stories,
            milestone.story_ids,
            name_attribute="title",
            key=f"milestone-stories-{milestone.id}",
        )
        submitted = st.form_submit_button(
            "Save milestone",
            type="primary",
            icon=":material/save:",
        )
    if submitted:
        values = _milestone_values(
            universe_id=milestone.universe_id,
            title=title,
            content=content,
            character_ids=character_ids,
            group_ids=group_ids,
            chapter_ids=chapter_ids,
            story_ids=story_ids,
        )
        if values is None:
            return
        try:
            service.update_milestone(milestone.id, values)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Milestone updated.", kind="success")
            st.rerun()

    with st.expander("Delete milestone"):
        st.warning("Deleting this milestone permanently removes the idea and all of its links.")
        confirmed = st.checkbox(
            "I confirm this milestone can be deleted.",
            key=f"delete-milestone-confirm-{milestone.id}",
        )
        if st.button(
            "Delete milestone",
            type="primary",
            icon=":material/delete:",
            disabled=not confirmed,
            key=f"delete-milestone-{milestone.id}",
        ):
            try:
                service.remove_milestone(milestone.id)
            except DomainError as error:
                show_toast(str(error), kind="error")
            else:
                st.session_state.pop(SELECTED_MILESTONE_KEY, None)
                queue_toast("Milestone deleted.", kind="success")
                st.rerun()


def render_milestones(
    milestone_service: MilestoneService,
    character_service: CharacterService,
    group_service: CharacterGroupService,
    chapter_service: ChapterService,
    story_service: StoryService,
    selected_universe: UniverseView | None,
    universes: list[UniverseView],
) -> None:
    """Render fast capture, inbox filtering, and direct milestone editing."""
    st.title("Milestones")
    render_queued_toast()
    st.subheader("Filters")
    universe_filter, scope_filter, milestone_filter = st.columns(
        3,
        vertical_alignment="bottom",
    )
    with universe_filter:
        selected_universe = render_universe_filter(universes, selected_universe)
    if selected_universe is None:
        st.warning("Create and select a universe before managing milestones.")
        return
    selected = _select_milestone(
        milestone_service,
        selected_universe,
        scope_filter,
        milestone_filter,
    )
    characters = character_service.list_for_universe(selected_universe.id)
    groups = group_service.list_for_universe(selected_universe.id)
    chapters = chapter_service.list_for_universe(selected_universe.id)
    stories = story_service.list_for_universe(selected_universe.id)
    _render_create_form(
        milestone_service,
        selected_universe,
        characters=characters,
        groups=groups,
        chapters=chapters,
        stories=stories,
    )
    if selected is None:
        st.info("Capture a milestone to begin.")
        return
    st.divider()
    _render_editor(
        milestone_service,
        selected,
        characters=characters,
        groups=groups,
        chapters=chapters,
        stories=stories,
    )
