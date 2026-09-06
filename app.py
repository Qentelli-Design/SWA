from pathlib import Path

import plotly.express as px
import streamlit as st

from config import (
    APP_TITLE,
    BRAND_IMAGE_PATH,
    CCC_RESOURCES_FILE_PATH,
    EXCEL_FILE_PATH,
    RISK_TRACKER_FILE_PATH,
    SWA_IMAGE_PATH,
)
from data_loader import (
    build_billability_summary,
    build_risk_summary,
    build_location_summary,
    build_total_resources,
    get_dashboard_summary,
    load_risks,
    load_detail1,
)
from team_structure import render_team_structure

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --ink: #17212b;
        --muted: #65727d;
        --paper: #f4f7f6;
        --teal: #087f8c;
        --orange: #d96c38;
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    [data-testid="stAppViewContainer"] .block-container {
        max-width: 1500px;
        padding-top: calc(0.85rem + 40px) !important;
        padding-bottom: 0.65rem;
    }

    [data-testid="stHeader"] {
        background: rgba(244, 247, 246, 0.88);
    }

    [data-testid="stSidebar"] {
        background: #17212b;
    }

    [data-testid="stSidebar"] * {
        color: #edf4f2;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #edf4f2;
        font-weight: 600;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent;
        border: 0;
        border-radius: 0;
        margin-bottom: 0.15rem;
        padding: 0.3rem 0;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: transparent;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #edf4f2 !important;
        font-weight: 600;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #75d3cc !important;
    }

    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: 0;
    }

    p, label, .stMarkdown, .stCaption, [data-testid="stMetricLabel"] {
        font-family: 'DM Sans', sans-serif;
        letter-spacing: 0;
    }

    h1 {
        font-size: 2.45rem;
        line-height: 1.05;
        margin-top: 0.35rem;
        margin-bottom: 0.15rem;
    }

    .landing-title {
        color: #087f8c;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.35rem;
        font-weight: 700;
        margin: 0;
        padding-top: 0.35rem;
        text-align: center;
    }

    .eyebrow {
        color: var(--teal);
        display: block;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-top: calc(0.75rem + 10px);
        position: relative;
        text-transform: uppercase;
        z-index: 1;
    }

    .hero-copy {
        color: var(--muted);
        font-size: 1rem;
        margin-bottom: 1.25rem;
    }

    .section-note {
        color: var(--muted);
        font-size: 0.88rem;
        margin-top: -0.35rem;
    }

    .source-pill {
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 8px;
        color: #b9d6d2;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.78rem;
        line-height: 1.45;
        padding: 0.7rem;
    }

    [data-testid="stButton"] button {
        border-radius: 8px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.92rem;
        font-weight: 700;
        min-height: 44px;
        transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
    }

    [data-testid="stButton"] button p,
    [data-testid="stButton"] button span {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stButton"] button[kind="secondary"] {
        background: #ffffff;
        border: 1px solid #b9c9cb;
        color: #25343d;
    }

    [data-testid="stButton"] button[kind="secondary"]:hover {
        background: #e8f3f1;
        border-color: #087f8c;
        color: #075f69;
    }

    [data-testid="stButton"] button[kind="primary"] {
        background: #087f8c;
        border: 1px solid #087f8c;
        color: #ffffff;
        box-shadow: 0 4px 12px rgba(8, 127, 140, 0.22);
    }

    [data-testid="stButton"] button[kind="primary"]:hover {
        background: #075f69;
        border-color: #075f69;
    }

    [data-testid="stButton"] button:focus-visible {
        border-color: #54b8b3;
        box-shadow: 0 0 0 3px rgba(84, 184, 179, 0.28);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #dfe7e9;
        border-radius: 8px;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button {
        background: #75d3cc;
        border: 1px solid #75d3cc;
        border-radius: 8px;
        color: #17212b;
        font-size: 0.92rem;
        font-weight: 700;
        min-height: 42px;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button p,
    [data-testid="stSidebar"] [data-testid="stButton"] button span {
        color: #17212b !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background: #a3e5df;
        border-color: #a3e5df;
        color: #17212b;
    }

    .st-key-navigation-grid [data-testid="stButton"] button {
        border: 1px solid transparent;
        color: #17212b;
        font-weight: 700;
    }

    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:first-child [data-testid="stColumn"]:nth-child(1) [data-testid="stButton"] button { background: #d9eee9; border-color: #9bcfc5; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:first-child [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button { background: #dce9f5; border-color: #a8c6df; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:first-child [data-testid="stColumn"]:nth-child(3) [data-testid="stButton"] button { background: #f7e6d5; border-color: #e4c19d; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:first-child [data-testid="stColumn"]:nth-child(4) [data-testid="stButton"] button { background: #f3e5e5; border-color: #dfbaba; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:last-child [data-testid="stColumn"]:nth-child(1) [data-testid="stButton"] button { background: #e8e1f3; border-color: #c6b6df; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:last-child [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button { background: #e8f0d9; border-color: #c1d59e; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:last-child [data-testid="stColumn"]:nth-child(3) [data-testid="stButton"] button { background: #e4edf1; border-color: #b9cfd8; }
    .st-key-navigation-grid [data-testid="stHorizontalBlock"]:last-child [data-testid="stColumn"]:nth-child(4) [data-testid="stButton"] button { background: #f5e8c8; border-color: #dfc98e; }

    .st-key-navigation-grid [data-testid="stButton"] button:hover {
        filter: brightness(0.96);
        border-color: #087f8c;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    base_frame = load_detail1(EXCEL_FILE_PATH)
    summary_metrics = get_dashboard_summary(EXCEL_FILE_PATH)
except FileNotFoundError:
    st.error(f"Excel file not found: {EXCEL_FILE_PATH}")
    st.stop()
except ValueError as error:
    st.error(str(error))
    st.stop()

sections = [
    "Resource pulse",
    "Billability",
    "Team structure",
    "Skills",
    "Certifications",
    "Project delivery status",
    "ORG Structure",
    "Risks",
]

if "dashboard_section" not in st.session_state:
    st.session_state.dashboard_section = None


def render_summary_chart(
    title: str,
    summary,
    group_column: str,
    accent: str,
    empty_message: str,
    top_n: int = 10,
    value_column: str = "Resources",
) -> None:
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
    chart.update_traces(textposition="outside", cliponaxis=False, hovertemplate=f"%{{y}}<br>{value_column}: %{{x}}<extra></extra>")
    chart.update_layout(
        height=max(420, min(760, 170 + len(visible) * 38)),
        margin=dict(l=10, r=45, t=20, b=20),
        xaxis_title=value_column,
        yaxis_title=None,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
    st.download_button(
        "Download chart data",
        data=visible.to_csv(index=False).encode("utf-8"),
        file_name=f"{title.lower().replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=False,
    )


if st.session_state.dashboard_section is None:
    logo_left, title_column, logo_right = st.columns([1, 4, 1], vertical_alignment="center")
    with logo_left:
        if BRAND_IMAGE_PATH.is_file():
            st.image(str(BRAND_IMAGE_PATH), width=100)
    with title_column:
        st.markdown('<h1 class="landing-title">SWA Project Status</h1>', unsafe_allow_html=True)
    with logo_right:
        if SWA_IMAGE_PATH.is_file():
            st.image(str(SWA_IMAGE_PATH), width=100)
    with st.container(key="navigation-grid"):
        navigation_rows = [st.columns(4), st.columns(4)]
        for row, row_sections in zip(navigation_rows, (sections[:4], sections[4:])):
            for column, section in zip(row, row_sections):
                with column:
                    if st.button(section, key=f"navigation_{section}", use_container_width=True):
                        st.session_state.dashboard_section = section
                        st.rerun()
    st.stop()

selected_section = st.session_state.dashboard_section
if selected_section != "Team structure":
    st.markdown('<div class="eyebrow">SWA / workforce planning</div>', unsafe_allow_html=True)
    st.title(selected_section)

with st.sidebar:
    if BRAND_IMAGE_PATH.is_file():
        st.image(str(BRAND_IMAGE_PATH), width=90)
    if st.button("Back to dashboard", use_container_width=True, type="secondary"):
        st.session_state.dashboard_section = None
        st.rerun()

if selected_section == "Resource pulse":
    st.markdown('<div class="hero-copy">A clear view of where the workforce is deployed across projects and locations.</div>', unsafe_allow_html=True)
    group_options = {column: column for column in ("Project", "Portfolio", "Wave") if column in base_frame.columns}
    if "Status" in base_frame.columns:
        group_options["OnBoarding Status"] = "Status"
    group_label = st.sidebar.radio("Group by", list(group_options), index=0, key="resource_group")
    top_n = st.sidebar.slider("Chart rows", min_value=5, max_value=30, value=10, step=1)
    with st.sidebar:
        st.divider()
        st.markdown(
            f'<div class="source-pill"><strong>Source sheet</strong><br>Detail1<br><br>'
            f'<strong>Workbook</strong><br>{Path(EXCEL_FILE_PATH).name}</div>',
            unsafe_allow_html=True,
        )
    group_column = group_options[group_label]
    total_resources = build_total_resources(EXCEL_FILE_PATH, group_column)
    onsite_resources = build_location_summary(EXCEL_FILE_PATH, "Onsite", group_column)
    offshore_resources = build_location_summary(EXCEL_FILE_PATH, "Offshore", group_column)
    if "resource_view" not in st.session_state:
        st.session_state.resource_view = "Total Resources"
    button_col1, button_col2, button_col3 = st.columns(3)
    for column, label, count in (
        (button_col1, "Total Resources", summary_metrics["Total Resources"]),
        (button_col2, "Onsite", summary_metrics["Onsite"]),
        (button_col3, "Offshore", summary_metrics["Offshore"]),
    ):
        with column:
            if st.button(f"{label}  |  {count}", key=f"{label.lower().replace(' ', '_')}_button", use_container_width=True, type="primary" if st.session_state.resource_view == label else "secondary"):
                st.session_state.resource_view = label
                st.rerun()
    selected_view = st.session_state.resource_view
    summary, accent = {
        "Total Resources": (total_resources, "#087f8c"),
        "Onsite": (onsite_resources, "#2d8a68"),
        "Offshore": (offshore_resources, "#d96c38"),
    }[selected_view]
    render_summary_chart(selected_view, summary, group_column, accent, "No matching resources were found in Detail1.", top_n)
elif selected_section == "Billability":
    st.markdown('<div class="hero-copy">Current billability distribution from the Detail1 worksheet.</div>', unsafe_allow_html=True)
    with st.sidebar:
        st.divider()
        st.markdown(
            f'<div class="source-pill"><strong>Source sheet</strong><br>Detail1<br><br>'
            f'<strong>Workbook</strong><br>{Path(EXCEL_FILE_PATH).name}</div>',
            unsafe_allow_html=True,
        )
    billability = build_billability_summary(EXCEL_FILE_PATH)
    render_summary_chart("Billability", billability, "Billability", "#087f8c", "No billability data was found in Detail1.")
elif selected_section == "Team structure":
    try:
        render_team_structure(CCC_RESOURCES_FILE_PATH)
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
else:
    if selected_section == "Risks":
        try:
            risk_summary = build_risk_summary(RISK_TRACKER_FILE_PATH)
            risk_details = load_risks(RISK_TRACKER_FILE_PATH)
        except (FileNotFoundError, ValueError) as error:
            st.error(str(error))
        else:
            with st.sidebar:
                st.divider()
                st.markdown(
                    f'<div class="source-pill"><strong>Source sheet</strong><br>Risk Tracker<br><br>'
                    f'<strong>Workbook</strong><br>{Path(RISK_TRACKER_FILE_PATH).name}</div>',
                    unsafe_allow_html=True,
                )

            render_summary_chart(
                "Risks by Portfolio Component",
                risk_summary,
                "Portfolio Component",
                "#d96c38",
                "No risk records were found.",
                top_n=30,
                value_column="Risks",
            )

            status_counts = risk_details["Risk Status"].fillna("Unknown").astype(str).str.strip().value_counts()
            risk_statuses = ("Open", "Inprogress", "Closed")
            if "risk_status" not in st.session_state or st.session_state.risk_status not in risk_statuses:
                st.session_state.risk_status = "Open"

            st.subheader("Risk status")
            status_columns = st.columns(3)
            for column, status in zip(status_columns, risk_statuses):
                count = int(status_counts.get(status, 0))
                with column:
                    if st.button(
                        f"{status}  |  {count}",
                        key=f"risk_status_{status.lower()}",
                        use_container_width=True,
                        type="primary" if st.session_state.risk_status == status else "secondary",
                    ):
                        st.session_state.risk_status = status
                        st.rerun()

            selected_status = st.session_state.risk_status
            selected_risks = risk_details[
                risk_details["Risk Status"].fillna("Unknown").astype(str).str.strip().eq(selected_status)
            ].copy()
            detail_columns = [
                "Risk Owner",
                "Portfolio Component",
                "Risk Core Description",
                "Mitigation Plan",
                "Impact",
                "Severity",
            ]
            detail_columns = [column for column in detail_columns if column in selected_risks.columns]
            st.subheader(f"{selected_status} risks")
            if selected_risks.empty:
                st.info(f"No {selected_status.lower()} risks were found.")
            else:
                st.dataframe(selected_risks[detail_columns], hide_index=True, use_container_width=True)
                st.download_button(
                    f"Download {selected_status.lower()} risks",
                    data=selected_risks[detail_columns].to_csv(index=False).encode("utf-8"),
                    file_name=f"{selected_status.lower()}_risks.csv",
                    mime="text/csv",
                    use_container_width=False,
                )
    else:
        with st.sidebar:
            st.divider()
            st.markdown(
                f'<div class="source-pill"><strong>Source sheet</strong><br>Detail1<br><br>'
                f'<strong>Workbook</strong><br>{Path(EXCEL_FILE_PATH).name}</div>',
                unsafe_allow_html=True,
            )
        st.info(f"{selected_section} is ready for its Detail1 data view.")
