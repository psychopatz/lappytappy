import customtkinter as ctk
from gui import LappyTappyApp

def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = LappyTappyApp()
    app.mainloop()

if __name__ == "__main__":
    main()
