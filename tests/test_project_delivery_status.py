import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import project_delivery_status
from project_delivery_status import format_progress, load_delivery_activities, select_portfolio


class ProjectDeliveryStatusTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "status.xlsx"
        self.write_workbook()

    def write_workbook(self, missing_column=None):
        ccc = pd.DataFrame([
            (" CCC ", "Shared", "Release 1", 0.88, "On Track", " Yes "),
            ("ccc", "Shared", "Release 2", "26%", "At Risk", "No"),
            ("C360", "Shared", "Release 3", None, "", ""),
            ("FSSR", "FSSR", "Release 4", 1, "Delayed", "yes"),
            ("AIS", "AIS", "Release 5", 0, "On Track", "No"),
            ("", "", "Release 6", "", "", ""),
        ], columns=["Portfolio", "Team", "Activity / Project", "Progress (Source)",
                    "Status (Source)", "Lead Confirms Risk? (Yes/No)"])
        concourse = pd.DataFrame([
            ("Concourse", "Concourse", "Release 7", 0.2, "On Track", "YES"),
        ], columns=ccc.columns)
        if missing_column:
            ccc = ccc.drop(columns=[missing_column])
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            ccc.to_excel(writer, sheet_name="CCC", index=False)
            concourse.to_excel(writer, sheet_name="Concourse", index=False)

    def test_grouping_uses_portfolio_values_and_preserves_every_activity(self):
        frame = load_delivery_activities(str(self.path))
        groups = [select_portfolio(frame, name) for name in ("C&C", "C360 and Other Products", "Concourse")]
        self.assertEqual([len(group) for group in groups], [2, 4, 1])
        self.assertEqual(groups[0]["Status (Source)"].tolist(), ["On Track", "At Risk"])
        self.assertEqual(groups[1]["Portfolio"].tolist(), ["C360", "FSSR", "AIS", ""])
        self.assertEqual(groups[2]["Activity / Project"].tolist(), ["Release 7"])
        with self.assertRaisesRegex(ValueError, "Unknown portfolio"):
            select_portfolio(frame, "Unknown")

    def test_missing_columns_and_workbook_are_reported(self):
        self.write_workbook(missing_column="Status (Source)")
        with self.assertRaisesRegex(ValueError, "CCC.*Status \\(Source\\)"):
            load_delivery_activities(str(self.path))
        with self.assertRaisesRegex(FileNotFoundError, "Product status workbook not found"):
            load_delivery_activities(str(self.path.parent / "missing.xlsx"))

    def test_processed_data_is_cached_and_refreshed_when_workbook_changes(self):
        with patch.object(project_delivery_status, "read_sheet", wraps=project_delivery_status.read_sheet) as reader:
            frame = load_delivery_activities(str(self.path))
            frame.loc[0, "Team"] = "Changed locally"
            self.assertEqual(load_delivery_activities(str(self.path)).loc[0, "Team"], "Shared")
            self.assertEqual(reader.call_count, 2)
            self.write_workbook(missing_column="Status (Source)")
            with self.assertRaisesRegex(ValueError, "CCC.*Status \\(Source\\)"):
                load_delivery_activities(str(self.path))

    def test_progress_values_are_not_silently_zeroed(self):
        for value, expected in [(0.88, "88%"), (1, "100%"), (0, "0%"), (25, "25%"),
                                ("26%", "26%"), (None, ""), ("Unknown", "Unknown")]:
            with self.subTest(value=value):
                self.assertEqual(format_progress(value), expected)

    def test_details_show_only_team_activity_and_progress_with_risk_highlighting(self):
        app = AppTest.from_string(
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        app.button(key="delivery_section_Active Releases").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any("SWA delivery overview" in item.value for item in app.markdown))
        self.assertFalse(any("Explore release activities and confirmed risks by portfolio and team."
                             in item.value for item in app.caption))
        self.assertEqual([app.button(key=f"delivery_portfolio_{index}").label for index in range(3)],
                         ["C&C", "C360 and Other Products", "Concourse"])
        self.assertEqual([app.button(key=f"delivery_portfolio_{index}").proto.type for index in range(3)],
                         ["primary", "secondary", "secondary"])
        self.assertFalse(app.tabs)
        self.assertFalse(any(caption.value.startswith("Portfolio:") for caption in app.caption))
        self.assertEqual(app.button(key="delivery_view_all_0").label, "View all releases (2)")
        button_keys = [button.key for button in app.button]
        self.assertLess(button_keys.index("delivery_view_all_0"), button_keys.index("delivery_portfolio_0"))
        self.assertLess(button_keys.index("delivery_portfolio_2"), button_keys.index("delivery_details_0_0"))
        card_summaries = "\n".join(item.value for item in app.markdown)
        self.assertIn("delivery-divider delivery-portfolio-divider", card_summaries)
        self.assertIn("<strong>2</strong> Releases", card_summaries)
        self.assertIn("<strong>1</strong> Risks", card_summaries)
        self.assertIn("delivery-summary-count delivery-risk-count", card_summaries)
        app.button(key="delivery_details_0_0").click().run()
        self.assertFalse(app.exception)
        self.assertIn("Confirmed risks are highlighted in red.", [item.value for item in app.caption])
        ccc = app.dataframe[0].value
        self.assertEqual(ccc.to_dict("records"), [
            {"Product": "Shared", "Release": "Release 1", "Progress": "88%"},
            {"Product": "Shared", "Release": "Release 2", "Progress": "26%"},
        ])
        styles = app.dataframe[0].proto.arrow_data.styler.styles
        self.assertIn("background-color: #fbe5e5", styles)
        self.assertIn("row0_col0", styles)
        self.assertNotIn("row1_col0", styles)
        other = AppTest.from_string(
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()
        other.button(key="delivery_section_Active Releases").click().run()
        other.button(key="delivery_portfolio_1").click().run()
        other_cards = "\n".join(item.value for item in other.markdown)
        self.assertIn("<strong>0</strong> Risks", other_cards)
        self.assertIn("delivery-summary-count delivery-risk-count delivery-risk-none", other_cards)
        other.button(key="delivery_view_all_1").click().run()
        self.assertFalse(other.exception)
        rows = other.dataframe[0].value.to_dict("records")
        self.assertEqual(len(rows), 4)
        self.assertEqual(list(other.dataframe[0].value.columns), ["Product", "Release", "Progress"])
        self.assertEqual(rows[0]["Progress"], "Not available")
        self.assertEqual(rows[1]["Progress"], "100%")
        self.assertIn("row1_col0", other.dataframe[0].proto.arrow_data.styler.styles)
        self.assertNotIn("row0_col0", other.dataframe[0].proto.arrow_data.styler.styles)

        concourse = AppTest.from_string(
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()
        concourse.button(key="delivery_section_Active Releases").click().run()
        concourse.button(key="delivery_portfolio_2").click().run()
        self.assertEqual([concourse.button(key=f"delivery_portfolio_{index}").proto.type for index in range(3)],
                         ["secondary", "secondary", "primary"])
        self.assertEqual(concourse.button(key="delivery_view_all_2").label, "View all releases (1)")
        concourse.button(key="delivery_portfolio_0").click().run()
        self.assertEqual(concourse.button(key="delivery_view_all_0").label, "View all releases (2)")
        concourse.button(key="delivery_portfolio_2").click().run()
        concourse.button(key="delivery_details_2_0").click().run()
        self.assertFalse(concourse.exception)
        self.assertEqual(list(concourse.dataframe[0].value.columns), ["Product", "Release", "Progress"])
        self.assertEqual(concourse.dataframe[0].value.iloc[0]["Release"], "Release 7")
        self.assertIn("row0_col0", concourse.dataframe[0].proto.arrow_data.styler.styles)

        concourse.button(key="delivery_back").click().run()
        concourse.button(key="delivery_section_Active Releases").click().run()
        self.assertEqual(concourse.button(key="delivery_portfolio_0").proto.type, "primary")

    def test_empty_group_shows_message(self):
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            columns = ["Portfolio", "Team", "Activity / Project", "Progress (Source)",
                       "Status (Source)", "Lead Confirms Risk? (Yes/No)"]
            pd.DataFrame([("CCC", "Team", "Release", 0.5, "On Track", "No")], columns=columns).to_excel(
                writer, sheet_name="CCC", index=False
            )
            pd.DataFrame(columns=columns).to_excel(writer, sheet_name="Concourse", index=False)
        app = AppTest.from_string(
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        app.button(key="delivery_section_Active Releases").click().run()
        app.button(key="delivery_portfolio_2").click().run()
        self.assertEqual(app.info[0].value, "No activities found for this portfolio.")

    def test_delivery_sections_are_dynamic_and_placeholders_do_not_load_workbook(self):
        app = AppTest.from_string(
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path.parent / "missing.xlsx")!r})
"""
        ).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Project Delivery Status</h1>" in item.value for item in app.markdown))
        self.assertEqual([button.label for button in app.button], ["Active Releases", "Risks", "Governance"])
        self.assertEqual([button.proto.type for button in app.button], ["secondary"] * 3)
        self.assertFalse(app.error)
        self.assertFalse(app.tabs)
        self.assertFalse(any("SWA Product Delivery Health" in item.value for item in app.markdown))
        app.button(key="delivery_section_Governance").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.button(key="delivery_section_Governance").proto.type, "primary")
        self.assertEqual(app.info[0].value, "Governance details will be added later.")
        app.button(key="delivery_section_Active Releases").click().run()
        self.assertIn("Product status workbook not found", app.error[0].value)
        self.assertTrue(any("SWA Product Delivery Health" in item.value for item in app.markdown))
        self.assertFalse(any("Project Delivery Status</h1>" in item.value for item in app.markdown))
        app.button(key="delivery_back").click().run()
        self.assertFalse(app.error)
        self.assertTrue(any("Project Delivery Status</h1>" in item.value for item in app.markdown))
        self.assertEqual([button.label for button in app.button], ["Active Releases", "Risks", "Governance"])

    def test_downloads_are_scoped_to_each_portfolio(self):
        app = AppTest.from_string(
            f"""
import sys
from pathlib import Path
from unittest.mock import patch
import streamlit as st
sys.path.insert(0, str(Path.cwd() / "src"))
from project_delivery_status import render_project_delivery_status
downloads = []
def capture_download(label, data, **kwargs):
    downloads.append((kwargs["key"], data))
with patch.object(st, "download_button", side_effect=capture_download):
    render_project_delivery_status({str(self.path)!r})
st.session_state["downloads"] = downloads
"""
        ).run()
        app.button(key="delivery_section_Active Releases").click().run()
        self.assertFalse(app.exception)
        for index, expected in enumerate((["Release 1", "Release 2"],
                                           ["Release 3", "Release 4", "Release 5", "Release 6"],
                                           ["Release 7"])):
            with self.subTest(portfolio=index):
                if index:
                    app.button(key=f"delivery_portfolio_{index}").click().run()
                downloads = dict(app.session_state["downloads"])
                self.assertEqual(list(downloads), [f"delivery_download_{index}"])
                frame = pd.read_csv(BytesIO(downloads[f"delivery_download_{index}"]))
                self.assertEqual(frame["Release"].tolist(), expected)
                self.assertTrue({"Product", "Release", "Progress"}.issubset(frame.columns))
                if index == 0:
                    self.assertEqual(frame["Portfolio"].tolist(), ["C&C", "C&C"])

    def test_existing_ccc_selection_is_migrated(self):
        app = AppTest.from_string(
            f"""
import sys
import streamlit as st
sys.path.insert(0, 'src')
from project_delivery_status import render_active_releases
st.session_state["delivery_selected_portfolio"] = "CCC"
render_active_releases({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["delivery_selected_portfolio"], "C&C")
        self.assertEqual(app.button(key="delivery_view_all_0").label, "View all releases (2)")
