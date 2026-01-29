"""
Excel Plans Inspector - Analyze structure of uploaded Excel files
"""
import pandas as pd
import sys

def inspect_territories_plan(file_path):
    """Inspect structure of territories plan file"""
    print("=" * 80)
    print("TERRITORIES PLAN INSPECTION")
    print("=" * 80)
    
    # Read Excel file
    xl = pd.ExcelFile(file_path)
    print(f"\nSheets found: {xl.sheet_names}")
    
    # Read first sheet
    df = pd.read_excel(file_path, sheet_name=0)
    
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\nColumns (first 20):")
    for i, col in enumerate(df.columns[:20]):
        print(f"  {i}: {col}")
    
    print(f"\nFirst 5 rows:")
    print(df.head())
    
    print(f"\nRegions found:")
    if 'РЕГИОН' in df.columns or df.columns[0].startswith('Unnamed'):
        # Column A might be unnamed if it's merged cells
        region_col = df.iloc[:, 0]  # First column
        regions = region_col.dropna().unique()
        for r in regions[:10]:
            print(f"  - {r}")
    
    return df

def inspect_warehouses_plan(file_path):
    """Inspect structure of warehouses plan file"""
    print("\n" + "=" * 80)
    print("WAREHOUSES PLAN INSPECTION")
    print("=" * 80)
    
    xl = pd.ExcelFile(file_path)
    print(f"\nSheets found: {xl.sheet_names}")
    
    # Look for "Планы Январь 2026" sheet
    target_sheet = None
    for sheet in xl.sheet_names:
        if 'январь' in sheet.lower() or 'jan' in sheet.lower():
            target_sheet = sheet
            break
    
    if not target_sheet:
        target_sheet = xl.sheet_names[0]
    
    print(f"\nReading sheet: '{target_sheet}'")
    df = pd.read_excel(file_path, sheet_name=target_sheet)
    
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\nColumns (first 20):")
    for i, col in enumerate(df.columns[:20]):
        print(f"  {i}: {col}")
    
    print(f"\nFirst 5 rows:")
    print(df.head())
    
    return df

if __name__ == "__main__":
    # Inspect both files
    territories_file = "__pycache__/plans_territories.xlsx"
    warehouses_file = "__pycache__/plans_warehouses.xlsx"
    
    try:
        df_territories = inspect_territories_plan(territories_file)
    except Exception as e:
        print(f"Error reading territories: {e}")
    
    try:
        df_warehouses = inspect_warehouses_plan(warehouses_file)
    except Exception as e:
        print(f"Error reading warehouses: {e}")
