import sys
import tempfile
import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import risks
from risks import (CHALLENGE_COLUMN, CHALLENGE_COLUMNS, RISK_COLUMNS, WORKAROUND_COLUMN,
                   load_confirmed_risks, load_other_challenges)


class DeliveryRiskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "risk.xlsx"
        self.rows = [
            ("CCC", "Alpha", "Release 1", " Yes ", "<Blocked>", "High", "Retest",
             datetime(2026, 11, 1), "13/11/26", "17/11/26"),
            ("CCC", "Beta", "Release 2", "No", "Excluded", "High", "Fix", "", "", ""),
            ("CCC", "Alpha", "Release 3", "YES", "", "", "", "", "", ""),
            ("CCC", "Gamma", "Release 4", "", "Excluded blank", "", "", "", "", ""),
            ("Concourse", "Concourse", "Release 5", "yes", "Concourse risk", "Medium",
             "Mitigate", "", "", ""),
        ]
        self.write_workbook()

    def write_workbook(self, *, missing=None, empty=False):
        frame = pd.DataFrame([] if empty else self.rows, columns=RISK_COLUMNS)
        frame[CHALLENGE_COLUMN] = ""
        frame[WORKAROUND_COLUMN] = ""
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            ccc = frame.iloc[:4]
            if missing:
                ccc = ccc.drop(columns=[missing])
            ccc.to_excel(writer, sheet_name="CCC", index=False)
            frame.iloc[4:].to_excel(writer, sheet_name="Concourse", index=False)

    def app(self):
        return AppTest.from_string(
            f"""
import sys
sys.path.insert(0, 'src')
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()

    def test_only_confirmed_rows_and_missing_fields_preserved(self):
        frame = load_confirmed_risks(str(self.path))
        self.assertEqual(frame["Activity / Project"].tolist(), ["Release 1", "Release 3", "Release 5"])
        self.assertTrue(pd.isna(frame.iloc[1]["Risk / Challenge Description"]))
        self.write_workbook(missing="Risk Severity")
        with self.assertRaisesRegex(ValueError, "CCC.*Risk Severity"):
            load_confirmed_risks(str(self.path))

    def test_confirmed_rows_cache_is_isolated_and_refreshes(self):
        with patch.object(risks, "read_sheet", wraps=risks.read_sheet) as reader:
            frame = load_confirmed_risks(str(self.path))
            frame.loc[0, "Team"] = "Changed locally"
            self.assertEqual(load_confirmed_risks(str(self.path)).loc[0, "Team"], "Alpha")
            self.assertEqual(reader.call_count, 2)
            self.write_workbook(empty=True)
            self.assertTrue(load_confirmed_risks(str(self.path)).empty)
            self.assertEqual(reader.call_count, 4)

    def test_risk_chart_opens_selected_team_details(self):
        app = self.app()
        app.button(key="delivery_section_Risks").click().run()
        self.assertFalse(app.exception)
        tiles = next(item.value for item in app.markdown if "class='rk-tiles'" in item.value)
        self.assertLess(tiles.index("Total risks"), tiles.index("With mitigation"))
        self.assertLess(tiles.index("With mitigation"), tiles.index("Teams affected"))
        self.assertLess(tiles.index("Teams affected"), tiles.index("No mitigation yet"))
        self.assertIn("<div class='rk-tile-value'>2</div><div class='rk-tile-label'>With mitigation</div>", tiles)
        self.assertIn("<div class='rk-tile-value'>2</div><div class='rk-tile-label'>Teams affected</div>", tiles)
        self.assertFalse(app.get("dialog"))
        self.assertFalse(app.dataframe)
        self.assertEqual(len(app.get("plotly_chart")), 1)
        with patch("risks.render_summary_chart", return_value="Alpha"):
            app.run()
        self.assertEqual(len(app.get("dialog")), 1)
        table = app.dataframe[0].value
        self.assertEqual(table.columns.tolist(), [
            "Product", "Release", "Risk / Challenge Description",
            "Risk Severity", "Mitigation Plan / Next Action",
        ])
        self.assertEqual(table.values.tolist(), [
            ["Alpha", "Release 1", "<Blocked>", "High", "Retest"],
            ["Alpha", "Release 3", "Not provided", "Not provided", "Not provided"],
        ])
        app.button(key="delivery_back").click().run()
        self.assertEqual([button.label for button in app.button], ["Active Releases", "Risks", "Governance"])

    def test_empty_and_missing_workbook_errors(self):
        self.write_workbook(empty=True)
        app = self.app()
        app.button(key="delivery_section_Risks").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.info[0].value, "No lead-confirmed risks found.")
        missing = AppTest.from_string(
            f"""
import sys
sys.path.insert(0, 'src')
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path.parent / "missing.xlsx")!r})
"""
        ).run()
        missing.button(key="delivery_section_Risks").click().run()
        self.assertIn("Product status workbook not found", missing.error[0].value)
        self.assertFalse(missing.exception)

    def test_risk_export_uses_display_labels(self):
        app = AppTest.from_string(
            f"""
