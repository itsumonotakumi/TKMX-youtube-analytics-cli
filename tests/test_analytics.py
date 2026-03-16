"""YouTube Analytics API テスト - 実APIを使った統合テスト"""
import pytest
from datetime import date, timedelta


# ── ユニットテスト（ロジック）───────────────────────────────────────────

def test_get_video_analytics_default_metrics(mocker):
    """metrics 未指定時はデフォルト指標セットを使う"""
    from youtube_analytics import get_video_analytics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [], "rows": []
    }
    get_video_analytics(mock_client, channel_id="UCtest",
                        start_date="2026-03-01", end_date="2026-03-16")
    call_kwargs = mock_client.reports.return_value.query.call_args[1]
    metrics = call_kwargs["metrics"]
    assert "views" in metrics
    assert "subscribersGained" in metrics
    assert "estimatedMinutesWatched" in metrics

def test_get_video_analytics_video_filter(mocker):
    """video_id 指定時は filters パラメータに含まれる"""
    from youtube_analytics import get_video_analytics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [], "rows": []
    }
    get_video_analytics(mock_client, channel_id="UCtest",
                        start_date="2026-03-01", end_date="2026-03-16",
                        video_id="vid123")
    call_kwargs = mock_client.reports.return_value.query.call_args[1]
    assert "filters" in call_kwargs
    assert "vid123" in call_kwargs["filters"]

def test_get_video_analytics_no_video_filter(mocker):
    """video_id=None の場合は filters パラメータなし"""
    from youtube_analytics import get_video_analytics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [], "rows": []
    }
    get_video_analytics(mock_client, channel_id="UCtest",
                        start_date="2026-03-01", end_date="2026-03-16",
                        video_id=None)
    call_kwargs = mock_client.reports.return_value.query.call_args[1]
    assert "filters" not in call_kwargs

def test_get_demographics_dimensions(mocker):
    """demographics は ageGroup,gender ディメンションを使う"""
    from youtube_analytics import get_demographics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [], "rows": []
    }
    get_demographics(mock_client, channel_id="UCtest",
                     start_date="2026-03-01", end_date="2026-03-16")
    call_kwargs = mock_client.reports.return_value.query.call_args[1]
    assert "ageGroup" in call_kwargs["dimensions"]
    assert "gender" in call_kwargs["dimensions"]

def test_analytics_response_to_records_basic():
    """基本的なレスポンス変換"""
    from youtube_analytics import analytics_response_to_records
    response = {
        "columnHeaders": [{"name": "day"}, {"name": "views"}],
        "rows": [["2026-03-01", 100], ["2026-03-02", 200]],
    }
    records = analytics_response_to_records(response)
    assert len(records) == 2
    assert records[0] == {"day": "2026-03-01", "views": 100}
    assert records[1]["views"] == 200

def test_analytics_response_to_records_empty():
    """空のレスポンスを空リストに変換"""
    from youtube_analytics import analytics_response_to_records
    response = {"columnHeaders": [{"name": "day"}], "rows": []}
    records = analytics_response_to_records(response)
    assert records == []

def test_analytics_response_to_records_no_rows_key():
    """rows キーがない場合も空リストを返す"""
    from youtube_analytics import analytics_response_to_records
    response = {"columnHeaders": [{"name": "day"}]}
    records = analytics_response_to_records(response)
    assert records == []

def test_analytics_response_multi_columns():
    """複数カラムのレスポンス変換"""
    from youtube_analytics import analytics_response_to_records
    response = {
        "columnHeaders": [
            {"name": "day"}, {"name": "views"},
            {"name": "estimatedMinutesWatched"}, {"name": "subscribersGained"}
        ],
        "rows": [["2026-03-01", 100, 500, 10]],
    }
    records = analytics_response_to_records(response)
    assert records[0]["day"] == "2026-03-01"
    assert records[0]["estimatedMinutesWatched"] == 500
    assert records[0]["subscribersGained"] == 10


# ── 実API統合テスト ─────────────────────────────────────────────────────

def test_real_get_video_analytics(analytics_client, my_channel_id, date_range):
    """実APIでチャンネルのAnalyticsデータを取得できる"""
    from youtube_analytics import get_video_analytics
    start, end = date_range
    resp = get_video_analytics(analytics_client, channel_id=my_channel_id,
                               start_date=start, end_date=end)
    assert "columnHeaders" in resp
    assert "rows" in resp
    headers = [h["name"] for h in resp["columnHeaders"]]
    assert "day" in headers
    assert "views" in headers

def test_real_analytics_to_records_structure(analytics_client, my_channel_id, date_range):
    """実APIレスポンスをレコードに変換できる"""
    from youtube_analytics import get_video_analytics, analytics_response_to_records
    start, end = date_range
    resp = get_video_analytics(analytics_client, channel_id=my_channel_id,
                               start_date=start, end_date=end)
    records = analytics_response_to_records(resp)
    assert isinstance(records, list)
    if records:
        assert "day" in records[0]
        assert "views" in records[0]

def test_real_get_demographics(analytics_client, my_channel_id, date_range):
    """実APIで視聴者属性データを取得できる"""
    from youtube_analytics import get_demographics
    start, end = date_range
    resp = get_demographics(analytics_client, channel_id=my_channel_id,
                            start_date=start, end_date=end)
    assert "columnHeaders" in resp
    headers = [h["name"] for h in resp["columnHeaders"]]
    assert "viewerPercentage" in headers

def test_real_get_traffic_sources(analytics_client, my_channel_id, date_range):
    """実APIでトラフィックソースデータを取得できる"""
    from youtube_analytics import get_traffic_sources
    start, end = date_range
    resp = get_traffic_sources(analytics_client, channel_id=my_channel_id,
                               start_date=start, end_date=end)
    assert "columnHeaders" in resp
    headers = [h["name"] for h in resp["columnHeaders"]]
    assert "insightTrafficSourceType" in headers
