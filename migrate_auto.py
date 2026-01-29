import pymysql
import psycopg2
import hourly_analytics

# Map common MySQL types to Postgres
TYPE_MAP = {
    'varchar': 'varchar(255)',
    'text': 'text',
    'int': 'integer',
    'tinyint': 'integer', # boolean or smallint
    'decimal': 'numeric',
    'double': 'numeric',
    'float': 'numeric',
    'datetime': 'timestamp',
    'date': 'date',
    'char': 'varchar(255)', # UUIDs are char(36) -> uuid or varchar
}

def get_mysql_schema():
    conn = pymysql.connect(**hourly_analytics.DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DESCRIBE product")
    cols = {}
    for r in cur.fetchall():
        # r[0] = Field, r[1] = Type (e.g. varchar(255), char(36), int(11))
        name = r[0]
        raw_type = r[1].split('(')[0]
        cols[name] = raw_type
    conn.close()
    return cols

def get_pg_schema():
    conn = psycopg2.connect(**hourly_analytics.POSTGRES_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='raw' AND table_name='product'")
    cols = {r[0] for r in cur.fetchall()}
    conn.close()
    return cols

def migrate():
    mysql_cols = get_mysql_schema()
    pg_cols = get_pg_schema()
    
    conn = psycopg2.connect(**hourly_analytics.POSTGRES_CONFIG)
    cur = conn.cursor()
    
    print("Starting Auto-Migration...")
    
    for col, mysql_type in mysql_cols.items():
        if col not in pg_cols:
            pg_type = TYPE_MAP.get(mysql_type, 'text') # Fallback to text
            
            # Special Handling
            if col in ['id', 'modified_user_id', 'created_by', 'assigned_user_id', 'category_id', 'currency_id', 'contact_id', 'manufacturer_id']:
                pg_type = 'uuid' 
                # Note: If migrating data, empty string '' must be converted to null for UUID! Loader handles this? Yes.
            
            print(f"Adding {col} ({pg_type}) [Source: {mysql_type}]")
            try:
                cur.execute(f"ALTER TABLE raw.product ADD COLUMN \"{col}\" {pg_type} DEFAULT NULL;")
                conn.commit()
            except Exception as e:
                print(f"Failed to add {col}: {e}")
                conn.rollback()
                
    print("Auto-Migration Complete.")
    conn.close()

if __name__ == "__main__":
    migrate()
