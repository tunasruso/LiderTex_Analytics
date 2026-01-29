
import psycopg2
from api.config_prod import POSTGRES_CONFIG

def init_auth_db():
    print("Connecting to Postgres...")
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Create Table
        print("Creating table raw.auth_users...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.auth_users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(100) NOT NULL
            );
        """)
        
        # 2. Upsert User
        print("Upserting default user...")
        # Postgres ON CONFLICT
        cur.execute("""
            INSERT INTO raw.auth_users (username, password)
            VALUES (%s, %s)
            ON CONFLICT (username) 
            DO UPDATE SET password = EXCLUDED.password;
        """, ('lider_viewer', 'LiderReadOnly2026'))
        
        print("Done.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_auth_db()
