from pathlib import Path

import pandas as pd
import streamlit as st

from project_delivery_status import (
    _format_date,
    normalize_progress,
    _count_badge,
    _render_styles,
    normalize_status,
    STATUS_ORDER,
    _status_badge,
)


def load_release_sheets(file_path: str) -> dict[str, pd.DataFrame]:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Product status workbook not found: {path}")

    workbook = pd.ExcelFile(path, engine="openpyxl")
    products = {}
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        frame.columns = [str(column).strip() for column in frame.columns]
        frame = frame.dropna(how="all").copy()
        if "Activities" not in frame.columns:
            continue
        frame["Activities"] = frame["Activities"].fillna("").astype(str).str.strip()
        # Ensure Activity Type and Environment columns exist for filtering and details
        if "Activity Type" not in frame.columns:
            frame["Activity Type"] = ""
        if "Environment" not in frame.columns:
            frame["Environment"] = ""

        # Filter only release activities (case-insensitive contains 'release' or equals)
        mask = frame["Activity Type"].astype(str).str.casefold().str.contains("release")
        releases = frame.loc[mask].copy()
        releases = releases[releases["Activities"].ne("")].reset_index(drop=True)
        products[sheet_name] = releases
    return products


@st.dialog("Release activity progress", width="large")
def show_release_details(product_name: str, frame: pd.DataFrame) -> None:
    st.markdown(
        f"<div class='dialog-product-title'>{product_name} - Release Activities</div>",
        unsafe_allow_html=True,
    )
    if frame.empty:
        st.info("No release activities found for this product.")
        return

    # Show a count row like the delivery page
    status_counts = frame["Status"].map(normalize_status).value_counts()
    st.markdown(
        "<div class='count-badge-row'>"
        + "".join(_count_badge(status, int(status_counts.get(status, 0))) for status in STATUS_ORDER)
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
                st.markdown(
                    f"<div class='activity-name'>{row_index + 1}. {row['Activities']} -- {progress:.0f}%</div>",
                    unsafe_allow_html=True,
                )
                st.progress(progress / 100)
            with env_column:
                st.markdown(_detail_value("Environment", row.get("Environment", "")), unsafe_allow_html=True)
            with date_column:
                st.markdown(_detail_value("Planned start", _format_date(row.get("Planned Start Date", ""))), unsafe_allow_html=True)
            with status_column:
                st.markdown(_detail_value("Status", _status_badge(status)), unsafe_allow_html=True)


def _detail_value(label: str, value: object) -> str:
    # Normalize missing/blank values to a friendly placeholder
    display = value
    try:
        if pd.isna(value) or str(value).strip().lower() in {"", "nan", "nat"}:
            display = "Not available"
    except Exception:
        # Fallback for unexpected types
        if value in (None, ""):
            display = "Not available"

    return (
        f"<div class='detail-field'><div class='detail-label'>{label}</div>"
        f"<div class='detail-value'>{display}</div></div>"
    )


def render_releases(file_path: str) -> None:
    _render_styles()
    products = load_release_sheets(file_path)
    # Use shared styles from project_delivery_status for a corporate look

    product_names = list(products)
    if not product_names:
        st.info("No releases found in the product status workbook.")
        return

    # Combined dataframe for all releases across products
    combined_frames = []
    for name, df in products.items():
        if df is None or df.empty:
            continue
        copy = df.copy()
        copy["Product"] = name
        combined_frames.append(copy)
    all_releases = pd.concat(combined_frames, ignore_index=True) if combined_frames else pd.DataFrame()

    # Top dashboard card: use delivery-card styling for corporate consistency
    with st.container(key=f"delivery-card-dashboard", border=True):
        cols = st.columns([1, 2, 2])
        with cols[0]:
            st.markdown(f"<div class='delivery-card-title'>Release Activities</div>", unsafe_allow_html=True)
            st.metric(label="", value=str(len(all_releases)))
        with cols[1]:
            if st.button("View all releases", key="view_all_releases", use_container_width=True):
                show_all_releases(all_releases)
        with cols[2]:
            if not all_releases.empty:
                if st.button("Download releases data", key="download_all_releases", use_container_width=True):
                    show_download_all(all_releases)

    for start in range(0, len(product_names), 3):
        columns = st.columns(3, gap="medium")
        for card_index, (column, product_name) in enumerate(zip(columns, product_names[start : start + 3])):
            with column:
                frame = products[product_name]
                release_count = int(len(frame))
                with st.container(key=f"release-card-{start + card_index}", border=True):
                    st.markdown(f"<div class='delivery-card-title'>{product_name}</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div class='count-badge-row'>" + _count_badge("Green", release_count) + "</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("View details", key=f"release_details_{product_name}", width="stretch"):
                        show_release_details(product_name, frame)


@st.dialog("All releases list", width="large")
def show_all_releases(frame: pd.DataFrame) -> None:
    st.markdown("<div class='dialog-product-title'>All Releases</div>", unsafe_allow_html=True)
    if frame.empty:
        st.info("No release activities found.")
        return

    # Show table with selected columns including Environment and Actual End Date
    cols = [c for c in ["Product", "Activities", "Environment", "Actual End Date", "Status", "% Completed"] if c in frame.columns]
    display = frame[cols].copy()
    # Normalize missing values for display and format % Completed
    if "Environment" in display.columns:
        display["Environment"] = display["Environment"].fillna("Not available")
    if "Actual End Date" in display.columns:
        display["Actual End Date"] = display["Actual End Date"].fillna("")
    if "% Completed" in display.columns:
        display["% Completed"] = display["% Completed"].apply(lambda v: f"{normalize_progress(v):.0f}%")

    # Render dataframe without the index (reset already) for a cleaner view
    st.dataframe(display.reset_index(drop=True))

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button("Download releases (CSV)", data=csv, file_name="all_releases.csv", mime="text/csv")


@st.dialog("Download all releases")
def show_download_all(frame: pd.DataFrame) -> None:
    st.markdown("<div class='dialog-product-title'>Download releases data</div>", unsafe_allow_html=True)
    if frame.empty:
        st.info("No release activities available to download.")
        return

    download_df = frame[[col for col in ["Product", "Activities", "Environment", "Actual End Date", "Status", "% Completed"] if col in frame.columns]]
    download_df = download_df.copy()
    if "% Completed" in download_df.columns:
        download_df["% Completed"] = download_df["% Completed"].apply(lambda v: f"{normalize_progress(v):.0f}%")

    csv = download_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download releases (CSV)", data=csv, file_name="all_releases.csv", mime="text/csv")


def preview_release_counts(file_path: str) -> dict[str, int]:
    """Return a mapping of product sheet name -> release activity count and print a summary.

    This is a lightweight preview helper intended for local checks and tests.
    """
    products = load_release_sheets(file_path)
    counts: dict[str, int] = {name: int(len(frame)) for name, frame in products.items()}
    if not counts:
        print("No releases found in the provided Product Status workbook.")
        return counts

    total = sum(counts.values())
    print(f"Found releases in {len(counts)} product sheets, total release activities: {total}")
    for name, cnt in sorted(counts.items(), key=lambda x: x[0].casefold()):
        print(f"- {name}: {cnt}")
    return counts


if __name__ == "__main__":
    import argparse
    from config import PROJECT_DELIVERY_STATUS_FILE_PATH

    parser = argparse.ArgumentParser(description="Preview release counts from Product_Status_Report workbook")
    parser.add_argument("file", nargs="?", default=PROJECT_DELIVERY_STATUS_FILE_PATH, help="Path to Product_Status_Report workbook")
    args = parser.parse_args()
    preview_release_counts(args.file)
