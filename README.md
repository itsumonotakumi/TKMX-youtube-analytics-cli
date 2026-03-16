# TKMX YouTube Analytics CLI

YouTube Data API v3 / Analytics API / Reporting API / Google Ads API を統合した単一ファイルCLIツール。チャンネル分析・動画パフォーマンス・広告ROIをターミナルから取得できます。

## 🚀 クイックスタート

```bash
# 依存インストール
pip install -r requirements.txt

# 初回OAuth認証
python youtube_analytics.py --auth

# チャンネル情報を取得
python youtube_analytics.py --channel-info --pretty

# 過去30日のAnalytics
python youtube_analytics.py --analytics --pretty

# フィールド定義確認（AI向け）
python youtube_analytics.py --schema
```

## 📦 インストール

**必要条件:** Python 3.11+

```bash
git clone https://github.com/itsumonotakumi/TKMX-youtube-analytics-cli.git
cd TKMX-youtube-analytics-cli
pip install -r requirements.txt
```

### 認証セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) で OAuth2 クライアントシークレットを作成
2. `~/.youtube-cli/client_secrets.json` に配置
3. 初回認証を実行:

```bash
python youtube_analytics.py --auth
```

**公開データのみ**（検索など）は `$YOUTUBE_API_KEY` 環境変数だけで利用可能:

```bash
export YOUTUBE_API_KEY="AIzaSy..."
python youtube_analytics.py --query "Python 入門" --region JP
```

## ⚙️ 設定ファイル

`~/.youtube-cli/config.toml` で永続設定:

```toml
[auth]
api_key = "AIzaSy..."
client_secrets = "~/.youtube-cli/client_secrets.json"
token_file = "~/.youtube-cli/token.json"

[ads]
customer_id = "1234567890"
developer_token = "your-developer-token"

[defaults]
format = "json"
days = 30
max_results = 50
```

**優先順位:** 設定ファイル < 環境変数 < CLIフラグ

## 📋 主要オプション

| オプション | 説明 |
|-----------|------|
| `--channel-info` | チャンネル基本情報（登録者数・再生数・動画数） |
| `--videos` | 動画一覧＋メタデータ |
| `--analytics` | 視聴回数・視聴時間・登録者増減（要OAuth） |
| `--demographics` | 視聴者属性（年齢・性別）（要OAuth） |
| `--traffic` | トラフィックソース（要OAuth） |
| `--revenue` | 収益データ（要OAuth） |
| `--roi` | 広告ROIレポート（要Google Ads） |
| `--query TEXT` | キーワード検索（公開データ） |
| `--dry-run` | API呼び出しなしでリクエスト内容を表示 |
| `--schema` | 全フィールドのJSON定義を出力 |

### 出力形式

```bash
--format json    # デフォルト（メタ情報付き）
--format csv     # CSV（スプレッドシート向け）
--format ndjson  # 改行区切りJSON（ストリーム処理向け）
--pretty         # JSON整形出力
--no-meta        # メタ情報を除外
```

### AI活用オプション

```bash
--schema              # フィールド定義をJSONで出力
--with-context        # 各フィールドに日本語説明を付与
--prompt-hint         # LLMへの渡し方ヒントを付与
```

## 💡 使用例

```bash
# 自チャンネルの概要（整形JSON）
python youtube_analytics.py --channel-info --pretty

# 過去7日間のAnalytics → CSV保存
python youtube_analytics.py --analytics --days 7 --format csv --output analytics.csv

# 特定チャンネルの動画一覧
python youtube_analytics.py --channel UCxxxxxx --videos --max-results 20

# 動画の詳細Analytics + 広告ROI
python youtube_analytics.py --video VIDEO_ID --analytics --roi --ads-customer-id 1234567890

# キーワード検索（日本・最大10件）
python youtube_analytics.py --query "Python 入門" --region JP --max-results 10

# LLM向けフル出力
python youtube_analytics.py --all-data --with-context --prompt-hint --pretty

# ドライラン（APIキー不要・リクエスト内容確認）
python youtube_analytics.py --channel UCxxxxxx --analytics --roi --dry-run
```

## 🏗️ アーキテクチャ

単一ファイル (`youtube_analytics.py`) で完結する4層構成:

```
設定レイヤー    load_config()          TOML / 環境変数 / CLI の3層マージ
認証レイヤー    load_oauth_credentials()  APIキー / OAuth2
APIクライアント  get_channel_info() etc.  YouTube Data / Analytics / Reporting / Google Ads
出力レイヤー    format_output()        JSON / NDJSON / CSV
```

## 🧪 テスト

```bash
pip install -r requirements-dev.txt

# 全テスト実行（125テスト）
pytest tests/ -v
```

実APIを使った統合テストを含みます（OAuth認証済みの場合）。

## 📄 ライセンス

MIT
