import os
import pandas as pd
import numpy as np

# --- Defaults ---
input_csv = r"D:\CityBank_Audit\Blanksout Not Audited.csv"
emp_csv = r"D:\CityBank_Audit\Company_emp.csv"
output_dir = r"D:\CityBank_Audit\chunks"

def split_csv():
    # ... previous checks ...
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df = pd.read_csv(input_csv)
    total_rows = len(df)
    print(f"Total rows: {total_rows}")

    print("\nChoose splitting method:")
    print("1. Rows per file")
    print("2. Specific number of files")
    print("3. Split by number of employees (from Company_emp.csv)")
    choice = input("Enter choice (1, 2, or 3): ")

    names = []
    if os.path.exists(emp_csv):
        emp_df = pd.read_csv(emp_csv)
        names = emp_df['Employee Name'].dropna().tolist()

    if choice == '1':
        size = int(input("Enter rows per file: "))
        chunks = [df[i:i + size] for i in range(0, total_rows, size)]
    elif choice == '2':
        num = int(input("Enter number of files: "))
        chunks = np.array_split(df, num)
    elif choice == '3':
        if not names:
            print("Error: No employee names found in Company_emp.csv")
            return
        num = len(names)
        print(f"Dividing into {num} files based on employee count.")
        chunks = np.array_split(df, num)
    else:
        return

    # Naming Setup
    print("\nChoose naming system:")
    print("1. Simple Serial (1.csv, 2.csv...)")
    print("2. Employee names with index (1_Tanvir Ahmed.csv, 2_Rashedul Islam.csv...)")
    name_choice = input("Enter choice (1 or 2): ")
    
    # Save chunks
    for i, chunk in enumerate(chunks):
        if name_choice == '2' and i < len(names):
            filename = f"{i + 1}_{names[i]}.csv"
        else:
            filename = f"{i + 1}.csv"
            
        output_file = os.path.join(output_dir, filename)
        chunk.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")

    print(f"\nCreated {len(chunks)} files in {output_dir}")

if __name__ == "__main__":
    split_csv()
