from scripts.collect_productivity import select_series


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
