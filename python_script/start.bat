@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set REQ_PYTHON_VER=3.12
set SCRIPT_NAME=videoplayer.py

echo ========================================
echo   City Bank Video Reviewer - Auto Setup
echo ========================================

:: 1. Check for Administrator privileges (Required for Python install and PATH changes)
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
        :: Small trick to reload PATH in current session
        for /f "tokens=*" %%a in ('powershell -Command "[System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')"') do set "PATH=%%a"
        
        timeout /t 3 >nul
    )
)

:: 3. Verification of Python command (handling alias issues)
set "PY_CMD=python"
python --version >nul 2>&1 || set "PY_CMD=py"

echo [+] Using Python Command: !PY_CMD!

:: 4. Install/Update required libraries
echo [+] Installing necessary libraries (streamlit, pandas, requests, tqdm)...
!PY_CMD! -m pip install --upgrade pip
!PY_CMD! -m pip install streamlit pandas requests tqdm

:: 5. Launch the application
echo [+] Launching Application...
:: Use 'python -m' to ensure the library is found even if pathing is fresh
!PY_CMD! -m streamlit run "%~dp0%SCRIPT_NAME%" --server.port 8501 --server.headless false

if %errorLevel% neq 0 (
    echo [X] App failed to start. 
    echo [!] Common fix: Restart this script one more time to finish path sync.
    pause
)

pause
