import os
import pandas as pd
import requests
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration
CSV_PATH = r"d:\City Bank_Recruitment\candidate_score_report - Filtered Blanksout Final.csv"
BASE_DOWNLOAD_DIR = r"d:\City Bank_Recruitment\python_script\downloads"
LOG_FILE = r"d:\City Bank_Recruitment\python_script\download_log.txt"
MAX_WORKERS = 10  # Process 10 files simultaneously

# Global settings
DOWNLOAD_MODE = "original" 
CONVERSION_PRESET = "ultrafast"

# Position Manager for Bars
available_positions = list(range(1, MAX_WORKERS + 1))
pos_lock = threading.Lock()

def get_pos():
    with pos_lock:
        return available_positions.pop(0) if available_positions else None

def release_pos(pos):
    with pos_lock:
        if pos is not None:
            available_positions.insert(0, pos)
            available_positions.sort()

def is_candidate_complete(candidate_id, mode):
    """Verifies that both recordings exist based on chosen mode."""
    candidate_dir = os.path.join(BASE_DOWNLOAD_DIR, str(candidate_id))
    if not os.path.exists(candidate_dir):
        return False
    
    files = os.listdir(candidate_dir)
    ext_pattern = ".mp4" if mode in ["rename", "convert"] else ".webm"
    
    screen_exists = any(f.startswith(f"{candidate_id}_screenrecord") and f.endswith(ext_pattern) and os.path.getsize(os.path.join(candidate_dir, f)) > 0 for f in files)
    webcam_exists = any(f.startswith(f"{candidate_id}_webcam") and f.endswith(ext_pattern) and os.path.getsize(os.path.join(candidate_dir, f)) > 0 for f in files)
    
    return screen_exists and webcam_exists

def get_video_duration(input_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0

def convert_to_mp4(input_path, pbar_idx=None, candidate_id=""):
    """Converts webm to mp4 with fallback for missing duration."""
    output_path = input_path.replace(".webm", ".mp4")
    duration = get_video_duration(input_path)
    filename = os.path.basename(input_path).replace(".webm", "")
    
    # If duration is missing, we use an indeterminate bar or time-based bar
    is_percent = duration > 0
    total_val = 100 if is_percent else None
    unit = "%" if is_percent else "s"

    try:
        # Increase stats reporting frequency
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx264", "-crf", "23", "-preset", CONVERSION_PRESET, "-c:a", "aac",
            "-stats", "-progress", "pipe:1", output_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, bufsize=1)
        
        with tqdm(
            desc=f"[ID: {candidate_id}] {filename} (CONV)",
            total=total_val,
            unit=unit,
            leave=False,
            position=pbar_idx,
            bar_format='{desc}: {n_fmt}{unit} |{bar}| {rate_fmt}' if not is_percent else None
        ) as bar:
            last_val = 0
            for line in process.stdout:
                if "out_time_ms=" in line or "out_time_us=" in line:
                    try:
                        raw_val = int(line.split('=')[1].strip())
                        time_sec = raw_val / 1_000_000
                        
                        if is_percent:
                            progress = (time_sec / duration) * 100
                            inc = progress - last_val
                            if inc > 0:
                                bar.update(inc)
                                last_val = progress
                        else:
                            # If no duration, just show seconds elapsed
                            inc = time_sec - last_val
                            if inc > 0:
                                bar.update(inc)
                                last_val = time_sec
                    except: pass
            
            process.wait()
            # Mark as done
            if is_percent and process.returncode == 0:
                bar.n = 100
                bar.refresh()

        if process.returncode == 0:
            if os.path.exists(input_path): os.remove(input_path)
            return True, "Converted"
        return False, "FFmpeg failed"
    except Exception as e:
        return False, f"Convert Error: {e}"

def get_existing_file(candidate_id, filename_base):
    candidate_dir = os.path.join(BASE_DOWNLOAD_DIR, str(candidate_id))
    if not os.path.exists(candidate_dir): return None
    for f in os.listdir(candidate_dir):
        if f.startswith(filename_base) and os.path.getsize(os.path.join(candidate_dir, f)) > 0:
            return os.path.join(candidate_dir, f)
    return None

