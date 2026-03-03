# 🎥 City Bank Video Reviewer: Developer & User Guide

This document provides a comprehensive technical and operational overview of the **One-Click Side-by-Side Video Reviewer** application.

---

## 🏗 High-Level Architecture

The application operates using a **Split-Server Architecture**:

1.  **Frontend (Streamlit)**: Handles the User Interface, Candidate auto-discovery, and layout management.
2.  **Multithreaded Media Server**: A custom `ThreadingTCPServer` that serves video chunks in parallel, ensuring both video streams load simultaneously without blocking each other.
3.  **Client-Side Sync Engine (vanilla JS)**: Embedded Javascript that ensures both video elements remain perfectly in sync with high-precision drift correction.

---

## 🚀 One-Click Quick Start (`start.bat`)

The application is designed for instant deployment on any Windows PC.

### What it does:
- **Admin Elevation**: Automatically requests rights to manage system paths.
- **Silent Python Setup**: Uses `winget` to install **Python 3.12** if missing.
- **Dependency Management**: Installs `streamlit`, `pandas`, `requests`, and `tqdm`.
- **PATH Refresh**: Dynamically reloads the system PATH into the current session so it works immediately after installation without a restart.
- **Auto-Launch**: Starts the server and opens the browser automatically.

---

## 🛠 Core Technical Components

### 1. High-Performance Streaming
- **Segmented Delivery**: Uses a `RangeRequestHandler` to allow the browser to seek instantly anywhere in the timeline.
- **128KB Chunk Optimization**: Adjusted chunk size to 128KB to balance low latency with high throughput for local SSDs.
- **Threading Support**: Upgraded from `TCPServer` to `ThreadingTCPServer` to allow the browser to fetch data for both videos at the exact same time.

### 2. Client-Side Sync & UI Logic
- **Drift Correction**: Logic checks every few milliseconds. If videos drift apart by more than 0.3s, the secondary video is snapped to the master's timestamp.
- **Debounced Seeking**: Arrow-key seeking (5s) is debounced to prevent browser request clogging, ensuring stability during rapid navigation.
- **Active Highlight System**: 
    - **Dimmed State**: Videos are dimmed (60% opacity) and shrunk (98% scale) when paused.
    - **Active State**: The active video pair glows with a blue border and scales to 100% during playback to maximize focus.
- **Glassmorphism**: Strategic use of frosted-glass backgrounds for individual video control bars.

### 3. Navigation & Controls
- **Spacebar**: Toggles Play/Pause globally.
- **Left/Right Arrows**: Seek -5s / +5s (Debounced).
- **Auto-Sync on Load**: Both videos are strictly initialized to `00:00:00` upon selecting a new candidate.
- **Duration Display**: Individual `Dur: HH:MM:SS` indicators for quick video length comparison.

---

## 📁 Required File Structure
The app automatically discovers folders following this standard:
```text
D:/City Bank_Downloads/
└── {CandidateID}/
    ├── {CandidateID}_screenrecord.mp4
    └── {CandidateID}_webcam.mp4
```

---

## 🛠 Recent Updates & Progress
- [x] **One-Click Installer**: Created `start.bat` for portable, zero-setup deployment.
- [x] **Parallel Streaming**: Switched to Threading server for zero-lag dual playback.
- [x] **Auto-Discovery**: Main page now features a dropdown of detected candidates.
- [x] **UI Polish**: Implemented active highlight, removed heavy headers to maximize video area.
- [x] **HH:MM:SS Formatting**: Global and individual durations unified to 24hr format.
- [x] **Debounced Seek**: Fixed "Video Freezing" bug during rapid arrow-key usage.

---

## ⏳ Future Roadmap
- [ ] **Evidence Snapshot**: Button to save a side-by-side `.png` of the current frame for reports.
- [ ] **Review Notes**: Native input box to save text logs directly into the candidate folder.
- [ ] **Frame Stepper**: Support for frame-by-frame forward/backward movement.
