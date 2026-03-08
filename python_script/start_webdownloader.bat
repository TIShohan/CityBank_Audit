@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set REQ_PYTHON_VER=3.12
set SCRIPT_NAME=web_downloader.py

echo ========================================
echo   Candidate Video Downloader - Auto Setup
echo ========================================

:: 1. Check for Administrator privileges
echo [+] Verifying Admin rights...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Admin privileges for setup...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 2. Check if Python is already installed
echo [+] Checking for Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    py --version >nul 2>&1
    if !errorLevel! neq 0 (
        echo [-] Python not found. Installing Python %REQ_PYTHON_VER% via winget...
        echo [!] This will take a few minutes. Please wait...
        
        :: Install Python 3.12
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        
        if !errorLevel! neq 0 (
            echo [X] Failed to install Python via winget. 
            echo [!] Please install Python manually from: https://www.python.org/downloads/
            echo [!] Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b
        )
        
        echo [+] Python installed successfully.
        echo [+] Refreshing system environment variables...
        for /f "tokens=*" %%a in ('powershell -Command "[System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')"') do set "PATH=%%a"
        
        timeout /t 3 >nul
    )
)

:: 3. Check for FFmpeg
echo [+] Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if %errorLevel% neq 0 (
    echo [-] FFmpeg not found. Installing via winget...
    winget install --id GYAN.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    if !errorLevel! neq 0 (
        echo [!] FFmpeg install failed. Please install manually if conversion is needed.
    ) else (
        echo [+] FFmpeg installed successfully.
        :: Refresh PATH again for FFmpeg
        for /f "tokens=*" %%a in ('powershell -Command "[System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')"') do set "PATH=%%a"
    )
)

:: 4. Verification of Python command
set "PY_CMD=python"
python --version >nul 2>&1 || set "PY_CMD=py"

echo [+] Using Python Command: !PY_CMD!

:: 5. Install/Update required libraries
echo [+] Installing necessary libraries (streamlit, pandas, requests, openpyxl, tk)...
!PY_CMD! -m pip install --upgrade pip
!PY_CMD! -m pip install streamlit pandas requests openpyxl

:: 5. Launch the application
echo [+] Launching Video Downloader...
:: Use a different port (8502) to avoid conflict if videoplayer is already running
!PY_CMD! -m streamlit run "%~dp0%SCRIPT_NAME%" --server.port 8502 --server.headless false

if %errorLevel% neq 0 (
    echo [X] App failed to start. 
    echo [!] Common fix: Restart this script one more time to finish path sync.
    pause
)

pause
