"""Transient, color-coded notifications that survive one Streamlit rerun."""

from typing import Literal

import streamlit as st

ToastKind = Literal["success", "error"]

TOAST_MESSAGE_KEY = "pending_toast_message"
TOAST_KIND_KEY = "pending_toast_kind"

TOAST_COLORS: dict[ToastKind, tuple[str, str, str]] = {
    "success": ("#0f5132", "#d1e7dd", "#75b798"),
    "error": ("#842029", "#f8d7da", "#ea868f"),
}
TOAST_ICONS: dict[ToastKind, str] = {
    "success": ":material/check_circle:",
    "error": ":material/error:",
}


def _apply_toast_style(kind: ToastKind) -> None:
    foreground, background, border = TOAST_COLORS[kind]
    st.html(
        f"""
        <style>
        @keyframes world-builder-toast-dismiss {{
            0%, 80% {{ opacity: 1; transform: translateY(0); }}
            100% {{ opacity: 0; transform: translateY(-0.5rem); visibility: hidden; }}
        }}
        [data-testid="stToast"] {{
            color: {foreground} !important;
            background: {background} !important;
            border: 1px solid {border} !important;
            animation: world-builder-toast-dismiss 1.5s ease-out forwards !important;
        }}
        [data-testid="stToast"] * {{ color: {foreground} !important; }}
        </style>
        """
    )


def show_toast(message: str, *, kind: ToastKind) -> None:
    """Display one semantically colored toast for 1.5 visible seconds."""
    _apply_toast_style(kind)
    st.toast(message, icon=TOAST_ICONS[kind], duration=2)


def queue_toast(message: str, *, kind: ToastKind) -> None:
    """Store a notification for the next completed render."""
    st.session_state[TOAST_MESSAGE_KEY] = message
    st.session_state[TOAST_KIND_KEY] = kind


def render_queued_toast() -> None:
    """Show and clear a notification queued before a rerun."""
    message = st.session_state.pop(TOAST_MESSAGE_KEY, None)
    kind = st.session_state.pop(TOAST_KIND_KEY, None)
    if message is not None and kind in TOAST_COLORS:
        show_toast(message, kind=kind)
