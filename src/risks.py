"""Risks and mitigation view built from the product status workbook."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.charts import render_summary_chart
from common.excel import DATA_ERRORS
from data_loader import build_risk_summary_from_product_status, load_risks_from_product_status

_RISK_STATUSES = ("Open", "Inprogress", "Closed")
_RISK_DETAIL_COLUMNS = ["Product", "Risks", "Mitigation Plan"]


def _select_risk_status(status: str) -> None:
    st.session_state.risk_status = status


def _render_risk_table(selected_risks: pd.DataFrame, selected_status: str) -> None:
    detail_columns = [column for column in _RISK_DETAIL_COLUMNS if column in selected_risks.columns]
    if selected_status == "All":
        st.markdown("<h3 class='all-risks-heading'>All risks</h3>", unsafe_allow_html=True)
    else:
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


def _render_summary_charts(risk_summary: pd.DataFrame) -> None:
    render_summary_chart(
        "Risks and Mitigation",
        risk_summary,
        "Product",
        "#f3c1c1",
        "No risks found.",
        top_n=20,
        value_column="Risks",
        heading_class="risks-mitigation-heading",
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


def _render_status_picker(risk_details: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Render the status buttons and return the matching risks with the active status."""
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
    return selected_risks, selected_status


def render_risks(file_path: str) -> None:
    try:
        risk_summary = build_risk_summary_from_product_status(file_path)
        risk_details = load_risks_from_product_status(file_path)
    except DATA_ERRORS as error:
        st.error(str(error))
        return

    _render_summary_charts(risk_summary)

    if "Risk Status" in risk_details.columns:
        selected_risks, selected_status = _render_status_picker(risk_details)
    else:
        selected_risks, selected_status = risk_details.copy(), "All"

    _render_risk_table(selected_risks, selected_status)
