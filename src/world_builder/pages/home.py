"""Initial application health and welcome page."""

import streamlit as st

from world_builder.settings import Settings


def render_home(settings: Settings) -> None:
    """Render the initial application shell."""
    st.title("World Builder")
    st.write("A local-first home for characters, stories, artwork, relationships, and ideas.")

    st.subheader("Application status")
    st.success("The application shell is running.")
    st.caption(f"Data directory: {settings.data_directory}")
    st.info("Universe management will be introduced in roadmap feature F-02.")
