from psycopg2.extras import execute_values
import logging

logger = logging.getLogger(__name__)

class PostgresLoader:
    def __init__(self, target_conn):
        self.target_conn = target_conn

    def load(self, table_name, data):
        if not data:
            logger.info(f"No data to load for {table_name}")
            return

        # Prepare columns and values
        # We need to clean data: convert empty strings to None for UUID compatibility
        data = self._clean_data(data)
        
        keys = list(data[0].keys())
        logger.info(f"Target Columns: {keys}")
        columns = ', '.join(keys)
        # VALUES %s is a placeholder for execute_values
        
        # Custom PK handling
        pk_field = '(id)'
        if table_name == 'gr_workdays':
            pk_field = '(year, month)'
            
        update_set = ', '.join([f"{k} = EXCLUDED.{k}" for k in keys if k not in ['id', 'year', 'month']])
        
        query = f"""
            INSERT INTO raw.{table_name} ({columns})
            VALUES %s
            ON CONFLICT {pk_field} DO UPDATE
            SET {update_set}
        """

        # Convert dicts to tuples in matching order
        rows_to_insert = [tuple(row[k] for k in keys) for row in data]

        with self.target_conn.cursor() as cursor:
            # execute_values is efficient for batch inserts
            execute_values(cursor, query, rows_to_insert)
            self.target_conn.commit()
            logger.info(f"Loaded {len(rows_to_insert)} rows into raw.{table_name}")

    def _clean_data(self, data):
        cleaned = []
        bool_fields = {'deleted', 'is_admin'}
        
        # Simple UUID check (36 chars) - could be more robust with regex
        def is_valid_uuid(val):
            if not isinstance(val, str): return False
            return len(val) == 36 and '-' in val

        uuid_fields = {
            'id', 'category_id', 'parent_category_id', 'created_by', 'modified_user_id', 
            'assigned_user_id', 'currency_id', 'manufacturer_id', 'contact_id', 'team_id'
        }

        for row in data:
            new_row = {}
            for k, v in row.items():
                # 1. Convert empty strings to None (for UUIDs)
                if isinstance(v, str):
                    s = v.strip()
                    if s == '':
                        v = None
                    # Special check for known UUID fields that might get garbage
                    elif k in uuid_fields and not is_valid_uuid(s):
                         # If it's a UUID field and value is NOT a valid UUID (e.g. '-99', 'seed_...'), force Null
                         v = None
                    elif 'id' in k and 'seed_' in s: # Catch generic seeds in other ID fields
                         v = None

                # 2. Convert 0/1 to Boolean
                if k in bool_fields and v is not None:
                    try:
                        v = bool(int(v))
                    except:
                        pass # Keep original if conversion fails

                # 3. Handle European decimals (e.g. "0,000") in potential numeric fields
                # If value is string, has comma, and looks numeric otherwise
                if isinstance(v, str) and ',' in v:
                    # simplistic check: if replacing comma with dot makes it a float
                    try:
                        clean_v = v.replace(',', '.')
                        float(clean_v) # check if valid number
                        v = clean_v
                    except:
                        pass # verification failed, keep original (might be text)

                new_row[k] = v
            cleaned.append(new_row)
        return cleaned
