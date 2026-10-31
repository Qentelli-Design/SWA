"""BAU Performance dashboard for product sheets in the BAU workbook."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st
from openpyxl import load_workbook

from common.charts import create_activity_line_chart
from common.excel import read_activity_sheet, require_workbook
from common.styles import inject_css, inject_css_rules

_EXCLUDED_ACTIVITIES = frozenset({"total"})
_CHART_ACCENTS = ("#087f8c", "#d96c38", "#087f8c", "#d96c38", "#087f8c", "#d96c38", "#087f8c")
_SELECTED_PRODUCT_KEY = "bau_selected_product_sheet"


def load_bau_products(file_path: str) -> tuple[str, ...]:
    """List visible product worksheets in the BAU workbook."""
    path = require_workbook(file_path, "BAU workbook not found: {path}")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        return tuple(sheet.title for sheet in workbook.worksheets if sheet.sheet_state == "visible")
    finally:
        workbook.close()


def load_bau_data(file_path: str, product_sheet: str) -> pd.DataFrame:
    """Read one product's activity/month table."""
    require_workbook(file_path, "BAU workbook not found: {path}")
    return read_activity_sheet(file_path, product_sheet)


def clean_bau_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop the sheet's Total summary row and rows with no monthly data."""
    if raw.empty:
        return raw
    month_columns = [column for column in raw.columns if column != "Activity"]
    cleaned = raw[~raw["Activity"].str.strip().str.casefold().isin(_EXCLUDED_ACTIVITIES)].copy()
    cleaned = cleaned[cleaned[month_columns].notna().any(axis=1)]
    return cleaned.reset_index(drop=True)


def calculate_mom(previous: float | None, current: float | None) -> float | None:
    """Percent change from ``previous`` to ``current``; ``None`` when it can't be computed safely."""
    if previous is None or current is None or pd.isna(previous) or pd.isna(current):
        return None
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def _format_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{int(round(float(value))):,}"


def _format_mom(mom: float | None) -> tuple[str, str]:
    """Return (label, css_class) for a MoM percentage, safe for missing/zero baselines."""
    if mom is None:
        return "\u2013 N/A", "neutral"
    if abs(mom) < 0.05:
        return "\u2013 0.0% MoM", "neutral"
    if mom > 0:
        return f"\u25b2 +{mom:.1f}% MoM", "positive"
    return f"\u25bc {mom:.1f}% MoM", "negative"


def _render_chart_card(
    index: int, activity_name: str, months: list[str], values: list[float | None], accent: str
) -> None:
    latest_value = values[-1]
    mom = calculate_mom(values[-2] if len(values) > 1 else None, latest_value)
    mom_label, mom_class = _format_mom(mom)
    with st.container(key=f"bau-chart-{index}", border=True):
        st.markdown(
            f"<div class='bau-accent-tick' style='background:{accent}'></div>"
            f"<div class='bau-chart-title'>{escape(activity_name)}</div>"
            "<div class='bau-chart-meta'>"
            f"<span class='bau-chart-value'>{_format_value(latest_value)}</span>"
            f"<span class='bau-mom {mom_class}'>{escape(mom_label)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        figure = create_activity_line_chart(activity_name, months, values, accent=accent)
        st.plotly_chart(figure, config={"displayModeBar": False}, key=f"bau-plot-{index}")


def _select_bau_product(product_sheet: str | None) -> None:
    st.session_state[_SELECTED_PRODUCT_KEY] = product_sheet


def _render_product_picker(products: tuple[str, ...]) -> None:
    product_color_rules = "\n".join(
        f".st-key-bau-product-option-{index} {{ --bau-product-hue: {360 * index / len(products):.2f}deg; }}"
        for index in range(len(products))
    )
    inject_css_rules(product_color_rules)

    for start in range(0, len(products), 4):
        product_row = products[start : start + 4]
        columns = st.columns(4, gap="medium")
        for column, (product_index, product) in zip(columns, enumerate(product_row, start=start)):
            with column:
                with st.container(key=f"bau-product-option-{product_index}"):
                    st.button(
                        product,
                        key=f"bau-select-{product}",
                        width="stretch",
                        on_click=_select_bau_product,
                        args=(product,),
                    )


def render_bau_performance(file_path: str) -> None:
    """Show BAU workbook sheets as product choices and render the selected sheet."""
    inject_css("bau_performance.css")
    products = load_bau_products(file_path)
    if not products:
        st.info("No product sheets were found in the BAU workbook.")
        return

    selected_product = st.session_state.get(_SELECTED_PRODUCT_KEY)
    if selected_product not in products:
        selected_product = None
        st.session_state[_SELECTED_PRODUCT_KEY] = None

    if selected_product is None:
        st.markdown(
            "<div class='bau-header'>"
            "<h1 class='bau-title'>BAU PERFORMANCE</h1>"
            "<p class='bau-subtitle'>Select a product to view monthly activity trends</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        _render_product_picker(products)
        return

    st.button("All products", key="bau-all-products", on_click=_select_bau_product, args=(None,))
    raw = load_bau_data(file_path, selected_product)
    clean = clean_bau_data(raw)
    month_columns = [column for column in raw.columns if column != "Activity"]

    if len(month_columns) < 2:
        st.error(f"The '{selected_product}' sheet needs at least two month columns.")
        return

    subtitle = f"Monthly Activity Overview | {' – '.join([month_columns[0], month_columns[-1]])}"
    st.markdown(
        "<div class='bau-header'>"
        f"<h1 class='bau-title'>{escape(selected_product.upper())} — BAU PERFORMANCE</h1>"
        f"<p class='bau-subtitle'>{escape(subtitle)}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    if clean.empty or len(month_columns) < 2:
        st.info(f"No BAU activity data was found for {selected_product}.")
        return

    st.markdown("<h2 class='bau-section-heading'>Activity Performance</h2>", unsafe_allow_html=True)
    activities = clean["Activity"].tolist()
    for start in range(0, len(activities), 2):
        row_activities = activities[start : start + 2]
        columns = st.columns(2, gap="medium")
        for offset, (column, activity_name) in enumerate(zip(columns, row_activities)):
            chart_index = start + offset
            row = clean.loc[clean["Activity"] == activity_name].iloc[0]
            values = [row[month] for month in month_columns]
            accent = _CHART_ACCENTS[chart_index % len(_CHART_ACCENTS)]
            with column:
                _render_chart_card(chart_index, activity_name, month_columns, values, accent)
