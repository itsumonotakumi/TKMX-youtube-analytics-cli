import pytest

def make_mock_yt(mocker, list_response: dict):
    """YouTube Data APIのモッククライアントを生成するヘルパー"""
    mock_client = mocker.MagicMock()
    mock_execute = mocker.MagicMock(return_value=list_response)
    mock_client.channels.return_value.list.return_value.execute = mock_execute
    mock_client.videos.return_value.list.return_value.execute = mock_execute
    mock_client.search.return_value.list.return_value.execute = mock_execute
    return mock_client

def test_get_channel_info(mocker):
    from youtube_analytics import get_channel_info
    mock_resp = {
        "items": [{
            "id": "UCtest",
            "snippet": {"title": "TestChannel", "description": "desc"},
            "statistics": {"subscriberCount": "1000", "videoCount": "50", "viewCount": "100000"},
        }]
    }
    mock_yt = make_mock_yt(mocker, mock_resp)
    result = get_channel_info(mock_yt, channel_id="UCtest")
    assert result["id"] == "UCtest"
    assert result["statistics"]["subscriberCount"] == "1000"

def test_get_channel_info_mine(mocker):
    from youtube_analytics import get_channel_info
    mock_resp = {"items": [{"id": "UCmine", "snippet": {}, "statistics": {}}]}
    mock_yt = make_mock_yt(mocker, mock_resp)
    result = get_channel_info(mock_yt, channel_id=None)
    # mine=True でリクエストされること
    call_kwargs = mock_yt.channels.return_value.list.call_args[1]
    assert call_kwargs.get("mine") is True

def test_list_videos(mocker):
    from youtube_analytics import list_videos
    # get_channel_info用レスポンス（contentDetailsが必要）
    channel_resp = {
        "items": [{
            "id": "UCtest",
            "snippet": {},
            "statistics": {},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUtest"}},
        }]
    }
    # playlistItems用レスポンス
    playlist_resp = {
        "items": [
            {"id": "vid1", "snippet": {"title": "Video 1", "publishedAt": "2026-01-01T00:00:00Z"}},
        ],
        "nextPageToken": None,
    }
    mock_client = mocker.MagicMock()
    mock_client.channels.return_value.list.return_value.execute.return_value = channel_resp
    mock_client.playlistItems.return_value.list.return_value.execute.return_value = playlist_resp
    videos = list_videos(mock_client, channel_id="UCtest", max_results=50, all_pages=False)
    assert len(videos) == 1
    assert videos[0]["id"] == "vid1"

def test_search_videos(mocker):
    from youtube_analytics import search_videos
    mock_resp = {
        "items": [{"id": {"videoId": "vid1"}, "snippet": {"title": "Result"}}],
        "nextPageToken": None,
    }
    mock_client = mocker.MagicMock()
    mock_client.search.return_value.list.return_value.execute.return_value = mock_resp
    results = search_videos(mock_client, query="test", region="JP", max_results=10)
    assert results[0]["id"]["videoId"] == "vid1"
