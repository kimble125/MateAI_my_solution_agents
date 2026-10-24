"""외부 패키지 없이 도는 시험: backend 폴더에서 python -m unittest tests.test_summary"""
import csv
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "summary", Path(__file__).resolve().parents[1] / "app" / "services" / "summary.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
CSV = Path(__file__).resolve().parents[2] / "data" / "inbound_visitors_monthly.csv"


def rows():
    with open(CSV, encoding="utf-8") as f:
        return [{"date": r["date"], "value": float(r["value"]), "memo": r["memo"]} for r in csv.DictReader(f)]


class T(unittest.TestCase):
    def test_count_100_plus(self):
        self.assertGreaterEqual(S.build_summary(rows())["count"], 100)

    def test_summary_fields(self):
        s = S.build_summary(rows())
        for k in ("period", "count", "metrics", "trend", "latest"):
            self.assertIn(k, s)
        self.assertLessEqual(s["metrics"]["min"], s["metrics"]["average"])
        self.assertLessEqual(s["metrics"]["average"], s["metrics"]["max"])

    def test_trend_words(self):
        up = [{"date": f"2024-{m:02d}-01", "value": 100 * m} for m in range(1, 13)]
        self.assertTrue(S.build_summary(up)["trend"].startswith("상승"))
        flat = [{"date": f"2024-{m:02d}-01", "value": 100} for m in range(1, 13)]
        self.assertTrue(S.build_summary(flat)["trend"].startswith("유지"))

    def test_empty(self):
        self.assertEqual(S.build_summary([])["count"], 0)

    def test_statistics(self):
        st = S.build_statistics(rows())
        self.assertEqual(len(st["month_average"]), 12)
        self.assertIn(st["busiest_month"], range(1, 13))


if __name__ == "__main__":
    unittest.main()
