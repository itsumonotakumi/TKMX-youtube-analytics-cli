"""Google Ads API + ROI計算テスト"""
import pytest


# ── ROI計算ユニットテスト ───────────────────────────────────────────────

def test_calculate_roi_basic():
    """基本的なROI計算"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=10000.0, subscribers_gained=100, views=5000)
    assert result["cost_per_subscriber_yen"] == pytest.approx(100.0)
    assert result["cost_per_view_yen"] == pytest.approx(2.0)
    assert result["subscriber_per_cost_ratio"] == pytest.approx(0.01)

def test_calculate_roi_zero_subscribers():
    """登録者0の場合はNone"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=5000.0, subscribers_gained=0, views=1000)
    assert result["cost_per_subscriber_yen"] is None
    assert result["cost_per_view_yen"] == pytest.approx(5.0)

def test_calculate_roi_zero_views():
    """再生0の場合はNone"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=5000.0, subscribers_gained=10, views=0)
    assert result["cost_per_view_yen"] is None
    assert result["cost_per_subscriber_yen"] == pytest.approx(500.0)

def test_calculate_roi_zero_cost():
    """広告費0の場合はNone"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=0.0, subscribers_gained=10, views=1000)
    assert result["subscriber_per_cost_ratio"] is None

def test_calculate_roi_returns_all_keys():
    """ROI結果に全必須キーが含まれる"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=1000.0, subscribers_gained=5, views=100)
    required_keys = [
        "total_cost_yen", "subscribers_gained", "views",
        "cost_per_subscriber_yen", "cost_per_view_yen", "subscriber_per_cost_ratio"
    ]
    for key in required_keys:
        assert key in result

def test_calculate_roi_preserves_input_values():
    """入力値がそのまま結果に含まれる"""
    from youtube_analytics import calculate_roi
    result = calculate_roi(total_cost_yen=9999.0, subscribers_gained=42, views=7777)
    assert result["total_cost_yen"] == 9999.0
    assert result["subscribers_gained"] == 42
    assert result["views"] == 7777


# ── get_video_ad_spend ユニットテスト ───────────────────────────────────

def test_get_video_ad_spend_cost_conversion(mocker):
    """cost_micros → 円変換を確認"""
    from youtube_analytics import get_video_ad_spend
    mock_client = mocker.MagicMock()
    mock_row = mocker.MagicMock()
    mock_row.campaign.id = 1
    mock_row.campaign.name = "Test"
    mock_row.metrics.cost_micros = 2_500_000  # 2.5円
    mock_row.segments.date = "2026-03-01"
    mock_row.metrics.video_views = 100
    mock_row.metrics.impressions = 500
    mock_client.get_service.return_value.search.return_value = [mock_row]
    result = get_video_ad_spend(mock_client, customer_id="123", video_id=None,
                                start_date="2026-03-01", end_date="2026-03-16")
    assert result[0]["cost_yen"] == pytest.approx(2.5)

def test_get_video_ad_spend_with_video_filter(mocker):
    """video_id 指定時はクエリに AND video.id が含まれる"""
    from youtube_analytics import get_video_ad_spend
    mock_client = mocker.MagicMock()
    mock_client.get_service.return_value.search.return_value = []
    get_video_ad_spend(mock_client, customer_id="123", video_id="myvid",
                       start_date="2026-03-01", end_date="2026-03-16")
    call_kwargs = mock_client.get_service.return_value.search.call_args[1]
    assert "myvid" in call_kwargs["query"]

def test_get_video_ad_spend_customer_id_dashes_removed(mocker):
    """customer_id のダッシュが除去される"""
    from youtube_analytics import get_video_ad_spend
    mock_client = mocker.MagicMock()
    mock_client.get_service.return_value.search.return_value = []
    get_video_ad_spend(mock_client, customer_id="123-456-7890", video_id=None,
                       start_date="2026-03-01", end_date="2026-03-16")
    call_kwargs = mock_client.get_service.return_value.search.call_args[1]
    assert call_kwargs["customer_id"] == "1234567890"

def test_get_video_ad_spend_returns_all_fields(mocker):
    """結果の各行に必須フィールドが含まれる"""
    from youtube_analytics import get_video_ad_spend
    mock_client = mocker.MagicMock()
    mock_row = mocker.MagicMock()
    mock_row.campaign.id = 99
    mock_row.campaign.name = "Campaign"
    mock_row.metrics.cost_micros = 1_000_000
    mock_row.segments.date = "2026-03-01"
    mock_row.metrics.video_views = 200
    mock_row.metrics.impressions = 1000
    mock_client.get_service.return_value.search.return_value = [mock_row]
    result = get_video_ad_spend(mock_client, customer_id="123", video_id=None,
                                start_date="2026-03-01", end_date="2026-03-16")
    assert len(result) == 1
    row = result[0]
    for key in ["campaign_id", "campaign_name", "date", "cost_yen", "video_views", "impressions"]:
        assert key in row
