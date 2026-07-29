# Areas

終了日を持たず、継続的に良い状態を維持する責任領域を管理します。

Areaごとに`30-areas/<slug>/index.md`を作り、期待する状態、健康状態、監視指標、
関連Projectを記載します。組織分類ではなく、自分が継続的に責任を負う単位に絞ります。

`index.md`は責任領域のダッシュボードです。現在のHealthと判断に必要なSignals、Concernsだけを
短く示し、過去のレビューや詳細な統制記録は配下Artifactへ分けます。

`status`は責任領域のライフサイクル、`health`は現在の健全性です。`review_cycle`と
`last_reviewed`を更新すると、Dashboardが次回レビュー日と期限超過を表示します。

`group`は、ファイル配置を変えずに近いAreaを表示上まとめる任意の分類です。組織変更時も
リンクを壊さず変更できます。責任の親子関係が本当に必要になるまでは、Area自体を物理的に
ネストしません。

Areaの詳細が増えたら、必要なものだけ次のディレクトリへ分けます。

```text
reviews/     定期レビューと状態変化の履歴
controls/    継続的な統制・チェック
metrics/     指標の定義と出力
operations/  運用固有の資料
references/  Area固有の参照資料
links/       外部システム上の資料への案内
assets/      画像・添付原本またはその説明
```

Area本体は必ず`30-areas/<slug>/index.md`へ置きます。Area内部の階層は自由に増やせますが、
Areaを入れ子にしたり、配下で別の`index.md`を使ったりしません。
Areaディレクトリ直下のMarkdownは`index.md`だけにし、補助Markdownは必ず用途別の
サブディレクトリへ置きます。

Areaの`index.md`には現在の状態だけを残し、過去の状態はLogまたは`reviews/`へ記録します。
関連Projectの手書き一覧は持たず、frontmatterの`related`と生成ナビゲーションを正にします。

責任そのものがなくなったら`status`を`retired`にし、月次レビューで
`workrepo archive area:<slug>`を実行します。問題があるだけのAreaをArchiveしてはいけません。
HealthがRedでも責任が続く限り、Areaは現在の作業場所に残します。
