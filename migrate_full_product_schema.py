import psycopg2
import hourly_analytics

DB_CONFIG = hourly_analytics.POSTGRES_CONFIG

# Map MySQL types to Postgres types (simplified)
COLUMN_DEFS = {
    'price_in1': 'numeric',
    'price_in2': 'numeric', 
    'cost': 'numeric',
    'list_price': 'numeric',
    'price': 'numeric',
    'price_up': 'numeric',
    'price_medium': 'numeric',
    'price_low': 'numeric',
    'pack_amount': 'numeric',
    'pack_weight': 'numeric',
    'weight': 'numeric',
    'discount': 'numeric',
    'vat': 'numeric',
    'opt_porog': 'numeric',
    'min_opt_porog': 'numeric',
    'szwhole': 'numeric',
    'szretail': 'numeric',
    'description': 'text',
    'unit': 'varchar(255)',
    'availability': 'varchar(255)',
    'url': 'text',
    'mfr_part_num': 'varchar(255)',
    'vendor_part_num': 'varchar(255)',
    'full_name': 'varchar(255)',
    'format': 'varchar(255)',
    'place': 'varchar(255)',
    'instock': 'numeric', # or boolean? typically qty
    'delivery': 'varchar(255)',
    'wholesale': 'integer', # bool?
    'individual_production': 'integer',
    'odd_flag': 'integer',
    'marked': 'integer',
    'matrix': 'integer',
    'packaged': 'integer',
    'modified_user_id': 'uuid',
    'created_by': 'uuid',
    'manufacturer_id': 'uuid',
    'contact_id': 'uuid',
    'currency_id': 'uuid',
    'assigned_user_id': 'uuid',
    'category_id': 'uuid',
    'date_available': 'date',
    'onec_sync_date': 'timestamp',
    'onec_sync_status': 'varchar(255)',
    'onec_sync_error': 'text',
    'onec_id': 'varchar(255)',
    'multiplicity': 'numeric',
    'rc_optimal': 'numeric',
    'rc_opt_optimal': 'numeric'
}

def migrate():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get existing columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='raw' AND table_name='product'")
        existing_cols = {r[0] for r in cur.fetchall()}
        
        print("Migrating raw.product schema...")
        
        for col, dtype in COLUMN_DEFS.items():
            if col not in existing_cols:
                print(f"Adding column: {col} ({dtype})")
                try:
                    cur.execute(f"ALTER TABLE raw.product ADD COLUMN {col} {dtype} DEFAULT NULL;")
                    conn.commit()
                except Exception as e:
                    print(f"Failed to add {col}: {e}")
                    conn.rollback()
            else:
                pass # Already exists
                
        print("Migration complete.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
