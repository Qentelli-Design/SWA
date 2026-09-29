"""Landing page, section selection, and the shared back-navigation sidebar."""

from __future__ import annotations

import streamlit as st

from config import BRAND_IMAGE_PATH, SWA_IMAGE_PATH

SECTIONS: tuple[str, ...] = (
    "Project Delivery Status",
    "Releases/Milestones",
    "Risks",
    "Billability",
    "Team Structure",
    "ORG Structure",
    "Skills",
    "Certifications",
    "Quick Links",
)

_HEADERLESS_SECTIONS = frozenset({"Team Structure", "ORG Structure", "Project Delivery Status"})
_SECTION_STATE = "dashboard_section"


def ensure_session_state() -> None:
    st.session_state.setdefault(_SECTION_STATE, None)


def select_section(section: str | None) -> None:
    st.session_state[_SECTION_STATE] = section


def current_section() -> str | None:
    ensure_session_state()
    section = st.session_state[_SECTION_STATE]
    return section if isinstance(section, str) else None


def render_landing() -> None:
    logo_left, title_column, logo_right = st.columns([1, 4, 1], vertical_alignment="center")
    with logo_left:
        if BRAND_IMAGE_PATH.is_file():
            st.image(str(BRAND_IMAGE_PATH), width=100)
    with title_column:
        st.markdown('<h1 class="landing-title">SWA Project Status</h1>', unsafe_allow_html=True)
    with logo_right:
        if SWA_IMAGE_PATH.is_file():
            st.image(str(SWA_IMAGE_PATH), width=100)

    with st.container(key="navigation-grid"):
        for start in range(0, len(SECTIONS), 4):
            row = st.columns(4)
            row_sections = SECTIONS[start : start + 4]
            for column, section in zip(row, row_sections):
                with column:
                    st.button(
                        section,
                        key=f"navigation_{section}",
                        width="stretch",
                        on_click=select_section,
                        args=(section,),
                    )


def render_section_header(selected_section: str) -> None:
    if selected_section in _HEADERLESS_SECTIONS:
        return
    st.title(selected_section)


def render_sidebar() -> None:
    with st.sidebar:
        if BRAND_IMAGE_PATH.is_file():
            st.image(str(BRAND_IMAGE_PATH), width=90)
        st.button(
            "Back to dashboard",
            width="stretch",
            type="secondary",
            on_click=select_section,
            args=(None,),
        )
