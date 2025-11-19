# Open Notebook UI 日本語化実装ガイド

このドキュメントは、Open NotebookのフロントエンドUIを完全に日本語化するための詳細な実装ガイドです。

---

## 📋 概要

**目標**: フロントエンドの157個のTypeScript/Reactファイルを日本語対応にする

**技術スタック**:
- **フレームワーク**: Next.js 15.4.7 (App Router)
- **推奨i18nライブラリ**: `next-intl` v3.x
- **推定工数**: 8-12時間

---

## 🎯 実装戦略

### フェーズ1: next-intl のセットアップ (1時間)

#### 1.1 依存関係のインストール

```bash
cd frontend
npm install next-intl
```

#### 1.2 i18n設定ファイルの作成

**`frontend/src/i18n/request.ts`:**
```typescript
import {getRequestConfig} from 'next-intl/server';
import {cookies} from 'next/headers';

export default getRequestConfig(async () => {
  // クッキーまたはブラウザ設定からロケールを取得
  const cookieStore = await cookies();
  const locale = cookieStore.get('NEXT_LOCALE')?.value || 'ja';

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default
  };
});
```

**`frontend/src/middleware.ts` に追加:**
```typescript
import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'ja'],
  defaultLocale: 'ja', // デフォルトを日本語に
  localePrefix: 'as-needed' // URLに/jaを付けない
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
};
```

#### 1.3 Next.js設定の更新

**`frontend/next.config.js`:**
```javascript
const withNextIntl = require('next-intl/plugin')('./src/i18n/request.ts');

module.exports = withNextIntl({
  // 既存の設定...
});
```

---

### フェーズ2: 翻訳ファイルの構造化 (2時間)

#### 2.1 ディレクトリ構造

```
frontend/
├── messages/
│   ├── en.json          # 英語翻訳（既存のテキストから抽出）
│   └── ja.json          # 日本語翻訳
├── src/
│   ├── i18n/
│   │   └── request.ts   # i18n設定
│   └── middleware.ts    # ロケールミドルウェア
```

#### 2.2 翻訳ファイルのスキーマ設計

**`frontend/messages/ja.json` の構造:**
```json
{
  "common": {
    "save": "保存",
    "cancel": "キャンセル",
    "delete": "削除",
    "edit": "編集",
    "create": "作成",
    "close": "閉じる",
    "loading": "読み込み中...",
    "error": "エラーが発生しました"
  },
  "notebooks": {
    "title": "ノートブック",
    "create": "新しいノートブックを作成",
    "empty": "ノートブックがありません",
    "archived": "アーカイブ済み",
    "search": "ノートブックを検索..."
  },
  "sources": {
    "title": "ソース",
    "add": "ソースを追加",
    "upload": "ファイルをアップロード",
    "url": "URLから追加",
    "text": "テキストを追加",
    "processing": "処理中..."
  },
  "chat": {
    "title": "チャット",
    "placeholder": "メッセージを入力...",
    "send": "送信",
    "clear": "履歴をクリア",
    "newSession": "新しいセッション"
  },
  "notes": {
    "title": "ノート",
    "create": "ノートを作成",
    "edit": "ノートを編集",
    "delete": "ノートを削除"
  },
  "transformations": {
    "title": "変換",
    "apply": "変換を適用",
    "custom": "カスタム変換",
    "summarize": "要約",
    "extract": "抽出"
  },
  "settings": {
    "title": "設定",
    "models": "モデル設定",
    "language": "言語",
    "theme": "テーマ",
    "account": "アカウント"
  }
}
```

---

### フェーズ3: コンポーネントの段階的移行 (5-7時間)

#### 3.1 優先順位付けされたコンポーネント

**Tier 1 (最優先 - ユーザーに最も見える部分):**
1. `NotebookHeader.tsx` - ノートブックタイトルとアクション
2. `SourcesColumn.tsx` - ソースリスト
3. `ChatColumn.tsx` - チャットインターフェース
4. `NotesColumn.tsx` - ノートリスト
5. ナビゲーションメニュー

**Tier 2 (中優先度):**
6. 設定画面 (`models/page.tsx`)
7. 変換画面 (`transformations/page.tsx`)
8. 検索機能 (`search/page.tsx`)

**Tier 3 (低優先度 - エラーやトースト):**
9. エラーメッセージ
10. トースト通知

#### 3.2 コンポーネント移行の例

**変更前** (`NotebookHeader.tsx`):
```typescript
<Button>
  Delete Notebook
</Button>
```

