# クイックスタート：外部Ollama

## 概要

別のマシンで動作しているOllamaサーバーに接続する場合の手順です。

## 手順

### 1. Ollamaサーバー側

```bash
# OllamaをAPIモードで起動
OLLAMA_HOST=0.0.0.0 ollama serve
```

### 2. Open Notebook側

`.env` に以下を追加：

```bash
OLLAMA_BASE_URL=http://ollama-server-ip:11434
```

### 3. 起動

```bash
docker compose up -d
```

### 4. モデル同期

Settings → API Keys → Ollama → モデル同期

> 原文: [Quick Start External Ollama](../quick-start-external-ollama.md)