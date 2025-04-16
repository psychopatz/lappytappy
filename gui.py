import customtkinter as ctk
import psutil
import threading
import time
import os
import sys
import pystray
from PIL import Image, ImageDraw
from win32com.client import Dispatch
from CTkMessagebox import CTkMessagebox
from settings_manager import load_settings, save_settings, reset_settings
from monitor import monitor_loop
from utils import get_idle_time, show_notification




def center_popup(popup, parent):
    popup.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (popup.winfo_height() // 2)
    popup.geometry(f"+{x}+{y}")


class LappyTappyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LappyTappy Utils")
        self.geometry("400x350")
        self.resizable(False, False)

        self.settings = load_settings()
        self.monitoring = False
        self.tray_icon = None
        self.idle_limit = self.settings["idle_minutes"] * 60
        self.close_behavior = self.settings.get("close_behavior", None)

        self.enabled = ctk.BooleanVar(value=self.settings["enabled"])
        self.idle_limit_var = ctk.StringVar(value=str(self.settings["idle_minutes"]))
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

        self.idle_label = ctk.CTkLabel(self, text="Current Idle: 0s")
        self.idle_label.pack(**padding)

        self.battery_label = ctk.CTkLabel(self, text="Power Status: Unknown")
        self.battery_label.pack(**padding)

        ctk.CTkButton(self, text="Apply Settings", command=self.apply_settings).pack(pady=(10, 5))
        ctk.CTkButton(self, text="Settings", command=self.open_settings_popup).pack()

    def apply_settings(self):
        valid_timeout = self.get_valid_timeout()

        self.settings.update({
            "enabled": self.enabled.get(),
            "idle_minutes": valid_timeout
        })
        save_settings(self.settings)

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
            show_notification("LappyTappy", "Monitoring (re)started.")
        else:
            show_notification("LappyTappy", "Monitoring stopped.")


    def get_valid_timeout(self):
        try:
            value = int(self.idle_limit_var.get())
            if value <= 0:
                raise ValueError
            return value
        except Exception:
            self.idle_limit_var.set("30")
            CTkMessagebox(title="Invalid Input", message="Idle timeout must be a positive number. Defaulting to 30.", icon="warning")
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

    def on_minimize(self, event):
        if self.state() == "iconic":
            self.hide_to_tray()

    # ========== TRAY ==========
    def hide_to_tray(self):
        self.withdraw()
        image = self.get_tray_icon()
        self.tray_icon = pystray.Icon("LappyTappy", image, "LappyTappy Utils", menu=pystray.Menu(
            pystray.MenuItem("Restore", self.show_window),
            pystray.MenuItem("Exit", self.exit_app)
        ))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.deiconify)

    def exit_app(self):
        self.monitoring = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)

    def get_tray_icon(self):
        icon_path = os.path.join("media", "icon.ico")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color='green')
            draw = ImageDraw.Draw(image)
            draw.rectangle((16, 16, 48, 48), fill="white")
            return image

    # ========== EXIT DIALOG ==========
    def handle_exit(self):
        if self.settings.get("close_behavior"):
            if self.settings["close_behavior"] == "minimize":
                self.hide_to_tray()
            else:
                self.exit_app()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Close LappyTappy?")
        dialog.geometry("320x200")
        dialog.resizable(False, False)
        dialog.grab_set()
        center_popup(dialog, self)

        remember_var = ctk.BooleanVar()

        ctk.CTkLabel(dialog, text="What do you want to do?").pack(pady=10)
        ctk.CTkCheckBox(dialog, text="Remember my choice", variable=remember_var).pack()

        def choose_exit():
            if remember_var.get():
                self.settings["close_behavior"] = "exit"
                save_settings(self.settings)
            dialog.destroy()
            self.exit_app()

        def choose_minimize():
            if remember_var.get():
                self.settings["close_behavior"] = "minimize"
                save_settings(self.settings)
            dialog.destroy()
            self.hide_to_tray()

        ctk.CTkButton(dialog, text="Minimize to Tray", command=choose_minimize, width=240).pack(pady=10)
        ctk.CTkButton(dialog, text="Exit Application", command=choose_exit, width=240).pack(pady=5)

    # ========== SETTINGS POPUP ==========
    def open_settings_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Settings")
        popup.geometry("300x280")
        popup.resizable(False, False)
        popup.grab_set()
        center_popup(popup, self)

        ctk.CTkLabel(popup, text="Theme:").pack(pady=(20, 5))

        def change_theme(value):
            ctk.set_appearance_mode(value)

        theme_options = ["System", "Light", "Dark"]
        theme_dropdown = ctk.CTkOptionMenu(popup, values=theme_options, command=change_theme)
        theme_dropdown.set("System")
        theme_dropdown.pack()

        autostart_var = ctk.BooleanVar(value=self.is_autostart_enabled())

        def toggle_autostart():
            self.set_autostart(autostart_var.get())

        ctk.CTkCheckBox(popup, text="Run on System Startup", variable=autostart_var, command=toggle_autostart).pack(pady=15)

        ctk.CTkButton(popup, text="Reset to Default", fg_color="red", hover_color="#aa0000", command=self.confirm_reset).pack(pady=(20, 10))

    def confirm_reset(self):
        confirm = ctk.CTkToplevel(self)
        confirm.title("Confirm Reset")
        confirm.geometry("300x150")
        confirm.grab_set()
        center_popup(confirm, self)

        ctk.CTkLabel(confirm, text="Reset all settings and restart?").pack(pady=20)

        def do_reset():
            reset_settings()
            confirm.destroy()
            self.restart_app()

        ctk.CTkButton(confirm, text="Yes, Reset", command=do_reset, fg_color="red", hover_color="#aa0000").pack(pady=10)
        ctk.CTkButton(confirm, text="Cancel", command=confirm.destroy).pack()

    def restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    # ========== STARTUP SHORTCUT ==========
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
