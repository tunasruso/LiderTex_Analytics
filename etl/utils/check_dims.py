import psycopg2
import sys
import os

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from etl.config.settings import POSTGRES_CONFIG

def check_dims():
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    print("--- Departments ---")
    cur.execute("SELECT * FROM mart.departments ORDER BY id")
    for r in cur.fetchall():
        print(r)
        
    print("\n--- Team Links (Sample) ---")
    cur.execute("""
        SELECT team_name, department_name 
        FROM mart.dim_teams 
        WHERE department_name IS NOT NULL
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(r)
        
    conn.close()

if __name__ == "__main__":
    check_dims()
