import pymysql
import psycopg2
from config.settings import MYSQL_CONFIG, POSTGRES_CONFIG

class MySQLSource:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = pymysql.connect(**MYSQL_CONFIG)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

class PostgresTarget:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = psycopg2.connect(**POSTGRES_CONFIG)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
