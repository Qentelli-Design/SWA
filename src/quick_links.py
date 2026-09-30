"""Quick links loaded from the CCC resources workbook."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

import streamlit as st
from openpyxl import load_workbook

from common.excel import CACHE_TTL, require_workbook, workbook_token
from common.styles import inject_css
from config import CCC_RESOURCES_FILE_PATH

SHEET_NAME = "Sharepoint links"
REQUIRED_COLUMNS = ("Folder or File name", "Link")
_QUICK_LINK_FEEDBACK_KEY = "quick_link_feedback"


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


def add_quick_link(file_path: str, name: str, link_name: str, url: str) -> bool:
    """Append a named hyperlink to the workbook; return False for exact duplicates."""
    name = name.strip()
    link_name = link_name.strip() or name
    url = url.strip()
    if not name:
        raise ValueError("Enter a folder or file name.")
    if not url:
        raise ValueError("Enter a link URL.")

    parsed_url = urlsplit(url)
    if parsed_url.scheme.casefold() not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Enter a valid HTTP or HTTPS URL.")

    path = require_workbook(file_path, "Resources workbook not found: {path}")
    workbook = load_workbook(path, read_only=False, data_only=False)
    temporary_path: Path | None = None
    try:
        sheet_name = next(
            (sheet for sheet in workbook.sheetnames if sheet.strip().casefold() == SHEET_NAME.casefold()),
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
        if any(column.casefold() not in headers for column in REQUIRED_COLUMNS):
            raise ValueError(
                f"The '{SHEET_NAME}' sheet must contain columns: {', '.join(REQUIRED_COLUMNS)}."
            )

        name_column = headers[REQUIRED_COLUMNS[0].casefold()] + 1
        link_column = headers[REQUIRED_COLUMNS[1].casefold()] + 1
        for row in sheet.iter_rows(min_row=2):
            existing_name = str(row[name_column - 1].value or "").strip()
            link_cell = row[link_column - 1]
            existing_url = link_cell.hyperlink.target if link_cell.hyperlink else str(link_cell.value or "").strip()
            if existing_name.casefold() == name.casefold() and existing_url == url:
                return False

        new_row = sheet.max_row + 1
        sheet.cell(row=new_row, column=name_column, value=name)
        link_cell = sheet.cell(row=new_row, column=link_column, value=link_name)
        link_cell.hyperlink = url

        with NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
        workbook.save(temporary_path)
        workbook.close()
        os.replace(temporary_path, path)
        temporary_path = None
        _load_quick_links.clear()
        return True
    except PermissionError as error:
        raise ValueError("Could not save the workbook. Close it in Excel and try again.") from error
    finally:
        workbook.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def render_quick_links(file_path: str = CCC_RESOURCES_FILE_PATH) -> None:
    """Render current links and a form for adding links in separate tabs."""
    inject_css("quick_links.css")
    links = load_quick_links(file_path)
    feedback = st.session_state.pop(_QUICK_LINK_FEEDBACK_KEY, None)

    with st.container(key="quick-links-view"):
        current_tab, add_tab = st.tabs([f"Current links ({len(links)})", "Add a link"])

        with current_tab:
            if feedback:
                st.success(feedback)
            if not links:
                st.info(f"No quick links found in the '{SHEET_NAME}' sheet.")
            else:
                for index, link in enumerate(links):
                    with st.container(key=f"quick-link-row-{index}", border=True):
                        name_column, action_column = st.columns([3, 1], vertical_alignment="center")
                        with name_column:
                            st.markdown(f"**{link['name']}**")
                            st.caption(link["link_name"])
                        with action_column:
                            st.link_button("Open link", link["url"], width="stretch")

        with add_tab:
            with st.container(key="quick-links-form"):
                with st.form("add_quick_link", clear_on_submit=True):
                    name_column, label_column = st.columns(2)
                    with name_column:
                        name = st.text_input("Folder or file name")
                    with label_column:
                        link_name = st.text_input(
                            "Link label",
                            help="Defaults to the folder or file name when left blank.",
                        )
                    url = st.text_input("Link URL", placeholder="https://...")
                    submitted = st.form_submit_button("Add link", type="primary")

            if submitted:
                try:
                    added = add_quick_link(file_path, name, link_name, url)
                except (FileNotFoundError, OSError, ValueError) as error:
                    st.error(str(error))
                else:
                    if added:
                        st.session_state[_QUICK_LINK_FEEDBACK_KEY] = "Quick link added."
                        st.rerun()
                    st.info("That quick link is already in the workbook.")
