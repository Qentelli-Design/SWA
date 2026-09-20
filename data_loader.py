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
def load_risks_from_product_status(file_path: str) -> pd.DataFrame:
    """Extract non-empty Risks and Mitigation Plan entries from each product sheet.

    Reads every sheet in the Product_Status_Report workbook. Looks for a column named 'Risks' (preferred),
    otherwise uses column L (0-based index 11). For Mitigation Plan uses 'Mitigation Plan' or column M (index 12).
    Returns a DataFrame with columns: Product, Risks, Mitigation Plan. Rows with empty Risks are excluded.
    """
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Product status workbook not found: {path}")

    workbook = pd.ExcelFile(path, engine="openpyxl")
    rows = []
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        frame.columns = [str(c).strip() for c in frame.columns]

        # determine risks column
        if "Risks" in frame.columns:
            risks_col = "Risks"
        elif len(frame.columns) >= 12:
            risks_col = frame.columns[11]
        else:
            continue

        # determine mitigation column
        if "Mitigation Plan" in frame.columns:
            mit_col = "Mitigation Plan"
        elif len(frame.columns) >= 13:
            mit_col = frame.columns[12]
        else:
            mit_col = None

        sub = frame[[risks_col]].copy()
        if mit_col:
            sub[mit_col] = frame[mit_col].copy()

        sub = sub.dropna(how="all").copy()
        sub[risks_col] = sub[risks_col].fillna("").astype(str).str.strip()
        if mit_col:
            sub[mit_col] = sub[mit_col].fillna("").astype(str).str.strip()

        sub = sub[sub[risks_col].ne("")].copy()
        if sub.empty:
            continue

        sub["Product"] = sheet_name
        # normalize column names
        if mit_col:
            sub = sub.rename(columns={risks_col: "Risks", mit_col: "Mitigation Plan"})
        else:
            sub = sub.rename(columns={risks_col: "Risks"})
            sub["Mitigation Plan"] = ""

        rows.append(sub[["Product", "Risks", "Mitigation Plan"]])

    if not rows:
        return pd.DataFrame(columns=["Product", "Risks", "Mitigation Plan"])
    details = pd.concat(rows, ignore_index=True)
    return details


@st.cache_data(show_spinner=False)
def build_risk_summary_from_product_status(file_path: str) -> pd.DataFrame:
    details = load_risks_from_product_status(file_path)
    if details.empty:
        return pd.DataFrame(columns=["Product", "Risks"]) 
    summary = details.groupby("Product", dropna=False).size().reset_index(name="Risks")
    return summary.sort_values("Risks", ascending=False).reset_index(drop=True)



