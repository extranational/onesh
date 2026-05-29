import json

from onesh.config import DEFAULT_CONFIG, load_config, resolve_api_key


def test_creates_default_on_first_run(tmp_path):
    cfg = load_config(config_dir=tmp_path, load_env=False)
    path = tmp_path / "config.json"
    assert path.exists()
    assert json.loads(path.read_text()) == DEFAULT_CONFIG
    assert cfg.model == DEFAULT_CONFIG["model"]
    assert cfg.base_url == DEFAULT_CONFIG["base_url"]


def test_file_values_override_defaults(tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps({"model": "custom/model", "temperature": 0.9})
    )
    cfg = load_config(config_dir=tmp_path, load_env=False)
    assert cfg.model == "custom/model"
    assert cfg.temperature == 0.9
    # keys absent from the file fall back to defaults
    assert cfg.base_url == DEFAULT_CONFIG["base_url"]


def test_cli_overrides_win(tmp_path):
    cfg = load_config({"model": "cli/model"}, config_dir=tmp_path, load_env=False)
    assert cfg.model == "cli/model"


def test_cli_override_none_ignored(tmp_path):
    cfg = load_config({"model": None}, config_dir=tmp_path, load_env=False)
    assert cfg.model == DEFAULT_CONFIG["model"]


def test_resolve_api_key_from_env(tmp_path):
    cfg = load_config(config_dir=tmp_path, load_env=False)
    assert resolve_api_key(cfg, env={"OPENROUTER_API_KEY": "sk-xyz"}) == "sk-xyz"


def test_resolve_api_key_missing(tmp_path):
    cfg = load_config(config_dir=tmp_path, load_env=False)
    assert resolve_api_key(cfg, env={}) is None