**変更後**:
```typescript
import {useTranslations} from 'next-intl';

export function NotebookHeader() {
  const t = useTranslations('notebooks');

  return (
    <Button>
      {t('delete')}
    </Button>
  );
}
```

#### 3.3 日付のローカライズ

**`date-fns` ロケール設定:**
```typescript
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

// 変更前
formatDistanceToNow(new Date(notebook.updated_at))

// 変更後
formatDistanceToNow(new Date(notebook.updated_at), { locale: ja, addSuffix: true })
// 出力: "2時間前"
```

---

### フェーズ4: 動的テキストの処理 (1-2時間)

#### 4.1 複数形の処理

```json
{
  "sources": {
    "count": "{count, plural, =0 {ソースなし} =1 {1個のソース} other {#個のソース}}"
  }
}
```

使用例:
```typescript
const t = useTranslations('sources');
<p>{t('count', { count: sourceList.length })}</p>
```

#### 4.2 変数の挿入

```json
{
  "chat": {
    "greeting": "こんにちは、{name}さん！"
  }
}
```

使用例:
```typescript
<h1>{t('chat.greeting', { name: user.name })}</h1>
```

---

### フェーズ5: テストと検証 (1時間)

#### 5.1 チェックリスト

- [ ] 全UI要素が日本語で表示される
- [ ] 日付が日本語形式（YYYY/MM/DD）
- [ ] 数値が適切にフォーマットされる
- [ ] 長い日本語テキストでレイアウトが崩れない
- [ ] エラーメッセージが日本語
- [ ] トースト通知が日本語

#### 5.2 ブラウザテスト

```bash
# 開発サーバー起動
cd frontend
npm run dev

# ブラウザでテスト:
# 1. http://localhost:3000 にアクセス
# 2. 全ページを確認
# 3. 各機能を実行してメッセージを確認
```

---

## 🛠️ 実装時のベストプラクティス

### 1. 用語の統一

| 英語 | 日本語 | 備考 |
|------|--------|------|
| Notebook | ノートブック | 「研究ノート」は避ける |
| Source | ソース | 「情報源」は使用しない |
| Chat | チャット | そのまま |
| Transformation | 変換 | 「トランスフォーメーション」は避ける |
| Podcast | ポッドキャスト | カタカナ |
| Embedding | 埋め込み | 「エンベディング」も可 |
| Model | モデル | そのまま |
| Settings | 設定 | そのまま |

### 2. 文字数制限の考慮

日本語は英語より文字数が多くなる傾向があるため、UIレイアウトに注意:

```typescript
// ボタンテキストは簡潔に
"Delete" → "削除" (OK)
"Delete Notebook" → "削除" (ボタン内では省略)

// ツールチップで詳細を提供
<Button title="ノートブックを削除">削除</Button>
```

### 3. 自然な日本語

直訳を避け、日本人が読んで自然な表現を使用:

```
❌ "Please select a notebook" → "ノートブックを選択してください"
✅ "ノートブックを選択"

❌ "Successfully saved" → "成功的に保存されました"
✅ "保存しました"
```

---

## 📦 翻訳ファイルの例

完全な翻訳ファイルの例は、リポジトリの `frontend/messages/ja.example.json` を参照してください（今後追加予定）。

---

## 🚀 段階的な移行戦略

全157ファイルを一度に変更するのではなく、段階的にリリース:

**v1.3.0**: Tier 1コンポーネント（メインUI）の日本語化
**v1.3.1**: Tier 2コンポーネント（設定、変換）の日本語化
**v1.4.0**: 完全な日本語化（エラー、ログを含む）

各リリース間でユーザーフィードバックを収集し、用語や表現を調整します。

---

## 🤝 コントリビューション

日本語翻訳の改善提案は歓迎します！

**プロセス**:
1. `frontend/messages/ja.json` を編集
2. ブラウザで確認
3. Pull Requestを作成

**翻訳のレビュー基準**:
- 自然な日本語であること
- 用語が統一されていること
- UIに収まる文字数であること
- 意味が正確に伝わること

---

## 📚 参考リンク

- **next-intl 公式ドキュメント**: https://next-intl-docs.vercel.app/
- **Next.js App Router i18n**: https://nextjs.org/docs/app/building-your-application/routing/internationalization
- **date-fns ロケール**: https://date-fns.org/v2.29.3/docs/I18n

---

**最終更新**: 2025年11月18日
**ステータス**: 設計書 - 実装準備完了
**次のステップ**: `next-intl` のインストールとセットアップ
