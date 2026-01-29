import logging
import etl.extractors.crm_extractor as extractor
import etl.loaders.postgres_loader as loader
import hourly_analytics
import pymysql
import psycopg2
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)

def refresh_products():
    print("Starting Product Data Refresh...")
    
    # 1. Source (MySQL)
    src_conn = pymysql.connect(**hourly_analytics.DB_CONFIG)
    
    # 2. Target (Postgres)
    tgt_conn = psycopg2.connect(**hourly_analytics.POSTGRES_CONFIG)
    
    # 3. ETL Components
    ext = extractor.CRMExtractor(src_conn)
    ld = loader.PostgresLoader(tgt_conn)
    
    # 4. Run
    # We pass last_sync=None to force full load, OR we rely on default behavior
    # Ideally full load to fill price_in1 for all rows
    # The extractor uses SYNC_START_DATE if last_sync is None.
    # To force ALL products, we might want a simpler query or very old date.
    # Let's override last_sync logic in a hacky way or just use a very old date.
    
    try:
        # Extract
        # Note: 'product' table
        # We want to force full reload to get price_in1 for everyone.
        # But BaseExtractor uses SYNC_START_DATE.
        # Let's verify SYNC_START_DATE.
        # Ideally we fetch everything.
        
        # Manually triggering extractor
        # Modify SYNC_START_DATE context or just pass 1970 date if extractor supports param override
        # The extract method takes `last_sync`. 
        # If I pass '2000-01-01', it should get everything.
        
        row_count = 0
        for batch in ext.extract('product', last_sync='2000-01-01'):
            if not batch: continue
            ld.load('product', batch)
            row_count += len(batch)
            print(f"Loaded {row_count} products...")
            
        print("Product Refresh Complete.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        src_conn.close()
        tgt_conn.close()

if __name__ == "__main__":
    refresh_products()
