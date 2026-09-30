"""Workbook loading helpers shared by dashboard sections."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

RESOURCE_LIST_SHEET = "Resource List"
CACHE_TTL = "30m"


def require_workbook(file_path: str, message: str) -> Path:
    """Return an existing workbook path or raise ``FileNotFoundError``."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(message.format(path=path))
    return path


def workbook_token(path: Path) -> tuple[str, int, int]:
    """Cache key that changes when the workbook is replaced or edited."""
    stat = path.stat()
    return str(path), stat.st_mtime_ns, stat.st_size


def read_excel_frame(path: Path, sheet_name: str | int) -> pd.DataFrame:
    """Read one worksheet and normalize header whitespace. Not cached."""
    frame = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    if not isinstance(frame, pd.DataFrame):
        raise ValueError(f"Expected a single worksheet, got {type(frame).__name__}.")
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame


def list_sheet_names(path: Path) -> tuple[str, ...]:
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        return tuple(workbook.sheet_names)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=32)
def read_excel_sheet(file_path: str, mtime_ns: int, size: int, sheet_name: str | int) -> pd.DataFrame:
    """Cached worksheet read. ``mtime_ns`` and ``size`` invalidate stale files."""
    del mtime_ns, size
    return read_excel_frame(Path(file_path), sheet_name)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=12)
def cached_sheet_names(file_path: str, mtime_ns: int, size: int) -> tuple[str, ...]:
    del mtime_ns, size
    return list_sheet_names(Path(file_path))


def read_sheet(file_path: str, sheet_name: str | int) -> pd.DataFrame:
    """Read a worksheet, refreshing the cache when the file changes."""
    path = Path(file_path).expanduser()
    resolved, mtime_ns, size = workbook_token(path)
    return read_excel_sheet(resolved, mtime_ns, size, sheet_name)


def sheet_names(file_path: str) -> tuple[str, ...]:
    path = Path(file_path).expanduser()
    resolved, mtime_ns, size = workbook_token(path)
    return cached_sheet_names(resolved, mtime_ns, size)


def read_resource_list(file_path: str) -> pd.DataFrame:
    """Read ``Resource List``, preserving the original missing-sheet error."""
    try:
        return read_sheet(file_path, RESOURCE_LIST_SHEET)
    except ValueError as error:
        raise ValueError(f"The workbook does not contain a '{RESOURCE_LIST_SHEET}' sheet.") from error


def dataframe_to_excel_bytes(frame: pd.DataFrame, sheet_name: str = "Resources") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


_MONTH_NAMES = frozenset(
    {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    }
)
_MISSING_VALUE_TOKENS = frozenset({"na", "n/a", "-", "null", "none", ""})


def _clean_activity_value(value: object) -> float | None:
    """Normalize a monthly cell to a float, or ``None`` for NA/blank/dash markers."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and value.strip().casefold() in _MISSING_VALUE_TOKENS:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_activity_table(path: Path, sheet_name: str, activity_label: str = "Activities") -> pd.DataFrame:
    """Read a month-by-activity table from a BAU-style worksheet.

    Scans for the header row containing ``activity_label``, then reads the
    activity name plus any adjacent month columns beneath it, stopping at the
    first row with a blank activity name. Recognized missing-value tokens
    (NA, N/A, "-", null, blank) are converted to ``None`` rather than zero.
    Reusable across product sheets that follow the same layout (Activities
    column followed by month columns).
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")

    header_row_index: int | None = None
    for index in range(len(raw)):
        row_values = raw.iloc[index].astype(str).str.strip().str.casefold()
        if row_values.eq(activity_label.casefold()).any():
            header_row_index = index
            break
    if header_row_index is None:
        raise ValueError(f"Could not find an '{activity_label}' header in sheet '{sheet_name}'.")

    header = raw.iloc[header_row_index].astype(str).str.strip()
    activity_columns = header.index[header.str.casefold() == activity_label.casefold()]
    if activity_columns.empty:
        raise ValueError(f"Could not find an '{activity_label}' column in sheet '{sheet_name}'.")
    activity_col = activity_columns[0]

    month_columns = [(column, name) for column, name in header.items() if name.casefold() in _MONTH_NAMES]
    if not month_columns:
        raise ValueError(f"No month columns were found next to '{activity_label}' in sheet '{sheet_name}'.")

    records: list[dict[str, object]] = []
    for row_index in range(header_row_index + 1, len(raw)):
        activity_name = raw.iat[row_index, activity_col]
        if pd.isna(activity_name) or not str(activity_name).strip():
            break
        record: dict[str, object] = {"Activity": str(activity_name).strip()}
        for column, month_name in month_columns:
            record[month_name] = _clean_activity_value(raw.iat[row_index, column])
        records.append(record)

    columns = ["Activity"] + [month_name for _, month_name in month_columns]
    return pd.DataFrame(records, columns=columns)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=16)
def _read_activity_table_cached(
    file_path: str, mtime_ns: int, size: int, sheet_name: str, activity_label: str
) -> pd.DataFrame:
    del mtime_ns, size
    return read_activity_table(Path(file_path), sheet_name, activity_label)


def read_activity_sheet(file_path: str, sheet_name: str, activity_label: str = "Activities") -> pd.DataFrame:
    """Cached read of an activity/month table, refreshed when the workbook changes."""
    path = Path(file_path).expanduser()
    resolved, mtime_ns, size = workbook_token(path)
    return _read_activity_table_cached(resolved, mtime_ns, size, sheet_name, activity_label)
