import os
import pandas as pd
import requests
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration
CSV_PATH = r"D:\CityBank_Audit\new.csv"
BASE_DOWNLOAD_DIR = r"D:\Distribution Folder for citybank"
LOG_FILE = r"D:\Distribution Folder for citybank\download_only_log.txt"

# Dynamic Position Manager for Progress Bars
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

def download_file(url, folder, filename, pbar_idx=None, candidate_id=""):
    if not url or pd.isna(url): return False, "Empty URL"
    final_path = os.path.join(folder, f"{filename}.webm")
    
    local_size = os.path.getsize(final_path) if os.path.exists(final_path) else 0
    
    try:
        # 1. Get total size from server
        head = requests.head(url, timeout=30, allow_redirects=True)
        total_size = int(head.headers.get('content-length', 0))
        
        # 2. Check if already complete
        if local_size >= total_size and total_size > 0:
            return True, "Already Complete"

        # 3. Prepare headers for resume
        headers = {}
        if local_size > 0:
            headers['Range'] = f"bytes={local_size}-"
            mode = 'ab' # Append binary
        else:
            mode = 'wb' # Write binary

        # 4. Start Download
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # If server doesn't support range (returns 200 instead of 206), restart download
        if response.status_code == 200 and local_size > 0:
            mode = 'wb'
            local_size = 0
            
        with tqdm(desc=f"[ID: {candidate_id}] {filename}", 
                  total=total_size, 
                  initial=local_size,
                  unit='B', unit_scale=True, leave=False, 
                  position=pbar_idx) as bar:
            
            with open(final_path, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        
        return True, "Success"
    except Exception as e:
        return False, f"Error: {str(e)}"

def process_file_task(args):
    url, folder, filename, info, c_id = args
    pos = get_pos()
    try:
        success, msg = download_file(url, folder, filename, pbar_idx=pos, candidate_id=c_id)
        logging.info(f"{info} | {filename} | {msg}")
        return success
    finally:
        release_pos(pos)

def main():
    if not os.path.exists(BASE_DOWNLOAD_DIR): os.makedirs(BASE_DOWNLOAD_DIR)
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print(f"Reading CSV from: {CSV_PATH}")
    try:
        df = pd.read_csv(CSV_PATH)
        data = df[['candidate_id', 'candidate_name', 'screen_record_url', 'webcam_record_url']].copy()
    except Exception as e:
        print(f"Error: {e}")
        return

    # Configuration Input
    try:
        qty_input = input(f"\nHow many candidates? (1-{len(data)} or 'all'): ").strip().lower()
        qty = len(data) if qty_input == 'all' else min(int(qty_input), len(data))
    except: qty = 1

    try:
        worker_input = input("How many workers (1-10) [default 5]: ").strip()
        max_workers = int(worker_input) if worker_input else 5
    except: max_workers = 5

    # Initialize positions for progress bars
    global available_positions
    available_positions = list(range(1, max_workers + 1))

    subset = data.head(qty)
    file_tasks = []
    for _, row in subset.iterrows():
        c_id = str(row['candidate_id'])
        c_dir = os.path.join(BASE_DOWNLOAD_DIR, c_id)
        os.makedirs(c_dir, exist_ok=True)
        info = f"ID: {c_id} ({row['candidate_name']})"
        file_tasks.append((row['screen_record_url'], c_dir, f"{c_id}_screenrecord", info, c_id))
        file_tasks.append((row['webcam_record_url'], c_dir, f"{c_id}_webcam", info, c_id))

    print(f"\nProcessing {len(file_tasks)} files for {qty} candidates using {max_workers} workers...")
    print("Resume logic is ACTIVE. Partially downloaded files will be resumed.\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file_task, task): task for task in file_tasks}
        with tqdm(total=len(file_tasks), desc="Overall Progress", position=0) as overall_bar:
            for future in as_completed(futures):
                future.result()
                overall_bar.update(1)

    print(f"\n\nDone. Check logs: {LOG_FILE}")

if __name__ == "__main__":
    main()
