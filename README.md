# EconAlert

## 概要
EconAlertは、経済指標を自動的にDiscordに通知するボットです。Alpha Vantage APIを使用し、GitHub Actionsで自動実行されます。

## 特徴
- 対象：日本、アメリカ、欧州、中国、インド、OPEC
- 指標：インフレ率、賃金、輸出入データ
- 週次自動更新
- 無料APIプラン対応

## 構成
```
econalert/
├── .github/workflows/economic_calendar.yml
├── src/
│   ├── config.py  # 設定管理
│   ├── api.py     # データ取得
│   ├── filters.py # データフィルタリング
│   ├── formatter.py # メッセージ整形
│   └── notifier.py # Discord通知
├── tests/         # 各モジュールのテスト
└── main.py        # エントリーポイント
```

## セットアップ
1. リポジトリをクローン
2. 依存関係をインストール: `pip install -r requirements.txt`
3. `.env`ファイルに環境変数を設定:
   ```
   ALPHA_VANTAGE_API_KEY=your_key
   DISCORD_WEBHOOK_URL=your_url
   ```
4. GitHubリポジトリの"Secrets"に上記の環境変数を設定
5. GitHub Actionsを有効化

## カスタマイズ
- `src/config.py`: 監視対象国・指標の変更
- `.github/workflows/economic_calendar.yml`: 実行頻度の調整
- `src/formatter.py`: 通知メッセージのフォーマット変更

## 動作フロー
1. GitHub Actionsが週次でトリガー
2. `main.py`が実行される
3. Alpha Vantage APIからデータ取得
4. 関連データをフィルタリング
5. メッセージを整形
6. Discordに通知を送信

## 使用例
```python
from src import api, filters, formatter, notifier

def main():
    raw_data = api.fetch_economic_calendar()
    filtered_data = filters.filter_events(raw_data)
    formatted_message = formatter.format_message(filtered_data)
    notifier.send_discord_message(formatted_message)

if __name__ == "__main__":
    main()
```

## テスト
- 実行: `pytest tests/`
- カバレッジ確認: `pytest --cov=src tests/`

## トラブルシューティング
1. API制限エラー: `src/config.py`の`API_CALL_DELAY`を調整
2. 通知未着: Webhook URLとDiscord設定を確認
3. GitHub Actions未実行: ワークフローファイルとリポジトリ権限を確認

## 拡張計画
- グラフィカルな指標視覚化
- 複数チャンネル同時通知
- カスタムアラート設定
- Web管理パネル
- 追加データソース統合

## 注意事項
- Alpha Vantage APIの利用制限に注意してください。
- 経済データは参考情報です。投資判断は自己責任で行ってください。

## サポート
問題や提案がある場合は、GitHubのIssueを開いてください。

## ライセンス
MITライセンスの下で公開されています。詳細は`LICENSE`ファイルを参照してください。

詳細な使用方法や貢献ガイドラインについては、プロジェクトのWikiを参照してください。
