"""Product delivery health cards and activity details."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from common.delivery import (
    STATUS_ORDER,
    count_badge as _count_badge,
    detail_value as _detail_value,
    format_actual_date as _format_actual_date,
    format_date as _format_date,
    normalize_progress,
    normalize_status,
    render_delivery_styles as _render_styles,
    status_badge as _status_badge,
)
from common.excel import CACHE_TTL, read_excel_frame, require_workbook, sheet_names, workbook_token

REQUIRED_COLUMNS = [
    "Activities",
    "Priority",
    "Owner",
    "% Completed",
    "Planned Start Date",
    "Actual Start Date",
    "Planned End Date",
    "Actual End Date",
    "Status",
    "Risks",
    "Mitigation Plan",
    "Comments",
]


def load_product_sheets(file_path: str) -> dict[str, pd.DataFrame]:
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_product_sheets(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_product_sheets(file_path: str, mtime_ns: int, size: int) -> dict[str, pd.DataFrame]:
    del mtime_ns, size
    products: dict[str, pd.DataFrame] = {}
    path = Path(file_path)
    for sheet_name in sheet_names(file_path):
        frame = read_excel_frame(path, sheet_name)
        for column in REQUIRED_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        frame = frame[REQUIRED_COLUMNS].dropna(how="all").copy()
        frame["Activities"] = frame["Activities"].fillna("").astype(str).str.strip()
        products[sheet_name] = frame[frame["Activities"].ne("")].reset_index(drop=True)
    return products


def _priority(value: object) -> str:
    text = str(value).strip().upper()
    return text if text.startswith("P") else ""


def calculate_overall_status(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "NA"

    priorities = frame["Priority"].map(_priority)
    statuses = frame["Status"].map(normalize_status)
    p1_red = (priorities.eq("P1") & statuses.eq("Red")).any()
    p1_amber = (priorities.eq("P1") & statuses.eq("Amber")).any()
    p2_red = (priorities.eq("P2") & statuses.eq("Red")).any()
    p2_amber_count = int((priorities.eq("P2") & statuses.eq("Amber")).sum())
    p3_red = (priorities.eq("P3") & statuses.eq("Red")).any()

    if p1_red:
        return "Red"
    if p1_amber or p2_red or p2_amber_count >= 2 or p3_red:
        return "Amber"
    return "Green"


def summarize_product(frame: pd.DataFrame) -> dict[str, object]:
    status_counts = frame["Status"].map(normalize_status).value_counts()
    return {
        "Green": int(status_counts.get("Green", 0)),
        "Amber": int(status_counts.get("Amber", 0)),
        "Red": int(status_counts.get("Red", 0)),
        "Overall": calculate_overall_status(frame),
    }


@st.dialog("Activity progress", width="large")
def show_product_details(product_name: str, frame: pd.DataFrame) -> None:
    st.markdown(
        f"<div class='dialog-product-title'>{escape(product_name)} - Activity Progress</div>",
        unsafe_allow_html=True,
    )
    for row_index, (_, row) in enumerate(frame.iterrows()):
        progress = normalize_progress(row["% Completed"])
        status = normalize_status(row["Status"])
        with st.container(key=f"activity-detail-{product_name}-{row_index}"):
            activity_column, owner_column, priority_column, date_column, status_column = st.columns(
                [3.2, 1.05, 0.5, 0.9, 0.7],
                gap="xsmall",
                vertical_alignment="center",
            )
            with activity_column:
                st.markdown(
                    f"<div class='activity-name'>{escape(str(row['Activities']))} -- {progress:.0f}%</div>",
                    unsafe_allow_html=True,
                )
                st.progress(progress / 100)
            with owner_column:
                st.markdown(_detail_value("Owner", str(row["Owner"]).strip() or "Unassigned"), unsafe_allow_html=True)
            with priority_column:
                st.markdown(_detail_value("Priority", _priority(row["Priority"]) or "NA"), unsafe_allow_html=True)
            with date_column:
                st.markdown(
                    "<div class='project-date-value'>"
                    + _detail_value("Planned start date", _format_date(row["Planned Start Date"]))
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div class='project-date-value'>"
                    + _detail_value("Actual end date", _format_actual_date(row["Actual End Date"]))
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with status_column:
                st.markdown(_detail_value("Status", _status_badge(status), html=True), unsafe_allow_html=True)


def render_project_delivery_status(file_path: str) -> None:
    _render_styles()
    products = load_product_sheets(file_path)
    st.markdown("<h1 class='delivery-title'>SWA Product Delivery Health</h1>", unsafe_allow_html=True)

    product_names = list(products)
    for start in range(0, len(product_names), 3):
        columns = st.columns(3, gap="medium")
        for card_index, (column, product_name) in enumerate(zip(columns, product_names[start : start + 3])):
            with column:
                frame = products[product_name]
                summary = summarize_product(frame)
                with st.container(key=f"delivery-card-{start + card_index}", border=True):
                    st.markdown(
                        f"<div class='delivery-card-title'>{escape(product_name)}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<div class='count-badge-row'>"
                        + "".join(_count_badge(status, int(summary[status])) for status in STATUS_ORDER)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<div class='status-row overall-row'><span class='status-label'>Overall</span>"
                        f"{_status_badge(str(summary['Overall']))}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("View details", key=f"delivery_details_{product_name}", width="stretch"):
                        show_product_details(product_name, frame)
