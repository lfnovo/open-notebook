# 開発環境セットアップ

## 前提条件

- Python 3.10+
- Node.js 18+
- Docker

## セットアップ手順

### 1. クローン

```bash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
```

### 2. Python環境

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. フロントエンド

```bash
cd frontend
npm install
```

### 4. データベース

```bash
docker run -d --name surrealdb -p 8000:8000 surrealdb/surrealdb:v2 start --log trace --user root --pass root
```

### 5. 起動

```bash
# ターミナル1: API
python -m open_notebook

# ターミナル2: フロントエンド
cd frontend && npm run dev
```

> 原文: [Development Setup](../development-setup.md)