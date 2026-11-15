import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills_data import get_team_skill_details, load_resource_skills, load_team_skills


class SkillsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "skills.xlsx"
        resources = pd.DataFrame([
            ("Alpha", "Alex", "Python", "Python"),
            ("Alpha", "Blair", None, None),
            ("Beta", "Alex", "Python", "SQL"),
            ("Beta", "Casey", "SQL", None),
            (None, "Dana", "Git", None),
            ("Alpha", None, "Java", None),
        ], columns=["Product", "Resource Name", "Skill 1", "Skill 2"])
        categories = pd.DataFrame([
            ("Engineering", "Python"), ("Data", "SQL"), ("Tools", "Git"),
        ], columns=["Category", "Skill"])
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            resources.to_excel(writer, sheet_name="Resource List", index=False)
            categories.to_excel(writer, sheet_name="Skill Categories", index=False)

    def test_team_data_retains_resource_without_skills_and_shared_names(self):
        rows = load_team_skills(str(self.path))
        alpha = get_team_skill_details(rows, "Alpha")
        self.assertEqual(alpha.to_dict("records"), [
            {"Resource Name": "Alex", "Skills": "python"},
            {"Resource Name": "Blair", "Skills": "No skills recorded"},
        ])
        beta = get_team_skill_details(rows, "Beta")
        self.assertEqual(beta.to_dict("records"), [
            {"Resource Name": "Alex", "Skills": "python, sql"},
            {"Resource Name": "Casey", "Skills": "sql"},
        ])
        self.assertIn("Unassigned", rows["Product Name"].tolist())
        self.assertNotIn("nan", rows["Resource Name"].tolist())
        category_rows = load_resource_skills(str(self.path))
        self.assertEqual(
            set(category_rows.loc[category_rows["Resource Name"].eq("Alex"), "Product Name"]),
            {"Alpha", "Beta"},
        )
        self.assertFalse(category_rows["Skill"].eq("").any())

    def test_team_view_and_category_drilldown(self):
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from skills import render_skills
render_skills({str(self.path)!r})
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.segmented_control(key="skills_view").value, "Team-wise skills")
        self.assertIn("Alpha  (2)", [button.label for button in app.button])
        self.assertEqual(len(app.dataframe), 0)
        app.button(key="skills_product_Alpha").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value.to_dict("records"), [
            {"Resource Name": "Alex", "Skills": "python"},
            {"Resource Name": "Blair", "Skills": "No skills recorded"},
        ])
        app.button(key="back_to_products").click().run()
        app.button(key="skills_product_Beta").click().run()
        self.assertEqual(app.dataframe[0].value.iloc[0]["Skills"], "python, sql")

        app.segmented_control(key="skills_view").set_value("Skills by category").run()
        self.assertFalse(app.exception)
        app.button(key="skill_category_Engineering").click().run()
        app.button(key="skill_Engineering_python").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(set(app.dataframe[0].value["Product Name"]), {"Alpha", "Beta"})
        self.assertEqual(len(app.get("download_button")), 1)


if __name__ == "__main__":
    unittest.main()
