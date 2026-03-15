#!/usr/bin/env python3
"""YouTube Analytics CLI - YouTube Data/Analytics/Reporting/Google Ads API 統合CLIツール"""

import csv
import json
import os
import sys
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

# ── 定数 ────────────────────────────────────────────────────────────────
DEFAULT_CONFIG_FILE = Path.home() / ".youtube-cli" / "config.toml"
DEFAULT_TOKEN_FILE  = Path.home() / ".youtube-cli" / "token.json"
DEFAULT_CLIENT_SECRETS = Path.home() / ".youtube-cli" / "client_secrets.json"

DEFAULTS: dict[str, Any] = {
    "auth": {
        "api_key": None,
        "client_secrets": str(DEFAULT_CLIENT_SECRETS),
        "token_file": str(DEFAULT_TOKEN_FILE),
    },
    "ads": {
        "customer_id": None,
        "developer_token": None,
    },
    "defaults": {
        "format": "json",
        "days": 30,
        "max_results": 50,
        "output": "-",
    },
}

ENV_MAP = {
    "YOUTUBE_API_KEY":           ("auth", "api_key"),
    "YOUTUBE_CLIENT_SECRETS":    ("auth", "client_secrets"),
    "YOUTUBE_TOKEN_FILE":        ("auth", "token_file"),
    "GOOGLE_ADS_CUSTOMER_ID":    ("ads", "customer_id"),
    "GOOGLE_ADS_DEVELOPER_TOKEN":("ads", "developer_token"),
    "YT_DEFAULT_FORMAT":         ("defaults", "format"),
    "YT_DEFAULT_DAYS":           ("defaults", "days"),
    "YT_CONFIG_FILE":            None,  # special
}


class ConfigError(Exception):
    pass


def load_config(
    config_file: str | None,
    env: dict,
    cli_args: dict,
    require_api_key: bool = False,
) -> dict:
    """設定を3層マージして返す（設定ファイル < 環境変数 < CLIフラグ）"""
    cfg = deepcopy(DEFAULTS)

    # Layer 1: 設定ファイル
    path = config_file or env.get("YT_CONFIG_FILE") or str(DEFAULT_CONFIG_FILE)
    if Path(path).exists():
        with open(path, "rb") as f:
            file_cfg = tomllib.load(f)
        _deep_merge(cfg, file_cfg)

    # Layer 2: 環境変数
    for env_key, mapping in ENV_MAP.items():
        if mapping and env_key in env:
            section, key = mapping
            val = env[env_key]
            if key == "days":
                val = int(val)
            cfg[section][key] = val

    # Layer 3: CLIフラグ
    cli_to_cfg = {
        "api_key":           ("auth", "api_key"),
        "client_secrets":    ("auth", "client_secrets"),
        "auth_file":         ("auth", "token_file"),
        "ads_customer_id":   ("ads", "customer_id"),
        "format":            ("defaults", "format"),
        "days":              ("defaults", "days"),
        "max_results":       ("defaults", "max_results"),
        "output":            ("defaults", "output"),
    }
    for cli_key, (section, key) in cli_to_cfg.items():
        if cli_args.get(cli_key) is not None:
            cfg[section][key] = cli_args[cli_key]

    if require_api_key and not cfg["auth"]["api_key"]:
        raise ConfigError(
            "api_key が設定されていません。"
            " $YOUTUBE_API_KEY 環境変数か --api-key フラグ、"
            " または ~/.youtube-cli/config.toml の [auth] api_key を設定してください。"
        )

    return cfg


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


# ── 認証レイヤー ─────────────────────────────────────────────────────────
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"

ALL_SCOPES = YOUTUBE_SCOPES + [GOOGLE_ADS_SCOPE]


def build_youtube_data_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def build_analytics_client(credentials):
    return build("youtubeAnalytics", "v2", credentials=credentials)


def build_reporting_client(credentials):
    return build("youtubereporting", "v1", credentials=credentials)


def load_oauth_credentials(
    token_file: str,
    client_secrets: str,
    scopes: list[str],
    token_file_exists: bool | None = None,
) -> Credentials:
    """OAuth2トークンをロード、必要に応じてリフレッシュ・新規取得"""
    exists = token_file_exists if token_file_exists is not None else Path(token_file).exists()
    creds = None

    if exists:
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, scopes)
            creds = flow.run_local_server(port=0)
        Path(token_file).parent.mkdir(parents=True, exist_ok=True)
        Path(token_file).write_text(creds.to_json())

    return creds


