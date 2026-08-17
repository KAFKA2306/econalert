#!/usr/bin/env python3
"""Collect the current BLS nonfarm-business productivity table."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.bls.gov/news.release/prod2.t02.htm"
NUMBER = r"[-+]?\d+(?:\.\d+)?"
METRICS = (
    "labor_productivity",
    "output",
    "hours_worked",
    "hourly_compensation",
    "real_hourly_compensation",
    "unit_labor_costs",
    "unit_nonlabor_payments",
    "output_price_deflator",
)
ROMAN_QUARTER = {"I": 1, "II": 2, "III": 3, "IV": 4}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def html_text(raw: bytes) -> str:
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def parse_current_table(raw: bytes) -> list[dict[str, object]]:
    text = html_text(raw)
    start = text.find("Percent change from previous quarter at annual rate")
    end = text.find("Percent change from corresponding quarter of previous year", start)
    if start < 0 or end < 0:
        raise ValueError("BLS Table 2 quarterly-change section not found")
    section = text[start:end]
    value = rf"({NUMBER})(?:\s+r)?"
    pattern = re.compile(
        rf"(?:(20\d{{2}})\s+)?(IV|III|II|I)\s+"
        + r"\s+".join([value] * len(METRICS))
    )
    observations: list[dict[str, object]] = []
    year: int | None = None
    for match in pattern.finditer(section):
        if match.group(1):
            year = int(match.group(1))
        if year is None:
            raise ValueError("quarter row appeared before a year")
        quarter = ROMAN_QUARTER[match.group(2)]
        values = [float(item) for item in match.groups()[2:]]
        observations.append(
            {
                "period": f"{year}-Q{quarter}",
                **dict(zip(METRICS, values, strict=True)),
            }
        )
    if len(observations) < 8:
        raise ValueError(f"expected at least 8 quarterly observations, found {len(observations)}")
    return observations


def collect() -> dict[str, object]:
    raw = fetch(SOURCE_URL)
    observations = parse_current_table(raw)
    return {
        "schema_version": 1,
        "publisher": "U.S. Bureau of Labor Statistics",
        "dataset": "Productivity and Costs",
        "table": "2",
        "sector": "Nonfarm business",
        "rate_basis": "percent change from previous quarter at annual rate",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_url": SOURCE_URL,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "observations": observations,
    }


def write_snapshot(payload: dict[str, object], output_dir: Path) -> Path:
    if len(payload["observations"]) < 8:
        raise ValueError("current productivity snapshot requires at least 8 quarters")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{str(payload['source_sha256'])[:16]}.json"
    if not path.exists():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/official/bls-productivity-current"))
    args = parser.parse_args()
    payload = collect()
    path = write_snapshot(payload, args.output_dir)
    print(f"wrote {len(payload['observations'])} quarters -> {path}")


if __name__ == "__main__":
    main()
