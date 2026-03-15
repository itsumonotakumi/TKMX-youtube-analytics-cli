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
