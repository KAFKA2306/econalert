from scripts.collect_productivity import coverage, select_series, validate_coverage
from scripts.collect_productivity_vintages import parse_nonfarm_b1


def test_selects_nonfarm_productivity_without_hardcoded_series_id():
    series = [
        {"series_id": "X1", "sector_code": "01", "measure_code": "10", "seasonal": "S", "duration_code": "Q", "base_year": "2017"},
        {"series_id": "X2", "sector_code": "02", "measure_code": "10", "seasonal": "S", "duration_code": "Q", "base_year": "2017"},
    ]
    sectors = [
        {"sector_code": "01", "sector_name": "Nonfarm Business"},
        {"sector_code": "02", "sector_name": "Government"},
    ]
    measures = [{"measure_code": "10", "measure_name": "Output per hour"}]
    selected = select_series(series, sectors, measures)
    assert [row["series_id"] for row in selected] == ["X1"]


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


def test_nonfarm_core_metrics_require_eight_quarters():
    measures = {
        "P": "Output per hour",
        "O": "Output",
        "H": "Hours worked",
        "C": "Hourly compensation",
        "U": "Unit labor costs",
    }
    payload = {
        "series": [
            {"series_id": sid, "sector": "Nonfarm Business", "measure": measure}
            for sid, measure in measures.items()
        ],
        "observations": [
            {"series_id": sid, "year": str(2024 + i // 4), "period": f"Q{(i % 4) + 1:02d}", "value": "1.0"}
            for sid in measures
            for i in range(8)
        ],
    }
    assert coverage(payload) == {
        "labor_productivity": 8,
        "output": 8,
        "hours_worked": 8,
        "hourly_compensation": 8,
        "unit_labor_costs": 8,
    }
    validate_coverage(payload)
