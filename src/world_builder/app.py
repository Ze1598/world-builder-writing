"""Streamlit entry point for World Builder."""

import streamlit as st

from world_builder.domain.services.lookups import LookupService
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.context import render_universe_switcher
from world_builder.pages.home import render_home
from world_builder.pages.lookups import render_lookups
from world_builder.pages.universes import render_universes
from world_builder.persistence.migrations import SchemaState, get_schema_status
from world_builder.persistence.runtime import get_session_factory
from world_builder.settings import get_settings


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
    lookup_service = LookupService(session_factory)
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
        ]
    )
    navigation.run()


if __name__ == "__main__":
    main()
