"""YouTube Reporting API テスト - 実APIを使った統合テスト"""
import pytest


# ── ユニットテスト ──────────────────────────────────────────────────────

def test_list_report_types_returns_list(mocker):
    """list_report_types はレポート種別リストを返す"""
    from youtube_analytics import list_report_types
    mock_client = mocker.MagicMock()
    mock_client.reportTypes.return_value.list.return_value.execute.return_value = {
        "reportTypes": [{"id": "channel_basic_a2", "name": "Channel Basic"}]
    }
    result = list_report_types(mock_client)
    assert result[0]["id"] == "channel_basic_a2"

def test_list_report_types_empty(mocker):
    """reportTypes キーがない場合は空リスト"""
    from youtube_analytics import list_report_types
    mock_client = mocker.MagicMock()
    mock_client.reportTypes.return_value.list.return_value.execute.return_value = {}
    result = list_report_types(mock_client)
    assert result == []

def test_list_jobs_returns_list(mocker):
    """list_reporting_jobs はジョブリストを返す"""
    from youtube_analytics import list_reporting_jobs
    mock_client = mocker.MagicMock()
    mock_client.jobs.return_value.list.return_value.execute.return_value = {
        "jobs": [{"id": "job1", "reportTypeId": "channel_basic_a2"}]
    }
    result = list_reporting_jobs(mock_client)
    assert result[0]["id"] == "job1"

def test_list_jobs_empty(mocker):
    """jobs キーがない場合は空リスト"""
    from youtube_analytics import list_reporting_jobs
    mock_client = mocker.MagicMock()
    mock_client.jobs.return_value.list.return_value.execute.return_value = {}
    result = list_reporting_jobs(mock_client)
    assert result == []

def test_create_reporting_job_sends_body(mocker):
    """create_reporting_job は正しいbodyを送信する"""
    from youtube_analytics import create_reporting_job
    mock_client = mocker.MagicMock()
    mock_client.jobs.return_value.create.return_value.execute.return_value = {
        "id": "newjob", "reportTypeId": "channel_basic_a2"
    }
    result = create_reporting_job(mock_client, "channel_basic_a2", "My Job")
    call_kwargs = mock_client.jobs.return_value.create.call_args[1]
    assert call_kwargs["body"]["reportTypeId"] == "channel_basic_a2"
    assert call_kwargs["body"]["name"] == "My Job"

def test_list_reports_for_job(mocker):
    """list_reports_for_job は指定ジョブのレポートリストを返す"""
    from youtube_analytics import list_reports_for_job
    mock_client = mocker.MagicMock()
    mock_client.jobs.return_value.reports.return_value.list.return_value.execute.return_value = {
        "reports": [{"id": "report1", "downloadUrl": "https://example.com/report"}]
    }
    result = list_reports_for_job(mock_client, "job1")
    assert result[0]["id"] == "report1"
    call_kwargs = mock_client.jobs.return_value.reports.return_value.list.call_args[1]
    assert call_kwargs["jobId"] == "job1"


# ── 実API統合テスト ─────────────────────────────────────────────────────

def test_real_list_report_types(reporting_client):
    """実APIでレポート種別一覧を取得できる"""
    from youtube_analytics import list_report_types
    result = list_report_types(reporting_client)
    assert isinstance(result, list)
    # Reporting APIは必ずいくつかのレポート種別を返す
    assert len(result) > 0
    for rt in result:
        assert "id" in rt
        assert "name" in rt

def test_real_list_report_types_contains_basic(reporting_client):
    """channel_basic_a2 などの基本レポートが存在する"""
    from youtube_analytics import list_report_types
    result = list_report_types(reporting_client)
    ids = [rt["id"] for rt in result]
    # 少なくとも何らかのチャンネルレポートが存在する
    channel_reports = [i for i in ids if i.startswith("channel")]
    assert len(channel_reports) > 0

def test_real_list_reporting_jobs(reporting_client):
    """実APIでジョブ一覧を取得できる（空でも可）"""
    from youtube_analytics import list_reporting_jobs
    result = list_reporting_jobs(reporting_client)
    assert isinstance(result, list)
    # ジョブがある場合の構造チェック
    for job in result:
        assert "id" in job
        assert "reportTypeId" in job
