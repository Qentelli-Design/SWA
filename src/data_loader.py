"""Load billability and product-status risk data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_excel_frame, require_workbook, sheet_names, workbook_token

_RISK_COLUMNS = ["Product", "Risks", "Mitigation Plan"]


def build_billability_summary(file_path: str, group_by: str = "Billability") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return billability counts and resource-level details from the CCC resources workbook.

    ``group_by`` is kept for caller compatibility. Counts always use the ``Billable`` column.
    """
    del group_by
    path = require_workbook(file_path, "Excel file not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _billability_summary(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _billability_summary(file_path: str, mtime_ns: int, size: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    del mtime_ns, size
    path = Path(file_path)
    try:
        frame = read_excel_frame(path, "Resource List")
    except ValueError:
        frame = read_excel_frame(path, 0)

    required = ["Resource Name", "Billable"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"The workbook must contain the columns: {', '.join(required)}")

    details = frame[required].copy()
    details["Resource Name"] = details["Resource Name"].fillna("").astype(str).str.strip()
    details["Billable"] = details["Billable"].fillna("Unknown").astype(str).str.strip()
    details = details[details["Resource Name"].ne("")].reset_index(drop=True)

    summary = details.groupby("Billable", dropna=False)["Resource Name"].nunique().reset_index(name="Resources")
    summary = summary.rename(columns={"Billable": "Billability"})
    summary = summary.sort_values("Resources", ascending=False).reset_index(drop=True)
    return summary, details


def load_risks_from_product_status(file_path: str) -> pd.DataFrame:
    """Extract non-empty Risks and Mitigation Plan entries from each product sheet.

    Reads every sheet in the product status workbook. Looks for a column named ``Risks``
    (preferred), otherwise uses column L (0-based index 11). Mitigation Plan uses that
    header or column M (index 12). Rows with empty Risks are excluded.
    """
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_risks(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_risks(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    rows: list[pd.DataFrame] = []
    for sheet_name in sheet_names(file_path):
        extracted = _risks_from_sheet(file_path, sheet_name)
        if extracted is not None:
            rows.append(extracted)
    if not rows:
        return pd.DataFrame(columns=_RISK_COLUMNS)
    return pd.concat(rows, ignore_index=True)


def _column_by_name_or_index(frame: pd.DataFrame, name: str, index: int) -> str | None:
    if name in frame.columns:
        return name
    if len(frame.columns) > index:
        return str(frame.columns[index])
    return None


def _risks_from_sheet(file_path: str, sheet_name: str) -> pd.DataFrame | None:
    frame = read_excel_frame(Path(file_path), sheet_name)
    risks_col = _column_by_name_or_index(frame, "Risks", 11)
    if risks_col is None:
        return None

    mitigation_col = _column_by_name_or_index(frame, "Mitigation Plan", 12)
    columns = [risks_col, mitigation_col] if mitigation_col else [risks_col]
    subset = frame[columns].dropna(how="all").copy()
    subset[risks_col] = subset[risks_col].fillna("").astype(str).str.strip()
    if mitigation_col:
        subset[mitigation_col] = subset[mitigation_col].fillna("").astype(str).str.strip()

    subset = subset[subset[risks_col].ne("")].copy()
    if subset.empty:
        return None

    subset["Product"] = sheet_name
    if mitigation_col:
        subset = subset.rename(columns={risks_col: "Risks", mitigation_col: "Mitigation Plan"})
    else:
        subset = subset.rename(columns={risks_col: "Risks"})
        subset["Mitigation Plan"] = ""
    return subset[_RISK_COLUMNS]


def build_risk_summary_from_product_status(file_path: str) -> pd.DataFrame:
    details = load_risks_from_product_status(file_path)
    if details.empty:
        return pd.DataFrame(columns=["Product", "Risks"])
    summary = details.groupby("Product", dropna=False).size().reset_index(name="Risks")
    return summary.sort_values("Risks", ascending=False).reset_index(drop=True)
