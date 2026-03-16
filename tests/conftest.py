"""
統合テスト用フィクスチャ
~/.youtube-cli/token.json から認証情報をロードして実APIを使う
"""
import json
import os
import pytest
from pathlib import Path

TOKEN_FILE = Path.home() / ".youtube-cli" / "token.json"
CLIENT_SECRETS = Path.home() / ".youtube-cli" / "client_secrets.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def _load_credentials():
    """token.json から Python google-auth Credentials を構築"""
    if not TOKEN_FILE.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        data = json.loads(TOKEN_FILE.read_text())

        # Python google-auth 形式か Node.js 形式かを判別
        if "token" in data:
            # Python 形式
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        else:
            # Node.js 形式 (access_token, expiry_date, etc.)
            from datetime import datetime, timezone
            client_data = json.loads(CLIENT_SECRETS.read_text())["installed"]
            expiry = None
            if "expiry_date" in data:
                expiry = datetime.fromtimestamp(
                    data["expiry_date"] / 1000, tz=timezone.utc
                )
            creds = Credentials(
                token=data.get("access_token"),
                refresh_token=data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_data["client_id"],
                client_secret=client_data["client_secret"],
                scopes=SCOPES,
                expiry=expiry,
            )

        # トークンリフレッシュ試行
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 更新後保存
                py_format = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else SCOPES,
                }
                TOKEN_FILE.write_text(json.dumps(py_format, indent=2))
            else:
                return None

        return creds
    except Exception as e:
        print(f"[conftest] 認証情報ロード失敗: {e}")
        return None


# モジュールレベルで一度だけ認証情報をロード
_CREDS = _load_credentials()
_NEED_AUTH = _CREDS is None


@pytest.fixture(scope="session")
def credentials():
    """OAuth2 認証情報フィクスチャ"""
    if _CREDS is None:
        pytest.skip("OAuth認証が必要: python youtube_analytics.py --auth を実行してください")
    return _CREDS


@pytest.fixture(scope="session")
def yt_client(credentials):
    """YouTube Data API v3 クライアント（OAuth認証済み）"""
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=credentials)


@pytest.fixture(scope="session")
def analytics_client(credentials):
    """YouTube Analytics API v2 クライアント"""
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=credentials)


@pytest.fixture(scope="session")
def reporting_client(credentials):
    """YouTube Reporting API v1 クライアント"""
    from googleapiclient.discovery import build
    return build("youtubereporting", "v1", credentials=credentials)


@pytest.fixture(scope="session")
def my_channel_id(yt_client):
    """認証済みユーザーのチャンネルIDを取得"""
    resp = yt_client.channels().list(part="id", mine=True).execute()
    items = resp.get("items", [])
    assert items, "チャンネルが見つかりません"
    return items[0]["id"]


@pytest.fixture(scope="session")
def date_range():
    """テスト用の日付範囲（直近30日）"""
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()
