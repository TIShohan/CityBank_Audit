import os
import subprocess
import logging
import threading
import time
import multiprocessing
import gc
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration
LOG_FILE = "conversion_log.txt"

# Windows Process Priority Constants
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

# Default ffmpeg settings (can be changed by user input)
FFMPEG_THREADS = "2"  # Limit threads per FFmpeg instance to reduce heat/contention
CRF_VALUE = "23"       # Default Quality (Lower is better, Higher is faster)
IS_ADMIN = False       # Admin mode for GPU acceleration
VIDEO_CODEC = "libx264" # Default CPU codec (fallback)
AVAILABLE_GPU = None   # Detected GPU type

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

def check_gpu_support():
    """Checks for available hardware encoders in FFmpeg."""
    try:
        # Check for NVIDIA (NVENC)
        nvenc = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        if "h264_nvenc" in nvenc.stdout:
            return "h264_nvenc", "NVIDIA (NVENC)"
        
        # Check for Intel (QuickSync)
        if "h264_qsv" in nvenc.stdout:
            return "h264_qsv", "Intel (QuickSync)"
            
        # Check for AMD (AMF)
        if "h264_amf" in nvenc.stdout:
            return "h264_amf", "AMD (AMF)"
            
        return "libx264", None
    except:
        return "libx264", None

