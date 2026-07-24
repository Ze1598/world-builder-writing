"""Shared universe selection and page-context helpers."""

import streamlit as st

from world_builder.domain.models import UniverseView
from world_builder.domain.services.universes import UniverseService

SELECTED_UNIVERSE_KEY = "selected_universe_id"
UNIVERSE_SWITCHER_KEY = "universe_switcher_id"


def get_selected_universe(service: UniverseService) -> UniverseView | None:
    """Resolve the current universe without rendering UI before a page title."""
    universes = service.list_universes()
    if not universes:
        st.session_state.pop(SELECTED_UNIVERSE_KEY, None)
        st.session_state.pop(UNIVERSE_SWITCHER_KEY, None)
        return None

    universes_by_id = {universe.id: universe for universe in universes}
    widget_id = st.session_state.get(UNIVERSE_SWITCHER_KEY)
    current_id = (
        widget_id if widget_id in universes_by_id else st.session_state.get(SELECTED_UNIVERSE_KEY)
    )
    if current_id not in universes_by_id:
        current_id = universes[0].id
    st.session_state[SELECTED_UNIVERSE_KEY] = current_id
    return universes_by_id[current_id]


def render_universe_filter(
    universes: list[UniverseView],
    selected: UniverseView | None,
) -> UniverseView | None:
    """Render a page-local universe filter and synchronize shared state."""
    if not universes:
        st.selectbox("Universe", ["Create a universe to begin"], disabled=True)
        return None

    universes_by_id = {universe.id: universe for universe in universes}
    selected_id = selected.id if selected is not None else universes[0].id
    if selected_id not in universes_by_id:
        selected_id = universes[0].id
    if st.session_state.get(UNIVERSE_SWITCHER_KEY) != selected_id:
        st.session_state[UNIVERSE_SWITCHER_KEY] = selected_id

    selected_id = st.selectbox(
        "Universe",
        options=list(universes_by_id),
        format_func=lambda universe_id: universes_by_id[universe_id].name,
        key=UNIVERSE_SWITCHER_KEY,
    )
    st.session_state[SELECTED_UNIVERSE_KEY] = selected_id
    return universes_by_id[selected_id]


def require_selected_universe(selected: UniverseView | None) -> UniverseView:
    """Stop a universe-dependent page when no universe is selected."""
    if selected is None:
        st.warning("Create and select a universe before using this page.")
        st.stop()
    return selected
