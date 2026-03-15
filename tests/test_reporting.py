import pytest

def test_list_report_types(mocker):
    from youtube_analytics import list_report_types
    mock_client = mocker.MagicMock()
    mock_client.reportTypes.return_value.list.return_value.execute.return_value = {
        "reportTypes": [
            {"id": "channel_basic_a2", "name": "Channel Basic"},
        ]
    }
    result = list_report_types(mock_client)
    assert result[0]["id"] == "channel_basic_a2"

def test_list_jobs(mocker):
    from youtube_analytics import list_reporting_jobs
    mock_client = mocker.MagicMock()
    mock_client.jobs.return_value.list.return_value.execute.return_value = {
        "jobs": [{"id": "job1", "reportTypeId": "channel_basic_a2"}]
    }
    result = list_reporting_jobs(mock_client)
    assert result[0]["id"] == "job1"
