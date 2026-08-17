# EconAlert — 公式経済指標を発表回ごとに確認できるデータ基盤

[![Data integrity](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml/badge.svg)](https://github.com/KAFKA2306/econalert/actions/workflows/data-integrity.yml)

EconAlertは、経済指標を公式発表から保存し、**どの発表回の・どの対象期間の・いつ取得した値か**を確認したうえでJSON/CSVとして利用できるようにする小さなデータ基盤です。現在の中心は通知botではなく、後段の分析や通知へ渡せる再現可能な公式データです。

## 目的

経済指標を早く通知することより、利用者が次を確認してから使える状態を優先します。

- 発表元とsource URL
- release IDと対象期間
- 取得日時
- 保存したsnapshotの内容
- 配布ファイルのSHA-256とbyte数
- 同じcommitから同じ配布物を再生成できること

予想値・未確認値・派生値を、公式発表値として保存しません。

## 設計方針

1. 公式発表ごとにsnapshotを保存し、過去の発表を上書きしません。
2. headline値とカテゴリー表の対応を検証します。
3. publisher、release ID、対象期間、取得日時、source URL、rights/termsをsnapshotと一緒に保持します。
4. 配布物のbyte数とSHA-256をmanifestへ記録します。
5. 通知や分析は、保存・検証済みデータの後段に置きます。

一般的な経済カレンダーや速報通知との違いは、**「いつ発表されたどの公式値を使ったか」を後から確認し、同じ入力から配布物を再生成できること**です。

## 現在のデータ

最初のデータセットとして、U.S. Bureau of Labor Statistics (BLS) の **Consumer Price Index (CPI)** を収録しています。

- 保存済みsnapshot: `data/official/bls-cpi-2026-06.json`
- 対象期間: 2026年6月
- 公式release: 2026年7月14日
- 配布: `api/v1/manifest.json`, `api/v1/latest.json`, `api/v1/categories.json`, `api/v1/categories.csv`
- 生成: `scripts/build_public_api.py`
- 検証: `tests/test_public_api.py`
- CI: `.github/workflows/data-integrity.yml`

**保存済みデータは2026年6月CPIです。** 2026年7月CPIは2026年8月12日に公表済みですが、このrepositoryの保存済みsnapshotにはまだ追加していません。BLSの現行scheduleでは、次の **2026年8月CPIは2026年9月11日 8:30 a.m. ET** に公表予定です。release scheduleは変更される可能性があるため、更新時にはBLS公式scheduleを再確認します。

BLS CPI release schedule: https://www.bls.gov/schedule/news_release/cpi.htm

## 利用の流れ

```text
BLS official release
  -> 保存済みsnapshot
  -> 整合性検証
  -> manifest / JSON / CSV
  -> 分析・通知などの利用側
```

`api/v1/latest.json` は「repositoryに保存されている最新snapshot」を表します。BLSがすでに公表した最新月と一致しない場合があります。保存していない月を推定して補完しません。

## データ契約

- 元snapshotを履歴として保存し、上書き削除しない
- publisher、release ID、対象期間、取得日時、source URL、rights/termsを保存する
- カテゴリー名を主キー相当として同一snapshot内の重複を拒否する
- headline値とカテゴリー表のAll items / core CPIを相互検証する
- 配布物のbyte数とSHA-256をmanifestへ記録する
- 予想値・未確認値・欠損値を公式値として補完しない

詳細は [`docs/data-api.md`](docs/data-api.md) を参照してください。

## 再生成と検証

```bash
python scripts/build_public_api.py
python -m pip install pytest
python -m pytest -q
```

通常CIは外部BLSへアクセスせず、保存済みsnapshotから決定的に配布物を再生成します。外部サイトの一時的な状態に左右されず、同じcommitから同じ配布内容を確認できます。

## 出典・利用条件

- CPI: https://www.bls.gov/cpi/
- Current release: https://www.bls.gov/news.release/cpi.nr0.htm
- Release schedule: https://www.bls.gov/schedule/news_release/cpi.htm
- Copyright: https://www.bls.gov/opub/copyright-information.htm
- API Terms: https://www.bls.gov/developers/termsOfService.htm

BLS Public Data APIの利用条件では、取得日を示してBLSを出典として明記すること、取得後のデータや分析についてBLSが品質・適時性を保証しない旨を明示することが求められています。本repositoryはBLSロゴを使用しません。

本repositoryの加工結果も投資助言ではありません。

## 今後

PPI、Employment Situation、賃金などを追加する場合も、指標ごとに公式source、release時点、改訂方針、利用条件を個別に保存します。通知機能は保存・検証済みデータの後段として扱い、未実装の通知機能を完成済みとは表示しません。