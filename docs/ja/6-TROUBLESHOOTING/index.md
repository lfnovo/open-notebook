# トラブルシューティング

よくある問題と解決方法です。

## カテゴリ

- [クイック修正](quick-fixes.md) — 最も一般的な問題の即解決法
- [接続問題](connection-issues.md) — サーバー接続・APIエラー
- [AIチャットの問題](ai-chat-issues.md) — AIの応答がない・遅い場合
- [FAQ](faq.md) — よくある質問と回答

## まず試すこと

1. **Dockerコンテナ**が実行中か確認：docker compose ps
2. **APIの状態**を確認：curl http://localhost:5055/health
3. **ブラウザのコンソール**でエラーを確認
4. **ログ**を確認：docker compose logs open_notebook
