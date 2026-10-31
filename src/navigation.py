"""Landing page, section selection, and the shared back-navigation sidebar."""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from common.excel import sheet_names
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
    "Offshore Team Skillset": ("Resource List", "Skill Categories"),
    "Quick Links": ("Sharepoint links",),
}


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
        st.markdown('<h1 class="landing-title">SWA Engagement - QMO</h1>', unsafe_allow_html=True)
    with logo_right:
        if SWA_IMAGE_PATH.is_file():
            st.image(str(SWA_IMAGE_PATH), width=100)

    st.space(10)
    with st.container(key="navigation-grid"):
        section_rows = (SECTIONS[:2], SECTIONS[2:6], SECTIONS[6:])
        section_index = 0
        for row_index, row_sections in enumerate(section_rows):
            if row_index:
                st.space(10)
            grid_columns = st.columns(4)
            if row_index == 0:
                row_columns = grid_columns[1:3]
            else:
                row_columns = grid_columns[: len(row_sections)]
            for column, section in zip(row_columns, row_sections):
                with column:
                    with st.container(key=f"navigation-item-{section_index}"):
                        st.button(
                            section,
                            key=f"navigation_{section}",
                            width="stretch",
                            on_click=select_section,
                            args=(section,),
                        )
                section_index += 1


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
            st.image(str(BRAND_IMAGE_PATH), width=90)
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
