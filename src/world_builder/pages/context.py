"""Shared universe selection and page-context helpers."""

import streamlit as st

from world_builder.domain.models import UniverseView
from world_builder.domain.services.universes import UniverseService

SELECTED_UNIVERSE_KEY = "selected_universe_id"
UNIVERSE_SWITCHER_KEY = "universe_switcher_id"


def _sync_universe_selection() -> None:
    """Copy sidebar widget state into shared application state."""
    st.session_state[SELECTED_UNIVERSE_KEY] = st.session_state[UNIVERSE_SWITCHER_KEY]


def render_universe_switcher(service: UniverseService) -> UniverseView | None:
    """Render the global universe selector and return its current value."""
    universes = service.list_universes()
    if not universes:
        st.session_state.pop(SELECTED_UNIVERSE_KEY, None)
        st.session_state.pop(UNIVERSE_SWITCHER_KEY, None)
        st.sidebar.info("Create a universe to begin.")
        return None

    universes_by_id = {universe.id: universe for universe in universes}
    current_id = st.session_state.get(SELECTED_UNIVERSE_KEY)
    if current_id not in universes_by_id:
        current_id = universes[0].id
        st.session_state[SELECTED_UNIVERSE_KEY] = current_id

    if st.session_state.get(UNIVERSE_SWITCHER_KEY) != current_id:
        st.session_state[UNIVERSE_SWITCHER_KEY] = current_id

    st.sidebar.selectbox(
        "Universe",
        options=list(universes_by_id),
        format_func=lambda universe_id: universes_by_id[universe_id].name,
        key=UNIVERSE_SWITCHER_KEY,
        on_change=_sync_universe_selection,
    )
    selected_id = st.session_state[SELECTED_UNIVERSE_KEY]
    return universes_by_id[selected_id]


def require_selected_universe(selected: UniverseView | None) -> UniverseView:
    """Stop a universe-dependent page when no universe is selected."""
    if selected is None:
        st.warning("Create and select a universe before using this page.")
        st.stop()
    return selected
