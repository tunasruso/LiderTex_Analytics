import os
import pymysql.cursors

# Source: MySQL CRM
MYSQL_CONFIG = {
    'host': '100.100.54.21',
    'port': 3307,
    'user': 'exchange',
    'password': 'OVs7MG13v!',
    'database': 'crm',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Target: PostgreSQL Analytics
POSTGRES_CONFIG = {
    'host': '100.68.160.86',
    'port': 5432,
    'dbname': 'crm_analytics',
    'user': 'antigravity_agent',
    'password': 'OVs7MG13v!',
    'connect_timeout': 10
}

# Extract Settings
SYNC_START_DATE = '2025-12-01 00:00:00'
