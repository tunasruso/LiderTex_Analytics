"""
Modal ETL Job for LiderTex Analytics
Syncs CRM data from MySQL to PostgreSQL on a schedule.
Uses Tailscale (SOCKS5 proxy) to connect to internal network.
"""
import modal
import os
import logging
import subprocess
import time
import socket
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Modal_ETL")

# Modal App
app = modal.App("lidertex-etl")

# Image with dependencies including Tailscale, PySocks, and pg8000
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "iptables", "iproute2")
    .run_commands(
        "curl -fsSL https://tailscale.com/install.sh | sh"
    )
    .pip_install(
        "pymysql",
        "pg8000",  # Pure Python PostgreSQL driver
        "cryptography",
        "pysocks"
    )
)

TABLES_TO_SYNC = [
    'teams',
    'users',
    'productcat',
    'product',
    'opportunities',
    'opportunities_audit',
    'productsale',
    'gr_payrol',
    'gr_payrol_items',
    'gr_workdays',
    # Territory tables
    'accounts',
    'accounts_cstm',
    'districts',
    'district_group'
]

SCHEMA_COLUMNS = {
    'teams': ['id', 'name', 'date_entered', 'date_modified', 'deleted', 'assigned_user_id'],
    'users': ['id', 'user_name', 'first_name', 'last_name', 'is_admin', 'status', 'team_id', 'deleted', 'date_entered', 'date_modified'],
    'productcat': ['id', 'name', 'parent_category_id', 'date_entered', 'date_modified', 'deleted'],
    'product': ['id', 'name', 'category_id', 'own_prod', 'price_in1', 'date_entered', 'date_modified', 'deleted'],
    'opportunities': ['id', 'name', 'date_entered', 'date_modified', 'date_closed', 'assigned_user_id', 'sales_stage', 'opportunity_type', 'amount', 'deleted'],
    'opportunities_audit': ['id', 'parent_id', 'date_created', 'field_name', 'before_value_string', 'after_value_string'],
    'productsale': ['id', 'opportunity_id', 'product_id', 'count', 'amount', 'date_entered', 'date_modified', 'deleted'],
    'gr_payrol': ['id', 'name', 'year', 'month', 'assigned_user_id', 'date_entered', 'date_modified', 'deleted'],
    'gr_payrol_items': ['id', 'salary_id', 'category_id', 'plan', 'checked'],
    'gr_workdays': ['year', 'month', 'days'],
    # Territory tables
    'accounts': ['id', 'name', 'date_entered', 'date_modified', 'deleted', 'assigned_user_id', 'inn', 'kpp'],
    'accounts_cstm': ['id_c', 'district_c'],
    'districts': ['id', 'name', 'district_group_id', 'team_id', 'deleted', 'city'],
    'district_group': ['id', 'name', 'deleted', 'assigned_user_id']
}

import uuid

def validate_uuid(val):
    """Return val if valid UUID, else None."""
    if not val:
        return None
    try:
        uuid.UUID(str(val))
        return val
    except ValueError:
        return None

# Store original socket
_original_socket = socket.socket


