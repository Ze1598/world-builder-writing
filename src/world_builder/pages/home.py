"""Initial application health and welcome page."""

import streamlit as st

from world_builder.persistence.migrations import SchemaState, get_schema_status
from world_builder.settings import Settings


def render_home(settings: Settings) -> None:
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
            "`uv run world-builder migrate`, then restart."
        )

    st.info("Universe management will be introduced in roadmap feature F-02.")
