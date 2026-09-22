from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import Optional

import pandas as pd
import streamlit as st

from config import CCC_RESOURCE_SKILLSET_FILE_PATH
from skills_config import SKILL_CATEGORIES, UNCATEGORIZED_LABEL

_RESOURCE_COL_ALIASES = {"resource name"}
_PRODUCT_COL_ALIASES = {"product name", "product"}
# Fallback when the sheet has no Product column (e.g. CCC_Resource_Skillset.xlsx).
_TEAM_FUNCTION_ALIASES = {"team / function", "team/function"}

# Common raw skill variants -> canonical normalized token.
_CANONICAL_SKILLS = {
    "git": "git",
    "github": "git",
    "gitlab": "git",
    "jira": "jira",
    "chatgpt": "chatgpt",
    "chat gpt": "chatgpt",
    "javascript": "javascript",
    "js": "javascript",
    "node js": "javascript",
    "nodejs": "javascript",
    "amazonq": "amazon q",
    "amazon q": "amazon q",
    "aws": "aws",
    "amazon web services": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "google cloud": "gcp",
    "sql": "sql",
    "postgres": "sql",
}


def _normalize_skill_token(value: object) -> str:
    """Normalize a raw skill cell into a comparable, canonical token."""
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return ""
    key = text.lower().replace("-", " ").replace("/", " ").strip()
    key = re.sub(r"[^a-z0-9 #+]+", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return _CANONICAL_SKILLS.get(key, key)


def _detect_skill_columns(frame: pd.DataFrame, exclude: set[str]) -> list[str]:
    """Detect columns that contain skills, preferring headers like 'Skill'/'Skill 1'."""
    skill_cols = [c for c in frame.columns if re.search(r"^skill\b|skill\s*\d", str(c), flags=re.I)]
    if skill_cols:
        return skill_cols

    # Heuristic fallback: a skill column has a non-trivial fraction of short, varied text values.
    total_rows = len(frame)
    if total_rows == 0:
        return []
    candidates: list[str] = []
    for column in frame.columns:
        if column in exclude:
            continue
        series = frame[column].astype(str).fillna("")
        non_empty = series.str.strip().ne("")
        non_empty_count = int(non_empty.sum())
        if non_empty_count == 0:
            continue
        frac = non_empty_count / total_rows
        avg_len = series[non_empty].str.len().mean()
        unique_vals = series[non_empty].nunique()
        if frac >= 0.05 and (avg_len <= 60 or unique_vals > 3):
            candidates.append(column)
    return candidates or [c for c in frame.columns if c not in exclude]


@st.cache_data(show_spinner="Loading resource skills...")
def load_resource_skills(file_path: Optional[str] = None) -> pd.DataFrame:
    """Load the resources sheet and reshape it to one row per (resource, skill).

    Returns columns: Resource Name, Product Name, Skill. A resource with the same
    skill in multiple cells (or duplicate cells) appears only once for that skill.
    """
    path = Path(file_path or CCC_RESOURCE_SKILLSET_FILE_PATH).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Resources workbook not found: {path}")

    try:
        raw = pd.read_excel(path, sheet_name="Resource List", engine="openpyxl")
    except ValueError:
        raw = pd.read_excel(path, engine="openpyxl")

    raw.columns = [str(c).strip() for c in raw.columns]

    resource_col = next((c for c in raw.columns if c.lower() in _RESOURCE_COL_ALIASES), None)
    product_col = next((c for c in raw.columns if c.lower() in _PRODUCT_COL_ALIASES), None)
    if product_col is None:
        # No Product column (e.g. CCC_Resource_Skillset.xlsx) -> use Team / Function instead.
        product_col = next((c for c in raw.columns if c.lower() in _TEAM_FUNCTION_ALIASES), None)
    if resource_col is None:
        raise ValueError("Resource Name column not found in resources sheet.")
    if product_col is None:
        raise ValueError("Product/Product Name/Team column not found in resources sheet.")

    raw[resource_col] = raw[resource_col].astype(str).str.strip()
    raw[product_col] = raw[product_col].astype(str).str.strip()
    raw = raw[raw[resource_col].ne("")].reset_index(drop=True)

    skill_cols = _detect_skill_columns(raw, exclude={resource_col, product_col})
    if not skill_cols:
        return pd.DataFrame(columns=["Resource Name", "Product Name", "Skill"])

    long_df = raw.melt(id_vars=[resource_col, product_col], value_vars=skill_cols, value_name="_raw_skill")
    long_df = long_df.rename(columns={resource_col: "Resource Name", product_col: "Product Name"})
    long_df["Skill"] = long_df["_raw_skill"].map(_normalize_skill_token)
    long_df = long_df[long_df["Skill"].ne("")]
    long_df = long_df.drop_duplicates(subset=["Resource Name", "Skill"])
    return long_df[["Resource Name", "Product Name", "Skill"]].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_skill_categories(file_path: Optional[str] = None) -> dict[str, list[str]]:
    """Load the Category -> Skills mapping from the workbook's 'Skill Categories' sheet.

    Falls back to the hardcoded SKILL_CATEGORIES config if the sheet is missing or unusable,
    so the app keeps working even against older workbooks.
    """
    path = Path(file_path or CCC_RESOURCE_SKILLSET_FILE_PATH).expanduser()
    try:
        cat_df = pd.read_excel(path, sheet_name="Skill Categories", engine="openpyxl")
    except (FileNotFoundError, ValueError, OSError):
        return SKILL_CATEGORIES

    cat_df.columns = [str(c).strip() for c in cat_df.columns]
    if "Category" not in cat_df.columns or "Skill" not in cat_df.columns:
        return SKILL_CATEGORIES

    cat_df["Category"] = cat_df["Category"].astype(str).str.strip()
    cat_df["Skill"] = cat_df["Skill"].astype(str).str.strip()
    cat_df = cat_df[cat_df["Category"].ne("") & cat_df["Skill"].ne("")]
    if cat_df.empty:
        return SKILL_CATEGORIES

    return {category: group["Skill"].tolist() for category, group in cat_df.groupby("Category")}


@st.cache_data(show_spinner=False)
def _skill_to_category_map(file_path: Optional[str] = None) -> dict[str, str]:
    """Invert the category config into skill_token -> category (first match wins)."""
    mapping: dict[str, str] = {}
    for category, skills in load_skill_categories(file_path).items():
        for raw_skill in skills:
            mapping.setdefault(_normalize_skill_token(raw_skill), category)
    return mapping


def _with_category(long_df: pd.DataFrame, file_path: Optional[str] = None) -> pd.DataFrame:
    mapping = _skill_to_category_map(file_path)
    out = long_df.copy()
    out["Category"] = out["Skill"].map(mapping).fillna(UNCATEGORIZED_LABEL)
    return out


def get_category_counts(long_df: pd.DataFrame, file_path: Optional[str] = None) -> pd.DataFrame:
    """Unique-resource counts per category (a resource counts once even with multiple matching skills)."""
    categorized = _with_category(long_df, file_path)
    return (
        categorized.groupby("Category")["Resource Name"]
        .nunique()
        .reset_index(name="Resources")
        .sort_values("Resources", ascending=False)
        .reset_index(drop=True)
    )


def get_skill_counts(long_df: pd.DataFrame, category: str, file_path: Optional[str] = None) -> pd.DataFrame:
    """Unique-resource counts per skill within a category."""
    categorized = _with_category(long_df, file_path)
    subset = categorized[categorized["Category"] == category]
    return (
        subset.groupby("Skill")["Resource Name"]
        .nunique()
        .reset_index(name="Resources")
        .sort_values("Resources", ascending=False)
        .reset_index(drop=True)
    )


def get_resources_by_skill(long_df: pd.DataFrame, skill_token: str) -> pd.DataFrame:
    """Deduplicated, alphabetically sorted resources with the given skill."""
    subset = long_df[long_df["Skill"] == skill_token]
    return (
        subset[["Resource Name", "Product Name"]]
        .drop_duplicates()
        .sort_values("Resource Name")
        .reset_index(drop=True)
    )


def create_download_dataframe(resources: pd.DataFrame) -> pd.DataFrame:
    return resources[["Resource Name", "Product Name"]].copy()


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resources")
    return buffer.getvalue()


def _select_category(category: str) -> None:
    st.session_state.skills_category = category
    st.session_state.skills_skill = None


def _select_skill(skill: str) -> None:
    st.session_state.skills_skill = skill


def _back_to_categories() -> None:
    st.session_state.skills_category = None
    st.session_state.skills_skill = None


def _back_to_skills() -> None:
    st.session_state.skills_skill = None


def _render_categories(long_df: pd.DataFrame, file_path: Optional[str]) -> None:
    st.markdown("### Skill categories")
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


def _render_skills_in_category(long_df: pd.DataFrame, category: str, file_path: Optional[str]) -> None:
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
    excel_data = _to_excel_bytes(download_df)
    st.download_button(
        f"Download {skill} resources (Excel)",
        data=excel_data,
        file_name=f"{skill}_resources.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        width="stretch",
    )


def render_skills(file_path: Optional[str] = None) -> None:
    """Render the dynamic Skills → Category → Skill → Resources drill-down."""
    st.session_state.setdefault("skills_category", None)
    st.session_state.setdefault("skills_skill", None)

    try:
        long_df = load_resource_skills(file_path)
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        return

    if long_df.empty:
        st.info("No skill data was found in the resources sheet.")
        return

    category = st.session_state.skills_category
    skill = st.session_state.skills_skill

    if category is None:
        _render_categories(long_df, file_path)
    elif skill is None:
        _render_skills_in_category(long_df, category, file_path)
    else:
        _render_resources_for_skill(long_df, category, skill)
