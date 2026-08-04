# EconAlert — 経済指標をDiscordへ通知するbotの構想メモ

EconAlertは、経済指標を取得し、重要な更新をDiscordへ通知する仕組みとして2024年9月に作成した構想メモです。

**現在、このリポジトリにはREADME以外の実装fileがありません。** `main.py`、`src/`、`tests/`、`requirements.txt`、GitHub Actions workflowは存在せず、bot、週次実行、Alpha Vantage連携、Discord通知は稼働していません。

> **状態:** design-only / 未実装  
> **作成時期:** 2024年9月  
> **定期通知:** 未登録・未稼働  
> **実行可能なcode:** なし

---

## 想定していた目的

次のような経済dataを定期取得し、Discordへ短く通知する構想でした。

- inflation
- wages
- imports / exports
- 日本、米国、欧州、中国、インド、OPECなどの地域別data
- 発表時刻、前回値、予想値、実績値

通知は、単に数値を投稿するのではなく、対象期間、単位、改訂、source URL、取得時刻を含める必要があります。

---

## 旧READMEに書かれていたが、存在しないもの

旧READMEは次の構造を実装済みとして説明していました。

```text
.github/workflows/economic_calendar.yml
src/config.py
src/api.py
src/filters.py
src/formatter.py
src/notifier.py
tests/
main.py
requirements.txt
```

2026年8月4日のdefault branchには、これらを確認できませんでした。

そのため、次の記述も現在事実ではありません。

- Alpha Vantage APIから自動取得する
- GitHub Actionsが週次実行する
- Discord webhookへ通知する
- pytestが存在する
- coverageを測定できる
- 複数地域を現在監視している

---

## 実装する場合の推奨境界

この構想を再開する場合は、KAFKA2306の横断的な定期処理として`com`にRecurring Serviceを作成し、目的、対象指標、source、鮮度、通知条件、停止条件を先に定義します。

実装の最小構成:

```text
src/
  models.py       指標eventの型
  sources/        公式data source adapter
  normalize.py    単位・時点・改訂の正規化
  select.py       通知対象の決定
  format.py       Discord message生成
  notify.py       webhook送信
main.py
tests/
.github/workflows/
```

### sourceの選び方

Alpha Vantageだけを唯一の正準にしません。指標ごとに、中央銀行、統計機関、国際機関などの一次sourceを優先します。

例:

- 日本銀行
- 総務省統計局
- 内閣府
- Federal Reserve / FRED
- U.S. Bureau of Labor Statistics
- Eurostat
- European Central Bank
- 中国国家統計局
- IMF
- OECD
- OPEC

API・公開file・calendarの利用条件と改訂policyを記録します。

---

## 通知契約

将来実装する場合、Discord通知には最低限次を含めます。

- 指標の正式名称
- 対象国・地域
- 対象期間
- 発表日時とtimezone
- 実績値
- 前回値と改訂値
- 予想値を使う場合はprovider
- 単位
- source URL
- 取得時刻
- dataが古い・欠損・未確認の場合の警告

通知がないことを「変化なし」と判断するには、取得成功と比較処理の証拠が必要です。

---

## セキュリティ

公開リポジトリへ保存しないもの:

- API key
- Discord webhook URL
- bot token
- private channel情報
- 認証済みresponse

secretはGitHub Actions Secretsまたは実行環境のsecret管理へ置きます。logへwebhook URLを出力しません。

---

## 現在の利用方法

現在は設計メモの閲覧だけです。

```bash
git clone https://github.com/KAFKA2306/econalert.git
cd econalert
```

install、test、run commandはありません。

---

## 既知の制約

- codeとworkflowがありません。
- data sourceの現行仕様を確認していません。
- Discord通知は稼働していません。
- 週次scheduleは存在しません。
- 旧READMEのmodule例は実装ではありません。
- 経済指標の発表日時、値、改訂は一次sourceで再確認が必要です。

---

## 今後の判断

- `investor`の市場data基盤へ統合する
- `com`のRecurring Serviceとして再設計する
- 構想メモとしてarchiveする

単独botを新設する場合も、同じ経済dataを複数repoで二重収集しないよう正準を決めます。

---

## 免責

経済指標の通知は投資助言、売買推奨、将来予測ではありません。dataの欠損、改訂、時刻差、API障害があり得ます。

**README実体監査:** 2026年8月4日
