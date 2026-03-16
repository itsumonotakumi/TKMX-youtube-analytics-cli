"""設定レイヤーテスト - TOML/ENV/CLI 3層マージ"""
import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, '.')


# ── デフォルト値テスト ──────────────────────────────────────────────────

def test_config_defaults():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={})
    assert cfg["defaults"]["format"] == "json"
    assert cfg["defaults"]["days"] == 30
    assert cfg["defaults"]["max_results"] == 50
    assert cfg["defaults"]["output"] == "-"

def test_config_auth_defaults_are_none():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={})
    assert cfg["auth"]["api_key"] is None
    assert cfg["ads"]["customer_id"] is None
    assert cfg["ads"]["developer_token"] is None

def test_config_auth_paths_have_defaults():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={})
    assert ".youtube-cli" in cfg["auth"]["client_secrets"]
    assert ".youtube-cli" in cfg["auth"]["token_file"]


# ── TOML設定ファイルテスト ──────────────────────────────────────────────

def test_toml_api_key_loaded(tmp_path):
    from youtube_analytics import load_config
    (tmp_path / "config.toml").write_text('[auth]\napi_key = "test_key"\n')
    cfg = load_config(config_file=str(tmp_path / "config.toml"), env={}, cli_args={})
    assert cfg["auth"]["api_key"] == "test_key"

def test_toml_defaults_section(tmp_path):
    from youtube_analytics import load_config
    toml = '[defaults]\nformat = "csv"\ndays = 7\nmax_results = 10\n'
    (tmp_path / "config.toml").write_text(toml)
    cfg = load_config(config_file=str(tmp_path / "config.toml"), env={}, cli_args={})
    assert cfg["defaults"]["format"] == "csv"
    assert cfg["defaults"]["days"] == 7
    assert cfg["defaults"]["max_results"] == 10

def test_toml_ads_section(tmp_path):
    from youtube_analytics import load_config
    toml = '[ads]\ncustomer_id = "9876543210"\ndeveloper_token = "dev_tok"\n'
    (tmp_path / "config.toml").write_text(toml)
    cfg = load_config(config_file=str(tmp_path / "config.toml"), env={}, cli_args={})
    assert cfg["ads"]["customer_id"] == "9876543210"
    assert cfg["ads"]["developer_token"] == "dev_tok"

def test_nonexistent_config_file_uses_defaults():
    from youtube_analytics import load_config
    cfg = load_config(config_file="/nonexistent/path/config.toml", env={}, cli_args={})
    assert cfg["defaults"]["format"] == "json"


# ── 環境変数テスト ──────────────────────────────────────────────────────

def test_env_overrides_config(tmp_path):
    from youtube_analytics import load_config
    (tmp_path / "config.toml").write_text('[auth]\napi_key = "from_file"\n')
    cfg = load_config(
        config_file=str(tmp_path / "config.toml"),
        env={"YOUTUBE_API_KEY": "from_env"},
        cli_args={}
    )
    assert cfg["auth"]["api_key"] == "from_env"

def test_env_client_secrets():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={"YOUTUBE_CLIENT_SECRETS": "/custom/secrets.json"}, cli_args={})
    assert cfg["auth"]["client_secrets"] == "/custom/secrets.json"

def test_env_token_file():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={"YOUTUBE_TOKEN_FILE": "/custom/token.json"}, cli_args={})
    assert cfg["auth"]["token_file"] == "/custom/token.json"

def test_env_ads_customer_id():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={"GOOGLE_ADS_CUSTOMER_ID": "111"}, cli_args={})
    assert cfg["ads"]["customer_id"] == "111"

def test_env_days_parsed_as_int():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={"YT_DEFAULT_DAYS": "7"}, cli_args={})
    assert cfg["defaults"]["days"] == 7
    assert isinstance(cfg["defaults"]["days"], int)


# ── CLIフラグテスト ─────────────────────────────────────────────────────

def test_cli_overrides_env(tmp_path):
    from youtube_analytics import load_config
    cfg = load_config(
        config_file=None,
        env={"YOUTUBE_API_KEY": "from_env"},
        cli_args={"api_key": "from_cli"}
    )
    assert cfg["auth"]["api_key"] == "from_cli"

def test_cli_format_override():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={"format": "csv"})
    assert cfg["defaults"]["format"] == "csv"

def test_cli_max_results_override():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={"max_results": 100})
    assert cfg["defaults"]["max_results"] == 100

def test_cli_none_values_ignored():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={"api_key": None, "format": None})
    assert cfg["auth"]["api_key"] is None
    assert cfg["defaults"]["format"] == "json"  # デフォルト維持


# ── エラーテスト ────────────────────────────────────────────────────────

def test_missing_api_key_raises():
    from youtube_analytics import load_config, ConfigError
    with pytest.raises(ConfigError, match="api_key"):
        load_config(config_file=None, env={}, cli_args={}, require_api_key=True)

def test_api_key_from_env_satisfies_require():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={"YOUTUBE_API_KEY": "key"}, cli_args={}, require_api_key=True)
    assert cfg["auth"]["api_key"] == "key"

def test_api_key_from_cli_satisfies_require():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={"api_key": "key"}, require_api_key=True)
    assert cfg["auth"]["api_key"] == "key"


# ── deep_merge テスト ───────────────────────────────────────────────────

def test_deep_merge_preserves_unset_keys(tmp_path):
    from youtube_analytics import load_config
    # TOMLに一部だけ設定した場合、他はデフォルト維持
    (tmp_path / "config.toml").write_text('[auth]\napi_key = "key"\n')
    cfg = load_config(config_file=str(tmp_path / "config.toml"), env={}, cli_args={})
    assert cfg["auth"]["api_key"] == "key"
    assert cfg["defaults"]["format"] == "json"  # デフォルト維持
    assert cfg["defaults"]["days"] == 30  # デフォルト維持
