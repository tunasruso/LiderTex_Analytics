"""
Excel Plans Inspector v2 - Analyze exact column structure
"""
import pandas as pd

def inspect_territories_detailed():
    """Inspect territories Excel file structure in detail"""
    file_path = "__pycache__/plans_territories.xlsx"
    
    print("=" * 100)
    print("TERRITORIES PLAN - DETAILED COLUMN ANALYSIS")
    print("=" * 100)
    
    # Read raw Excel
    df = pd.read_excel(file_path, sheet_name='Планы', header=None)
    
    print(f"\nTotal Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    
    # Show first 5 rows completely
    print("\n" + "=" * 50)
    print("FIRST 10 ROWS (raw):")
    print("=" * 50)
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        print(f"\nRow {i}:")
        for col_idx in range(min(10, len(row))):
            val = row[col_idx]
            print(f"  Col {col_idx}: {repr(val)}")
    
    # Identify header rows
    print("\n" + "=" * 50)
    print("HEADER ANALYSIS (Rows 0-3):")
    print("=" * 50)
    for i in range(min(4, len(df))):
        row = df.iloc[i]
        # Show first 15 columns
        values = [str(row[j])[:20] if pd.notna(row[j]) else 'NaN' for j in range(min(15, len(row)))]
        print(f"Row {i}: {values}")
    
    # Show data rows with first 3 columns
    print("\n" + "=" * 50)
    print("DATA ROWS - First 3 columns (Rows 2-25):")
    print("=" * 50)
    for i in range(2, min(25, len(df))):
        row = df.iloc[i]
        col0 = row[0] if pd.notna(row[0]) else '-'
        col1 = row[1] if pd.notna(row[1]) else '-'
        col2 = row[2] if pd.notna(row[2]) else '-'
        print(f"Row {i}: [{col0}] | [{col1}] | [{col2}]")

if __name__ == "__main__":
    inspect_territories_detailed()
