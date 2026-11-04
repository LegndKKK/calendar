"""模型接口配置的读写。"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "",
    "model": "deepseek-chat",
}


def load_config(path: Path) -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return config
    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            value = data.get(key)
            if isinstance(value, str):
                config[key] = value
    return config


def save_config(path: Path, patch: dict) -> dict:
    config = load_config(path)

    if "base_url" in patch:
        config["base_url"] = str(patch["base_url"] or "").strip().rstrip("/")
    if "model" in patch:
        config["model"] = str(patch["model"] or "").strip()
    if patch.get("clear_key"):
        config["api_key"] = ""
    elif patch.get("api_key"):
        config["api_key"] = str(patch["api_key"]).strip()

    if not config["base_url"].startswith(("http://", "https://")):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
    if not config["model"]:
        raise ValueError("模型名不能为空")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return config


def public_config(config: dict) -> dict:
    key = config.get("api_key") or ""
    return {
        "base_url": config.get("base_url", ""),
        "model": config.get("model", ""),
        "has_key": bool(key),
        "key_hint": f"••••{key[-4:]}" if len(key) >= 4 else ("已保存" if key else ""),
    }
