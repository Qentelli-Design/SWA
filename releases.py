"""Release activities extracted from the product status workbook."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from common.delivery import (
    STATUS_ORDER,
    count_badge,
    detail_value,
    format_date,
    normalize_progress,
    normalize_status,
    render_delivery_styles,
    status_badge,
)
from common.excel import CACHE_TTL, read_excel_frame, require_workbook, sheet_names, workbook_token

_RELEASE_COLUMNS = ["Product", "Activities", "Environment", "Actual End Date", "Status", "% Completed"]


def load_release_sheets(file_path: str) -> dict[str, pd.DataFrame]:
    path = require_workbook(file_path, "Product status workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_release_sheets(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_release_sheets(file_path: str, mtime_ns: int, size: int) -> dict[str, pd.DataFrame]:
    del mtime_ns, size
    products: dict[str, pd.DataFrame] = {}
    path = Path(file_path)
    for sheet_name in sheet_names(file_path):
        frame = read_excel_frame(path, sheet_name).dropna(how="all").copy()
        if "Activities" not in frame.columns:
            continue
        frame["Activities"] = frame["Activities"].fillna("").astype(str).str.strip()
        if "Activity Type" not in frame.columns:
            frame["Activity Type"] = ""
        if "Environment" not in frame.columns:
            frame["Environment"] = ""

        mask = frame["Activity Type"].astype(str).str.casefold().str.contains("release")
        releases = frame.loc[mask].copy()
        products[sheet_name] = releases[releases["Activities"].ne("")].reset_index(drop=True)
    return products


def _combine_releases(products: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name, frame in products.items():
        if frame is None or frame.empty:
            continue
        copy = frame.copy()
        copy["Product"] = name
        frames.append(copy)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _release_download_frame(frame: pd.DataFrame) -> pd.DataFrame:
    download = frame[[column for column in _RELEASE_COLUMNS if column in frame.columns]].copy()
    if "% Completed" in download.columns:
        download["% Completed"] = download["% Completed"].apply(lambda value: f"{normalize_progress(value):.0f}%")
    return download


@st.dialog("Release activity progress", width="large")
def show_release_details(product_name: str, frame: pd.DataFrame) -> None:
    st.markdown(
        f"<div class='dialog-product-title'>{escape(product_name)} - Release Activities</div>",
        unsafe_allow_html=True,
    )
    if frame.empty:
        st.info("No release activities found for this product.")
        return

    status_counts = frame["Status"].map(normalize_status).value_counts()
    st.markdown(
        "<div class='count-badge-row'>"
        + "".join(count_badge(status, int(status_counts.get(status, 0))) for status in STATUS_ORDER)
        + "</div>",
        unsafe_allow_html=True,
    )

    for row_index, (_, row) in enumerate(frame.iterrows()):
        progress = normalize_progress(row.get("% Completed", ""))
        status = normalize_status(row.get("Status", ""))
        with st.container(key=f"release-detail-{product_name}-{row_index}"):
            activity_column, env_column, owner_column, date_column, status_column = st.columns(
                [3.2, 0.9, 1.05, 0.9, 0.7],
                gap="xsmall",
                vertical_alignment="center",
            )
            with activity_column:
                activity = escape(str(row["Activities"]))
                st.markdown(
                    f"<div class='activity-name'>{row_index + 1}. {activity} -- {progress:.0f}%</div>",
                    unsafe_allow_html=True,
                )
                st.progress(progress / 100)
            with env_column:
                st.markdown(detail_value("Environment", row.get("Environment", "")), unsafe_allow_html=True)
            with date_column:
                st.markdown(
                    detail_value("Planned start", format_date(row.get("Planned Start Date", ""))),
                    unsafe_allow_html=True,
                )
            with status_column:
                st.markdown(detail_value("Status", status_badge(status), html=True), unsafe_allow_html=True)


@st.dialog("All releases list", width="large")
def show_all_releases(frame: pd.DataFrame) -> None:
    st.markdown("<div class='dialog-product-title'>All Releases</div>", unsafe_allow_html=True)
    if frame.empty:
        st.info("No release activities found.")
        return

    display = _release_download_frame(frame)
    if "Environment" in display.columns:
        display["Environment"] = display["Environment"].fillna("Not available")
    if "Actual End Date" in display.columns:
        display["Actual End Date"] = display["Actual End Date"].fillna("")

    st.dataframe(display.reset_index(drop=True))
    st.download_button(
        "Download releases (CSV)",
        data=display.to_csv(index=False).encode("utf-8"),
        file_name="all_releases.csv",
        mime="text/csv",
    )


@st.dialog("Download all releases")
def show_download_all(frame: pd.DataFrame) -> None:
    st.markdown("<div class='dialog-product-title'>Download releases data</div>", unsafe_allow_html=True)
    if frame.empty:
        st.info("No release activities available to download.")
        return

    download = _release_download_frame(frame)
    st.download_button(
        "Download releases (CSV)",
        data=download.to_csv(index=False).encode("utf-8"),
        file_name="all_releases.csv",
        mime="text/csv",
    )


def render_releases(file_path: str) -> None:
    render_delivery_styles()
    products = load_release_sheets(file_path)
    product_names = list(products)
    if not product_names:
        st.info("No releases found in the product status workbook.")
        return

    all_releases = _combine_releases(products)
    with st.container(key="delivery-card-dashboard", border=True):
        total_column, view_column, download_column = st.columns([1, 2, 2])
        with total_column:
            st.markdown("<div class='delivery-card-title'>Release Activities</div>", unsafe_allow_html=True)
            st.metric(label="Total releases", value=str(len(all_releases)))
        with view_column:
            if st.button("View all releases", key="view_all_releases", width="stretch"):
                show_all_releases(all_releases)
        with download_column:
            if not all_releases.empty and st.button("Download releases data", key="download_all_releases", width="stretch"):
                show_download_all(all_releases)

    for start in range(0, len(product_names), 3):
        columns = st.columns(3, gap="medium")
        for card_index, (column, product_name) in enumerate(zip(columns, product_names[start : start + 3])):
            with column:
                frame = products[product_name]
                with st.container(key=f"release-card-{start + card_index}", border=True):
                    st.markdown(
                        f"<div class='delivery-card-title'>{escape(product_name)}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<div class='count-badge-row'>" + count_badge("Green", len(frame)) + "</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("View details", key=f"release_details_{product_name}", width="stretch"):
                        show_release_details(product_name, frame)


def preview_release_counts(file_path: str) -> dict[str, int]:
    """Return product sheet name to release activity count, and print a summary.

    Lightweight helper for local checks. Not used by the Streamlit app.
    """
    products = load_release_sheets(file_path)
    counts = {name: int(len(frame)) for name, frame in products.items()}
    if not counts:
        print("No releases found in the provided Product Status workbook.")
        return counts

    print(f"Found releases in {len(counts)} product sheets, total release activities: {sum(counts.values())}")
    for name, count in sorted(counts.items(), key=lambda item: item[0].casefold()):
        print(f"- {name}: {count}")
    return counts


if __name__ == "__main__":
    import argparse

    from config import PROJECT_DELIVERY_STATUS_FILE_PATH

    parser = argparse.ArgumentParser(description="Preview release counts from Product_Status_Report workbook")
    parser.add_argument(
        "file",
        nargs="?",
        default=PROJECT_DELIVERY_STATUS_FILE_PATH,
        help="Path to Product_Status_Report workbook",
    )
    preview_release_counts(parser.parse_args().file)
