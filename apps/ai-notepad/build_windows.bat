@echo off
setlocal
cd /d "%~dp0"

echo === AI Notepad Windows Build ===

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python 3.11+ from python.org and enable the launcher.
    pause
    exit /b 1
)

py -m venv .venv
if errorlevel 1 exit /b 1

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --clean --windowed --onefile ^
  --name "AI Notepad" ^
  ai_notepad.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED
    pause
    exit /b 1
)

echo.
echo BUILD PASS
echo EXE: %CD%\dist\AI Notepad.exe
pause
