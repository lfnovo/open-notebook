# APIリファレンス

完全なAPI仕様は OpenAPI ドキュメントとして提供されています。

## Swagger UI

起動後に以下でアクセス可能：

- Swagger UI: [http://localhost:5055/docs](http://localhost:5055/docs)
- OpenAPI JSON: [http://localhost:5055/openapi.json](http://localhost:5055/openapi.json)

## 主要エンドポイント

### ノートブック
- `GET /api/notebooks` — 一覧取得
- `POST /api/notebooks` — 作成
- `PUT /api/notebooks/{id}` — 更新
- `DELETE /api/notebooks/{id}` — 削除

### 検索
- `POST /api/search` — 全文＋ベクトル検索
- `POST /api/search/ask` — AI質問応答（RAG）
- `POST /api/search/ask/simple` — 簡易質問

### モデル
- `GET /api/models` — モデル一覧
- `POST /api/models` — モデル追加
- `PUT /api/models/defaults` — デフォルト設定

> 原文: [API Reference](../api-reference.md)