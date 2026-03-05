import streamlit as st
import os
import requests
import subprocess
import time
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
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
    
    if os.path.exists(final_path): 
        if progress_bar: progress_bar.progress(1.0, text=f"{filename}: Already Downloaded")
        return True, "Already Exists"

    try:
        temp_ext = ".webm"
        download_path = final_path if mode == "Rename" else os.path.join(folder, f"{filename}{temp_ext}")
        
        # Cleanup partial/corrupted temp files from previous interrupted runs
        if os.path.exists(download_path):
            os.remove(download_path)
        
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

# Initialize Session State
if 'history' not in st.session_state:
    st.session_state.history = []
if 'download_path' not in st.session_state:
    st.session_state.download_path = ""

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

st.title("🎥 Candidate Video Manager")

# Folder Picker
with st.container(border=True):
    st.write("**Download Destination Folder**")
    col_path, col_browse = st.columns([5, 1])
    with col_path:
        target_dir = st.text_input("Destination Path", st.session_state.download_path, placeholder="Please select a folder...", label_visibility="collapsed")
    with col_browse:
        if st.button("📁 Browse", width="stretch"):
            selected_path = select_folder()
            if selected_path:
                st.session_state.download_path = selected_path
                st.rerun()

# Shared Settings (Mode & Preset)
with st.sidebar:
    st.header("Settings")
    mode = st.selectbox("Output Mode", ["Convert (.mp4)", "Original (.webm)", "Rename (.mp4)"])
    
    preset = "ultrafast"
    if mode == "Convert (.mp4)":
        preset = st.radio(
            "FFmpeg Preset",
            options=["ultrafast", "superfast", "veryfast", "faster"],
            index=0,
            help="Ultrafast = ⚡ Speed | Faster = 📁 Smallest size"
        )
    
    st.divider()
    st.header("⚡ Performance")
    num_workers = st.number_input("Parallel Workers", min_value=1, max_value=10, value=4, help="Number of files to process at once.")
    st.caption("💡 *Set 4 workers for safe performance*")

tab1, tab2 = st.tabs(["👤 Single Candidate", "📂 Bulk Upload (CSV/Excel)"])

with tab1:
    with st.container(border=True):
        c_id = st.text_input("Candidate ID", placeholder="e.g. 1217")
        screen_url = st.text_input("Screen Record URL", placeholder="https://...")
        webcam_url = st.text_input("Webcam Record URL", placeholder="https://...")
        
        if st.button("🚀 Start Single Process", type="primary"):
            if not target_dir:
                st.error("Please select a download destination folder first!")
            elif not c_id:
                st.error("Missing Candidate ID")
            else:
                candidate_dir = os.path.join(target_dir, c_id)
                os.makedirs(candidate_dir, exist_ok=True)
                
                # Process Screen
                p1 = st.progress(0, text="Waiting for Screen Record...")
                s1, m1 = download_file(screen_url, candidate_dir, f"{c_id}_screenrecord", mode.split(' ')[0], preset, None, p1)
                
                # Process Webcam
                p2 = st.progress(0, text="Waiting for Webcam Record...")
                s2, m2 = download_file(webcam_url, candidate_dir, f"{c_id}_webcam", mode.split(' ')[0], preset, None, p2)
                
                if s1 or s2:
                    st.balloons()
                    st.success("Complete!")
                    st.session_state.history.insert(0, {"Time": time.strftime("%H:%M:%S"), "ID": c_id, "Status": "Success"})

