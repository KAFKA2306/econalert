import json

from scripts.collect_productivity import SERIES, parse
from scripts.collect_productivity_vintages import parse_nonfarm_b1


def test_public_api_requires_and_parses_eight_complete_quarters():
    series = []
    for series_id, metric in SERIES.items():
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


def test_parse_nonfarm_revision_table():
    raw = b"""<html><body><pre>
Table B1. Labor productivity growth and related measures - revised and previously published first-quarter 2026
Sector Labor productivity Output Hours worked Hourly compensation Real hourly compensation Unit labor costs
Nonfarm business Revised 0.3 1.0 0.7 2.1 -1.4 1.8
Previously published 0.8 1.5 0.7 3.1 -0.5 2.3
</pre></body></html>"""
    result = parse_nonfarm_b1(raw)
    assert result["revised"]["labor_productivity"] == 0.3
    assert result["previously_published"]["hourly_compensation"] == 3.1
    assert result["revised"]["unit_labor_costs"] == 1.8
