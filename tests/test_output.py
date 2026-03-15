import json
import csv
import io
import pytest
from datetime import datetime, timezone

def test_format_json_output():
    from youtube_analytics import format_output
    data = {"channel": "UCtest", "views": 100}
    result = format_output(data, fmt="json", pretty=True, with_meta=True,
                           query_params={"channel": "UCtest"})
    parsed = json.loads(result)
    assert "meta" in parsed
    assert "data" in parsed
    assert parsed["data"]["views"] == 100

def test_format_ndjson_output():
    from youtube_analytics import format_output
    data = [{"date": "2026-03-01", "views": 100}, {"date": "2026-03-02", "views": 200}]
    result = format_output(data, fmt="ndjson")
    lines = result.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["views"] == 100

def test_format_csv_output():
    from youtube_analytics import format_output
    data = [{"date": "2026-03-01", "views": 100}, {"date": "2026-03-02", "views": 200}]
    result = format_output(data, fmt="csv")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert rows[0]["date"] == "2026-03-01"
    assert rows[1]["views"] == "200"

def test_generate_schema():
    from youtube_analytics import generate_schema
    schema = generate_schema()
    assert "channel_info" in schema
    assert "analytics" in schema
    assert "properties" in schema["analytics"]

def test_add_context():
    from youtube_analytics import add_field_context
    data = {"views": 100, "subscribersGained": 5}
    result = add_field_context(data)
    assert "_context" in result
    assert "views" in result["_context"]
