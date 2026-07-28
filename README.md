# AI-ready Work Repository

仕事に関する文書、コード、ローカル限定ファイルを、責務とGit境界を分けながら一つの
VS Code workspaceで扱うためのテンプレート。

## Structure

- [`work-repository/`](work-repository/README.md): 文書、記録、テンプレート、文書用ツール
- [`code/`](code/README.md): 独立したGit履歴を持つコードリポジトリの配置先
- [`local-private/`](local-private/README.md): GitおよびVS Code workspaceの対象外とする領域
- [`ai-work.code-workspace`](ai-work.code-workspace): 文書とコードをまとめて開くVS Code設定

## Safety boundaries

- `local-private/`では、この説明ファイル以外を親Gitリポジトリで追跡しない。
- `code/`の子ディレクトリは必要に応じて独立したGitリポジトリとして管理する。
- 実際の仕事文書を追加する前に、保存先、Git追跡、AI利用、外部送信の可否を確認する。
- TermKeeperとはCLI、MCP、HTTPなどの公開インターフェースだけで連携する。
