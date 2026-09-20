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
def build_billability_summary(file_path: str, group_by: str = "Billability") -> tuple[pd.DataFrame, pd.DataFrame]:
    # Billability is sourced from the CCC resources workbook 'Resource List' sheet
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")

    try:
        df = pd.read_excel(path, sheet_name="Resource List", engine="openpyxl")
    except ValueError:
        # fallback to first sheet
        df = pd.read_excel(path, engine="openpyxl")

    df.columns = [str(column).strip() for column in df.columns]
    required = ["Resource Name", "Billable"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"The workbook must contain the columns: {', '.join(required)}")

    details = df[required].copy()
    details["Resource Name"] = details["Resource Name"].fillna("").astype(str).str.strip()
    details["Billable"] = details["Billable"].fillna("Unknown").astype(str).str.strip()
    details = details[details["Resource Name"].ne("")].reset_index(drop=True)

    # Count unique resource names per billability value
    summary = (
        details.groupby("Billable", dropna=False)["Resource Name"].nunique().reset_index(name="Resources")
    )
    summary.rename(columns={"Billable": "Billability"}, inplace=True)
    summary = summary.sort_values("Resources", ascending=False).reset_index(drop=True)

    # Return both aggregated summary and resource-level details for downloads
    return summary, details


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



