"""Filesystem paths and app constants.

Override any workbook or image with the matching environment variable.
Paths stay strings so existing callers can pass them straight to loaders.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_TITLE = "SWA Workforce & Project Dashboard"


def _env_path(env_name: str, default_name: str) -> str:
    default_path = BASE_DIR / "excel" / default_name
    return str(Path(os.getenv(env_name, str(default_path))).expanduser())


CCC_RESOURCES_FILE_PATH = _env_path("CCC_RESOURCES_FILE_PATH", "CCC_Resources.xlsx")
ORG_STRUCTURE_FILE_PATH = _env_path("ORG_STRUCTURE_FILE_PATH", "CCC_Resources.xlsx")
PROJECT_DELIVERY_STATUS_FILE_PATH = _env_path(
    "PROJECT_DELIVERY_STATUS_FILE_PATH",
    "Product_Status_Report.xlsx",
)
CCC_RESOURCE_SKILLSET_FILE_PATH = _env_path(
    "CCC_RESOURCE_SKILLSET_FILE_PATH",
    "CCC_Resource_Skillset.xlsx",
)
BRAND_IMAGE_PATH = Path(
    os.getenv("SWA_BRAND_IMAGE_PATH", str(BASE_DIR / "assets" / "Qentelli.jpg"))
)
SWA_IMAGE_PATH = Path(os.getenv("SWA_IMAGE_PATH", str(BASE_DIR / "assets" / "swa.jpg")))
