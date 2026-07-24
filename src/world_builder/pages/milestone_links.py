"""Reusable milestone reverse lookups for entity profiles."""

from collections.abc import Callable

import streamlit as st

from world_builder.domain.models import MilestoneView


def render_linked_milestones(
    loader: Callable[[str], list[MilestoneView]],
    entity_id: str,
) -> None:
    """Render planning ideas linked to one character, group, chapter, or story."""
    milestones = loader(entity_id)
    with st.expander(f"Linked milestones ({len(milestones)})"):
        if not milestones:
            st.caption("No planning ideas link to this record.")
            return
        st.caption("Planning ideas only; these do not change canonical content.")
        for milestone in milestones:
            st.markdown(f"- **{milestone.title}**")
