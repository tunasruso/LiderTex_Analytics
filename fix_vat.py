import psycopg2
import hourly_analytics

DB_CONFIG = hourly_analytics.POSTGRES_CONFIG

def fix_vat():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Changing 'vat' column to varchar...")
        # We might need to drop data if it can't cast, but table is empty of new rows anyway?
        # Or we use using clause if needed.
        # But wait, earlier migration added it as numeric. If rows exist with numeric data, convert might be weird.
        # But unlikely many rows exist yet if loader failed?
        # Actually loader commits in batches. Some rows might be there.
        # Safest is to ALTER type.
        cur.execute("ALTER TABLE raw.product ALTER COLUMN vat TYPE varchar(255) USING vat::varchar;")
        print("VAT column fixed.")
        
        print("Changing 'weight' columns to varchar...")
        cur.execute("ALTER TABLE raw.product ALTER COLUMN weight TYPE varchar(255) USING weight::varchar;")
        cur.execute("ALTER TABLE raw.product ALTER COLUMN pack_weight TYPE varchar(255) USING pack_weight::varchar;")
        cur.execute("ALTER TABLE raw.product ALTER COLUMN pack_weight TYPE varchar(255) USING pack_weight::varchar;")
        conn.commit()
        print("Weight columns fixed.")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_vat()
