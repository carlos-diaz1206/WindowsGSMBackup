@echo off
setlocal enabledelayedexpansion
REM WinGSM Backup Manager - Installation Script
REM This script installs Python (if needed) and all required packages

echo ========================================
echo WinGSM Backup Manager - Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo.
    echo Attempting to install Python automatically...
    echo.
    
    REM Check if winget is available (Windows Package Manager)
    set WINGET_AVAILABLE=0
    where winget >nul 2>&1
    if not errorlevel 1 set WINGET_AVAILABLE=1
    
    if !WINGET_AVAILABLE! EQU 1 (
        echo Using Windows Package Manager (winget) to install Python...
        echo This will install the latest Python 3.x version.
        echo.
        echo Please wait, this may take a few minutes...
        echo.
        
        REM Install Python using winget
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        if not errorlevel 1 (
            echo.
            echo Python installation completed!
            echo.
            echo Refreshing environment variables...
            REM Refresh PATH to include newly installed Python
            set "SYSTEMPATH="
            for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEMPATH=%%b"
            if defined SYSTEMPATH (
                set "PATH=!SYSTEMPATH!"
            )
            
            REM Add common Python installation paths
            if exist "%LOCALAPPDATA%\Programs\Python" (
                for /d %%p in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
                    set "PATH=!PATH!;%%p;%%p\Scripts"
                )
            )
            if exist "%ProgramFiles%\Python*" (
                for /d %%p in ("%ProgramFiles%\Python*") do (
                    set "PATH=!PATH!;%%p;%%p\Scripts"
                )
            )
            
            REM Wait a moment for PATH to update
            timeout /t 3 /nobreak >nul
            
            REM Verify Python is now available
            python --version >nul 2>&1
            if not errorlevel 1 (
                echo Python is now available!
                echo.
                goto :python_installed
            )
        )
    )
    
    REM If winget failed or is not available, try downloading Python installer
    echo winget is not available or installation failed.
    echo.
    echo Attempting to download Python installer...
    echo.
    
    REM Create temp directory
    set "TEMP_DIR=%TEMP%\WinGSMBackup_Install"
    if not exist "!TEMP_DIR!" mkdir "!TEMP_DIR!"
    
    REM Download Python installer (64-bit, latest stable)
    set "PYTHON_URL=https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe"
    set "PYTHON_INSTALLER=!TEMP_DIR!\python-installer.exe"
    
    echo Downloading Python installer...
    echo This may take a few minutes depending on your connection speed...
    echo.
    
    REM Try using PowerShell to download
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}" >nul 2>&1
    
    if not exist "!PYTHON_INSTALLER!" (
        echo.
        echo ERROR: Failed to download Python installer automatically.
        echo.
        echo Please install Python manually:
        echo   1. Download Python 3.8+ from: https://www.python.org/downloads/
        echo   2. During installation, check "Add Python to PATH"
        echo   3. Run this script again after installation
        echo.
        echo Opening Python download page in your browser...
        start https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo Installing Python...
    echo Please wait, this may take a few minutes...
    echo.
    echo IMPORTANT: In the Python installer window that opens:
    echo   - Check "Add Python to PATH" at the bottom
    echo   - Click "Install Now"
    echo.
    
    REM Run Python installer with silent install and add to PATH
    "!PYTHON_INSTALLER!" /quiet InstallAllUsers=1 PrependPath=1
    
    REM Wait for installation to complete
    timeout /t 10 /nobreak >nul
    
    REM Clean up installer
    del /q "!PYTHON_INSTALLER!" >nul 2>&1
    rmdir "!TEMP_DIR!" >nul 2>&1
    
    REM Refresh PATH
    echo.
    echo Refreshing environment variables...
    set "SYSTEMPATH="
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEMPATH=%%b"
    if defined SYSTEMPATH (
        set "PATH=!SYSTEMPATH!"
    )
    
    REM Add common Python installation paths
    if exist "%ProgramFiles%\Python*" (
        for /d %%p in ("%ProgramFiles%\Python*") do (
            set "PATH=!PATH!;%%p;%%p\Scripts"
        )
    )
    if exist "%ProgramFiles(x86)%\Python*" (
        for /d %%p in ("%ProgramFiles(x86)%\Python*") do (
            set "PATH=!PATH!;%%p;%%p\Scripts"
        )
    )
    
    REM Wait for PATH to update
    timeout /t 5 /nobreak >nul
    
    REM Verify Python is now available
    python --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo WARNING: Python was installed but may not be in PATH yet.
        echo.
        echo Please do one of the following:
        echo   1. Close and reopen this command prompt, then run install.bat again
        echo   2. Restart your computer to ensure PATH is updated
        echo   3. Manually add Python to PATH in System Environment Variables
        echo.
        pause
        exit /b 1
    )
    
    echo Python is now available!
    echo.
)

:python_installed
REM Display Python version
echo Checking Python installation...
python --version
echo.

REM Check Python version is 3.8 or higher - simplified approach
set PYTHON_OK=0
python --version 2>&1 | findstr /R /C:"Python 3\.[89]\." >nul
if not errorlevel 1 set PYTHON_OK=1
python --version 2>&1 | findstr /R /C:"Python 3\.[1-9][0-9]\." >nul
if not errorlevel 1 set PYTHON_OK=1

if !PYTHON_OK! EQU 0 (
    REM Check if it's Python 3 but older than 3.8
    python --version 2>&1 | findstr /R /C:"Python 3\.[0-7]\." >nul
    if not errorlevel 1 (
        echo ERROR: Python 3.8 or later is required.
        echo.
        python --version
        echo.
        echo Please install Python 3.8 or later from https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    REM If not Python 3 at all, warn but continue
    python --version 2>&1 | findstr /R /C:"Python 2\." >nul
    if not errorlevel 1 (
        echo ERROR: Python 3.8 or later is required. Python 2.x is not supported.
        echo.
        pause
        exit /b 1
    )
)

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo.
    echo Attempting to install pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: Failed to install pip
        echo.
        echo Please ensure pip is installed with Python.
        echo.
        pause
        exit /b 1
    )
)

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found
    echo.
    echo Please make sure you're running this script from the project directory.
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

echo Installing required packages...
echo.
echo This may take a few minutes...
echo.

REM Upgrade pip first
echo [1/2] Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo WARNING: Failed to upgrade pip, continuing anyway...
    echo.
)

REM Install requirements
echo [2/2] Installing packages from requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install some packages
    echo.
    echo Please check the error messages above and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo You can now run the application with:
echo   python main.py
echo   or double-click run.bat
echo.
pause
endlocal
