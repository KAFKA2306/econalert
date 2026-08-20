# U.S. corporate profit share and productivity distribution

This dataset keeps the inputs needed to test whether unusually high U.S. corporate profits are associated with changes in productivity, labor costs, value-added prices, and nonfinancial-corporate unit profits.

## Canonical sources

### Corporate profits and GDI

The original publisher is the U.S. Bureau of Economic Analysis (BEA).

- Corporate Profits: https://www.bea.gov/data/income-saving/corporate-profits
- Gross Domestic Income: https://www.bea.gov/data/income-saving/gross-domestic-income

BEA's API requires a registered 36-character UserID. The scheduled no-secret collector therefore retrieves the same BEA-published `CPROFIT` and `GDI` series through the Federal Reserve Bank of St. Louis FRED distribution endpoint and records both the retrieval provider and original publisher.

- CPROFIT metadata: https://fred.stlouisfed.org/series/CPROFIT
- GDI metadata: https://fred.stlouisfed.org/series/GDI
- BEA API registration/documentation: https://apps.bea.gov/api/signup/

The collector never labels FRED as the original publisher of these national-account series.

### Productivity and distribution

The U.S. Bureau of Labor Statistics (BLS) is the original publisher and retrieval provider.

- Public Data API: https://api.bls.gov/publicAPI/v2/timeseries/data/
- Major Sector Productivity bulk files: https://download.bls.gov/pub/time.series/pr/
- Current Productivity and Costs release: https://www.bls.gov/news.release/prod2.nr0.htm

Every live collection verifies the pinned series IDs against BLS's current `pr.series`, `pr.measure`, `pr.sector`, and `pr.duration` metadata before accepting values. If an upstream definition changes, collection fails rather than silently remapping the series.

## Stored evidence

Content-addressed snapshots:

```text
data/official/us-profit-distribution-current/<source-fingerprint>.json
```

The source fingerprint covers the FRED CPROFIT/GDI response, BLS API response, and the BLS metadata files used to validate series identity. The snapshot retains retrieval time, source URLs, original publisher, series IDs, units, formula definitions, and SHA-256 hashes of every raw response used to build the selected dataset.

A changed response creates a new snapshot. Existing snapshots are never overwritten.

## Distribution views

Deterministic files generated only from the latest committed snapshot:

```text
api/v1/profit-distribution/latest.json
api/v1/profit-distribution/summary.json
api/v1/profit-distribution/corporate-profit-share.csv
api/v1/profit-distribution/productivity-distribution.csv
api/v1/profit-distribution/manifest.json
```

`manifest.json` records the source snapshot hash and output hashes.

## Metrics

### BEA national-account series

For each quarter where both inputs are available:

```text
corporate_profits_gdi_pct = 100 * CPROFIT / GDI
corporate_profits_yoy_pct = 100 * (CPROFIT_t / CPROFIT_t-4 - 1)
gdi_yoy_pct = 100 * (GDI_t / GDI_t-4 - 1)
```

`CPROFIT` and `GDI` are both billions of dollars at seasonally adjusted annual rates, so their ratio is dimensionless.

### BLS nonfarm business

Stored as separate BLS-published transformations:

- labor productivity: YoY and previous-quarter annualized rate
- hourly compensation: YoY and previous-quarter annualized rate
- unit labor costs: YoY and previous-quarter annualized rate
- value-added output price deflator: YoY and previous-quarter annualized rate

Two labor-share change calculations are added from the YoY rates:

```text
log approximation = ULC YoY - value-added-price YoY

rate-consistent change =
100 * ((1 + ULC_YoY/100) / (1 + value_added_price_YoY/100) - 1)
```

The second expression is preferred when comparing the published rounded growth rates because the labor share is proportional to unit labor cost divided by the value-added output price. Neither field is stored as the BLS labor-share level.

### BLS nonfinancial corporations

Stored:

- labor productivity: YoY and previous-quarter annualized rate
- unit labor costs: YoY and previous-quarter annualized rate
- value-added output price deflator: YoY and previous-quarter annualized rate
- unit profits: YoY and previous-quarter annualized rate

BLS defines unit profits as corporate profits before tax with inventory valuation and capital consumption adjustments per unit of real value added.

## Schedule

`.github/workflows/profit-distribution.yml` runs weekly on Thursday and can also be dispatched manually. Pull requests run the unit tests and make a live endpoint read without committing evidence. `main` runs collect → build views → commit only when source or derived files change.

The underlying BEA and BLS statistics are quarterly; a weekly check is intentionally more frequent than the release cadence without making daily network calls that cannot produce new quarterly observations.

## Fail-closed conditions

Collection fails when any of the following occur:

- FRED no longer returns both `CPROFIT` and `GDI`
- a value is missing or malformed for a supposedly complete row
- BLS omits any required series
- BLS series metadata no longer match the pinned sector/measure/duration definitions
- there are fewer than eight complete quarterly observations in the requested BLS window
- there are fewer than eight complete CPROFIT/GDI observations
