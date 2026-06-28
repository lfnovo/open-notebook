# API設定

## REST API

Open Notebook は `localhost:5055` で完全なREST APIを提供します。

### 主なエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/notebooks` | ノートブック一覧 |
| POST | `/api/notebooks` | ノートブック作成 |
| POST | `/api/search` | 検索 |
| POST | `/api/search/ask` | AI質問（RAG） |
| GET | `/api/models` | モデル一覧 |
| GET | `/health` | ヘルスチェック |

### 認証

`OPEN_NOTEBOOK_PASSWORD` が設定されている場合、Basic認証が必要です。

> 原文: [API Configuration](../api-configuration.md)