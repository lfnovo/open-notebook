# アーキテクチャ

## 技術スタック

| 層 | 技術 |
|----|------|
| フロントエンド | Next.js (React) |
| APIサーバー | Python (FastAPI) |
| データベース | SurrealDB |
| AI連携 | LangChain / LangGraph |
| コンテナ化 | Docker |

## システム構成

`
ブラウザ (Next.js) → REST API (FastAPI :5055) → SurrealDB (:8000)
                           ↓
                    LangGraph ワークフロー
                           ↓
                    AI プロバイダー (OpenAI / Ollama / etc.)
`

## 主要ワークフロー

1. **ソース処理**: 入力 → 解析 → 埋め込み生成 → DB保存
2. **検索/質問**: クエリ → ベクトル検索 → RAG → 応答生成
3. **ポッドキャスト**: ソース → スクリプト生成 → TTS → 音声出力

> 原文: [Architecture](../architecture.md)
