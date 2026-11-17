"""Attrition page: resource counts from the Attrition worksheet."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_sheet, require_workbook, workbook_token
from common.styles import inject_css
from common.text import display_portfolio_name

STATUS_COLUMN = "Resource Status"
ATTRITION_SHEET = "Attrition"
ATTRITION_STATUSES = ("Resigned", "Managed Attrition", "Unmanaged Attrition")
_SELECTED_KEY = "attrition_status"
_DETAIL_COLUMNS = ["Resource Name", "Portfolio", "Product", "Role", "Location", "Reporting Manager"]


def load_data(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Excel file not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_attrition_data(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_attrition_data(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    frame = read_sheet(file_path, ATTRITION_SHEET)
    if STATUS_COLUMN not in frame.columns:
        raise ValueError(f"The '{ATTRITION_SHEET}' sheet is missing: {STATUS_COLUMN}")
    for column in _DETAIL_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[_DETAIL_COLUMNS + [STATUS_COLUMN]].copy()
    for column in frame.columns:
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    return frame.reset_index(drop=True)


def count_by_status(frame: pd.DataFrame) -> dict[str, int]:
    statuses = frame[STATUS_COLUMN].str.casefold()
    return {status: int(statuses.eq(status.casefold()).sum()) for status in ATTRITION_STATUSES}


def _select_status(status: str) -> None:
    st.session_state[_SELECTED_KEY] = status


def render_attrition(file_path: str) -> None:
    frame = load_data(file_path)
    counts = count_by_status(frame)

    if st.session_state.get(_SELECTED_KEY) not in ATTRITION_STATUSES:
        st.session_state[_SELECTED_KEY] = None

    inject_css("summary_cards.css")
    inject_css("attrition.css")
    with st.container(key="attrition-cards"):
        columns = st.columns(len(ATTRITION_STATUSES))
    for index, (column, status) in enumerate(zip(columns, ATTRITION_STATUSES)):
        with column, st.container(key=f"attrition-card-{index}"):
            is_selected = st.session_state[_SELECTED_KEY] == status
            st.button(
                f"{status}\n\n**{counts[status]}**",
                key=f"attrition_{status}",
                type="primary" if is_selected else "secondary",
                width="stretch",
                on_click=_select_status,
                args=(status,),
            )

    selected = st.session_state[_SELECTED_KEY]
    if selected:
        details = frame.loc[frame[STATUS_COLUMN].str.casefold().eq(selected.casefold()), _DETAIL_COLUMNS].copy()
        details["Portfolio"] = details["Portfolio"].map(display_portfolio_name)
        st.subheader(selected)
        st.dataframe(details, hide_index=True)
