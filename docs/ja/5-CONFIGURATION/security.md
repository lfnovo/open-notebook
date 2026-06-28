# セキュリティ

## パスワード保護

環境変数 OPEN_NOTEBOOK_PASSWORD を設定すると、インスタンス全体がパスワード保護されます。

`ash
OPEN_NOTEBOOK_PASSWORD=your-secure-password
`

## APIキーの暗号化

すべてのAPIキーは OPEN_NOTEBOOK_ENCRYPTION_KEY で暗号化され、SurrealDBに保存されます。

## 本番環境のチェックリスト

- [ ] OPEN_NOTEBOOK_ENCRYPTION_KEY を強力な値に変更
- [ ] OPEN_NOTEBOOK_PASSWORD を設定
- [ ] CORS_ORIGINS を適切に制限
- [ ] SurrealDB の認証情報をデフォルトから変更
- [ ] HTTPS化（リバースプロキシ経由）

> 原文: [Security](../security.md)
