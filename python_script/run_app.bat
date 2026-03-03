@echo off
cd /d "%~dp0"
echo Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Python not found! Please install Python.
    pause
    exit
)
echo Installing libraries...
pip install streamlit pandas requests tqdm
echo Starting App...
streamlit run video_reviewer_app.py
pause
