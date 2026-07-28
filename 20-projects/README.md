# Projects

明確な成果物または終了条件のある変化を管理します。

Projectごとに`20-projects/<slug>/index.md`を作り、目的、現在状態、次の行動、リスクを
短く保ちます。日々の詳細はLogへ記録し、Projectから関連付けます。

Projectは複数のAreaに関係できるため、Areaの配下には置きません。

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

Project一覧を人手で階層化せず、`NAVIGATION.md`または
`workrepo list --type project --area area:<slug>`で絞り込みます。
