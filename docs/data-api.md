# EconAlert BLS CPI data API v1

`api/v1/` は、BLS公式Consumer Price Indexリリースから確認した公開データを機械利用できる形で配布します。

## 正準ソース

- Publisher: U.S. Bureau of Labor Statistics (BLS)
- Release: Consumer Price Index - June 2026 (`USDL-26-1191`)
- Release date: 2026-07-14
- Source: https://www.bls.gov/news.release/cpi.nr0.htm
- Category chart: https://www.bls.gov/news.release/charts/cpi-cpi_rc_1cpibycat.stm
- Copyright: https://www.bls.gov/opub/copyright-information.htm
- Terms: https://www.bls.gov/developers/termsOfService.htm

BLS公開物は、過去に著作権保護された写真・イラスト等を除きpublic domainです。本リポジトリはBLSロゴや画像を再配布せず、数値・メタデータのみを保存します。BLSの要請に従い、出典と取得日時を記録します。

## エンドポイント

- `manifest.json`: 件数、出典snapshot、SHA-256、byte数、利用条件
- `latest.json`: headline CPIと次回公表予定
- `categories.json`: 38カテゴリーの12か月変化率（NSA）
- `categories.csv`: 同一データのCSV

## 欠損・改訂

値を推定補完しません。BLSはCPIの直近10〜12か月の指数が改訂対象になり得るとしています。新しいreleaseを取り込む場合は既存snapshotを削除せず、別ファイルとして履歴を保持します。

## 差分同期

最初に`manifest.json`を取得し、`files.<name>.sha256`が手元の値と異なる配布物だけ再取得してください。`cache.revalidate_seconds`は再確認の目安であり、HTTPキャッシュ保証ではありません。

## Python例

```python
import json
from urllib.request import urlopen

url = "https://raw.githubusercontent.com/KAFKA2306/econalert/main/api/v1/latest.json"
with urlopen(url) as response:
    latest = json.load(response)
print(latest["period"], latest["headline"]["all_items_12m_nsa_pct"])
```

## 更新方針

BLSへのアクセスはreleaseごとの明示的な更新時に限定し、通常CIでは保存済みsnapshotのみを検証・再生成します。頻繁なポーリングを行いません。
