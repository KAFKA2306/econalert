import hashlib
import json
from pathlib import Path

from scripts.contract_escalation import READY, calculate


SNAPSHOT = Path("data/official/bls-cpi-u-all-items-index-2025-07-2026-07.json")


def test_official_july_cpi_u_snapshot_and_contract_calculation():
    source = json.loads(SNAPSHOT.read_text())
    assert source["series_id"] == "CUUR0000SA0"
    assert source["observations"] == [
        {
            "period": "2025-M07",
            "value": 323.048,
            "source_url": "https://www.bls.gov/news.release/cpi.t01.htm",
        },
        {
            "period": "2026-M06",
            "value": 333.952,
            "source_url": "https://www.bls.gov/news.release/cpi.t01.htm",
        },
        {
            "period": "2026-M07",
            "value": 333.918,
            "source_url": "https://www.bls.gov/news.release/cpi.t01.htm",
        },
    ]

    profile = {
        "contract_id": "july-index-verification",
        "series_id": "CUUR0000SA0",
        "base_period": "2025-M07",
        "comparison_period": "2026-M07",
        "formula": "percent_change",
        "clause_verified": True,
        "floor_percent": None,
        "cap_percent": None,
        "adjustment_date": None,
        "notice_lead_days": None,
    }
    snapshot_sha = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    report = calculate(profile, source, snapshot_sha, as_of_date="2026-08-19")

    assert report["status"] == READY
    assert report["calculation"]["base_index"] == 323.048
    assert report["calculation"]["comparison_index"] == 333.918
    assert report["calculation"]["raw_percent_change"] == 3.36482504
    assert report["calculation"]["adjustment_percent"] == 3.36482504
