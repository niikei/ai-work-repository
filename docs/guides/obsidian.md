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
- [ERP](../../40-library/10-catalog/systems/erp.md) (`system:erp`)
<!-- workrepo:related:end -->
```

これらのリンクはObsidianのBacklinksとGraph Viewで認識されます。マーカー内を直接編集しても
次回の同期で置き換わるため、関係の変更は必ず`related`で行います。

[Dashboard](../../DASHBOARD.md)も同じコマンドで更新されます。ObsidianではDashboardを
ブックマークすると、Inboxに加えてAttention、進行中Project、Areaレビュー、直近LogのBaseを
同じ画面で操作できます。Dashboardを開いた状態でObsidianを終了すれば、次回起動時にも前回の
ワークスペースとして復元されます。操作可能なBaseを先頭に配置し、その下にObsidian以外でも
読めるMarkdown概要を配置しています。

完了済みProjectなどを`workrepo archive ID`で移動した場合も、標準Markdownリンクと
生成関連リンクは新しい相対パスへ更新されます。Obsidianのファイル操作で管理対象を直接
Archiveへ移動せず、必ずコマンドを使ってください。

## Basesで状態を確認する

コアプラグインのBasesを有効にすると、`40-library/40-resources/views/`にある次の管理画面を
利用できます。

- `attention.base`: Project、Area、外部リソースを横断する要注意項目
- `projects.base`: 要注意、進行中、全体ポートフォリオ
- `areas.base`: 要注意、group別、レビュー周期別
- `recent-logs.base`: 直近7日、直近30日、全Log
- `external-resources.base`: 90日以上未確認、access別、全外部リソース
- `library.base`: Draft、種類別のActive、Retired

各行は安定IDを表示名にしたリンクです。ProjectとAreaは物理ファイル名がどちらも`index.md`の
ため、`file.name`ではなくIDを使って区別します。Projectの要注意ビューには、blocked、
amber/red、critical、および`target_date`超過が表示されます。

Base上で既存プロパティを編集した場合も、変更後に`uv run workrepo check`を実行してください。
Baseから新しい行を作ると、必須プロパティや配置規則を満たさない可能性があります。新規文書は
引き続き`workrepo new`、一時記録は`workrepo capture`を使います。

各ビューには用途に合う既定の並び順と件数上限があります。要注意項目や期限は古いものから、
更新履歴やLogは新しいものから表示されます。上限を超えた項目は削除されず、Baseのフィルターや
上限を変更すれば確認できます。

ターミナルや検索結果で安定IDが分かっている場合は、パスを探さずに対象を開けます。

```shell
uv run workrepo open project:erp-upgrade
```

Archiveやrestoreで物理パスが変わった後も、同じIDで現在のファイルを解決します。

## Gitで共有するもの

`.obsidian/app.json`と`.obsidian/templates.json`だけを共有します。次のような個人状態は
`.gitignore`によって追跡されません。

- 開いているタブと画面レイアウト
- ホットキー
- テーマとコミュニティプラグイン
- Obsidianのキャッシュ

プラグインなしでも読める標準Markdownを維持することが、このリポジトリの基本方針です。

スキーマv4から更新する場合は、[スキーマv5移行ガイド](schema-v5-migration.md)を参照してください。
