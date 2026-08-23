# EconAlert — official economic releases

[![Data integrity](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml)
[![BLS productivity](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml)
[![Deploy Pages](https://github.com/KAFKA2306/econalert/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/pages.yml)

U.S. Bureau of Labor Statistics (BLS) の公式releaseを、**対象期間・release date・取得元・revisionを失わず**保存します。予想値・推定値・欠損補完をofficial observationとして保存しません。

## Public dashboard

- Daily entry point: https://kafka2306.github.io/econalert/
- latest BLS Productivity and Costs observation
- labor productivity / real hourly compensation / unit labor costs
- previous-quarter rate difference using the same official definition
- CPI release period / release date / freshness state
- links from the public values back to canonical JSON and revision evidence

GitHub Pagesは`api/v1/`をread-onlyで投影します。monthly CPIとquarterly productivityを同じcadenceや独自scoreへ潰しません。保存済みCPI snapshotの`next_release`が既に過ぎている場合は、未取得の新releaseを推測せず**stale**と表示します。

## BLS Productivity and Costs

Canonical output:

- [`api/v1/productivity/latest.json`](api/v1/productivity/latest.json) — current revised quarterly series
- [`api/v1/productivity/revisions.json`](api/v1/productivity/revisions.json) — revised / previously published evidence
- [`api/v1/productivity/manifest.json`](api/v1/productivity/manifest.json) — provenance

[`scripts/collect_productivity.py`](scripts/collect_productivity.py) はBLS Public Data APIからnonfarm businessの次のseriesを取得します。

- labor productivity: `PRS85006092`
- output: `PRS85006042`
- hours worked: `PRS85006032`
- hourly compensation: `PRS85006102`
- real hourly compensation: `PRS85006152`
- unit labor costs: `PRS85006112`

単位は `percent change from previous quarter at annual rate` に固定します。API responseはSHA-256でcontent-addressed保存し、後続releaseで過去値が改訂されても以前のsnapshotを上書きしません。

`BLS productivity` workflowは定期的にBLS Public Data APIを確認し、responseが変わった場合だけ新snapshotとderived viewを保存します。

## CPI

Canonical output:

- [`api/v1/latest.json`](api/v1/latest.json) — repositoryに保存された最新CPI release snapshot
- [`api/v1/categories.json`](api/v1/categories.json) / [`categories.csv`](api/v1/categories.csv) — 12-month category observations
- [`api/v1/manifest.json`](api/v1/manifest.json) — source snapshot / SHA-256 / derived file hashes

`api/v1/latest.json` は**repositoryに取り込まれた最新release**であり、BLSがその後に公表した値を推測で補完しません。そのためPagesではrelease scheduleを使ってfresh/staleを明示します。

CPI連動契約の計算境界を確認するsynthetic PoCは [CPI contract escalation PoC](docs/business/cpi-contract-escalation.md) に分離しています。実顧客の契約や個人情報は扱いません。

## Data contract

- official sourceだけをfactとして保存する
- release/API snapshotを上書きしない
- current revised seriesとhistorical release vintageを区別する
- source URL、対象期間、release/retrieval timeを保持する
- live API responseはSHA-256を保持する
- percent change、index、level、annualized rateを混在させない
- monthly / quarterly cadenceを不正比較しない
- missing / revision / series changeを推測で補完しない
- 同じcommitの保存済み入力からderived outputを再生成できる

## Verification

```bash
python -m pytest -q
python scripts/build_public_api.py
```

- `Data integrity` は保存済みsnapshotからCPI APIを決定的に再生成します。
- `BLS productivity` はBLS Public Data APIをlive取得してcollector contractを検証します。
- `Deploy Pages` はcanonical APIをartifactへ同梱し、deploy後に`deployment.json`のcommit SHAと公開JSON/UIを照合します。

## Primary sources

- BLS Public Data API: https://www.bls.gov/developers/home.htm
- BLS Productivity: https://www.bls.gov/bls/news-release/prod.htm
- BLS CPI: https://www.bls.gov/cpi/
- BLS Copyright: https://www.bls.gov/opub/copyright-information.htm
- BLS API Terms: https://www.bls.gov/developers/termsOfService.htm

本repositoryの加工結果は投資助言ではありません。
