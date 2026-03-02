# 🎥 Side-by-Side Video Reviewer App

This application is designed specifically for reviewing candidate recordings for **City Bank Recruitment**. It allows a reviewer to watch two synchronized videos (Screen Record and Webcam) simultaneously with a single universal controller.

## 📁 Project Structure
- **Script Location**: `D:\City Bank_Recruitment\python_script\video_reviewer_app.py`
- **Data Source**: `D:\City Bank_Downloads` (Contains folders named by Candidate ID)
- **Framework**: Streamlit + Custom HTTP Streaming Server

## 🚀 Key Features
- **Synchronized Playback**: A single Play/Pause button and Seek Bar control both videos at once.
- **Universal Seek Bar**: Scrubbing through one timeline automatically updates both videos.
- **Individual Mute Controls**: Each video has a dedicated mute button to isolate audio.
- **Auto-Sync Logic**: Built-in Javascript logic prevents video drift; the webcam video is snapped to the screen record's timestamp if they get out of sync by >0.3s.
- **Playback Speeds**: Options for 0.5x, 1.0x, 1.5x, and 2.0x playback.
- **Range-Request Support**: Uses a custom `RangeRequestHandler` to allow seeking/jumping in high-resolution `.mp4` files.

## 🛠 Progress & Status
- [x] **Initial Setup**: Created basic Streamlit UI for Candidate ID entry.
- [x] **Video Streaming**: Implemented a background threading server to serve local files from `D:\City Bank_Downloads` via HTTP.
- [x] **Sync Logic**: Added JS-based synchronization for play, pause, and seek events.
- [x] **Bug Fix (Path Resolution)**: Resolved an `os.chdir` conflict where Streamlit couldn't find the script file. Now uses absolute path translation in the HTTP server.
- [x] **UI Polish**: Applied a premium dark-mode theme with glassmorphism effects.

## 📝 Usage for Future Agents
- **To Run**: `streamlit run video_reviewer_app.py --server.port 8502`
- **Port Conflict**: The video server finds a random free port to stream files; this port is displayed in the sidebar status.
- **File Matching**: The app expects files inside `D:\City Bank_Downloads\{candidate_id}\` named exactly as:
  - `{candidate_id}_screenrecord.mp4`
  - `{candidate_id}_webcam.mp4`

## ⏳ To-Do / Future Enhancements
- [ ] Add a "Save Review Notes" feature.
- [ ] Implement a folder browser for easier Candidate ID selection.
- [ ] Add frame-by-frame navigation for detailed analysis.
