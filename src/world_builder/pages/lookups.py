"""Managed vocabulary administration page."""

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from world_builder.domain.errors import DomainError
from world_builder.domain.lookups import LOOKUP_DEFINITIONS_BY_CODE, RELATIONSHIP_TYPE
from world_builder.domain.models import LookupValueInput, LookupValueView, UniverseView
from world_builder.domain.services.lookups import LookupService
from world_builder.pages.context import render_universe_filter
from world_builder.pages.notifications import queue_toast, render_queued_toast, show_toast
from world_builder.persistence.models import RelationshipDirectionality


def _table_frame(values: list[LookupValueView], category_code: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for value in values:
        row: dict[str, Any] = {
            "id": value.id,
            "name": value.name,
            "description": value.description,
            "active": value.is_active,
        }
        if category_code == RELATIONSHIP_TYPE:
            row["directionality"] = (
                value.relationship_directionality.value
                if value.relationship_directionality is not None
                else RelationshipDirectionality.SYMMETRIC.value
            )
        rows.append(row)
    columns = ["id", "name", "description", "active"]
    if category_code == RELATIONSHIP_TYPE:
        columns.append("directionality")
    return pd.DataFrame(rows, columns=columns)


def _validated_row(row: Mapping[Hashable, Any], category_code: str) -> LookupValueInput | None:
    name = str(row.get("name") or "")
    if not name.strip():
        return None
    directionality = None
    if category_code == RELATIONSHIP_TYPE:
        directionality = RelationshipDirectionality(
            row.get("directionality") or RelationshipDirectionality.SYMMETRIC.value
        )
    return LookupValueInput(
        name=name,
        description=str(row.get("description") or ""),
        relationship_directionality=directionality,
    )


def _save_frame(
    service: LookupService,
    universe_id: str,
    category_code: str,
    frame: pd.DataFrame,
) -> None:
    populated = frame.loc[frame["name"].fillna("").astype(str).str.strip().ne("")].copy()
    normalized_names = populated["name"].astype(str).str.strip().str.casefold()
    if normalized_names.duplicated().any():
        raise ValueError("Names must be unique within a lookup category.")

    for row in populated.to_dict(orient="records"):
        values = _validated_row(row, category_code)
        if values is None:
            continue
        value_id = str(row.get("id") or "")
        if value_id:
            service.update_value(value_id, values)
            service.set_active(value_id, is_active=bool(row.get("active", True)))
        else:
            created = service.create_value(universe_id, category_code, values)
            if not bool(row.get("active", True)):
                service.set_active(created.id, is_active=False)


def render_lookups(
    service: LookupService,
    selected_universe: UniverseView | None,
    universes: list[UniverseView] | None = None,
) -> None:
    """Render compact universe-specific lookup administration."""
    st.title("Managed lookups")
    render_queued_toast()
    st.subheader("Filters")
    selected_universe = render_universe_filter(
        universes or ([selected_universe] if selected_universe is not None else []),
        selected_universe,
    )
    if selected_universe is None:
        st.warning("Create and select a universe before managing lookup values.")
        return

    service.ensure_defaults(selected_universe.id)
    categories = service.list_categories()
    category_codes = [category.code for category in categories]
    category = st.selectbox(
        "Lookup category",
        category_codes,
        format_func=lambda code: LOOKUP_DEFINITIONS_BY_CODE[code].name,
        key="managed-lookup-category",
    )
    definition = LOOKUP_DEFINITIONS_BY_CODE[category]
    st.caption(f'{definition.description} Values belong only to "{selected_universe.name}".')

    values = service.list_values(selected_universe.id, category)
    column_config: dict[str, Any] = {
        "id": None,
        "name": st.column_config.TextColumn("Name", required=True, width="medium"),
        "description": st.column_config.TextColumn("Description", width="large"),
        "active": st.column_config.CheckboxColumn("Active", default=True, width="small"),
    }
    if category == RELATIONSHIP_TYPE:
        column_config["directionality"] = st.column_config.SelectboxColumn(
            "Directionality",
            options=[
                RelationshipDirectionality.SYMMETRIC.value,
                RelationshipDirectionality.DIRECTIONAL.value,
            ],
            required=True,
            default=RelationshipDirectionality.SYMMETRIC.value,
            width="small",
        )

    with st.form(f"lookup-table-{category}"):
        edited = st.data_editor(
            _table_frame(values, category),
            column_config=column_config,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key=f"lookup-editor-{category}-{selected_universe.id}",
        )
        submitted = st.form_submit_button("Save values", type="primary", icon=":material/save:")

    if submitted:
        try:
            _save_frame(service, selected_universe.id, category, edited)
        except (DomainError, ValidationError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Lookup values saved.", kind="success")
            st.rerun()
