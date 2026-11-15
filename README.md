# SWA Engagement - QMO

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

### Module structure

Each page keeps data logic separate from UI code, and `sections.py` only routes sections to views.

| Area | Data / logic | UI |
|---|---|---|
| Team Structure | `team_data.py` | `team_structure.py` |
| ORG Structure | `org_data.py` | `org_structure.py` |
| Offshore Team Skillset | `skills_data.py` | `skills.py` |
| Risks / Billability | `data_loader.py` | `risks.py`, `billability.py` |
| Project Delivery, Releases, BAU, Quick Links | in the view module | `project_delivery_status.py`, `releases.py`, `bau_performance.py`, `quick_links.py` |

Shared helpers live in `src/common/`: `excel.py` (cached workbook reads), `delivery.py` (status formatting and the stale-activity filter), `charts.py`, `styles.py` (CSS injection) and `text.py` (name matching and text cleanup).

## Workbooks

- `excel/CCC_Resources.xlsx`: Billability, Team Structure, ORG Structure, Attrition, and Quick Links. Attrition reads the `Attrition` sheet and groups records by `Resource Status`. Quick Links uses the `Sharepoint links` sheet with `Folder or File name` and `Link` columns; each Link cell needs an Excel hyperlink target.
- `excel/CCC_Resource_Skillset.xlsx`: Skills, with `Resource List` and `Skill Categories` sheets. The default team-wise view lists products and each resource's skills; the category view provides the existing category and skill drill-down. Resources without a product appear under Unassigned.
- `excel/Product_Status_Report.xlsx`: Project Delivery Status, Releases/Milestones, and Risks. These views read product worksheets from this workbook.
  Product Delivery and Releases/Milestones hide activities that are completed and have an Actual End Date older than 20 days.

The dashboard also reads `assets/Qentelli.jpg` and `assets/swa.jpg` when present.

Team Structure groups product resources by the `Resource List` sheet's `Portfolio` column:
`CCC` appears under C&C, `Concourse` under Concourse, and all other values under C360 and
Other Products. Product details contain only rows from the selected group; the summary and
C&C leadership remain overall.
Product Delivery Structure displays names from `Qentelli Mail ID`, replacing dots with spaces
and capitalizing each part. When an email is unavailable, the existing name is retained; the
leadership root remains unchanged because it is not a resource row in the workbook.
Use **Show XID** in the sidebar to display each product team's `XID` from
`Resource List`; missing IDs appear as `NA`. The C&C leadership chart does not show XIDs.

ORG Structure shows the reporting tree below Siva Rao Kompella S V. Reporting relationships
that cannot be connected to that tree are shown separately under their listed managers, and
resources with no reporting manager are listed separately. Rebadge resources remain excluded.

Set `CCC_RESOURCES_FILE_PATH`, `ORG_STRUCTURE_FILE_PATH`, `PROJECT_DELIVERY_STATUS_FILE_PATH`, or `CCC_RESOURCE_SKILLSET_FILE_PATH` to override the default workbook paths. Set `SWA_BRAND_IMAGE_PATH` or `SWA_IMAGE_PATH` to override image paths.

## Deploy

Keep the Streamlit entry point `app.py` at the repository root, other Python modules in `src/`, workbooks in `excel/`, images in `assets/`, and stylesheets in `css/`. In Streamlit Community Cloud, set the main file to `app.py`. Confirm company data is approved for hosting before publishing workbooks.
