import os
import subprocess
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration
LOG_FILE = "conversion_log.txt"

# Default ffmpeg settings (can be changed by user input)
CONVERSION_PRESET = "ultrafast"

# Position Manager for Parallel Bars
pos_lock = threading.Lock()
available_positions = []

def get_pos():
    with pos_lock:
        return available_positions.pop(0) if available_positions else None

def release_pos(pos):
    with pos_lock:
        if pos is not None:
            available_positions.append(pos)
            available_positions.sort()

def get_video_duration(input_path):
    """Retrieves duration of the video using ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0

def convert_to_mp4(input_path, pbar_idx=None):
    """
    Converts webm to mp4 robustly:
    - Skips already finished files.
    - Uses .tmp while converting to prevent corruption if interrupted.
    - Cleans up old temp files.
    """
    output_path = input_path.replace(".webm", ".mp4")
    temp_path = output_path + ".tmp"
    
    # 1. SKIP IF ALREADY FINISHED
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return True, "Already Finished (Skipped)"

    # 2. CLEANUP OLD TEMP FILE (from previous interruption)
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except: pass

    duration = get_video_duration(input_path)
    filename = os.path.basename(input_path)
    
    # Check if duration is valid for progress bar
    is_percent = duration > 0
    total_val = 100 if is_percent else None
    unit = "%" if is_percent else "s"

    try:
        # FFMPEG Command
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx264", "-crf", "23", "-preset", CONVERSION_PRESET, "-c:a", "aac",
            "-stats", "-progress", "pipe:1", "-f", "mp4", temp_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1)
        
        # We need a way to collect stderr if it fails
        error_output = []
        def capture_stderr():
            for err_line in process.stderr:
                error_output.append(err_line)

        stderr_thread = threading.Thread(target=capture_stderr)
        stderr_thread.start()

        with tqdm(
            desc=f"{filename}",
            total=total_val,
            unit=unit,
            leave=False,
            position=pbar_idx,
            bar_format='{desc}: {n_fmt}{unit} |{bar}| {rate_fmt}' if not is_percent else None
        ) as bar:
            last_val = 0
            for line in process.stdout:
                if "out_time_ms=" in line:
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
                            inc = time_sec - last_val
                            if inc > 0:
                                bar.update(inc)
                                last_val = time_sec
                    except: pass
            
            process.wait()
            stderr_thread.join()
            if is_percent and process.returncode == 0:
                bar.n = 100
                bar.refresh()

        if process.returncode == 0:
            # ATOMIC MOVE: Successfully converted, rename temp to final
            os.rename(temp_path, output_path)
            return True, "Success"
        else:
            if os.path.exists(temp_path): os.remove(temp_path)
            # Log the last few lines of error if available
            err_msg = "".join(error_output[-5:]).strip().replace("\n", " ")
            return False, f"FFmpeg Error: {err_msg if err_msg else 'Unknown crash'}"
            
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return False, f"Error: {e}"

def process_conversion_task(args):
    input_path, info = args
    pos = get_pos()
    try:
        success, msg = convert_to_mp4(input_path, pbar_idx=pos)
        # Update log file after each conversion
        logging.info(f"{info} | {os.path.basename(input_path)} | {msg}")
        return success
    finally:
        release_pos(pos)

def main():
    # 1. Path Decision
    default_dir = r"D:\Distribution Folder for citybank"
    print("--- CityBank Audit Only Converter ---")
    base_dir = input(f"Enter the Main Folder path contains candidate IDs [{default_dir}]: ").strip() or default_dir
    
    if not os.path.exists(base_dir):
        print(f"\n[ERROR] Path '{base_dir}' does not exist.")
        return

    # 2. Setup Logging
    log_path = os.path.join(base_dir, LOG_FILE)
    logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 3. Scan for .webm Recursively
    print(f"\nScanning for .webm files in subfolders...")
    tasks = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".webm"):
                webm_p = os.path.join(root, f)
                mp4_p = webm_p.replace(".webm", ".mp4")
                # Pre-skip fully completed files
                if not os.path.exists(mp4_p):
                    tasks.append((webm_p, f"Folder: {os.path.basename(root)}"))

    if not tasks:
        print("\nSuccess: All files are already converted to .mp4!")
        input("\nPress Enter to exit...")
        return

    print(f"Found {len(tasks)} files that need conversion.")

    # 4. User Configuration (Parallel Speed)
    try:
        workers_in = input("How many files to convert at once (Parallel Workers, e.g., 2, 4) [default 2]: ").strip()
        workers = int(workers_in) if workers_in else 2
    except: workers = 2

    # 5. User Configuration (FFmpeg Speed)
    print("\nSelect Conversion Speed Decision (How fast it should be?):")
    print("[1] Ultrafast (Maximum Speed - Recommended for local PC)")
    print("[2] Superfast (Very Fast)")
    print("[3] Veryfast  (Fast)")
    print("[4] Fast      (Balanced)")
    print("[5] Slower    (Best Quality/Smallest File Size)")
    
    speed_map = {"1": "ultrafast", "2": "superfast", "3": "veryfast", "4": "fast", "5": "slower"}
    choice = input("Select Option (1-5) [default 1]: ").strip()
    global CONVERSION_PRESET
    CONVERSION_PRESET = speed_map.get(choice, "ultrafast")
    
    print(f"\nStarting conversion using {workers} workers with {CONVERSION_PRESET.upper()} preset...")

    # Initialize positions for progress bars
    global available_positions
    available_positions = list(range(1, workers + 1))

    # 6. Execute Parallel Tasks
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_conversion_task, t): t for t in tasks}
        with tqdm(total=len(tasks), desc="Total Conversion Progress", position=0) as pbar:
            for f in as_completed(futures):
                f.result()
                pbar.update(1)

    print(f"\n\n[DONE] All files processed. Original .webm files were KEPT.")
    print(f"Update logs added to: {LOG_FILE}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
