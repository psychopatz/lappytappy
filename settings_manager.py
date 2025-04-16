import json
import os

SETTINGS_FILE = "settings.json"

default_settings = {
    "enabled": False,
    "idle_minutes": 30,
    "autostart": False,
    "close_behavior": "minimize" or "exit",
    "action": "shutdown"

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

import os

SETTINGS_FILE = "settings.json"

def reset_settings():
    if os.path.exists(SETTINGS_FILE):
        os.remove(SETTINGS_FILE)

    # Also delete startup shortcut
    startup_path = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
    shortcut_path = os.path.join(startup_path, "LappyTappyUtils.lnk")
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
