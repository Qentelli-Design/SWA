"""Billability distribution view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.charts import render_summary_chart
from common.styles import dialog_table_height
from data_loader import build_billability_summary


def _reset_billability_chart() -> None:
    st.session_state["billability_chart_generation"] = st.session_state.get("billability_chart_generation", 0) + 1


@st.dialog("**Billability resources**", width="small", on_dismiss=_reset_billability_chart)
def _show_billability_resources(category: str, details: pd.DataFrame) -> None:
    st.subheader(category if category else "Blank")
    resources = details.loc[:, ["Resource Name", "Product"]].copy()
    resources["Product"] = resources["Product"].replace("", "Not provided")
    resources = resources.drop_duplicates().reset_index(drop=True)
    st.dataframe(resources, hide_index=True, width="stretch", height=dialog_table_height(len(resources)))
    st.download_button(
        "Download resource list (CSV)",
        data=resources.to_csv(index=False).encode("utf-8-sig"),
        file_name="billability_resources.csv",
        mime="text/csv",
        on_click="ignore",
    )


def render_billability(file_path: str) -> None:
    st.markdown(
        '<div class="hero-copy">Team billability status at a glance.</div>',
        unsafe_allow_html=True,
    )
    summary, details = build_billability_summary(file_path)
    if not summary.empty:
        st.caption("Select a bar to view and download its resource list.")
    category = render_summary_chart(
        "Billability",
        summary,
        "Billability",
        "#1f4e79",
        "No billability data was found.",
        top_n=30,
        value_column="Resources",
        show_heading=False,
        corporate=True,
        selection_key=f"billability_chart_{st.session_state.get('billability_chart_generation', 0)}",
    )
    if category is not None:
        _show_billability_resources(category, details.loc[details["Billable"].eq(category)])
