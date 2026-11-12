import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from org_data import ROOT_NAME, build_hierarchy, clean_data, load_data, unassigned_resources, unconnected_relationships


def make_frame(rows):
    frame = pd.DataFrame(rows, columns=["Resource Name", "Reporting Manager", "Product", "Vendor"])
    return frame.fillna("")


class OrganizationDataTests(unittest.TestCase):
    def test_workbook_changes_refresh_cached_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.xlsx"
            frame = make_frame([("Alice", ROOT_NAME, "A", "Qentelli")])
            for column in ("Portfolio", "Location", "Role"):
                frame[column] = ""
            frame.to_excel(path, sheet_name="Resource List", index=False)
            self.assertEqual(len(load_data(str(path))), 1)
            frame.loc[1] = ["Bob", ROOT_NAME, "A", "Qentelli", "", "", ""]
            frame.to_excel(path, sheet_name="Resource List", index=False)
            self.assertEqual(len(load_data(str(path))), 2)

    def test_unconnected_chains_and_cycles_are_not_lost(self):
        frame = make_frame([
            ("Alice", ROOT_NAME, "A", "Qentelli"),
            ("Bob", "Alice", "A", "Qentelli"),
            ("Carol", "Missing Manager", "B", "Qentelli"),
            ("Dave", "Carol", "B", "Qentelli"),
            ("Eve", "Frank", "C", "Qentelli"),
            ("Frank", "Eve", "C", "Qentelli"),
            ("Bob", "Alice", "A", "Qentelli"),
            ("Excluded", "Missing Manager", "B", "Rebadge"),
        ])
        cleaned = clean_data(frame)
        hierarchy = build_hierarchy(cleaned)
        missing = unconnected_relationships(cleaned, hierarchy)
        self.assertEqual(
            set(zip(missing["Resource Name"], missing["Reporting Manager"])),
            {("Carol", "Missing Manager"), ("Dave", "Carol"), ("Eve", "Frank"), ("Frank", "Eve")},
        )

    def test_unassigned_skips_root_and_rebadge(self):
        frame = make_frame([
            (ROOT_NAME, "", "", "Qentelli"),
            ("Unassigned", "", "A", "Qentelli"),
            ("Unassigned", "", "A", "Qentelli"),
            ("Excluded", "", "A", "Rebadge"),
        ])
        self.assertEqual(unassigned_resources(frame)["Resource Name"].tolist(), ["Unassigned"])

    def test_cycles_below_root_report_unrendered_edges(self):
        frame = make_frame([
            ("Alice", ROOT_NAME, "A", "Qentelli"),
            ("Bob", "Alice", "A", "Qentelli"),
            ("Alice", "Bob", "A", "Qentelli"),
        ])
        cleaned = clean_data(frame)
        missing = unconnected_relationships(cleaned, build_hierarchy(cleaned))
        self.assertEqual(missing["Resource Name"].tolist(), ["Alice"])


APP_SCRIPT = """
import sys
from pathlib import Path
from unittest.mock import patch
import pandas as pd
sys.path.insert(0, str(Path.cwd() / "src"))
import org_structure
frame = pd.DataFrame([
    ("Connected", "Siva Rao Kompella S V", "A", "Qentelli"),
    ("Missing Person", "External Manager", "B", "Qentelli"),
    ("No Manager", "", "C", "Qentelli"),
], columns=["Resource Name", "Reporting Manager", "Product", "Vendor"])
with patch.object(org_structure, "load_data", return_value=frame):
    org_structure.render_org_structure("unused")
"""


class OrganizationViewTests(unittest.TestCase):
    def test_connected_and_unconnected_resources_render(self):
        app = AppTest.from_string(APP_SCRIPT).run()
        self.assertFalse(app.exception)
        text = "\n".join(item.value for item in app.markdown)
        self.assertIn("Connected", text)
        self.assertIn("External Manager", text)
        self.assertIn("Missing Person", text)
        self.assertIn("No Manager", text)
        self.assertTrue(any("1 reporting relationship cannot" in item.value for item in app.warning))

    def test_unconnected_resources_render_without_root_reports(self):
        app = AppTest.from_string(APP_SCRIPT.replace(
            '("Connected", "Siva Rao Kompella S V", "A", "Qentelli"),',
            '("Connected", "Another Manager", "A", "Qentelli"),',
        )).run()
        self.assertFalse(app.exception)
        text = "\n".join(item.value for item in app.markdown)
        self.assertIn("Missing Person", text)
        self.assertIn("No Manager", text)
        self.assertTrue(any("No connected reporting relationships" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
