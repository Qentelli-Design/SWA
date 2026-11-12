import sys
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from team_data import PORTFOLIO_GROUPS, get_portfolio_team, get_products


class PortfolioGroupingTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            [
                ("CCC", "Shared", "Engineer"),
                (" concourse ", "Shared", "Engineer"),
                ("C360", "C360", "Engineer"),
                ("", "Unassigned", "Engineer"),
                ("CCC", "Governance", "Governance lead"),
                ("CCC", "", "Engineer"),
            ],
            columns=["Portfolio", "Product", "Role"],
        )

    def test_grouping_uses_each_resource_row(self):
        expected = [
            ["Shared"],
            ["Shared"],
            ["C360", "Unassigned"],
        ]
        for group, products in zip(PORTFOLIO_GROUPS, expected):
            with self.subTest(group=group):
                team = get_portfolio_team(self.frame, group)
                self.assertEqual(get_products(team), products)
                self.assertFalse(team["Role"].str.startswith("Governance").any())

    def test_unknown_group_is_rejected(self):
        with self.assertRaises(ValueError):
            get_portfolio_team(self.frame, "Unknown")


APP_SCRIPT = """
import sys
from pathlib import Path
from unittest.mock import patch
import pandas as pd
sys.path.insert(0, str(Path.cwd() / "src"))
import team_structure

frame = pd.DataFrame([
    ("CCC", "Alpha", "CCC Person", "Engineer", "Onsite"),
    ("CCC", "Shared", "CCC Shared", "Engineer", "Offshore"),
    ("Concourse", "Shared", "Concourse Shared", "Engineer", "Onsite"),
    ("Concourse", "Team 2", "Concourse Person", "Engineer", "Offshore"),
    ("C360", "C360", "C360 Person", "Engineer", "Onsite"),
    ("Other", "Beta", "Other Person", "Engineer", "Offshore"),
], columns=["Portfolio", "Product", "Resource Name", "Role", "Location Normalized"])
for column in ["Vendor", "Qentelli Designation", "Qentelli ID", "Qentelli Mail ID", "Qentelli DOJ",
               "Reporting Manager"]:
    frame[column] = ""
frame["Is Consultant"] = False
with patch.object(team_structure, "load_data", return_value=frame):
    team_structure.render_team_structure("unused")
"""


class PortfolioBrowserTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_string(APP_SCRIPT).run()
        self.assertFalse(self.app.exception)

    def click(self, key):
        self.app.button(key=key).click().run()
        self.assertFalse(self.app.exception)

    def markdown_text(self):
        return "\n".join(item.value for item in self.app.markdown)

    def test_portfolio_navigation_and_scoped_product_details(self):
        self.assertEqual(
            [button.label for button in self.app.button],
            list(PORTFOLIO_GROUPS),
        )
        self.assertEqual(len(self.app.metric), 0)

        self.click("team_portfolio_C&C")
        self.assertEqual(self.app.metric[0].value, "6")
        self.assertIn("C&amp;C Leadership", self.markdown_text())
        self.assertEqual(
            [button.label for button in self.app.button][3:], ["Alpha", "Shared"]
        )
        self.click("team_product_button_Shared")
        self.assertIn("CCC Shared", self.markdown_text())
        self.assertNotIn("Concourse Shared", self.markdown_text())

        self.click("team_portfolio_Concourse")
        self.assertEqual(
            [button.label for button in self.app.button][3:], ["Shared", "Team 2"]
        )
        self.assertIn("Concourse Shared", self.markdown_text())
        self.assertNotIn("CCC Shared", self.markdown_text())
        self.assertEqual(self.app.metric[0].value, "6")

        self.click("team_portfolio_C360 and Other Products")
        self.assertEqual(
            [button.label for button in self.app.button][3:], ["Beta", "C360"]
        )
        self.click("team_product_button_C360")
        self.assertIn("C360 Person", self.markdown_text())
        self.assertNotIn("Other Person", self.markdown_text())
        self.assertEqual(self.app.metric[0].value, "6")
        self.assertIn("C&amp;C Leadership", self.markdown_text())

        self.click("team_portfolio_C&C")
        self.assertIn("CCC Person", self.markdown_text())
        self.assertNotIn("C360 Person", self.markdown_text())

    def test_empty_group_shows_message(self):
        app = AppTest.from_string(
            APP_SCRIPT.replace('("Concourse", "Shared"', '("Other", "Shared"')
            .replace('("Concourse", "Team 2"', '("Other", "Team 2"')
        ).run()
        app.button(key="team_portfolio_Concourse").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No product teams found for Concourse" in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()
