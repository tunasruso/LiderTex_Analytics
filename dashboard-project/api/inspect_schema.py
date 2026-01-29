import psycopg2
import os
from api.config_prod import POSTGRES_CONFIG

def inspect_schema():
    try:
        print("Connecting to PostgreSQL...")
        # Print config (masking password)
        config_safe = POSTGRES_CONFIG.copy()
        if 'password' in config_safe:
            config_safe['password'] = '******'
            
        print(f"Config: {config_safe}")
        
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        print("\n--- Schemas ---")
        cursor.execute("SELECT schema_name FROM information_schema.schemata;")
        schemas = cursor.fetchall()
        for s in schemas:
            print(f" - {s[0]}")
            
        print("\n--- Tables in 'mart' schema ---")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'mart';")
        mart_tables = cursor.fetchall()
        if not mart_tables:
            print(" (No tables found in 'mart')")
        for t in mart_tables:
            print(f" - mart.{t[0]}")

        print("\n--- Tables in 'raw' schema ---")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw';")
        raw_tables = cursor.fetchall()
        for t in raw_tables:
            print(f" - raw.{t[0]}")
        for t in public_tables:
            print(f" - public.{t[0]}")
            
        print("\n--- All tables with 'opportunities' in name ---")
        cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name LIKE '%opportunities%';")
        opp_tables = cursor.fetchall()
        for t in opp_tables:
            print(f" - {t[0]}.{t[1]}")

        conn.close()
        print("\nDone.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_schema()
