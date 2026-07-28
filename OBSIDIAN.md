# Obsidian利用ガイド

## Vaultを開く

Obsidianで「保管庫としてフォルダーを開く」を選び、このリポジトリのルートを指定します。
`00-inbox/`だけをVaultにせず、`.git`があるルート全体を開きます。

共有設定により、次の動作が有効になります。

- リンクは標準Markdownの相対リンクとして作成する
- リンク先の名前を変えたとき、参照元も更新する
- 添付ファイルは現在の文書と同じ階層の`assets/`へ置く
- `90-templates/`をObsidian標準のTemplatesプラグインから利用する
- 開発用ディレクトリを検索やGraph Viewの対象から除外する

初回だけObsidianの「コアプラグイン」でTemplatesを有効にしてください。プラグインの有効状態は
個人設定なので、このテンプレートでは強制しません。

## 文書同士を関連付ける

frontmatterの`related`へ、リンク先の安定IDを追加します。

```yaml
related:
  - area:erp-operations
  - system:erp
```

その後、リポジトリのルートで実行します。

```shell
uv run workrepo refresh
```

文書末尾に次のような標準Markdownリンクが生成されます。

```markdown
## Related documents

<!-- workrepo:related:start -->
- [ERP運用](../../30-areas/erp-operations/index.md) (`area:erp-operations`)
- [ERP](../../40-library/20-systems/erp.md) (`system:erp`)
<!-- workrepo:related:end -->
```

これらのリンクはObsidianのBacklinksとGraph Viewで認識されます。マーカー内を直接編集しても
次回の同期で置き換わるため、関係の変更は必ず`related`で行います。

[Dashboard](DASHBOARD.md)も同じコマンドで更新されます。ObsidianではDashboardを
ブックマークすると、Inbox、進行中Project、Areaへすぐ移動できます。

## Gitで共有するもの

`.obsidian/app.json`と`.obsidian/templates.json`だけを共有します。次のような個人状態は
`.gitignore`によって追跡されません。

- 開いているタブと画面レイアウト
- ホットキー
- テーマとコミュニティプラグイン
- Obsidianのキャッシュ

プラグインなしでも読める標準Markdownを維持することが、このリポジトリの基本方針です。
