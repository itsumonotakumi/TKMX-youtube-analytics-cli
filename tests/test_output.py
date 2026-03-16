"""出力レイヤーテスト - JSON/NDJSON/CSV + AI機能"""
import json
import csv
import io
import pytest
from datetime import datetime, timezone


# ── JSON出力テスト ──────────────────────────────────────────────────────

def test_format_json_with_meta():
    from youtube_analytics import format_output
    data = {"channel": "UCtest", "views": 100}
    result = format_output(data, fmt="json", pretty=True, with_meta=True,
                           query_params={"channel": "UCtest"})
    parsed = json.loads(result)
    assert "meta" in parsed
    assert "data" in parsed
    assert parsed["data"]["views"] == 100

def test_format_json_without_meta():
    from youtube_analytics import format_output
    data = {"views": 100}
    result = format_output(data, fmt="json", with_meta=False)
    parsed = json.loads(result)
    assert "meta" not in parsed
    assert parsed["views"] == 100

def test_format_json_pretty_indented():
    from youtube_analytics import format_output
    data = {"a": 1}
    result = format_output(data, fmt="json", pretty=True, with_meta=False)
    assert "\n" in result  # インデントあり

def test_format_json_not_pretty_compact():
    from youtube_analytics import format_output
    data = {"a": 1}
    result = format_output(data, fmt="json", pretty=False, with_meta=False)
    assert "\n" not in result  # 1行

def test_format_json_meta_has_generated_at():
    from youtube_analytics import format_output
    result = format_output({"k": "v"}, fmt="json", with_meta=True)
    parsed = json.loads(result)
    assert "generated_at" in parsed["meta"]

def test_format_json_meta_has_query_params():
    from youtube_analytics import format_output
    qp = {"channel": "UCtest", "start_date": "2026-01-01"}
    result = format_output({}, fmt="json", with_meta=True, query_params=qp)
    parsed = json.loads(result)
    assert parsed["meta"]["query"] == qp

def test_format_json_prompt_hint_added():
    from youtube_analytics import format_output
    result = format_output({}, fmt="json", with_meta=True, prompt_hint=True)
    parsed = json.loads(result)
    assert "llm_usage_hint" in parsed["meta"]

def test_format_json_no_prompt_hint_by_default():
    from youtube_analytics import format_output
    result = format_output({}, fmt="json", with_meta=True, prompt_hint=False)
    parsed = json.loads(result)
    assert "llm_usage_hint" not in parsed["meta"]

def test_format_json_ensure_ascii_false():
    """日本語文字がエスケープされないこと"""
    from youtube_analytics import format_output
    data = {"title": "テスト動画"}
    result = format_output(data, fmt="json", with_meta=False)
    assert "テスト動画" in result  # \u エスケープなし


# ── NDJSON出力テスト ────────────────────────────────────────────────────

def test_format_ndjson_list():
    from youtube_analytics import format_output
    data = [{"date": "2026-03-01", "views": 100}, {"date": "2026-03-02", "views": 200}]
    result = format_output(data, fmt="ndjson")
    lines = result.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["views"] == 100
    assert json.loads(lines[1])["views"] == 200

def test_format_ndjson_single_dict():
    """dict を渡した場合は1行"""
    from youtube_analytics import format_output
    data = {"views": 100}
    result = format_output(data, fmt="ndjson")
    lines = result.strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0])["views"] == 100

def test_format_ndjson_each_line_valid_json():
    from youtube_analytics import format_output
    data = [{"a": i} for i in range(5)]
    result = format_output(data, fmt="ndjson")
    for line in result.strip().split("\n"):
        json.loads(line)  # 各行がvalid JSON


# ── CSV出力テスト ───────────────────────────────────────────────────────

def test_format_csv_basic():
    from youtube_analytics import format_output
    data = [{"date": "2026-03-01", "views": 100}, {"date": "2026-03-02", "views": 200}]
    result = format_output(data, fmt="csv")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert rows[0]["date"] == "2026-03-01"
    assert rows[1]["views"] == "200"

def test_format_csv_has_header():
    from youtube_analytics import format_output
    data = [{"col1": "v1", "col2": "v2"}]
    result = format_output(data, fmt="csv")
    lines = result.strip().split("\n")
    assert "col1" in lines[0]
    assert "col2" in lines[0]

def test_format_csv_empty_list():
    from youtube_analytics import format_output
    result = format_output([], fmt="csv")
    assert result == ""

def test_format_csv_multiple_rows():
    from youtube_analytics import format_output
    data = [{"a": i, "b": i*2} for i in range(10)]
    result = format_output(data, fmt="csv")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 10


# ── スキーマテスト ──────────────────────────────────────────────────────

def test_generate_schema_has_sections():
    from youtube_analytics import generate_schema
    schema = generate_schema()
    assert "channel_info" in schema
    assert "analytics" in schema
    assert "roi" in schema

def test_generate_schema_analytics_properties():
    from youtube_analytics import generate_schema
    schema = generate_schema()
    props = schema["analytics"]["properties"]
    assert "views" in props
    assert "subscribersGained" in props
    assert "estimatedMinutesWatched" in props

def test_generate_schema_channel_info_properties():
    from youtube_analytics import generate_schema
    schema = generate_schema()
    props = schema["channel_info"]["properties"]
    assert "id" in props
    assert "statistics.subscriberCount" in props

def test_generate_schema_each_section_has_description():
    from youtube_analytics import generate_schema
    schema = generate_schema()
    for section in schema.values():
        assert "description" in section


# ── フィールドコンテキストテスト ────────────────────────────────────────

def test_add_context_known_fields():
    from youtube_analytics import add_field_context
    data = {"views": 100, "subscribersGained": 5}
    result = add_field_context(data)
    assert "_context" in result
    assert "views" in result["_context"]
    assert "subscribersGained" in result["_context"]

def test_add_context_unknown_fields_ignored():
    from youtube_analytics import add_field_context
    data = {"unknownField": 999}
    result = add_field_context(data)
    assert "_context" not in result  # コンテキストなし（未知フィールドのみ）

def test_add_context_preserves_original_data():
    from youtube_analytics import add_field_context
    data = {"views": 100}
    result = add_field_context(data)
    assert result["views"] == 100

def test_format_output_with_context_adds_context():
    from youtube_analytics import format_output
    data = {"views": 50}
    result = format_output(data, fmt="json", with_meta=False, with_context=True)
    parsed = json.loads(result)
    assert "_context" in parsed


# ── 不正フォーマットテスト ──────────────────────────────────────────────

def test_format_output_invalid_format_raises():
    from youtube_analytics import format_output
    with pytest.raises(ValueError, match="未対応のフォーマット"):
        format_output({}, fmt="xml")


# ── write_output テスト ─────────────────────────────────────────────────

def test_write_output_to_file(tmp_path):
    from youtube_analytics import write_output
    out_file = tmp_path / "output.json"
    write_output('{"test": 1}', str(out_file))
    assert out_file.exists()
    assert out_file.read_text() == '{"test": 1}'

def test_write_output_to_stdout(capsys):
    from youtube_analytics import write_output
    write_output("hello world", "-")
    captured = capsys.readouterr()
    assert "hello world" in captured.out

def test_write_output_adds_newline_if_missing(capsys):
    from youtube_analytics import write_output
    write_output("no newline", "-")
    captured = capsys.readouterr()
    assert captured.out.endswith("\n")
