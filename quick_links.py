"""Quick links loaded from the CCC resources workbook."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st
from openpyxl import load_workbook

from common.excel import CACHE_TTL, require_workbook, workbook_token
from config import CCC_RESOURCES_FILE_PATH

SHEET_NAME = "Sharepoint links"
REQUIRED_COLUMNS = ("Folder or File name", "Link")


def load_quick_links(file_path: str = CCC_RESOURCES_FILE_PATH) -> list[dict[str, str]]:
    """Load named external links from the workbook's Sharepoint links sheet."""
    path = require_workbook(file_path, "Resources workbook not found: {path}")
    resolved, mtime_ns, size = workbook_token(path)
    return _load_quick_links(resolved, mtime_ns, size)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=8)
def _load_quick_links(file_path: str, mtime_ns: int, size: int) -> list[dict[str, str]]:
    del mtime_ns, size
    workbook = load_workbook(file_path, read_only=False, data_only=False)
    try:
        sheet_name = next(
            (name for name in workbook.sheetnames if name.strip().casefold() == SHEET_NAME.casefold()),
            None,
        )
        if sheet_name is None:
            raise ValueError(f"The workbook must contain a '{SHEET_NAME}' sheet.")

        sheet = workbook[sheet_name]
        headers = {
            str(cell.value).strip().casefold(): index
            for index, cell in enumerate(sheet[1])
            if cell.value is not None
        }
        missing = [column for column in REQUIRED_COLUMNS if column.casefold() not in headers]
        if missing:
            raise ValueError(f"The '{SHEET_NAME}' sheet must contain columns: {', '.join(REQUIRED_COLUMNS)}.")

        name_column = headers[REQUIRED_COLUMNS[0].casefold()]
        link_column = headers[REQUIRED_COLUMNS[1].casefold()]
        links: list[dict[str, str]] = []
        for row in sheet.iter_rows(min_row=2):
            name_value = row[name_column].value
            link_cell = row[link_column]
            link_name_value = link_cell.value
            url_value = link_cell.hyperlink.target if link_cell.hyperlink else link_name_value
            if name_value is None and url_value is None:
                continue

            name = str(name_value or "").strip()
            link_name = str(link_name_value or "").strip()
            url = str(url_value or "").strip()
            if not name or not url:
                continue
            if not link_name:
                link_name = name

            parsed_url = urlsplit(url)
            if parsed_url.scheme.casefold() not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError(f"Quick link '{name}' must have a valid HTTP or HTTPS destination.")
            links.append({"name": name, "link_name": link_name, "url": url})

        return links
    finally:
        workbook.close()


def render_quick_links(file_path: str = CCC_RESOURCES_FILE_PATH) -> None:
    """Render each workbook entry as a named, clickable quick link."""
    links = load_quick_links(file_path)
    if not links:
        st.info(f"No quick links found in the '{SHEET_NAME}' sheet.")
        return

    for index, link in enumerate(links):
        with st.container(key=f"quick-link-{index}", border=True):
            name_column, link_column = st.columns([1, 2], vertical_alignment="center")
            with name_column:
                st.markdown(f"**{link['name']}**")
            with link_column:
                st.link_button(link["link_name"], link["url"], width="stretch")
