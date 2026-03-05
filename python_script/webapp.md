# Candidate Video Manager (Web Application)

## 🎥 Application Overview
The **Candidate Video Manager** is a visual, browser-based interface designed for fast, manual or bulk processing of candidate recording links. It provides an intuitive GUI to manage, download, and transcode video files without editing CSV records.

## 🚀 Key Features
- **User-Friendly Interface (Streamlit):** A clean, browser-based dashboard with two modes: **Single Candidate** and **Bulk Upload**.
- **Bulk Processing (CSV/Excel):** Upload spreadsheets to process dozens of candidates at once.
- **Smart Column Detection:** Automatically identifies "candidate_id", "screen_record_url", and "webcam_record_url".
- **Interactive Row Selection:** Select specific candidates to process; includes "Mark All" and "Unmark All" controls.
- **Multi-threaded Processing:** Configurable **Concurrent Workers** (1-10) to process multiple candidates simultaneously, maximizing your PC's CPU and bandwidth.
- **Interruption Safety:** Automatically cleans up partial/corrupted files if a download is interrupted, ensuring clean retries.
- **Bulk Summary Report:** Provides a categorized result (Success/Partial/Failed) with metrics after every bulk operation.
- **Interactive Folder Selection:** Integrated Windows Folder Picker ("Browse" button) for setting custom download destinations.
- **Smart Transcoding Control:** 
  - Choice of **Original**, **Rename**, or **Convert** (True MP4) output.
  - Interactive **Conversion Preset Slider** in the sidebar.
- **Live Progress UI:** Real-time individual progress bars for screen and webcam files, along with an **Overall Progress** tracker for bulk jobs.

## 🛠 Technical Stack
- **Dashboard:** Streamlit (Python Web Framework).
- **Processing:** FFmpeg (via Subprocess) for H.264 transcoding.
- **Concurrency:** `ThreadPoolExecutor` (3 workers) with `ScriptRunContext` for thread-safe UI updates.
- **Data Handling:** `pandas` for CSV/Excel parsing and interactive data editing.
- **System Integration:** `tkinter` for native OS folder browsing.

## 📖 How to Use
### Option A: Single Candidate
1. **Identity:** Enter the **Candidate ID**.
2. **Links:** Paste the screen and webcam links.
3. **Start:** Click `🚀 Start Single Process`.

### Option B: Bulk Upload
1. **Upload:** Drag and drop your CSV or Excel file.
2. **Select:** Use the checkboxes or the **Mark All** button to choose which candidates to process.
3. **Process:** Click `🚀 Process Selected Candidates`. Watch 3 candidates process at once!

## 📂 System File
Located at: `d:\CityBank_Audit\python_script\web_downloader.py`
