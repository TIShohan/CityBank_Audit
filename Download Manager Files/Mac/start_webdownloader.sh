#!/bin/bash

# --- CONFIGURATION ---
SCRIPT_NAME="web_downloader_macos.py"

echo "========================================"
echo "  Candidate Video Downloader - macOS Setup"
echo "========================================"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[X] Python 3 not found."
    echo "[!] Please install Python from: https://www.python.org/downloads/"
    exit 1
fi

# 2. Check for FFmpeg (Required for conversion)
if ! command -v ffmpeg &> /dev/null; then
    echo "[!] FFmpeg not found. Conversion mode will fail."
    echo "[!] Please install it using Homebrew: brew install ffmpeg"
    echo "[!] Or download from: https://ffmpeg.org/download.html"
fi

# 3. Install/Update required libraries
echo "[+] Installing/Updating libraries (streamlit, pandas, requests, openpyxl)..."
python3 -m pip install --upgrade pip
python3 -m pip install streamlit pandas requests openpyxl

# 4. Launch the application
echo "[+] Launching Video Downloader on Port 8502..."
# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
python3 -m streamlit run "$DIR/$SCRIPT_NAME" --server.port 8502 --server.headless false

if [ $? -ne 0 ]; then
    echo "[X] App failed to start."
    read -p "Press enter to exit..."
fi
