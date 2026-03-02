import streamlit as st
import os
import requests
import subprocess
import time
import threading
from tkinter import filedialog, Tk

# Page Configuration
st.set_page_config(page_title="Candidate Record Manager", page_icon="🎥", layout="centered")

# --- CORE LOGIC (Adapted for Streamlit) ---

def get_video_duration(input_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0

def convert_to_mp4(input_path, preset, status_text, progress_bar, filename):
    output_path = input_path.replace(".webm", ".mp4")
    duration = get_video_duration(input_path)
    
    try:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c:v", "libx264", "-crf", "23", "-preset", preset, "-c:a", "aac", "-progress", "pipe:1", output_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, bufsize=1)
        
        last_val = 0
        for line in process.stdout:
            if "out_time_ms=" in line or "out_time_us=" in line:
                try:
                    raw_val = int(line.split('=')[1].strip())
                    time_sec = raw_val / 1_000_000
                    if duration > 0:
                        progress = min(100, int((time_sec / duration) * 100))
                        progress_bar.progress(progress / 100, text=f"Converting {filename}... {progress}%")
                    else:
                        progress_bar.progress(0, text=f"Converting {filename}... {int(time_sec)}s processed")
                except: pass
        process.wait()
        
        if process.returncode == 0:
            if os.path.exists(input_path): os.remove(input_path)
            return True, "Done"
        return False, "FFmpeg Error"
    except Exception as e:
        return False, str(e)

def download_file(url, folder, filename, mode, preset, status_text, progress_bar):
    if not url: return False, "Skipped"
    target_ext = ".mp4" if mode in ["Rename", "Convert"] else ".webm"
    final_path = os.path.join(folder, f"{filename}{target_ext}")
    
    if os.path.exists(final_path): return True, "Already Exists"

    try:
        temp_ext = ".webm"
        download_path = final_path if mode == "Rename" else os.path.join(folder, f"{filename}{temp_ext}")
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        dl_size = 0
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    dl_size += len(chunk)
                    if total_size > 0:
                        percent = min(100, int((dl_size / total_size) * 100))
                        progress_bar.progress(percent / 100, text=f"Downloading {filename}... {percent}%")
        
        if mode == "Convert":
            return convert_to_mp4(download_path, preset, status_text, progress_bar, filename)
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- UI INTERFACE ---

# Initialize Session State for Inputs and History
if 'history' not in st.session_state:
    st.session_state.history = []
if 'c_id_val' not in st.session_state:
    st.session_state.c_id_val = ""
if 'screen_url_val' not in st.session_state:
    st.session_state.screen_url_val = ""
if 'webcam_url_val' not in st.session_state:
    st.session_state.webcam_url_val = ""

st.title("🎥 Candidate Video Manager")
st.markdown("Paste candidate details below to download and process files instantly.")

# Folder Picker using Tkinter
if 'download_path' not in st.session_state:
    st.session_state.download_path = r"D:\City Bank_Downloads"

def select_folder():
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory(master=root)
        root.destroy()
        return path
    except:
        return None

with st.container(border=True):
    st.write("**Download Destination Folder**")
    col_path, col_browse = st.columns([5, 1])
    with col_path:
        target_dir = st.text_input("Destination Path", st.session_state.download_path, label_visibility="collapsed")
    with col_browse:
        if st.button("📁 Browse", use_container_width=True):
            selected_path = select_folder()
            if selected_path:
                st.session_state.download_path = selected_path
                st.rerun()

# Candidate Details
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        c_id = st.text_input("Candidate ID", placeholder="e.g. 1217", key="c_id_val")
    with col2:
        # Changed default to "Convert (.mp4)" by moving it to the first position
        mode = st.selectbox("Output Mode", ["Convert (.mp4)", "Original (.webm)", "Rename (.mp4)"])

    screen_url = st.text_input("Screen Record URL", placeholder="https://...", key="screen_url_val")
    webcam_url = st.text_input("Webcam Record URL", placeholder="https://...", key="webcam_url_val")

# Settings
if mode == "Convert (.mp4)":
    with st.expander("⚙️ Advanced Conversion Settings", expanded=True):
        st.info("""
        **FFmpeg Speed vs. Efficiency Guide:**
        - 🚀 **ultrafast (RECOMMENDED)**: Fastest processing, largest files.
        - ⚡ **superfast**: Very quick, slightly better compression.
        - ⚖️ **veryfast**: Balanced speed and file size.
        - 📁 **faster**: Best compression (smallest files), but slower processing.
        """)

        st.divider()
        preset = st.radio(
            "Select Conversion Speed",
            options=["ultrafast", "superfast", "veryfast", "faster"],
            index=0,
            horizontal=True,
            help="Ultrafast = ⚡ Speed | Faster = 📁 Smallest size"
        )
else:
    preset = "ultrafast"

# Action Buttons
btn_col1, btn_col2 = st.columns([3, 1])
with btn_col1:
    start_btn = st.button("🚀 Start Process", use_container_width=True, type="primary")
with btn_col2:
    if st.button("🧹 Clear All", use_container_width=True):
        st.session_state.c_id_val = ""
        st.session_state.screen_url_val = ""
        st.session_state.webcam_url_val = ""
        st.rerun()

if start_btn:
    if not c_id or (not screen_url and not webcam_url):
        st.error("Please provide at least a Candidate ID and one URL.")
    elif not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir)
        except:
            st.error("Invalid download folder. Please check permissions.")
    else:
        # Create candidate folder
        candidate_dir = os.path.join(target_dir, c_id)
        os.makedirs(candidate_dir, exist_ok=True)
        
        st.divider()
        st.info(f"Processing Candidate: **{c_id}**")
        
        # Process Screen
        p1 = st.progress(0, text="Waiting for Screen Record...")
        success1, msg1 = download_file(screen_url, candidate_dir, f"{c_id}_screenrecord", mode.split(' ')[0], preset, None, p1)
        if success1:
            st.success(f"Screen Record: {msg1}")
        else:
            st.error(f"Screen Record Error: {msg1}")

        # Process Webcam
        p2 = st.progress(0, text="Waiting for Webcam Record...")
        success2, msg2 = download_file(webcam_url, candidate_dir, f"{c_id}_webcam", mode.split(' ')[0], preset, None, p2)
        if success2:
            st.success(f"Webcam Record: {msg2}")
        else:
            st.error(f"Webcam Record Error: {msg2}")

        if success1 or success2:
            st.balloons()
            st.success("Candidate processing complete!")
            # Save to History (prepend to show latest first)
            history_item = {
                "Time": time.strftime("%H:%M:%S"),
                "Candidate ID": c_id,
                "Mode": mode,
                "Status": "✅ Success" if (success1 and success2) else "⚠️ Partial"
            }
            st.session_state.history.insert(0, history_item)

# Session History
if st.session_state.history:
    st.divider()
    st.subheader("📊 Session History")
    st.table(st.session_state.history)

st.sidebar.markdown("### Instructions")
st.sidebar.info("1. Enter Candidate ID\n2. Paste URLs\n3. Click Start")
st.sidebar.warning("Requires FFmpeg installed for 'Convert' mode.")
