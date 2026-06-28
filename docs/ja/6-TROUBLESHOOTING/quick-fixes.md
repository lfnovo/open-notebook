# トラブルシューティング：クイック修正

## Dockerが起動しない

```bash
# Docker Desktopが実行中か確認
docker info

# コンテナを再起動
docker compose down
docker compose up -d
```

## APIに接続できない

```bash
# ヘルスチェック
curl http://localhost:5055/health
# → {"status":"healthy"} なら正常
```

## AIが応答しない

1. Settings → API Keys でAPIキーが正しいか確認
2. 「接続テスト」を実行
3. モデルが同期されているか確認

## フロントエンドが真っ白

- ブラウザコンソールでエラーを確認
- `docker compose logs open_notebook` でログ確認

> 原文: [Quick Fixes](../quick-fixes.md)