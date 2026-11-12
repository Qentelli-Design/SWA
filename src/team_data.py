"""Team structure data: loading, classification, and derived figures. No UI code."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_resource_list, require_workbook, workbook_token
from common.text import person_key

REQUIRED_COLUMNS = [
    "Portfolio",
    "Product",
    "Resource Name",
    "Location",
    "Role",
    "Vendor",
    "Reporting Manager",
]
DETAIL_COLUMNS = ["Qentelli ID", "Qentelli Mail ID", "Qentelli DOJ", "Qentelli Designation"]
CONSULTANT_DESIGNATION = "q consultant"
PRIMARY_PORTFOLIO = "CCC"
CONCOURSE_PORTFOLIO = "Concourse"
PORTFOLIO_GROUPS = ("C&C", "Concourse", "C360 and Other Products")
LEADERSHIP_ROOT = "Siva Rao Kompella S V"
LEADERSHIP_DISPLAY_ORDER = [
    "B Ramesh",
    "Madhav Patibandla",
    "Swetha Gundimeda",
    "Kanti Yalavarthy",
]
LEADERSHIP_DISPLAY_NAMES = {
    person_key("Gundimeda Swetha"): "Swetha Gundimeda",
    person_key("Yalavarthy Kanti Krishna"): "Kanti Yalavarthy",
}


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


def get_portfolio_team(frame: pd.DataFrame, group: str) -> pd.DataFrame:
    """Return non-governance resource rows belonging to the selected portfolio group."""
    team = get_product_team(frame)
    portfolios = team["Portfolio"].str.strip().str.casefold()
    primary = portfolios.eq(PRIMARY_PORTFOLIO.casefold())
    concourse = portfolios.eq(CONCOURSE_PORTFOLIO.casefold())
    if group == PORTFOLIO_GROUPS[0]:
        mask = primary
    elif group == PORTFOLIO_GROUPS[1]:
        mask = concourse
    elif group == PORTFOLIO_GROUPS[2]:
        mask = ~(primary | concourse)
    else:
        raise ValueError(f"Unknown portfolio group: {group}")
    return team[mask].copy()


def get_products(frame: pd.DataFrame) -> list[str]:
    products = frame.loc[frame["Product"].ne(""), "Product"].unique()
    return sorted(products.tolist(), key=str.casefold)


def get_leadership_hierarchy(governance: pd.DataFrame) -> dict:
    """Build the C&C leadership tree from governance members' reporting managers."""
    names: dict[str, str] = {}
    reports: dict[str, list[str]] = {}
    for _, row in governance.iterrows():
        name = row["Resource Name"]
        manager = row["Reporting Manager"]
        person = person_key(name)
        manager_key = person_key(manager)
        if not person or not manager_key:
            continue
        names.setdefault(person, LEADERSHIP_DISPLAY_NAMES.get(person, name))
        reports.setdefault(manager_key, [])
        if person not in reports[manager_key]:
            reports[manager_key].append(person)

    display_order = {person_key(name): index for index, name in enumerate(LEADERSHIP_DISPLAY_ORDER)}

    def build_node(key: str, name: str, visited: frozenset[str]) -> dict:
        children = sorted(
            reports.get(key, []),
            key=lambda child: (display_order.get(child, len(display_order)), names[child].casefold()),
        )
        return {
            "name": name,
            "children": [
                build_node(child, names[child], visited | {key})
                for child in children
                if child not in visited and child != key
            ],
        }

    root_key = person_key(LEADERSHIP_ROOT)
    return build_node(root_key, LEADERSHIP_ROOT, frozenset({root_key}))


def build_team_metrics(frame: pd.DataFrame) -> list[tuple[str, int]]:
    """Headline counts for the summary tiles. ``frame`` holds everyone, governance included."""
    governance = get_governance_members(frame)
    product_team = get_product_team(frame)
    onsite = product_team[product_team["Location Normalized"].eq("Onsite")]
    offshore = product_team[product_team["Location Normalized"].eq("Offshore")]
    return [
        ("Total team", len(product_team) + len(governance)),
        ("Onsite", len(onsite)),
        ("Offshore", len(offshore)),
        ("Governance", len(governance)),
        ("Onsite leads", int(onsite["Role"].str.casefold().str.contains("lead onsite").sum())),
        ("Offshore leads", int(offshore["Role"].str.casefold().str.contains("lead offshore").sum())),
        ("Q Consultants", int(product_team["Is Consultant"].sum())),
    ]


def count_by_location(product_frame: pd.DataFrame) -> tuple[int, int]:
    """Return (onsite, offshore) resource counts."""
    return (
        int(product_frame["Location Normalized"].eq("Onsite").sum()),
        int(product_frame["Location Normalized"].eq("Offshore").sum()),
    )
