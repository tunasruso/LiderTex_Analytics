import os
from dotenv import load_dotenv

load_dotenv()

# MySQL (CRM Facts)
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '100.100.54.21'),
    'port': int(os.getenv('MYSQL_PORT', 3307)),
    'user': os.getenv('MYSQL_USER', 'exchange'),
    'password': os.getenv('MYSQL_PASSWORD', 'OVs7MG13v!'),
    'database': os.getenv('MYSQL_DB', 'crm'),
    'connect_timeout': 60
}

# PostgreSQL (Analytics/Plans)
POSTGRES_CONFIG = {
    'host': os.getenv('DB_HOST', '100.68.160.86'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'dbname': os.getenv('DB_NAME', 'crm_analytics'),
    'user': os.getenv('DB_USER', 'antigravity_agent'),
    'password': os.getenv('DB_PASSWORD', 'OVs7MG13v!'),
    'connect_timeout': 10
}

CORP_TEAM_ID = os.getenv('CORP_TEAM_ID', 'c613f93d-974f-5cc7-5593-681887d59aaa')
