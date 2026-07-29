---
type: guide
id: guide:directory-contract
status: active
created: 2026-07-29
updated: 2026-07-30
related:
  - guide:classification-guide
  - guide:document-contract
---

# ディレクトリ契約

## Top level

```text
00-inbox/     未分類の一時入力
10-log/       年・月・週で整理する事実と判断
20-projects/  終了条件のある変化
30-areas/     継続的な責任
40-library/   再利用する対象、方法、知識、外部原本への案内
80-archive/   非アクティブな管理対象
90-templates/ 管理文書の生成元
docs/         リポジトリ自体の利用・保守文書
```

番号の空きは予約領域ではありません。用途が明確になるまで新しいTop-level directoryを
追加しません。`docs/`は業務文書の分類先ではなく、テンプレートの利用ガイド、設計説明、
検証記録などを業務記録から分離するための保守領域です。

ルート直下のMarkdownは`README.md`、生成される`DASHBOARD.md`と`NAVIGATION.md`、
公開テンプレートの標準文書`CHANGELOG.md`、`CONTRIBUTING.md`、`SECURITY.md`だけにします。
その他の利用・設計・検証文書は`docs/`へ置きます。

## Hierarchy policy

| Root | Policy |
| --- | --- |
| Inbox | 日付ファイルだけを置き、階層化しない |
| Log | `YYYY/MM/YYYY-MM-DD-week/`の固定階層 |
| Projects | Entityは一階層、内部の補助内容は必要に応じて階層化 |
| Areas | Entityは一階層、内部の補助内容は必要に応じて階層化 |
| Library | 機能、種類、単独Markdownの固定階層 |
| Archive | 年、種類、Entityの固定階層 |
| Templates | 少数の共有Templateをフラットに配置 |
| Docs | 用途別に階層化するが、業務記録を置かない |

Area、Project、System、provider、owner、statusなどの関係や分類を物理階層で表しません。
安定ID、`related`、metadata、生成Navigationを使用します。

## Directory entities

ProjectとAreaは`<root>/<slug>/index.md`で管理します。Entity directory直下のMarkdownは
`index.md`だけです。補助Markdownは`analysis/`、`reports/`、`reviews/`、`notes/`など、
目的を表すサブディレクトリへ置きます。別のEntityや`index.md`を内部へ作りません。

Markdown以外のコードや設定ファイルはこの直下制約の対象外です。内部階層は通常2〜3段を
目安とし、空ディレクトリを先に作りません。

## Library

Libraryは次の固定分類を使います。

```text
40-library/
├── 10-catalog/    systems, roles, organizations, services
├── 20-playbooks/  processes, procedures, controls, standards
├── 30-knowledge/  concepts, guides, glossary
└── 40-resources/  外部原本への管理された案内
```

Library Entityは種類別ディレクトリ直下の単独Markdownです。任意の深い階層、製品別の
Top-level分類、`misc`、`other`、`reference`を作りません。

## Lifecycle

非アクティブな管理対象は手動で移動せず、`workrepo archive ID`を使います。Restoreを含め、
安定ID、Project・Area内部の階層、Markdownリンクを維持します。

## Related documents

<!-- workrepo:related:start -->
- [文書の分類ガイド](classification-guide.md) (`guide:classification-guide`)
- [文書契約](document-contract.md) (`guide:document-contract`)
<!-- workrepo:related:end -->
