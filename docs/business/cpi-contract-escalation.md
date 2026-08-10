# CPI contract escalation evidence pack

CPI連動条項を持つB2B契約について、**顧客が明示したBLS series IDと観測期間**を使い、更新時の計算根拠を人がレビューできる形へ整えるPoCです。

## 無料demo

公開repositoryの `contracts/synthetic-demo.json` と `data/synthetic/cpi-index-demo.json` は計算engine確認専用のsynthetic fixtureです。値はBLS実測値ではありません。

```bash
python scripts/contract_escalation.py \
  contracts/synthetic-demo.json \
  data/synthetic/cpi-index-demo.json \
  --output /tmp/contract-escalation-report.json
```

reportはseries ID、base/comparison period、使用index、式、floor/cap、snapshot SHA-256を保持します。

## 有償PoCの境界

想定単位は1社・最大20契約・1更新サイクルです。顧客側で契約書からseries ID、観測期間ルール、formula、存在する場合だけfloor/cap、条項確認状態を入力します。public repositoryには顧客名、契約本文、価格、連絡先を保存しません。

本機能はseriesを自動選択しません。契約profileとsource snapshotのseries IDが一致しなければ `SOURCE_MISMATCH`、comparison observationが未公表なら `WAITING_FOR_RELEASE`、baseや契約条件が不足する場合は成功値を返しません。

## 保証しないこと

- 契約条項の法的解釈
- 値上げ可否の判断
- 推奨価格
- 未取得のBLS値の推測
- 類似CPI seriesへの自動置換

BLS Public Data APIはseries IDを指定して時系列を取得する公式APIです。実顧客PoCでは、契約書に明記されたseries IDの公式index-level snapshotを別途取得・履歴保存してから計算します。

## 次の実運用ゲート

1. 実契約でseries IDを確認する。
2. BLS公式APIからそのseriesだけを取得し、取得日時・source URL・raw bytes SHA-256を保存する。
3. synthetic fixtureではなく公式snapshotをengineへ渡す。
4. reportをFinance/RevOps/法務担当がレビューする。
5. 実際に発生したinquiry/demo/paid pilotだけをKPIへ記録する。
