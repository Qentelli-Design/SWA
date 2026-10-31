"""Status formatting shared by delivery health and release views."""

from __future__ import annotations

from html import escape

import pandas as pd

from common.styles import inject_css
from common.text import strip_format_characters

STATUS_ORDER = ("Green", "Amber", "Red")


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


_COMPLETED_STATUS_TOKENS = frozenset({"complete", "completed", "done", "closed"})


def is_completed_activity(progress: object, status: object = "") -> bool:
    status_text = str(status).strip().casefold()
    if status_text in _COMPLETED_STATUS_TOKENS:
        return True
    return normalize_progress(progress) >= 100.0


def is_stale_completed_activity(
    progress: object,
    completion_date: object,
    *,
    status: object = "",
    grace_days: int = 20,
) -> bool:
    if not is_completed_activity(progress, status):
        return False
    if pd.isna(completion_date) or str(completion_date).strip() in {"", "NaT", "nan"}:
        return False
    value: object = completion_date
    if isinstance(value, str):
        value = strip_format_characters(value)
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return False
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=grace_days)
    return parsed.normalize() < cutoff


def exclude_stale_completed(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop completed activities whose actual end date is older than the grace period."""
    if frame.empty:
        return frame
    stale_mask = frame.apply(
        lambda row: is_stale_completed_activity(
            row.get("% Completed", ""),
            row.get("Actual End Date", ""),
            status=row.get("Status", ""),
        ),
        axis=1,
    )
    return frame.loc[~stale_mask].reset_index(drop=True)


def format_date(value: object) -> str:
    if pd.isna(value) or str(value).strip() in {"", "NaT", "nan"}:
        return "Not planned"
    if isinstance(value, str):
        value = strip_format_characters(value)
    parsed = pd.to_datetime(value, errors="coerce")
    return "Not planned" if pd.isna(parsed) else parsed.strftime("%d %b %y")


def format_actual_date(value: object) -> str:
    formatted = format_date(value)
    return "Not available" if formatted == "Not planned" else formatted


def status_badge(status: str) -> str:
    class_name = status.casefold() if status in STATUS_ORDER else "na"
    label = status.upper() if status else "NA"
    return f"<span class='status-badge {class_name}'>{label}</span>"


def count_badge(status: str, count: int) -> str:
    return (
        f"<span class='count-badge {status.casefold()}' aria-label='{escape(status)} status'>"
        f"{int(count)}</span>"
    )


def detail_value(label: str, value: object, *, html: bool = False) -> str:
    """Render a compact label/value pair. Escape text unless ``html`` is trusted markup."""
    display: object = value
    try:
        missing = bool(pd.isna(value)) or str(value).strip().lower() in {"", "nan", "nat"}
    except (TypeError, ValueError):
        missing = value in (None, "")
    if missing:
        display = "Not available"
        html = False
    rendered = str(display) if html else escape(str(display))
    return (
        f"<div class='detail-field'><div class='detail-label'>{escape(label)}</div>"
        f"<div class='detail-value'>{rendered}</div></div>"
    )


def render_delivery_styles() -> None:
    inject_css("delivery.css")
