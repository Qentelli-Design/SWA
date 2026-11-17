"""Reusable summary charts for count-based dashboard sections."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ACTIVITY_CHART_HEIGHT = 260


def _show_summary_chart(chart: go.Figure, selection_key: str | None) -> str | None:
    if selection_key is None:
        st.plotly_chart(chart, config={"displayModeBar": False})
        return None
    event = st.plotly_chart(
        chart, key=selection_key, on_select="rerun",
        selection_mode="points", config={"displayModeBar": False},
    )
    if event.selection.points:
        return str(event.selection.points[-1]["y"])
    return None


def render_summary_chart(
    title: str,
    summary: pd.DataFrame,
    group_column: str,
    accent: str,
    empty_message: str,
    top_n: int = 10,
    value_column: str = "Resources",
    heading_class: str | None = None,
    show_heading: bool = True,
    corporate: bool = False,
    selection_key: str | None = None,
    compact: bool = False,
) -> str | None:
    """Draw a horizontal bar chart from an aggregated summary frame."""
    if not show_heading:
        pass
    elif heading_class:
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
        height=(min(760, 110 + len(visible) * 52) if compact
                else max(420, min(760, 170 + len(visible) * 38))),
        margin=dict(l=10, r=45, t=20, b=20),
        xaxis_title=value_column,
        yaxis_title=None,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, Arial, sans-serif"),
    )
    if corporate:
        font = dict(family="DM Sans, Arial, sans-serif", color="#1f2d3d", size=13)
        chart.update_traces(
            marker=dict(color=accent, line=dict(color="#0b2540", width=1)),
            textfont=dict(size=13, color="#0b2540"),
            width=0.62,
        )
        chart.update_layout(
            font=font,
            margin=dict(l=10, r=50, t=10, b=10),
            xaxis=dict(
                title=dict(text=value_column, font=dict(size=12, color="#5b6b7b")),
                showgrid=True,
                gridcolor="#e6ebf0",
                zeroline=False,
                showline=True,
                linecolor="#cfd8e0",
                tickfont=dict(size=12, color="#5b6b7b"),
            ),
            yaxis=dict(
                showline=True,
                linecolor="#cfd8e0",
                tickfont=dict(size=13, color="#1f2d3d"),
            ),
        )
        if compact or visible[value_column].max() <= 5:
            chart.update_xaxes(dtick=1)
        with st.container(border=True, key="summary-chart-card"):
            return _show_summary_chart(chart, selection_key)
    return _show_summary_chart(chart, selection_key)


def create_activity_line_chart(
    activity_name: str,
    months: list[str],
    values: list[float | None],
    accent: str = "#087f8c",
    height: int = ACTIVITY_CHART_HEIGHT,
) -> go.Figure:
    """One reusable monthly trend line for a single BAU activity.

    Kept generic (name + months + values in) so any future product sheet with
    the same Activity/month layout can reuse it without duplicating chart code.
    """
    labels = [
        "" if value is None or pd.isna(value) else f"{int(round(value)):,}" for value in values
    ]
    numeric_values = [value for value in values if value is not None and not pd.isna(value)]
    y_range = None
    if numeric_values:
        low, high = min(numeric_values), max(numeric_values)
        span = (high - low) or high or 1
        # Extra headroom above the highest point so the "top center" value label never clips.
        y_range = [max(0, low - span * 0.15), high + span * 0.32]

    figure = go.Figure(
        go.Scatter(
            x=months,
            y=values,
            mode="lines+markers+text",
            line=dict(color=accent, width=2.5, shape="spline", smoothing=0.3),
            marker=dict(color=accent, size=9, line=dict(color="#ffffff", width=1.5)),
            text=labels,
            textposition="top center",
            textfont=dict(color="#17212b", size=12, family="DM Sans, Arial, sans-serif"),
            hovertemplate=f"{escape(activity_name)}<br>%{{x}}: %{{y:,.0f}}<extra></extra>",
            connectgaps=False,
            showlegend=False,
            cliponaxis=False,
        )
    )
    figure.update_layout(
        height=height,
        margin=dict(l=8, r=18, t=34, b=8),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, Arial, sans-serif"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#65727d")),
        yaxis=dict(
            showgrid=True,
            gridcolor="#eef2f1",
            zeroline=False,
            tickformat=",d",
            tickfont=dict(size=11, color="#8a9598"),
            range=y_range,
        ),
    )
    return figure