import sys
from unittest.mock import patch
import streamlit as st
sys.path.insert(0, 'src')
from risks import _render_confirmed_risks
def capture(label, data, **kwargs):
    st.session_state["export"] = data
with patch.object(st, "download_button", side_effect=capture):
    _render_confirmed_risks({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        frame = pd.read_csv(BytesIO(app.session_state["export"]))
        self.assertIn("Product", frame.columns)
        self.assertEqual(frame["Release"].tolist(), ["Release 1", "Release 3", "Release 5"])
        self.assertEqual(frame["Portfolio"].tolist(), ["C&C", "C&C", "Concourse"])


class OtherChallengesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "challenges.xlsx"
        self.rows = [
            ("CCC", "Alpha", "Release 1", " Yes ", "<Challenge>", "Workaround A"),
            ("CCC", "Beta", "Release 2", "No", "Excluded challenge", "Excluded fix"),
            ("CCC", "Alpha", "Release 3", "YES", "", "Workaround only"),
            ("CCC", "Empty", "Release 4", "yes", "", ""),
            ("Concourse", "Concourse", "Release 5", "yes", "Concourse challenge", ""),
        ]
        self.write_workbook()

    def write_workbook(self, missing=None):
        frame = pd.DataFrame(self.rows, columns=CHALLENGE_COLUMNS)
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            ccc = frame.iloc[:4]
            if missing:
                ccc = ccc.drop(columns=[missing])
            ccc.to_excel(writer, sheet_name="CCC", index=False)
            frame.iloc[4:].to_excel(writer, sheet_name="Concourse", index=False)

    def test_confirmed_challenges_from_both_sheets_and_missing_column(self):
        frame = load_other_challenges(str(self.path))
        self.assertEqual(frame["Activity / Project"].tolist(), ["Release 1", "Release 3", "Release 5"])
        self.write_workbook(missing=WORKAROUND_COLUMN)
        with self.assertRaisesRegex(ValueError, "CCC.*Mitigation Plan / Workaround"):
            load_other_challenges(str(self.path))

    def test_challenges_cache_is_isolated_and_refreshes(self):
        with patch.object(risks, "read_sheet", wraps=risks.read_sheet) as reader:
            frame = load_other_challenges(str(self.path))
            frame.loc[0, "Team"] = "Changed locally"
            self.assertEqual(load_other_challenges(str(self.path)).loc[0, "Team"], "Alpha")
            self.assertEqual(reader.call_count, 2)
            self.rows = [(p, t, a, r, "", "") for p, t, a, r, _, _ in self.rows]
            self.write_workbook()
            self.assertTrue(load_other_challenges(str(self.path)).empty)
            self.assertEqual(reader.call_count, 4)

    def test_navigation_buttons_keep_existing_risk_errors_isolated(self):
        app = AppTest.from_string(
            f"""
import sys
sys.path.insert(0, 'src')
from project_delivery_status import render_project_delivery_status
render_project_delivery_status({str(self.path)!r})
"""
        ).run()
        app.button(key="delivery_section_Risks").click().run()
        self.assertEqual([app.button(key=f"delivery_risk_section_{view}").label
                          for view in ("Risks", "Other Challenges")], ["Risks", "Other Challenges"])
        self.assertFalse(app.tabs)
        self.assertIn("Risk Severity", app.error[0].value)
        app.button(key="delivery_risk_section_Other Challenges").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertFalse(app.get("dialog"))
        tiles = next(item.value for item in app.markdown if "class='rk-tiles'" in item.value)
        self.assertEqual(tiles.count("class='rk-tile'"), 3)
        self.assertIn("<div class='rk-tile-value'>3</div><div class='rk-tile-label'>Total challenges</div>", tiles)
        self.assertIn("<div class='rk-tile-value'>2</div><div class='rk-tile-label'>With mitigation</div>", tiles)
        self.assertIn("<div class='rk-tile-value'>2</div><div class='rk-tile-label'>Teams affected</div>", tiles)
        self.assertLess(tiles.index("Total challenges"), tiles.index("With mitigation"))
        self.assertLess(tiles.index("With mitigation"), tiles.index("Teams affected"))
        self.assertTrue(any("Challenges by team" in item.value for item in app.markdown))
        self.assertEqual(len(app.get("plotly_chart")), 1)
        self.assertFalse(app.dataframe)
        with patch("risks.render_summary_chart", return_value="Concourse"):
            app.run()
        self.assertEqual(len(app.get("dialog")), 1)
        table = app.dataframe[0].value
        self.assertEqual(table.columns.tolist(), ["Product", "Challenge", WORKAROUND_COLUMN])
        self.assertEqual(table.values.tolist(), [["Concourse", "Concourse challenge", "Not provided"]])
        self.assertEqual(next(item.value for item in app.markdown if "class='rk-tiles'" in item.value), tiles)
        app.button(key="delivery_risk_section_Risks").click().run()
        self.assertIn("Risk Severity", app.error[0].value)
        self.assertFalse(app.get("dialog"))
        self.assertFalse(app.exception)

    def test_missing_and_empty_challenges(self):
        self.rows = [(p, t, a, r, "", "") for p, t, a, r, _, _ in self.rows]
        self.write_workbook()
        self.assertTrue(load_other_challenges(str(self.path)).empty)

    def test_challenge_export_uses_display_labels(self):
        app = AppTest.from_string(
            f"""
import sys
from unittest.mock import patch
import streamlit as st
sys.path.insert(0, 'src')
from risks import _render_other_challenges
def capture(label, data, **kwargs):
    st.session_state["export"] = data
with patch.object(st, "download_button", side_effect=capture):
    _render_other_challenges({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        frame = pd.read_csv(BytesIO(app.session_state["export"]))
        self.assertIn("Product", frame.columns)
        self.assertEqual(frame["Release"].tolist(), ["Release 1", "Release 3", "Release 5"])
        self.assertEqual(frame["Portfolio"].tolist(), ["C&C", "C&C", "Concourse"])

    def test_summary_excludes_missing_teams_and_blank_mitigations(self):
        self.rows[4] = ("Concourse", " alpha ", "Release 5", "yes", "Challenge", "  ")
        self.rows.append(("Concourse", "", "Release 6", "yes", "Challenge", ""))
        self.write_workbook()
        app = AppTest.from_string(
            f"""
import sys
sys.path.insert(0, 'src')
from risks import _render_other_challenges
_render_other_challenges({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        tiles = next(item.value for item in app.markdown if "class='rk-tiles'" in item.value)
        self.assertIn("<div class='rk-tile-value'>4</div><div class='rk-tile-label'>Total challenges</div>", tiles)
        self.assertIn("<div class='rk-tile-value'>2</div><div class='rk-tile-label'>With mitigation</div>", tiles)
        self.assertIn("<div class='rk-tile-value'>1</div><div class='rk-tile-label'>Teams affected</div>", tiles)

    def test_challenge_rows_are_excluded_from_risks_even_with_risk_fields(self):
        frame = pd.DataFrame(self.rows, columns=CHALLENGE_COLUMNS)
        for column in RISK_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        frame["Risk / Challenge Description"] = "Risk description"
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            frame.iloc[:4].to_excel(writer, sheet_name="CCC", index=False)
            frame.iloc[4:].to_excel(writer, sheet_name="Concourse", index=False)
        self.assertEqual(load_confirmed_risks(str(self.path))["Activity / Project"].tolist(), ["Release 4"])
        self.assertEqual(load_other_challenges(str(self.path))["Activity / Project"].tolist(),
                         ["Release 1", "Release 3", "Release 5"])
