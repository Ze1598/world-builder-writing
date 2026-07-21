"""Streamlit entry point for World Builder."""

import streamlit as st

from world_builder.pages.home import render_home
from world_builder.settings import get_settings


def main() -> None:
    """Configure and run the World Builder page router."""
    st.set_page_config(
        page_title="World Builder",
        page_icon="📚",
        layout="wide",
    )

    settings = get_settings()
    navigation = st.navigation(
        [
            st.Page(
                lambda: render_home(settings),
                title="Home",
                icon="🏠",
                default=True,
            )
        ]
    )
    navigation.run()


if __name__ == "__main__":
    main()
