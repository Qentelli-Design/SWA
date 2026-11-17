"""Lead-confirmed risks from the current product status workbook."""

from __future__ import annotations

from datetime import date, datetime
import pandas as pd
import streamlit as st

from common.charts import render_summary_chart
from common.delivery import DELIVERY_DISPLAY_COLUMNS
from common.excel import CACHE_TTL, DATA_ERRORS, read_sheet, require_workbook, workbook_token
from common.styles import dialog_table_height, inject_css
from common.text import display_portfolio_name

RISK_COLUMNS = (
    "Portfolio", "Team", "Activity / Project", "Lead Confirms Risk? (Yes/No)",
    "Risk / Challenge Description", "Risk Severity", "Mitigation Plan /Next Action",
    "Risk Identified Date", "Date Reported to SWA", "Target Closure Date",
)
DATE_COLUMNS = ("Risk Identified Date", "Date Reported to SWA", "Target Closure Date")
CHALLENGE_COLUMN = "Other Challenges / Dependencies /Environment issues/ Resource availablity etc"
WORKAROUND_COLUMN = "Mitigation Plan / Workaround"
CHALLENGE_COLUMNS = (
    "Portfolio", "Team", "Activity / Project", "Lead Confirms Risk? (Yes/No)",
    CHALLENGE_COLUMN, WORKAROUND_COLUMN,
)


def _load_confirmed_rows(file_path: str, columns: tuple[str, ...]) -> pd.DataFrame:
    sheets = []
    for sheet_name in ("CCC", "Concourse"):
        frame = read_sheet(file_path, sheet_name).dropna(how="all")
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"Sheet '{sheet_name}' is missing required columns: {', '.join(missing)}.")
        frame = frame.loc[:, list(columns)].copy()
        confirmed = frame["Lead Confirms Risk? (Yes/No)"].fillna("").astype(str).str.strip().str.casefold()
        sheets.append(frame.loc[confirmed.eq("yes")])
    return pd.concat(sheets, ignore_index=True)


