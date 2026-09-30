"""Reusable summary charts for count-based dashboard sections."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st


def render_summary_chart(
    title: str,
    summary: pd.DataFrame,
    group_column: str,
    accent: str,
    empty_message: str,
    top_n: int = 10,
    value_column: str = "Resources",
    heading_class: str | None = None,
) -> None:
    """Draw a horizontal bar chart from an aggregated summary frame."""
    if heading_class:
        st.markdown(
            f"<h3 class='{escape(heading_class)}'>{escape(title)}</h3>",
            unsafe_allow_html=True,
        )
    else:
        st.subheader(title)
    if summary.empty:
        st.info(empty_message)
        return

    visible = summary.head(top_n).copy()
    chart = px.bar(
        visible.sort_values(value_column),
        x=value_column,
        y=group_column,
        orientation="h",
        text=value_column,
        template="plotly_white",
        color_discrete_sequence=[accent],
    )
    chart.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{value_column}: %{{x}}<extra></extra>",
    )
    chart.update_layout(
        height=max(420, min(760, 170 + len(visible) * 38)),
        margin=dict(l=10, r=45, t=20, b=20),
        xaxis_title=value_column,
        yaxis_title=None,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(chart, config={"displayModeBar": False})
