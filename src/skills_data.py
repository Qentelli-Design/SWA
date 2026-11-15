"""Skills data: loading, normalizing, and aggregating resource skills. No UI code."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import streamlit as st

from common.excel import CACHE_TTL, dataframe_to_excel_bytes, read_excel_frame, require_workbook, workbook_token
from config import CCC_RESOURCE_SKILLSET_FILE_PATH

UNCATEGORIZED_LABEL = "Uncategorized / Review"

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


def load_resource_skills(file_path: str | None = None) -> pd.DataFrame:
    """Load the resources sheet and reshape it to one row per (resource, skill).

    Returns columns: Resource Name, Product Name, Skill. Duplicate skills for the
    same resource and product appear only once.
    """
    path = require_workbook(file_path or CCC_RESOURCE_SKILLSET_FILE_PATH, "Resources workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_resource_skills(resolved, mtime_ns, size)


@st.cache_data(show_spinner="Loading resource skills...", ttl=CACHE_TTL, max_entries=8)
def _load_resource_skills(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    rows = _load_skill_rows(file_path, mtime_ns, size)
    return rows[rows["Skill"].ne("")].reset_index(drop=True)


def load_team_skills(file_path: str | None = None) -> pd.DataFrame:
    """Load resource skills, retaining resources without recorded skills."""
    path = require_workbook(file_path or CCC_RESOURCE_SKILLSET_FILE_PATH, "Resources workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_skill_rows(resolved, mtime_ns, size)


@st.cache_data(show_spinner="Loading resource skills...", ttl=CACHE_TTL, max_entries=8)
def _load_skill_rows(file_path: str, mtime_ns: int, size: int) -> pd.DataFrame:
    del mtime_ns, size
    try:
        raw = read_excel_frame(Path(file_path), "Resource List")
    except ValueError:
        raw = read_excel_frame(Path(file_path), 0)

    resource_col = next((c for c in raw.columns if c.lower() in _RESOURCE_COL_ALIASES), None)
    product_col = next((c for c in raw.columns if c.lower() in _PRODUCT_COL_ALIASES), None)
    if product_col is None:
        # No Product column (e.g. CCC_Resource_Skillset.xlsx) -> use Team / Function instead.
        product_col = next((c for c in raw.columns if c.lower() in _TEAM_FUNCTION_ALIASES), None)
    if resource_col is None:
        raise ValueError("Resource Name column not found in resources sheet.")
    if product_col is None:
        raise ValueError("Product/Product Name/Team column not found in resources sheet.")

    raw[resource_col] = raw[resource_col].fillna("").astype(str).str.strip()
    raw[product_col] = raw[product_col].fillna("").astype(str).str.strip().replace({"CCC": "C&C", "": "Unassigned"})
    raw = raw[raw[resource_col].ne("")].reset_index(drop=True)

    skill_cols = _detect_skill_columns(raw, exclude={resource_col, product_col})
    if not skill_cols:
        rows = raw[[resource_col, product_col]].rename(
            columns={resource_col: "Resource Name", product_col: "Product Name"}
        ).copy()
        rows["Skill"] = ""
        return rows.drop_duplicates().reset_index(drop=True)

    long_df = raw.melt(id_vars=[resource_col, product_col], value_vars=skill_cols, value_name="_raw_skill")
    long_df = long_df.rename(columns={resource_col: "Resource Name", product_col: "Product Name"})
    long_df["Skill"] = long_df["_raw_skill"].map(_normalize_skill_token)
    long_df = long_df.drop_duplicates(subset=["Resource Name", "Product Name", "Skill"])
    return long_df[["Resource Name", "Product Name", "Skill"]].reset_index(drop=True)


def get_team_skill_details(team_df: pd.DataFrame, product: str) -> pd.DataFrame:
    """Summarize each product resource and their distinct recorded skills."""
    subset = team_df[team_df["Product Name"].eq(product)]
    return (
        subset.groupby("Resource Name", sort=True)["Skill"]
        .agg(lambda skills: ", ".join(sorted(set(skill for skill in skills if skill))) or "No skills recorded")
        .reset_index(name="Skills")
    )


def load_skill_categories(file_path: str | None = None) -> dict[str, list[str]]:
    """Load the Category -> Skills mapping from the workbook's 'Skill Categories' sheet."""
    path_text = file_path or CCC_RESOURCE_SKILLSET_FILE_PATH
    path = require_workbook(path_text, "Resources workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_skill_categories(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_skill_categories(file_path: str, mtime_ns: int, size: int) -> dict[str, list[str]]:
    del mtime_ns, size
    try:
        cat_df = read_excel_frame(Path(file_path), "Skill Categories")
    except ValueError as error:
        raise ValueError("The workbook must contain a 'Skill Categories' sheet.") from error

    if "Category" not in cat_df.columns or "Skill" not in cat_df.columns:
        raise ValueError("The 'Skill Categories' sheet must contain 'Category' and 'Skill' columns.")

    cat_df["Category"] = cat_df["Category"].fillna("").astype(str).str.strip()
    cat_df["Skill"] = cat_df["Skill"].fillna("").astype(str).str.strip()
    cat_df = cat_df[cat_df["Category"].ne("") & cat_df["Skill"].ne("")]
    if cat_df.empty:
        raise ValueError("The 'Skill Categories' sheet contains no usable category/skill rows.")

    return {category: group["Skill"].tolist() for category, group in cat_df.groupby("Category")}


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _skill_to_category_map(file_path: str | None = None) -> dict[str, str]:
    """Invert the category config into skill_token -> category (first match wins)."""
    mapping: dict[str, str] = {}
    for category, skills in load_skill_categories(file_path).items():
        for raw_skill in skills:
            mapping.setdefault(_normalize_skill_token(raw_skill), category)
    return mapping


def _with_category(long_df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    mapping = _skill_to_category_map(file_path)
    out = long_df.copy()
    out["Category"] = out["Skill"].map(mapping).fillna(UNCATEGORIZED_LABEL)
    return out


def get_category_counts(long_df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    """Unique-resource counts per category (a resource counts once even with multiple matching skills)."""
    categorized = _with_category(long_df, file_path)
    return (
        categorized.groupby("Category")["Resource Name"]
        .nunique()
        .reset_index(name="Resources")
        .sort_values("Resources", ascending=False)
        .reset_index(drop=True)
    )


def get_skill_counts(long_df: pd.DataFrame, category: str, file_path: str | None = None) -> pd.DataFrame:
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


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    return dataframe_to_excel_bytes(df, sheet_name="Resources")
