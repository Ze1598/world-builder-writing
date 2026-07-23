"""Shared artwork previews that preserve original bytes for fullscreen viewing."""

import streamlit as st

from world_builder.domain.errors import MissingArtworkFileError
from world_builder.domain.models import ArtworkView
from world_builder.storage.artwork import ArtworkStorage


def render_preview_styles() -> None:
    """Standardize profile and gallery frames without affecting fullscreen images."""
    st.html(
        """
        <style>
        .st-key-artwork-profile-preview
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] {
            width: 320px !important;
            height: 320px !important;
            max-width: 100%;
            overflow: hidden !important;
            border-radius: 0.5rem;
        }
        [class*="st-key-artwork-gallery-preview-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] {
            width: 240px !important;
            height: 240px !important;
            max-width: 100%;
            overflow: hidden !important;
            border-radius: 0.5rem;
        }
        .st-key-artwork-profile-preview
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImageContainer"],
        [class*="st-key-artwork-gallery-preview-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImageContainer"] {
            width: 100% !important;
            height: 100% !important;
        }
        .st-key-artwork-profile-preview
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImageContainer"] img,
        [class*="st-key-artwork-gallery-preview-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImageContainer"] img {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
        }
        [class*="st-key-artwork-gallery-preview-"]
        [data-testid="stFullScreenFrame"]:not(:has(button[aria-label="Close fullscreen"]))
        [data-testid="stImage"] img {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
        }
        </style>
        """
    )


def render_gallery_preview(storage: ArtworkStorage, artwork: ArtworkView) -> None:
    """Render one standardized gallery crop with original-resolution fullscreen."""
    with st.container(key=f"artwork-gallery-preview-{artwork.id}"):
        _render_original(storage, artwork)


def render_profile_preview(storage: ArtworkStorage, artwork: ArtworkView) -> None:
    """Render one standardized profile crop with original-resolution fullscreen."""
    with st.container(key="artwork-profile-preview"):
        _render_original(storage, artwork)


def _render_original(storage: ArtworkStorage, artwork: ArtworkView) -> None:
    try:
        st.image(
            storage.data_uri(artwork.relative_path, artwork.mime_type),
            width="stretch",
        )
    except MissingArtworkFileError as error:
        st.warning(str(error))
