import hashlib
import json
import unittest

from scripts.contract_escalation import (
    MISSING_TERM,
    READY,
    SOURCE_MISMATCH,
    WAITING,
    calculate,
)


def profile(**overrides):
    value = {
        "contract_id": "synthetic-001",
        "series_id": "CUUR0000SA0",
        "base_period": "2025-M06",
        "comparison_period": "2026-M06",
        "formula": "percent_change",
        "clause_verified": True,
        "floor_percent": 1.0,
        "cap_percent": 4.0,
    }
    value.update(overrides)
    return value


def snapshot(**overrides):
    value = {
        "publisher": "U.S. Bureau of Labor Statistics",
        "series_id": "CUUR0000SA0",
        "series_title": "Synthetic fixture for CUUR0000SA0 contract tests",
        "source_url": "https://www.bls.gov/developers/api_signature_v2.htm",
        "retrieved_at": "SYNTHETIC_FIXTURE",
        "observations": [
            {"period": "2025-M06", "value": 100.0},
            {"period": "2026-M06", "value": 105.0},
        ],
    }
    value.update(overrides)
    return value


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class ContractEscalationTests(unittest.TestCase):
    def test_exact_series_and_cap(self):
        source = snapshot()
        result = calculate(profile(), source, sha(source))
        self.assertEqual(READY, result["status"])
        self.assertEqual(5.0, result["calculation"]["raw_percent_change"])
        self.assertEqual(4.0, result["calculation"]["adjustment_percent"])
        self.assertEqual("CUUR0000SA0", result["source"]["series_id"])
        self.assertEqual(64, len(result["source"]["snapshot_sha256"]))
        self.assertEqual(64, len(result["calculation_revision"]))

    def test_floor_applies_only_when_declared(self):
        source = snapshot(observations=[
            {"period": "2025-M06", "value": 100.0},
            {"period": "2026-M06", "value": 99.0},
        ])
        self.assertEqual(1.0, calculate(profile(), source, sha(source))["calculation"]["adjustment_percent"])
        no_floor = profile(floor_percent=None, cap_percent=None)
        self.assertEqual(-1.0, calculate(no_floor, source, sha(source))["calculation"]["adjustment_percent"])

    def test_series_mismatch_fails_closed(self):
        source = snapshot(series_id="CUSR0000SA0")
        result = calculate(profile(), source, sha(source))
        self.assertEqual(SOURCE_MISMATCH, result["status"])
        self.assertEqual({}, result["calculation"])

    def test_missing_comparison_waits_for_release(self):
        source = snapshot(observations=[{"period": "2025-M06", "value": 100.0}])
        result = calculate(profile(), source, sha(source))
        self.assertEqual(WAITING, result["status"])
        self.assertEqual({}, result["calculation"])

    def test_missing_base_and_unverified_clause_fail_closed(self):
        source = snapshot(observations=[{"period": "2026-M06", "value": 105.0}])
        self.assertEqual(MISSING_TERM, calculate(profile(), source, sha(source))["status"])
        self.assertEqual(MISSING_TERM, calculate(profile(clause_verified=False), snapshot(), sha(snapshot()))["status"])

    def test_invalid_floor_cap_is_not_silently_corrected(self):
        source = snapshot()
        result = calculate(profile(floor_percent=5.0, cap_percent=2.0), source, sha(source))
        self.assertEqual(MISSING_TERM, result["status"])
        self.assertEqual("floor_exceeds_cap", result["reason"])


if __name__ == "__main__":
    unittest.main()
