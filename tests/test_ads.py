import pytest

def test_get_video_ad_spend(mocker):
    from youtube_analytics import get_video_ad_spend
    mock_client = mocker.MagicMock()
    mock_row = mocker.MagicMock()
    mock_row.campaign.id = 1
    mock_row.campaign.name = "TestCampaign"
    mock_row.metrics.cost_micros = 1_000_000  # 1円
    mock_row.segments.date = "2026-03-01"
    mock_row.metrics.video_views = 100
    mock_row.metrics.impressions = 500
    mock_client.get_service.return_value.search.return_value = [mock_row]

    result = get_video_ad_spend(
        mock_client,
        customer_id="1234567890",
        video_id="vid1",
        start_date="2026-03-01",
        end_date="2026-03-16",
    )
    assert result[0]["cost_yen"] == pytest.approx(1.0)

def test_calculate_roi():
    from youtube_analytics import calculate_roi
    result = calculate_roi(
        total_cost_yen=10000.0,
        subscribers_gained=100,
        views=5000,
    )
    assert result["cost_per_subscriber_yen"] == pytest.approx(100.0)
    assert result["cost_per_view_yen"] == pytest.approx(2.0)
    assert result["subscriber_per_cost_ratio"] == pytest.approx(0.01)
