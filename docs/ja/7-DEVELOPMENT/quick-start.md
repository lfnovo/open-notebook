# クイックスタート（開発者向け）

## 5分で開発開始

### 1. クローンと環境構築

```bash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
cp .env.example .env
# OPEN_NOTEBOOK_ENCRYPTION_KEY を設定
```

### 2. Dockerで起動（最も簡単）

```bash
docker compose up -d
```

### 3. 開発モード

```bash
# API
python -m open_notebook

# フロントエンド（別ターミナル）
cd frontend && npm run dev
```

### 4. アクセス

- UI: http://localhost:3000 （開発モード）
- API: http://localhost:5055

> 原文: [Quick Start (Development)](../quick-start.md)