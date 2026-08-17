# EconAlert — 公式経済指標を発表回ごとに保存する

[![Data integrity](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml)
[![BLS productivity](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml)

公式経済指標を、**発表時点・対象期間・取得元を失わず**保存し、後段の分析や通知から再利用できるようにするrepositoryです。正準責務は `economic-releases` へのrename後も同じです。

予想値・推定値・欠損補完を公式発表値として保存しません。

## BLS Productivity and Costs

ARK Big Ideas 2026 の `AI Productivity` を実体経済側から検証するため、U.S. Bureau of Labor Statistics (BLS) の Productivity and Costs を収集します。

一次情報:

- https://www.bls.gov/productivity/
- https://www.bls.gov/news.release/prod2.t02.htm
- https://www.bls.gov/bls/news-release/prod.htm

### Current revised series

[`scripts/collect_productivity.py`](scripts/collect_productivity.py) はBLS公式releaseの Table 2 から、nonfarm business の productivity、output、hours、hourly compensation、real hourly compensation、unit labor costsを取得します。

保存先:

```text
data/official/bls-productivity-current/<source-fingerprint>.json
```

source HTMLのSHA-256からpathを決めるため、同じreleaseを重複保存せず、BLSが表を更新した場合も以前のsnapshotを上書きしません。`Percent change from previous quarter at annual rate` のquarterly observationが8四半期未満なら収集を失敗させます。

### Release vintage / revision

[`scripts/collect_productivity_vintages.py`](scripts/collect_productivity_vintages.py) はBLS公式archiveのrevised releaseにある Table B1 から、nonfarm businessの次を保存します。

- revised value
- previously published value
- revision in percentage points
- quarter / release date / status
- source URL / source SHA-256

保存先:

```text
data/official/bls-productivity-vintages.json
```

対象は2024-Q3から2026-Q1までの7 revised releasesです。2026-Q2以降は同じworkflowで継続追加します。BLS archive自身が、archive値は後続releaseで改訂される場合があると明記しているため、current revised seriesとrelease vintageは同じ値として扱いません。

### 自動取得と検証

[`BLS productivity`](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml) は毎週BLS一次情報を確認し、source内容が変わったときだけsnapshotをcommitします。collector変更がmainへ入った直後にも実行するため、実データをseedします。

```bash
python -m pip install pytest
python -m pytest -q tests/test_productivity_collector.py
python scripts/collect_productivity.py
python scripts/collect_productivity_vintages.py
```

Pull Requestではlive BLS HTMLを実取得し、Table 2 / Table B1の構造変化をfail closedで検出します。

## CPI

既存のBLS CPI snapshotと配布APIは別release系列として維持しています。

- `data/official/bls-cpi-2026-06.json`
- `api/v1/manifest.json`
- `api/v1/latest.json`
- `api/v1/categories.json`
- `api/v1/categories.csv`
- 生成: `scripts/build_public_api.py`

`api/v1/latest.json` はrepositoryに保存されている最新CPI snapshotを表し、BLSが公表済みの最新月を推測で補完しません。

## データ契約

- official sourceだけをfactとして保存する
- release時点のsnapshotを上書きしない
- current revised seriesとrelease vintageを区別する
- source URL、対象期間、取得日時またはrelease date、SHA-256を保持する
- percent change、index、level、annualized rateを混在させない
- 欠損・revision・series変更を推測で補完しない
- 同じcommitの保存済み入力からderived outputを再生成できるようにする

## 既存CPI配布物の再生成

```bash
python scripts/build_public_api.py
python -m pip install pytest
python -m pytest -q
```

通常の `Data integrity` CIは保存済みsnapshotから決定的に既存CPI APIを再生成します。Productivity workflowだけがBLS外部sourceを取得します。

## 出典・利用条件

- BLS Productivity: https://www.bls.gov/productivity/
- BLS Productivity archive: https://www.bls.gov/bls/news-release/prod.htm
- BLS CPI: https://www.bls.gov/cpi/
- Copyright: https://www.bls.gov/opub/copyright-information.htm
- API Terms: https://www.bls.gov/developers/termsOfService.htm

本repositoryの加工結果は投資助言ではありません。
