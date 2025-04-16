import os
import time
import psutil
from utils import get_idle_time, play_beep_warning 

def shutdown():
    print("[LappyTappy] ✅ Shutdown triggered!")
    os.system("shutdown /s /t 0")

def monitor_loop(idle_limit, should_continue, status_callback):
    print(f"[LappyTappy] 🔁 Monitor loop started. Waiting for {idle_limit}s of idle.")
    warned = False

    while should_continue():
        idle = get_idle_time()
        battery = psutil.sensors_battery()
        on_battery = battery is not None and not battery.power_plugged

        print(f"[LappyTappy] ⏱ Idle: {int(idle)}s | On battery: {on_battery} | Threshold: {idle_limit}s")
        status_callback(idle, on_battery)

        # ⚠ Warn at 10 seconds before shutdown
        if idle >= (idle_limit - 10) and on_battery and not warned:
            print("[LappyTappy] ⚠️ Beep warning: 10 seconds to shutdown.")
            play_beep_warning()
            warned = True

        if idle >= idle_limit and on_battery:
            print("[LappyTappy] 🚨 Conditions met: shutting down now...")
            shutdown()
            break

        time.sleep(1)
