"""Risks and mitigation view built from the product status workbook.

Fully data-driven: any number of risks, products and statuses found in the
workbook are rendered, so new rows need no code changes.
"""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.charts import render_summary_chart
from common.excel import DATA_ERRORS
from common.styles import inject_css
from data_loader import build_risk_summary_from_product_status, load_risks_from_product_status

_ALL = "All"
_STATUS_COLUMN = "Risk Status"
_NAVY = "#1f4e79"


def _text_html(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip()
    if not text:
        return "<span class='rk-none'>Not provided</span>"
    return escape(text).replace("\n", "<br>")


def _tiles_html(details: pd.DataFrame) -> str:
    mitigations = details["Mitigation Plan"].fillna("").astype(str).str.strip()
    with_plan = int(mitigations.ne("").sum())
    tiles = (
        (len(details), "Total risks"),
        (details["Product"].nunique(), "Products affected"),
        (with_plan, "With mitigation"),
        (len(details) - with_plan, "No mitigation yet"),
    )
    return "<div class='rk-tiles'>" + "".join(
        f"<div class='rk-tile'><div class='rk-tile-value'>{value}</div>"
        f"<div class='rk-tile-label'>{label}</div></div>"
        for value, label in tiles
    ) + "</div>"


def _status_class(status: str) -> str:
    lowered = status.casefold()
    if "clos" in lowered:
        return " rk-closed"
    if "progress" in lowered:
        return " rk-progress"
    return ""


def _card_html(number: int, row: pd.Series) -> str:
    status = str(row.get(_STATUS_COLUMN, "") or "").strip()
    badge = f"<span class='rk-status'>{escape(status)}</span>" if status else ""
    return (
        f"<div class='rk-card{_status_class(status)}'>"
        f"<div class='rk-head'><span class='rk-num'>{number:02d}</span>"
        f"<span class='rk-product'>{escape(str(row['Product']))}</span>{badge}</div>"
        "<div class='rk-grid'>"
        f"<div class='rk-col rk-risk'><div class='rk-col-label'>Risk</div>{_text_html(row['Risks'])}</div>"
        f"<div class='rk-col rk-mit'><div class='rk-col-label'>Mitigation plan</div>"
        f"{_text_html(row['Mitigation Plan'])}</div>"
        "</div></div>"
    )


def _render_filters(details: pd.DataFrame) -> pd.DataFrame:
    """Status and product filters built from whatever values the data contains."""
    filtered = details
    if _STATUS_COLUMN in details.columns:
        statuses = details[_STATUS_COLUMN].fillna("Unknown").astype(str).str.strip()
        counts = statuses.value_counts()
        options = [_ALL, *counts.index.tolist()]
        choice = st.segmented_control(
            "Status",
            options,
            default=_ALL,
            format_func=lambda option: (
                f"{option}  |  {len(details)}" if option == _ALL else f"{option}  |  {int(counts[option])}"
            ),
            key="risk_status_filter",
        ) or _ALL
        if choice != _ALL:
            filtered = filtered[statuses.eq(choice)]

    products = sorted(details["Product"].dropna().astype(str).unique())
    selected = st.multiselect("Product", products, placeholder="All products", key="risk_product_filter")
    if selected:
        filtered = filtered[filtered["Product"].astype(str).isin(selected)]
    return filtered


def _render_risk_cards(details: pd.DataFrame) -> None:
    st.markdown(
        f"<div class='rk-section'>Risks &amp; mitigation plans ({len(details)})</div>",
        unsafe_allow_html=True,
    )
    if details.empty:
        st.info("No risks match the selected filters.")
        return
    st.markdown(
        "".join(_card_html(number, row) for number, (_, row) in enumerate(details.iterrows(), start=1)),
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download risks (CSV)",
        data=details.to_csv(index=False).encode("utf-8"),
        file_name="risks.csv",
        mime="text/csv",
        width="content",
    )


def render_risks(file_path: str) -> None:
    inject_css("risks.css")
    try:
        risk_summary = build_risk_summary_from_product_status(file_path)
        risk_details = load_risks_from_product_status(file_path)
    except DATA_ERRORS as error:
        st.error(str(error))
        return

    if risk_details.empty:
        st.info("No risks found.")
        return

    st.markdown(_tiles_html(risk_details), unsafe_allow_html=True)

    st.markdown("<div class='rk-section'>Risks by product</div>", unsafe_allow_html=True)
    render_summary_chart(
        "Risks by product",
        risk_summary,
        "Product",
        _NAVY,
        "No risks found.",
        top_n=20,
        value_column="Risks",
        show_heading=False,
        corporate=True,
    )

    filtered = _render_filters(risk_details)
    _render_risk_cards(filtered)