# ── YouTube Data API クライアント ────────────────────────────────────────

def get_channel_info(yt_client, channel_id: str | None) -> dict:
    """チャンネル情報を取得。channel_id=None の場合は自チャンネル"""
    params = dict(
        part="snippet,statistics,contentDetails,brandingSettings",
        maxResults=1,
    )
    if channel_id:
        params["id"] = channel_id
    else:
        params["mine"] = True

    resp = yt_client.channels().list(**params).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError(f"チャンネルが見つかりません: {channel_id or 'mine'}")
    return items[0]


def list_videos(
    yt_client,
    channel_id: str | None,
    max_results: int = 50,
    all_pages: bool = False,
) -> list[dict]:
    """チャンネルの動画一覧を取得"""
    ch = get_channel_info(yt_client, channel_id)
    uploads_id = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    page_token = None

    while True:
        params = dict(
            part="snippet,contentDetails,statistics",
            playlistId=uploads_id,
            maxResults=min(max_results - len(videos), 50),
        )
        if page_token:
            params["pageToken"] = page_token

        resp = yt_client.playlistItems().list(**params).execute()
        videos.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")

        if not all_pages or not page_token or len(videos) >= max_results:
            break

    return videos


def search_videos(
    yt_client,
    query: str,
    region: str | None = None,
    category_id: str | None = None,
    max_results: int = 50,
    all_pages: bool = False,
) -> list[dict]:
    """キーワード検索"""
    params = dict(
        part="snippet",
        q=query,
        type="video",
        maxResults=min(max_results, 50),
    )
    if region:
        params["regionCode"] = region
    if category_id:
        params["videoCategoryId"] = category_id

    results = []
    page_token = None

    while True:
        if page_token:
            params["pageToken"] = page_token
        resp = yt_client.search().list(**params).execute()
        results.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not all_pages or not page_token or len(results) >= max_results:
            break

    return results


# ── YouTube Analytics API クライアント ──────────────────────────────────

def get_video_analytics(
    analytics_client,
    channel_id: str,
    start_date: str,
    end_date: str,
    video_id: str | None = None,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
) -> dict:
    if metrics is None:
        metrics = [
            "views", "estimatedMinutesWatched", "averageViewDuration",
            "averageViewPercentage", "subscribersGained", "subscribersLost",
            "likes", "dislikes", "comments", "shares",
            "impressions", "impressionClickThroughRate",
        ]
    if dimensions is None:
        dimensions = ["day"]

    params = dict(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics=",".join(metrics),
        dimensions=",".join(dimensions),
    )
    if video_id:
        params["filters"] = f"video=={video_id}"

    return analytics_client.reports().query(**params).execute()


def get_demographics(
    analytics_client,
    channel_id: str,
    start_date: str,
    end_date: str,
    video_id: str | None = None,
) -> dict:
    params = dict(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="viewerPercentage",
        dimensions="ageGroup,gender",
    )
    if video_id:
        params["filters"] = f"video=={video_id}"
    return analytics_client.reports().query(**params).execute()


def get_traffic_sources(
    analytics_client,
    channel_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    return analytics_client.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched",
        dimensions="insightTrafficSourceType",
    ).execute()


def get_revenue(
    analytics_client,
    channel_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    return analytics_client.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="estimatedRevenue,estimatedAdRevenue,grossRevenue,cpm,adImpressions",
        dimensions="day",
    ).execute()


def analytics_response_to_records(response: dict) -> list[dict]:
    """Analytics APIレスポンスを [{col: val, ...}] 形式に変換"""
    headers = [h["name"] for h in response.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in response.get("rows", [])]


# ── YouTube Reporting API クライアント ──────────────────────────────────
import urllib.request

def list_report_types(reporting_client) -> list[dict]:
    resp = reporting_client.reportTypes().list().execute()
    return resp.get("reportTypes", [])


def list_reporting_jobs(reporting_client) -> list[dict]:
    resp = reporting_client.jobs().list().execute()
    return resp.get("jobs", [])


