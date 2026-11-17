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
| Risks | in the view module | `risks.py` |
| Billability | `data_loader.py` | `billability.py` |
| Project Delivery, BAU, Quick Links | in the view module | `project_delivery_status.py`, `bau_performance.py`, `quick_links.py` |

Shared helpers live in `src/common/`: `excel.py` (cached workbook reads), `delivery.py` (delivery display labels and styles), `charts.py`, `styles.py` (CSS injection) and `text.py` (name matching and display).

## Workbooks

- `excel/CCC_Resources.xlsx`: Billability, Team Structure, ORG Structure, Attrition, and Quick Links. Billability groups distinct resource names by `Billable`; selecting a bar opens a downloadable list of resource names and products from `Resource List`. A resource with multiple products can appear more than once in the list. Attrition reads the `Attrition` sheet and groups records by `Resource Status`. Quick Links uses the `Sharepoint links` sheet with `Folder or File name` and `Link` columns; each Link cell needs an Excel hyperlink target.
- `excel/CCC_Resource_Skillset.xlsx`: Skills, with `Resource List` and `Skill Categories` sheets. The default team-wise view lists products and each resource's skills; the category view provides the existing category and skill drill-down. Resources without a product appear under Unassigned.
- `excel/Product_Status_Report.xlsx`: Project Delivery Status offers Active Releases, Risks, and a Governance placeholder. Active Releases and Risks open separate views with a back button. Active Releases reads the `CCC` and `Concourse` sheets, groups rows by `Portfolio` and `Team`, and displays Product, Release and Progress; confirmed risks are highlighted red. These labels also appear in related CSV exports, while the workbook retains its original column names. Risks contains Risks and Other Challenges navigation buttons, each limited to rows where `Lead Confirms Risk? (Yes/No)` is Yes. Rows with a populated other-challenge or workaround field appear only in Other Challenges, even if they also contain risk details. Both views show summary counts and a team chart. Selecting a bar opens that team's details: Risks shows Product, Release, description, severity and mitigation; Other Challenges shows Product, challenge and workaround. Missing values are shown as Not provided. The views provide CSV downloads.

The dashboard also reads `assets/Qentelli.jpg` and `assets/swa.jpg` when present.

On the delivery health page, the header actions show and download releases for the selected portfolio.
Risk and challenge team charts use a compact responsive layout; selecting a bar opens the team's details.

Team Structure groups product resources by the `Resource List` sheet's `Portfolio` column:
`CCC` appears under C&C, `Concourse` under Concourse, and all other values under C360 and
Other Products. Product details contain only rows from the selected group; the summary and
C&C leadership remain overall.
The dashboard displays the `CCC` portfolio as C&C, including delivery and attrition views
and delivery CSV exports; workbook sheet names and source values remain unchanged.
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
