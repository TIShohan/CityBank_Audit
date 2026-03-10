import streamlit as st
import os
import requests
import subprocess
import time
import threading
import pandas as stats
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from tkinter import filedialog, Tk

# Page Configuration
st.set_page_config(page_title="Candidate Record Manager (Mac)", page_icon="🎥", layout="centered")

# --- CORE LOGIC ---

def get_video_duration(input_path):
    try:
        # On Mac, we assume ffprobe is in $PATH
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0

def convert_to_mp4(input_path, preset, status_text, progress_bar, filename):
    output_path = input_path.replace(".webm", ".mp4")
    duration = get_video_duration(input_path)
    
    try:
        # Cleanup any existing stale/broken MP4 before starting
        if os.path.exists(output_path):
            os.remove(output_path)

        cmd = ["ffmpeg", "-y", "-i", input_path, "-c:v", "libx264", "-crf", "23", "-preset", preset, "-c:a", "aac", "-progress", "pipe:1", output_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1)
        
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
        
        _, stderr_output = process.communicate()
        
        if process.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                if os.path.exists(input_path): os.remove(input_path)
                return True, "Done"
            else:
                if os.path.exists(output_path): os.remove(output_path)
                if os.path.exists(input_path): os.remove(input_path)
                return False, "Output file empty/corrupted"
        
        if os.path.exists(output_path): os.remove(output_path)
        if os.path.exists(input_path): os.remove(input_path)
        error_msg = stderr_output.split('\n')[-2] if stderr_output else "FFmpeg Crash"
        return False, f"FFmpeg Error: {error_msg}"
    except Exception as e:
        return False, str(e)

