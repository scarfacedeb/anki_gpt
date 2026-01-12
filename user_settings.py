import json
import os
from typing import Dict, Any
from dataclasses import dataclass

SETTINGS_FILE = "user_settings.json"

ALLOWED_MODELS = [
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-5",
    "gpt-5.2",
    "gpt-4o",
    "gpt-4o-mini"
]

ALLOWED_EFFORTS = ["minimal", "low", "medium", "high"]

@dataclass
class UserConfig:
    model: str = "gpt-5-nano"
    effort: str = "minimal"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        model = data.get("model", "gpt-5-nano")
        effort = data.get("effort", "minimal")

        if model not in ALLOWED_MODELS:
            model = "gpt-5-nano"
        if effort not in ALLOWED_EFFORTS:
            effort = "minimal"

        return cls(model=model, effort=effort)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "effort": self.effort
        }

_user_config_cache: Dict[int, UserConfig] = {}

def load_user_settings() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(SETTINGS_FILE):
        return {}

    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_user_settings(settings: Dict[str, Dict[str, Any]]) -> None:
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_user_config(user_id: int) -> UserConfig:
    if user_id in _user_config_cache:
        return _user_config_cache[user_id]

    settings = load_user_settings()
    user_settings = settings.get(str(user_id), {})
    config = UserConfig.from_dict(user_settings)
    _user_config_cache[user_id] = config
    return config

def set_user_config(user_id: int, config: UserConfig) -> None:
    _user_config_cache[user_id] = config
    settings = load_user_settings()
    settings[str(user_id)] = config.to_dict()
    save_user_settings(settings)

def get_user_setting(user_id: int, key: str, default: Any = None) -> Any:
    settings = load_user_settings()
    user_settings = settings.get(str(user_id), {})
    return user_settings.get(key, default)

def set_user_setting(user_id: int, key: str, value: Any) -> bool:
    if key == "model" and value not in ALLOWED_MODELS:
        return False
    if key == "effort" and value not in ALLOWED_EFFORTS:
        return False

    settings = load_user_settings()
    user_id_str = str(user_id)

    if user_id_str not in settings:
        settings[user_id_str] = {}

    settings[user_id_str][key] = value
    save_user_settings(settings)

    if user_id in _user_config_cache:
        del _user_config_cache[user_id]

    return True

def set_user_model(user_id: int, model: str) -> bool:
    return set_user_setting(user_id, "model", model)

def set_user_effort(user_id: int, effort: str) -> bool:
    return set_user_setting(user_id, "effort", effort)