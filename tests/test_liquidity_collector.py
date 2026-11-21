import importlib.util
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location("collect_liquidity", Path(__file__).resolve().parents[1] / "scripts/collect_liquidity.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LiquidityTest(unittest.TestCase):
    def test_csv_distinguishes_missing_and_rejects_unsafe_formats(self):
        raw = b"DATE,SOFR\n2026-11-01,3.9\n2026-11-02,.\n2026-11-03,3.8\n2026-11-04,3.9\n2026-11-05,3.8\n2026-11-06,3.9\n2026-11-09,3.8\n2026-11-10,3.9\n2026-11-11,3.8\n"
        rows = mod.parse_csv(raw, "SOFR")
        self.assertEqual(len(rows), 8)
        self.assertNotIn("2026-11-02", [r["date"] for r in rows])
        with self.assertRaises(ValueError):
            mod.parse_csv(raw.replace(b"2026-11-10,3.9", b"2026-11-10,nan"), "SOFR")
        with self.assertRaises(ValueError):
            mod.parse_csv(raw.replace(b"DATE,SOFR", b"date,SOFR"), "SOFR")

    def test_cross_market_warning_requires_distinct_groups(self):
        today = date(2026, 11, 20)
        def mk(v, freq="daily"):
            rows = [{"date": (today - timedelta(days=i)).isoformat(), "value": v} for i in range(49, -1, -1)]
            return {"observations": rows, "latest": rows[-1], "stale": False, "frequency": freq}
        s = {k: mk(3.0) for k, (_, _, required) in mod.SERIES.items() if required}
        s["STLFSI4"] = mk(-0.5, "weekly")
        self.assertEqual(mod.assess(s, today)["status"], "normal")
        # One distress signal stays at attention, even if the level looks bad.
        for r in s["BAMLH0A0HYM2"]["observations"][-10:]: r["value"] += 0.6
        s["BAMLH0A0HYM2"]["latest"] = s["BAMLH0A0HYM2"]["observations"][-1]
        self.assertEqual(mod.assess(s, today)["status"], "attention")
        s["STLFSI4"]["latest"]["value"] = 0.3
        self.assertEqual(mod.assess(s, today)["status"], "warning")
        s["SOFR"]["stale"] = True
        self.assertEqual(mod.assess(s, today)["status"], "unverified")

    def test_negative_index_change_has_no_meaningless_percentage(self):
        rows = [{"date": "2026-10-01", "value": -1.0}, {"date": "2026-11-01", "value": -0.5}]
        self.assertIsNone(mod.four_week_change({"observations": rows})["percent_change"])

    def test_snapshot_dedup_and_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = {"source_signature": "a" * 64, "series": {}, "assessment": {"status": "unverified"}}
            latest = root / "api/latest.json"
            self.assertTrue(mod.store(first, root / "raw", latest))
            self.assertFalse(mod.store(first, root / "raw", latest))
            self.assertTrue(mod.store({**first, "source_signature": "b" * 64}, root / "raw", latest))
            self.assertEqual(len(list((root / "raw").glob("*.json"))), 2)
            self.assertEqual(json.loads(latest.read_text())["source_signature"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
