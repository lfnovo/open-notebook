# 詳細設定

## パフォーマンスチューニング

### チャンク設定

```bash
CHUNK_SIZE=1500    # デフォルト
CHUNK_OVERLAP=150  # デフォルト
```

### 埋め込みバッチサイズ

```bash
OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE=50  # デフォルト
```

### LLMタイムアウト

```bash
ESPERANTO_LLM_TIMEOUT=60  # デフォルト（秒）
```

## ログ設定

```bash
# デバッグログの有効化
LOGLEVEL=debug
```

## LangSmith トレーシング

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT="Open Notebook"
```

> 原文: [Advanced Configuration](../advanced.md)