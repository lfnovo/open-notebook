# トラブルシューティング：接続問題

## 一般的な接続問題

### 「APIサーバーに接続できません」

1. Dockerコンテナが実行中か確認：
   ```bash
   docker compose ps
   ```
2. ログを確認：
   ```bash
   docker compose logs open_notebook
   ```

### 「SurrealDBに接続できません」

`.env` のデータベース設定を確認：
```bash
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
```

### CORS エラー

環境変数 `CORS_ORIGINS` を適切に設定：
```bash
CORS_ORIGINS=http://localhost:8502
```

> 原文: [Connection Issues](../connection-issues.md)