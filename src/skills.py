"""Skills page: the Skills -> Category -> Skill -> Resources drill-down."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common.excel import DATA_ERRORS
from skills_data import (
    create_download_dataframe,
    get_category_counts,
    get_resources_by_skill,
    get_skill_counts,
    load_resource_skills,
    load_skill_categories,
    to_excel_bytes,
)

_CATEGORY_KEY = "skills_category"
_SKILL_KEY = "skills_skill"


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


def _render_categories(long_df: pd.DataFrame, file_path: str | None) -> None:
    st.markdown("<h3 class='skill-categories-heading'>Skill categories</h3>", unsafe_allow_html=True)
    counts = get_category_counts(long_df, file_path)
    columns = st.columns(3)
    for index, row in counts.iterrows():
        with columns[index % 3]:
            st.button(
                f"{row['Category']}  ({row['Resources']})",
                key=f"skill_category_{row['Category']}",
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
    st.markdown(f"### {category}")
    counts = get_skill_counts(long_df, category, file_path)
    if counts.empty:
        st.info("No skills found for this category.")
        return

    columns = st.columns(3)
    for index, row in counts.iterrows():
        with columns[index % 3]:
            st.button(
                f"{row['Skill']}  ({row['Resources']})",
                key=f"skill_{category}_{row['Skill']}",
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
    st.markdown(f"### {skill}")

    resources = get_resources_by_skill(long_df, skill)
    st.caption(f"Total resources: {len(resources)}")
    if resources.empty:
        st.info("No resources found for this skill.")
        return

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


def render_skills(file_path: str | None = None) -> None:
    """Render the dynamic Skills → Category → Skill → Resources drill-down."""
    st.session_state.setdefault(_CATEGORY_KEY, None)
    st.session_state.setdefault(_SKILL_KEY, None)

    try:
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
