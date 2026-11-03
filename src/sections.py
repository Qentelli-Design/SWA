"""Section dispatch. Each view lives in its own module; this file only routes."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from attrition import render_attrition
from bau_performance import render_bau_performance
from billability import render_billability
from common.excel import DATA_ERRORS
from config import (
    BAU_PERFORMANCE_FILE_PATH,
    CCC_RESOURCE_SKILLSET_FILE_PATH,
    CCC_RESOURCES_FILE_PATH,
    ORG_STRUCTURE_FILE_PATH,
    PROJECT_DELIVERY_STATUS_FILE_PATH,
)
from org_structure import render_org_structure
from project_delivery_status import render_project_delivery_status
from quick_links import render_quick_links
from releases import render_releases
from risks import render_risks
from skills import render_skills
from team_structure import render_team_structure

ViewRenderer = Callable[[str], None]


def _guarded(render: ViewRenderer, file_path: str) -> Callable[[], None]:
    """Show workbook/data errors inline instead of a stack trace."""

    def _run() -> None:
        try:
            render(file_path)
        except DATA_ERRORS as error:
            st.error(str(error))

    return _run


_HANDLERS: dict[str, Callable[[], None]] = {
    "Billability": _guarded(render_billability, CCC_RESOURCES_FILE_PATH),
    "Team Structure": _guarded(render_team_structure, CCC_RESOURCES_FILE_PATH),
    "ORG Structure": _guarded(render_org_structure, ORG_STRUCTURE_FILE_PATH),
    "Attrition": _guarded(render_attrition, CCC_RESOURCES_FILE_PATH),
    "Project Delivery Status": _guarded(render_project_delivery_status, PROJECT_DELIVERY_STATUS_FILE_PATH),
    "Releases/Milestones": _guarded(render_releases, PROJECT_DELIVERY_STATUS_FILE_PATH),
    # The risks view reports its own load errors and leaves rendering errors unhandled.
    "Risks": lambda: render_risks(PROJECT_DELIVERY_STATUS_FILE_PATH),
    "Offshore Team Skillset": _guarded(render_skills, CCC_RESOURCE_SKILLSET_FILE_PATH),
    "Quick Links": _guarded(render_quick_links, CCC_RESOURCES_FILE_PATH),
    "BAU Performance": _guarded(render_bau_performance, BAU_PERFORMANCE_FILE_PATH),
}


def render_selected_section(selected_section: str) -> None:
    handler = _HANDLERS.get(selected_section)
    if handler is not None:
        handler()
