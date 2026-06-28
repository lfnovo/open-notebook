# コード規約

## Python

- [PEP 8](https://peps.python.org/pep-0008/) に準拠
- 型ヒントを積極的に使用
- ドキュメント文字列（docstring）を書く

## TypeScript / React

- ESLint + Prettier を使用
- 型を明示的に定義
- コンポーネントは関数コンポーネントで

## コミットメッセージ

```
type(scope): description

例:
feat(i18n): add Japanese translations
fix(api): resolve search timeout
docs: update installation guide
refactor(types): type-check domain base model
test(ci): measure and report test coverage
```

## ファイル構成

- `open_notebook/` — Python APIとコアロジック
- `frontend/src/` — Next.jsアプリケーション
- `docs/` — 英語ドキュメント
- `docs/ja/` — 日本語ドキュメント

> 原文: [Code Standards](../code-standards.md)