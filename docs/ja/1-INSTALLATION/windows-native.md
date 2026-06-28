# Windowsネイティブ インストール

## 前提条件

- Python 3.10+
- Node.js 18+
- SurrealDB

## 手順

### 1. リポジトリをクローン

```powershell
git clone https://github.com/kentalos/open-notebook.git
cd open-notebook
```

### 2. Python環境

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -e .
```

### 3. フロントエンド

```powershell
cd frontend
npm install
```

### 4. SurrealDB

```powershell
surreal start --log trace --user root --pass root memory
```

### 5. アプリ起動

```powershell
# ターミナル1: API
python -m open_notebook

# ターミナル2: フロントエンド
cd frontend; npm run dev
```

> 原文: [Windows Native](../windows-native.md)