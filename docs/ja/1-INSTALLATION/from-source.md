# ソースからのインストール

## 前提条件

- Python 3.10+
- Node.js 18+
- SurrealDB

## 手順

### 1. Python環境

`ash
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
`

### 2. フロントエンド

`ash
cd frontend
npm install
`

### 3. 環境設定

`ash
cp .env.example .env
# OPEN_NOTEBOOK_ENCRYPTION_KEY を設定
`

### 4. SurrealDBを起動

`ash
surreal start --log trace --user root --pass root memory
`

### 5. アプリ起動

`ash
# ターミナル1: API
python -m open_notebook

# ターミナル2: フロントエンド
cd frontend && npm run dev
`

> 原文: [Install from Source](../from-source.md)
