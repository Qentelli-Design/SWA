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
