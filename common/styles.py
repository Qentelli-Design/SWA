"""Inject the dashboard stylesheet without duplicating it in page modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import streamlit as st

_STYLE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=4)
def _read_css(name: str) -> str:
    return (_STYLE_DIR / name).read_text(encoding="utf-8")


def inject_css(name: str) -> None:
    st.markdown(f"<style>\n{_read_css(name)}\n</style>", unsafe_allow_html=True)


def inject_global_styles() -> None:
    inject_css("app.css")
