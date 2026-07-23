"""Story placeholders, Markdown content, associations, and artwork uploads."""

from typing import Any

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkView,
    ChapterView,
    CharacterGroupView,
    CharacterView,
    StoryInput,
    StoryView,
    UniverseView,
)
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.stories import StoryService
from world_builder.pages.artwork_previews import (
    render_gallery_preview,
    render_preview_styles,
)
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast

SELECTED_STORY_KEY = "selected_story_id"


def _import_markdown(upload_key: str, content_key: str, error_key: str) -> None:
    uploaded = st.session_state.get(upload_key)
    if uploaded is None:
        return
    try:
        st.session_state[content_key] = uploaded.getvalue().decode("utf-8-sig")
        st.session_state.pop(error_key, None)
    except UnicodeDecodeError:
        st.session_state[error_key] = "The Markdown file must use UTF-8 text encoding."


def _markdown_import(prefix: str, initial_content: str = "") -> str:
    upload_key = f"{prefix}-markdown-upload"
    content_key = f"{prefix}-content"
    error_key = f"{prefix}-markdown-error"
    reset_key = f"{prefix}-reset"
    if st.session_state.pop(reset_key, False):
        st.session_state.pop(upload_key, None)
        st.session_state.pop(content_key, None)
        st.session_state.pop(error_key, None)
    st.session_state.setdefault(content_key, initial_content)
    st.file_uploader(
        "Import Markdown file",
        type=["md", "markdown", "txt"],
        key=upload_key,
        on_change=_import_markdown,
        args=(upload_key, content_key, error_key),
    )
    if error := st.session_state.get(error_key):
        st.error(error)
    return content_key


def _story_values(
    universe_id: str,
    chapter_id: str,
    title: str,
    content: str,
    character_ids: list[str],
    group_ids: list[str],
    artwork_ids: list[str],
) -> StoryInput | None:
    if not title.strip():
        show_toast("Story title is required.", kind="error")
        return None
    try:
        return StoryInput(
            universe_id=universe_id,
            chapter_id=chapter_id,
            title=title,
            content=content,
            character_ids=tuple(character_ids),
            group_ids=tuple(group_ids),
            artwork_ids=tuple(artwork_ids),
        )
    except ValidationError:
        show_toast("Story title must be 200 characters or fewer.", kind="error")
        return None


def _artwork_values(
    title: str, description: str, uploaded: Any
) -> tuple[ArtworkDetailsInput | None, bool]:
    supplied = uploaded is not None or bool(title.strip()) or bool(description.strip())
    if not supplied:
        return None, True
    if uploaded is None:
        show_toast("Select an image when adding artwork.", kind="error")
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


def _association_fields(
    prefix: str,
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    artworks: list[ArtworkView],
    *,
    character_ids: tuple[str, ...] = (),
    group_ids: tuple[str, ...] = (),
    artwork_ids: tuple[str, ...] = (),
) -> tuple[list[str], list[str], list[str]]:
    characters_by_id = {item.id: item for item in characters}
    groups_by_id = {item.id: item for item in groups}
    artworks_by_id = {item.id: item for item in artworks}
    selected_characters = st.multiselect(
        "Characters",
        list(characters_by_id),
        default=[item_id for item_id in character_ids if item_id in characters_by_id],
        format_func=lambda item_id: characters_by_id[item_id].name,
        key=f"{prefix}-characters",
    )
    selected_groups = st.multiselect(
        "Character groups",
        list(groups_by_id),
        default=[item_id for item_id in group_ids if item_id in groups_by_id],
        format_func=lambda item_id: groups_by_id[item_id].name,
        key=f"{prefix}-groups",
    )
    selected_artworks = st.multiselect(
        "Existing artwork",
        list(artworks_by_id),
        default=[item_id for item_id in artwork_ids if item_id in artworks_by_id],
        format_func=lambda item_id: artworks_by_id[item_id].title,
        key=f"{prefix}-artworks",
    )
    return selected_characters, selected_groups, selected_artworks


