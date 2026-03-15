import subprocess
import sys
import pytest

def run_cli(*args):
    return subprocess.run(
        [sys.executable, "youtube_analytics.py", *args],
        capture_output=True,
        text=True,
    )

def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "YOUTUBE_API_KEY" in result.stdout

def test_schema_exits_zero():
    result = run_cli("--schema")
    assert result.returncode == 0
    import json
    schema = json.loads(result.stdout)
    assert "analytics" in schema

def test_dry_run_no_api_call():
    result = run_cli(
        "--channel", "UCtest",
        "--channel-info",
        "--dry-run",
    )
    # dry-run はAPIキー不要でリクエスト内容を表示して終了
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout

def test_missing_required_args_exits_nonzero():
    result = run_cli("--analytics")  # チャンネルIDなし・認証なし
    assert result.returncode != 0
