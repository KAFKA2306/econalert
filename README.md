# EconAlert — 公式経済指標を発表回ごとに保存する

[![Data integrity](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml)
[![BLS productivity](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml)

公式経済指標を、**発表時点・対象期間・取得元を失わず**保存し、後段の分析や通知から再利用できるようにするrepositoryです。正準責務は `economic-releases` へのrename後も同じです。

予想値・推定値・欠損補完を公式発表値として保存しません。

## BLS Productivity and Costs

ARK Big Ideas 2026 の `AI Productivity` を実体経済側から検証するため、U.S. Bureau of Labor Statistics (BLS) の Productivity and Costs を収集します。

一次情報:

- https://api.bls.gov/publicAPI/v2/timeseries/data/
- https://www.bls.gov/developers/home.htm
- https://www.bls.gov/bls/news-release/prod.htm

### Current revised series

[`scripts/collect_productivity.py`](scripts/collect_productivity.py) はBLS Public Data APIから、nonfarm business の次の公式seriesを取得します。

- labor productivity: `PRS85006092`
- output: `PRS85006042`
- hours worked: `PRS85006032`
- hourly compensation: `PRS85006102`
- real hourly compensation: `PRS85006152`
- unit labor costs: `PRS85006112`

保存先:

```text
data/official/bls-productivity-current/<source-fingerprint>.json
```

API responseのSHA-256からpathを決めるため、同じresponseを重複保存せず、BLSが過去値を改訂した場合も以前のsnapshotを上書きしません。6指標が揃ったquarterly observationが8四半期未満なら収集を失敗させます。単位は `percent change from previous quarter at annual rate` として固定し、別単位のseriesを混ぜません。

### Historical release vintage / revision

[`data/official/bls-productivity-vintages.json`](data/official/bls-productivity-vintages.json) はBLS公式archiveの Table B1 にある `revised` と `previously published` を保存します。

対象は2024-Q3から2026-Q1までの7 revised releasesです。各rowにquarter、release date、source URL、source sectionと6指標の両値を保持します。archiveをGitHub Actionsから再取得する処理は、BLSがGitHub-hosted runnerからの `www.bls.gov` accessを403で拒否するため置きません。

以後のvintageは、Public Data API responseをcontent-addressed snapshotとして蓄積することで保持します。過去snapshotを更新しないため、同じquarterの値が後続releaseで変わった場合にcommit間でrevisionを再構成できます。

### 自動取得と検証

[`BLS productivity`](https://github.com/KAFKA2306/econalert/actions/workflows/productivity.yml) は毎週BLS Public Data APIを確認し、response内容が変わったときだけ新しいsnapshotをcommitします。collector変更がmainへ入った直後にも実行するため、初回実データもseedします。

```bash
python -m pip install pytest
python -m pytest -q tests/test_productivity_collector.py
python scripts/collect_productivity.py
```

Pull Requestでは同じPublic Data APIを実取得し、series欠落・8四半期未満・API failureをfail closedで検出します。

## CPI

既存のBLS CPI snapshotと配布APIは別release系列として維持しています。

- `data/official/bls-cpi-2026-06.json`
- `api/v1/manifest.json`
- `api/v1/latest.json`
- `api/v1/categories.json`
- `api/v1/categories.csv`
- 生成: `scripts/build_public_api.py`

`api/v1/latest.json` はrepositoryに保存されている最新CPI snapshotを表し、BLSが公表済みの最新月を推測で補完しません。

### CPI連動契約の計算PoC

契約書に明記されたBLS CPI series IDと観測期間を使い、更新時の計算根拠を人がレビューできる形で出力するsynthetic demoがあります。

- [PoCの範囲・入力・保証しないこと](docs/business/cpi-contract-escalation.md)
- [synthetic contract profile](contracts/synthetic-demo.json)
- [synthetic CPI fixture](data/synthetic/cpi-index-demo.json)

series IDを推測で選ばず、契約profileとsource snapshotが一致しない場合や必要な観測値が未公表の場合は成功値を返しません。実顧客の契約本文・価格・社名・連絡先はpublic repositoryへ保存しません。

## データ契約

- official sourceだけをfactとして保存する
- release/API snapshotを上書きしない
- current revised seriesとhistorical release vintageを区別する
- source URL、対象期間、取得日時またはrelease dateを保持する
- live API responseはSHA-256を保持する
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

- BLS Public Data API: https://www.bls.gov/developers/home.htm
- BLS Productivity archive: https://www.bls.gov/bls/news-release/prod.htm
- BLS CPI: https://www.bls.gov/cpi/
- Copyright: https://www.bls.gov/opub/copyright-information.htm
- API Terms: https://www.bls.gov/developers/termsOfService.htm

本repositoryの加工結果は投資助言ではありません。
