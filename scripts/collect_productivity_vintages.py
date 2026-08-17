#!/usr/bin/env python3
"""Collect BLS Productivity and Costs release vintages from archived releases."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

REVISED_RELEASES = (
    ("2024-Q3", "2024-12-10", "https://www.bls.gov/news.release/archives/prod2_12102024.htm"),
    ("2024-Q4", "2025-03-06", "https://www.bls.gov/news.release/archives/prod2_03062025.htm"),
    ("2025-Q1", "2025-06-05", "https://www.bls.gov/news.release/archives/prod2_06052025.htm"),
    ("2025-Q2", "2025-09-04", "https://www.bls.gov/news.release/archives/prod2_09042025.htm"),
    ("2025-Q3", "2026-01-29", "https://www.bls.gov/news.release/archives/prod2_01292026.htm"),
    ("2025-Q4", "2026-03-24", "https://www.bls.gov/news.release/archives/prod2_03242026.htm"),
    ("2026-Q1", "2026-06-04", "https://www.bls.gov/news.release/archives/prod2_06042026.htm"),
)
METRICS = (
    "labor_productivity",
    "output",
    "hours_worked",
    "hourly_compensation",
    "real_hourly_compensation",
    "unit_labor_costs",
)
NUMBER = r"[-+]?\d+(?:\.\d+)?"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert"})
    with urlopen(req, timeout=60) as response:
        return response.read()


def html_text(raw: bytes) -> str:
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def parse_nonfarm_b1(raw: bytes) -> dict[str, dict[str, float]]:
    text = html_text(raw)
    marker = text.find("Table B1.")
    if marker < 0:
        raise ValueError("Table B1 not found")
    table = text[marker:]
    row = re.search(
        rf"Nonfarm business\s+Revised\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})"
        rf"\s+Previously published\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})",
        table,
        flags=re.IGNORECASE,
    )
    if not row:
        raise ValueError("nonfarm business revised/previous rows not found in Table B1")
    values = [float(value) for value in row.groups()]
    revised = dict(zip(METRICS, values[:6], strict=True))
    previous = dict(zip(METRICS, values[6:], strict=True))
    return {"revised": revised, "previously_published": previous}


def collect() -> dict[str, object]:
    releases = []
    for quarter, release_date, url in REVISED_RELEASES:
        raw = fetch(url)
        values = parse_nonfarm_b1(raw)
        revisions = {
            metric: round(values["revised"][metric] - values["previously_published"][metric], 10)
            for metric in METRICS
        }
        releases.append(
            {
                "quarter": quarter,
                "release_date": release_date,
                "status": "revised",
                "sector": "Nonfarm business",
                "rate_basis": "percent change from previous quarter at annual rate",
                "source_url": url,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                **values,
                "revision_percentage_points": revisions,
            }
        )
    return {
        "schema_version": 1,
        "publisher": "U.S. Bureau of Labor Statistics",
        "dataset": "Productivity and Costs",
        "table": "B1",
        "releases": releases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/official/bls-productivity-vintages.json"),
    )
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['releases'])} release vintages -> {args.output}")


if __name__ == "__main__":
    main()
