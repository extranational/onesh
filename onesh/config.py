import dataclasses
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_CONFIG = {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY",
    "model": "qwen/qwen3.8-max-0902",
    "image_model": "deepseek/deepseek-v4-flash-vision-exp",
    "system_prompt": (
        "You are a concise terminal assistant. Answer directly and briefly. "
        "When asked for a command, give the command first, then at most one "
        "short line of explanation."
    ),
    "temperature": 0.2,
    "list_limit": 20,
}


@dataclass
class Config:
    base_url: str
    api_key_env: str
    model: str
    image_model: str
    system_prompt: str
    temperature: float
    list_limit: int
    http_referer: str | None = None
    x_title: str | None = None


def default_config_dir():
    return Path.home() / ".config" / "onesh"


def load_config(cli_overrides=None, *, config_dir=None, load_env=True):
    config_dir = Path(config_dir) if config_dir else default_config_dir()
    path = config_dir / "config.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        data = dict(DEFAULT_CONFIG)

    merged = {**DEFAULT_CONFIG, **data}
    for key, value in (cli_overrides or {}).items():
        if value is not None:
            merged[key] = value

    if load_env:
        load_dotenv()

    fields = {f.name for f in dataclasses.fields(Config)}
    return Config(**{k: merged[k] for k in fields if k in merged})


def resolve_api_key(config, env=None):
    env = os.environ if env is None else env
    return env.get(config.api_key_env)
