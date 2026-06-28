# シングルコンテナ インストール

## 手順

### 1. イメージの取得

```bash
docker pull lfnovo/open_notebook:v1-latest
```

### 2. SurrealDBを起動

```bash
docker run -d --name surrealdb -p 8000:8000 surrealdb/surrealdb:v2 start --log trace --user root --pass root
```

### 3. Open Notebookを起動

```bash
docker run -d --name open-notebook -p 5055:5055 -p 8502:8502 -e SURREAL_URL=ws://host.docker.internal:8000/rpc -e OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key lfnovo/open_notebook:v1-latest
```

> 原文: [Single Container](../single-container.md)