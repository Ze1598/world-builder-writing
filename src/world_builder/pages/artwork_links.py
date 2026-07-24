"""Reusable visual controls for linking existing artwork to content."""

import streamlit as st

from world_builder.domain.errors import DomainError
from world_builder.domain.models import ArtworkEntityKind, ArtworkView
from world_builder.domain.services.artworks import ArtworkService
from world_builder.pages.artwork_previews import render_gallery_preview
from world_builder.pages.notifications import queue_toast, show_toast


def render_existing_artwork_picker(
    service: ArtworkService,
    *,
    universe_id: str,
    entity_kind: ArtworkEntityKind,
    entity_id: str,
    linked_artworks: list[ArtworkView],
) -> None:
    """Render eligible images and atomically link the checked artwork."""
    linked_ids = {artwork.id for artwork in linked_artworks}
    candidates = [
        artwork
        for artwork in service.list_available_for_universe(universe_id)
        if artwork.id not in linked_ids
    ]
    with st.expander("Link existing artwork", icon=":material/add_link:"):
        if not candidates:
            st.caption("Every available artwork is already linked.")
            return
        with st.form(f"link-existing-{entity_kind.value}-{entity_id}"):
            selected_ids: list[str] = []
            columns = st.columns(3)
            for index, artwork in enumerate(candidates):
                with columns[index % 3], st.container(border=True):
                    render_gallery_preview(service.storage, artwork)
                    st.markdown(f"**{artwork.title}**")
                    st.caption(artwork.description)
                    if st.checkbox(
                        "Select",
                        key=f"select-existing-{entity_kind.value}-{entity_id}-{artwork.id}",
                    ):
                        selected_ids.append(artwork.id)
            submitted = st.form_submit_button(
                "Link selected artwork",
                type="primary",
                icon=":material/add_link:",
            )
        if not submitted:
            return
        if not selected_ids:
            show_toast("Select at least one artwork to link.", kind="error")
            return
        try:
            service.add_associations(tuple(selected_ids), entity_kind, entity_id)
        except (DomainError, ValueError) as error:
            show_toast(str(error), kind="error")
        else:
            queue_toast("Selected artwork linked.", kind="success")
            st.rerun()
