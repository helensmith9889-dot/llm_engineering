"""
数据加载组件（中文注释版，逻辑与标识符保持不变）
"""
"""Loading indicators and status helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


@contextmanager
def source_status(label: str) -> Iterator[st.delta_generator.DeltaGenerator]:
    """Context manager that yields a status widget for source fetching."""
    status = st.status(label, expanded=True)
    try:
        yield status
        status.update(label=f"{label} ✅", state="complete")
    except Exception as exc:  # noqa: BLE001
        status.update(label=f"{label} ⚠️ {exc}", state="error")
        raise


def show_empty_state(message: str) -> None:
    """Render a friendly empty-state callout."""
    st.info(message, icon="🔎")
