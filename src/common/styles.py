"""Inject the dashboard stylesheet without duplicating it in page modules."""

from __future__ import annotations

from functools import lru_cache

import streamlit as st

from config import BASE_DIR

_STYLE_DIR = BASE_DIR / "css"


@lru_cache(maxsize=16)
def _read_css(name: str) -> str:
    return (_STYLE_DIR / name).read_text(encoding="utf-8")


def inject_css_rules(css: str) -> None:
    """Inject raw CSS rules into the page.

    Uses ``st.markdown`` rather than ``st.html``: its invisible spacer is part of the tuned page layout.
    """
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)


def inject_css(name: str) -> None:
    inject_css_rules(_read_css(name))


def inject_global_styles() -> None:
    inject_css("app.css")
