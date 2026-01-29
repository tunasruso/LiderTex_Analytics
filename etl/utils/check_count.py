import pymysql
import sys
import os

# Add project root to path (2 levels up from utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)
from etl.config.settings import MYSQL_CONFIG

def check_count():
    conn = pymysql.connect(**MYSQL_CONFIG)
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM gr_payrol_items")
        print(f"Items Count: {cursor.fetchone()['COUNT(*)']}")
    conn.close()

if __name__ == "__main__":
    check_count()
