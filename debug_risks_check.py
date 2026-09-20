from pathlib import Path
import pandas as pd
from config import PROJECT_DELIVERY_STATUS_FILE_PATH
from data_loader import load_risks_from_product_status, build_risk_summary_from_product_status

p = Path(PROJECT_DELIVERY_STATUS_FILE_PATH)
print('PROJECT_DELIVERY_STATUS_FILE_PATH ->', PROJECT_DELIVERY_STATUS_FILE_PATH)
print('exists:', p.is_file())
if not p.is_file():
    print('ERROR: Product status file not found at path above')
    raise SystemExit(1)

xls = pd.ExcelFile(p, engine='openpyxl')
print('sheets:', xls.sheet_names)
for s in xls.sheet_names:
    df = pd.read_excel(p, sheet_name=s, engine='openpyxl')
    print(f"Sheet: {s} rows={len(df)} cols={len(df.columns)} first_cols={list(df.columns)[:12]}")

details = load_risks_from_product_status(PROJECT_DELIVERY_STATUS_FILE_PATH)
print('\nExtracted risk detail rows:', len(details))
print(details.head(50).to_string(index=False))

summary = build_risk_summary_from_product_status(PROJECT_DELIVERY_STATUS_FILE_PATH)
print('\nRisk summary per product:')
print(summary.to_string(index=False))
