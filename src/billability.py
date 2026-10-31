"""Billability distribution view."""

from __future__ import annotations

import streamlit as st

from common.charts import render_summary_chart
from data_loader import build_billability_summary


def render_billability(file_path: str) -> None:
    st.markdown(
        '<div class="hero-copy">Team billability status at a glance.</div>',
        unsafe_allow_html=True,
    )
    summary, _ = build_billability_summary(file_path)
    render_summary_chart(
        "Billability",
        summary,
        "Billability",
        "#1f4e79",
        "No billability data was found.",
        top_n=30,
        value_column="Resources",
        show_heading=False,
        corporate=True,
    )
