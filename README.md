# AI-ready Work Repository

仕事の記録、文書、分析コードを、人間とAIの双方が読みやすい形で管理するための
プライベートリポジトリ用テンプレートです。

## 5つの入口

| 場所 | 判断基準 | 例 |
| --- | --- | --- |
| [`00-inbox/`](00-inbox/README.md) | まだ置き場所を判断していない | 走り書き、受領直後のメモ |
| [`10-log/`](10-log/README.md) | 何が起きたか | 日記、会議、障害、判断の記録 |
| [`20-projects/`](20-projects/README.md) | 終了条件のある変化は何か | 導入、改善、移行、調査 |
| [`30-areas/`](30-areas/README.md) | 継続的な責任は健全か | ERP運用、アクセス管理 |
| [`40-library/`](40-library/README.md) | 今後も参照する知識は何か | 役割、システム、手順、資料 |

[Dashboard](DASHBOARD.md)には、未処理Inbox、進行中Project、Areaの現在状態を集約します。

`inbox`は文書の種類ではなく一時的な状態です。定期的に整理し、残し続けません。
完了したProjectなどは移動せず、`status`を変更します。これによりリンク切れを防ぎます。

## 基本ワークフロー

1. 判断に迷う情報は`workrepo capture`で`00-inbox/`へ短く記録する。
2. 起きた事実や新しい管理対象は`workrepo new`で作成する。
3. 現在の状態や次の行動は、関連するProjectまたはAreaの`index.md`へ反映する。
4. 繰り返し使う知識は`40-library/`へ整理する。
5. `uv run workrepo check`で構造とリンクを検証する。
6. レビュー前に`uv run workrepo refresh`でリンク、AI向け索引、Dashboardを更新する。

## 日常コマンド

```shell
# 迷った情報を今日のInboxへ追加
uv run workrepo capture "在庫連携の監視手順を確認する"

# Areaを作成
uv run workrepo new area erp-operations --title "ERP運用"

# Areaに関連するProjectを作成
uv run workrepo new project erp-upgrade \
  --title "ERP更改" \
  --related area:erp-operations

# 日付付きのLogを作成
uv run workrepo new log upgrade-meeting \
  --title "ERP更改定例会議" \
  --template meeting \
  --related project:erp-upgrade

# Projectに正式な週次報告を作成
uv run workrepo new artifact 2026-07-27-weekly-report \
  --title "ERP更改 2026-07-27週次報告" \
  --parent project:erp-upgrade \
  --kind weekly-report

# 検証と生成物の更新
uv run workrepo check
uv run workrepo refresh
```

`new`は日付、ID、保存先、frontmatterをテンプレートから生成し、存在しない関連IDや
既存ファイルの上書き、Windowsで利用できない名前、大文字小文字だけが異なる衝突を拒否します。
コマンドは配下のディレクトリから実行しても、最寄りのリポジトリルートを自動検出します。

Logは`10-log/2026/07/2026-07-27-week/`のように、年・月・週で整理されます。
月と年は週の開始日を基準にするため、月跨ぎの週も分断されません。AI向け索引には
`2026-W31`のISO週番号も自動的に収録されます。

## 文書規約

- 文書タイトルの正はMarkdownのH1です。YAMLに`title`は書きません。
- Entityと正式な成果物には、テンプレートに沿ったYAML frontmatterを付けます。
- ProjectとAreaでは`index.md`が管理対象です。配下の成果物や分析コードはそのProject固有の
  文脈として自由に構成できます。
- ProjectとArea配下のMarkdownは、frontmatterなしなら軽量な作業メモとして索引されます。
  frontmatterを付けた場合はTyped Artifactとして厳密に検証され、安定IDを持ちます。
- `id`は`project:erp-upgrade`のような種類付きの安定IDにします。
- 関係はファイルパスではなく`related`に安定IDを列挙します。
- ProjectとAreaは親子にせず、多対多で関連付けます。
- Word、Excel、PDF、画像の原本は保持し、必要なら同じ場所にMarkdownの説明を添えます。

詳しい判断基準は
[分類ガイド](40-library/40-references/classification-guide.md)と
[文書契約](40-library/40-references/document-contract.md)を参照してください。

## Obsidian

このリポジトリのルートをObsidianのVaultとして開けます。共有する設定は、標準Markdown、
相対リンク、`90-templates/`、文書ごとの`assets/`だけに限定しています。レイアウト、テーマ、
プラグインなどの個人設定はGitで追跡しません。

`related`の安定IDが関係の正です。次のコマンドは、IDから通常のMarkdownリンクを生成し、
ObsidianのBacklinksとGraph Viewでも関係を利用できるようにします。

```shell
uv run workrepo refresh
```

生成された`workrepo:related`マーカー内は直接編集せず、frontmatterの`related`を変更して
再実行してください。詳細は[Obsidian利用ガイド](OBSIDIAN.md)にあります。

## セットアップ

Python 3.12以上と[uv](https://docs.astral.sh/uv/)を用意し、次を実行します。

```shell
uv sync
uv run workrepo check
uv run workrepo refresh
uv run pytest
uv run ruff check .
```

開発依存関係はuvの既定の`dev`グループなので、通常は`--extra dev`を付けません。
CIはLinuxとWindowsの両方で、検証、生成物の差分、Ruff、mypy、pytestを確認します。

## コードとデータの境界

- このリポジトリを整備するコードは`src/workrepo/`へ置きます。
- Project固有の小さな分析・自動化コードは、そのProject内へ置けます。
- 独立した製品やサービスに育ったコードは、別リポジトリへ切り出します。
- Gitまたは利用するAIに渡せないデータは、必ずこのリポジトリの外に置きます。
- TermKeeperとはCLI、MCP、HTTPの公開インターフェースだけで連携します。
