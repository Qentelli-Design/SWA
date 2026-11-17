"""Load billability data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_excel_frame, require_workbook, workbook_token


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

    required = ["Resource Name", "Billable", "Product"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"The workbook must contain the columns: {', '.join(required)}")

    details = frame[required].copy()
    details["Resource Name"] = details["Resource Name"].fillna("").astype(str).str.strip()
    details["Billable"] = details["Billable"].fillna("Unknown").astype(str).str.strip()
    details["Product"] = details["Product"].fillna("").astype(str).str.strip()
    details = details[details["Resource Name"].ne("")].reset_index(drop=True)

    summary = details.groupby("Billable", dropna=False)["Resource Name"].nunique().reset_index(name="Resources")
    summary = summary.rename(columns={"Billable": "Billability"})
    summary = summary.sort_values("Resources", ascending=False).reset_index(drop=True)
    return summary, details
