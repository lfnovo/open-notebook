# OpenAI クイックスタート

## 前提条件

- OpenAI APIキー（[https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) から取得）
- Docker / Docker Compose

## 手順

### 1. リポジトリをクローン

`ash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
`

### 2. 環境設定

`ash
cp .env.example .env
`

.env の OPEN_NOTEBOOK_ENCRYPTION_KEY を任意の文字列に変更。

### 3. 起動

`ash
docker compose up -d
`

### 4. APIキー設定

1. [http://localhost:8502](http://localhost:8502) を開く
2. **Settings → API Keys** に移動
3. OpenAI の「APIキーを設定」をクリック
4. APIキーを入力して保存

### 5. 使い始める

1. ノートブックを作成
2. ソースを追加（PDF、URL、YouTube等）
3. チャットまたは検索でAIと対話

> 原文: [Quick Start OpenAI](../quick-start-openai.md)
