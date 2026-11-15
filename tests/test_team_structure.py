import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from team_data import (
    LEADERSHIP_ROOT, PORTFOLIO_GROUPS, email_display_name,
    get_leadership_hierarchy, get_portfolio_team, get_products, load_data,
)


class DisplayNameTests(unittest.TestCase):
    def test_workbook_xid_loading_and_missing_column(self):
        frame = pd.DataFrame([{
            "Portfolio": "CCC", "Product": "Alpha", "Resource Name": "Test",
            "XID": " x123 ", "Location": "Onsite", "Role": "Engineer",
            "Vendor": "", "Reporting Manager": "",
        }, {
            "Portfolio": "CCC", "Product": "Alpha", "Resource Name": "Other",
            "XID": None, "Location": "Offshore", "Role": "Engineer",
            "Vendor": "", "Reporting Manager": "",
        }])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.xlsx"
            frame.to_excel(path, sheet_name="Resource List", index=False)
            self.assertEqual(load_data(str(path))["XID"].tolist(), ["x123", ""])
            frame.drop(columns=["XID"]).to_excel(path, sheet_name="Resource List", index=False)
            with self.assertRaisesRegex(ValueError, "missing: XID"):
                load_data(str(path))

    def test_email_names_and_fallbacks(self):
        examples = [
            (" first.last@qentelli.com ", "First Last"),
            ("FIRST.MIDDLE.LAST@QENTELLI.COM", "First Middle Last"),
            ("firstname@qentelli.com", "Firstname"),
            ("", "Original Name"),
            ("first.last@example.com", "Original Name"),
            ("@qentelli.com", "Original Name"),
        ]
        for email, expected in examples:
            with self.subTest(email=email):
                self.assertEqual(email_display_name(email, "Original Name"), expected)

    def test_leadership_names_use_email_without_changing_reporting_links(self):
        governance = pd.DataFrame([
            ("Original Manager", LEADERSHIP_ROOT, "first.manager@qentelli.com", "x111"),
            ("Original Report", "Original Manager", "second.report@qentelli.com", ""),
        ], columns=["Resource Name", "Reporting Manager", "Qentelli Mail ID", "XID"])
        hierarchy = get_leadership_hierarchy(governance)
        self.assertEqual(hierarchy["name"], LEADERSHIP_ROOT)
        self.assertEqual(hierarchy["children"][0]["name"], "First Manager")
        self.assertEqual(hierarchy["children"][0]["children"][0]["name"], "Second Report")


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
for column in ["Vendor", "Qentelli Designation", "Qentelli ID", "Qentelli Mail ID", "Qentelli DOJ", "XID",
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

    def test_sidebar_xid_toggle_for_leads_members_and_leadership(self):
        script = APP_SCRIPT.replace(
            'frame["Is Consultant"] = False',
            '''frame["Is Consultant"] = False
frame.loc[0, "Qentelli Mail ID"] = "jane.doe@qentelli.com"
frame.loc[0, "Role"] = "Lead Onsite"
frame.loc[0, "XID"] = "x123456"
frame.loc[1, "Qentelli Mail ID"] = "john.smith@qentelli.com"
frame.loc[1, "Vendor"] = "Rebadge"
frame.loc[2, "XID"] = "x789123"
governance = frame.iloc[0].copy()
governance["Resource Name"] = "Original Manager"
governance["Qentelli Mail ID"] = "first.manager@qentelli.com"
governance["Reporting Manager"] = "Siva Rao Kompella S V"
governance["Role"] = "Governance"
governance["XID"] = "x555555"
frame = pd.concat([frame, pd.DataFrame([governance])], ignore_index=True)
''',
        )
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.toggle(key="team_show_xid").label, "Show XID")
        self.assertFalse(app.toggle(key="team_show_xid").value)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Jane Doe", markup)
        self.assertNotIn("(x123456)", markup)
        app.toggle(key="team_show_xid").set_value(True).run()
        self.assertFalse(app.exception)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn('Jane Doe <span class="team-xid">(x123456)</span>', markup)
        self.assertIn("First Manager", markup)
        self.assertIn("Siva Rao Kompella S V", markup)
        self.assertNotIn("(x555555)", markup)
        self.assertNotIn("Siva Rao Kompella S V (NA)", markup)
        app.button(key="team_product_button_Shared").click().run()
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn('John Smith <span class="team-xid">(NA)</span> - Rebadge', markup)
        app.button(key="team_portfolio_Concourse").click().run()
        self.assertIn('Concourse Shared <span class="team-xid">(x789123)</span>', "\n".join(item.value for item in app.markdown))
        app.toggle(key="team_show_xid").set_value(False).run()
        markup = "\n".join(item.value for item in app.markdown)
        self.assertNotIn("(x789123)", markup)
        self.assertNotIn("(NA)", markup)
        self.assertIn("Concourse Shared", markup)

    def test_summary_and_leadership_appear_before_portfolio_controls(self):
        for group in PORTFOLIO_GROUPS:
            with self.subTest(group=group):
                self.click(f"team_portfolio_{group}")
                elements = list(self.app.main)
                caption = next(i for i, element in enumerate(elements)
                               if element.type == "caption" and
                               element.value == "Overall workforce overview and C&C leadership.")
                metric = next(i for i, element in enumerate(elements) if element.type == "metric")
                leadership = next(i for i, element in enumerate(elements)
                                  if element.type == "markdown" and "<div class='governance-card'>" in element.value)
                tab = next(i for i, element in enumerate(elements)
                           if element.type == "button" and element.key == "team_portfolio_C&C")
                heading = next(i for i, element in enumerate(elements)
                               if element.type == "markdown" and "Product Delivery Structure</h2>" in element.value)
                self.assertLess(caption, metric)
                self.assertLess(metric, leadership)
                self.assertLess(leadership, tab)
                self.assertLess(tab, heading)

    def test_team_cards_leads_and_consultant_badge(self):
        script = APP_SCRIPT.replace(
            'frame["Is Consultant"] = False',
            '''frame["Is Consultant"] = False
frame.loc[0, "Qentelli Mail ID"] = "jane.doe@qentelli.com"
frame.loc[0, "Role"] = "Lead Onsite"
frame.loc[0, "Is Consultant"] = True
frame.loc[0, "Qentelli ID"] = "LEAD-123"
frame.loc[0, "Qentelli DOJ"] = "01 Jan 2020"
frame.loc[1, "Qentelli Mail ID"] = "john.smith@qentelli.com"
frame.loc[1, "Vendor"] = "Rebadge"
frame.loc[1, "Is Consultant"] = True
frame.loc[1, "Qentelli ID"] = "MEMBER-123"
''',
        )
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Jane Doe", markup)
        self.assertNotIn("CCC Person", markup)
        self.assertIn("<span class='consultant-tag'>Q Consultant</span>", markup)
        self.assertNotIn("LEAD-123", markup)
        self.assertNotIn("jane.doe@qentelli.com", markup)
        self.assertNotIn("01 Jan 2020", markup)
        app.button(key="team_product_button_Shared").click().run()
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("John Smith - Rebadge", markup)
        self.assertNotIn("CCC Shared", markup)
        self.assertIn("<span class='consultant-tag'>Q Consultant</span>", markup)
        self.assertNotIn("MEMBER-123", markup)
        self.assertNotIn("john.smith@qentelli.com", markup)

    def test_product_rail_precedes_details_for_each_portfolio(self):
        rail_keys = ("ccc-portfolio-rail", "concourse-portfolio-rail", "other-portfolio-rail")
        for group, rail_key in zip(PORTFOLIO_GROUPS, rail_keys):
            with self.subTest(group=group):
                self.click(f"team_portfolio_{group}")
                self.assertTrue(any(
                    container.proto.id.endswith(f"-{rail_key}")
                    for container in self.app.get("flex_container")
                ))
                columns = self.app.get("column")
                rail_index = next(
                    index for index, column in enumerate(columns)
                    if any(
                        item.type == "button" and item.key.startswith("team_product_button_")
                        for item in column
                    )
                )
                self.assertTrue(any(
                    item.type == "markdown" and "selected-product-panel" in item.value
                    for item in columns[rail_index + 1]
                ))

    def test_portfolio_navigation_and_scoped_product_details(self):
        self.assertEqual(
            [button.label for button in self.app.button][:3],
            list(PORTFOLIO_GROUPS),
        )
        self.assertEqual(self.app.button(key="team_portfolio_C&C").proto.type, "primary")
        self.assertEqual(self.app.button(key="team_portfolio_Concourse").proto.type, "secondary")
        self.assertFalse(any("Select a portfolio" in item.value for item in self.app.info))
        self.assertEqual(self.app.metric[0].value, "6")
        self.assertIn("C&amp;C Leadership", self.markdown_text())
        self.assertIn("CCC Person", self.markdown_text())
        self.assertEqual(
            [button.label for button in self.app.button][3:], ["Alpha", "Shared"]
        )
        self.click("team_product_button_Shared")
        self.assertIn("CCC Shared", self.markdown_text())
        self.assertNotIn("Concourse Shared", self.markdown_text())

        self.click("team_portfolio_Concourse")
        self.assertEqual(self.app.button(key="team_portfolio_Concourse").proto.type, "primary")
        self.assertEqual(self.app.button(key="team_portfolio_C&C").proto.type, "secondary")
        self.assertEqual(
            [button.label for button in self.app.button][3:], ["Shared", "Team 2"]
        )
        self.assertIn("Concourse Shared", self.markdown_text())
        self.assertNotIn("CCC Shared", self.markdown_text())
        self.assertEqual(self.app.metric[0].value, "6")

        self.click("team_portfolio_C360 and Other Products")
        self.assertEqual(self.app.button(key="team_portfolio_C360 and Other Products").proto.type, "primary")
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
