# Docker Compose インストール

## 前提条件

- [Docker](https://docs.docker.com/get-docker/) がインストールされていること
- Docker Compose（Docker Desktopに同梱）

## インストール手順

### 1. リポジトリをクローン

`ash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
`

### 2. 環境設定

.env.example を .env にコピーし、暗号化キーを設定します：

`ash
cp .env.example .env
`

.env ファイルを編集し、OPEN_NOTEBOOK_ENCRYPTION_KEY を任意の秘密文字列に変更してください（16文字以上推奨）。

### 3. 起動

`ash
docker compose up -d
`

### 4. アクセス

- **UI**: [http://localhost:8502](http://localhost:8502)
- **API**: [http://localhost:5055](http://localhost:5055)

### 5. AIプロバイダー設定

UIの **Settings → API Keys** からAPIキーを設定してください。

## アップデート

`ash
git pull
docker compose up -d --build
`

> 原文: [Docker Compose Installation](../docker-compose.md)
