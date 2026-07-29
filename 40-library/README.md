# Library

複数のProjectやAreaから継続的に参照する、整理済みの対象、方法、知識、外部原本への案内を
管理します。

- [`10-catalog/`](10-catalog/README.md)：何が存在するか
- [`20-playbooks/`](20-playbooks/README.md)：どのように仕事をするか
- [`30-knowledge/`](30-knowledge/README.md)：何を知っているか
- [`40-resources/`](40-resources/README.md)：原本はどこにあるか

フォルダは文書の主目的だけを表します。SAPやMicrosoft 365などのドメイン、Area、Project、
provider、owner、statusは物理階層にせず、安定ID、`related`、metadata、生成Navigationで
表現します。

Library Entityは種類別ディレクトリ直下の単独Markdownです。任意の深い階層や分類保留用の
`misc`、`other`、`reference`は作りません。

`NAVIGATION.md`は種類別の現在件数と保存先を生成します。文書が増えても手作業で索引を
維持せず、`workrepo list --type TYPE`または`workrepo search TEXT`で絞り込みます。
