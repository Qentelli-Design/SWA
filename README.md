# SWA Workforce & Project Dashboard

A Streamlit dashboard for workforce, skills, project delivery, releases, risks, and SharePoint links.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Project layout

```text
app.py        Streamlit entry point
assets/       Dashboard images
css/          Application and page stylesheets
excel/        Source workbooks
src/          Page and application Python modules
src/common/   Shared Python helpers
```

## Workbooks

- `excel/CCC_Resources.xlsx`: Billability, Team Structure, ORG Structure, and Quick Links. Quick Links uses the `Sharepoint links` sheet with `Folder or File name` and `Link` columns; each Link cell needs an Excel hyperlink target.
- `excel/CCC_Resource_Skillset.xlsx`: Skills, with `Resource List` and `Skill Categories` sheets.
- `excel/Product_Status_Report.xlsx`: Project Delivery Status, Releases/Milestones, and Risks. These views read product worksheets from this workbook.

The dashboard also reads `assets/Qentelli.jpg` and `assets/swa.jpg` when present.

Set `CCC_RESOURCES_FILE_PATH`, `ORG_STRUCTURE_FILE_PATH`, `PROJECT_DELIVERY_STATUS_FILE_PATH`, or `CCC_RESOURCE_SKILLSET_FILE_PATH` to override the default workbook paths. Set `SWA_BRAND_IMAGE_PATH` or `SWA_IMAGE_PATH` to override image paths.

## Deploy

Keep the Streamlit entry point `app.py` at the repository root, other Python modules in `src/`, workbooks in `excel/`, images in `assets/`, and stylesheets in `css/`. In Streamlit Community Cloud, set the main file to `app.py`. Confirm company data is approved for hosting before publishing workbooks.
