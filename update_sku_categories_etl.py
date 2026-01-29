import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import uuid
import datetime
import logging
from etl.config.settings import POSTGRES_CONFIG

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = 'SKU_Categories.csv'
TARGET_TABLE = 'mart.sku_category_mapping'

def is_valid_uuid(val):
    if not val: return False
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def get_all_category_ids(cursor, root_id):
    """Recursively find all category IDs including children."""
    ids = {str(root_id)} 
    # Get direct children
    cursor.execute("SELECT id FROM raw.productcat WHERE parent_category_id = %s", (root_id,))
    children = cursor.fetchall()
    
    for (child_id,) in children:
        child_id_str = str(child_id)
        if child_id_str not in ids:
            ids.add(child_id_str)
            # Recurse
            ids.update(get_all_category_ids(cursor, child_id))
    
    return list(ids)

def update_sku_mapping():
    conn = None
    try:
        logger.info("Step 1: Connecting to Postgres...")
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        # 1. Check Tables
        # Ensure target table exists in MART schema
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TARGET_TABLE} (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(255) NOT NULL,
                product_id UUID NOT NULL,
                source VARCHAR(50) NOT NULL, -- 'direct' or 'from_category'
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_sku_cat_name ON {TARGET_TABLE}(category_name);
            CREATE INDEX IF NOT EXISTS idx_sku_prod_id ON {TARGET_TABLE}(product_id);
        """)
        conn.commit()

        # 2. Truncate
        logger.info(f"Step 2: Truncating {TARGET_TABLE}...")
        cursor.execute(f"TRUNCATE TABLE {TARGET_TABLE} RESTART IDENTITY;")
        conn.commit()

        # 3. Read CSV
        if not os.path.exists(CSV_FILE):
            logger.error(f"CSV File not found: {CSV_FILE}")
            return

        logger.info(f"Step 3: Reading {CSV_FILE}...")
        df = pd.read_csv(CSV_FILE)
        # Clean NaNs
        df = df.where(pd.notnull(df), None)
        logger.info(f"Loaded {len(df)} rows.")

        records_to_insert = []
        stats = {
            'processed': 0,
            'direct': 0,
            'from_valid_cat': 0,
            'skipped': 0,
            'errors': []
        }

        for index, row in df.iterrows():
            cat_name = row.get('Название')
            prod_id = row.get('Product ID')
            cat_id = row.get('Productcat ID')

            if not cat_name or (not prod_id and not cat_id):
                stats['skipped'] += 1
                continue

            # CASE 1: Direct Product
            if prod_id and is_valid_uuid(prod_id):
                records_to_insert.append((cat_name, prod_id, 'direct'))
                stats['direct'] += 1

            # CASE 2: From Category (Recursive)
            if cat_id and is_valid_uuid(cat_id):
                try:
                    # [FIX] Get ALL sub-categories recursively
                    all_cat_ids = get_all_category_ids(cursor, cat_id)
                    
                    if not all_cat_ids:
                        continue
                        
                    # Fetch all products in these categories
                    # Need valid UUID syntax for SQL IN clause
                    placeholders =  ','.join(['%s'] * len(all_cat_ids))
                    query = f"SELECT id FROM raw.product WHERE category_id IN ({placeholders})"
                    
                    cursor.execute(query, tuple(all_cat_ids))
                    prods = cursor.fetchall()
                    
                    for (pid,) in prods:
                        records_to_insert.append((cat_name, pid, 'from_category'))
                        stats['from_valid_cat'] += 1
                        
                except Exception as e:
                    stats['errors'].append(f"Row {index} Cat Lookup Error: {e}")
                    conn.rollback() # Rollback query error
            
            stats['processed'] += 1
        
        # 4. Bulk Insert
        logger.info(f"Step 4: Inserting {len(records_to_insert)} records...")
        
        # Deduplicate (tuple set)
        unique_records = list(set(records_to_insert))
        logger.info(f"Unique records after dedupe: {len(unique_records)}")

        if unique_records:
            sql_insert = f"""
                INSERT INTO {TARGET_TABLE} (category_name, product_id, source)
                VALUES %s
            """
            execute_values(cursor, sql_insert, unique_records, page_size=1000)
            conn.commit()
            logger.info("Insertion Complete.")
        
        # 5. Report
        logger.info("="*30)
        logger.info("REPORT")
        logger.info("="*30)
        logger.info(f"Total Rows Processed: {stats['processed']}")
        logger.info(f"Direct Mappings: {stats['direct']}")
        logger.info(f"From Category: {stats['from_valid_cat']}")
        logger.info(f"Total Inserted: {len(unique_records)}")
        
        cursor.execute(f"SELECT category_name, count(*) FROM {TARGET_TABLE} GROUP BY 1 ORDER BY 1")
        rows = cursor.fetchall()
        logger.info("--- By Category ---")
        for r in rows:
            logger.info(f"{r[0]}: {r[1]}")

        # 6. Export CSV
        cursor.execute(f"""
            SELECT m.category_name, p.name, m.product_id, m.source, m.created_at
            FROM {TARGET_TABLE} m
            LEFT JOIN raw.product p ON m.product_id = p.id
            ORDER BY m.category_name, p.name
        """)
        report_data = cursor.fetchall()
        report_df = pd.DataFrame(report_data, columns=['Category', 'ProductName', 'ProductID', 'Source', 'CreatedAt'])
        report_df.to_csv('category_mapping_report.csv', index=False)
        report_df.to_excel('category_mapping_report.xlsx', index=False)
        logger.info("Report saved to category_mapping_report.csv/xlsx")

    except Exception as e:
        logger.error(f"Critical Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    update_sku_mapping()
