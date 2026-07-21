"""Universe management page."""

import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import UniverseInput, UniverseView
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.context import SELECTED_UNIVERSE_KEY


def _validated_input(name: str, description: str) -> UniverseInput | None:
    try:
        return UniverseInput(name=name, description=description)
    except ValidationError:
        st.error("Universe name is required and must be 200 characters or fewer.")
        return None


def _render_create_form(service: UniverseService) -> None:
    st.subheader("Create universe")
    with st.form("create-universe", clear_on_submit=True):
        name = st.text_input("Name", max_chars=200)
        description = st.text_area("Description", height=160)
        submitted = st.form_submit_button("Create universe", type="primary")

    if not submitted:
        return
    values = _validated_input(name, description)
    if values is None:
        return
    try:
        universe = service.create_universe(values)
    except DomainError as error:
        st.error(str(error))
        return

    st.session_state[SELECTED_UNIVERSE_KEY] = universe.id
    st.success(f'Created universe "{universe.name}".')
    st.rerun()


def _render_universe_detail(service: UniverseService, universe: UniverseView) -> None:
    st.subheader(universe.name)
    if universe.description:
        st.markdown(universe.description)
    else:
        st.caption("No description yet.")

    st.caption(f"Universe ID: `{universe.id}`")
    st.caption(f"Created: {universe.created_at:%Y-%m-%d %H:%M UTC}")

    with st.expander("Edit universe"):
        with st.form(f"edit-universe-{universe.id}"):
            name = st.text_input("Name", value=universe.name, max_chars=200)
            description = st.text_area(
                "Description",
                value=universe.description,
                height=180,
            )
            submitted = st.form_submit_button("Save changes", type="primary")

        if submitted:
            values = _validated_input(name, description)
            if values is None:
                return
            try:
                service.update_universe(universe.id, values)
            except DomainError as error:
                st.error(str(error))
            else:
                st.success("Universe updated.")
                st.rerun()


def render_universes(service: UniverseService, selected: UniverseView | None) -> None:
    """Render universe creation, navigation, detail, and editing."""
    st.title("Universes")
    st.write("Each universe is an isolated canon and content workspace.")

    _render_create_form(service)
    st.divider()

    universes = service.list_universes()
    if not universes:
        st.info("No universes exist yet. Create your first universe above.")
        return

    st.subheader("Your universes")
    columns = st.columns(min(len(universes), 3))
    for index, universe in enumerate(universes):
        with columns[index % len(columns)]:
            st.markdown(f"#### {universe.name}")
            st.caption(universe.description or "No description yet.")
            if st.button(
                "Selected" if selected is not None and selected.id == universe.id else "Select",
                key=f"select-universe-{universe.id}",
                disabled=selected is not None and selected.id == universe.id,
                width="stretch",
            ):
                st.session_state[SELECTED_UNIVERSE_KEY] = universe.id
                st.rerun()

    current = selected or universes[0]
    st.divider()
    _render_universe_detail(service, current)
