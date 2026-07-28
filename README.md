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

`inbox`は文書の種類ではなく一時的な状態です。定期的に整理し、残し続けません。
完了したProjectなどは移動せず、`status`を変更します。これによりリンク切れを防ぎます。

## 基本ワークフロー

1. 判断に迷う情報は`00-inbox/`へ短く記録する。
2. 起きた事実は`10-log/YYYY/MM/`へ記録する。
3. 現在の状態や次の行動は、関連するProjectまたはAreaの`index.md`へ反映する。
4. 繰り返し使う知識は`40-library/`へ整理する。
5. `uv run workrepo check`で構造とリンクを検証する。
6. `uv run workrepo links`でObsidian向けの文書リンクを同期する。
7. `uv run workrepo index`でAIやツール向けの索引を生成する。

## 文書規約

- 文書タイトルの正はMarkdownのH1です。YAMLに`title`は書きません。
- 管理対象文書には、テンプレートに沿ったYAML frontmatterを付けます。
- ProjectとAreaでは`index.md`が管理対象です。配下の成果物や分析コードはそのProject固有の
  文脈として自由に構成できます。
- `id`は`project:erp-upgrade`のような種類付きの安定IDにします。
- 関係はファイルパスではなく`related`に安定IDを列挙します。
- ProjectとAreaは親子にせず、多対多で関連付けます。
- Word、Excel、PDF、画像の原本は保持し、必要なら同じ場所にMarkdownの説明を添えます。

詳しい判断基準は
[分類ガイド](40-library/40-references/classification-guide.md)を参照してください。

## Obsidian

このリポジトリのルートをObsidianのVaultとして開けます。共有する設定は、標準Markdown、
相対リンク、`90-templates/`、文書ごとの`assets/`だけに限定しています。レイアウト、テーマ、
プラグインなどの個人設定はGitで追跡しません。

`related`の安定IDが関係の正です。次のコマンドは、IDから通常のMarkdownリンクを生成し、
ObsidianのBacklinksとGraph Viewでも関係を利用できるようにします。

```shell
uv run workrepo links
```

生成された`workrepo:related`マーカー内は直接編集せず、frontmatterの`related`を変更して
再実行してください。詳細は[Obsidian利用ガイド](OBSIDIAN.md)にあります。

## セットアップ

Python 3.12以上と[uv](https://docs.astral.sh/uv/)を用意し、次を実行します。

```shell
uv sync
uv run workrepo check
uv run workrepo links
uv run pytest
uv run ruff check .
```

開発依存関係はuvの既定の`dev`グループなので、通常は`--extra dev`を付けません。

## コードとデータの境界

- このリポジトリを整備するコードは`src/workrepo/`へ置きます。
- Project固有の小さな分析・自動化コードは、そのProject内へ置けます。
- 独立した製品やサービスに育ったコードは、別リポジトリへ切り出します。
- Gitまたは利用するAIに渡せないデータは、必ずこのリポジトリの外に置きます。
- TermKeeperとはCLI、MCP、HTTPの公開インターフェースだけで連携します。
