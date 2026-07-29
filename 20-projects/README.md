# Projects

明確な成果物または終了条件のある変化を管理します。

Projectごとに`20-projects/<slug>/index.md`を作り、目的、現在状態、次の行動、リスクを
短く保ちます。日々の詳細はLogへ記録し、Projectから関連付けます。

`index.md`はProject固有のダッシュボードです。会議録、調査過程、長い仕様、過去の週次状態を
本文へ積み上げず、Logまたは配下Artifactへ分けます。

Projectは複数のAreaに関係できるため、Areaの配下には置きません。
Project本体もgroupやArea別の物理階層にはせず、必ず
`20-projects/<slug>/index.md`へ置きます。分類は`related`、Area、status、生成Navigationで
表現します。

途中の短いメモはfrontmatterなしで置けます。正式な報告、仕様、分析、成果物は
`workrepo new artifact`でTyped Artifactとして作成し、安定IDと状態を持たせます。

Projectが大きくなったら、内容の種類で次のディレクトリを必要なものだけ作ります。
空のディレクトリを先に作る必要はありません。

```text
analysis/        調査・比較
decisions/       意思決定記録
specifications/  要件・仕様
reports/         週次・月次・完了報告
deliverables/    成果物
links/           外部システム上の資料への案内
assets/          画像・添付原本またはその説明
```

Project内部の階層は自由に増やせますが、Projectを入れ子にしたり、配下で別の`index.md`を
使ったりしません。`index.md`はProjectダッシュボードだけの予約名です。深くしすぎると人間も
AIも探索しにくいため、通常は2〜3段を目安にします。
Projectディレクトリ直下のMarkdownは`index.md`だけにし、補助Markdownは必ず用途別の
サブディレクトリへ置きます。コードや設定などMarkdown以外のファイルはこの制約の対象外です。

Project一覧を人手で階層化せず、`NAVIGATION.md`または
`workrepo list --type project --area area:<slug>`で絞り込みます。

Projectを完了または中止した直後は、`status`を`completed`または`cancelled`にします。
履歴を確認した月次レビューで作業場所から外す場合だけ、次を実行します。

```shell
uv run workrepo archive project:<slug>
```

Projectディレクトリ全体が配下Artifactとともに`80-archive/<year>/projects/`へ移動します。
安定IDと検索性は維持され、誤ってArchiveした場合は`workrepo restore project:<slug>`で
元へ戻せます。