def start_tailscale():
    """Start Tailscale daemon and authenticate using SOCKS5 proxy mode."""
    authkey = os.environ.get("TAILSCALE_AUTHKEY")
    if not authkey:
        raise RuntimeError("TAILSCALE_AUTHKEY not set")
    
    logger.info("Starting Tailscale daemon in userspace mode with SOCKS5...")
    
    # Start tailscaled in userspace mode with SOCKS5 proxy
    subprocess.Popen(
        ["tailscaled", "--tun=userspace-networking", "--socks5-server=localhost:1055"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Increased wait
    
    # Authenticate
    logger.info("Authenticating with Tailscale...")
    result = subprocess.run(
        ["tailscale", "up", "--authkey", authkey, "--hostname", "modal-etl", "--accept-routes"],
        capture_output=True,
        text=True,
        timeout=120  # Increased timeout
    )
    
    if result.returncode != 0:
        logger.error(f"Tailscale auth failed: {result.stderr}")
        raise RuntimeError(f"Tailscale authentication failed: {result.stderr}")
    
    # Wait for connection to establish fully
    time.sleep(10)  # Increased wait for stability
    
    # Check status
    status = subprocess.run(["tailscale", "status"], capture_output=True, text=True)
    logger.info(f"Tailscale status:\n{status.stdout}")
    
    # Enable SOCKS proxy for all sockets
    import socks
    socks.set_default_proxy(socks.SOCKS5, "localhost", 1055)
    socket.socket = socks.socksocket
    
    return True


def get_mysql_conn():
    """Connect to MySQL through SOCKS5 proxy."""
    import pymysql
    
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=60
    )


def get_pg_conn():
    """Connect to PostgreSQL using pg8000 (pure Python, works with SOCKS)."""
    import pg8000
    
    # Retry connection for SOCKS proxy stability
    for attempt in range(3):
        try:
            conn = pg8000.connect(
                host=os.environ["PG_HOST"],
                port=int(os.environ["PG_PORT"]),
                user=os.environ["PG_USER"],
                password=os.environ["PG_PASSWORD"],
                database=os.environ["PG_DATABASE"],
                timeout=120  # Increased timeout
            )
            return conn
        except Exception as e:
            logger.warning(f"PostgreSQL connection attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise


def get_last_sync(pg_conn, table_name):
    """Get last sync timestamp for a table."""
    cur = pg_conn.cursor()
    cur.execute("""
        SELECT last_sync FROM raw.etl_state WHERE table_name = %s
    """, (table_name,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else datetime(2025, 12, 1)


def update_last_sync(pg_conn, table_name, timestamp):
    """Update last sync timestamp."""
    cur = pg_conn.cursor()
    cur.execute("""
        INSERT INTO raw.etl_state (table_name, last_sync) 
        VALUES (%s, %s)
        ON CONFLICT (table_name) DO UPDATE SET last_sync = EXCLUDED.last_sync
    """, (table_name, timestamp))
    pg_conn.commit()
    cur.close()


def extract_table(mysql_conn, table_name, last_sync):
    """Extract data from MySQL since last sync."""
    date_field = 'date_created' if table_name == 'opportunities_audit' else 'date_modified'
    
    # Static/reference tables - always full sync
    static_tables = ['gr_workdays', 'districts', 'district_group', 'accounts_cstm']
    
    if table_name in static_tables:
        query = f"SELECT * FROM {table_name}"
    else:
        query = f"SELECT * FROM {table_name} WHERE {date_field} > %s"
    
    with mysql_conn.cursor() as cur:
        if table_name in static_tables:
            cur.execute(query)
        else:
            cur.execute(query, (last_sync,))
        return cur.fetchall()


def filter_columns(table, data):
    """Keep only columns defined in schema."""
    if table not in SCHEMA_COLUMNS:
        return data
    valid_cols = set(SCHEMA_COLUMNS[table])
    return [{k: v for k, v in row.items() if k in valid_cols} for row in data]


def load_table(pg_conn, table_name, data):
    """Load data into PostgreSQL using UPSERT."""
    if not data:
        return
    
    columns = list(data[0].keys())
    cols_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    
    # Determine primary key
    if table_name == 'gr_workdays':
        pk = 'year, month'
    elif table_name == 'accounts_cstm':
        pk = 'id_c'
    else:
        pk = 'id' if 'id' in columns else columns[0]
    
    update_cols = [f"{c} = EXCLUDED.{c}" for c in columns if c not in pk.split(', ')]
    update_str = ", ".join(update_cols) if update_cols else f"{columns[0]} = EXCLUDED.{columns[0]}"
    
    query = f"""
        INSERT INTO raw.{table_name} ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT ({pk}) DO UPDATE SET {update_str}
    """
    
    cur = pg_conn.cursor()
    for row in data:
        values = []
        for c in columns:
            val = row.get(c)
            # Basic cleaning for UUIDs
            if c in ['id', 'assigned_user_id', 'parent_id', 'opportunity_id', 
                     'product_id', 'team_id', 'district_group_id', 'id_c']:
                 val = validate_uuid(val)
            values.append(val)
            
        try:
            cur.execute(query, values)
        except Exception as e:
            logger.warning(f"Failed to insert row in {table_name}: {e}")
            pg_conn.rollback() # Rollback transaction to clear error state
    
    pg_conn.commit()
    cur.close()
    logger.info(f"Loaded batch into raw.{table_name}")


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("mysql-crm"),
        modal.Secret.from_name("postgres-analytics"),
        modal.Secret.from_name("tailscale-key")
    ],
    schedule=modal.Cron("0 5-18 * * *"),  # Every hour 8:00-21:00 Moscow (UTC+3)
    timeout=1800  # 30 min for initial sync
)
def run_etl():
    """Main ETL job - runs every hour."""
    start_time = datetime.now()
    logger.info(f"Starting ETL at {start_time}")
    
    # Connect to Tailscale network first (enables SOCKS proxy)
    start_tailscale()
    
    mysql_conn = get_mysql_conn()
    logger.info("MySQL connected!")
    
    pg_conn = get_pg_conn()
    logger.info("PostgreSQL connected!")
    
    try:
        for table in TABLES_TO_SYNC:
            try:
                last_sync = get_last_sync(pg_conn, table)
                logger.info(f"Processing {table}. Last sync: {last_sync}")
                
                data = extract_table(mysql_conn, table, last_sync)
                
                if data:
                    data = filter_columns(table, data)
                    load_table(pg_conn, table, data)
                    
                    date_field = 'date_created' if table == 'opportunities_audit' else 'date_modified'
                    if date_field in data[0]:
                        timestamps = [row[date_field] for row in data if row.get(date_field)]
                        if timestamps:
                            update_last_sync(pg_conn, table, max(timestamps))
                else:
                    logger.info(f"No new data for {table}")
                    
            except Exception as e:
                logger.error(f"Error processing {table}: {e}")
                pg_conn.rollback()
                
    finally:
        mysql_conn.close()
        pg_conn.close()
    
    duration = datetime.now() - start_time
    logger.info(f"ETL completed in {duration}")
    return {"status": "success", "duration": str(duration)}


@app.local_entrypoint()
def main():
    """Manual trigger for testing."""
    result = run_etl.remote()
    print(f"ETL Result: {result}")
