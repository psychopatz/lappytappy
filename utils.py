import ctypes
import threading
import time
from win10toast import ToastNotifier

_notifier = ToastNotifier()

def get_idle_time():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0

def show_notification(title, message, duration=5):
    def safe_toast():
        try:
            # Small delay ensures Windows UI thread is ready
            time.sleep(0.1)
            _notifier.show_toast(title, message, duration=duration, threaded=False)
        except Exception as e:
            print(f"[LappyTappy] ⚠️ Toast error: {e}")

    threading.Thread(target=safe_toast, daemon=True).start()
