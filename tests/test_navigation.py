import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from navigation import SECTIONS


class SidebarTests(unittest.TestCase):
    def test_attrition_heading_has_a_dedicated_container(self):
        app = AppTest.from_string("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from navigation import render_section_header
render_section_header("Attrition")
""").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Attrition")
        self.assertTrue(app.get("flex_container")[0].proto.id.endswith("-attrition-heading"))

    def test_home_has_no_releases_section(self):
        app = AppTest.from_string("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from navigation import render_landing
render_landing()
""").run()
        self.assertFalse(app.exception)
        self.assertEqual([button.label for button in app.button], list(SECTIONS))
        self.assertNotIn("Releases/Milestones", SECTIONS)
        self.assertNotIn("Risks", SECTIONS)
        self.assertIn("Project Delivery Status", [button.label for button in app.button])

    def test_sidebar_has_navigation_without_data_source_on_every_section(self):
        script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from navigation import current_section, render_sidebar
st_section = current_section()
render_sidebar()
"""
        app = AppTest.from_string(script)
        for section in SECTIONS:
            with self.subTest(section=section):
                app.session_state["dashboard_section"] = section
                app.run()
                self.assertFalse(app.exception)
                self.assertEqual(app.sidebar.button[0].label, "Return to Home")
                sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
                self.assertNotIn("Data source", sidebar_text)
                self.assertNotIn("source-card", sidebar_text)
        app.sidebar.button[0].click().run()
        self.assertIsNone(app.session_state["dashboard_section"])

    def test_return_home_clears_delivery_subview(self):
        app = AppTest.from_string("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from navigation import render_sidebar
render_sidebar()
""")
        app.session_state["dashboard_section"] = "Project Delivery Status"
        app.session_state["project_delivery_view"] = "Active Releases"
        app.run()
        app.sidebar.button[0].click().run()
        self.assertIsNone(app.session_state["dashboard_section"])
        self.assertNotIn("project_delivery_view", app.session_state.filtered_state)


if __name__ == "__main__":
    unittest.main()
