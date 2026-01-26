import pymysql
from datetime import datetime

# DB Config
DB_CONFIG = {
    'host': '100.100.54.21',
    'port': 3307,
    'user': 'exchange',
    'password': 'OVs7MG13v!',
    'database': 'crm',
    'connect_timeout': 60
}

def run_query(query):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        print(f"\nQUERY: {query}")
        cursor.execute(query)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        print(f"COLUMNS: {columns}")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== PRODUCTSALE (margin/cost search) ===")
    run_query("DESCRIBE productsale")
    run_query("SELECT id, amount, product_id, count FROM productsale LIMIT 2")
    
    print("\n=== OPPORTUNITIES (gp search) ===")
    run_query("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'crm' AND TABLE_NAME = 'opportunities' AND (COLUMN_NAME LIKE '%gp%' OR COLUMN_NAME LIKE '%profit%' OR COLUMN_NAME LIKE '%margin%')")
    
    print("\n=== TEAM MONTH PLANS (structure) ===")
    run_query("DESCRIBE teammonthplans")
    run_query("SELECT * FROM teammonthplans ORDER BY date_entered DESC LIMIT 5")
    
    print("\n=== GR_PLAN (structure) ===")
    run_query("DESCRIBE gr_plan")
    
    print("\n=== RESALE SEARCH ===")
    # Check if there is a 'is_resale' flag in products
    run_query("DESCRIBE product")
    run_query("SELECT id, name, category_id FROM product WHERE name LIKE '%китай%' LIMIT 2")
