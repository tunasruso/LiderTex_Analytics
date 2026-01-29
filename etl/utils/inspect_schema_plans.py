import pymysql
import sys
import os
import json

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from etl.config.settings import MYSQL_CONFIG

def inspect_tables(tables):
    conn = pymysql.connect(**MYSQL_CONFIG)
    schema_map = {}
    
    with conn.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                # columns is list of dicts if DictCursor, or tuples?
                # Config uses DictCursor now.
                # output: {'Field': 'id', 'Type': 'char(36)', ...}
                
                col_defs = []
                for col in columns:
                    col_defs.append({
                        'name': col['Field'],
                        'type': col['Type']
                    })
                schema_map[table] = col_defs
                print(f"✅ Found {table}")
            except Exception as e:
                print(f"❌ Error {table}: {e}")
                
    conn.close()
    
    print("\n--- DDL Suggestions ---")
    for table, cols in schema_map.items():
        print(f"\n-- {table}")
        print(f"CREATE TABLE IF NOT EXISTS raw.{table} (")
        definitions = []
        for col in cols:
            # Map MySQL types to Postgres
            pg_type = 'TEXT' # Default
            ctype = col['type'].lower()
            if 'int' in ctype: pg_type = 'INTEGER'
            elif 'double' in ctype or 'float' in ctype: pg_type = 'NUMERIC'
            elif 'decimal' in ctype: pg_type = 'NUMERIC'
            elif 'date' in ctype: pg_type = 'TIMESTAMP' # Handle datetime
            elif 'char(36)' in ctype: pg_type = 'UUID'
            
            definitions.append(f"    {col['name']} {pg_type}")
        
        # Add primary key if 'id' exists
        # Assuming id is first or present
        print(",\n".join(definitions))
        print(");")

if __name__ == "__main__":
    inspect_tables(['gr_payrol', 'gr_payrol_items', 'gr_workdays'])
