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
