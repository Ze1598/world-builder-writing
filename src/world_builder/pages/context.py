"""Shared universe selection and page-context helpers."""

import streamlit as st

from world_builder.domain.models import UniverseView
from world_builder.domain.services.universes import UniverseService

SELECTED_UNIVERSE_KEY = "selected_universe_id"


def render_universe_switcher(service: UniverseService) -> UniverseView | None:
    """Render the global universe selector and return its current value."""
    universes = service.list_universes()
    if not universes:
        st.session_state.pop(SELECTED_UNIVERSE_KEY, None)
        st.sidebar.info("Create a universe to begin.")
        return None

    universes_by_id = {universe.id: universe for universe in universes}
    current_id = st.session_state.get(SELECTED_UNIVERSE_KEY)
    if current_id not in universes_by_id:
        st.session_state[SELECTED_UNIVERSE_KEY] = universes[0].id

    st.sidebar.selectbox(
        "Universe",
        options=list(universes_by_id),
        format_func=lambda universe_id: universes_by_id[universe_id].name,
        key=SELECTED_UNIVERSE_KEY,
    )
    selected_id = st.session_state[SELECTED_UNIVERSE_KEY]
    return universes_by_id[selected_id]


def require_selected_universe(selected: UniverseView | None) -> UniverseView:
    """Stop a universe-dependent page when no universe is selected."""
    if selected is None:
        st.warning("Create and select a universe before using this page.")
        st.stop()
    return selected
