import os
import sys
import pytest

sys.path.insert(0, '.')

def test_config_defaults():
    from youtube_analytics import load_config
    cfg = load_config(config_file=None, env={}, cli_args={})
    assert cfg["defaults"]["format"] == "json"
    assert cfg["defaults"]["days"] == 30
    assert cfg["defaults"]["max_results"] == 50

def test_env_overrides_config(tmp_path):
    from youtube_analytics import load_config
    toml_content = '[auth]\napi_key = "from_file"\n'
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml_content)
    cfg = load_config(
        config_file=str(config_file),
        env={"YOUTUBE_API_KEY": "from_env"},
        cli_args={}
    )
    assert cfg["auth"]["api_key"] == "from_env"

def test_cli_overrides_env(tmp_path):
    from youtube_analytics import load_config
    cfg = load_config(
        config_file=None,
        env={"YOUTUBE_API_KEY": "from_env"},
        cli_args={"api_key": "from_cli"}
    )
    assert cfg["auth"]["api_key"] == "from_cli"

def test_missing_api_key_raises():
    from youtube_analytics import load_config, ConfigError
    with pytest.raises(ConfigError, match="api_key"):
        load_config(config_file=None, env={}, cli_args={}, require_api_key=True)
