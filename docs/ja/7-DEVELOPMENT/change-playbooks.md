# 変更プレイブック

## 新機能の追加

1. フィーチャーブランチを作成
2. 実装（必要に応じてテストも）
3. i18n文字列を全ロケールファイルに追加（`frontend/src/lib/locales/`）
4. ドキュメントを更新（`docs/` および `docs/ja/`）

## バグ修正

1. 問題を再現するテストを書く
2. 修正を実装
3. テストが通ることを確認
4. CHANGELOGを更新

## i18n / 翻訳更新

1. `frontend/src/lib/locales/en-US/index.ts` に英文字列を追加
2. 全ロケールファイル（`ja-JP`, `zh-CN` 等）に同じキーを追加
3. 翻訳がないロケールは英語をプレースホルダとして使用

> 原文: [Change Playbooks](../change-playbooks.md)