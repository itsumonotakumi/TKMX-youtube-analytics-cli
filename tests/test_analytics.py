import pytest
from datetime import date, timedelta

def test_get_video_analytics(mocker):
    from youtube_analytics import get_video_analytics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [
            {"name": "day"}, {"name": "views"}, {"name": "estimatedMinutesWatched"},
            {"name": "subscribersGained"},
        ],
        "rows": [["2026-03-01", 100, 500, 10]],
    }
    result = get_video_analytics(
        mock_client,
        channel_id="UCtest",
        video_id="vid1",
        start_date="2026-03-01",
        end_date="2026-03-16",
        metrics=["views", "estimatedMinutesWatched", "subscribersGained"],
    )
    assert result["rows"][0][1] == 100

def test_get_demographics(mocker):
    from youtube_analytics import get_demographics
    mock_client = mocker.MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [{"name": "ageGroup"}, {"name": "gender"}, {"name": "viewerPercentage"}],
        "rows": [["age25-34", "male", 35.5]],
    }
    result = get_demographics(mock_client, channel_id="UCtest",
                              start_date="2026-03-01", end_date="2026-03-16")
    assert result["rows"][0][2] == 35.5

def test_analytics_to_records():
    from youtube_analytics import analytics_response_to_records
    response = {
        "columnHeaders": [{"name": "day"}, {"name": "views"}],
        "rows": [["2026-03-01", 100], ["2026-03-02", 200]],
    }
    records = analytics_response_to_records(response)
    assert records[0] == {"day": "2026-03-01", "views": 100}
    assert records[1]["views"] == 200
