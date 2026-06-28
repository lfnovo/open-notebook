# 環境変数リファレンス

## 必須設定

| 変数 | デフォルト | 説明 |
|------|----------|------|
| OPEN_NOTEBOOK_ENCRYPTION_KEY | なし | APIキー暗号化用の秘密文字列（**必須**） |
| SURREAL_URL | ws://surrealdb:8000/rpc | SurrealDB接続URL |
| SURREAL_USER | 
oot | SurrealDBユーザー名 |
| SURREAL_PASSWORD | 
oot | SurrealDBパスワード |
| SURREAL_NAMESPACE | open_notebook | SurrealDB名前空間 |
| SURREAL_DATABASE | open_notebook | SurrealDBデータベース名 |

## セキュリティ

| 変数 | 説明 |
|------|------|
| OPEN_NOTEBOOK_PASSWORD | インスタンス全体のパスワード保護 |
| CORS_ORIGINS | 許可するオリジン（デフォルト: *） |

## AI設定

| 変数 | 説明 |
|------|------|
| OPENAI_API_KEY | OpenAI APIキー |
| ANTHROPIC_API_KEY | Anthropic APIキー |
| GOOGLE_API_KEY | Google AI APIキー |
| GROQ_API_KEY | Groq APIキー |
| OLLAMA_BASE_URL | OllamaエンドポイントURL |

> **注意**: APIキーはUI（Settings → API Keys）から設定することを推奨します。  
> 原文: [Environment Reference](../environment-reference.md)
