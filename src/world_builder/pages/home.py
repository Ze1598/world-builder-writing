"""Initial application health and welcome page."""

import streamlit as st

from world_builder.domain.models import UniverseView
from world_builder.persistence.migrations import SchemaState, get_schema_status
from world_builder.settings import Settings


def render_home(settings: Settings, selected_universe: UniverseView | None = None) -> None:
    """Render the initial application shell."""
    st.title("World Builder")
    st.write("A local-first home for characters, stories, artwork, relationships, and ideas.")

    st.subheader("Application status")
    st.success("The application shell is running.")
    st.caption(f"Data directory: {settings.data_directory}")

    schema_status = get_schema_status(settings.database_path)
    if schema_status.state is SchemaState.CURRENT:
        st.success(f"Database schema is current ({schema_status.head_revision}).")
    else:
        st.warning(
            "The database schema is not ready "
            f"({schema_status.state.value}). Stop the app and run "
            "`just migrate`, then restart."
        )
        return

    if selected_universe is None:
        st.info("Create a universe from the Universes page to begin.")
    else:
        st.subheader("Current universe")
        st.markdown(f"### {selected_universe.name}")
        if selected_universe.description:
            st.markdown(selected_universe.description)
