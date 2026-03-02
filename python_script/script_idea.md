# Candidate Record Downloader

## Script Overview
A high-performance Python automation tool designed for large-scale video acquisition and processing. It maps candidate data from a CSV report to remote AWS/S3 resources, organizing them into a structured directory with automated transcoding.

## 🚀 Key Features
- **Parallel File Processing:** Uses 10 simultaneous worker threads. Processes Screen and Webcam recordings for multiple candidates in parallel for maximum bandwidth/CPU usage.
- **Triple Output Modes:**
  - **Original:** Downloads and keeps the native `.webm` source.
  - **Rename (FAST):** Instant conversion to `.mp4` by renaming the extension (best for quick viewing).
  - **Convert (FFmpeg):** True H.264 transcode for maximum device compatibility.
- **FFmpeg Performance Tuning:** Interactive preset menu (Ultrafast, Veryfast, Faster) to balance CPU conversion speed vs. final disk space.
- **Smart Skip (Advanced):**
  - Detects if a candidate is "complete" before asking for quantity.
  - If a file exists in an alternate format (e.g., .webm), the script renames or converts it **locally** instead of redownloading.
- **Rich Real-Time UI:**
  - **Nested Progress Bars:** 1 "Overall" bar + 10 individual "Active File" bars.
  - **Live Feedback:** Shows download speeds (MB/s) and conversion progress (Percentage or Seconds).
  - **ID Tracking:** Every active bar displays the specific `[ID: XXXX]` for intuitive monitoring.

## 🛠 Technical Architecture
- **Language:** Python 3.12+
- **Concurrency:** `concurrent.futures.ThreadPoolExecutor` (10 Workers).
- **Processing Engine:** `FFmpeg` (via subprocess) for reliable transcoding.
- **Progress Management:** `tqdm` with dynamic position locking to prevent UI flickering.
- **Data Engine:** `pandas` for efficient filtering of large CSV datasets.
- **Safety:** Thread-safe logging and automated directory management.

## 📁 System Paths
- **CSV Data:** `d:\City Bank_Recruitment\candidate_score_report - Filtered Blanksout Final.csv`
- **Output Dir:** `d:\City Bank_Recruitment\python_script\downloads`
- **Audit Log:** `d:\City Bank_Recruitment\python_script\download_log.txt`

## 📋 Running the Script
1. Ensure FFmpeg is installed and added to your System PATH.
2. Install dependencies: `pip install pandas requests tqdm`
3. Run: `python downloader.py`
4. Select your mode, choose your conversion speed, and enter the quantity of candidates to process.
