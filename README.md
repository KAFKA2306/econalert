# EconAlert — 公式経済指標データ基盤

EconAlertは、経済指標を一次情報から取得・監査し、機械利用可能なJSON/CSVへ配布するための小さなデータ基盤です。Discord通知botの旧構想から、まず正準データ層を独立して実装しています。

## 現在の実装

最初のデータセットとして、U.S. Bureau of Labor Statistics (BLS) のConsumer Price Indexを収録しています。

- 正準snapshot: `data/official/bls-cpi-2026-06.json`
- 配布: `api/v1/manifest.json`, `latest.json`, `categories.json`, `categories.csv`
- 生成: `scripts/build_public_api.py`
- 検証: `tests/test_public_api.py`
- CI: `.github/workflows/data-integrity.yml`

2026年6月CPIの公式releaseは2026年7月14日です。次回の2026年7月CPIは2026年8月12日 8:30 a.m. ETに公表予定です。値や予定時刻は更新時にBLS公式ページで再確認します。

## データ契約

- 元snapshotを履歴として保存し、上書き削除しない
- publisher、release ID、対象期間、取得日時、source URL、rights/termsを保存する
- カテゴリー名を主キー相当として同一snapshot内の重複を拒否する
- headline値とカテゴリー表のAll items / core CPIを相互検証する
- 配布物のbyte数とSHA-256をmanifestへ記録する
- 推定値や未確認値を補完しない

詳細は [`docs/data-api.md`](docs/data-api.md) を参照してください。

## 再生成と検証

```bash
python scripts/build_public_api.py
python -m pip install pytest
python -m pytest -q
```

通常CIは外部BLSへアクセスせず、保存済みsnapshotから決定的に配布物を再生成します。これにより外部負荷を抑え、同じcommitから同じ配布内容を再現できます。

## 出典・利用条件

BLS公開物は、過去に著作権保護された写真・イラスト等を除きpublic domainです。BLSは出典と取得日の明記を求めています。本リポジトリはBLSロゴ・画像を再配布しません。

- CPI: https://www.bls.gov/cpi/
- Current release: https://www.bls.gov/news.release/cpi.nr0.htm
- Copyright: https://www.bls.gov/opub/copyright-information.htm
- API Terms: https://www.bls.gov/developers/termsOfService.htm

BLSは取得後の派生データ・分析の品質や適時性を保証しません。本リポジトリの加工結果も投資助言ではありません。

## 今後

同じ契約に従ってPPI、雇用統計、賃金等を追加できますが、各指標ごとに一次source、release時点、改訂方針、利用条件を独立に保存します。通知機能は正準データ層の後段として扱います。
