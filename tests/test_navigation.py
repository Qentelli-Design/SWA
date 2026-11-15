import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from navigation import SECTIONS


class SidebarTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
