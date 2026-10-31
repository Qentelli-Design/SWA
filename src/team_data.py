"""Team structure data: loading, classification, and derived figures. No UI code."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_resource_list, require_workbook, workbook_token
from common.text import person_key

REQUIRED_COLUMNS = ["Portfolio", "Product", "Resource Name", "Location", "Role", "Vendor"]
DETAIL_COLUMNS = ["Qentelli ID", "Qentelli Mail ID", "Qentelli DOJ", "Qentelli Designation"]
CONSULTANT_DESIGNATION = "consultant"
PRIMARY_PORTFOLIO = "CCC"
LEADERSHIP_DISPLAY_ORDER = [
    "Siva Rao Kompella S V",
    "B Ramesh",
    "Swetha Gundimeda",
    "Kanti Yalavarthy",
]
STATIC_LEADERSHIP_NAMES = {"Siva Rao Kompella S V", "Kanti Yalavarthy"}


def load_data(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Excel file not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_team_data(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_team_data(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    frame = read_resource_list(file_path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"The 'Resource List' sheet is missing: {', '.join(missing_columns)}")

    for column in DETAIL_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["Qentelli DOJ"] = pd.to_datetime(frame["Qentelli DOJ"], errors="coerce").dt.strftime("%d %b %Y")
    frame = frame[REQUIRED_COLUMNS + DETAIL_COLUMNS].dropna(how="all").copy()
    for column in REQUIRED_COLUMNS + DETAIL_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    frame["Location Normalized"] = frame["Location"].map(_normalize_location)
    frame["Is Consultant"] = frame["Qentelli Designation"].str.casefold().eq(CONSULTANT_DESIGNATION)
    return frame.reset_index(drop=True)


def _normalize_location(value: str) -> str:
    normalized = value.casefold().replace(" ", "")
    if "offshore" in normalized:
        return "Offshore"
    if "onsite" in normalized or "office" in normalized:
        return "Onsite"
    return "Other"


def governance_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["Role"].str.casefold().str.startswith("gover", na=False)


def get_governance_members(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[governance_mask(frame)].copy()


def get_product_team(frame: pd.DataFrame) -> pd.DataFrame:
    """Everyone who is not a governance member."""
    return frame[~governance_mask(frame)].copy()


def get_products_by_portfolio(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    product_frame = frame[
        (~governance_mask(frame)) & frame["Product"].ne("")
    ].drop_duplicates("Product")
    primary_products = product_frame.loc[product_frame["Portfolio"].eq(PRIMARY_PORTFOLIO), "Product"]
    other_products = product_frame.loc[~product_frame["Portfolio"].eq(PRIMARY_PORTFOLIO), "Product"]
    return (
        sorted(primary_products.tolist(), key=str.casefold),
        sorted(other_products.tolist(), key=str.casefold),
    )


def get_leadership_names(governance: pd.DataFrame) -> list[str]:
    """Leaders to display, in reporting order: fixed leaders plus those present as governance rows."""
    governance_names = {person_key(name) for name in governance["Resource Name"]}
    return [
        name
        for name in LEADERSHIP_DISPLAY_ORDER
        if name in STATIC_LEADERSHIP_NAMES or person_key(name) in governance_names
    ]


def build_team_metrics(product_frame: pd.DataFrame) -> list[tuple[str, int]]:
    """Headline counts for the summary tiles."""
    product_team = get_product_team(product_frame)
    onsite = product_team[product_team["Location Normalized"].eq("Onsite")]
    offshore = product_team[product_team["Location Normalized"].eq("Offshore")]
    return [
        ("Total team", len(product_team)),
        ("Onsite", len(onsite)),
        ("Offshore", len(offshore)),
        ("Onsite leads", int(onsite["Role"].str.casefold().str.contains("lead onsite").sum())),
        ("Offshore leads", int(offshore["Role"].str.casefold().str.contains("lead offshore").sum())),
        ("Consultants", int(product_team["Is Consultant"].sum())),
    ]


def count_by_location(product_frame: pd.DataFrame) -> tuple[int, int]:
    """Return (onsite, offshore) resource counts."""
    return (
        int(product_frame["Location Normalized"].eq("Onsite").sum()),
        int(product_frame["Location Normalized"].eq("Offshore").sum()),
    )
