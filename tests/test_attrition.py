import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import attrition


class AttritionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "resources.xlsx"
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            pd.DataFrame(
                [{"Resource Name": "Resource list person", "Resource Status": "Resigned"}]
            ).to_excel(writer, sheet_name="Resource List", index=False)
            pd.DataFrame(
                [
                    {"Resource Name": "Attrition person", "Resource Status": " Managed Attrition ", "Portfolio": "CCC"},
                    {"Resource Name": "Another person", "Resource Status": "resigned"},
                    {"Resource Name": "Active person", "Resource Status": "Active Resource"},
                ]
            ).to_excel(writer, sheet_name="Attrition", index=False)

    def test_reads_attrition_sheet_and_counts_only_known_statuses(self):
        frame = attrition.load_data(str(self.path))
        self.assertEqual(frame["Resource Name"].tolist(), [
            "Attrition person", "Another person", "Active person"
        ])
        self.assertEqual(attrition.count_by_status(frame), {
            "Resigned": 1, "Managed Attrition": 1, "Unmanaged Attrition": 0
        })
        self.assertEqual(frame.loc[0, "Portfolio"], "CCC")

    def test_missing_sheet_is_reported_instead_of_using_resource_list(self):
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            pd.DataFrame({"Resource Status": ["Resigned"]}).to_excel(
                writer, sheet_name="Resource List", index=False
            )
        with self.assertRaisesRegex(ValueError, "Attrition"):
            attrition.load_data(str(self.path))

    def test_missing_status_column_identifies_attrition_sheet(self):
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            pd.DataFrame({"Resource Name": ["Example"]}).to_excel(
                writer, sheet_name="Attrition", index=False
            )
        with self.assertRaisesRegex(ValueError, "'Attrition' sheet is missing: Resource Status"):
            attrition.load_data(str(self.path))

    def test_cards_and_details_use_attrition_sheet(self):
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from attrition import render_attrition
render_attrition({str(self.path)!r})
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertIn("**1**", app.button(key="attrition_Managed Attrition").label)
        self.assertIn("**1**", app.button(key="attrition_Resigned").label)
        app.button(key="attrition_Managed Attrition").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value["Resource Name"].tolist(), ["Attrition person"])
        self.assertEqual(app.dataframe[0].value["Portfolio"].tolist(), ["C&C"])


if __name__ == "__main__":
    unittest.main()
