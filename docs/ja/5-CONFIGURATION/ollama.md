# Ollama 設定

## 概要

Ollamaを使うと、外部APIを使わず完全ローカルでAIを実行できます。

## セットアップ

### 1. Ollamaインストール

[https://ollama.com/download](https://ollama.com/download) からインストール。

### 2. モデルをダウンロード

```bash
ollama pull llama3.1    # 高性能（要16GB+ RAM）
ollama pull mistral     # 軽量（8GB RAM）
ollama pull nomic-embed-text  # 埋め込み用
```

### 3. Open Notebookと接続

`.env` に追加：

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

UIの Settings → API Keys でOllamaの「モデル同期」を実行。

> 原文: [Ollama](../ollama.md)