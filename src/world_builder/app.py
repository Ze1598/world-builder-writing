"""Streamlit entry point for World Builder."""

import streamlit as st

from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.lookups import LookupService
from world_builder.domain.services.stories import StoryService
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.chapters import render_chapters
from world_builder.pages.characters import render_characters
from world_builder.pages.context import render_universe_switcher
from world_builder.pages.groups import render_groups
from world_builder.pages.home import render_home
from world_builder.pages.lookups import render_lookups
from world_builder.pages.stories import render_stories
from world_builder.pages.universes import render_universes
from world_builder.persistence.migrations import SchemaState, get_schema_status
from world_builder.persistence.runtime import get_session_factory
from world_builder.settings import get_settings
from world_builder.storage.artwork import ArtworkStorage


def main() -> None:
    """Configure and run the World Builder page router."""
    st.set_page_config(
        page_title="World Builder",
        page_icon="📚",
        layout="wide",
    )

    settings = get_settings()
    schema_status = get_schema_status(settings.database_path)
    if schema_status.state is not SchemaState.CURRENT:
        navigation = st.navigation(
            [
                st.Page(
                    lambda: render_home(settings),
                    title="Home",
                    icon="🏠",
                    url_path="home",
                    default=True,
                )
            ]
        )
        navigation.run()
        return

    session_factory = get_session_factory(settings.database_path)
    universe_service = UniverseService(session_factory)
    chapter_service = ChapterService(session_factory)
    lookup_service = LookupService(session_factory)
    character_service = CharacterService(
        session_factory, ArtworkStorage(settings.artwork_directory)
    )
    group_service = CharacterGroupService(
        session_factory, ArtworkStorage(settings.artwork_directory)
    )
    story_service = StoryService(session_factory, ArtworkStorage(settings.artwork_directory))
    selected_universe = render_universe_switcher(universe_service)
    navigation = st.navigation(
        [
            st.Page(
                lambda: render_home(settings, selected_universe),
                title="Home",
                icon=":material/home:",
                url_path="home",
                default=True,
            ),
            st.Page(
                lambda: render_universes(universe_service, selected_universe),
                title="Universes",
                icon=":material/public:",
                url_path="universes",
            ),
            st.Page(
                lambda: render_lookups(lookup_service, selected_universe),
                title="Managed lookups",
                icon=":material/list_alt:",
                url_path="lookups",
            ),
            st.Page(
                lambda: render_characters(
                    character_service,
                    selected_universe,
                    universe_service.list_universes(),
                    story_service,
                ),
                title="Characters",
                icon=":material/groups:",
                url_path="characters",
            ),
            st.Page(
                lambda: render_groups(
                    group_service,
                    character_service,
                    selected_universe,
                    story_service,
                ),
                title="Character groups",
                icon=":material/group_work:",
                url_path="groups",
            ),
            st.Page(
                lambda: render_chapters(
                    chapter_service,
                    character_service,
                    group_service,
                    selected_universe,
                    story_service,
                ),
                title="Chapters",
                icon=":material/view_timeline:",
                url_path="chapters",
            ),
            st.Page(
                lambda: render_stories(
                    story_service,
                    chapter_service,
                    character_service,
                    group_service,
                    selected_universe,
                ),
                title="Stories",
                icon=":material/menu_book:",
                url_path="stories",
            ),
        ]
    )
    navigation.run()


if __name__ == "__main__":
    main()
