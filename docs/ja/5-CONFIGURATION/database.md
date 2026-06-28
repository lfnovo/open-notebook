# データベース設定

## SurrealDB

Open Notebook はデフォルトで SurrealDB を使用します。

### 設定

`.env` ファイルで設定：

```bash
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
```

### データの永続化

Docker Compose 使用時、データはDockerボリュームに保存され、コンテナを停止しても保持されます。

### バックアップ

```bash
# SurrealDBのデータディレクトリをバックアップ
docker exec open-notebook-surrealdb-1 /surreal export --conn ws://localhost:8000 --user root --pass root --ns open_notebook --db open_notebook export.sql
```

> 原文: [Database](../database.md)