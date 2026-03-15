# YouTube Analytics CLI

YouTube Data API v3 / Analytics API / Reporting API / Google Ads API を統合した単一ファイルCLIツール。

## プロジェクト構造

```
youtube-cli/
├── youtube_analytics.py   # メインスクリプト（単一ファイル）
├── requirements.txt       # 本番依存
├── requirements-dev.txt   # 開発依存（pytest）
├── tests/
│   ├── test_config.py     # 設定レイヤーテスト
│   ├── test_auth.py       # 認証レイヤーテスト
│   ├── test_youtube_data.py  # YouTube Data APIテスト
│   ├── test_analytics.py  # Analytics APIテスト
│   ├── test_reporting.py  # Reporting APIテスト
│   ├── test_ads.py        # Google Ads + ROIテスト
│   ├── test_output.py     # 出力レイヤーテスト
│   └── test_cli.py        # CLIエントリポイントテスト
└── docs/plans/            # 設計・実装ドキュメント
```

## アーキテクチャ

単一ファイル構成。レイヤー順:

1. **設定レイヤー** (`load_config`) - TOML < ENV < CLI の3層マージ
2. **認証レイヤー** (`load_oauth_credentials`, `build_*_client`) - APIキー / OAuth2
3. **APIクライアント** - YouTube Data / Analytics / Reporting / Google Ads
4. **出力レイヤー** (`format_output`, `write_output`) - JSON / NDJSON / CSV
5. **CLIエントリポイント** (`build_parser`, `main`) - argparse

## よく使うコマンド

```bash
# テスト実行
pytest tests/ -v

# 依存インストール
pip install -r requirements.txt -r requirements-dev.txt

# --help 表示
python youtube_analytics.py --help

# スキーマ確認（AI向け）
python youtube_analytics.py --schema | jq .

# ドライラン（API呼び出しなし）
python youtube_analytics.py --channel UCxxxxxx --analytics --roi --dry-run

# 初回OAuth認証
python youtube_analytics.py --auth
```

## 初期セットアップ

1. `~/.youtube-cli/client_secrets.json` に Google Cloud Console からダウンロードした OAuth2 クライアントシークレットを配置
2. 公開データのみ使用する場合は `YOUTUBE_API_KEY` 環境変数を設定
3. 初回 OAuth 認証: `python youtube_analytics.py --auth`

## 設定ファイル例

```toml
# ~/.youtube-cli/config.toml
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

## 認証フロー

- **公開データ（チャンネル検索など）**: `YOUTUBE_API_KEY` 環境変数または `--api-key` フラグ
- **自チャンネル・収益・Analytics**: OAuth2（`--auth` で初回認証）
- **Google Ads**: OAuth2（同トークン使用）
