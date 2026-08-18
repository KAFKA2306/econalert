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

### PoCを相談する

[新規PoC相談を開始する](https://github.com/KAFKA2306/econalert/issues/new?title=CPI%E9%80%A3%E5%8B%95%E5%A5%91%E7%B4%84PoC%E3%81%AE%E7%9B%B8%E8%AB%87&body=%E5%85%AC%E9%96%8BIssue%E3%81%A7%E3%81%99%E3%80%82%E5%80%8B%E4%BA%BA%E6%83%85%E5%A0%B1%E3%83%BB%E5%A5%91%E7%B4%84%E6%9C%AC%E6%96%87%E3%83%BB%E4%BE%A1%E6%A0%BC%E3%83%BB%E8%AA%8D%E8%A8%BC%E6%83%85%E5%A0%B1%E3%81%AF%E8%A8%98%E8%BC%89%E3%81%97%E3%81%AA%E3%81%84%E3%81%A7%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84%E3%80%82%0A%0A-+%E6%A5%AD%E7%A8%AE%3A%0A-+%E5%A5%91%E7%B4%84%E6%95%B0%E3%81%AE%E7%9B%AE%E5%AE%89%3A%0A-+%E5%A5%91%E7%B4%84%E6%9B%B8%E3%81%ABBLS+series+ID%E3%81%8C%E6%98%8E%E8%A8%98%E3%81%95%E3%82%8C%E3%81%A6%E3%81%84%E3%82%8B%E3%81%8B%3A+%E3%81%AF%E3%81%84+%2F+%E3%81%84%E3%81%84%E3%81%88+%2F+%E6%9C%AA%E7%A2%BA%E8%AA%8D%0A-+%E6%AC%A1%E5%9B%9E%E6%9B%B4%E6%96%B0%E6%99%82%E6%9C%9F%3A%0A-+%E7%9B%B8%E8%AB%87%E3%81%97%E3%81%9F%E3%81%84%E5%86%85%E5%AE%B9%3A%0A)

GitHub Issueは公開されます。個人情報、契約本文、価格、認証情報は記載しないでください。初回相談では業種、契約数の目安、契約書にBLS series IDが明記されているか、次回更新時期、相談したい内容だけを確認します。

## 保証しないこと

- 契約条項の法的解釈
- 値上げ可否の判断
- 推奨価格
- 未取得のBLS値の推測
- 類似CPI seriesへの自動置換

BLS Public Data APIはseries IDを指定して時系列を取得する公式APIです。実顧客PoCでは、契約書に明記されたseries IDの公式index-level snapshotを別途取得・履歴保存してから計算します。

## 次の実運用

1. 実契約でseries IDを確認する。
2. BLS公式APIからそのseriesだけを取得し、取得日時・source URL・raw bytes SHA-256を保存する。
3. synthetic fixtureではなく公式snapshotをengineへ渡す。
4. reportをFinance/RevOps/法務担当がレビューする。
5. 実際に発生したinquiry/demo/paid pilotだけをKPIへ記録する。
