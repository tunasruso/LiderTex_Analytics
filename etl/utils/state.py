from datetime import datetime

class StateStore:
    def __init__(self, conn):
        self.conn = conn

    def get_last_sync(self, table_name):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT last_sync_timestamp FROM meta.sync_state WHERE table_name = %s",
                (table_name,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def update_last_sync(self, table_name, timestamp):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO meta.sync_state (table_name, last_sync_timestamp)
                VALUES (%s, %s)
                ON CONFLICT (table_name) DO UPDATE
                SET last_sync_timestamp = EXCLUDED.last_sync_timestamp
                """,
                (table_name, timestamp)
            )
            self.conn.commit()
