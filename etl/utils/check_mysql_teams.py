import pymysql
import sys
import os

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)
from etl.config.settings import MYSQL_CONFIG

def check_mysql_teams():
    conn = pymysql.connect(**MYSQL_CONFIG)
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*), name FROM teams GROUP BY name")
        rows = cursor.fetchall()
        print(f"Total Groups: {len(rows)}")
        for row in rows:
            print(row)
    conn.close()

if __name__ == "__main__":
    check_mysql_teams()
