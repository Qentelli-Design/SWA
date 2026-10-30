from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_resource_list, require_workbook, workbook_token
from common.styles import inject_css


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
    cleaned["Person Key"] = cleaned["Resource Name"].map(_person_key)
    cleaned["Manager Key"] = cleaned["Reporting Manager"].map(_person_key)
    return cleaned.reset_index(drop=True)


def _person_key(name: str) -> str:
    return " ".join(sorted(name.casefold().split()))


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
    root_key = _person_key(ROOT_NAME)

    def make_node(person_key: str, name: str, product: str, visited: frozenset[tuple[str, str]]) -> dict:
        resource = resource_lookup.get((person_key, product), {"name": name, "product": product})
        node = {
            "key": person_key,
            "name": resource["name"],
            "product": resource["product"],
            "is_manager": person_key in managers,
            "children": [],
        }
        if (person_key, product) in visited:
            return node

        next_visited = visited | {(person_key, product)}
        for report in get_direct_reports(person_key, relationships):
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


def _node_display(node: dict) -> str:
    return f"{node['name']} - {node['product']}" if node["product"] else node["name"]


def _render_resource_card(node: dict) -> None:
    st.markdown(
        f"<div class='org-resource-card'>{escape(_node_display(node))}</div>",
        unsafe_allow_html=True,
    )


def _ordered_children(node: dict) -> list[dict]:
    managers = [child for child in node["children"] if child["children"]]
    individual_contributors = [child for child in node["children"] if not child["children"]]
    return managers + individual_contributors


def _render_reporting_branch(node: dict) -> None:
    if not node["children"]:
        _render_resource_card(node)
        return

    report_count = len(node["children"])
    label = f"{_node_display(node)}  ·  {report_count} reporting resource{'s' if report_count != 1 else ''}"
    with st.expander(label, expanded=False):
        st.markdown("<div class='org-manager-note'>Reporting resources</div>", unsafe_allow_html=True)
        for child in _ordered_children(node):
            _render_reporting_branch(child)


def render_org_chart(hierarchy: dict) -> None:
    st.markdown(
        f"<div class='org-root-card'><div class='org-root-name'>{escape(_node_display(hierarchy))}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='org-branch-label'>Direct reports</div>", unsafe_allow_html=True)
    for child in _ordered_children(hierarchy):
        _render_reporting_branch(child)


def _render_styles() -> None:
    inject_css("org.css")

def render_org_structure(file_path: str) -> None:
    _render_styles()
    frame = clean_data(load_data(file_path))
    hierarchy = build_hierarchy(frame)
    if not hierarchy["children"]:
        st.warning(f"No connected reporting relationships were found below {ROOT_NAME}.")
        return

    st.markdown("<h1 class='org-title'>C&amp;C Organization Structure</h1>", unsafe_allow_html=True)
    st.markdown("<p class='org-subtitle'>Reporting Hierarchy</p>", unsafe_allow_html=True)
    with st.container(border=True):
        render_org_chart(hierarchy)
