# アイデアソン・アシスタント

AIと一緒にブレインストーミングができるWebアプリです。
フレームワークを活用して効率的にアイデアを発想・評価できます。

## 機能

- **アイデア生成**: テーマを入力してAIがアイデアを生成
- **フレームワーク選択**: SCAMPER、6W2H、オズボーンのチェックリスト
- **アイデア評価**: 4つの観点（実現可能性、コスト、インパクト、新規性）で評価
- **深掘り**: 選んだアイデアを詳細化
- **組み合わせ**: 2つのアイデアを掛け合わせて新案を生成
- **エクスポート**: JSON/テキスト形式でダウンロード

## セットアップ

### 1. 依存関係のインストール

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. APIキーの設定

1. https://aistudio.google.com でAPIキーを取得
2. `.streamlit/secrets.toml` を作成

```toml
GOOGLE_API_KEY = "your-api-key-here"
```

### 3. 実行

```bash
streamlit run app.py
```

## デプロイ（Streamlit Community Cloud）

1. GitHubにリポジトリをpush
2. https://share.streamlit.io でデプロイ
3. Secretsに `GOOGLE_API_KEY` を設定

## ライセンス

MIT
