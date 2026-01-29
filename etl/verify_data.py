import psycopg2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import POSTGRES_CONFIG

def verify_counts():
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    tables = [
        'teams', 'users', 'productcat', 'product', 
        'opportunities', 'opportunities_audit', 'productsale',
        'gr_payrol', 'gr_payrol_items', 'gr_workdays'
    ]
    
    print("Row Counts in PostgreSQL:")
    print("-" * 30)
    
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM raw.{table}")
            count = cur.fetchone()[0]
            print(f"{table.ljust(20)}: {count}")
        except Exception as e:
            print(f"{table.ljust(20)}: Error ({e})")
            conn.rollback()
            
    conn.close()

if __name__ == "__main__":
    verify_counts()
