import psycopg2
import sys
import os

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from etl.config.settings import POSTGRES_CONFIG

def fix_schema():
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    print("Dropping raw.gr_payrol_items...")
    cur.execute("DROP TABLE IF EXISTS raw.gr_payrol_items")
    
    print("Creating raw.gr_payrol_items with Integer ID...")
    cur.execute("""
        CREATE TABLE raw.gr_payrol_items (
            id INTEGER PRIMARY KEY,
            salary_id UUID, 
            category_id UUID,
            plan INTEGER,
            checked INTEGER
        )
    """)
    conn.commit()
    print("✅ Schema fixed.")
    conn.close()

if __name__ == "__main__":
    fix_schema()
