import pymysql

from config import DB_CONFIG

def run_query(query):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        print(f"\nQUERY: {query}")
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        if not rows:
            print("No results.")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== CHECKING PLANS 2026 ===")
    run_query("SELECT team_id, date_start, date_due, amount, pair_count FROM teammonthplans WHERE date_start >= '2026-01-01' ORDER BY date_start LIMIT 10")
    
    print("\n=== CHECKING OWN_PROD DISTRIBUTION ===")
    run_query("SELECT own_prod, count(*) FROM product GROUP BY own_prod")
    
    print("\n=== CHECKING COST IN PRODUCTSALE (RECENT) ===")
    # Check if cost is populated in recent sales
    run_query("SELECT date_entered, count, cost, amount FROM productsale WHERE deleted=0 ORDER BY date_entered DESC LIMIT 10")
