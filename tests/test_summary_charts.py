import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common.charts import render_summary_chart


class SummaryChartTests(unittest.TestCase):
    def test_compact_height_and_integer_ticks(self):
        for count, expected in ((1, 162), (2, 214), (20, 760)):
            with self.subTest(count=count):
                summary = pd.DataFrame({"Team": [f"Team {i}" for i in range(count)], "Risks": [1] * count})
                with patch("common.charts._show_summary_chart") as show:
                    render_summary_chart(
                        "Risks", summary, "Team", "#1f4e79", "Empty",
                        top_n=count, value_column="Risks", corporate=True, compact=True,
                        show_heading=False, selection_key="risk-test",
                    )
                figure, key = show.call_args.args
                self.assertEqual(figure.layout.height, expected)
                self.assertEqual(figure.layout.xaxis.dtick, 1)
                self.assertEqual(figure.data[0].textposition, "outside")
                self.assertEqual(key, "risk-test")

    def test_default_chart_height_is_unchanged(self):
        summary = pd.DataFrame({"Team": ["Alpha"], "Resources": [1]})
        with patch("common.charts._show_summary_chart") as show:
            render_summary_chart("Chart", summary, "Team", "#1f4e79", "Empty", show_heading=False)
        self.assertEqual(show.call_args.args[0].layout.height, 420)


if __name__ == "__main__":
    unittest.main()
