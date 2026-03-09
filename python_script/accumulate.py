import pandas as pd
import os
import tkinter as tk
from tkinter import messagebox

def accumulate_excel_sheets():
    # Setup
    root = tk.Tk()
    root.withdraw()

    print("--- Simple Excel Accumulator ---")
    
    # Helper to convert "A" -> 0, "B" -> 1, etc.
    def col_to_idx(s):
        idx = 0
        for char in s.upper():
            idx = idx * 26 + (ord(char) - ord('A') + 1)
        return idx - 1

    # 1. Paths
    input_file = r"D:\CityBank_Audit\Fraud Monitoring & Review (2).xlsx"
    output_dir = r"D:\CityBank_Audit"

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    # Get User Input
    print("Example: D,A,C")
    user_cols_str = input("Enter column letters to accumulate (e.g., D,A,C): ").upper().replace(" ", "")
    if not user_cols_str:
        print("No columns entered.")
        return
    
    selected_letters = user_cols_str.split(",")
    col_indices = [col_to_idx(l) for l in selected_letters]

    try:
        print(f"Reading file: {os.path.basename(input_file)}")
        xls = pd.ExcelFile(input_file)
        sheet_names = xls.sheet_names
        
        all_data = []

        for sheet in sheet_names:
            print(f"Processing sheet: {sheet}...")
            # Read all columns first to allow reordering
            df = pd.read_excel(xls, sheet_name=sheet, skiprows=1, header=None)
            
            if df.empty:
                continue
                
            # Filter and Rearrange columns
            try:
                df = df.iloc[:, col_indices]
            except IndexError:
                print(f"Warning: Sheet '{sheet}' is missing columns. Skipping.")
                continue

            # Name columns based on letters
            df.columns = [f"Col {l}" for l in selected_letters]
            
            # Add Source Sheet name
            df.insert(0, 'Source Sheet', sheet)
            
            # Remove rows where all selected data columns are empty
            df = df.dropna(how='all', subset=df.columns[1:])
            
            all_data.append(df)

        if all_data:
            print("Merging...")
            master_df = pd.concat(all_data, ignore_index=True)

            # Final Save
            output_file = os.path.join(output_dir, "Master_Accumulated.xlsx")
            print(f"Saving to: {output_file}")
            master_df.to_excel(output_file, index=False)
            
            messagebox.showinfo("Success", "Done!")
            print("[DONE]")
        else:
            print("No data found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    accumulate_excel_sheets()
