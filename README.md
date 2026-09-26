# SWA_1
SWA Project Status
# SWA Workforce Dashboard

A focused Streamlit dashboard that reads the `Detail1` worksheet and presents workforce planning views.

## Dashboard sections

- `Resource pulse`: Total Resources, Onsite, Offshore, Project, Portfolio, Wave, and OnBoarding Status
- `Billability`: resource counts grouped by the Excel `Billability` column
- `Team structure`
- `ORG Structure`: interactive Reporting Manager to Resource Name hierarchy from `CCC_Resources.xlsx`
- `Skills`
- `Certifications`
- `Project Delivery Status`: dynamic product health cards and activity details from `Product_Status_Report.xlsx`
- `Milestones`
- `Risks`

The last six sections are ready for future Detail1 data additions.
The `Risks` section reads `Risk_Tracker.xlsx`, using the worksheet named exactly `Risk Tracker` and its `Portfolio Component` column. The path can be overridden with `SWA_RISK_TRACKER_FILE_PATH`.

The loader handles the title rows in `Detail1`, finds the row containing `S.No` as the table header, and normalizes location values before calculating counts.

## Install and run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The default paths are repository-relative. Place these files in the project folder when you need the corresponding dashboard sections:

- `CCC_Resources.xlsx` for `Team structure` and its `Resource List` sheet
- `CCC_Resource_Skillset.xlsx` for `Skills`, including `Resource List` and `Skill Categories` sheets
- `Product_Status_Report.xlsx` for `Project Delivery Status`, with one product per sheet
- `SWA Consolidated sheet.xlsx` for the existing `Resource pulse` and `Billability` sections, including `Detail1`
- `Risk_Tracker.xlsx` for the `Risks` section, including `Risk Tracker`
- `Qentelli.jpg` and `swa.jpg` for the optional dashboard images

You can override any path without editing code:

```powershell
$env:SWA_EXCEL_FILE_PATH = 'C:\path\to\workbook.xlsx'
python -m streamlit run app.py
```

## Deploy with GitHub and Streamlit Community Cloud

1. Create a new GitHub repository. Keep it private if the workbooks contain company or personal information.
2. Copy the application files into the repository root: `app.py`, `config.py`, `data_loader.py`, `navigation.py`, `sections.py`, `team_structure.py`, `org_structure.py`, `project_delivery_status.py`, `releases.py`, `skills.py`, the `common` package, `requirements.txt`, and `README.md`.
3. Copy the workbook files required by the sections you want to publish into the same repository folder. The Team structure page requires `CCC_Resources.xlsx`.
4. Do not upload `.venv`, `__pycache__`, passwords, API keys, or unrelated personal files. Add a `.gitignore` before committing.
5. Commit and push the repository to GitHub.
6. Open https://share.streamlit.io/ and sign in with GitHub.
7. Select **Create app**, choose the repository and branch, and set the main file to `app.py`.
8. Choose **Deploy**. Streamlit Cloud installs packages from `requirements.txt` and runs `app.py` on its Linux server.
9. After every GitHub push, Streamlit Cloud normally redeploys automatically. Use **Manage app** if you need to reboot or inspect logs.

Important: Streamlit Cloud cannot read `C:\Users\...` paths from your computer. Files must be committed to GitHub or supplied through Streamlit secrets. Excel workbooks are usually simplest as repository files, but confirm that your organization's data policy allows that.

For a Team structure-only deployment, `CCC_Resources.xlsx` is required, but the current `app.py` also loads `SWA Consolidated sheet.xlsx` at startup. Either include that workbook too, or change the app to lazy-load the legacy sections before deploying.

## Troubleshooting

- File not found: check the configured path or `SWA_EXCEL_FILE_PATH`.
- Missing detail sheet: the application requires a sheet named exactly `Detail1`.
- Refresh after workbook changes: use Streamlit's Rerun option or clear the cache.
