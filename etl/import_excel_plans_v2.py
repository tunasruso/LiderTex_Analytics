"""
Excel Plans Importer v2 - Fixed to correctly parse Region, Territory, Manager
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config.settings import POSTGRES_CONFIG

# Product groups mapping
PRODUCT_GROUPS = [
    'ПЕРЧАТКИ', 'ОБЛИВ', 'ВАФЛЯ', 'ВЕТОШЬ', 'МЕШКИ', 'РУКАВИЦЫ',
    'КИТАЙСКИЕ ПЕРЧАТКИ', 'СТРЕЙЧ', 'МИКРОФИБРА', 'ЧИСТАЯ ЗВЕЗДА',
    'ВАФЛЯ УЗБ', 'ХПП', 'ПРОЧЕЕ', 'НАШ ТОВАР', 'ПЕРЕКУП'
]

# Known regions (uppercase names in column 0)
KNOWN_REGIONS = [
    'МОСКВА', 'ПОВОЛЖЬЕ', 'СЕВЕРО-ЗАПАД', 'СИБИРЬ-УРАЛ', 'ЦЕНТР', 'ЮГ',
    'ОТДЕЛ КОРПОРАТИВНЫХ ПРОДАЖ'
]

def parse_territories_plan_v2(file_path, year, month):
    """
    Parse territories Excel file with correct structure:
    - Column 0: Territory (or Region for summary row)
    - Column 1: Manager/ФИО
    - Column 2: % доля
    - Columns 3+: Product groups × 3 metrics (Выручка, Кол-во, ГП)
    
    Returns: List of tuples (year, month, region, territory, manager, product_group, metric_type, value)
    """
    print(f"Reading territories plan v2: {file_path}")
    
    df = pd.read_excel(file_path, sheet_name='Планы', header=None)
    
    data_rows = []
    current_region = None
    
    # Start from row 3 (data rows)
    for idx in range(3, len(df)):
        row = df.iloc[idx]
        
        col0 = str(row[0]).strip() if pd.notna(row[0]) else ''
        col1 = str(row[1]).strip() if pd.notna(row[1]) else ''
        
        if not col0 and not col1:
            continue  # Skip empty rows
        
        # Check if this is a region header row (uppercase name)
        # BUG FIX: Ensure strict uppercase to avoid matching territories like "Юг" as regions
        is_region_header = col0 in KNOWN_REGIONS or (col0.isupper() and len(col0) > 2)
        
        if is_region_header:
            current_region = col0.upper()
            # Skip region summary rows - we only want territories
            continue
        
        # This is a territory row
        territory = col0
        manager = col1
        
        if not territory:
            continue
        
        # Parse product groups - starting from column 3
        # Structure: each product group has 3 columns (Выручка, Кол-во, ГП)
        col_idx = 3
        
        for pg_idx, product_group in enumerate(PRODUCT_GROUPS):
            base_col = 3 + (pg_idx * 3)
            
            if base_col + 2 < len(row):
                revenue = row[base_col] if pd.notna(row[base_col]) else 0
                quantity = row[base_col + 1] if pd.notna(row[base_col + 1]) else 0
                gp = row[base_col + 2] if pd.notna(row[base_col + 2]) else 0
                
                # Only add if there's any data
                if revenue or quantity or gp:
                    data_rows.append((year, month, current_region, territory, manager, product_group, 'revenue', float(revenue) if revenue else 0))
                    data_rows.append((year, month, current_region, territory, manager, product_group, 'quantity', float(quantity) if quantity else 0))
                    data_rows.append((year, month, current_region, territory, manager, product_group, 'gp', float(gp) if gp else 0))
    
    print(f"Parsed {len(data_rows)} territory plan records")
    print(f"Regions found: {set(r[2] for r in data_rows if r[2])}")
    return data_rows

def truncate_and_insert(conn, data_rows, year, month, table_name='mart.excel_plans_territories'):
    """Clear existing data for period and insert new"""
    cur = conn.cursor()
    
    # Delete existing data for this period
    cur.execute(f"""
        DELETE FROM {table_name} 
        WHERE year = %s AND month = %s
    """, (year, month))
    deleted = cur.rowcount
    print(f"Deleted {deleted} existing records from {table_name}")
    
    # Determine columns based on table
    if 'territories' in table_name:
        query = f"""
        INSERT INTO {table_name} 
            (year, month, region, territory, manager, product_group, metric_type, plan_value)
        VALUES %s
        """
    else:  # warehouses
        query = f"""
        INSERT INTO {table_name} 
            (year, month, region, warehouse, product_group, metric_type, plan_value)
        VALUES %s
        """
    
    execute_values(cur, query, data_rows)
    conn.commit()
    print(f"✅ Inserted {len(data_rows)} records into {table_name}")

# Known warehouse regions
WAREHOUSE_REGIONS = ['ПОВОЛЖЬЕ', 'СЕВЕРО-ЗАПАД', 'СИБИРЬ-УРАЛ', 'ЮГ', 'ЦЕНТР', 'МОСКВА']

def parse_warehouses_plan(file_path, year, month):
    """
    Parse warehouses Excel file with structure:
    - Region rows (Поволжье, Северо-Запад, etc.) - no 'Склад' prefix
    - Warehouse rows start with 'Склад ' followed by city name
    - Exception: 'Москва' row contains data directly and has no 'Склад' prefix
    
    Returns: List of tuples (year, month, region, warehouse, product_group, metric_type, value)
    """
    print(f"Reading warehouses plan: {file_path}")
    
    df = pd.read_excel(file_path, sheet_name='Планы Январь 2026', header=None)
    
    data_rows = []
    current_region = None
    
    # Start from row 3 (data rows)
    for idx in range(3, len(df)):
        row = df.iloc[idx]
        
        col0 = str(row[0]).strip() if pd.notna(row[0]) else ''
        
        if not col0:
            continue
        
        # Skip summary/total rows
        if 'итого' in col0.lower() or 'отдел' in col0.lower():
            continue
            
        col0_upper = col0.upper()
        
        # 1. Handle Regular Regions (exclude Moscow here to handle it specially)
        is_region = any(r in col0_upper for r in WAREHOUSE_REGIONS) and not col0.startswith('Склад') and 'МОСКВА' not in col0_upper
        
        if is_region:
            # Map to standard region name
            for r in WAREHOUSE_REGIONS:
                if r in col0_upper:
                    current_region = r.title() if r != 'МОСКВА' else 'Москва'
                    # Fix formatting
                    if r == 'СЕВЕРО-ЗАПАД': current_region = 'Северо-Запад'
                    elif r == 'СИБИРЬ-УРАЛ': current_region = 'Сибирь-Урал'
                    break
            continue
        
        # 2. Check if this is a warehouse row OR Moscow special case
        is_warehouse = col0.startswith('Склад')
        is_moscow = 'МОСКВА' in col0_upper
        
        if not is_warehouse and not is_moscow:
            continue
            
        warehouse_name = col0
        
        if is_moscow:
            current_region = 'Москва'
            warehouse_name = 'Склад Москва' # Synthetic name for consistency
            
        if not current_region:
            print(f"⚠️ Skipping warehouse {warehouse_name} - no region context")
            continue
        
        # Parse product groups - starting from column 1
        # Structure: each product group has 3 columns (Кол-во, Выручка, ГП) based on Excel header
        for pg_idx, product_group in enumerate(PRODUCT_GROUPS):
            base_col = 1 + (pg_idx * 3)
            
            if base_col + 2 < len(row):
                quantity = row[base_col] if pd.notna(row[base_col]) else 0
                revenue = row[base_col + 1] if pd.notna(row[base_col + 1]) else 0
                gp = row[base_col + 2] if pd.notna(row[base_col + 2]) else 0
                
                # Only add if there's any data
                if revenue or quantity or gp:
                    data_rows.append((year, month, current_region, warehouse_name, product_group, 'revenue', float(revenue) if revenue else 0))
                    data_rows.append((year, month, current_region, warehouse_name, product_group, 'quantity', float(quantity) if quantity else 0))
                    data_rows.append((year, month, current_region, warehouse_name, product_group, 'gp', float(gp) if gp else 0))
    
    print(f"Parsed {len(data_rows)} warehouse plan records")
    print(f"Regions found: {set(r[2] for r in data_rows if r[2])}")
    print(f"Warehouses found: {len(set(r[3] for r in data_rows))}")
    return data_rows

def main():
    territories_file = "__pycache__/plans_territories.xlsx"
    warehouses_file = "__pycache__/plans_warehouses.xlsx"
    year = 2026
    month = 1
    
    print("=" * 80)
    print("EXCEL PLANS IMPORT v2")
    print("=" * 80)
    
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    
    try:
        # Import Territories with new structure
        print("\n--- TERRITORIES ---")
        territories_data = parse_territories_plan_v2(territories_file, year, month)
        truncate_and_insert(conn, territories_data, year, month, 'mart.excel_plans_territories')
        
        # Import Warehouses
        print("\n--- WAREHOUSES ---")
        warehouses_data = parse_warehouses_plan(warehouses_file, year, month)
        truncate_and_insert(conn, warehouses_data, year, month, 'mart.excel_plans_warehouses')
        
        # Verify territories
        cur = conn.cursor()
        cur.execute("""
            SELECT region, territory, manager, COUNT(*) 
            FROM mart.excel_plans_territories 
            WHERE year=%s AND month=%s 
            GROUP BY region, territory, manager 
            ORDER BY region, territory
            LIMIT 10
        """, (year, month))
        
        print("\n" + "=" * 80)
        print("VERIFICATION - Territories:")
        print("=" * 80)
        for row in cur.fetchall():
            print(f"{row[0]:20} | {row[1]:25} | {row[2]:25} | {row[3]} records")
        
        # Verify warehouses
        cur.execute("""
            SELECT region, warehouse, COUNT(*) 
            FROM mart.excel_plans_warehouses 
            WHERE year=%s AND month=%s 
            GROUP BY region, warehouse 
            ORDER BY region, warehouse
            LIMIT 20
        """, (year, month))
        
        print("\n" + "=" * 80)
        print("VERIFICATION - Warehouses:")
        print("=" * 80)
        for row in cur.fetchall():
            print(f"{row[0]:20} | {row[1]:30} | {row[2]} records")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()

