"""
Excel Plans Importer - Import sales plans from Excel files to PostgreSQL
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config.settings import POSTGRES_CONFIG

# Product groups mapping (normalize names)
PRODUCT_GROUPS = {
    'ПЕРЧАТКИ': 'ПЕРЧАТКИ',
    'ОБЛИВ': 'ОБЛИВ',
    'ВАФЛЯ': 'ВАФЛЯ',
    'ВЕТОШЬ': 'ВЕТОШЬ',
    'МЕШКИ': 'МЕШКИ',
    'РУКАВИЦЫ': 'РУКАВИЦЫ',
    'КИТАЙСКИЕ ПЕРЧАТКИ': 'КИТАЙСКИЕ ПЕРЧАТКИ',
    'СТРЕЙЧ': 'СТРЕЙЧ',
    'МИКРОФИБРА': 'МИКРОФИБРА',
    'ЧИСТАЯ ЗВЕЗДА': 'ЧИСТАЯ ЗВЕЗДА',
    'ВАФЛЯ УЗБ': 'ВАФЛЯ УЗБ',
    'ХПП': 'ХПП',
    'ПРОЧЕЕ': 'ПРОЧЕЕ',
    'НАШ ТОВАР': 'НАШ ТОВАР',
    'ПЕРЕКУП': 'ПЕРЕКУП'
}

def parse_territories_plan(file_path, year, month):
    """
    Parse territories Excel file (wide format) to long format
    Returns: List of tuples (year, month, region, territory, product_group, metric_type, value)
    """
    print(f"Reading territories plan: {file_path}")
    
    # Read with header=None to handle multi-level headers manually
    df = pd.read_excel(file_path, sheet_name='Планы', header=None)
    
    # Identify structure
    # Row 0-1: Headers (product groups + metrics)
    # Row 2+: Data (region, territory, values...)
    
    # Start from row 2 (0-indexed)
    data_rows = []
    
    for idx in range(2, len(df)):
        row = df.iloc[idx]
        
        # First 2-3 columns are region/territory info
        region = row[0] if pd.notna(row[0]) else None
        territory = row[1] if pd.notna(row[1]) else None
        
        if not territory:
            continue  # Skip summary rows
        
        # Parse product group columns starting from column 2
        # Pattern: Each product group has 3 columns (Выручка, Кол-во, ГП)
        col_idx = 2
        
        for product_group in PRODUCT_GROUPS.keys():
            # Try to find this product group's columns
            # Columns are: Выручка, Кол-во, ГП (repeating pattern)
            
            if col_idx + 2 < len(row):
                revenue = row[col_idx] if pd.notna(row[col_idx]) else 0
                quantity = row[col_idx + 1] if pd.notna(row[col_idx + 1]) else 0
                gp = row[col_idx + 2] if pd.notna(row[col_idx + 2]) else 0
                
                if revenue or quantity or gp:
                    data_rows.append((year, month, region, territory, product_group, 'revenue', float(revenue) if revenue else 0))
                    data_rows.append((year, month, region, territory, product_group, 'quantity', float(quantity) if quantity else 0))
                    data_rows.append((year, month, region, territory, product_group, 'gp', float(gp) if gp else 0))
                
                col_idx += 3
    
    print(f"Parsed {len(data_rows)} territory plan records")
    return data_rows

def parse_warehouses_plan(file_path, year, month):
    """
    Parse warehouses Excel file (wide format) to long format
    Returns: List of tuples (year, month, region, warehouse, product_group, metric_type, value)
    """
    print(f"Reading warehouses plan: {file_path}")
    
    # Read the correct sheet
    df = pd.read_excel(file_path, sheet_name='Планы Январь 2026', header=None)
    
    # Row structure similar to territories
    # Row 0-2: Headers
    # Row 3+: Data
    
    data_rows = []
    
    for idx in range(3, len(df)):
        row = df.iloc[idx]
        
        # Column 0: Region or Warehouse name
        location = row[0] if pd.notna(row[0]) else None
        
        if not location or location == 'ИТОГО':
            continue
        
        # Determine if this is a region or warehouse
        # Warehouses typically have "Склад" prefix
        if 'Склад' in str(location):
            warehouse = location
            region = None  # Warehouses might not have explicit region in same row
        else:
            region = location
            warehouse = None
        
        # Parse product groups (similar pattern as territories)
        col_idx = 1
        
        for product_group in PRODUCT_GROUPS.keys():
            if col_idx + 2 < len(row):
                quantity = row[col_idx] if pd.notna(row[col_idx]) else 0
                revenue = row[col_idx + 1] if pd.notna(row[col_idx + 1]) else 0
                gp = row[col_idx + 2] if pd.notna(row[col_idx + 2]) else 0
                
                # For warehouses, use location as warehouse name
                target = warehouse if warehouse else location
                
                if revenue or quantity or gp:
                    data_rows.append((year, month, region, target, product_group, 'revenue', float(revenue) if revenue else 0))
                    data_rows.append((year, month, region, target, product_group, 'quantity', float(quantity) if quantity else 0))
                    data_rows.append((year, month, region, target, product_group, 'gp', float(gp) if gp else 0))
                
                col_idx += 3
    
    print(f"Parsed {len(data_rows)} warehouse plan records")
    return data_rows

def upsert_territories(conn, data_rows):
    """Insert territories plan data with UPSERT"""
    cur = conn.cursor()
    
    query = """
    INSERT INTO mart.excel_plans_territories 
        (year, month, region, territory, product_group, metric_type, plan_value)
    VALUES %s
    ON CONFLICT (year, month, region, territory, product_group, metric_type)
    DO UPDATE SET 
        plan_value = EXCLUDED.plan_value,
        created_at = NOW()
    """
    
    execute_values(cur, query, data_rows)
    conn.commit()
    print(f"✅ Inserted {len(data_rows)} territory plan records")

def upsert_warehouses(conn, data_rows):
    """Insert warehouses plan data with UPSERT"""
    cur = conn.cursor()
    
    query = """
    INSERT INTO mart.excel_plans_warehouses 
        (year, month, region, warehouse, product_group, metric_type, plan_value)
    VALUES %s
    ON CONFLICT (year, month, region, warehouse, product_group, metric_type)
    DO UPDATE SET 
        plan_value = EXCLUDED.plan_value,
        created_at = NOW()
    """
    
    execute_values(cur, query, data_rows)
    conn.commit()
    print(f"✅ Inserted {len(data_rows)} warehouse plan records")

def main():
    # File paths
    territories_file = "__pycache__/plans_territories.xlsx"
    warehouses_file = "__pycache__/plans_warehouses.xlsx"
    
    # Target period
    year = 2026
    month = 1
    
    print("=" * 80)
    print("EXCEL PLANS IMPORT")
    print("=" * 80)
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    
    try:
        # 1. Import Territories
        territories_data = parse_territories_plan(territories_file, year, month)
        upsert_territories(conn, territories_data)
        
        # 2. Import Warehouses
        warehouses_data = parse_warehouses_plan(warehouses_file, year, month)
        upsert_warehouses(conn, warehouses_data)
        
        # 3. Verify
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM mart.excel_plans_territories WHERE year=%s AND month=%s", (year, month))
        t_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM mart.excel_plans_warehouses WHERE year=%s AND month=%s", (year, month))
        w_count = cur.fetchone()[0]
        
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print(f"Territories: {t_count} records")
        print(f"Warehouses: {w_count} records")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
