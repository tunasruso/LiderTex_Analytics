import psycopg2
import sys
import os

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from etl.config.settings import POSTGRES_CONFIG

def check_teams():
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM raw.teams")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} teams.")
    for row in rows:
        print(f"'{row[1]}' (ID: {row[0]})")
        
    conn.close()

if __name__ == "__main__":
    check_teams()
