from pathlib import Path

import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = ["Portfolio", "Product", "Resource Name", "Location", "Role", "Vendor"]
LEADERSHIP_DISPLAY_ORDER = [
    "B Ramesh",
    "Swetha Gundimeda",
    "Kanti Yalavarthy",
]


@st.cache_data(show_spinner=False)
def load_data(file_path: str) -> pd.DataFrame:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")

    try:
        frame = pd.read_excel(path, sheet_name="Resource List", engine="openpyxl")
    except ValueError as error:
        raise ValueError("The workbook does not contain a 'Resource List' sheet.") from error

    frame.columns = [str(column).strip() for column in frame.columns]
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


def get_products(frame: pd.DataFrame) -> list[str]:
    products = frame.loc[
        (~_governance_mask(frame)) & frame["Product"].ne(""),
        "Product",
    ]
    return sorted(products.drop_duplicates().tolist(), key=str.casefold)


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
            <div class="team-card-name">{display_name}</div>
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
            <div class="lead-name">{display_name}</div>
            <div class="lead-role">{resource['Role']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_governance_section(governance: pd.DataFrame) -> None:
    governance_by_name = governance.set_index("Resource Name")
    leadership_rows = []
    for name in LEADERSHIP_DISPLAY_ORDER:
        if name not in governance_by_name.index:
            continue
        resource = governance_by_name.loc[name]
        is_swetha = name == "Swetha Gundimeda"
        person_class = "governance-primary" if is_swetha else "governance-secondary"
        if name == "B Ramesh":
            person_class = "governance-featured"
        leadership_rows.append(
            f"<div class='governance-person {person_class}'>"
            f"<span class='governance-name'>{name}</span>"
            "</div>"
        )
    st.markdown(
        "<div class='governance-card'><div class='governance-heading'>CCC Leadership</div>"
        "<div class='governance-people'>" + "".join(leadership_rows) + "</div></div>",
        unsafe_allow_html=True,
    )


def render_product_summary(product_frame: pd.DataFrame) -> None:
    product_team = product_frame[~_governance_mask(product_frame)].drop_duplicates(subset=["Resource Name"])
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


def _apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### Team filters")
        vendors = sorted(frame["Vendor"].loc[frame["Vendor"].ne("")].unique().tolist(), key=str.casefold)
        roles = sorted(frame["Role"].loc[frame["Role"].ne("")].unique().tolist(), key=str.casefold)
        selected_vendors = st.multiselect("Vendor", vendors, default=vendors, key="team_vendor_filter")
        selected_roles = st.multiselect("Role", roles, default=roles, key="team_role_filter")
    return frame[frame["Vendor"].isin(selected_vendors) & frame["Role"].isin(selected_roles)].copy()


def _render_styles() -> None:
    st.markdown(
        """
        <style>
        .team-hero {
            background: #ffffff;
            border-bottom: 1px solid #d7e2e2;
            margin: 0 0 1.15rem;
            padding: 0.15rem 0 1.1rem;
        }
        .team-hero h1 { color: #173c43; font-size: 2.2rem; margin: 0.25rem 0 0.25rem; }
        .team-hero p { color: #65727d; margin: 0; }
        .section-kicker, .governance-label, .lead-label {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .team-hero .section-kicker { color: #d96c38; }
        .section-kicker { color: #087f8c; margin-top: 0.35rem; }
        .page-kicker { color: #173c43; font-size: 1.35rem; font-weight: 800; letter-spacing: 0.1em; margin: 0 0 0.2rem; text-transform: uppercase; }
        .page-title { color: #173c43; font-size: 1.5rem !important; font-weight: 700; line-height: 1.1 !important; margin: 0 0 0.65rem; }
        .section-title { color: #173c43; font-size: 1.35rem; font-weight: 700; margin: 0.1rem 0 0.55rem; }
        .product-divider { border-top: 1px solid #dfe7e9; margin: 0.75rem 0 0.6rem; }
        .product-title h2 { color: #173c43; font-size: 1.3rem; margin: 0.1rem 0 0.55rem; }
        .governance-heading { color: #173c43; font-size: 0.87rem; font-weight: 800; letter-spacing: 0.08em; margin: 0 0 0.35rem; text-align: center; text-transform: uppercase; }
        .governance-card, .team-card, .lead-card {
            border-radius: 8px;
            margin: 0 0 0.35rem;
            padding: 0.55rem 0.7rem;
        }
        .governance-card { background: #f5f8f7; border: 1px solid #c8ddda; border-left: 4px solid #087f8c; border-radius: 8px; margin: 0 0 0.55rem; padding: 0.45rem 0.75rem; }
        .governance-label { color: #426782; }
        .governance-people { display: flex; gap: 0.6rem; }
        .governance-person { align-items: baseline; background: #ffffff; border: 1px solid #dfe7e9; border-radius: 6px; display: flex; flex: 1; gap: 0.65rem; padding: 0.35rem 0.5rem; }
        .governance-name { color: #183342; font-size: 0.85rem; font-weight: 800; }
        .governance-primary { border-color: #8fcfc8; }
        .governance-primary .governance-name { color: #087f8c; }
        .governance-featured { background: #fff7ed; border-color: #e5b77e; }
        .governance-featured .governance-name { color: #9a5b16; }
        .governance-role { color: #65727d; font-size: 0.8rem; }
        .governance-role { color: #526d7b; font-size: 0.88rem; margin-top: 0.2rem; }
        .team-heading { border-bottom: 2px solid #dfe7e9; font-size: 0.95rem; font-weight: 700; margin: 0 0 0.5rem; padding-bottom: 0.35rem; }
        .onsite-heading { color: #a85425; }
        .offshore-heading { color: #126c76; }
        .lead-card.lead-onsite { background: #fff2e7; border: 1px solid #efc39f; border-left: 4px solid #d96c38; }
        .lead-card.lead-offshore { background: #e8f6f4; border: 1px solid #b8deda; border-left: 4px solid #087f8c; }
        .lead-label { color: #4b5a60; }
        .lead-name { color: #17212b; font-size: 0.92rem; font-weight: 700; margin-top: 0.05rem; }
        .lead-role { color: #65727d; font-size: 0.72rem; margin-top: 0.05rem; }
        .team-card { border: 1px solid #c5d9d7; padding: 0.4rem 0.6rem; }
        .team-card-name { color: #24343b; font-size: 0.82rem; font-weight: 650; line-height: 1.2; }
        .team-card.onsite-member { background: #fff8f1; border-color: #efd3bb; }
        .team-card.offshore-member { background: #f0f8f7; border-color: #c4e0dd; }
        .team-card.lead-onsite { background: #fff2e7; border-color: #efc39f; }
        .team-card.lead-offshore { background: #e8f6f4; border-color: #b8deda; }
        .team-card.rebadge-member { background: #f2ecfb; border-color: #cbb9e8; }
        .team-card.rebadge-member .team-card-name { color: #5d3c85; }
        .portfolio-rail { border-radius: 8px; padding: 0.55rem; }
        .ccc-portfolio-rail { background: #eef8f6; border: 1px solid #c6e4df; }
        .other-portfolio-rail { background: #f4f0fb; border: 1px solid #ddd1ed; }
        .product-rail-title { color: #173c43; font-size: 0.9rem; font-weight: 800; letter-spacing: 0.04em; margin: 0.1rem 0 0; padding-bottom: 20px; text-transform: uppercase; }
        .product-rail [data-testid="stButton"] button { background: #fbfefd; border: 1px solid #bfd0cf; color: #31555b; font-size: 0.7rem; font-weight: 800; min-height: 1.4rem; padding: 0.12rem 0.25rem; white-space: normal; }
        .product-rail [data-testid="stButton"] button:hover { background: #e8f6f4; border-color: #087f8c; color: #075f69; }
        .product-rail [data-testid="stButton"] button[kind="primary"] { background: #087f8c; border-color: #087f8c; color: #ffffff; font-weight: 800; }
        .other-portfolio-rail .product-rail [data-testid="stButton"] button { background: #fcfaff; border-color: #cdbbe5; }
        .other-portfolio-rail .product-rail [data-testid="stButton"] button[kind="primary"] { background: #8064a9; border-color: #8064a9; color: #ffffff; }
        .selected-product-panel { background: #f7fbfa; border: 1px solid #d6e7e3; border-left: 4px solid #087f8c; border-radius: 8px; margin: 0 0 0.65rem; padding: 0.65rem 0.8rem; }
        .selected-product-name { color: #173c43; font-size: 1.15rem; font-weight: 800; margin-bottom: 0.45rem; }
        .selected-product-stats { display: flex; gap: 0.45rem; }
        .selected-product-stat { background: #ffffff; border: 1px solid #dfe7e9; border-radius: 6px; color: #48636a; flex: 1; font-size: 0.68rem; padding: 0.35rem 0.45rem; }
        .selected-product-stat strong { color: #173c43; display: block; font-size: 1rem; line-height: 1.05; }
        .st-key-product-summary { background: #f5f8f7; border: 1px solid #c8ddda; border-left: 4px solid #087f8c; border-radius: 8px; margin: 0 0 0.7rem; padding: 0.55rem 0.65rem; }
        .st-key-product-summary [data-testid="stMetric"] { background: #ffffff; border: 1px solid #d6e7e3; border-radius: 7px; padding: 0.45rem 0.55rem; }
        .st-key-product-summary [data-testid="stMetricLabel"] { color: #48636a; font-size: 0.66rem; font-weight: 700; }
        .st-key-product-summary [data-testid="stMetricValue"] { color: #173c43; font-size: 1.35rem; font-weight: 800; }
        .team-box { background: #ffffff; border: 1px solid #dfe7e9; border-radius: 8px; padding: 0.65rem; }
        .member-heading { color: #65727d; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; margin: 0.55rem 0 0.35rem; text-transform: uppercase; }
        [data-baseweb="tab-list"] { gap: 0.35rem; overflow-x: auto; padding: 0.25rem 0 0.65rem; scrollbar-width: thin; }
        [data-baseweb="tab"] { background: #eaf1f0; border: 1px solid #d1dfdd; border-radius: 999px; color: #48636a; font-size: 0.82rem; min-height: 2.2rem; padding: 0.4rem 0.85rem; }
        [data-baseweb="tab"][aria-selected="true"] { background: #087f8c; border-color: #087f8c; color: #ffffff; }
        [data-baseweb="tab-highlight"] { background: transparent; }
        [data-testid="stMetric"] { background: #ffffff; border: 1px solid #dfe7e9; border-radius: 8px; padding: 0.45rem 0.6rem; }
        [data-testid="stMetricLabel"] { color: #65727d; font-size: 0.68rem; }
        [data-testid="stMetricValue"] { color: #173c43; font-size: 1.25rem; }
        [data-testid="stVerticalBlock"] { gap: 0.45rem; }
        [data-testid="stHorizontalBlock"] { gap: 0.75rem; }
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stWidgetLabel"] p { font-size: 0.92rem; margin-bottom: 0.35rem; }
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div { min-height: 2.6rem; padding: 0.25rem 0.45rem; }
        [data-testid="stSidebar"] [role="listbox"] [role="option"] { line-height: 1.45; min-height: 2.2rem; padding: 0.45rem 0.65rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
                if st.button(
                    product,
                    key=f"ccc_product_button_{product}",
                    type="primary" if selected_product == product else "secondary",
                    width="stretch",
                ):
                    st.session_state.selected_team_product = product
                    st.rerun()
    with center:
        st.markdown(
            f"""
            <div class="selected-product-panel">
                <div class="selected-product-name">{selected_product}</div>
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
                if st.button(
                    product,
                    key=f"other_product_button_{product}",
                    type="primary" if selected_product == product else "secondary",
                    width="stretch",
                ):
                    st.session_state.selected_team_product = product
                    st.rerun()