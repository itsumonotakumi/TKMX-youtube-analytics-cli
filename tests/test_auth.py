"""認証レイヤーテスト - 実APIを使った統合テスト"""
import json
import pytest
from pathlib import Path


# ── ユニットテスト（APIクライアントビルダー）────────────────────────────

def test_build_youtube_data_client_returns_resource(mocker):
    mocker.patch("youtube_analytics.build")
    from youtube_analytics import build_youtube_data_client
    build_youtube_data_client(api_key="test_key")
    import youtube_analytics as ya
    ya.build.assert_called_once_with("youtube", "v3", developerKey="test_key")

def test_build_analytics_client_uses_credentials(mocker):
    mocker.patch("youtube_analytics.build")
    mock_creds = mocker.MagicMock()
    from youtube_analytics import build_analytics_client
    build_analytics_client(credentials=mock_creds)
    import youtube_analytics as ya
    ya.build.assert_called_once_with("youtubeAnalytics", "v2", credentials=mock_creds)

def test_build_reporting_client_uses_credentials(mocker):
    mocker.patch("youtube_analytics.build")
    mock_creds = mocker.MagicMock()
    from youtube_analytics import build_reporting_client
    build_reporting_client(credentials=mock_creds)
    import youtube_analytics as ya
    ya.build.assert_called_once_with("youtubereporting", "v1", credentials=mock_creds)


# ── 認証情報ファイルロードテスト ────────────────────────────────────────

def test_load_credentials_from_valid_token(mocker, tmp_path):
    from youtube_analytics import load_oauth_credentials
    mock_creds = mocker.MagicMock()
    mock_creds.valid = True
    mocker.patch("youtube_analytics.Credentials.from_authorized_user_file",
                 return_value=mock_creds)
    creds = load_oauth_credentials(
        token_file=str(tmp_path / "token.json"),
        client_secrets="dummy.json",
        scopes=["scope1"],
        token_file_exists=True,
    )
    assert creds == mock_creds

def test_load_credentials_no_file_triggers_flow(mocker, tmp_path):
    """トークンファイルなしの場合はOAuthフローが起動する"""
    from youtube_analytics import load_oauth_credentials
    mock_creds = mocker.MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = '{"token": "test_token"}'
    mock_flow = mocker.MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mocker.patch("youtube_analytics.InstalledAppFlow.from_client_secrets_file",
                 return_value=mock_flow)
    creds = load_oauth_credentials(
        token_file=str(tmp_path / "token.json"),
        client_secrets="dummy.json",
        scopes=["scope1"],
        token_file_exists=False,
    )
    assert creds == mock_creds
    mock_flow.run_local_server.assert_called_once_with(port=0)

def test_load_credentials_expired_with_refresh(mocker, tmp_path):
    """期限切れトークンはリフレッシュされる"""
    from youtube_analytics import load_oauth_credentials
    mock_creds = mocker.MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "rtoken"
    mock_creds.to_json.return_value = '{"token": "refreshed_token"}'
    mocker.patch("youtube_analytics.Credentials.from_authorized_user_file",
                 return_value=mock_creds)
    mocker.patch("youtube_analytics.Request")
    creds = load_oauth_credentials(
        token_file=str(tmp_path / "token.json"),
        client_secrets="dummy.json",
        scopes=["scope1"],
        token_file_exists=True,
    )
    mock_creds.refresh.assert_called_once()

def test_load_credentials_saves_token_after_auth(mocker, tmp_path):
    """新規認証後にトークンが保存される"""
    from youtube_analytics import load_oauth_credentials
    token_file = tmp_path / "token.json"
    mock_creds = mocker.MagicMock()
    mock_creds.valid = False
    mock_creds.expired = False
    mock_creds.refresh_token = None
    mock_creds.to_json.return_value = '{"token":"test"}'
    mock_flow = mocker.MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mocker.patch("youtube_analytics.Credentials.from_authorized_user_file",
                 return_value=mock_creds)
    mocker.patch("youtube_analytics.InstalledAppFlow.from_client_secrets_file",
                 return_value=mock_flow)
    load_oauth_credentials(
        token_file=str(token_file),
        client_secrets="dummy.json",
        scopes=["scope1"],
        token_file_exists=True,
    )
    assert token_file.exists()


# ── 実API統合テスト ─────────────────────────────────────────────────────

def test_real_credentials_are_valid(credentials):
    """実認証情報が有効であること"""
    assert credentials is not None
    assert credentials.valid

def test_real_youtube_data_client_connects(yt_client):
    """実YouTube Data APIクライアントが接続できること"""
    resp = yt_client.channels().list(part="id", mine=True).execute()
    assert "items" in resp or "pageInfo" in resp

def test_real_analytics_client_connects(analytics_client, my_channel_id, date_range):
    """実Analytics APIクライアントが接続できること"""
    start, end = date_range
    resp = analytics_client.reports().query(
        ids=f"channel=={my_channel_id}",
        startDate=start,
        endDate=end,
        metrics="views",
        dimensions="day",
    ).execute()
    assert "columnHeaders" in resp
