import sys
import os
import logging
from datetime import datetime

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.utils.db import MySQLSource, PostgresTarget
from etl.utils.state import StateStore
from etl.extractors.crm_extractor import CRMExtractor
from etl.loaders.postgres_loader import PostgresLoader
from etl.main_etl import filter_columns

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ETL_Plans")

TABLES_TO_SYNC = [
    'gr_payrol',
    'gr_payrol_items',
    'gr_workdays',
    'teams',
    'productcat'
]

def run_plans_etl():
    start_time = datetime.now()
    logger.info(f"Starting Plans ETL at {start_time}")

    with MySQLSource() as mysql_conn, PostgresTarget() as pg_conn:
        extractor = CRMExtractor(mysql_conn)
        loader = PostgresLoader(pg_conn)
        state_store = StateStore(pg_conn)

        for table in TABLES_TO_SYNC:
            try:
                # Force full fetch if needed, or use sync state
                last_sync = state_store.get_last_sync(table)
                # Override for workdays maybe? No, let's try normal flow
                
                # Check if table works with date_modified?
                # gr_workdays has year, month, days... NO date_modified in schema I saw.
                # gr_payrol has date_modified.
                # gr_payrol_items has NO date_modified.
                
                # We need custom extraction logic for these tables if they lack date_modified
                if table in ['gr_workdays', 'gr_payrol_items', 'teams', 'productcat']:
                    logger.info(f"Full fetch for {table}")
                    with mysql_conn.cursor() as cursor:
                        cursor.execute(f"SELECT * FROM {table}")
                        data = cursor.fetchall()
                else:
                    data = extractor.extract(table, last_sync)

                if data:
                    data = filter_columns(table, data)
                    loader.load(table, data)
                    
                    if table == 'gr_payrol':
                         # Update state
                        timestamps = [row['date_modified'] for row in data if row.get('date_modified')]
                        if timestamps:
                            state_store.update_last_sync(table, max(timestamps))

                else:
                    logger.info(f"No new data for {table}")

            except Exception as e:
                logger.error(f"Error processing {table}: {e}", exc_info=True)
                pg_conn.rollback()

if __name__ == "__main__":
    run_plans_etl()
