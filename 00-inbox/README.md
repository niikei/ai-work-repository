# Inbox

まだ分類を判断していない情報を、一時的に置く入口です。

## ここに置くもの

- 会話中に浮かんだ短いアイデア
- 受領したが、用途をまだ判断していないファイル
- 後で確認したいURLや断片的なメモ

## 置かないもの

- 日付と文脈が確定した出来事：`10-log/`
- 終了条件のある活動：`20-projects/`
- 継続的に監視する責任：`30-areas/`
- 整理済みの再利用知識：`40-library/`

Inboxはファイル置き場ではなく、日付別の短いチェックリストです。手作業で`a.md`のような
仮ファイルを作らず、次のコマンドで記録します。

```shell
uv run workrepo capture "確認する内容"
uv run workrepo inbox status
uv run workrepo inbox review
```

`capture`は`YYYY-MM-DD.md`へ`- [ ]`項目を追記します。処理時は、正式な文書へ反映して
チェックを完了させ、完了項目しか残っていない日付ファイルは削除します。既定では7日で警告、
30日でcommitを拒否します。Inbox内のファイルにYAML frontmatterは付けません。
