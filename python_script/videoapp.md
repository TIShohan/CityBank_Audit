# 🎥 City Bank Video Reviewer: Developer Guide

This document provides a deep technical overview of the **Side-by-Side Video Reviewer** application (`videoplayer.py`). It is designed to help new agents or developers understand the architecture, core logic, and synchronization mechanisms.

## 🏗 High-Level Architecture

The application operates using a **Split-Server Architecture**:

1.  **Frontend (Streamlit)**: Handles the User Interface, Candidate ID entry, and Folder Picking.
2.  **Background Media Server (Python Threading)**: A dedicated HTTP server that streams video files from the local filesystem.
3.  **Client-Side Sync Engine (HTML5/JS)**: Embedded Javascript that ensures both video elements remain perfectly in sync.

---

## 🛠 Core Technical Components

### 1. Dynamic Path Management (`PathConfig`)
Because the background HTTP server runs in a separate thread, we cannot use global variables or `os.chdir()` (which would break Streamlit’s file resolution). 
- **Solution**: A `PathConfig` class instance is stored in `st.session_state`. 
- **Mechanism**: The background server holds a reference to this object. When the user "Browses" for a new folder, we update `path_config.path`, and the running server immediately starts looking in the new location without needing a restart.

### 2. The `RangeRequestHandler`
Standard browsers require "Byte-Range" support to allow users to click anywhere on a video timeline (seeking).
- **Function**: It intercepts `GET` requests, parses the `Range` header (e.g., `bytes=5000-`), and sends back a `206 Partial Content` response.
- **Path Translation**: It uses `translate_path` to map the browser's request (e.g., `/794/video.mp4`) to the dynamic `base_path` selected by the user.

### 3. Synchronized Playback Engine (Javascript)
Both videos are rendered inside a single `st.components.v1.html` block. The synchronization logic is entirely client-side for zero latency:
- **Master-Slave Sync**: `v1` (Screen Record) acts as the master. `v2` (Webcam) listens for `timeupdate` events from `v1`.
- **Drift Correction**: If `Math.abs(v1.currentTime - v2.currentTime) > 0.3` seconds, the code forces `v2` to jump to `v1`'s exact time.
- **Universal Seek Bar**: An `<input type="range">` calculates the percentage of the master video’s duration and updates both `v1.currentTime` and `v2.currentTime` simultaneously.

---

## 📁 File Structure & Expectations

The app looks for a specific naming convention within the selected **Source Path**:
```text
Source Path/
└── {CandidateID}/
    ├── {CandidateID}_screenrecord.mp4
    └── {CandidateID}_webcam.mp4
```

---

## 🚀 Deployment & Runtime Details

### Running the App
```bash
streamlit run videoplayer.py --server.port 8502
```

### Port Management
- The app uses `find_free_port()` to automatically find an available port for the video streaming server (to avoid conflicts with the Streamlit port).
- The port remains persistent in the `st.session_state` during the browser session.

---

## 🛠 Progress Log & Knowledge Base

- [x] **Absolute Path Fix**: Previously, `os.chdir` caused "File Not Found" errors for the `.py` script. This was resolved by using a custom `translate_path` in the `RangeRequestHandler`.
- [x] **Folder Picker**: Integrated `tkinter.filedialog` to allow users to pick recording folders on any drive.
- [x] **Playback Speed**: Implemented `playbackRate` synchronization for fast/slow-motion review.
- [x] **Mute Toggle**: Added CSS/JS logic for individual mute buttons with UI state colors (Red=Active, Grey=Muted).

## ⏳ Future Roadmap
- [ ] **Review Notes**: Add an input field to save time-stamped comments to a `.txt` or `.csv` file in the candidate folder.
- [ ] **Frame Stepper**: Add buttons to move forward/backward by exactly 1 frame (0.04s).
- [ ] **Auto-Discovery**: Automatically list all Candidate IDs found in the selected folder in a dropdown.
