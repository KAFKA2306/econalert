import hashlib
import json
from pathlib import Path

from scripts.contract_escalation import READY, calculate


SNAPSHOT = Path("data/official/bls-cpi-u-all-items-index-2025-05-2026-05.json")


def test_official_may_cpi_u_snapshot_and_contract_calculation():
    source = json.loads(SNAPSHOT.read_text())
    assert source["series_id"] == "CUUR0000SA0"
    assert source["observations"] == [
        {
            "period": "2025-M05",
            "value": 321.465,
            "source_url": "https://www.bls.gov/news.release/archives/cpi_06102026.htm",
        },
        {
            "period": "2026-M04",
            "value": 333.020,
            "source_url": "https://www.bls.gov/news.release/archives/cpi_06102026.htm",
        },
        {
            "period": "2026-M05",
            "value": 335.123,
            "source_url": "https://www.bls.gov/news.release/archives/cpi_06102026.htm",
        },
    ]

    profile = {
        "contract_id": "may-index-verification",
        "series_id": "CUUR0000SA0",
        "base_period": "2025-M05",
        "comparison_period": "2026-M05",
        "formula": "percent_change",
        "clause_verified": True,
        "floor_percent": None,
        "cap_percent": None,
        "adjustment_date": None,
        "notice_lead_days": None,
    }
    snapshot_sha = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    report = calculate(profile, source, snapshot_sha, as_of_date="2026-08-16")

    assert report["status"] == READY
    assert report["calculation"]["base_index"] == 321.465
    assert report["calculation"]["comparison_index"] == 335.123
    assert report["calculation"]["raw_percent_change"] == 4.24867404
    assert report["calculation"]["adjustment_percent"] == 4.24867404
