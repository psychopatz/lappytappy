pyinstaller --noconsole --onefile main.py --icon=media/icon.ico --name "LappyTappy"
rmdir /s /q build
del main.spec
pause
