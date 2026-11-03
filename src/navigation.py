"""Landing page, section selection, and the shared back-navigation sidebar."""

from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from common.excel import sheet_names
from common.styles import inject_css
from config import (
    BRAND_IMAGE_PATH,
    CCC_RESOURCE_SKILLSET_FILE_PATH,
    CCC_RESOURCES_FILE_PATH,
    BAU_PERFORMANCE_FILE_PATH,
    ORG_STRUCTURE_FILE_PATH,
    PROJECT_DELIVERY_STATUS_FILE_PATH,
    SWA_IMAGE_PATH,
)

SECTIONS: tuple[str, ...] = (
    "Project Delivery Status",
    "Releases/Milestones",
    "Risks",
    "BAU Performance",
    "Team Structure",
    "ORG Structure",
    "Attrition",
    "Offshore Team Skillset",
    "Certifications",
    "Quick Links",
    "Billability",
)

_HEADERLESS_SECTIONS = frozenset(
    {"Team Structure", "ORG Structure", "Project Delivery Status", "BAU Performance"}
)
_SECTION_STATE = "dashboard_section"
_PRODUCT_WORKBOOK_SECTIONS = frozenset(
    {"Project Delivery Status", "Releases/Milestones", "Risks", "BAU Performance"}
)
_SOURCE_WORKBOOKS = {
    "Project Delivery Status": PROJECT_DELIVERY_STATUS_FILE_PATH,
    "Releases/Milestones": PROJECT_DELIVERY_STATUS_FILE_PATH,
    "Risks": PROJECT_DELIVERY_STATUS_FILE_PATH,
    "Billability": CCC_RESOURCES_FILE_PATH,
    "Attrition": CCC_RESOURCES_FILE_PATH,
    "Team Structure": CCC_RESOURCES_FILE_PATH,
    "ORG Structure": ORG_STRUCTURE_FILE_PATH,
    "Offshore Team Skillset": CCC_RESOURCE_SKILLSET_FILE_PATH,
    "Quick Links": CCC_RESOURCES_FILE_PATH,
    "BAU Performance": BAU_PERFORMANCE_FILE_PATH,
}
_SOURCE_SHEETS = {
    "Billability": ("Resource List",),
    "Team Structure": ("Resource List",),
    "ORG Structure": ("Resource List",),
    "Attrition": ("Resource List",),
    "Offshore Team Skillset": ("Resource List", "Skill Categories"),
    "Quick Links": ("Sharepoint links",),
}


_IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


@lru_cache(maxsize=4)
def _image_data_uri(path: str) -> str:
    image_path = Path(path)
    mime = _IMAGE_MIME.get(image_path.suffix.lower(), "image/png")
    return f"data:{mime};base64,{base64.b64encode(image_path.read_bytes()).decode()}"


def _render_logo(path: Path, width: int) -> None:
    """Plain <img> instead of st.image, which adds a fullscreen toolbar that blanks the page."""
    st.markdown(
        f'<img class="brand-logo" src="{_image_data_uri(str(path))}" width="{width}" alt="">',
        unsafe_allow_html=True,
    )


def ensure_session_state() -> None:
    st.session_state.setdefault(_SECTION_STATE, None)


def select_section(section: str | None) -> None:
    st.session_state[_SECTION_STATE] = section


def current_section() -> str | None:
    ensure_session_state()
    section = st.session_state[_SECTION_STATE]
    return section if isinstance(section, str) else None


_NAV_ROWS: tuple[tuple[str, ...], ...] = (SECTIONS[:2], SECTIONS[2:6], SECTIONS[6:])
_SECTION_ICONS = {
    "Project Delivery Status": ":material/rocket_launch:",
    "Releases/Milestones": ":material/event_available:",
    "Risks": ":material/warning:",
    "BAU Performance": ":material/trending_up:",
    "Team Structure": ":material/groups:",
    "ORG Structure": ":material/account_tree:",
    "Attrition": ":material/person_remove:",
    "Offshore Team Skillset": ":material/psychology:",
    "Certifications": ":material/workspace_premium:",
    "Quick Links": ":material/link:",
    "Billability": ":material/payments:",
}


def render_landing() -> None:
    inject_css("landing.css")
    with st.container(key="landing-hero"):
        logo_left, title_column, logo_right = st.columns([1, 4, 1], vertical_alignment="center")
        with logo_left:
            if BRAND_IMAGE_PATH.is_file():
                _render_logo(BRAND_IMAGE_PATH, 100)
        with title_column:
            st.markdown('<h1 class="landing-title">SWA Engagement - QMO</h1>', unsafe_allow_html=True)
        with logo_right:
            if SWA_IMAGE_PATH.is_file():
                _render_logo(SWA_IMAGE_PATH, 100)

    st.space(10)
    with st.container(key="navigation-grid"):
        for row_index, row_sections in enumerate(_NAV_ROWS):
            if row_index:
                st.space(10)
            with st.container(key=f"nav-group-{row_index}"):
                grid_columns = st.columns(max(4, len(row_sections)))
                row_columns = grid_columns[1:3] if row_index == 0 else grid_columns[: len(row_sections)]
                for column, section in zip(row_columns, row_sections):
                    with column, st.container(key=f"navigation-item-{SECTIONS.index(section)}"):
                        st.button(
                            section,
                            key=f"navigation_{section}",
                            icon=_SECTION_ICONS[section],
                            width="stretch",
                            on_click=select_section,
                            args=(section,),
                        )


def render_section_header(selected_section: str) -> None:
    if selected_section in _HEADERLESS_SECTIONS:
        return
    st.title(selected_section)


def _render_source_details(selected_section: str) -> None:
    workbook_path = _SOURCE_WORKBOOKS.get(selected_section)
    if selected_section == "Certifications" or workbook_path is None:
        body = '<div class="source-empty">No data source for this tab</div>'
    else:
        if selected_section in _PRODUCT_WORKBOOK_SECTIONS:
            try:
                worksheets = sheet_names(workbook_path)
            except (FileNotFoundError, OSError, ValueError):
                worksheets = ("Unable to read worksheet names",)
        else:
            worksheets = _SOURCE_SHEETS[selected_section]
        worksheet_label = "All sheets" if len(worksheets) > 1 else worksheets[0]
        body = (
            f'<div class="source-file">{escape(Path(workbook_path).name)}</div>'
            f'<div class="source-sheet">{escape(worksheet_label)}</div>'
        )
    st.markdown(
        f'<div class="source-card"><div class="source-label">Data source</div>{body}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(selected_section: str) -> None:
    with st.sidebar:
        if BRAND_IMAGE_PATH.is_file():
            _render_logo(BRAND_IMAGE_PATH, 90)
        st.button(
            "Dashboard overview",
            width="stretch",
            type="secondary",
            on_click=select_section,
            args=(None,),
        )
        st.divider()
        with st.container(key="source-details"):
            _render_source_details(selected_section)
