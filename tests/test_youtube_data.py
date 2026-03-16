"""YouTube Data API クライアントテスト - 実APIを使った統合テスト"""
import pytest


# ── ユニットテスト（モックなし・ロジックテスト）────────────────────────

def test_get_channel_info_uses_id_param(mocker):
    """channel_id 指定時は id パラメータで検索する"""
    from youtube_analytics import get_channel_info
    mock_resp = {"items": [{"id": "UCtest", "snippet": {}, "statistics": {},
                            "contentDetails": {"relatedPlaylists": {"uploads": "UUtest"}}}]}
    mock_yt = mocker.MagicMock()
    mock_yt.channels.return_value.list.return_value.execute.return_value = mock_resp
    get_channel_info(mock_yt, channel_id="UCtest")
    call_kwargs = mock_yt.channels.return_value.list.call_args[1]
    assert call_kwargs.get("id") == "UCtest"
    assert "mine" not in call_kwargs

def test_get_channel_info_mine_flag(mocker):
    """channel_id=None の場合は mine=True で検索する"""
    from youtube_analytics import get_channel_info
    mock_resp = {"items": [{"id": "UCmine", "snippet": {}, "statistics": {}}]}
    mock_yt = mocker.MagicMock()
    mock_yt.channels.return_value.list.return_value.execute.return_value = mock_resp
    get_channel_info(mock_yt, channel_id=None)
    call_kwargs = mock_yt.channels.return_value.list.call_args[1]
    assert call_kwargs.get("mine") is True

def test_get_channel_info_not_found_raises(mocker):
    """チャンネルが見つからない場合は ValueError"""
    from youtube_analytics import get_channel_info
    mock_yt = mocker.MagicMock()
    mock_yt.channels.return_value.list.return_value.execute.return_value = {"items": []}
    with pytest.raises(ValueError, match="チャンネルが見つかりません"):
        get_channel_info(mock_yt, channel_id="UCnotfound")

def test_list_videos_uses_uploads_playlist(mocker):
    """list_videos は uploads プレイリストを使う"""
    from youtube_analytics import list_videos
    channel_resp = {"items": [{"id": "UCtest", "snippet": {}, "statistics": {},
                               "contentDetails": {"relatedPlaylists": {"uploads": "UUtest123"}}}]}
    playlist_resp = {"items": [{"id": "vid1", "snippet": {"title": "V1"}}], "nextPageToken": None}
    mock_yt = mocker.MagicMock()
    mock_yt.channels.return_value.list.return_value.execute.return_value = channel_resp
    mock_yt.playlistItems.return_value.list.return_value.execute.return_value = playlist_resp
    list_videos(mock_yt, channel_id="UCtest", max_results=10, all_pages=False)
    call_kwargs = mock_yt.playlistItems.return_value.list.call_args[1]
    assert call_kwargs.get("playlistId") == "UUtest123"

def test_list_videos_respects_max_results(mocker):
    """list_videos は max_results を超えない"""
    from youtube_analytics import list_videos
    channel_resp = {"items": [{"id": "UCtest", "snippet": {}, "statistics": {},
                               "contentDetails": {"relatedPlaylists": {"uploads": "UUtest"}}}]}
    playlist_resp = {"items": [{"id": f"vid{i}"} for i in range(3)], "nextPageToken": None}
    mock_yt = mocker.MagicMock()
    mock_yt.channels.return_value.list.return_value.execute.return_value = channel_resp
    mock_yt.playlistItems.return_value.list.return_value.execute.return_value = playlist_resp
    videos = list_videos(mock_yt, channel_id="UCtest", max_results=5, all_pages=False)
    assert len(videos) <= 5

def test_search_videos_with_region(mocker):
    """search_videos は regionCode を渡す"""
    from youtube_analytics import search_videos
    mock_resp = {"items": [{"id": {"videoId": "vid1"}, "snippet": {}}], "nextPageToken": None}
    mock_yt = mocker.MagicMock()
    mock_yt.search.return_value.list.return_value.execute.return_value = mock_resp
    search_videos(mock_yt, query="test", region="JP")
    call_kwargs = mock_yt.search.return_value.list.call_args[1]
    assert call_kwargs.get("regionCode") == "JP"

def test_search_videos_without_region(mocker):
    """search_videos は region=None の場合 regionCode を渡さない"""
    from youtube_analytics import search_videos
    mock_resp = {"items": [], "nextPageToken": None}
    mock_yt = mocker.MagicMock()
    mock_yt.search.return_value.list.return_value.execute.return_value = mock_resp
    search_videos(mock_yt, query="test", region=None)
    call_kwargs = mock_yt.search.return_value.list.call_args[1]
    assert "regionCode" not in call_kwargs

def test_search_videos_max_results_capped_at_50(mocker):
    """YouTube Data API は max 50 per page"""
    from youtube_analytics import search_videos
    mock_resp = {"items": [], "nextPageToken": None}
    mock_yt = mocker.MagicMock()
    mock_yt.search.return_value.list.return_value.execute.return_value = mock_resp
    search_videos(mock_yt, query="test", max_results=200)
    call_kwargs = mock_yt.search.return_value.list.call_args[1]
    assert call_kwargs.get("maxResults") <= 50


# ── 実API統合テスト ─────────────────────────────────────────────────────

def test_real_get_channel_info_mine(yt_client):
    """実APIで自チャンネル情報を取得できる"""
    from youtube_analytics import get_channel_info
    result = get_channel_info(yt_client, channel_id=None)
    assert "id" in result
    assert result["id"].startswith("UC")
    assert "snippet" in result
    assert "statistics" in result

def test_real_channel_info_has_required_fields(yt_client):
    """取得したチャンネル情報に必須フィールドが存在する"""
    from youtube_analytics import get_channel_info
    result = get_channel_info(yt_client, channel_id=None)
    assert "title" in result["snippet"]
    assert "subscriberCount" in result["statistics"]
    assert "viewCount" in result["statistics"]
    assert "videoCount" in result["statistics"]

def test_real_list_videos_returns_items(yt_client, my_channel_id):
    """実APIで動画一覧を取得できる"""
    from youtube_analytics import list_videos
    videos = list_videos(yt_client, channel_id=my_channel_id, max_results=5, all_pages=False)
    assert isinstance(videos, list)
    # 動画がある場合はスニペット確認
    if videos:
        assert "id" in videos[0] or "snippet" in videos[0]

def test_real_list_videos_count_respects_max(yt_client, my_channel_id):
    """max_results を超えないことを実APIで確認"""
    from youtube_analytics import list_videos
    videos = list_videos(yt_client, channel_id=my_channel_id, max_results=3, all_pages=False)
    assert len(videos) <= 3

def test_real_search_videos_returns_results(yt_client):
    """実APIでYouTube検索ができる"""
    from youtube_analytics import search_videos
    results = search_videos(yt_client, query="Python プログラミング", region="JP", max_results=5)
    assert isinstance(results, list)
    assert len(results) > 0
    for item in results:
        assert "id" in item
        assert "snippet" in item
