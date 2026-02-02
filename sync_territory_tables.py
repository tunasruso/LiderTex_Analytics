"""
Initial sync for territory tables: accounts, accounts_cstm, districts, district_group
"""
import pymysql
import psycopg2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Territory_Sync")

import os

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '100.100.54.21'),
    'port': int(os.getenv('MYSQL_PORT', 3307)),
    'user': os.getenv('MYSQL_USER', 'exchange'),
    'password': os.getenv('MYSQL_PASSWORD'),  # Required via env var
    'database': os.getenv('MYSQL_DATABASE', 'crm'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 60
}

PG_CONFIG = {
    'host': os.getenv('PG_HOST', '100.68.160.86'),
    'port': int(os.getenv('PG_PORT', 5432)),
    'dbname': os.getenv('PG_DATABASE', 'crm_analytics'),
    'user': os.getenv('PG_USER', 'antigravity_agent'),
    'password': os.getenv('PG_PASSWORD'),  # Required via env var
    'connect_timeout': 60
}

def sync_district_group(mysql_conn, pg_conn):
    """Sync district_group (107 rows)"""
    logger.info("Syncing district_group...")
    with mysql_conn.cursor() as cur:
        cur.execute("SELECT id, name, deleted, assigned_user_id FROM district_group")
        rows = cur.fetchall()
    
    logger.info(f"Fetched {len(rows)} district_group")
    pg_cur = pg_conn.cursor()
    
    for row in rows:
        pg_cur.execute("""
            INSERT INTO raw.district_group (id, name, deleted, assigned_user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                deleted = EXCLUDED.deleted,
                assigned_user_id = EXCLUDED.assigned_user_id
        """, (row['id'], row['name'], bool(row['deleted']) if row['deleted'] else False, 
              row['assigned_user_id'] if row['assigned_user_id'] else None))
    
    pg_conn.commit()
    pg_cur.close()
    logger.info("district_group synced!")


def sync_districts(mysql_conn, pg_conn):
    """Sync districts (2K rows)"""
    logger.info("Syncing districts...")
    with mysql_conn.cursor() as cur:
        cur.execute("SELECT id, name, district_group_id, team_id, deleted, city FROM districts")
        rows = cur.fetchall()
    
    logger.info(f"Fetched {len(rows)} districts")
    pg_cur = pg_conn.cursor()
    
    for row in rows:
        pg_cur.execute("""
            INSERT INTO raw.districts (id, name, district_group_id, team_id, deleted, city)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                district_group_id = EXCLUDED.district_group_id,
                team_id = EXCLUDED.team_id,
                deleted = EXCLUDED.deleted,
                city = EXCLUDED.city
        """, (row['id'], row['name'], 
              row['district_group_id'] if row['district_group_id'] else None,
              row['team_id'] if row['team_id'] else None,
              bool(row['deleted']) if row['deleted'] else False,
              row['city']))
    
    pg_conn.commit()
    pg_cur.close()
    logger.info("districts synced!")


def sync_accounts_cstm(mysql_conn, pg_conn):
    """Sync accounts_cstm (151K rows) - only id_c and district_c"""
    logger.info("Syncing accounts_cstm...")
    with mysql_conn.cursor() as cur:
        cur.execute("SELECT id_c, district_c FROM accounts_cstm")
        rows = cur.fetchall()
    
    logger.info(f"Fetched {len(rows)} accounts_cstm")
    pg_cur = pg_conn.cursor()
    
    batch = []
    for row in rows:
        batch.append((row['id_c'], row['district_c']))
        
        if len(batch) >= 5000:
            from psycopg2.extras import execute_values
            execute_values(pg_cur, """
                INSERT INTO raw.accounts_cstm (id_c, district_c)
                VALUES %s
                ON CONFLICT (id_c) DO UPDATE SET district_c = EXCLUDED.district_c
            """, batch)
            pg_conn.commit()
            logger.info(f"  Inserted batch of {len(batch)}")
            batch = []
    
    if batch:
        from psycopg2.extras import execute_values
        execute_values(pg_cur, """
            INSERT INTO raw.accounts_cstm (id_c, district_c)
            VALUES %s
            ON CONFLICT (id_c) DO UPDATE SET district_c = EXCLUDED.district_c
        """, batch)
        pg_conn.commit()
        logger.info(f"  Inserted final batch of {len(batch)}")
    
    pg_cur.close()
    logger.info("accounts_cstm synced!")


import uuid

def validate_uuid(val):
    if not val: 
        return None
    try:
        uuid.UUID(str(val))
        return val
    except ValueError:
        return None

def sync_accounts(mysql_conn, pg_conn, since_date='2025-01-01'):
    """Sync accounts - incremental"""
    logger.info(f"Syncing accounts since {since_date}...")
    with mysql_conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, date_entered, date_modified, deleted, 
                   assigned_user_id, inn, kpp 
            FROM accounts WHERE date_modified >= %s
        """, (since_date,))
        rows = cur.fetchall()
    
    logger.info(f"Fetched {len(rows)} accounts")
    pg_cur = pg_conn.cursor()
    
    formatted_data = []
    for row in rows:
        formatted_data.append((
            row['id'], 
            row['name'], 
            row['date_entered'], 
            row['date_modified'],
            bool(row['deleted']) if row['deleted'] else False,
            validate_uuid(row['assigned_user_id']),  # Validate UUID
            row['inn'], 
            row['kpp']
        ))

    # Use execute_values for speed
    batch_size = 5000
    for i in range(0, len(formatted_data), batch_size):
        batch = formatted_data[i:i+batch_size]
        try:
            from psycopg2.extras import execute_values
            execute_values(pg_cur, """
                INSERT INTO raw.accounts (id, name, date_entered, date_modified, deleted, assigned_user_id, inn, kpp)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    date_entered = EXCLUDED.date_entered,
                    date_modified = EXCLUDED.date_modified,
                    deleted = EXCLUDED.deleted,
                    assigned_user_id = EXCLUDED.assigned_user_id,
                    inn = EXCLUDED.inn,
                    kpp = EXCLUDED.kpp
            """, batch)
            pg_conn.commit()
            logger.info(f"  Inserted batch of {len(batch)} accounts")
        except Exception as e:
            logger.error(f"Error in batch: {e}")
            pg_conn.rollback()

    pg_cur.close()
    logger.info("accounts synced!")


if __name__ == "__main__":
    logger.info("=== Territory Tables Sync ===")
    
    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    pg_conn = psycopg2.connect(**PG_CONFIG)
    
    try:
        sync_district_group(mysql_conn, pg_conn)
        sync_districts(mysql_conn, pg_conn)
        sync_accounts_cstm(mysql_conn, pg_conn)
        sync_accounts(mysql_conn, pg_conn)
        logger.info("=== All Territory Tables Synced! ===")
    finally:
        mysql_conn.close()
        pg_conn.close()
