import psycopg2
import pymysql
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import MYSQL_CONFIG, POSTGRES_CONFIG

def test_mysql():
    print("Testing MySQL Connection...")
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ MySQL Connected! Version: {version}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ MySQL Connection Failed: {e}")
        return False

def test_postgres():
    print("\nTesting PostgreSQL Connection...")
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ PostgreSQL Connected! Version: {version[0]}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL Connection Failed: {e}")
        return False

if __name__ == "__main__":
    mysql_ok = test_mysql()
    pg_ok = test_postgres()
    
    if mysql_ok and pg_ok:
        print("\n🎉 All systems go!")
        sys.exit(0)
    else:
        print("\n⚠️ Connection Check Failed")
        sys.exit(1)
