import os
import subprocess
import logging
import threading
import time
import multiprocessing
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration
LOG_FILE = "conversion_log.txt"

# Windows Process Priority Constants
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

# Default ffmpeg settings (can be changed by user input)
CONVERSION_PRESET = "ultrafast"
FFMPEG_THREADS = "2"  # Limit threads per FFmpeg instance to reduce heat/contention

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
            "-threads", FFMPEG_THREADS, # Limit CPU threads to reduce heat
            "-c:v", "libx264", "-crf", "23", "-preset", CONVERSION_PRESET, "-c:a", "aac",
            "-stats", "-progress", "pipe:1", "-f", "mp4", temp_path
        ]
        
        # Use BELOW_NORMAL_PRIORITY_CLASS so the PC stays responsive during high CPU usage
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True, 
            bufsize=1,
            creationflags=BELOW_NORMAL_PRIORITY_CLASS
        )
        
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

        if process.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            # ATOMIC MOVE: Successfully converted, rename temp to final
            os.rename(temp_path, output_path)
            return True, "Success"
        else:
            if os.path.exists(temp_path): os.remove(temp_path)
            # Log the last few lines of error if available
            err_msg = "".join(error_output[-5:]).strip().replace("\n", " ")
            return False, f"FFmpeg Error/Empty Output: {err_msg if err_msg else 'Unknown crash'}"
            
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
    # 1. Path Decision (Easy for Non-Technical Users)
    print("--- CityBank Audit - Smooth Video Converter ---")
    
    # Create a hidden Tkinter window to show the folder picker
    root_tk = tk.Tk()
    root_tk.withdraw()
    root_tk.attributes("-topmost", True)
    
    print("\n[STEP 1] Select the folder containing your videos.")
    base_dir = filedialog.askdirectory(title="Select Top level Folder containing Candidate Folders")
    root_tk.destroy()

    if not base_dir:
        print("\n[ERROR] No folder selected. Exiting...")
        return
        
    print(f"Selected: {base_dir}")

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

    # 4. Simple Configuration
    print("\n[STEP 2] How would you like to run?")
    print("[1] Fast   (Recommended - Uses 50% of your computer's power)")
    print("[2] Smooth (Safer - Keeps your computer very cool)")
    print("[3] Custom (Enter specific number)")
    
    config_choice = input("Select Option (1-3) [default 1]: ").strip()
    
    suggested_workers = max(1, multiprocessing.cpu_count() // 2)
    if config_choice == "2":
        workers = 1
        global FFMPEG_THREADS
        FFMPEG_THREADS = "1"
    elif config_choice == "3":
        try:
            workers_in = input(f"Enter number of files to process at once: ").strip()
            workers = int(workers_in) if workers_in else suggested_workers
        except: workers = suggested_workers
    else:
        workers = suggested_workers

    # 5. Speed Decision (Simplified)
    print("\n[STEP 3] Video Quality Decision:")
    print("[1] Standard  (Normal quality - Small files)")
    print("[2] High      (Best looking - Larger files)")
    
    speed_choice = input("Select Option (1-2) [default 1]: ").strip()
    global CONVERSION_PRESET
    CONVERSION_PRESET = "ultrafast" if speed_choice == "1" else "medium"
    
    # 6. Cooldown Configuration
    print("\n[STEP 4] Cooldown Strategy:")
    print("[1] Aggressive (Pause every 10 files - Faster)")
    print("[2] Balanced   (Pause every 5 files - Recommended)")
    print("[3] Careful    (Pause every 2 files - Keeps PC very cool)")
    
    batch_choice = input("Select Option (1-3) [default 2]: ").strip()
    batch_map = {"1": 10, "2": 5, "3": 2}
    batch_size = batch_map.get(batch_choice, 5)

    print(f"\n--- READY TO START ---")
    print(f"-> Folders to Scan: {base_dir}")
    print(f"-> Files Found: {len(tasks)}")
    print(f"-> Strategy: Processing {workers} at a time, pausing every {batch_size} files.")
    input("\nPress Enter to Begin...")

    # Initialize positions for progress bars
    global available_positions
    available_positions = list(range(1, workers + 1))

    # 7. Execute Parallel Tasks in Batches
    wait_time = 10
    total_success = 0
    total_files = len(tasks)
    
    with tqdm(total=total_files, desc="Total Conversion Progress", position=0) as pbar:
        for i in range(0, total_files, batch_size):
            batch = tasks[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_conversion_task, t): t for t in batch}
                for f in as_completed(futures):
                    if f.result():
                        total_success += 1
                    pbar.update(1)
            
            # Cool down wait if not the last batch
            if i + batch_size < len(tasks):
                for remaining in range(wait_time, 0, -1):
                    pbar.set_description(f"Cooling Down... ({remaining}s)")
                    time.sleep(1)
                pbar.set_description("Total Conversion Progress")

    print(f"\n\n[DONE] Finished processing {total_files} files.")
    print(f"Summary: {total_success} Successful, {total_files - total_success} Failed.")
    print(f"Original .webm files were KEPT.")
    print(f"Detailed logs added to: {LOG_FILE}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
