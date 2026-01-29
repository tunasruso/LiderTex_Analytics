from .base import BaseExtractor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

import pymysql.cursors

class CRMExtractor(BaseExtractor):
    def extract(self, table_name, last_sync=None, batch_size=5000):
        logger.info(f"Extracting {table_name}, last_sync={last_sync}")
        
        # Determine delta field
        date_field = 'date_modified'
        if table_name == 'opportunities_audit':
            date_field = 'date_created'
        
        # Construct query
        if last_sync:
            sql = f"SELECT * FROM {table_name} WHERE {date_field} >= %s"
            params = (last_sync,)
        else:
            from config.settings import SYNC_START_DATE
            sql = f"SELECT * FROM {table_name} WHERE {date_field} >= %s"
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

