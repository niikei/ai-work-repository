# AI-ready Work Repository

仕事の記録、文書、分析コードを、人間とAIの双方が読みやすい形で管理するための
プライベートリポジトリ用テンプレートです。

このテンプレートと付属ツールは[MIT License](LICENSE)で公開されています。
変更履歴は[CHANGELOG.md](CHANGELOG.md)、貢献方法は[CONTRIBUTING.md](CONTRIBUTING.md)、
脆弱性の報告方法は[SECURITY.md](SECURITY.md)を参照してください。

## 5つの作業入口とArchive

| 場所 | 判断基準 | 例 |
| --- | --- | --- |
| [`00-inbox/`](00-inbox/README.md) | まだ置き場所を判断していない | 走り書き、受領直後のメモ |
| [`10-log/`](10-log/README.md) | 何が起きたか | 日記、会議、障害、判断の記録 |
| [`20-projects/`](20-projects/README.md) | 終了条件のある変化は何か | 導入、改善、移行、調査 |
| [`30-areas/`](30-areas/README.md) | 継続的な責任は健全か | ERP運用、アクセス管理 |
| [`40-library/`](40-library/README.md) | 再利用する文脈は何か | 対象、方法、知識、外部原本 |

[Dashboard](DASHBOARD.md)には現在状態を、[Navigation](NAVIGATION.md)にはArea別・group別の
探索導線を集約します。

`inbox`は文書の種類ではなく一時的な状態です。定期的に整理し、残し続けません。
完了・中止・廃止した記録は、まず`status`を変更します。月次レビューなどで現在の作業場所から
外すときだけ、専用コマンドで[`80-archive/`](80-archive/README.md)へ安全に移動します。

ProjectとAreaの`index.md`は、詳細文書の置き場ではなく局所的な現在状態ダッシュボードです。
ProjectはOutcome、Current state、Next actions、Risksを、AreaはResponsibility、Health、
Signals、Concernsを短く保ちます。出来事はLog、仕様・分析・報告は配下Artifactへ分けます。

## 基本ワークフロー

1. 判断に迷う情報は`workrepo capture`で`00-inbox/`へ短く記録する。
2. 起きた事実や新しい管理対象は`workrepo new`で作成する。
3. 現在の状態や次の行動は、関連するProjectまたはAreaの`index.md`へ反映する。
4. 繰り返し使う知識は`40-library/`へ整理する。
5. `uv run workrepo inbox review`で古い未整理項目を確認する。
6. `uv run workrepo check`で構造とリンクを検証する。
7. レビュー前に`uv run workrepo refresh`でリンク、AI向け索引、Dashboardを更新する。
8. 月次レビューで非アクティブな記録だけを明示的にArchiveする。

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

# 長期管理が必要になった外部原本を管理対象へ昇格
uv run workrepo new artifact erp-scope \
  --title "ERP更改スコープ原本" \
  --parent project:erp-upgrade \
  --kind external-resource \
  --provider sharepoint \
  --url "https://example.com/sites/erp/scope.docx" \
  --owner "ERP Team" \
  --access restricted

# 検証と生成物の更新
uv run workrepo check
uv run workrepo refresh

# 大量の文書を型・状態・Areaで絞り込む
uv run workrepo list --type project --status active
uv run workrepo list --type project --area area:erp-operations
uv run workrepo search "cutover decision" --type artifact

# 完了済みProjectを月次レビューでArchiveし、必要なら戻す
uv run workrepo archive project:erp-upgrade
uv run workrepo restore project:erp-upgrade

# 通常一覧はArchiveを除外し、検索はArchiveも含む
uv run workrepo list --type project --include-archived
uv run workrepo list --type project --archived-only
uv run workrepo search "cutover decision" --archived-only
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
- ProjectとArea本体は`<root>/<slug>/index.md`の一階層に保ちます。内部の成果物は
  階層化できますが、入れ子のEntityや別の`index.md`は作りません。Entity直下のMarkdownは
  `index.md`だけにし、補助Markdownはサブディレクトリへ置きます。
- 非アクティブなProject、Area、Catalog、Playbook、Knowledge、ResourceのEntityは
  `workrepo archive ID`で`80-archive/<year>/`へ移動できます。LogとInboxは対象外です。
- Archiveは安定ID、配下Artifact、内部リンクを維持し、`workrepo restore ID`で元へ戻せます。
- ProjectとArea配下のMarkdownは、frontmatterなしなら軽量な作業メモとして索引されます。
  frontmatterを付けた場合はTyped Artifactとして厳密に検証され、安定IDを持ちます。
- `id`は`project:erp-upgrade`のような種類付きの安定IDにします。
- 関係はファイルパスではなく`related`に安定IDを列挙します。
- ProjectとAreaは親子にせず、多対多で関連付けます。
- 物理ディレクトリは安定した所有場所を表し、表示上のgroupやArea別一覧は生成します。
- SharePoint、Excel、PowerPointなどのリンクは、まず通常のMarkdownリンクとして直接貼ります。
  貼られた外部リンクはラベル、URL、provider、記載元とともにAI向け索引へ自動収録されます。
