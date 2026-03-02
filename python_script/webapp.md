# Candidate Video Manager (Web Application)

## 🎥 Application Overview
The **Candidate Video Manager** is a visual, browser-based interface designed for fast, manual processing of candidate recording links. It provides an intuitive GUI to manage, download, and transcode video files without editing CSV records.

## 🚀 Key Features
- **User-Friendly Interface (Streamlit):** A clean, browser-based dashboard hosted locally.
- **Manual Input:** Dedicated sections for pasting Candidate IDs and direct URLs (`screen_record_url`, `webcam_record_url`).
- **Parallel Processing:** Handles Screen and Webcam recordings simultaneously in background threads, effectively doubling the processing speed per candidate.
- **Interactive Folder Selection:** Integrated Windows Folder Picker ("Browse" button) for setting custom download destinations.
- **Smart Transcoding Control:** 
  - Choice of **Original**, **Rename**, or **Convert** (True MP4) output.
  - Interactive **Conversion Preset Slider** to control speed vs. file size.
- **Live Progress UI:** Real-time side-by-side progress bars for each file, showing percentages and real-time conversion speeds.

## 🛠 Technical Stack
- **Dashboard:** Streamlit (Python Web Framework).
- **Processing:** FFmpeg (via Subprocess) for H.264 transcoding.
- **Concurrency:** `ThreadPoolExecutor` with automated `ScriptRunContext` management for thread-safe UI updates.
- **System Integration:** `tkinter` for native OS folder browsing.

## 📖 How to Use
1. **Set Folder:** Choose where you want the files saved using the **Browse** button.
2. **Identity:** Enter the **Candidate ID**.
3. **Links:** Paste the screen and webcam links into their respective fields.
4. **Options:** Select "Convert (.mp4)" and adjust the conversion speed in the "Advanced Settings" if needed.
5. **Start:** Click `🚀 Start Process`. Watch both progress bars move simultaneously!

## 📂 System File
Located at: `d:\City Bank_Recruitment\python_script\web_downloader.py`
