"""Organization structure page: the reporting hierarchy below the root leader."""

from __future__ import annotations

from html import escape

import streamlit as st

from common.styles import inject_css
from org_data import ROOT_NAME, build_hierarchy, clean_data, load_data


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


def render_org_structure(file_path: str) -> None:
    inject_css("org.css")
    frame = clean_data(load_data(file_path))
    hierarchy = build_hierarchy(frame)
    if not hierarchy["children"]:
        st.warning(f"No connected reporting relationships were found below {ROOT_NAME}.")
        return

    st.markdown("<h1 class='org-title'>C&amp;C Organization Structure</h1>", unsafe_allow_html=True)
    st.markdown("<p class='org-subtitle'>Reporting Hierarchy</p>", unsafe_allow_html=True)
    with st.container(border=True):
        render_org_chart(hierarchy)