def create_reporting_job(reporting_client, report_type_id: str, name: str) -> dict:
    body = {"reportTypeId": report_type_id, "name": name}
    return reporting_client.jobs().create(body=body).execute()


def list_reports_for_job(reporting_client, job_id: str) -> list[dict]:
    resp = reporting_client.jobs().reports().list(jobId=job_id).execute()
    return resp.get("reports", [])


def download_report(download_url: str, credentials) -> list[dict]:
    """レポートCSVをダウンロードして辞書リストで返す"""
    import io
    req = urllib.request.Request(
        download_url,
        headers={"Authorization": f"Bearer {credentials.token}"},
    )
    with urllib.request.urlopen(req) as f:
        content = f.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


# ── Google Ads API クライアント + ROI計算 ────────────────────────────────

def build_google_ads_client(config: dict):
    """Google Ads APIクライアントを構築"""
    from google.ads.googleads.client import GoogleAdsClient as _GoogleAdsClient
    credentials = {
        "developer_token": config["ads"]["developer_token"],
        "use_proto_plus": True,
    }
    token_file = config["auth"]["token_file"]
    if Path(token_file).exists():
        import json as _json
        token_data = _json.loads(Path(token_file).read_text())
        credentials.update({
            "client_id": token_data.get("client_id"),
            "client_secret": token_data.get("client_secret"),
            "refresh_token": token_data.get("refresh_token"),
        })
    return _GoogleAdsClient.load_from_dict(credentials)


