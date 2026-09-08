from pathlib import Path

import pandas as pd
import streamlit as st


STATUS_ORDER = ("Green", "Amber", "Red")
REQUIRED_COLUMNS = [
    "Activities",
    "Priority",
    "Owner",
    "% Completed",
    "Planned Start Date",
    "Actual Start Date",
    "Planned End Date",
    "Actual End Date",
    "Status",
    "Risks",
    "Mitigation Plan",
    "Comments",
]


@st.cache_data(show_spinner=False)
def load_product_sheets(file_path: str) -> dict[str, pd.DataFrame]:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Product status workbook not found: {path}")

    workbook = pd.ExcelFile(path, engine="openpyxl")
    products = {}
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        frame.columns = [str(column).strip() for column in frame.columns]
        for column in REQUIRED_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        frame = frame[REQUIRED_COLUMNS].copy()
        frame = frame.dropna(how="all")
        frame["Activities"] = frame["Activities"].fillna("").astype(str).str.strip()
        frame = frame[frame["Activities"].ne("")].copy()
        products[sheet_name] = frame.reset_index(drop=True)
    return products


def normalize_status(value: object) -> str:
    status = str(value).strip().casefold()
    for expected in STATUS_ORDER:
        if status == expected.casefold():
            return expected
    return ""


def normalize_progress(value: object) -> float:
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, str):
        text = value.strip().replace("%", "")
        try:
            number = float(text)
        except ValueError:
            return 0.0
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
    if number <= 1:
        number *= 100
    return max(0.0, min(100.0, number))


def _priority(value: object) -> str:
    text = str(value).strip().upper()
    return text if text.startswith("P") else ""


