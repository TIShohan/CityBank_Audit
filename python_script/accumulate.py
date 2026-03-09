import pandas as pd
import os
import tkinter as tk
from tkinter import messagebox

def accumulate_excel_sheets():
    # Setup
    root = tk.Tk()
    root.withdraw()

    print("--- Simple Excel Accumulator ---")
    
    # 1. Paths
    input_file = r"D:\CityBank_Audit\Fraud Monitoring & Review (1).xlsx"
    output_dir = r"D:\CityBank_Audit"

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    try:
        print(f"Reading file: {os.path.basename(input_file)}")
        xls = pd.ExcelFile(input_file)
        sheet_names = xls.sheet_names
        
        all_data = []

        for sheet in sheet_names:
            print(f"Processing sheet: {sheet}...")
            # Read Column A and B exactly (indices 0 and 1)
            # We skip the header because you asked to skip the first row
            df = pd.read_excel(xls, sheet_name=sheet, usecols=[0, 1], skiprows=1, header=None)
            
            if df.empty:
                continue
                
            # Name the columns
            df.columns = ['Candidate ID', 'Is Cheater']
            
            # Add Source Sheet name
            df.insert(0, 'Source Sheet', sheet)
            
            # Remove rows where BOTH columns are empty
            df = df.dropna(how='all', subset=['Candidate ID', 'Is Cheater'])
            
            all_data.append(df)

        if all_data:
            print("Merging...")
            master_df = pd.concat(all_data, ignore_index=True)

            # Final Save
            output_file = os.path.join(output_dir, "Fraud Monitoring & Review (1)_Master_Accumulated.xlsx")
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