def _render_create(
    service: StoryService,
    universe: UniverseView,
    chapters: list[ChapterView],
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    artworks: list[ArtworkView],
) -> None:
    if not chapters:
        st.info("Create a chapter before creating a story.")
        return
    with st.expander("Create story"):
        content_key = _markdown_import("create-story")
        chapters_by_id = {chapter.id: chapter for chapter in chapters}
        with st.form("create-story-form", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Story title *", max_chars=200)
            chapter_id = st.selectbox(
                "Chapter *",
                list(chapters_by_id),
                format_func=lambda item_id: chapters_by_id[item_id].title,
            )
            content = st.text_area(
                "Story Markdown",
                height=420,
                key=content_key,
                help="Optional while the story is a placeholder.",
            )
            character_ids, group_ids, artwork_ids = _association_fields(
                "create-story", characters, groups, artworks
            )
            st.markdown("#### Upload new unassigned artwork (optional)")
            artwork_title = st.text_input("Artwork title", max_chars=200)
            artwork_description = st.text_area("Artwork description", height=100)
            uploaded_artwork = st.file_uploader(
                "Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="create-story-artwork-upload",
            )
            submitted = st.form_submit_button("Create story", type="primary", icon=":material/add:")
        if not submitted:
            return
        values = _story_values(
            universe.id,
            chapter_id,
            title,
            content,
            character_ids,
            group_ids,
            artwork_ids,
        )
        details, valid_artwork = _artwork_values(
            artwork_title, artwork_description, uploaded_artwork
        )
        if values is None or not valid_artwork:
            return
        try:
            created = service.create_story(values, details, uploaded_artwork)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            st.session_state[SELECTED_STORY_KEY] = created.id
            st.session_state["create-story-reset"] = True
            queue_toast(f'Created story "{created.title}".', kind="success")
            st.rerun()


def _select_story(stories: list[StoryView]) -> StoryView | None:
    st.sidebar.divider()
    st.sidebar.subheader("Story view")
    st.sidebar.caption(f"{len(stories)} story or stories")
    if not stories:
        return None
    by_id = {story.id: story for story in stories}
    selected_id = st.session_state.get(SELECTED_STORY_KEY)
    if selected_id not in by_id:
        selected_id = stories[0].id
    options = list(by_id)
    selected_id = st.sidebar.selectbox(
        "Story",
        options,
        index=options.index(selected_id),
        format_func=lambda item_id: by_id[item_id].title,
        key="story-selector",
    )
    st.session_state[SELECTED_STORY_KEY] = selected_id
    return by_id[selected_id]


def _render_edit(
    service: StoryService,
    story: StoryView,
    chapters: list[ChapterView],
    characters: list[CharacterView],
    groups: list[CharacterGroupView],
    artworks: list[ArtworkView],
) -> None:
    prefix = f"edit-story-{story.id}"
    with st.expander("Edit story"):
        content_key = _markdown_import(prefix, story.content)
        chapters_by_id = {chapter.id: chapter for chapter in chapters}
        with st.form(f"{prefix}-form"):
            st.caption("\\* Required fields")
            title = st.text_input("Story title *", value=story.title, max_chars=200)
            chapter_options = list(chapters_by_id)
            chapter_id = st.selectbox(
                "Chapter *",
                chapter_options,
                index=chapter_options.index(story.chapter_id),
                format_func=lambda item_id: chapters_by_id[item_id].title,
            )
            content = st.text_area("Story Markdown", height=500, key=content_key)
            character_ids, group_ids, artwork_ids = _association_fields(
                prefix,
                characters,
                groups,
                artworks,
                character_ids=story.character_ids,
                group_ids=story.group_ids,
                artwork_ids=story.artwork_ids,
            )
            submitted = st.form_submit_button("Save story", type="primary", icon=":material/save:")
        if submitted:
            values = _story_values(
                story.universe_id,
                chapter_id,
                title,
                content,
                character_ids,
                group_ids,
                artwork_ids,
            )
            if values is None:
                return
            try:
                service.update_story(story.id, values)
            except (DomainError, ValueError) as error:
                show_toast(str(error), kind="error")
            else:
                queue_toast("Story updated.", kind="success")
                st.rerun()


def _render_add_artwork(service: StoryService, story: StoryView) -> None:
    with st.expander("Upload unassigned artwork"):
        with st.form(f"story-artwork-{story.id}", clear_on_submit=True):
            st.caption("\\* Required fields")
            title = st.text_input("Artwork title *", max_chars=200)
            description = st.text_area("Artwork description *", height=120)
            uploaded = st.file_uploader(
                "Image *",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"story-artwork-upload-{story.id}",
            )
            submitted = st.form_submit_button(
                "Upload and link", type="primary", icon=":material/add_photo_alternate:"
            )
        if not submitted:
            return
        details, valid = _artwork_values(title, description, uploaded)
        if not valid or details is None or uploaded is None:
            return
        try:
            service.add_unassigned_artwork(story.id, details, uploaded)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Artwork uploaded and linked.", kind="success")
            st.rerun()


def _render_gallery(service: StoryService, story: StoryView, artworks: list[ArtworkView]) -> None:
    by_id = {artwork.id: artwork for artwork in artworks}
    linked = [by_id[item_id] for item_id in story.artwork_ids if item_id in by_id]
    if not linked:
        return
    st.subheader("Artwork")
    columns = st.columns(3)
    for index, artwork in enumerate(linked):
        with columns[index % 3], st.container(border=True):
            render_gallery_preview(service.storage, artwork)
            st.markdown(f"**{artwork.title}**")
            st.markdown(artwork.description)


def _render_remove(service: StoryService, story: StoryView) -> None:
    with st.expander("Delete story"):
        st.warning(
            "Deleting this story removes its links but does not delete any artwork. "
            "This action cannot be undone."
        )
        confirmed = st.checkbox(
            f'I understand that "{story.title}" will be deleted.',
            key=f"confirm-delete-story-{story.id}",
        )
        if st.button(
            "Delete story",
            type="primary",
            disabled=not confirmed,
            key=f"delete-story-{story.id}",
            icon=":material/delete:",
        ):
            try:
                service.remove_story(story.id)
            except DomainError as error:
                show_toast(str(error), kind="error")
            else:
                st.session_state.pop(SELECTED_STORY_KEY, None)
                queue_toast("Story deleted.", kind="success")
                st.rerun()


def render_stories(
    story_service: StoryService,
    chapter_service: ChapterService,
    character_service: CharacterService,
    group_service: CharacterGroupService,
    selected_universe: UniverseView | None,
) -> None:
    """Render story placeholders, content, associations, and artwork."""
    render_preview_styles()
    st.title("Stories")
    render_queued_toast()
    if selected_universe is None:
        st.warning("Create and select a universe before managing stories.")
        return
    chapters = chapter_service.list_for_universe(selected_universe.id)
    characters = character_service.list_for_universe(selected_universe.id)
    groups = group_service.list_for_universe(selected_universe.id)
    artworks = story_service.list_available_artworks(selected_universe.id)
    _render_create(
        story_service,
        selected_universe,
        chapters,
        characters,
        groups,
        artworks,
    )
    stories = story_service.list_for_universe(selected_universe.id)
    selected = _select_story(stories)
    if selected is None:
        if chapters:
            st.info("Create a story placeholder in this universe to begin.")
        return
    st.divider()
    st.caption(f"Chapter: {selected.chapter_title}")
    st.title(selected.title)
    if selected.content:
        st.markdown(selected.content)
    else:
        st.info("This story is a placeholder with no written content.")
    with st.container(horizontal=True):
        st.download_button(
            "Download Markdown",
            data=selected.content,
            file_name=f"{selected.title}.md",
            mime="text/markdown",
            icon=":material/download:",
        )
    if selected.character_names:
        st.markdown(f"**Characters:** {', '.join(selected.character_names)}")
    if selected.group_names:
        st.markdown(f"**Groups:** {', '.join(selected.group_names)}")
    _render_gallery(story_service, selected, artworks)
    _render_edit(story_service, selected, chapters, characters, groups, artworks)
    _render_add_artwork(story_service, selected)
    _render_remove(story_service, selected)
