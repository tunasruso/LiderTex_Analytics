import psycopg2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import POSTGRES_CONFIG

def apply_schema(sql_file):
    print(f"Applying schema from {sql_file}...")
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        
        with open(sql_file, 'r') as f:
            sql_script = f.read()
            
        cur.execute(sql_script)
        conn.commit()
        
        print("✅ Schema applied successfully!")
        conn.close()
    except Exception as e:
        print(f"❌ Schema Application Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ddl_path = os.path.join(os.path.dirname(__file__), 'ddl.sql')
    apply_schema(ddl_path)
