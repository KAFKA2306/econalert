from scripts.collect_productivity import parse_current_table
from scripts.collect_productivity_vintages import parse_nonfarm_b1


def test_current_table_requires_and_parses_quarters():
    raw = b"""<html><body><pre>
Percent change from previous quarter at annual rate (5)
2026 II 1.4 1.7 0.3 2.7 -3.1 1.3 14.0 7.0
I 0.8 r 1.5 r 0.7 2.1 -1.4 1.3 r 9.8 r 5.1 r
2025 IV 1.6 1.3 -0.2 3.7 1.2 2.1 4.7 3.3
III 5.2 5.4 0.2 6.2 3.0 1.0 7.9 4.1
II 4.2 5.2 1.0 1.2 -0.5 -2.9 7.8 1.8
I -0.9 -0.9 0.0 6.3 2.5 7.3 -1.5 3.2
2024 IV 1.4 1.7 0.3 4.4 1.1 2.9 0.3 1.7
III 3.7 3.9 0.2 4.8 3.5 1.1 0.6 0.9
Percent change from corresponding quarter of previous year
</pre></body></html>"""
    rows = parse_current_table(raw)
    assert len(rows) == 8
    assert rows[0]["period"] == "2026-Q2"
    assert rows[1]["period"] == "2026-Q1"
    assert rows[-1]["period"] == "2024-Q3"
    assert rows[0]["labor_productivity"] == 1.4
    assert rows[1]["unit_labor_costs"] == 1.3


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
