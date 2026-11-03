"""Team structure page: leadership, headline metrics, and the product browser."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.styles import inject_css
from team_data import (
    build_team_metrics,
    count_by_location,
    get_governance_members,
    get_leadership_hierarchy,
    get_product_team,
    get_products_by_portfolio,
    load_data,
)

_SELECTED_PRODUCT_KEY = "selected_team_product"


def _card_class(role: str) -> str:
    role_key = role.casefold()
    if "lead onsite" in role_key:
        return "lead-onsite"
    if "lead offshore" in role_key:
        return "lead-offshore"
    return "team-member"


def _is_rebadge(resource: pd.Series) -> bool:
    return resource["Vendor"].casefold() == "rebadge"


def _display_name(resource: pd.Series) -> str:
    return f"{resource['Resource Name']} - Rebadge" if _is_rebadge(resource) else resource["Resource Name"]


def _consultant_tag(resource: pd.Series) -> str:
    if not resource["Is Consultant"]:
        return ""
    details = [
        resource["Resource Name"],
        resource["Qentelli Designation"],
        f"ID: {resource['Qentelli ID']}" if resource["Qentelli ID"] else "",
        resource["Qentelli Mail ID"],
        f"Joined: {resource['Qentelli DOJ']}" if resource["Qentelli DOJ"] else "",
    ]
    tooltip = escape(" | ".join(detail for detail in details if detail))
    return f"<span class='consultant-tag' title='{tooltip}'>Consultant</span>"


def render_team_member_card(resource: pd.Series) -> None:
    card_class = _card_class(resource["Role"])
    card_class += " onsite-member" if resource["Location Normalized"] == "Onsite" else " offshore-member"
    if _is_rebadge(resource):
        card_class += " rebadge-member"
    st.markdown(
        f'<div class="team-card {card_class}">'
        f'<div class="team-card-name">{escape(_display_name(resource))}</div>'
        f"{_consultant_tag(resource)}</div>",
        unsafe_allow_html=True,
    )


def render_lead_card(resource: pd.Series) -> None:
    st.markdown(
        f'<div class="lead-card {_card_class(resource["Role"])}">'
        f'<div class="lead-heading"><div class="lead-name">{escape(_display_name(resource))}</div>'
        f"{_consultant_tag(resource)}</div>"
        f'<div class="lead-role">{escape(resource["Role"])}</div></div>',
        unsafe_allow_html=True,
    )


def _leadership_node_html(node: dict, depth: int = 1) -> str:
    tier = min(depth, 4)
    children = "".join(_leadership_node_html(child, depth + 1) for child in node["children"])
    child_group = (
        f"<div class='leader-connector'></div><div class='leader-peer-row'>{children}</div>"
        if children
        else ""
    )
    return (
        "<div class='leader-branch'>"
        f"<div class='leader-bar leader-tier-{tier}'>{escape(node['name'])}</div>"
        f"{child_group}</div>"
    )


def render_governance_section(governance: pd.DataFrame) -> None:
    hierarchy = get_leadership_hierarchy(governance)
    st.markdown(
        "<div class='governance-card'><div class='governance-heading'>C&amp;C Leadership</div>"
        "<div class='leader-tree'>" + _leadership_node_html(hierarchy) + "</div></div>"
        "<div class='leadership-gap'></div>",
        unsafe_allow_html=True,
    )


def render_product_summary(frame: pd.DataFrame) -> None:
    metrics = build_team_metrics(frame)
    with st.container(key="product-summary", border=True):
        metric_columns = st.columns(len(metrics), gap="small")
        for column, (label, value) in zip(metric_columns, metrics):
            with column:
                st.metric(label, value, border=True)


def render_location_team(product_frame: pd.DataFrame, location: str) -> None:
    """Render the leads and team members of one product for ``location`` (Onsite/Offshore)."""
    team = product_frame[product_frame["Location Normalized"].eq(location)]
    leads = team[team["Role"].str.casefold().str.contains(f"lead {location.casefold()}")]
    members = team[~team.index.isin(leads.index)]
    if team.empty:
        st.caption(f"No {location} resources available.")
        return
    for _, resource in leads.iterrows():
        render_lead_card(resource)
    if not members.empty:
        st.markdown("<div class='member-heading'>Team members</div>", unsafe_allow_html=True)
        for _, resource in members.iterrows():
            render_team_member_card(resource)


def _select_team_product(product: str) -> None:
    st.session_state[_SELECTED_PRODUCT_KEY] = product


def _render_product_rail(
    container_key: str,
    title_html: str,
    button_key_prefix: str,
    products: list[str],
    selected_product: str,
) -> None:
    with st.container(key=container_key, border=True):
        st.markdown(f"<div class='product-rail-title'>{title_html}</div>", unsafe_allow_html=True)
        for product in products:
            st.button(
                product,
                key=f"{button_key_prefix}{product}",
                type="primary" if selected_product == product else "secondary",
                width="stretch",
                on_click=_select_team_product,
                args=(product,),
            )


def _render_product_detail(selected_product: str, product_frame: pd.DataFrame) -> None:
    onsite_count, offshore_count = count_by_location(product_frame)
    st.markdown(
        f"""
        <div class="selected-product-panel">
            <div class="selected-product-name">{escape(selected_product)}</div>
            <div class="selected-product-stats">
                <div class="selected-product-stat"><strong>{onsite_count}</strong>Onsite resources</div>
                <div class="selected-product-stat"><strong>{offshore_count}</strong>Offshore resources</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    onsite_column, offshore_column = st.columns(2, gap="medium")
    with onsite_column:
        with st.container(border=True):
            st.markdown("<div class='team-heading onsite-heading'>Onsite team</div>", unsafe_allow_html=True)
            render_location_team(product_frame, "Onsite")
    with offshore_column:
        with st.container(border=True):
            st.markdown("<div class='team-heading offshore-heading'>Offshore team</div>", unsafe_allow_html=True)
            render_location_team(product_frame, "Offshore")


