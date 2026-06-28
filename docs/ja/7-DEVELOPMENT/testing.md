# テスト

## テストの実行

### Python テスト

```bash
pytest
# またはカバレッジ付き
pytest --cov=open_notebook
```

### フロントエンド テスト

```bash
cd frontend
npm test
```

## テストの種類

- **ユニットテスト**: 関数・メソッド単位
- **統合テスト**: API・DBを含む
- **E2Eテスト**: ブラウザ自動化

> 原文: [Testing](../testing.md)