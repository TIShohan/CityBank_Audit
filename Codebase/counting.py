import os
import shutil

# Target directory
target_path = r"F:\City Bank Files\CityBank_Audit\python_script\downloads\3 March Not Distributed"

def count_files():
    if not os.path.exists(target_path):
        print(f"Error: Path not found: {target_path}")
        return

    # Print Header
    print(f"{'Folder Name':<50} | {'Total':<8} | {'MP4':<8} | {'WebM':<8}")
    print("-" * 80)

    # Iterate through folders (sorted numerically)
    folders = [f for f in os.listdir(target_path) if os.path.isdir(os.path.join(target_path, f))]
    folders.sort(key=lambda x: int(x) if x.isdigit() else x)

    folders_with_webm = []

    for folder in folders:
        folder_full_path = os.path.join(target_path, folder)
        files = os.listdir(folder_full_path)
        
        total_count = len(files)
        mp4_count = len([f for f in files if f.lower().endswith('.mp4')])
        webm_count = len([f for f in files if f.lower().endswith('.webm')])
        
        # Print row
        print(f"{folder:<50} | {total_count:<8} | {mp4_count:<8} | {webm_count:<8}")
        
        if webm_count > 0:
            folders_with_webm.append((folder, folder_full_path))

    # Deletion Prompt
    if folders_with_webm:
        print("\n" + "="*30)
        print(f"The following folders contain WebM files:")
        for name, _ in folders_with_webm:
            print(f"- {name}")
        
        print(f"\nTotal: {len(folders_with_webm)} folder(s).")
        confirm = input("Do you want to delete these folders? (yes/no): ").lower().strip()
        
        if confirm == 'yes':
            for name, path in folders_with_webm:
                try:
                    shutil.rmtree(path)
                    print(f"Deleted: {name}")
                except Exception as e:
                    print(f"Failed to delete {name}: {e}")
            print("Deletion complete.")
        else:
            print("Deletion cancelled.")
    else:
        print("\nNo folders with WebM files found.")

if __name__ == "__main__":
    count_files()
