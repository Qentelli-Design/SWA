"""Status formatting shared by delivery health and release views."""

from __future__ import annotations

from html import escape
import unicodedata

import pandas as pd

from common.styles import inject_css

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


def format_date(value: object) -> str:
    if pd.isna(value) or str(value).strip() in {"", "NaT", "nan"}:
        return "Not planned"
    if isinstance(value, str):
        value = "".join(character for character in value if unicodedata.category(character) != "Cf").strip()
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