- 複数箇所から参照する正式な原本、owner・access・最終確認日の管理が必要なリンクだけを
  `external-resource`へ昇格します。認証が必要なURLをオンライン照会はしません。
- パスワード、token、署名付きURLは通常Markdownにも`external-resource`にも記録しません。

例えば会議中は、LogやProjectへそのまま貼るだけで構いません。

```markdown
## References

- [ERP更改対象一覧](https://example.com/sites/erp/scope.xlsx)
```

「直接貼る → 重要になったら管理対象へ昇格」が標準ワークフローです。

詳しい判断基準は
[分類ガイド](40-library/30-knowledge/guides/classification-guide.md)と
[文書契約](40-library/30-knowledge/guides/document-contract.md)、
[ディレクトリ契約](40-library/30-knowledge/guides/directory-contract.md)を参照してください。

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
再実行してください。詳細は[Obsidian利用ガイド](docs/guides/obsidian.md)にあります。

## GitHub Copilot

VS CodeのCopilot Agent Mode向けに、常時適用するinstructions、パス別instructions、
必要時だけ読み込むAgent Skills、手動実行するprompt、専用Agentを共有しています。

- Chatで`/process-inbox`：Inboxを読み取り、変更前に分類案を提示
- Chatで`/weekly-review`：期間内の記録を根拠付きで週次レビュー
- Agent選択で`Work Repository Steward`：複数文書にまたがる整理を安全に支援

常時読み込む`.github/copilot-instructions.md`は安全性と探索方法だけに絞っています。文書規約は
編集対象に合うパス別instructions、Inbox整理や週次レビューなどの長い手順は必要時だけSkill
から読み込まれます。通常の依頼では、リポジトリ全体や全ガイドをChatへ添付せず、
`workrepo list`または`workrepo search`で候補を絞ってから、対象文書と最寄りの`index.md`
だけを読ませてください。分類・配置・metadataで迷った場合に限り、該当する契約ガイドを
追加で参照します。これによりコンテキスト消費と誤った類推の両方を抑えます。

Copilotの提案は品質ゲートではありません。変更後は`workrepo check`、commit時はGit hookが
決定的に検査します。設定の読み込み状況はVS Code ChatのReferencesまたはCustomization
Diagnosticsで確認できます。

## セットアップ

Python 3.12以上と[uv](https://docs.astral.sh/uv/)を用意し、次を実行します。

```shell
uv sync
uv run workrepo hooks install
uv run workrepo doctor
uv run workrepo check
uv run workrepo refresh
uv run rumdl check .
uv run pytest
uv run ruff check .
```

開発依存関係はuvの既定の`dev`グループなので、通常は`--extra dev`を付けません。
CIはLinuxとWindowsの両方で、検証、生成物の差分、rumdl、Ruff、mypy、pytestを確認します。

VS Codeでは推奨拡張`rumdl`をインストールすると、Markdownの問題がエディタ上に表示され、
明示的な保存時に自動修正されます。リポジトリ全体を手動整形する場合は
`uv run rumdl fmt .`、変更せず検査する場合は`uv run rumdl check .`を使います。

## ローカルだけで効く品質ゲート

GitHubやCIを利用できない環境でも、`workrepo hooks install`を各cloneで一度実行すると、
commit直前に「実際にstagingされた内容」を検査します。作業中ファイルではなくGit indexを
見るため、commit対象と検査対象がずれません。Markdown lintも同じstaged snapshotに対して
実行され、修正が必要な場合はcommitを止めます。

```shell
# 日常の確認
uv run workrepo check
uv run workrepo inbox status
uv run workrepo inbox review

# commitされる内容だけを手動確認
uv run workrepo check --staged

# 警告も失敗として扱う厳格なレビュー
uv run workrepo check --strict
```

次はcommitを拒否します。

- `00-inbox/`直下の`YYYY-MM-DD.md`以外の一時ファイル
- 30日以上未処理のInbox項目、または50件を超える未処理項目
- 不正・重複したYAMLキー、未知のfrontmatter項目
- 壊れたリンク、重複ID、存在しない関連ID、スキーマ違反
- commit済み文書の`created`を書き換えた変更
- 本文を変更したのに`updated`が作業当日になっていないstaged文書
- 未来の`created`、`updated`、`last_reviewed`

7日以上のInbox項目と、完了済みなのに残っているInboxファイルは警告します。期限と件数は
[`.workspace/policy.yaml`](.workspace/policy.yaml)で調整できます。緊急時にhookを迂回した
commitは可能ですが、通常運用では`--no-verify`を使わず、先に原因を整理してください。
文書日付は同じpolicyの`timezone`を基準にするため、PCとUTCのCIで日付境界がずれません。

## コードとデータの境界

- このリポジトリを整備するコードは`src/workrepo/`へ置きます。
- Project固有の小さな分析・自動化コードは、そのProject内へ置けます。
- 独立した製品やサービスに育ったコードは、別リポジトリへ切り出します。
- Gitまたは利用するAIに渡せないデータは、必ずこのリポジトリの外に置きます。
- TermKeeperとはCLI、MCP、HTTPの公開インターフェースだけで連携します。
