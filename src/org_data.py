"""Organization structure data: loading and the reporting hierarchy. No UI code."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_resource_list, require_workbook, workbook_token
from common.text import person_key

ROOT_NAME = "Siva Rao Kompella S V"
REQUIRED_COLUMNS = [
    "Portfolio",
    "Product",
    "Resource Name",
    "Location",
    "Role",
    "Vendor",
    "Reporting Manager",
]


def load_data(file_path: str) -> pd.DataFrame:
    path = require_workbook(file_path, "Excel file not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_org_data(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_org_data(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    frame = read_resource_list(file_path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"The 'Resource List' sheet is missing: {', '.join(missing_columns)}")

    frame = frame[REQUIRED_COLUMNS].copy()
    for column in REQUIRED_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    return frame.dropna(how="all").reset_index(drop=True)


def clean_data(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned = cleaned[
        cleaned["Resource Name"].ne("")
        & cleaned["Reporting Manager"].ne("")
        & ~cleaned["Vendor"].str.casefold().eq("rebadge")
    ].copy()
    cleaned = cleaned.drop_duplicates(subset=["Resource Name", "Product", "Reporting Manager"]).copy()
    cleaned["Person Key"] = cleaned["Resource Name"].map(person_key)
    cleaned["Manager Key"] = cleaned["Reporting Manager"].map(person_key)
    return cleaned.reset_index(drop=True)


def build_reporting_relationships(frame: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    relationships: dict[str, list[dict[str, str]]] = {}
    for _, row in frame.iterrows():
        relationships.setdefault(row["Manager Key"], []).append(
            {
                "person_key": row["Person Key"],
                "name": row["Resource Name"],
                "product": row["Product"],
            }
        )
    return relationships


def get_direct_reports(
    manager_key: str,
    relationships: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    unique_reports = {}
    for report in relationships.get(manager_key, []):
        unique_key = (report["person_key"], report.get("product", ""))
        unique_reports.setdefault(unique_key, report)
    return list(unique_reports.values())


def identify_managers(relationships: dict[str, list[dict[str, str]]]) -> set[str]:
    return {manager_key for manager_key, reports in relationships.items() if reports}


def _resource_lookup(frame: pd.DataFrame) -> dict[str, dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for _, row in frame.iterrows():
        key = (row["Person Key"], row["Product"])
        lookup.setdefault(key, {"name": row["Resource Name"], "product": row["Product"]})
    return lookup


def build_hierarchy(frame: pd.DataFrame) -> dict:
    relationships = build_reporting_relationships(frame)
    managers = identify_managers(relationships)
    resource_lookup = _resource_lookup(frame)
    root_key = person_key(ROOT_NAME)

    def make_node(key: str, name: str, product: str, visited: frozenset[tuple[str, str]]) -> dict:
        resource = resource_lookup.get((key, product), {"name": name, "product": product})
        node = {
            "key": key,
            "name": resource["name"],
            "product": resource["product"],
            "is_manager": key in managers,
            "children": [],
        }
        if (key, product) in visited:
            return node

        next_visited = visited | {(key, product)}
        for report in get_direct_reports(key, relationships):
            report_key = (report["person_key"], report.get("product", ""))
            if report_key not in next_visited:
                node["children"].append(
                    make_node(
                        report["person_key"],
                        report["name"],
                        report["product"],
                        next_visited,
                    )
                )
        return node

    return make_node(root_key, ROOT_NAME, "", frozenset())


def unconnected_relationships(frame: pd.DataFrame, hierarchy: dict) -> pd.DataFrame:
    """Find reporting relationships not rendered in the root leader's tree."""
    represented: set[tuple[str, str, str]] = set()

    def collect(node: dict) -> None:
        for child in node["children"]:
            represented.add((node["key"], child["key"], child["product"]))
            collect(child)

    collect(hierarchy)
    missing = [
        (row["Manager Key"], row["Person Key"], row["Product"]) not in represented
        for _, row in frame.iterrows()
    ]
    return frame.loc[missing].drop_duplicates(subset=["Manager Key", "Person Key", "Product"]).copy()


def unassigned_resources(frame: pd.DataFrame) -> pd.DataFrame:
    """Find resources without a reporting manager, excluding the root and rebadges."""
    names = frame["Resource Name"]
    missing = (
        names.ne("")
        & frame["Reporting Manager"].eq("")
        & ~frame["Vendor"].str.casefold().eq("rebadge")
        & names.map(person_key).ne(person_key(ROOT_NAME))
    )
    return frame.loc[missing].drop_duplicates(subset=["Resource Name", "Product"]).copy()
