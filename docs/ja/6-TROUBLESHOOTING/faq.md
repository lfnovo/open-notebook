# FAQ（よくある質問）

## インストール

**Q: Dockerが起動しません**  
A: Docker Desktopが実行中か確認してください。エラーが続く場合は[接続問題](connection-issues.md)を参照。

**Q: 環境変数の設定方法がわかりません**  
A: .env.exampleを.envにコピーし、OPEN_NOTEBOOK_ENCRYPTION_KEYを編集するだけです。

## AI

**Q: AIが応答しません**  
A: APIキーが正しく設定されているか確認。Settings → API Keysで接続テストを実行してください。

**Q: ローカルLLM（Ollama）が遅いです**  
A: より小さいモデル（mistral, phi等）を試すか、ハードウェアを確認してください。

**Q: 複数のAIプロバイダーを併用できますか？**  
A: はい。用途に応じて使い分けられます（例：チャットはOpenAI、埋め込みはOllama）。

## データ

**Q: データのバックアップ方法は？**  
A: SurrealDBのデータディレクトリをバックアップしてください。Docker使用時はdocker compose downで永続化されます。

> 原文: [FAQ](../faq.md)
