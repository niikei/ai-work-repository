# スキーマv5移行ガイド

スキーマv5では、ProjectとAreaの管理情報を拡張します。既存文書の一括書き換えは不要です。
追加プロパティはすべて任意で、値を持たないv4文書もそのまま検証できます。

## 変更点

- Projectに`owner`、`priority`、`target_date`を追加
- `priority`は`low`、`medium`、`high`、`critical`のいずれか
- Areaに`owner`を追加
- Obsidian Basesで期限超過、レビュー超過、確認期限超過を横断表示

`health`、`review_cycle`、`last_reviewed`など、従来の必須項目は変わりません。

## 移行手順

ツールとスキーマは同じコミットから取得し、リポジトリのルートで次を実行します。

```shell
uv sync
uv run workrepo doctor
uv run workrepo check
uv run workrepo refresh
uv run workrepo check
```

`doctor`で`schema: version 5`が表示され、最後の`check`が成功すれば移行完了です。
`refresh`は関連リンク、Dashboard、Navigation、検索インデックスを再生成します。

## 管理情報を追加する

必要なProjectやAreaだけにプロパティを追加します。

```yaml
# Project
owner: Platform Team
priority: high
target_date: 2026-09-30
```

```yaml
# Area
owner: Operations Team
```

日付は`YYYY-MM-DD`形式にします。Projectが`completed`または`cancelled`になると、期限を過ぎても
Attention Centerの期限超過には表示されません。

## 問題が起きた場合

エラーに表示されたファイルだけを修正し、`uv run workrepo check`を再実行します。v5の変更は
任意項目の追加なので、追加した`owner`、`priority`、`target_date`を取り除けば既存文書の状態へ
戻せます。ツールを以前の版へ戻す場合は、`.workspace/schemas/document.schema.yaml`も必ず同じ
コミットへ戻してください。ツールとスキーマの版を混在させないことが重要です。
