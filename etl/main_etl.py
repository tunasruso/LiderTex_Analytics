import sys
import os
import logging
from datetime import datetime
import time

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.utils.db import MySQLSource, PostgresTarget
from etl.utils.state import StateStore
from etl.extractors.crm_extractor import CRMExtractor
from etl.loaders.postgres_loader import PostgresLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ETL_Main")

TABLES_TO_SYNC = [
    'productsale', # Priority High
    'teams',
    'users',
    'productcat',
    'product',
    'opportunities',
    #'opportunities_audit', # Skip for speed
    'gr_payrol',
    'gr_payrol_items',
    'gr_workdays'
]

# Strict Column Mapping (Must match DDL)
SCHEMA_COLUMNS = {
    'teams': ['id', 'name', 'date_entered', 'date_modified', 'deleted', 'assigned_user_id'],
    'users': ['id', 'user_name', 'first_name', 'last_name', 'is_admin', 'status', 'team_id', 'deleted', 'date_entered', 'date_modified'],
    'productcat': ['id', 'name', 'parent_category_id', 'date_entered', 'date_modified', 'deleted'],
    'product': ['id', 'name', 'category_id', 'own_prod', 'date_entered', 'date_modified', 'deleted'],
    'opportunities': ['id', 'name', 'date_entered', 'date_modified', 'date_closed', 'assigned_user_id', 'sales_stage', 'opportunity_type', 'amount', 'deleted'],
    'opportunities_audit': ['id', 'parent_id', 'date_created', 'field_name', 'before_value_string', 'after_value_string'],
    'productsale': ['id', 'opportunity_id', 'product_id', 'count', 'amount', 'date_entered', 'date_modified', 'deleted'],
    'gr_payrol': ['id', 'name', 'year', 'month', 'assigned_user_id', 'date_entered', 'date_modified', 'deleted'],
    'gr_payrol_items': ['id', 'salary_id', 'category_id', 'plan', 'checked'],
    'gr_workdays': ['year', 'month', 'days']
}

# Per-table incremental sync configuration
# 'incremental_col': Column used for delta detection (date_modified, date_entered, id, or None for full load)
# 'full_load': If True, always do full extract (no incremental)
TABLE_CONFIG = {
    'productsale':        {'incremental_col': 'date_modified'},
    'teams':              {'incremental_col': 'date_modified'},
    'users':              {'incremental_col': 'date_modified'},
    'productcat':         {'incremental_col': 'date_modified'},
    'product':            {'incremental_col': 'date_modified'},
    'opportunities':      {'incremental_col': 'date_modified'},
    'opportunities_audit':{'incremental_col': 'date_created'},
    'gr_payrol':          {'incremental_col': 'date_modified'},
    'gr_payrol_items':    {'incremental_col': None, 'full_load': True},  # No date column
    'gr_workdays':        {'incremental_col': None, 'full_load': True},  # No date column
}

def filter_columns(table, data):
    """Retain only columns that exist in the target schema."""
    if table not in SCHEMA_COLUMNS:
        logger.warning(f"No schema definition for {table}, using all columns.")
        return data # Risk of mismatched columns
    
    valid_cols = set(SCHEMA_COLUMNS[table])
    filtered_data = []
    
    for row in data:
        new_row = {k: v for k, v in row.items() if k in valid_cols}
        filtered_data.append(new_row)
        
    return filtered_data

def run_etl():
    start_time = datetime.now()
    logger.info(f"Starting ETL Job at {start_time}")

    with MySQLSource() as mysql_conn, PostgresTarget() as pg_conn:
        
        extractor = CRMExtractor(mysql_conn)
        loader = PostgresLoader(pg_conn)
        state_store = StateStore(pg_conn)

        for table in TABLES_TO_SYNC:
            try:
                # 1. Get Last Sync
                last_sync = state_store.get_last_sync(table)
                logger.info(f"Processing {table}. Last Sync: {last_sync}")

                # 2. Get table config
                tbl_cfg = TABLE_CONFIG.get(table, {})
                incremental_col = tbl_cfg.get('incremental_col', 'date_modified')
                is_full_load = tbl_cfg.get('full_load', False)
                
                # 3. Extract Data (pass incremental_col to extractor)
                effective_last_sync = None if is_full_load else last_sync
                data_iterator = extractor.extract(table, effective_last_sync, incremental_col=incremental_col)
                
                # We need to track the max_date across all batches to update state at the end
                max_date_seen = None
                total_loaded = 0
                
                # Check if it's a generator (streaming) or list
                import types
                if isinstance(data_iterator, types.GeneratorType):
                    logger.info(f"Processing {table} in batches...")
                    for batch in data_iterator:
                         if not batch: continue
                         
                         batch = filter_columns(table, batch)
                         loader.load(table, batch)
                         total_loaded += len(batch)

                         # Track max date (only if incremental_col exists)
                         if incremental_col:
                             timestamps = [row[incremental_col] for row in batch if row.get(incremental_col)]
                             if timestamps:
                                 batch_max = max(timestamps)
                                 if not max_date_seen or batch_max > max_date_seen:
                                     max_date_seen = batch_max
                else:
                    # Legacy behavior: Single huge list
                    batch = data_iterator
                    if batch:
                        batch = filter_columns(table, batch)
                        loader.load(table, batch)
                        total_loaded += len(batch)
                        
                        if incremental_col:
                            timestamps = [row[incremental_col] for row in batch if row.get(incremental_col)]
                            if timestamps:
                                 max_date_seen = max(timestamps)

                # 4. Update State (Once per table)
                if total_loaded > 0:
                    if max_date_seen:
                        state_store.update_last_sync(table, max_date_seen)
                        logger.info(f"Updated state for {table} to {max_date_seen}. Total rows: {total_loaded}")
                    else:
                        state_store.update_last_sync(table, start_time)
                else:
                     logger.info(f"No new data for {table}")



            except Exception as e:
                logger.error(f"Error processing {table}: {e}", exc_info=True)
                pg_conn.rollback() # Critical: Reset transaction state


    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"ETL Job Completed in {duration}")

if __name__ == "__main__":
    run_etl()