def get_video_ad_spend(
    ads_client,
    customer_id: str,
    start_date: str,
    end_date: str,
    video_id: str | None = None,
) -> list[dict]:
    """動画への広告費をGoogle Ads APIから取得"""
    ga_service = ads_client.get_service("GoogleAdsService")
    cid = customer_id.replace("-", "")

    where_clause = f"WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'"
    if video_id:
        where_clause += f" AND video.id = '{video_id}'"

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.date,
            metrics.cost_micros,
            metrics.video_views,
            metrics.impressions
        FROM campaign
        {where_clause}
        ORDER BY segments.date DESC
    """

    rows = []
    for row in ga_service.search(customer_id=cid, query=query):
        rows.append({
            "campaign_id": str(row.campaign.id),
            "campaign_name": row.campaign.name,
            "date": row.segments.date,
            "cost_yen": row.metrics.cost_micros / 1_000_000,
            "video_views": row.metrics.video_views,
            "impressions": row.metrics.impressions,
        })
    return rows


def calculate_roi(
    total_cost_yen: float,
    subscribers_gained: int,
    views: int,
) -> dict:
    """ROI指標を計算して返す"""
    return {
        "total_cost_yen": total_cost_yen,
        "subscribers_gained": subscribers_gained,
        "views": views,
        "cost_per_subscriber_yen": total_cost_yen / subscribers_gained if subscribers_gained else None,
        "cost_per_view_yen": total_cost_yen / views if views else None,
        "subscriber_per_cost_ratio": subscribers_gained / total_cost_yen if total_cost_yen else None,
    }


# ── 出力レイヤー ─────────────────────────────────────────────────────────
import io as _io
from datetime import datetime, timezone

FIELD_DESCRIPTIONS: dict[str, str] = {
    "views":                       "総再生回数",
    "estimatedMinutesWatched":     "推定視聴時間（分）",
    "averageViewDuration":         "平均視聴時間（秒）",
    "averageViewPercentage":       "平均視聴率（%）",
    "subscribersGained":           "登録者増加数",
    "subscribersLost":             "登録解除数",
    "likes":                       "高評価数",
    "comments":                    "コメント数",
    "shares":                      "共有数",
    "impressions":                 "インプレッション数",
    "impressionClickThroughRate":  "インプレッションCTR（%）",
    "estimatedRevenue":            "推定総収益（USD）",
    "estimatedAdRevenue":          "推定広告収益（USD）",
    "grossRevenue":                "総収益（USD）",
    "cpm":                         "CPM（1000インプレッションあたりコスト、USD）",
    "viewerPercentage":            "視聴者割合（%）",
    "ageGroup":                    "年齢層（age13-17, age18-24, age25-34, age35-44, age45-54, age55-64, age65-）",
    "gender":                      "性別（male/female）",
    "cost_yen":                    "広告費（円）",
    "cost_per_subscriber_yen":     "登録者1人あたり広告費（円）",
    "cost_per_view_yen":           "再生1回あたり広告費（円）",
    "subscriber_per_cost_ratio":   "1円あたりの登録者獲得率",
}

SCHEMA: dict[str, Any] = {
    "channel_info": {
        "description": "チャンネル基本情報",
        "properties": {
            "id": {"type": "string", "description": "チャンネルID"},
            "snippet.title": {"type": "string", "description": "チャンネル名"},
            "statistics.subscriberCount": {"type": "string", "description": "登録者数"},
            "statistics.viewCount": {"type": "string", "description": "総再生数"},
            "statistics.videoCount": {"type": "string", "description": "動画数"},
        }
    },
    "analytics": {
        "description": "動画パフォーマンス指標（YouTube Analytics API）",
        "properties": {k: {"type": "number", "description": v}
                      for k, v in FIELD_DESCRIPTIONS.items()
                      if k not in ("ageGroup", "gender", "cost_yen",
                                   "cost_per_subscriber_yen", "cost_per_view_yen",
                                   "subscriber_per_cost_ratio")},
    },
    "roi": {
        "description": "広告ROI指標",
        "properties": {k: {"type": "number", "description": v}
                      for k, v in FIELD_DESCRIPTIONS.items()
                      if k in ("cost_yen", "cost_per_subscriber_yen",
                               "cost_per_view_yen", "subscriber_per_cost_ratio")},
    },
}


def generate_schema() -> dict:
    return SCHEMA


def add_field_context(data: dict) -> dict:
    """データに _context フィールドを追加（LLM向け）"""
    if isinstance(data, dict):
        context = {k: FIELD_DESCRIPTIONS[k]
                  for k in data if k in FIELD_DESCRIPTIONS}
        if context:
            return {**data, "_context": context}
    return data


def format_output(
    data: Any,
    fmt: str = "json",
    pretty: bool = False,
    with_meta: bool = True,
    query_params: dict | None = None,
    with_context: bool = False,
    prompt_hint: bool = False,
) -> str:
    """データを指定フォーマットで文字列に変換"""

    if with_context and isinstance(data, dict):
        data = add_field_context(data)
    elif with_context and isinstance(data, list):
        data = [add_field_context(d) if isinstance(d, dict) else d for d in data]

    if fmt == "json":
        if with_meta:
            payload: dict[str, Any] = {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "query": query_params or {},
                    "schema_hint": "実行時に --schema オプションで全フィールド定義を確認できます",
                },
                "data": data,
            }
            if prompt_hint:
                payload["meta"]["llm_usage_hint"] = (
                    "このJSONをLLMに渡す場合: data フィールドに分析対象データが含まれます。"
                    "meta.query で取得条件を確認してください。"
                    "--with-context オプションで各フィールドの日本語説明が付与されます。"
                )
        else:
            payload = data
        indent = 2 if pretty else None
        return json.dumps(payload, ensure_ascii=False, indent=indent)

    elif fmt == "ndjson":
        items = data if isinstance(data, list) else [data]
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in items)

    elif fmt == "csv":
        if not isinstance(data, list) or not data:
            return ""
        output = _io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    else:
        raise ValueError(f"未対応のフォーマット: {fmt}. json/csv/ndjson から選択してください。")


def write_output(content: str, output_path: str) -> None:
    """標準出力またはファイルに書き出す"""
    if output_path == "-":
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
    else:
        Path(output_path).write_text(content, encoding="utf-8")
        print(f"✅ 出力完了: {output_path}", file=sys.stderr)


def run_auth_flow(config: dict) -> None:
    """--auth コマンド: 対話認証フローを実行してトークンを保存"""
    print("🔑 OAuth2認証フローを開始します...")
    creds = load_oauth_credentials(
        token_file=config["auth"]["token_file"],
        client_secrets=config["auth"]["client_secrets"],
        scopes=ALL_SCOPES,
    )
    print(f"✅ 認証完了。トークンを保存しました: {config['auth']['token_file']}")
    return creds