@st.fragment
def _render_product_browser(
    product_team: pd.DataFrame, primary_products: list[str], other_products: list[str]
) -> None:
    """Product picker and detail. A fragment, so choosing a product only reruns this block."""
    products = primary_products + other_products
    if _SELECTED_PRODUCT_KEY not in st.session_state or st.session_state[_SELECTED_PRODUCT_KEY] not in products:
        st.session_state[_SELECTED_PRODUCT_KEY] = products[0]

    selected_product = st.session_state[_SELECTED_PRODUCT_KEY]
    product_frame = product_team[product_team["Product"].eq(selected_product)].copy()
    left_rail, center, right_rail = st.columns([1.25, 3.5, 1.25], gap="large")
    with left_rail:
        _render_product_rail(
            "ccc-portfolio-rail", "C&amp;C portfolio", "ccc_product_button_", primary_products, selected_product
        )
    with center:
        _render_product_detail(selected_product, product_frame)
    with right_rail:
        _render_product_rail(
            "other-portfolio-rail", "Other products", "other_product_button_", other_products, selected_product
        )


def render_team_structure(file_path: str) -> None:
    inject_css("team.css")
    frame = load_data(file_path)
    st.markdown("<div class='page-kicker'>SWA workforce intelligence</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='page-title'>C&amp;C Product Delivery Structure</h1>", unsafe_allow_html=True)
    st.markdown("<div class='product-divider'></div>", unsafe_allow_html=True)

    primary_products, other_products = get_products_by_portfolio(frame)
    if not (primary_products or other_products):
        st.info("No product teams found.")
        return
    product_team = get_product_team(frame)
    render_product_summary(frame)
    render_governance_section(get_governance_members(frame))
    st.markdown("<div class='product-divider'></div>", unsafe_allow_html=True)
    _render_product_browser(product_team, primary_products, other_products)
