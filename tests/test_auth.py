import pytest

def test_build_youtube_data_client_with_api_key(mocker):
    mocker.patch("youtube_analytics.build")
    from youtube_analytics import build_youtube_data_client
    client = build_youtube_data_client(api_key="test_key")
    import youtube_analytics as ya
    ya.build.assert_called_once_with(
        "youtube", "v3", developerKey="test_key"
    )

def test_build_analytics_client_requires_credentials(mocker):
    mocker.patch("youtube_analytics.build")
    mock_creds = mocker.MagicMock()
    from youtube_analytics import build_analytics_client
    build_analytics_client(credentials=mock_creds)
    import youtube_analytics as ya
    ya.build.assert_called_once_with(
        "youtubeAnalytics", "v2", credentials=mock_creds
    )

def test_load_credentials_from_file(mocker, tmp_path):
    from youtube_analytics import load_oauth_credentials
    token_file = tmp_path / "token.json"
    mock_creds = mocker.MagicMock()
    mock_creds.valid = True
    mocker.patch("youtube_analytics.Credentials.from_authorized_user_file",
                 return_value=mock_creds)
    creds = load_oauth_credentials(
        token_file=str(token_file),
        client_secrets="dummy.json",
        scopes=["scope1"],
        token_file_exists=True,
    )
    assert creds == mock_creds