def download_file(url, folder, filename, mode, preset, status_text, progress_bar):
    if not url: return False, "Skipped"
    target_ext = ".mp4" if mode in ["Rename", "Convert"] else ".webm"
    final_path = os.path.join(folder, f"{filename}{target_ext}")
    
    if os.path.exists(final_path) and os.path.getsize(final_path) > 1000: 
        if progress_bar: progress_bar.progress(1.0, text=f"{filename}: Already Downloaded")
        return True, "Already Exists"

    try:
        temp_ext = ".webm"
        download_path = os.path.join(folder, f"{filename}{temp_ext}")
        
        if mode == "Convert" and os.path.exists(download_path):
            if progress_bar: progress_bar.progress(0.1, text=f"{filename}: Found WebM, resuming convert...")
            return convert_to_mp4(download_path, preset, status_text, progress_bar, filename)

        actual_dl_path = final_path if mode == "Rename" else download_path
        
        if os.path.exists(actual_dl_path) and mode != "Convert":
            os.remove(actual_dl_path)
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        dl_size = 0
        with open(actual_dl_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    dl_size += len(chunk)
                    if total_size > 0:
                        percent = min(100, int((dl_size / total_size) * 100))
                        progress_bar.progress(percent / 100, text=f"Downloading {filename}... {percent}%")
        
        if mode == "Convert":
            return convert_to_mp4(actual_dl_path, preset, status_text, progress_bar, filename)
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- UI INTERFACE ---

if 'download_path' not in st.session_state:
    st.session_state.download_path = ""

def select_folder():
    try:
        root = Tk()
        root.withdraw()
        # Bring to front for Mac specifically
        root.attributes('-topmost', True)
        root.lift() 
        path = filedialog.askdirectory(master=root)
        root.destroy()
        return path
    except:
        return None

st.title("🎥 Candidate Video Manager (Mac)")

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

with st.sidebar:
    st.header("Settings")
    mode = st.selectbox("Output Mode", ["Convert (.mp4)", "Original (.webm)", "Rename (.mp4)"])
    
    preset = "ultrafast"
    if mode == "Convert (.mp4)":
        preset = st.radio("FFmpeg Preset", options=["ultrafast", "superfast", "veryfast", "faster"], index=0)
    
    st.divider()
    st.header("⚡ Performance")
    num_workers = st.number_input("Parallel Workers", min_value=1, max_value=10, value=4)
    st.caption("💡 *Set 4 workers for safe performance*")

tab1, tab2 = st.tabs(["👤 Single Candidate", "📂 Bulk Upload (CSV/Excel)"])

with tab1:
    with st.container(border=True):
        c_id = st.text_input("Candidate ID", placeholder="e.g. 1217")
        screen_url = st.text_input("Screen Record URL")
        webcam_url = st.text_input("Webcam Record URL")
        
        if st.button("🚀 Start Single Process", type="primary"):
            if not target_dir:
                st.error("Please select a download destination folder first!")
            elif not c_id:
                st.error("Missing Candidate ID")
            else:
                candidate_dir = os.path.join(target_dir, c_id)
                os.makedirs(candidate_dir, exist_ok=True)
                p1 = st.progress(0, text="Waiting for Screen Record...")
                download_file(screen_url, candidate_dir, f"{c_id}_screenrecord", mode.split(' ')[0], preset, None, p1)
                p2 = st.progress(0, text="Waiting for Webcam Record...")
                download_file(webcam_url, candidate_dir, f"{c_id}_webcam", mode.split(' ')[0], preset, None, p2)
                st.success("Process Attempt Complete")

with tab2:
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            df = df.dropna(how='all')
            cols = df.columns.tolist()
            id_col = next((c for c in cols if 'candidate_id' in str(c).lower()), None)
            screen_col = next((c for c in cols if 'screen_record_url' in str(c).lower()), None)
            webcam_col = next((c for c in cols if 'webcam_record_url' in str(c).lower()), None)
            
            if not id_col:
                st.error("Could not find 'candidate_id' column.")
            else:
                if 'selected_df' not in st.session_state or st.session_state.get('last_uploaded') != uploaded_file.name:
                    temp_df = df.copy()
                    temp_df.insert(0, "Process", True)
                    st.session_state.selected_df = temp_df
                    st.session_state.last_uploaded = uploaded_file.name

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
                            ctx = get_script_run_ctx()

                            def single_file_task(url, folder, filename, mode_val, preset_val, bar_obj, context):
                                add_script_run_ctx(threading.current_thread(), context)
                                if url:
                                    download_file(url, folder, filename, mode_val.split(' ')[0], preset_val, None, bar_obj)

                            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                                futures = []
                                for idx, row in to_process.iterrows():
                                    cid = str(row[id_col])
                                    c_dir = os.path.join(target_dir, cid)
                                    os.makedirs(c_dir, exist_ok=True)
                                    s_url = row[screen_col] if screen_col and pd.notna(row[screen_col]) else None
                                    w_url = row[webcam_col] if webcam_col and pd.notna(row[webcam_col]) else None

                                    with progress_container:
                                        slot = st.empty()
                                        with slot.container():
                                            st.write(f"⚙️ Processing: **{cid}**")
                                            col_p1, col_p2 = st.columns(2)
                                            with col_p1: b1 = st.progress(0, f"ID:{cid} Screen")
                                            with col_p2: b2 = st.progress(0, f"ID:{cid} Webcam")
                                    
                                    if s_url: futures.append(executor.submit(single_file_task, s_url, c_dir, f"{cid}_screenrecord", mode, preset, b1, ctx))
                                    if w_url: futures.append(executor.submit(single_file_task, w_url, c_dir, f"{cid}_webcam", mode, preset, b2, ctx))

                                total_files = len(futures)
                                for i, future in enumerate(futures):
                                    future.result()
                                    overall_bar.progress((i + 1) / total_files, text=f"Overall Progress ({i+1}/{total_files} files)")

                            st.success("Bulk processing complete!")
                            
                            # Summary Report
                            st.divider()
                            st.subheader("📊 Bulk Process Summary")
                            summary_data = []
                            required_ext = ".mp4" if mode.startswith("Convert") or mode.startswith("Rename") else ".webm"
                            
                            for _, row in to_process.iterrows():
                                cid = str(row[id_col])
                                c_dir = os.path.join(target_dir, cid)
                                def is_file_healthy(f_name):
                                    p = os.path.join(c_dir, f_name)
                                    return os.path.exists(p) and os.path.getsize(p) > 1000
                                has_s = is_file_healthy(f"{cid}_screenrecord{required_ext}")
                                has_w = is_file_healthy(f"{cid}_webcam{required_ext}")
                                status = "✅ Success" if (has_s and has_w) else "⚠️ Partial" if (has_s or has_w) else "❌ Failed"
                                summary_data.append({"Candidate ID": cid, "Status": status})
                            
                            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error reading file: {e}")