def get_video_duration(input_path):
    """Retrieves duration of the video using ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0

def convert_to_mp4(input_path, output_path, pbar_idx=None):
    """
    Returns (success, message, duration_seconds)
    """
    start_time = time.time()
    temp_path = output_path + ".tmp"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. SKIP IF ALREADY FINISHED
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return True, "Already Finished (Skipped)", 0

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
        if IS_ADMIN and VIDEO_CODEC != "libx264":
            # GPU Accelerated Command
            # Note: Hardware encoders have slightly different quality flags
            if VIDEO_CODEC == "h264_nvenc":
                q_flag, q_val = "-cq", CRF_VALUE
            elif VIDEO_CODEC == "h264_qsv":
                q_flag, q_val = "-global_quality", CRF_VALUE
            else:
                q_flag, q_val = "-qp", CRF_VALUE # AMF fallback
                
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", VIDEO_CODEC, "-preset", "p1", q_flag, q_val, "-c:a", "aac",
                "-stats", "-progress", "pipe:1", "-f", "mp4", temp_path
            ]
        else:
            # Standard CPU Command
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-threads", FFMPEG_THREADS, 
                "-c:v", "libx264", "-crf", CRF_VALUE, "-preset", CONVERSION_PRESET, "-c:a", "aac",
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
            duration_spent = time.time() - start_time
            return True, f"Success ({duration_spent:.1f}s)", duration_spent
        else:
            if os.path.exists(temp_path): os.remove(temp_path)
            # Log the last few lines of error if available
            err_msg = "".join(error_output[-5:]).strip().replace("\n", " ")
            return False, f"FFmpeg Error/Empty Output: {err_msg if err_msg else 'Unknown crash'}", 0
            
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return False, f"Error: {e}", 0

def process_conversion_task(args):
    input_path, output_path, info = args
    pos = get_pos()
    try:
        success, msg, dur = convert_to_mp4(input_path, output_path, pbar_idx=pos)
        # Update log file after each conversion
        logging.info(f"{info} | {os.path.basename(input_path)} | {msg}")
        return success
    finally:
        release_pos(pos)
def main():
    # 0. Mode Selection
    print("--- CityBank Audit - Smooth Video Converter ---")
    print("\n[STEP 0] Select Mode:")
    print("[1] Standard User (Safe/CPU Mode)")
    print("[2] GPU User      (High Performance/Hardware Mode)")
    
    mode_choice = input("Select Option (1-2) [default 1]: ").strip()
    global IS_ADMIN, FFMPEG_THREADS, CONVERSION_PRESET, VIDEO_CODEC
    
    if mode_choice == "2":
        codec, gpu_name = check_gpu_support()
        if gpu_name:
            print(f"\n*** GPU USER MODE ENABLED: Using {gpu_name} Acceleration ***")
            VIDEO_CODEC = codec
            IS_ADMIN = True
        else:
            print("\n[WARNING] No compatible GPU detected. Falling back to High Performance CPU mode.")
            VIDEO_CODEC = "libx264"
            IS_ADMIN = True # Still allow high-performance CPU settings
    else:
        IS_ADMIN = False

    # 1. Path Decision (Easy for Non-Technical Users)
    
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
    output_root = os.path.join(base_dir, "ConvertedMP4")
    
    for root, dirs, files in os.walk(base_dir):
        # Skip the output folder if it already exists to avoid double scanning
        if "ConvertedMP4" in dirs:
            dirs.remove("ConvertedMP4")
            
        for f in files:
            if f.endswith(".webm"):
                webm_p = os.path.join(root, f)
                
                # Determine folder structure for output (preserving nesting)
                rel_path = os.path.relpath(root, base_dir)
                target_dir = os.path.join(output_root, rel_path)
                mp4_p = os.path.join(target_dir, f.replace(".webm", ".mp4"))
                
                # Pre-skip fully completed files
                if not os.path.exists(mp4_p):
                    tasks.append((webm_p, mp4_p, f"Folder: {rel_path}"))

    if not tasks:
        print("\nSuccess: All files are already converted to .mp4!")
        input("\nPress Enter to exit...")
        return

    print(f"Found {len(tasks)} files that need conversion.")

    # 4. CPU Power Configuration
    print("\n[STEP 2] CPU Power - How much of your computer's power to use?")
    print("[1] 50% Power (Standard - Recommended)")
    print("[2] 75% Power (Fast - PC will be warm)")
    print("[3] 90% Power (Turbo - Maximum speed)")
    print("[4] Custom    (Enter specific percentage, e.g., 80%)")
    
    config_choice = input("Select Option (1-4) [default 1]: ").strip()
    
    cpu_count = multiprocessing.cpu_count()
    
    if config_choice == "2":
        workers = max(1, int(cpu_count * 0.75))
    elif config_choice == "3":
        workers = max(1, int(cpu_count * 0.90))
        global FFMPEG_THREADS
        FFMPEG_THREADS = "4" # Allow more threads per file in Turbo mode
    elif config_choice == "4":
        try:
            val = input("Enter percentage (e.g. 80) or number of files: ").strip().replace("%", "")
            val_int = int(val)
            if val_int <= 100 and val_int > 0: # Treat as percentage
                workers = max(1, int(cpu_count * (val_int / 100)))
            else: # Treat as fixed number
                workers = max(1, val_int)
        except: workers = max(1, cpu_count // 2)
    else:
        workers = max(1, cpu_count // 2)

    # 5. Speed/Quality Decision (CRF)
    print("\n[STEP 3] Video Quality & Speed Decision:")
    print("[1] High Quality (CRF 20 - Slowest, Best Looking)")
    print("[2] Standard     (CRF 23 - Recommended Balance)")
    print("[3] Small File   (CRF 28 - Fastest, Lower Quality)")
    print("[4] Custom CRF   (Enter value 0-51, lower is better quality)")
    
    speed_choice = input("Select Option (1-4) [default 2]: ").strip()
    global CONVERSION_PRESET, CRF_VALUE
    CONVERSION_PRESET = "ultrafast" # Keep preset fast for maximum speed
    
    if speed_choice == "1":
        CRF_VALUE = "20"
    elif speed_choice == "3":
        CRF_VALUE = "28"
    elif speed_choice == "4":
        try:
            val = input("Enter CRF value (18-30 recommended): ").strip()
            CRF_VALUE = str(int(val))
        except: CRF_VALUE = "23"
    else:
        CRF_VALUE = "23"
    
    # 6. Cooldown Configuration
    print("\n[STEP 4] Cooldown Strategy (Batch Size):")
    print("[1] Aggressive (Pause every 10 files - Faster)")
    print("[2] Balanced   (Pause every 5 files - Recommended)")
    print("[3] Careful    (Pause every 2 files - Keeps PC very cool)")
    print("[4] Custom     (Enter specific number of files)")
    
    batch_choice = input("Select Option (1-4) [default 2]: ").strip()
    
    if batch_choice == "4":
        try:
            val = input("Enter number of files before each break: ").strip()
            batch_size = max(1, int(val))
        except: batch_size = 5
    else:
        batch_map = {"1": 10, "2": 5, "3": 2}
        batch_size = batch_map.get(batch_choice, 5)

    # 7. Rest Duration Configuration
    print("\n[STEP 5] Rest Duration (System Refresh Sleep):")
    print("[1] Short    (10 seconds - Minimum refresh)")
    print("[2] Balanced (30 seconds - Standard cooldown)")
    print("[3] Long     (60 seconds - Maximum cooling)")
    
    wait_choice = input("Select Option (1-3) [default 2]: ").strip()
    wait_map = {"1": 10, "2": 30, "3": 60}
    wait_time = wait_map.get(wait_choice, 30)

    print(f"\n--- READY TO START ---")
    print(f"-> Folders to Scan: {base_dir}")
    print(f"-> Files Found: {len(tasks)}")
    print(f"-> Strategy: Processing {workers} at a time, pausing for {wait_time}s every {batch_size} files.")
    input("\nPress Enter to Begin...")

    # For GPU User mode, we can handle more parallel files easily
    if IS_ADMIN:
        workers = min(workers * 2, multiprocessing.cpu_count()) 
        print(f"-> Performance: GPU User Mode boosted to {workers} parallel tasks.")

    # Initialize positions for progress bars
    global available_positions
    available_positions = list(range(1, workers + 1))

    # 8. Execute Parallel Tasks in Batches
    process_start_time = time.time()
    total_success = 0
    total_files = len(tasks)
    
    with tqdm(
        total=total_files, 
        desc="Total Conversion Progress", 
        position=0, 
        unit="file",
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
    ) as pbar:
        for i in range(0, total_files, batch_size):
            batch = tasks[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_conversion_task, t): t for t in batch}
                for f in as_completed(futures):
                    if f.result():
                        total_success += 1
                    pbar.update(1)
            
            # Cool down wait and Refresh Resources
            if i + batch_size < len(tasks):
                # Explicitly clear RAM/Memory
                gc.collect() 
                
                for remaining in range(wait_time, 0, -1):
                    pbar.set_description(f"Refreshing System & RAM... ({remaining}s)")
                    time.sleep(1)
                pbar.set_description("Total Conversion Progress")

    total_time = time.time() - process_start_time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)

    print(f"\n\n[DONE] Finished processing {total_files} files.")
    print(f"Total Time Taken: {minutes}m {seconds}s")
    print(f"Summary: {total_success} Successful, {total_files - total_success} Failed.")
    print(f"Original .webm files were KEPT.")
    print(f"Detailed logs added to: {LOG_FILE}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