with tab2:
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Remove empty rows and handle duplicates in headers if any
            df = df.dropna(how='all')
            
            # Detect columns (flexible matching)
            cols = df.columns.tolist()
            id_col = next((c for c in cols if 'candidate_id' in str(c).lower()), None)
            screen_col = next((c for c in cols if 'screen_record_url' in str(c).lower()), None)
            webcam_col = next((c for c in cols if 'webcam_record_url' in str(c).lower()), None)
            
            if not id_col:
                st.error("Could not find 'candidate_id' column.")
            else:
                st.success(f"Found columns: ID({id_col}), Screen({screen_col}), Webcam({webcam_col})")
                
                if 'selected_df' not in st.session_state or st.session_state.get('last_uploaded') != uploaded_file.name:
                    temp_df = df.copy()
                    temp_df.insert(0, "Process", True)
                    st.session_state.selected_df = temp_df
                    st.session_state.last_uploaded = uploaded_file.name

                # Selection Header & Buttons
                col_head, col_mark1, col_mark2 = st.columns([5, 1.5, 1.5])
                with col_head:
                    st.subheader("📋 Candidate List")
                with col_mark1:
                    if st.button("Mark All", width="stretch", help="Select all candidates"):
                        st.session_state.selected_df["Process"] = True
                        st.rerun()
                with col_mark2:
                    if st.button("Unmark All", width="stretch", help="Deselect all candidates"):
                        st.session_state.selected_df["Process"] = False
                        st.rerun()

                edited_df = st.data_editor(st.session_state.selected_df, hide_index=True, width="stretch")
                st.session_state.selected_df = edited_df
                
                if st.button("🚀 Process Selected Candidates", type="primary"):
                    if not target_dir:
                        st.error("Please select a download destination folder first!")
                    else:
                        to_process = edited_df[edited_df["Process"] == True]
                    if to_process.empty:
                        st.warning("No candidates selected.")
                    else:
                        progress_container = st.container()
                        overall_bar = st.progress(0, text="Overall Progress")
                        
                        # Capture current context for all threads
                        ctx = get_script_run_ctx()

                        def single_file_task(url, folder, filename, mode_val, preset_val, bar_obj, context):
                            add_script_run_ctx(threading.current_thread(), context)
                            if url:
                                download_file(url, folder, filename, mode_val.split(' ')[0], preset_val, None, bar_obj)

                        # We use a shared pool for all tasks
                        with ThreadPoolExecutor(max_workers=num_workers) as executor:
                            futures = []
                            for idx, row in to_process.iterrows():
                                cid = str(row[id_col])
                                c_dir = os.path.join(target_dir, cid)
                                os.makedirs(c_dir, exist_ok=True)
                                
                                s_url = row[screen_col] if screen_col and pd.notna(row[screen_col]) else None
                                w_url = row[webcam_col] if webcam_col and pd.notna(row[webcam_col]) else None

                                # Create active UI slot for this candidate
                                with progress_container:
                                    slot = st.empty()
                                    with slot.container():
                                        st.write(f"⚙️ Processing: **{cid}**")
                                        col_p1, col_p2 = st.columns(2)
                                        with col_p1: b1 = st.progress(0, f"ID:{cid} Screen")
                                        with col_p2: b2 = st.progress(0, f"ID:{cid} Webcam")
                                
                                # File tasks (greedy: starts as soon as a worker is free)
                                if s_url:
                                    futures.append(executor.submit(single_file_task, s_url, c_dir, f"{cid}_screenrecord", mode, preset, b1, ctx))
                                if w_url:
                                    futures.append(executor.submit(single_file_task, w_url, c_dir, f"{cid}_webcam", mode, preset, b2, ctx))

                            # Track overall progress based on files
                            total_files = len(futures)
                            for i, future in enumerate(futures):
                                try:
                                    future.result()
                                except Exception as e:
                                    st.error(f"Worker Error: {e}")
                                overall_bar.progress((i + 1) / total_files, text=f"Overall Progress ({i+1}/{total_files} files)")

                        st.balloons()
                        st.success("Bulk processing complete!")

                        st.balloons()
                        st.success("Bulk processing complete!")
                        
                        # Generate Summary Report
                        st.divider()
                        st.subheader("📊 Bulk Process Summary")
                        
                        # Re-check existence to confirm status
                        summary_data = []
                        for _, row in to_process.iterrows():
                            cid = str(row[id_col])
                            c_dir = os.path.join(target_dir, cid)
                            
                            has_s = any(f.startswith(f"{cid}_screenrecord") for f in (os.listdir(c_dir) if os.path.exists(c_dir) else []))
                            has_w = any(f.startswith(f"{cid}_webcam") for f in (os.listdir(c_dir) if os.path.exists(c_dir) else []))
                            
                            status = "✅ Success" if (has_s and has_w) else "⚠️ Partial" if (has_s or has_w) else "❌ Failed"
                            summary_data.append({"Candidate ID": cid, "Status": status})
                        
                        sum_df = pd.DataFrame(summary_data)
                        col_s1, col_s2, col_s3 = st.columns(3)
                        col_s1.metric("Total", len(sum_df))
                        col_s2.metric("Success", len(sum_df[sum_df["Status"] == "✅ Success"]))
                        col_s3.metric("Failed/Partial", len(sum_df[sum_df["Status"] != "✅ Success"]))
                        
                        st.dataframe(sum_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error reading file: {e}")


# Session History
if st.session_state.history:
    st.divider()
    st.subheader("📊 Session History")
    st.table(st.session_state.history)

st.sidebar.markdown("### Instructions")
st.sidebar.info("1. Enter Candidate ID\n2. Paste URLs\n3. Click Start")
st.sidebar.warning("Requires FFmpeg installed for 'Convert' mode.")