def calculate_overall_status(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "NA"

    priorities = frame["Priority"].map(_priority)
    statuses = frame["Status"].map(normalize_status)
    p1_red = (priorities.eq("P1") & statuses.eq("Red")).any()
    p1_amber = (priorities.eq("P1") & statuses.eq("Amber")).any()
    p2_red = (priorities.eq("P2") & statuses.eq("Red")).any()
    p2_amber_count = int((priorities.eq("P2") & statuses.eq("Amber")).sum())
    p3_red = (priorities.eq("P3") & statuses.eq("Red")).any()

    if p1_red:
        return "Red"
    if p1_amber or p2_red or p2_amber_count >= 2 or p3_red:
        return "Amber"
    return "Green"


def summarize_product(frame: pd.DataFrame) -> dict[str, object]:
    status_counts = frame["Status"].map(normalize_status).value_counts()
    return {
        "Green": int(status_counts.get("Green", 0)),
        "Amber": int(status_counts.get("Amber", 0)),
        "Red": int(status_counts.get("Red", 0)),
        "Overall": calculate_overall_status(frame),
    }


def _format_date(value: object) -> str:
    if pd.isna(value) or str(value).strip() in {"", "NaT", "nan"}:
        return "Not planned"
    parsed = pd.to_datetime(value, errors="coerce")
    return "Not planned" if pd.isna(parsed) else parsed.strftime("%d %b %y")


def _status_badge(status: str) -> str:
    class_name = status.casefold() if status in STATUS_ORDER else "na"
    return f"<span class='status-badge {class_name}'>{status.upper() if status else 'NA'}</span>"


def _count_badge(status: str, count: int) -> str:
    return f"<span class='count-badge {status.casefold()}' aria-label='{status} status'>{count}</span>"


def _detail_value(label: str, value: str) -> str:
    return (
        f"<div class='detail-field'><div class='detail-label'>{label}</div>"
        f"<div class='detail-value'>{value}</div></div>"
    )


@st.dialog("Activity progress", width="large")
def show_product_details(product_name: str, frame: pd.DataFrame) -> None:
    st.markdown(
        f"<div class='dialog-product-title'>{product_name} - Activity Progress</div>",
        unsafe_allow_html=True,
    )
    for row_index, (_, row) in enumerate(frame.iterrows()):
        progress = normalize_progress(row["% Completed"])
        status = normalize_status(row["Status"])
        with st.container(key=f"activity-detail-{product_name}-{row_index}"):
            activity_column, owner_column, priority_column, date_column, status_column = st.columns(
                [3.2, 1.05, 0.5, 0.9, 0.7],
                gap="xsmall",
                vertical_alignment="center",
            )
            with activity_column:
                st.markdown(
                    f"<div class='activity-name'>{row['Activities']} -- {progress:.0f}%</div>",
                    unsafe_allow_html=True,
                )
                st.progress(progress / 100)
            with owner_column:
                st.markdown(_detail_value("Owner", str(row["Owner"]).strip() or "Unassigned"), unsafe_allow_html=True)
            with priority_column:
                st.markdown(_detail_value("Priority", _priority(row["Priority"]) or "NA"), unsafe_allow_html=True)
            with date_column:
                st.markdown(_detail_value("Planned start", _format_date(row["Planned Start Date"])), unsafe_allow_html=True)
            with status_column:
                st.markdown(_detail_value("Status", _status_badge(status)), unsafe_allow_html=True)


def _render_styles() -> None:
    st.markdown(
        """
        <style>
        .delivery-title { color: #173c43; font-size: 1.45rem !important; font-weight: 750; margin: 0.1rem 0 0.7rem; }
        .dialog-product-title { color: #173c43; font-size: 1rem; font-weight: 700; line-height: 1.15; margin: 0 0 0.35rem; }
        [class*="st-key-delivery-card-"] { background: #f5faf9; border: 1px solid #cfe3df; border-top: 3px solid #8fcfc8; border-radius: 8px; min-height: 190px; padding: 0.55rem 0.65rem; }
        .delivery-card-title { border-bottom: 1px solid #dce9e6; color: #173c43; font-size: 0.98rem; font-weight: 700; margin-bottom: 0.7rem; padding-bottom: 0.45rem; }
        .count-badge-row { display: flex; gap: 0.5rem; justify-content: center; margin: 0.2rem 0 0.75rem; }
        .count-badge { align-items: center; border-radius: 7px; display: flex; font-size: 1rem; font-weight: 700; height: 2rem; justify-content: center; width: 2.35rem; }
        .count-badge.green { background: #e5f3e8; color: #327044; }
        .count-badge.amber { background: #fff3d8; color: #936d1a; }
        .count-badge.red { background: #fbe5e5; color: #a94343; }
        .status-row { align-items: center; display: flex; justify-content: space-between; padding: 0.16rem 0; }
        .status-label { color: #526b70; font-size: 0.76rem; font-weight: 650; }
        .status-badge { border-radius: 999px; display: inline-block; font-size: 0.96rem; font-weight: 800; letter-spacing: 0.05em; padding: 0.2rem 0.5rem; }
        .status-badge.green { background: #e5f3e8; color: #327044; }
        .status-badge.amber { background: #fff3d8; color: #936d1a; }
        .status-badge.red { background: #fbe5e5; color: #a94343; }
        .status-badge.na { background: #edf1f2; color: #65727d; }
        .overall-row { border-top: 1px solid #e1e9e8; margin-top: 0.35rem; padding-top: 0.45rem; }
        .overall-row .status-label { font-size: 0.7rem; font-weight: 700; }
        .activity-name { color: #173c43; font-size: 0.8rem; font-weight: 650; line-height: 1.15; }
        .detail-field { min-height: 2.15rem; padding-top: 0.05rem; }
        .detail-label { color: #718286; font-size: 0.62rem; font-weight: 700; line-height: 1; margin-bottom: 0.22rem; }
        .detail-value { color: #26383d; font-size: 0.76rem; font-weight: 650; line-height: 1.15; white-space: nowrap; }
        [class*="st-key-activity-detail-"] { background: #fbfdfd; border: 2px solid #dfe9e7; border-radius: 6px; margin: 0 auto 0.25rem; max-width: 98%; padding: 0.28rem 0.56rem; }
        [class*="st-key-activity-detail-"] [data-testid="stHorizontalBlock"] { gap: 0.44rem; }
        [class*="st-key-activity-detail-"] [data-testid="stVerticalBlock"] { gap: 0.23rem; }
        [class*="st-key-activity-detail-"] [data-testid="stCaptionContainer"] { font-size: 0.62rem; margin-bottom: 0.05rem; }
        [class*="st-key-activity-detail-"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0.05rem; }
        [class*="st-key-activity-detail-"] [data-testid="stProgress"] { margin: 0.125rem 0 0; max-width: 90%; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_project_delivery_status(file_path: str) -> None:
    _render_styles()
    products = load_product_sheets(file_path)
    st.markdown("<h1 class='delivery-title'>SWA Product Delivery Health</h1>", unsafe_allow_html=True)

    product_names = list(products)
    for start in range(0, len(product_names), 3):
        columns = st.columns(3, gap="medium")
        for card_index, (column, product_name) in enumerate(zip(columns, product_names[start : start + 3])):
            with column:
                frame = products[product_name]
                summary = summarize_product(frame)
                with st.container(key=f"delivery-card-{start + card_index}", border=True):
                    st.markdown(f"<div class='delivery-card-title'>{product_name}</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div class='count-badge-row'>"
                        + "".join(_count_badge(status, summary[status]) for status in STATUS_ORDER)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='status-row overall-row'><span class='status-label'>Overall</span>{_status_badge(summary['Overall'])}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("View details", key=f"delivery_details_{product_name}", width="stretch"):
                        show_product_details(product_name, frame)
