# ローカル クイックスタート（Ollama）

## 前提条件

- [Ollama](https://ollama.com/download) がインストール済み
- Docker / Docker Compose
- 最低 8GB RAM（16GB以上推奨）

## 手順

### 1. Ollamaのセットアップ

`ash
# モデルをダウンロード
ollama pull llama3.1
# または軽量モデル
ollama pull mistral
`

### 2. Open Notebookをクローン

`ash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
`

### 3. 環境設定

.env.example を .env にコピーし、OPEN_NOTEBOOK_ENCRYPTION_KEY を設定。

また、.env に以下を追加：

`ash
OLLAMA_BASE_URL=http://host.docker.internal:11434
`

### 4. 起動

`ash
docker compose up -d
`

### 5. モデル設定

1. [http://localhost:8502](http://localhost:8502) を開く
2. **Settings → API Keys** → Ollamaの「モデル同期」
3. デフォルトモデルを選択

> 原文: [Quick Start Local](../quick-start-local.md)
