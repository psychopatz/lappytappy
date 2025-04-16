import json
import os

SETTINGS_FILE = "settings.json"

default_settings = {
    "enabled": False,
    "idle_minutes": 30,
    "autostart": False,
    "close_behavior": "minimize" or "exit"

}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return default_settings.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return default_settings.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
