#!/bin/bash

# --- City Bank Video Reviewer: macOS Launcher ---

# Clear screen for better readability
clear
echo "========================================"
echo "   City Bank Video Reviewer (macOS)"
echo "========================================"

# 1. Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "[!] python3 could not be found."
    echo "[!] Please install Python from https://www.python.org/downloads/"
    exit
fi

# 2. Check and install dependencies
echo "[+] Checking/Installing dependencies (streamlit, pandas, requests, tqdm)..."
python3 -m pip install --quiet streamlit pandas requests tqdm

# 3. Launch the application
echo "[+] Launching Video Reviewer..."
echo "[!] If the browser doesn't open automatically, go to: http://localhost:8501"

# We use 'python3 -m streamlit' to avoid PATH issues common on Mac
python3 -m streamlit run videoplayer_mac.py --server.port 8501

# Keep terminal open if it crashes
echo ""
echo "[!] Script finished. Press any key to exit..."
read -n 1
