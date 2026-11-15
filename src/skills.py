"""Skills page: team-wise skills and the category drill-down."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from common.excel import DATA_ERRORS
from common.styles import inject_css
from skills_data import (
    create_download_dataframe,
    get_category_counts,
    get_resources_by_skill,
    get_skill_counts,
    get_team_skill_details,
    load_resource_skills,
    load_skill_categories,
    load_team_skills,
    to_excel_bytes,
)

_CATEGORY_KEY = "skills_category"
_SKILL_KEY = "skills_skill"
_PRODUCT_KEY = "skills_product"
_TEAM_VIEW = "Team-wise skills"
_CATEGORY_VIEW = "Skills by category"


def _select_product(product: str) -> None:
    st.session_state[_PRODUCT_KEY] = product


def _back_to_products() -> None:
    st.session_state[_PRODUCT_KEY] = None


def _select_category(category: str) -> None:
    st.session_state[_CATEGORY_KEY] = category
    st.session_state[_SKILL_KEY] = None


def _select_skill(skill: str) -> None:
    st.session_state[_SKILL_KEY] = skill


def _back_to_categories() -> None:
    st.session_state[_CATEGORY_KEY] = None
    st.session_state[_SKILL_KEY] = None


def _back_to_skills() -> None:
    st.session_state[_SKILL_KEY] = None


def _breadcrumb(*parts: str) -> None:
    trail = " <span class='sk-sep'>&rsaquo;</span> ".join(
        f"<span class='sk-crumb{' sk-current' if index == len(parts) - 1 else ''}'>{escape(part)}</span>"
        for index, part in enumerate(parts)
    )
    st.markdown(f"<div class='sk-breadcrumb'>{trail}</div>", unsafe_allow_html=True)


def _render_categories(long_df: pd.DataFrame, file_path: str | None) -> None:
    _breadcrumb("Skill categories")
    counts = get_category_counts(long_df, file_path)
    with st.container(key="skills-grid"):
        columns = st.columns(3)
        for index, row in counts.iterrows():
            with columns[index % 3]:
                st.button(
                    f"{row['Category']}  ({row['Resources']})",
                    key=f"skill_category_{row['Category']}",
                    icon=":material/category:",
                    width="stretch",
                    on_click=_select_category,
                    args=(row["Category"],),
                )


def _render_skills_in_category(long_df: pd.DataFrame, category: str, file_path: str | None) -> None:
    st.button(
        "\u2190 Back to categories",
        key="back_to_categories",
        on_click=_back_to_categories,
    )
    _breadcrumb("Skill categories", category)
    counts = get_skill_counts(long_df, category, file_path)
    if counts.empty:
        st.info("No skills found for this category.")
        return

    with st.container(key="skills-grid"):
        columns = st.columns(3)
        for index, row in counts.iterrows():
            with columns[index % 3]:
                st.button(
                    f"{row['Skill']}  ({row['Resources']})",
                    key=f"skill_{category}_{row['Skill']}",
                    icon=":material/psychology:",
                    width="stretch",
                    on_click=_select_skill,
                    args=(row["Skill"],),
                )


def _render_resources_for_skill(long_df: pd.DataFrame, category: str, skill: str) -> None:
    st.button(
        "\u2190 Back to category",
        key="back_to_skills",
        on_click=_back_to_skills,
    )
    _breadcrumb("Skill categories", category, skill)

    resources = get_resources_by_skill(long_df, skill)
    st.markdown(
        f"<div class='sk-total'><span class='sk-total-value'>{len(resources)}</span>"
        "<span class='sk-total-label'>Total resources</span></div>",
        unsafe_allow_html=True,
    )
    if resources.empty:
        st.info("No resources found for this skill.")
        return

    with st.container(key="skills-table"):
        st.dataframe(resources, width="stretch", hide_index=True)

    download_df = create_download_dataframe(resources)
    excel_data = to_excel_bytes(download_df)
    st.download_button(
        f"Download {skill} resources (Excel)",
        data=excel_data,
        file_name=f"{skill}_resources.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        width="stretch",
    )


def _render_team_skills(team_df: pd.DataFrame) -> None:
    products = sorted(team_df["Product Name"].unique(), key=str.casefold)
    if not products:
        st.info("No team resources were found in the resources sheet.")
        return

    product = st.session_state.get(_PRODUCT_KEY)
    if product not in products:
        product = None
        st.session_state[_PRODUCT_KEY] = None

    if product is None:
        _breadcrumb("Team-wise skills", "Products")
        st.caption("Select a product to see its resources and their skills.")
        counts = team_df.groupby("Product Name")["Resource Name"].nunique()
        with st.container(key="skills-grid"):
            columns = st.columns(3)
            for index, name in enumerate(products):
                with columns[index % 3]:
                    st.button(
                        f"{name}  ({counts[name]})",
                        key=f"skills_product_{name}",
                        icon=":material/groups:",
                        width="stretch",
                        on_click=_select_product,
                        args=(name,),
                    )
        return

    st.button("\u2190 Back to products", key="back_to_products", on_click=_back_to_products)
    _breadcrumb("Team-wise skills", product)
    details = get_team_skill_details(team_df, product)
    st.markdown(
        f"<div class='sk-total'><span class='sk-total-value'>{len(details)}</span>"
        "<span class='sk-total-label'>Team resources</span></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="skills-table"):
        st.dataframe(details, width="stretch", hide_index=True)


def render_skills(file_path: str | None = None) -> None:
    """Render team-wise skills or the category-to-resource drill-down."""
    inject_css("skills.css")
    st.session_state.setdefault(_CATEGORY_KEY, None)
    st.session_state.setdefault(_SKILL_KEY, None)

    view = st.segmented_control(
        "View skills by",
        [_TEAM_VIEW, _CATEGORY_VIEW],
        default=_TEAM_VIEW,
        required=True,
        key="skills_view",
    )

    try:
        if view == _TEAM_VIEW:
            _render_team_skills(load_team_skills(file_path))
            return
        long_df = load_resource_skills(file_path)
        load_skill_categories(file_path)
    except DATA_ERRORS as error:
        st.error(str(error))
        return

    if long_df.empty:
        st.info("No skill data was found in the resources sheet.")
        return

    category = st.session_state[_CATEGORY_KEY]
    skill = st.session_state[_SKILL_KEY]

    if category is None:
        _render_categories(long_df, file_path)
    elif skill is None:
        _render_skills_in_category(long_df, category, file_path)
    else:
        _render_resources_for_skill(long_df, category, skill)
