import json
from pathlib import Path

from scripts.collect_productivity import SERIES, parse


def test_public_api_requires_and_parses_eight_complete_quarters():
    series = []
    for series_id in SERIES:
        data = []
        for index in range(8):
            year = 2024 + index // 4
            quarter = index % 4 + 1
            data.append(
                {
                    "year": str(year),
                    "period": f"Q{quarter:02d}",
                    "value": str(index + 0.5),
                    "footnotes": [{"text": "Revised."}] if index == 7 else [{}],
                }
            )
        series.append({"seriesID": series_id, "data": data})
    raw = json.dumps(
        {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": series}}
    ).encode()
    rows = parse(raw)
    assert len(rows) == 8
    assert rows[0]["period"] == "2024-Q1"
    assert rows[-1]["period"] == "2025-Q4"
    assert rows[-1]["labor_productivity"] == 7.5
    assert rows[-1]["footnotes"]["labor_productivity"] == ["Revised."]


def test_seeded_release_vintages_have_complete_primary_source_rows():
    payload = json.loads(
        Path("data/official/bls-productivity-vintages.json").read_text(encoding="utf-8")
    )
    metrics = set(payload["metrics"])
    assert len(payload["releases"]) == 7
    assert payload["releases"][0]["quarter"] == "2024-Q3"
    assert payload["releases"][-1]["quarter"] == "2026-Q1"
    for release in payload["releases"]:
        assert release["source_url"].startswith("https://www.bls.gov/news.release/archives/")
        assert release["source_section"] == "Table B1"
        assert set(release["revised"]) == metrics
        assert set(release["previously_published"]) == metrics
