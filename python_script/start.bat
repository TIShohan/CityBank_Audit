@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set REQ_PYTHON_VER=3.12
set SCRIPT_NAME=videoplayer.py

echo ========================================
echo   City Bank Video Reviewer - Auto Setup
echo ========================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Admin privileges for setup...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Check if Python is installed
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [-] Python not found. Installing Python %REQ_PYTHON_VER%...
    echo [!] This may take a few minutes. Please wait...
    
    :: Install Python 3.12 using winget
    winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    
    if !errorLevel! neq 0 (
        echo [X] Failed to install Python via winget. 
        echo please download it manually from https://www.python.org/downloads/
        pause
        exit /b
    )
    
    echo [+] Python installed successfully. 
    echo [!] You may need to restart this script after the installer finishes.
    timeout /t 5
)

:: Install required libraries directly
echo [+] Checking and installing necessary libraries...
python -m pip install --upgrade pip
python -m pip install streamlit pandas requests tqdm

:: Start the application
echo [+] Launching Application...
clear
streamlit run "%~dp0%SCRIPT_NAME%" --server.port 8501 --server.headless false

pause
