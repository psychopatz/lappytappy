import os
import time
import psutil
from utils import get_idle_time, play_beep_warning
from settings_manager import load_settings

def perform_action(action):
    print(f"[LappyTappy] 🧾 Executing: {action}")
    if action == "shutdown":
        os.system("shutdown /s /t 0")
    elif action == "sleep":
        os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
    elif action == "hibernate":
        os.system("shutdown /h")
    elif action == "lock":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif action == "logout":
        os.system("shutdown /l")

def monitor_loop(idle_limit, should_continue, status_callback):
    settings = load_settings()
    action = settings.get("action", "shutdown")
    print(f"[LappyTappy] 🔁 Monitor loop started. Action: {action}, Idle: {idle_limit}s")

    warned = False

    while should_continue():
        idle = get_idle_time()
        battery = psutil.sensors_battery()
        on_battery = battery is not None and not battery.power_plugged

        print(f"[LappyTappy] ⏱ Idle: {int(idle)}s | On battery: {on_battery} | Threshold: {idle_limit}s")
        status_callback(idle, on_battery)

        if idle >= (idle_limit - 10) and on_battery and not warned:
            play_beep_warning()
            warned = True

        if idle >= idle_limit and on_battery:
            perform_action(action)
            break

        time.sleep(1)
