"""Section dispatch. Each view stays in its own module; this file only routes."""

from __future__ import annotations

from collections.abc import Callable
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from common.charts import render_summary_chart
from config import (
    CCC_RESOURCE_SKILLSET_FILE_PATH,
    CCC_RESOURCES_FILE_PATH,
    ORG_STRUCTURE_FILE_PATH,
    PROJECT_DELIVERY_STATUS_FILE_PATH,
)
from data_loader import build_billability_summary, build_risk_summary_from_product_status, load_risks_from_product_status
from org_structure import render_org_structure
from project_delivery_status import render_project_delivery_status
from quick_links import render_quick_links
from releases import render_releases
from skills import render_skills
from team_structure import render_team_structure

_DATA_ERRORS = (FileNotFoundError, ValueError)
_RISK_STATUSES = ("Open", "Inprogress", "Closed")
_RISK_DETAIL_COLUMNS = ["Product", "Risks", "Mitigation Plan"]


def _run(action: Callable[[], None]) -> None:
    try:
        action()
    except _DATA_ERRORS as error:
        st.error(str(error))


def _render_billability() -> None:
    st.markdown(
        '<div class="hero-copy">Current billability distribution from the CCC resources sheet.</div>',
        unsafe_allow_html=True,
    )

    def _load() -> None:
        summary, details = build_billability_summary(CCC_RESOURCES_FILE_PATH)
        render_summary_chart(
            "Billability",
            summary,
            "Billability",
            "#087f8c",
            "No billability data was found.",
            top_n=30,
            value_column="Resources",
            details=details,
        )

    _run(_load)


def _render_project_delivery() -> None:
    _run(lambda: render_project_delivery_status(PROJECT_DELIVERY_STATUS_FILE_PATH))
    st.info("Project Delivery Status is ready for its data view.")


def _render_releases() -> None:
    _run(lambda: render_releases(PROJECT_DELIVERY_STATUS_FILE_PATH))


def _render_team() -> None:
    _run(lambda: render_team_structure(CCC_RESOURCES_FILE_PATH))


def _render_org() -> None:
    _run(lambda: render_org_structure(ORG_STRUCTURE_FILE_PATH))


def _render_skills() -> None:
    _run(lambda: render_skills(CCC_RESOURCE_SKILLSET_FILE_PATH))


def _render_quick_links() -> None:
    _run(lambda: render_quick_links(CCC_RESOURCES_FILE_PATH))


def _select_risk_status(status: str) -> None:
    st.session_state.risk_status = status


def _render_risk_table(selected_risks: pd.DataFrame, selected_status: str) -> None:
    detail_columns = [column for column in _RISK_DETAIL_COLUMNS if column in selected_risks.columns]
    st.subheader(f"{selected_status} risks")
    if selected_risks.empty:
        st.info(f"No {selected_status.lower()} risks were found.")
        return

    visible = selected_risks[detail_columns]
    st.dataframe(visible)
    st.download_button(
        f"Download {selected_status.lower()} risks",
        data=visible.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_status.lower()}_risks.csv",
        mime="text/csv",
        width="content",
    )


def _render_risks() -> None:
    try:
        risk_summary = build_risk_summary_from_product_status(PROJECT_DELIVERY_STATUS_FILE_PATH)
        risk_details = load_risks_from_product_status(PROJECT_DELIVERY_STATUS_FILE_PATH)
    except _DATA_ERRORS as error:
        st.error(str(error))
        return

    workbook_name = escape(Path(PROJECT_DELIVERY_STATUS_FILE_PATH).name)
    with st.sidebar:
        st.divider()
        st.markdown(
            "<div class='source-pill'><strong>Source sheet</strong><br>Product_Status_Report<br><br>"
            f"<strong>Workbook</strong><br>{workbook_name}</div>",
            unsafe_allow_html=True,
        )
    render_summary_chart(
        "Risks",
        risk_summary,
        "Product",
        "#f3c1c1",
        "No risks found.",
        top_n=20,
        value_column="Risks",
        details=risk_details,
    )
    if "Portfolio Component" in risk_summary.columns:
        render_summary_chart(
            "Risks by Portfolio Component",
            risk_summary,
            "Portfolio Component",
            "#d96c38",
            "No risk records were found.",
            top_n=30,
            value_column="Risks",
        )

    if "Risk Status" in risk_details.columns:
        status_counts = risk_details["Risk Status"].fillna("Unknown").astype(str).str.strip().value_counts()
        if "risk_status" not in st.session_state or st.session_state.risk_status not in _RISK_STATUSES:
            st.session_state.risk_status = "Open"

        st.subheader("Risk status")
        status_columns = st.columns(3)
        for column, status in zip(status_columns, _RISK_STATUSES):
            count = int(status_counts.get(status, 0))
            with column:
                st.button(
                    f"{status}  |  {count}",
                    key=f"risk_status_{status.lower()}",
                    width="stretch",
                    type="primary" if st.session_state.risk_status == status else "secondary",
                    on_click=_select_risk_status,
                    args=(status,),
                )

        selected_status = st.session_state.risk_status
        selected_risks = risk_details[
            risk_details["Risk Status"].fillna("Unknown").astype(str).str.strip().eq(selected_status)
        ].copy()
    else:
        selected_risks = risk_details.copy()
        selected_status = "All"

    _render_risk_table(selected_risks, selected_status)


_HANDLERS: dict[str, Callable[[], None]] = {
    "Billability": _render_billability,
    "Team Structure": _render_team,
    "ORG Structure": _render_org,
    "Project Delivery Status": _render_project_delivery,
    "Releases": _render_releases,
    "Risks": _render_risks,
    "Skills": _render_skills,
    "Quick Links": _render_quick_links,
}


def render_selected_section(selected_section: str) -> None:
    handler = _HANDLERS.get(selected_section)
    if handler is not None:
        handler()
