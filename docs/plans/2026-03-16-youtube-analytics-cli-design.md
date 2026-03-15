# YouTube Analytics CLI 設計書

**日付:** 2026-03-16
**ファイル:** `youtube_analytics.py`

## 概要

YouTube Data API v3 / YouTube Analytics API / YouTube Reporting API / Google Ads API を統合したPython製CLIスクリプト。自チャンネル分析と外部リサーチを一本で行い、AI活用を最大化する。

---

## アーキテクチャ

```
youtube_analytics.py（単一ファイル）
│
├── 設定レイヤー（優先順位: 設定ファイル < 環境変数 < CLIフラグ）
│   ├── ~/.youtube-cli/config.toml
│   └── 環境変数（YOUTUBE_API_KEY, GOOGLE_ADS_CUSTOMER_ID, etc.）
│
├── 認証レイヤー
│   ├── APIキー認証 ($YOUTUBE_API_KEY) → 公開データ
│   ├── OAuth2 YouTube scopes → Analytics/Revenue/Reporting
│   └── OAuth2 Google Ads scope → 広告費データ
│
├── データ取得クライアント
│   ├── YouTubeDataClient   (Data API v3)
│   ├── AnalyticsClient     (YouTube Analytics API)
│   ├── ReportingClient     (YouTube Reporting API)
│   └── GoogleAdsClient     (Google Ads API - GAQL)
│
└── 出力レイヤー
    ├── JSON（デフォルト、LLM向け構造化）
    ├── NDJSON（ストリーミング・パイプライン向け）
    └── CSV（スプレッドシート向け）
```

---

## CLI引数設計

```
usage: youtube_analytics.py [OPTIONS]

🔑 認証
  --auth                    OAuth2認証フロー起動（初回・トークン更新）
  --auth-file PATH          OAuth2トークン保存先（default: ~/.youtube-cli/token.json）
  --client-secrets PATH     client_secrets.json パス

🎯 対象指定
  --channel CHANNEL_ID      対象チャンネルID（省略時は自チャンネル）
  --video VIDEO_ID          単一動画ID
  --query TEXT              検索キーワード
  --region CC               地域コード（JP, US など）
  --category-id ID          動画カテゴリID

📦 取得データ
  --channel-info            チャンネル基本情報
  --videos                  動画一覧＋メタデータ
  --analytics               視聴回数・視聴時間・インプレッション（要OAuth）
  --demographics            視聴者属性（年齢・性別・地域）（要OAuth）
  --traffic                 トラフィックソース（要OAuth）
  --revenue                 収益データ（要OAuth）
  --report TYPE             Reportingバルクレポート
  --all-data                全データ取得

📊 Google Ads連携
  --ads-customer-id CID     Google Ads カスタマーID
  --ads-campaign            キャンペーン別広告費取得
  --ads-video VIDEO_ID      特定動画の広告費
  --roi                     ROIレポート（広告費÷登録者増加数）

📅 期間
  --days N                  直近N日間（default: 30）
  --start YYYY-MM-DD        開始日
  --end YYYY-MM-DD          終了日

📄 ページネーション
  --max-results N           最大件数（default: 50）
  --all-pages               全ページ取得

📤 出力
  --format json|csv|ndjson  出力形式（default: json）
  --output PATH             出力ファイル（default: stdout）
  --pretty                  JSON整形出力
  --no-meta                 メタ情報を除外

🤖 AI活用
  --schema                  全フィールドのJSONスキーマを出力して終了
  --schema-for FIELD        特定フィールドのスキーマのみ
  --with-context            フィールドに説明文を付与（LLM向け）
  --dry-run                 APIリクエスト内容を表示して終了
  --prompt-hint             LLMへの渡し方ヒントを出力に付与
  --retry N                 クォータ超過時のリトライ回数（default: 3）
```

---

## 設定ファイル

**`~/.youtube-cli/config.toml`:**
```toml
[auth]
api_key = "AIza..."
client_secrets = "~/.youtube-cli/client_secrets.json"
token_file = "~/.youtube-cli/token.json"

[ads]
customer_id = "123-456-7890"
developer_token = "..."

[defaults]
format = "json"
days = 30
max_results = 50
output = "-"
```

**環境変数:**
```
YOUTUBE_API_KEY
YOUTUBE_CLIENT_SECRETS
YOUTUBE_TOKEN_FILE
GOOGLE_ADS_CUSTOMER_ID
GOOGLE_ADS_DEVELOPER_TOKEN
YT_DEFAULT_FORMAT
YT_DEFAULT_DAYS
YT_CONFIG_FILE
```

---

## JSON出力構造（AI向け）

```json
{
  "meta": {
    "generated_at": "2026-03-16T06:53:00Z",
    "query": { "channel": "UC...", "days": 30 },
    "api_units_used": 12,
    "schema_url": "run with --schema to see field definitions"
  },
  "data": { ... }
}
```

---

## ROIレポート計算

```
cost_per_subscriber = 広告費(円) / subscribersGained
subscriber_rate     = subscribersGained / impressions
```

Google Ads API (GAQL) で `metrics.cost_micros` を取得し、YouTube Analytics の `subscribersGained` と動画IDで突合。

---

## 依存ライブラリ

```
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
google-ads
```

---

## ファイル構成

```
youtube_analytics.py
requirements.txt
~/.youtube-cli/
  config.toml
  client_secrets.json
  token.json
```
