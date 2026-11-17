"""Portfolio and team delivery activities from the product status workbook."""

from __future__ import annotations

from html import escape
from numbers import Real

import pandas as pd
import streamlit as st

from common.delivery import DELIVERY_DISPLAY_COLUMNS, render_delivery_styles
from common.excel import CACHE_TTL, DATA_ERRORS, read_sheet, require_workbook, workbook_token
from common.styles import dialog_table_height, inject_css
from common.text import display_portfolio_name
from navigation import DELIVERY_VIEW_STATE
from risks import render_risks

SHEETS = ("CCC", "Concourse")
REQUIRED_COLUMNS = (
    "Portfolio", "Team", "Activity / Project", "Progress (Source)",
    "Status (Source)", "Lead Confirms Risk? (Yes/No)",
)
PORTFOLIOS = ("C&C", "C360 and Other Products", "Concourse")
PORTFOLIO_STATE = "delivery_selected_portfolio"


def format_progress(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, Real) and not isinstance(value, bool):
        percentage = value * 100 if 0 <= value <= 1 else value
        return f"{percentage:.12g}%"
    return str(value).strip()


def load_delivery_activities(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    return _load_delivery_activities(*workbook_token(path))


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_delivery_activities(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    sheets = []
    for sheet_name in SHEETS:
        frame = read_sheet(file_path, sheet_name).dropna(how="all")
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError(f"Sheet '{sheet_name}' is missing required columns: {', '.join(missing)}.")
        frame = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
        frame["Progress (Source)"] = frame["Progress (Source)"].map(format_progress)
        for column in REQUIRED_COLUMNS:
            frame[column] = frame[column].fillna("").astype(str).str.strip()
        sheets.append(frame)
    return pd.concat(sheets, ignore_index=True)


def select_portfolio(frame: pd.DataFrame, portfolio: str) -> pd.DataFrame:
    values = frame["Portfolio"].str.casefold()
    if portfolio == PORTFOLIOS[0]:
        return frame.loc[values.eq("ccc")]
    if portfolio == PORTFOLIOS[1]:
        return frame.loc[~values.isin(("ccc", "concourse"))]
    if portfolio == PORTFOLIOS[2]:
        return frame.loc[values.eq("concourse")]
    raise ValueError(f"Unknown portfolio tab: {portfolio}")


def prepare_display(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    for column in REQUIRED_COLUMNS:
        display[column] = display[column].replace("", "Not available")
    display["Portfolio"] = display["Portfolio"].map(display_portfolio_name)
    return display.reset_index(drop=True)


def render_activity_table(frame: pd.DataFrame) -> None:
    display = prepare_display(frame)
    risk_rows = display["Lead Confirms Risk? (Yes/No)"].str.casefold().eq("yes")
    table = display.loc[:, ["Team", "Activity / Project", "Progress (Source)"]].rename(columns=DELIVERY_DISPLAY_COLUMNS)
    styles = pd.DataFrame("", index=table.index, columns=table.columns)
    styles.loc[risk_rows, :] = "background-color: #fbe5e5; color: #a00000"
    st.dataframe(
        table.style.apply(lambda _: styles, axis=None),
        hide_index=True,
        width="stretch",
        height=dialog_table_height(len(table)),
        column_config={
            "Release": st.column_config.TextColumn("Release", width="large"),
        },
    )


@st.dialog("**Release activities**", width="medium")
def show_activity_details(title: str, frame: pd.DataFrame) -> None:
    st.markdown(f"<div class='dialog-product-title'>{escape(title)} - Release Activities</div>",
                unsafe_allow_html=True)
    st.caption("Confirmed risks are highlighted in red.")
    render_activity_table(frame)


def render_portfolio(frame: pd.DataFrame, tab_index: int) -> None:
    if frame.empty:
        st.info("No activities found for this portfolio.")
        return

    display = prepare_display(frame)
    portfolio_keys = frame["Portfolio"].reset_index(drop=True).replace("", "Not available").str.casefold()
    team_keys = display["Team"].str.casefold()
    groups = list(display.groupby([portfolio_keys, team_keys], sort=False))
    for start in range(0, len(groups), 3):
        for offset, (column, (_, activities)) in enumerate(zip(st.columns(3, gap="medium"), groups[start:start + 3])):
            team = activities["Team"].iloc[0]
            risks = int(activities["Lead Confirms Risk? (Yes/No)"].str.casefold().eq("yes").sum())
            with column, st.container(key=f"release-card-delivery-{tab_index}-{start + offset}", border=True):
                st.markdown(f"<div class='delivery-card-title'>{escape(team)}</div>", unsafe_allow_html=True)
                risk_class = "delivery-risk-count" if risks else "delivery-risk-count delivery-risk-none"
                st.markdown(
                    "<div class='delivery-card-summary'>"
                    f"<span class='delivery-summary-count'><strong>{len(activities)}</strong> Releases</span>"
                    f"<span class='delivery-summary-count {risk_class}'><strong>{risks}</strong> Risks</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                if st.button("View details", key=f"delivery_details_{tab_index}_{start + offset}", width="stretch"):
                    show_activity_details(team, activities)


def render_active_releases(file_path: str) -> None:
    with st.container(key="delivery-page"):
        with st.container(key="delivery-header"):
            title_column, view_column, download_column = st.columns([2.4, 1.3, 1.3], vertical_alignment="center")
            with title_column:
                st.markdown("<h1 class='delivery-title'>SWA Product Delivery Health</h1>", unsafe_allow_html=True)
            try:
                activities = load_delivery_activities(file_path)
            except DATA_ERRORS as error:
                st.error(str(error))
                return
            selected = st.session_state.get(PORTFOLIO_STATE, PORTFOLIOS[0])
            if selected == "CCC":
                selected = PORTFOLIOS[0]
                st.session_state[PORTFOLIO_STATE] = selected
            index = PORTFOLIOS.index(selected)
            portfolio_frame = select_portfolio(activities, selected)
            if not portfolio_frame.empty:
                with view_column:
                    if st.button(
                        f"View all releases ({len(portfolio_frame)})",
                        key=f"delivery_view_all_{index}",
                        icon=":material/list_alt:",
                        width="stretch",
                        type="primary",
                    ):
                        show_activity_details(selected, portfolio_frame)
                with download_column:
                    display = prepare_display(portfolio_frame)
                    st.download_button(
                        "Download releases (.csv)",
                        data=display.rename(columns=DELIVERY_DISPLAY_COLUMNS).to_csv(index=False).encode("utf-8"),
                        file_name=f"releases_{index + 1}.csv",
                        mime="text/csv",
                        key=f"delivery_download_{index}",
                        icon=":material/download:",
                        width="stretch",
                        on_click="ignore",
                    )
        st.markdown("<div class='delivery-divider'></div>", unsafe_allow_html=True)
        with st.container(key="delivery-portfolio-navigation"):
            for nav_index, (column, portfolio) in enumerate(zip(st.columns(3, gap="xsmall"), PORTFOLIOS)):
                with column, st.container(key=f"delivery-portfolio-choice-{nav_index}"):
                    st.button(
                        portfolio,
                        key=f"delivery_portfolio_{nav_index}",
                        type="primary" if selected == portfolio else "secondary",
                        width="stretch",
                        on_click=_select_portfolio,
                        args=(portfolio,),
                    )
        st.markdown("<div class='delivery-divider delivery-portfolio-divider'></div>", unsafe_allow_html=True)
        render_portfolio(portfolio_frame, index)


def _select_portfolio(portfolio: str) -> None:
    st.session_state[PORTFOLIO_STATE] = portfolio


def render_project_delivery_status(file_path: str) -> None:
    inject_css("summary_cards.css")
    render_delivery_styles()
    selected = st.session_state.get(DELIVERY_VIEW_STATE)
    if selected in ("Active Releases", "Risks"):
        st.button(
            "Back to Project Delivery Status",
            key="delivery_back",
            on_click=_select_delivery_view,
            args=(None,),
        )
        if selected == "Active Releases":
            render_active_releases(file_path)
        else:
            try:
                render_risks(file_path)
            except DATA_ERRORS as error:
                st.error(str(error))
        return

    with st.container(key="delivery-landing"):
        st.markdown("<h1 class='delivery-title delivery-landing-title'>Project Delivery Status</h1>",
                    unsafe_allow_html=True)
        with st.container(key="delivery-navigation"):
            sections = ("Active Releases", "Risks", "Governance")
            for column, section in zip(st.columns(3), sections):
                with column, st.container(key=f"delivery-nav-{section.lower().replace(' ', '-')}"):
                    st.button(
                        section,
                        key=f"delivery_section_{section}",
                        type="primary" if selected == section else "secondary",
                        width="stretch",
                        on_click=_select_delivery_view,
                        args=(section,),
                    )
    selected = st.session_state.get(DELIVERY_VIEW_STATE)
    if selected == "Governance":
        st.info("Governance details will be added later.")


def _select_delivery_view(section: str | None) -> None:
    st.session_state[DELIVERY_VIEW_STATE] = section
    if section == "Active Releases":
        st.session_state[PORTFOLIO_STATE] = PORTFOLIOS[0]
