from .base import BaseExtractor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

import pymysql.cursors

class CRMExtractor(BaseExtractor):
    def extract(self, table_name, last_sync=None, batch_size=5000, incremental_col=None):
        """
        Extract data from table.
        
        Args:
            table_name: Name of the table to extract
            last_sync: Last sync timestamp (None for full load)
            batch_size: Number of rows per batch
            incremental_col: Column to use for incremental sync (e.g., 'date_modified', 'date_entered')
                            If None, does full extract.
        """
        logger.info(f"Extracting {table_name}, last_sync={last_sync}, incremental_col={incremental_col}")
        
        # If no incremental column specified, do full load
        if incremental_col is None:
            logger.info(f"Full extract for {table_name} (no incremental column)")
            sql = f"SELECT * FROM {table_name}"
            params = ()
        else:
            # Verify if column exists in MySQL
            has_date_field = True
            try:
                with self.source_conn.cursor() as check_cur:
                    check_cur.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (incremental_col,))
                    if not check_cur.fetchone():
                        has_date_field = False
            except:
                has_date_field = False

            if not has_date_field:
                logger.warning(f"Column '{incremental_col}' not found in {table_name}. Doing full extract.")
                sql = f"SELECT * FROM {table_name}"
                params = ()
            elif last_sync:
                sql = f"SELECT * FROM {table_name} WHERE {incremental_col} >= %s"
                params = (last_sync,)
            else:
                from config.settings import SYNC_START_DATE
                sql = f"SELECT * FROM {table_name} WHERE {incremental_col} >= %s"
                params = (SYNC_START_DATE,)

        # Use SSDictCursor for streaming large datasets without OOM
        try:
            # Note: We need to ensure connection is not committed/closed mid-stream
            # Create a specific cursor for this operation
            cursor = self.source_conn.cursor(pymysql.cursors.SSDictCursor)
            cursor.execute(sql, params)
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                logger.info(f"Yielding batch of {len(rows)} rows from {table_name}")
                yield rows
                
        finally:
            cursor.close()

