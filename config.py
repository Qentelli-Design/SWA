from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
APP_TITLE = "SWA Workforce & Project Dashboard"
EXCEL_FILE_PATH = os.getenv("SWA_EXCEL_FILE_PATH", str(BASE_DIR / "SWA Consolidated sheet.xlsx"))
CCC_RESOURCES_FILE_PATH = os.getenv("CCC_RESOURCES_FILE_PATH", str(BASE_DIR / "CCC_Resources.xlsx"))
ORG_STRUCTURE_FILE_PATH = os.getenv("ORG_STRUCTURE_FILE_PATH", str(BASE_DIR / "CCC_Resources.xlsx"))
BRAND_IMAGE_PATH = Path(os.getenv("SWA_BRAND_IMAGE_PATH", str(BASE_DIR / "Qentelli.jpg")))
SWA_IMAGE_PATH = Path(os.getenv("SWA_IMAGE_PATH", str(BASE_DIR / "swa.jpg")))
RISK_TRACKER_FILE_PATH = os.getenv("SWA_RISK_TRACKER_FILE_PATH", str(BASE_DIR / "Risk_Tracker.xlsx"))
