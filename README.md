---
type: workspace
title: AI-ready Work Repository
status: active
---

# AI-ready Work Repository

仕事に関する文書、記録、補助ファイルを、人間とAIの双方が段階的に理解できる形で管理する。

## Entry points

- [Inbox](inbox/index.md): 未整理の記録と受領ファイル
- [Projects](projects/index.md): 完了条件のある仕事
- [Areas](areas/index.md): 継続的に維持する責任領域
- [Reference](reference/index.md): 再利用する参照資料
- [Journal](journal/index.md): 日付を軸にした作業記録
- [Archive](archive/index.md): 完了・廃止した文脈

## Principles

- ファイル形式ではなく仕事の文脈を基準に配置する。
- 各ProjectやAreaでは`index.md`を入口にする。
- Word、Excel、画像などの原本は保持し、必要に応じてMarkdownの説明を添える。
- 自動生成物は`.workspace/cache/`へ隔離する。
- 機密性が高くGitやAIの対象にできないファイルは、リポジトリ外の`local-private/`へ置く。
- TermKeeperとはCLI、MCP、HTTPなどの公開インターフェースだけで連携する。
