import customtkinter as ctk
import psutil
import threading
import time
import os
import sys
import pystray
from PIL import Image, ImageDraw, ImageFont
from tkinter import messagebox, Toplevel, BooleanVar, Checkbutton, Button, Label
from win32com.client import Dispatch

from monitor import monitor_loop
from utils import get_idle_time
from settings_manager import load_settings, save_settings


class LappyTappyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LappyTappy Utils")
        self.geometry("400x330")
        self.resizable(False, False)

        self.settings = load_settings()
        self.monitoring = False
        self.tray_icon = None
        self.idle_limit = self.settings["idle_minutes"] * 60
        self.close_behavior = self.settings.get("close_behavior", None)

        # Tkinter variables
        self.enabled = ctk.BooleanVar(value=self.settings["enabled"])
        self.idle_limit_var = ctk.StringVar(value=str(self.settings["idle_minutes"]))
        self.autostart_var = ctk.BooleanVar(value=self.settings["autostart"])
        self.idle_time = ctk.StringVar()
        self.power_status = ctk.StringVar()

        self.build_ui()
        self.update_status_loop()

        self.protocol("WM_DELETE_WINDOW", self.handle_exit)
        self.bind("<Unmap>", self.on_minimize)

        if self.enabled.get():
            self.apply_settings()

    def build_ui(self):
        padding = {"padx": 20, "pady": 10}

        ctk.CTkCheckBox(self, text="Enable Shutdown on Idle", variable=self.enabled).pack(**padding)
        ctk.CTkLabel(self, text="Idle Timeout (minutes):").pack(**padding)
        ctk.CTkEntry(self, textvariable=self.idle_limit_var, width=80).pack(**padding)
        ctk.CTkCheckBox(self, text="Run on system startup", variable=self.autostart_var).pack(**padding)

        self.idle_label = ctk.CTkLabel(self, text="Current Idle: 0s")
        self.idle_label.pack(**padding)

        self.battery_label = ctk.CTkLabel(self, text="Power Status: Unknown")
        self.battery_label.pack(**padding)

        ctk.CTkButton(self, text="Apply Settings", command=self.apply_settings).pack(pady=(20, 10))

    def apply_settings(self):
        valid_timeout = self.get_valid_timeout()

        self.settings.update({
            "enabled": self.enabled.get(),
            "idle_minutes": valid_timeout,
            "autostart": self.autostart_var.get()
        })
        save_settings(self.settings)

        self.set_autostart(self.autostart_var.get())
        self.idle_limit = valid_timeout * 60
        self.monitoring = False
        time.sleep(0.1)

        if self.enabled.get():
            self.monitoring = True
            threading.Thread(
                target=monitor_loop,
                args=(self.idle_limit, lambda: self.monitoring, self.update_status),
                daemon=True
            ).start()
            messagebox.showinfo("LappyTappy Utils", "Monitoring (re)started.")
        else:
            messagebox.showinfo("LappyTappy Utils", "Monitoring stopped.")

    def get_valid_timeout(self):
        try:
            value = int(self.idle_limit_var.get())
            if value <= 0:
                raise ValueError
            return value
        except Exception:
            messagebox.showwarning("Invalid Input", "Idle timeout must be a positive number. Defaulting to 30.")
            self.idle_limit_var.set("30")
            return 30

    def update_status(self, idle_seconds, on_battery):
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._safe_update_status(idle_seconds, on_battery))
        except RuntimeError:
            print("[LappyTappy GUI] ⚠️ Tried updating UI after window closed.")

    def _safe_update_status(self, idle_seconds, on_battery):
        if self.winfo_exists():
            self.idle_time.set(f"{int(idle_seconds)}s")
            self.power_status.set("On Battery" if on_battery else "Plugged In")

    def update_status_loop(self):
        idle = get_idle_time()
        battery = psutil.sensors_battery()
        self.idle_label.configure(text=f"Current Idle: {int(idle)}s")
        self.battery_label.configure(
            text="Power Status: " + ("On Battery" if battery and not battery.power_plugged else "Plugged In")
        )
        self.after(3000, self.update_status_loop)

    # ===================== TRAY ==========================
    def hide_to_tray(self):
        self.withdraw()
        image = self.get_tray_icon()
        self.tray_icon = pystray.Icon("LappyTappy", image, "LappyTappy Utils", menu=pystray.Menu(
            pystray.MenuItem("Restore", self.show_window),
            pystray.MenuItem("Exit", self.exit_app)
        ))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def get_tray_icon(self):
        icon_path = os.path.join("media", "icon.ico")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color='green')
            draw = ImageDraw.Draw(image)
            draw.rectangle((16, 16, 48, 48), fill="white")
            return image

    def show_window(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.deiconify)

    def exit_app(self):
        self.monitoring = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)

    def on_minimize(self, event):
        if self.state() == "iconic":
            self.hide_to_tray()

    # ===================== EXIT POPUP ======================
    def handle_exit(self):
        if self.settings.get("close_behavior"):
            if self.settings["close_behavior"] == "minimize":
                self.hide_to_tray()
            else:
                self.exit_app()
            return

        dialog = Toplevel(self)
        dialog.title("Close LappyTappy")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.grab_set()

        remember_choice = BooleanVar()

        Label(dialog, text="What do you want to do?").pack(pady=10)
        Checkbutton(dialog, text="Remember my choice", variable=remember_choice).pack()

        def choose_exit():
            if remember_choice.get():
                self.settings["close_behavior"] = "exit"
                save_settings(self.settings)
            dialog.destroy()
            self.exit_app()

        def choose_minimize():
            if remember_choice.get():
                self.settings["close_behavior"] = "minimize"
                save_settings(self.settings)
            dialog.destroy()
            self.hide_to_tray()

        Button(dialog, text="Minimize to Tray", command=choose_minimize, width=20).pack(pady=(10, 5))
        Button(dialog, text="Exit App", command=choose_exit, width=20).pack()

    # ===================== AUTOSTART ======================
    def get_startup_path(self):
        return os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')

    def get_shortcut_path(self):
        return os.path.join(self.get_startup_path(), "LappyTappyUtils.lnk")

    def set_autostart(self, enable):
        shortcut_path = self.get_shortcut_path()

        if getattr(sys, 'frozen', False):
            target = sys.executable
        else:
            target = os.path.abspath(__file__)

        if enable:
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = target
            shortcut.WorkingDirectory = os.path.dirname(target)
            shortcut.IconLocation = target
            shortcut.save()
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)

    def is_autostart_enabled(self):
        return os.path.exists(self.get_shortcut_path())
