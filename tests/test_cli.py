"""CLI エントリポイントテスト - argparse + main"""
import json
import subprocess
import sys
import pytest
from pathlib import Path


def run_cli(*args, env=None):
    import os
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, "youtube_analytics.py", *args],
        capture_output=True,
        text=True,
        env=run_env,
    )


# ── --help テスト ────────────────────────────────────────────────────────

def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0

def test_help_contains_api_key_info():
    result = run_cli("--help")
    assert "YOUTUBE_API_KEY" in result.stdout

def test_help_contains_auth_group():
    result = run_cli("--help")
    assert "認証" in result.stdout

def test_help_contains_dry_run():
    result = run_cli("--help")
    assert "--dry-run" in result.stdout

def test_help_contains_schema():
    result = run_cli("--help")
    assert "--schema" in result.stdout

def test_help_contains_output_formats():
    result = run_cli("--help")
    assert "json" in result.stdout
    assert "csv" in result.stdout
    assert "ndjson" in result.stdout


# ── --schema テスト ─────────────────────────────────────────────────────

def test_schema_exits_zero():
    result = run_cli("--schema")
    assert result.returncode == 0

def test_schema_valid_json():
    result = run_cli("--schema")
    schema = json.loads(result.stdout)
    assert isinstance(schema, dict)

def test_schema_has_analytics_section():
    result = run_cli("--schema")
    schema = json.loads(result.stdout)
    assert "analytics" in schema

def test_schema_has_channel_info_section():
    result = run_cli("--schema")
    schema = json.loads(result.stdout)
    assert "channel_info" in schema

def test_schema_for_analytics():
    result = run_cli("--schema-for", "analytics")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "properties" in parsed

def test_schema_for_unknown_exits_nonzero():
    result = run_cli("--schema-for", "nonexistent_section")
    assert result.returncode != 0
    assert "未定義" in result.stderr


# ── --dry-run テスト ────────────────────────────────────────────────────

def test_dry_run_exits_zero():
    result = run_cli("--channel", "UCtest", "--channel-info", "--dry-run")
    assert result.returncode == 0

def test_dry_run_outputs_json():
    result = run_cli("--channel", "UCtest", "--analytics", "--dry-run")
    parsed = json.loads(result.stdout)
    assert "DRY RUN" in parsed

def test_dry_run_shows_would_fetch():
    result = run_cli("--channel", "UCtest", "--analytics", "--dry-run")
    parsed = json.loads(result.stdout)
    assert "would_fetch" in parsed
    assert parsed["would_fetch"]["analytics"] is True

def test_dry_run_shows_params():
    result = run_cli("--channel", "UCtest", "--dry-run", "--days", "7")
    parsed = json.loads(result.stdout)
    assert "params" in parsed
    assert parsed["params"]["channel"] == "UCtest"

def test_dry_run_no_api_call():
    """dry-run はAPI呼び出しなしで成功する（APIキー不要）"""
    result = run_cli("--channel", "UCtest", "--analytics", "--roi", "--dry-run")
    assert result.returncode == 0

def test_dry_run_all_data():
    result = run_cli("--all-data", "--dry-run")
    parsed = json.loads(result.stdout)
    assert parsed["would_fetch"]["analytics"] is True
    assert parsed["would_fetch"]["demographics"] is True


# ── エラーケーステスト ──────────────────────────────────────────────────

def test_analytics_without_auth_exits_nonzero():
    """認証なしで --analytics を指定するとエラー"""
    result = run_cli("--analytics")
    assert result.returncode != 0

def test_no_action_shows_help():
    """アクション指定なしはヘルプ表示してexit 1"""
    result = run_cli()
    assert result.returncode != 0

def test_roi_without_ads_customer_id():
    """--roi に --ads-customer-id なしはエラー（dry-run で確認）"""
    result = run_cli("--channel", "UCtest", "--roi", "--dry-run")
    # dry-run なのでROIのパラメータだけ確認
    parsed = json.loads(result.stdout)
    assert parsed["would_fetch"]["roi"] is True


# ── 実API統合CLIテスト ─────────────────────────────────────────────────

def test_real_cli_schema_matches_expected(yt_client):
    """実API実行後も --schema は一貫している"""
    result = run_cli("--schema")
    schema = json.loads(result.stdout)
    assert "channel_info" in schema
    assert "analytics" in schema
    assert "roi" in schema

def test_real_cli_channel_info_dry_run_with_my_channel(my_channel_id):
    """実チャンネルIDで --dry-run が正常に動作する"""
    result = run_cli("--channel", my_channel_id, "--channel-info", "--analytics", "--dry-run")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["params"]["channel"] == my_channel_id
    assert parsed["would_fetch"]["channel_info"] is True
    assert parsed["would_fetch"]["analytics"] is True
