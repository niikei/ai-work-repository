---
type: reference
id: reference:document-contract
status: active
created: 2026-07-29
updated: 2026-07-29
related:
  - reference:classification-guide
---

# 文書契約

## 3段階の管理

| 種類 | YAML | 安定ID | 主な用途 |
| --- | --- | --- | --- |
| 非管理文書 | なし | なし | README、Dashboard、Inbox |
| 軽量Artifact | なし | なし | Project・Area内の途中メモ |
| 管理対象 | 必須 | 必須 | Entity、正式なTyped Artifact |

ProjectまたはArea配下のMarkdownにfrontmatterを書くと、その文書はTyped Artifactとして
厳密に検証されます。部分的なYAMLは許可されず、入力が黙って無視されることもありません。

## Entity

EntityはLog、Project、Area、Role、System、Process、Referenceです。共通して`type`、`id`、
`status`、`created`、`updated`、`related`を持ちます。

ProjectとAreaの`health`は`unknown`、`green`、`amber`、`red`です。Projectの`status`は
期限のある変化のライフサイクルを示します。Areaの`status`は`active`、`paused`、`retired`で、
責任領域そのものが有効かを示します。問題の有無を`status`へ混ぜません。

Areaは`review_cycle`と`last_reviewed`も持ちます。周期は`weekly`、`monthly`、`quarterly`、
`annual`です。DashboardとAI向け索引は次回レビュー日を導出します。

## Typed Artifact

正式な報告、分析、仕様、成果物は次のコマンドで作ります。

```shell
uv run workrepo new artifact 2026-07-27-weekly-report \
  --title "ERP更改 2026-07-27週次報告" \
  --parent project:erp-upgrade \
  --kind weekly-report
```

`kind`は`weekly-report`、`report`、`analysis`、`specification`、`deliverable`、
`attachment-note`、`note`、`review`、`control`、`external-resource`から選びます。
状態は`draft`、`active`、`final`、`superseded`です。所有するProjectまたはAreaは
`related`へ必ず含まれます。

期間を持つArtifactには`period_start`と`period_end`を対で追加できます。終了日は開始日より
前にできません。

## 機械向け索引

`.workspace/indexes/documents.json`は生成物です。各Artifactには所有元の`parent_id`、
各管理対象には自分を参照する`backlinks`と、本文へ直接貼られた`external_links`が
導出されます。外部リンクにはラベル、URL、provider、行番号が含まれます。直接編集せず、
`workrepo refresh`で再生成します。

外部リンクは通常のMarkdownへ直接貼るのが既定です。複数文書から参照する正式な原本や、
owner・access・最終確認日の管理が必要になったリンクだけを`external-resource`へ昇格します。

## Related documents

<!-- workrepo:related:start -->
- [文書の分類ガイド](classification-guide.md) (`reference:classification-guide`)
<!-- workrepo:related:end -->