def download_file(url, folder, filename, mode, pbar_idx=None, candidate_id=""):
    if not url or pd.isna(url): return False, "Empty URL"
    target_ext = ".mp4" if mode in ["rename", "convert"] else ".webm"
    final_path = os.path.join(folder, f"{filename}{target_ext}")
    
    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
        return True, "Already Exists"

    existing_local = get_existing_file(os.path.basename(folder), filename)
    if existing_local:
        if mode == "rename":
            os.rename(existing_local, final_path)
            return True, "Renamed Local"
        elif mode == "convert":
            return convert_to_mp4(existing_local, pbar_idx=pbar_idx, candidate_id=candidate_id)
        elif mode == "original" and existing_local.endswith(".mp4"):
            return True, "Skipped (MP4 Exists)"

    try:
        temp_ext = ".webm"
        download_path = final_path if mode == "rename" else os.path.join(folder, f"{filename}{temp_ext}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with tqdm(desc=f"[ID: {candidate_id}] {filename}", total=total_size, unit='B', unit_scale=True, leave=False, position=pbar_idx) as bar:
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        
        if mode == "convert":
            return convert_to_mp4(download_path, pbar_idx=pbar_idx, candidate_id=candidate_id)
        return True, "Success"
    except Exception as e:
        return False, str(e)

def process_file_task(args):
    url, folder, filename, mode, info, c_id = args
    pos = get_pos()
    try:
        success, msg = download_file(url, folder, filename, mode, pbar_idx=pos, candidate_id=c_id)
        logging.info(f"{info} | {filename} | {msg}")
        return success
    finally:
        release_pos(pos)

def main():
    global DOWNLOAD_MODE
    if not os.path.exists(BASE_DOWNLOAD_DIR): os.makedirs(BASE_DOWNLOAD_DIR)
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print(f"Reading CSV from: {CSV_PATH}")
    try:
        df = pd.read_csv(CSV_PATH)
        data = df[['candidate_id', 'candidate_name', 'screen_record_url', 'webcam_record_url']].copy()
    except Exception as e:
        print(f"Error: {e}")
        return

    print("\nFormat Options: [1] Original [2] Rename [3] Convert")
    choice = input("Select: ").strip()
    DOWNLOAD_MODE = "rename" if choice == "2" else "convert" if choice == "3" else "original"
    
    if DOWNLOAD_MODE == "convert":
        try: 
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("\nPreset Options (Quality is always high):")
            print("[1] Ultrafast (Max Speed, Larger Files)")
            print("[2] Veryfast  (Balanced Speed/Size)")
            print("[3] Faster    (Slower, Smaller Files)")
            p_choice = input("Select Preset (1-3) [default 1]: ").strip()
            global CONVERSION_PRESET
            CONVERSION_PRESET = "veryfast" if p_choice == "2" else "faster" if p_choice == "3" else "ultrafast"
            print(f"Using Preset: {CONVERSION_PRESET.upper()}")
        except: 
            DOWNLOAD_MODE = "original"
            print("FFmpeg not found. Using Original.")

    print("\nChecking for missing files...")
    pending_mask = data['candidate_id'].apply(lambda x: not is_candidate_complete(x, DOWNLOAD_MODE))
    pending_data = data[pending_mask]
    
    if len(pending_data) == 0:
        print("Everything is complete.")
        return

    try:
        qty_input = input(f"\nHow many candidates? (1-{len(pending_data)} or 'all'): ").strip().lower()
        qty = len(pending_data) if qty_input == 'all' else min(int(qty_input), len(pending_data))
    except: qty = 1

    subset = pending_data.head(qty)
    file_tasks = []
    for _, row in subset.iterrows():
        c_id = str(row['candidate_id'])
        c_dir = os.path.join(BASE_DOWNLOAD_DIR, c_id)
        os.makedirs(c_dir, exist_ok=True)
        info = f"ID: {c_id} ({row['candidate_name']})"
        file_tasks.append((row['screen_record_url'], c_dir, f"{c_id}_screenrecord", DOWNLOAD_MODE, info, c_id))
        file_tasks.append((row['webcam_record_url'], c_dir, f"{c_id}_webcam", DOWNLOAD_MODE, info, c_id))

    print(f"\nProcessing {len(file_tasks)} files for {qty} candidates using {MAX_WORKERS} workers...\n")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_file_task, task): task for task in file_tasks}
        with tqdm(total=len(file_tasks), desc="Overall File Progress", position=0) as overall_bar:
            for future in as_completed(futures):
                future.result()
                overall_bar.update(1)

    print(f"\n\nDone. Check logs: {LOG_FILE}")

if __name__ == "__main__":
    main()
