import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_loader import build_billability_summary
from common.styles import dialog_table_height


class BillabilityTests(unittest.TestCase):
    def test_dialog_table_height_scales_and_is_capped(self):
        self.assertEqual(dialog_table_height(1), "content")
        self.assertEqual(dialog_table_height(8), "content")
        self.assertEqual(dialog_table_height(9), 360)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "resources.xlsx"
        self.frame = pd.DataFrame([
            ("Alice", "Yes", "Alpha"),
            ("Alice", "Yes", "Alpha"),
            ("Alice", "Yes", "Beta"),
            ("Bob", "Yes", ""),
            ("Carol", "No", "Gamma"),
            ("", "Yes", "Ignored"),
        ], columns=["Resource Name", "Billable", "Product"])
        self.write_workbook()

    def write_workbook(self):
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            self.frame.to_excel(writer, sheet_name="Resource List", index=False)

    def test_summary_retains_distinct_resource_counts(self):
        summary, details = build_billability_summary(str(self.path))
        self.assertEqual(dict(zip(summary["Billability"], summary["Resources"])), {"Yes": 2, "No": 1})
        self.assertEqual(len(details), 5)

    def test_selected_bar_shows_only_its_resources_and_download(self):
        app = AppTest.from_string(
            f"""
import sys
from unittest.mock import patch
import streamlit as st
sys.path.insert(0, 'src')
from billability import render_billability
def capture(label, data, **kwargs):
    st.session_state["download"] = data
with patch.object(st, "download_button", side_effect=capture):
    render_billability({str(self.path)!r})
"""
        ).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("dialog"))
        with patch("billability.render_summary_chart", return_value="Yes"):
            app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("dialog")), 1)
        expected = [["Alice", "Alpha"], ["Alice", "Beta"], ["Bob", "Not provided"]]
        self.assertEqual(app.dataframe[0].value.columns.tolist(), ["Resource Name", "Product"])
        self.assertEqual(app.dataframe[0].value.values.tolist(), expected)
        exported = pd.read_csv(BytesIO(app.session_state["download"]))
        self.assertEqual(exported.values.tolist(), expected)
        with patch("billability.render_summary_chart", return_value="No"):
            app.run()
        self.assertEqual(app.dataframe[0].value.values.tolist(), [["Carol", "Gamma"]])

    def test_missing_product_column_reports_error(self):
        self.frame = self.frame.drop(columns=["Product"])
        self.write_workbook()
        with self.assertRaisesRegex(ValueError, "Product"):
            build_billability_summary(str(self.path))


if __name__ == "__main__":
    unittest.main()
