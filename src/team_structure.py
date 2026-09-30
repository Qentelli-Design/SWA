from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, read_resource_list, require_workbook, workbook_token
from common.styles import inject_css


REQUIRED_COLUMNS = ["Portfolio", "Product", "Resource Name", "Location", "Role", "Vendor"]
LEADERSHIP_DISPLAY_ORDER = [
    "Siva Rao Kompella S V",
    "B Ramesh",
    "Swetha Gundimeda",
    "Kanti Yalavarthy",
]


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

    frame = frame[REQUIRED_COLUMNS].dropna(how="all").copy()
    for column in REQUIRED_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    frame["Location Normalized"] = frame["Location"].map(_normalize_location)
    return frame.reset_index(drop=True)


def _normalize_location(value: str) -> str:
    normalized = value.casefold().replace(" ", "")
    if "offshore" in normalized:
        return "Offshore"
    if "onsite" in normalized or "office" in normalized:
        return "Onsite"
    return "Other"


def _governance_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["Role"].str.casefold().str.startswith("gover", na=False)


def get_governance_members(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[_governance_mask(frame)].copy()


def get_products_by_portfolio(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    product_frame = frame[
        (~_governance_mask(frame)) & frame["Product"].ne("")
    ].drop_duplicates("Product")
    ccc_products = product_frame.loc[product_frame["Portfolio"].eq("CCC"), "Product"]
    other_products = product_frame.loc[~product_frame["Portfolio"].eq("CCC"), "Product"]
    return (
        sorted(ccc_products.tolist(), key=str.casefold),
        sorted(other_products.tolist(), key=str.casefold),
    )


def _card_class(role: str) -> str:
    role_key = role.casefold()
    if "lead onsite" in role_key:
        return "lead-onsite"
    if "lead offshore" in role_key:
        return "lead-offshore"
    return "team-member"


def render_team_member_card(resource: pd.Series) -> None:
    card_class = _card_class(resource["Role"])
    card_class += " onsite-member" if resource["Location Normalized"] == "Onsite" else " offshore-member"
    is_rebadge = resource["Vendor"].casefold() == "rebadge"
    if is_rebadge:
        card_class += " rebadge-member"
    display_name = f"{resource['Resource Name']} - Rebadge" if is_rebadge else resource["Resource Name"]
    st.markdown(
        f"""
        <div class="team-card {card_class}">
            <div class="team-card-name">{escape(display_name)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_lead_card(resource: pd.Series) -> None:
    is_rebadge = resource["Vendor"].casefold() == "rebadge"
    display_name = f"{resource['Resource Name']} - Rebadge" if is_rebadge else resource["Resource Name"]
    st.markdown(
        f"""
        <div class="lead-card {_card_class(resource['Role'])}">
            <div class="lead-name">{escape(display_name)}</div>
            <div class="lead-role">{escape(resource['Role'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_governance_section(governance: pd.DataFrame) -> None:
    governance_by_name = governance.set_index("Resource Name")
    leadership_rows = []
    for index, name in enumerate(LEADERSHIP_DISPLAY_ORDER):
        if name != "Siva Rao Kompella S V" and name not in governance_by_name.index:
            continue
        is_swetha = name == "Swetha Gundimeda"
        person_class = "governance-primary" if is_swetha else "governance-secondary"
        if name == "B Ramesh":
            person_class = "governance-head"
        if name == "Siva Rao Kompella S V":
            person_class = "governance-featured"
        if name == "Kanti Yalavarthy":
            person_class = "governance-kanti"
        arrow_class = {
            "B Ramesh": "arrow-ramesh",
            "Swetha Gundimeda": "arrow-swetha",
            "Kanti Yalavarthy": "arrow-kanti",
        }.get(name, "")
        arrow = "" if index == 0 else f"<div class='leadership-arrow {arrow_class}'>↓</div>"
        level_class = {
            "B Ramesh": "leadership-ramesh",
            "Swetha Gundimeda": "leadership-swetha",
            "Kanti Yalavarthy": "leadership-kanti",
        }.get(name, "")
        leadership_rows.append(
            arrow +
            f"<div class='governance-person {person_class} {level_class}'>"
            f"<span class='governance-name'>{escape(name)}</span>"
            "</div>"
        )
    st.markdown(
        "<div class='governance-card'><div class='governance-heading'>CCC Leadership</div>"
        "<div class='governance-people'>" + "".join(leadership_rows) + "</div></div>"
        "<div class='leadership-gap'></div>",
        unsafe_allow_html=True,
    )


def render_product_summary(product_frame: pd.DataFrame) -> None:
    product_team = product_frame[~_governance_mask(product_frame)].copy()
    onsite = product_team[product_team["Location Normalized"].eq("Onsite")]
    offshore = product_team[product_team["Location Normalized"].eq("Offshore")]
    metrics = [
        ("Total team", len(product_team)),
        ("Onsite", len(onsite)),
        ("Offshore", len(offshore)),
        ("Onsite leads", int(onsite["Role"].str.casefold().str.contains("lead onsite").sum())),
        ("Offshore leads", int(offshore["Role"].str.casefold().str.contains("lead offshore").sum())),
    ]
    with st.container(key="product-summary", border=True):
        metric_columns = st.columns(len(metrics), gap="small")
        for column, (label, value) in zip(metric_columns, metrics):
            with column:
                st.metric(label, value, border=True)


def _render_team_column(team: pd.DataFrame, location: str) -> None:
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


def render_onsite_team(product_frame: pd.DataFrame) -> None:
    _render_team_column(product_frame[product_frame["Location Normalized"].eq("Onsite")], "Onsite")


def render_offshore_team(product_frame: pd.DataFrame) -> None:
    _render_team_column(product_frame[product_frame["Location Normalized"].eq("Offshore")], "Offshore")


def _select_team_product(product: str) -> None:
    st.session_state.selected_team_product = product


def _apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### Team filters")
        vendors = sorted(frame["Vendor"].loc[frame["Vendor"].ne("")].unique().tolist(), key=str.casefold)
        roles = sorted(frame["Role"].loc[frame["Role"].ne("")].unique().tolist(), key=str.casefold)
        selected_vendors = st.multiselect("Vendor", vendors, default=vendors, key="team_vendor_filter")
        selected_roles = st.multiselect("Role", roles, default=roles, key="team_role_filter")
    return frame[frame["Vendor"].isin(selected_vendors) & frame["Role"].isin(selected_roles)].copy()


def _render_styles() -> None:
    inject_css("team.css")

def render_team_structure(file_path: str) -> None:
    _render_styles()
    frame = load_data(file_path)
    filtered = _apply_filters(frame)
    st.markdown("<div class='page-kicker'>SWA workforce intelligence</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='page-title'>CCC Product Delivery Structure</h1>", unsafe_allow_html=True)
    st.markdown("<div class='product-divider'></div>", unsafe_allow_html=True)

    ccc_products, other_products = get_products_by_portfolio(filtered)
    products = ccc_products + other_products
    if not products:
        st.info("No product teams match the selected filters.")
        return
    product_team = filtered[~_governance_mask(filtered)].copy()
    render_product_summary(product_team)
    render_governance_section(get_governance_members(filtered))
    st.markdown("<div class='product-divider'></div>", unsafe_allow_html=True)

    if "selected_team_product" not in st.session_state or st.session_state.selected_team_product not in products:
        st.session_state.selected_team_product = products[0]

    selected_product = st.session_state.selected_team_product
    product_frame = product_team[product_team["Product"].eq(selected_product)].copy()
    onsite_count = int(product_frame["Location Normalized"].eq("Onsite").sum())
    offshore_count = int(product_frame["Location Normalized"].eq("Offshore").sum())
    left_rail, center, right_rail = st.columns([1.25, 3.5, 1.25], gap="large")
    with left_rail:
        with st.container(key="ccc-portfolio-rail", border=True):
            st.markdown("<div class='product-rail-title'>CCC portfolio</div>", unsafe_allow_html=True)
            for product in ccc_products:
                st.button(
                    product,
                    key=f"ccc_product_button_{product}",
                    type="primary" if selected_product == product else "secondary",
                    width="stretch",
                    on_click=_select_team_product,
                    args=(product,),
                )
    with center:
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
                render_onsite_team(product_frame)
        with offshore_column:
            with st.container(border=True):
                st.markdown("<div class='team-heading offshore-heading'>Offshore team</div>", unsafe_allow_html=True)
                render_offshore_team(product_frame)
    with right_rail:
        with st.container(key="other-portfolio-rail", border=True):
            st.markdown("<div class='product-rail-title'>Other portfolios</div>", unsafe_allow_html=True)
            for product in other_products:
                st.button(
                    product,
                    key=f"other_product_button_{product}",
                    type="primary" if selected_product == product else "secondary",
                    width="stretch",
                    on_click=_select_team_product,
                    args=(product,),
                )
