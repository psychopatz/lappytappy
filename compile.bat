pyinstaller --onefile --noconsole --icon=media/icon.ico main.py
rmdir /s /q build
del main.spec
pause