def load_confirmed_risks(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    return _cached_confirmed_risks(*workbook_token(path))


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _cached_confirmed_risks(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    frame = _load_confirmed_rows(file_path, RISK_COLUMNS + (CHALLENGE_COLUMN, WORKAROUND_COLUMN))
    return frame.loc[~_has_challenge(frame), list(RISK_COLUMNS)].reset_index(drop=True)


def _has_challenge(frame: pd.DataFrame) -> pd.Series:
    populated = frame.loc[:, [CHALLENGE_COLUMN, WORKAROUND_COLUMN]].fillna("").astype(str)
    return populated.apply(lambda column: column.str.strip().ne("")).any(axis=1)


def load_other_challenges(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    return _cached_other_challenges(*workbook_token(path))


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _cached_other_challenges(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    frame = _load_confirmed_rows(file_path, CHALLENGE_COLUMNS)
    return frame.loc[_has_challenge(frame)].reset_index(drop=True)


def _text(value: object) -> str:
    if pd.isna(value) or not str(value).strip():
        return "Not provided"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d %b %Y")
    return str(value).strip()


def _prepare_export(details: pd.DataFrame) -> pd.DataFrame:
    export = details.copy()
    export["Portfolio"] = export["Portfolio"].map(
        lambda value: display_portfolio_name(value) if isinstance(value, str) else value
    )
    return export.rename(columns=DELIVERY_DISPLAY_COLUMNS)


def _render_summary_tiles(tiles: tuple[tuple[int, str], ...]) -> None:
    st.markdown(
        "<div class='rk-tiles'>" + "".join(
            f"<div class='rk-tile'><div class='rk-tile-value'>{value}</div>"
            f"<div class='rk-tile-label'>{label}</div></div>" for value, label in tiles
        ) + "</div>",
        unsafe_allow_html=True,
    )


def _render_confirmed_risks(file_path: str) -> None:
    details = load_confirmed_risks(file_path)
    if details.empty:
        st.info("No lead-confirmed risks found.")
        return

    teams = details["Team"].map(_text)
    plans = details["Mitigation Plan /Next Action"].fillna("").astype(str).str.strip().ne("")
    affected = int(teams[teams.ne("Not provided")].str.casefold().nunique())
    _render_summary_tiles((
        (len(details), "Total risks"), (int(plans.sum()), "With mitigation"),
        (affected, "Teams affected"), (int((~plans).sum()), "No mitigation yet"),
    ))
    team = _render_team_chart(teams, "Risks", "risks")
    if team is not None:
        _show_risk_details(team, details.loc[teams.eq(team)])
    export = _prepare_export(details)
    for column in DATE_COLUMNS:
        export[column] = export[column].map(_text)
    st.download_button("Download risks (CSV)", data=export.to_csv(index=False).encode("utf-8"),
                       file_name="risks.csv", mime="text/csv", width="content", on_click="ignore")


def _select_risk_view(view: str) -> None:
    st.session_state["delivery_risk_view"] = view
    _reset_chart_selection()


def _reset_chart_selection() -> None:
    st.session_state["delivery_chart_generation"] = st.session_state.get("delivery_chart_generation", 0) + 1


def _chart_key(view: str) -> str:
    return f"delivery_{view}_chart_{st.session_state.get('delivery_chart_generation', 0)}"


def _render_team_chart(teams: pd.Series, label: str, view: str) -> str | None:
    summary = teams.value_counts().rename_axis("Team").reset_index(name=label)
    with st.container(key="risk-team-breakdown"):
        st.markdown(f"<div class='rk-section'>{label} by team</div>", unsafe_allow_html=True)
        st.caption(f"Select a team bar to see its {view}.")
        return render_summary_chart(
            f"{label} by team", summary, "Team", "#1f4e79", f"No {view} found.",
            top_n=len(summary), value_column=label, show_heading=False, corporate=True,
            selection_key=_chart_key(view), compact=True,
        )


@st.dialog("**Risk details**", width="medium", on_dismiss=_reset_chart_selection)
def _show_risk_details(team: str, details: pd.DataFrame) -> None:
    st.subheader(team)
    columns = ["Team", "Activity / Project", "Risk / Challenge Description",
               "Risk Severity", "Mitigation Plan /Next Action"]
    display = details.loc[:, columns].copy().map(_text)
    display = display.rename(columns={**DELIVERY_DISPLAY_COLUMNS, "Mitigation Plan /Next Action": "Mitigation Plan / Next Action"})
    st.dataframe(display, hide_index=True, width="stretch", height=dialog_table_height(len(display)))


@st.dialog("**Other Challenges**", width="medium", on_dismiss=_reset_chart_selection)
def _show_challenge_details(team: str, details: pd.DataFrame) -> None:
    st.subheader(team)
    display = details.loc[:, ["Team", CHALLENGE_COLUMN, WORKAROUND_COLUMN]].copy().map(_text)
    display = display.rename(columns={**DELIVERY_DISPLAY_COLUMNS, CHALLENGE_COLUMN: "Challenge"})
    st.dataframe(display, hide_index=True, width="stretch", height=dialog_table_height(len(display)))


def _render_other_challenges(file_path: str) -> None:
    details = load_other_challenges(file_path)
    teams = details["Team"].map(_text)
    plans = details[WORKAROUND_COLUMN].fillna("").astype(str).str.strip().ne("")
    affected = int(teams[teams.ne("Not provided")].str.casefold().nunique())
    _render_summary_tiles((
        (len(details), "Total challenges"),
        (int(plans.sum()), "With mitigation"),
        (affected, "Teams affected"),
    ))
    if details.empty:
        st.info("No lead-confirmed challenges or workarounds found.")
        return
    team = _render_team_chart(teams, "Challenges", "challenges")
    if team is not None:
        _show_challenge_details(team, details.loc[teams.eq(team)])
    export = _prepare_export(details)
    st.download_button("Download challenges (CSV)", data=export.to_csv(index=False).encode("utf-8"),
                       file_name="other_challenges.csv", mime="text/csv", width="content", on_click="ignore")


def render_risks(file_path: str) -> None:
    inject_css("risks.css")
    st.markdown("<h1 class='delivery-title'>Risks</h1>", unsafe_allow_html=True)
    selected = st.session_state.get("delivery_risk_view", "Risks")
    with st.container(key="delivery-risk-navigation"):
        for column, view in zip(st.columns(2), ("Risks", "Other Challenges")):
            with column:
                st.button(
                    view,
                    key=f"delivery_risk_section_{view}",
                    type="primary" if selected == view else "secondary",
                    width="stretch",
                    on_click=_select_risk_view,
                    args=(view,),
                )
    try:
        if selected == "Other Challenges":
            _render_other_challenges(file_path)
        else:
            _render_confirmed_risks(file_path)
    except DATA_ERRORS as error:
        st.error(str(error))
