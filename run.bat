@echo off
REM WinGSM Backup Manager - Quick Run Script

echo Starting WinGSM Backup Manager...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or later from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found
    echo.
    echo Please make sure you're running this script from the project directory.
    echo.
    pause
    exit /b 1
)

REM Run the application
REM The console window will minimize automatically when the app starts
python main.py

if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    echo.
    echo If this is the first time running, make sure to run install.bat first
    echo to install required packages.
    echo.
    pause
    exit /b 1
)

