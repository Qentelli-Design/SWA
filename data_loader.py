from pathlib import Path

import pandas as pd
import streamlit as st


def _normalize_location(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    text = str(value).strip().lower()
    if not text:
        return "Unknown"
    if "offshore" in text:
        return "Offshore"
    if "onsite" in text or "on site" in text or "office" in text:
        return "Onsite"
    if "remote" in text:
        return "Remote"
    return "Other"


def _guess_group_column(frame: pd.DataFrame) -> str:
    for candidate in ("Project", "Portfolio", "Wave"):
        if candidate in frame.columns:
            return candidate
    return frame.columns[0] if len(frame.columns) else "Project"


@st.cache_data(show_spinner=False)
def load_detail1(file_path: str) -> pd.DataFrame:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")

    raw = pd.read_excel(path, sheet_name="Detail1", header=None, engine="openpyxl")

    header_row = raw[raw.apply(lambda row: row.astype(str).str.strip().eq("S.No").any(), axis=1)]
    if header_row.empty:
        raise ValueError("The 'Detail1' sheet does not contain the expected header row.")

    header_index = int(header_row.index[0])
    table = raw.iloc[header_index + 1 :, :].copy()
    table.columns = raw.iloc[header_index, : table.shape[1]].tolist()

    table = table.dropna(how="all").copy()
    table.columns = [str(column).strip() for column in table.columns]

    if "Location" in table.columns:
        table["Location Normalized"] = table["Location"].map(_normalize_location)
    else:
        table["Location Normalized"] = "Unknown"

    if "Project" not in table.columns and "Portfolio" in table.columns:
        table["Project"] = table["Portfolio"]

    return table.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def build_total_resources(file_path: str, group_by: str = "Project") -> pd.DataFrame:
    frame = load_detail1(file_path)
    group_col = group_by if group_by in frame.columns else _guess_group_column(frame)

    filtered = frame[frame["Location Normalized"].isin(["Offshore", "Onsite"])].copy()
    if filtered.empty:
        return pd.DataFrame(columns=[group_col, "Resources"])

    summary = filtered.groupby(group_col, dropna=False).size().reset_index(name="Resources")
    return summary.sort_values("Resources", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def build_location_summary(file_path: str, location_name: str, group_by: str = "Project") -> pd.DataFrame:
    frame = load_detail1(file_path)
    group_col = group_by if group_by in frame.columns else _guess_group_column(frame)

    filtered = frame[frame["Location Normalized"].eq(location_name)].copy()
    if filtered.empty:
        return pd.DataFrame(columns=[group_col, "Resources"])

    summary = filtered.groupby(group_col, dropna=False).size().reset_index(name="Resources")
    return summary.sort_values("Resources", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def build_billability_summary(file_path: str, group_by: str = "Billability") -> pd.DataFrame:
    frame = load_detail1(file_path)
    group_col = group_by if group_by in frame.columns else "Billability"
    if group_col not in frame.columns:
        return pd.DataFrame(columns=["Billability", "Resources"])

    filtered = frame[frame["Location Normalized"].isin(["Offshore", "Onsite"])].copy()
    if filtered.empty:
        return pd.DataFrame(columns=[group_col, "Resources"])

    filtered[group_col] = filtered[group_col].fillna("Unknown").astype(str).str.strip()
    summary = filtered.groupby(group_col, dropna=False).size().reset_index(name="Resources")
    return summary.sort_values("Resources", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_risks(file_path: str, sheet_name: str = "Risk Tracker") -> pd.DataFrame:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")

    try:
        risks = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    except ValueError as error:
        raise ValueError(f"The workbook does not contain a sheet named '{sheet_name}'.") from error

    risks = risks.dropna(how="all").copy()
    risks.columns = [str(column).strip() for column in risks.columns]
    if "Portfolio Component" not in risks.columns:
        raise ValueError(f"The '{sheet_name}' sheet must contain a 'Portfolio Component' column.")
    risks["Portfolio Component"] = risks["Portfolio Component"].fillna("Unknown").astype(str).str.strip()
    return risks.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def build_risk_summary(file_path: str) -> pd.DataFrame:
    risks = load_risks(file_path)
    summary = risks.groupby("Portfolio Component", dropna=False).size().reset_index(name="Risks")
    return summary.sort_values("Risks", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def get_dashboard_summary(file_path: str) -> dict[str, int]:
    frame = load_detail1(file_path)
    location_counts = frame["Location Normalized"].value_counts(dropna=False)
    total = int(location_counts.get("Offshore", 0) + location_counts.get("Onsite", 0))
    return {
        "Total Resources": total,
        "Offshore": int(location_counts.get("Offshore", 0)),
        "Onsite": int(location_counts.get("Onsite", 0)),
    }
