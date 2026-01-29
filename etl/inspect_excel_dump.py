import pandas as pd
import os

def inspect_file(file_path, sheet_name):
    print(f"\n--- INSPECTING: {file_path} [{sheet_name}] ---")
    if not os.path.exists(file_path):
        print("❌ File not found!")
        return

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        print(f"Total rows: {len(df)}")
        print("First 50 rows (Column 0 and 1):")
        for idx, row in df.iterrows():
            if idx > 150: break # Inspect more rows to capture Moscow
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ''
            col1 = str(row[1]).strip() if pd.notna(row[1]) else ''
            print(f"Row {idx}: '{col0}' | '{col1}'")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    inspect_file("__pycache__/plans_territories.xlsx", "Планы")
    inspect_file("__pycache__/plans_warehouses.xlsx", "Планы Январь 2026")
