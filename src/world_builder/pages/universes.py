"""Universe management page."""

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.models import UniverseInput, UniverseView
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.context import SELECTED_UNIVERSE_KEY, UNIVERSE_SWITCHER_KEY
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast


def _validated_input(name: str, description: str) -> UniverseInput | None:
    try:
        return UniverseInput(name=name, description=description)
    except ValidationError:
        show_toast(
            "Universe name is required and must be 200 characters or fewer.",
            kind="error",
        )
        return None


def _render_create_form(service: UniverseService) -> None:
    st.subheader("Create universe")
    with st.form("create-universe", clear_on_submit=True):
        name = st.text_input("Name", max_chars=200)
        description = st.text_area("Description", height=140)
        submitted = st.form_submit_button("Create universe", type="primary", icon=":material/add:")

    if not submitted:
        return
    values = _validated_input(name, description)
    if values is None:
        return
    try:
        universe = service.create_universe(values)
    except DomainError as error:
        show_toast(str(error), kind="error")
        return

    st.session_state[SELECTED_UNIVERSE_KEY] = universe.id
    st.session_state[UNIVERSE_SWITCHER_KEY] = universe.id
    queue_toast(f'Created universe "{universe.name}".', kind="success")
    st.rerun()


def _universe_frame(universes: list[UniverseView]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": universe.id,
                "name": universe.name,
                "description": universe.description,
            }
            for universe in universes
        ],
        columns=["id", "name", "description"],
    )


def _universe_input(row: Mapping[Hashable, Any]) -> UniverseInput:
    return UniverseInput(
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
    )


def _save_universe_frame(service: UniverseService, frame: pd.DataFrame) -> None:
    normalized_names = frame["name"].fillna("").astype(str).str.strip().str.casefold()
    if normalized_names.eq("").any():
        raise ValueError("Every universe requires a name.")
    if normalized_names.duplicated().any():
        raise ValueError("Universe names must be unique.")

    for row in frame.to_dict(orient="records"):
        service.update_universe(str(row["id"]), _universe_input(row))


def _render_universe_table(service: UniverseService, universes: list[UniverseView]) -> None:
    st.subheader("Existing universes")
    with st.form("manage-universes"):
        edited = st.data_editor(
            _universe_frame(universes),
            column_config={
                "id": None,
                "name": st.column_config.TextColumn("Name", required=True, width="medium"),
                "description": st.column_config.TextColumn("Description", width="large"),
            },
            disabled=["id"],
            hide_index=True,
            width="stretch",
            key="universe-editor",
        )
        submitted = st.form_submit_button("Save universes", type="primary", icon=":material/save:")

    if submitted:
        try:
            _save_universe_frame(service, edited)
        except (DomainError, ValidationError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Universes saved.", kind="success")
            st.rerun()


def render_universes(service: UniverseService, selected: UniverseView | None) -> None:
    """Render universe creation and table-based editing."""
    del selected
    st.title("Universes")
    render_queued_toast()
    st.write("Each universe is an isolated canon and content workspace.")

    _render_create_form(service)
    st.divider()

    universes = service.list_universes()
    if not universes:
        st.info("No universes exist yet. Create your first universe above.")
        return
    _render_universe_table(service, universes)
