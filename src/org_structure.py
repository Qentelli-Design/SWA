"""Organization structure page: an expandable reporting tree below the root leader."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.styles import inject_css
from org_data import (
    ROOT_NAME,
    build_hierarchy,
    clean_data,
    load_data,
    unassigned_resources,
    unconnected_relationships,
)

_MAX_ACCENT_DEPTH = 4


def _node_display(node: dict) -> str:
    return f"{node['name']} - {node['product']}" if node["product"] else node["name"]


def _ordered_children(node: dict) -> list[dict]:
    managers = [child for child in node["children"] if child["children"]]
    individual_contributors = [child for child in node["children"] if not child["children"]]
    return managers + individual_contributors


def _count_below(node: dict) -> int:
    return sum(1 + _count_below(child) for child in node["children"])


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _label_html(node: dict) -> str:
    product = f"<span class='org-product'>{escape(node['product'])}</span>" if node["product"] else ""
    return f"<span class='org-name'>{escape(node['name'])}</span>{product}"


def _node_html(node: dict, depth: int) -> str:
    """One tree row. People with reports are collapsible <details>; others are plain cards."""
    accent = f"org-depth-{min(depth, _MAX_ACCENT_DEPTH)}"
    label = _label_html(node)
    children = _ordered_children(node)
    if not children:
        return f"<li class='org-item'><div class='org-card org-leaf {accent}'>{label}</div></li>"

    direct = len(children)
    total = _count_below(node)
    badges = f"<span class='org-count'>{_plural(direct, 'report')}</span>"
    if total != direct:
        badges += f"<span class='org-total'>{total} in team</span>"
    branches = "".join(_node_html(child, depth + 1) for child in children)
    return (
        "<li class='org-item'><details class='org-branch'>"
        f"<summary class='org-card org-manager {accent}'>"
        f"<span class='org-chevron' aria-hidden='true'></span>{label}"
        f"<span class='org-badges'>{badges}</span></summary>"
        f"<ul class='org-list'>{branches}</ul></details></li>"
    )


def _root_html(hierarchy: dict) -> str:
    direct = len(hierarchy["children"])
    total = _count_below(hierarchy)
    return (
        "<div class='org-root'>"
        f"<div class='org-root-name'>{escape(_node_display(hierarchy))}</div>"
        f"<div class='org-root-stats'><span>{_plural(direct, 'direct report')}</span>"
        f"<span>{total} in organization</span></div>"
        "<div class='org-root-hint'>Click a name to expand their reporting team.</div></div>"
    )


def render_org_chart(hierarchy: dict) -> None:
    branches = "".join(_node_html(child, 1) for child in _ordered_children(hierarchy))
    st.markdown(
        f"<div class='org-tree'>{_root_html(hierarchy)}<ul class='org-list org-list-root'>{branches}</ul></div>",
        unsafe_allow_html=True,
    )


def render_unconnected_relationships(frame: pd.DataFrame) -> None:
    groups: dict[str, dict] = {}
    for _, row in frame.iterrows():
        group = groups.setdefault(
            row["Manager Key"],
            {"key": row["Manager Key"], "name": row["Reporting Manager"], "product": "", "children": []},
        )
        group["children"].append(
            {"key": row["Person Key"], "name": row["Resource Name"], "product": row["Product"], "children": []}
        )
    branches = "".join(
        _node_html(group, 1)
        for group in sorted(groups.values(), key=lambda group: group["name"].casefold())
    )
    st.markdown(f"<div class='org-tree'><ul class='org-list org-list-root'>{branches}</ul></div>", unsafe_allow_html=True)


def render_org_structure(file_path: str) -> None:
    inject_css("org.css")
    raw = load_data(file_path)
    frame = clean_data(raw)
    hierarchy = build_hierarchy(frame)
    unconnected = unconnected_relationships(frame, hierarchy)
    unassigned = unassigned_resources(raw)

    st.markdown("<h1 class='org-title'>C&amp;C Organization Structure</h1>", unsafe_allow_html=True)
    st.markdown("<p class='org-subtitle'>Reporting Hierarchy</p>", unsafe_allow_html=True)
    if hierarchy["children"]:
        with st.container(border=True):
            render_org_chart(hierarchy)
    else:
        st.warning(f"No connected reporting relationships were found below {ROOT_NAME}.")

    if not unconnected.empty:
        st.subheader("Reporting groups not connected to the main hierarchy")
        st.warning(
            f"{_plural(len(unconnected), 'reporting relationship')} cannot be linked to {ROOT_NAME}. "
            "They are grouped by their listed manager below; check the manager's reporting chain in the workbook."
        )
        with st.container(border=True):
            render_unconnected_relationships(unconnected)

    if not unassigned.empty:
        st.subheader("Resources without a reporting manager")
        st.warning(f"{_plural(len(unassigned), 'resource')} with no reporting manager in the workbook.")
        resources = "".join(
            _node_html({"name": row["Resource Name"], "product": row["Product"], "children": []}, 1)
            for _, row in unassigned.iterrows()
        )
        with st.container(border=True):
            st.markdown(
                f"<div class='org-tree'><ul class='org-list org-list-root'>{resources}</ul></div>",
                unsafe_allow_html=True,
            )
