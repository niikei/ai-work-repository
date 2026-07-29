# Catalog

業務上識別し、複数の文脈から参照する対象を管理します。

- `systems/`：管理対象となるシステム
- `roles/`：立場に期待される責任と権限
- `organizations/`：継続的に参照する組織
- `services/`：利用者へ継続提供するサービス

分類は対象の主な性質で一つだけ選び、Area、Project、provider、ownerなどは`related`または
本文で表現します。各Entityは種類別ディレクトリ直下の単独Markdownにします。
