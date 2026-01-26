import pymysql
import argparse

from config import DB_CONFIG

TARGET_STAGES_SQL = "'Shipment expectation','Order send','Closed Won'"

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def check_troshina_deals():
    conn = get_connection()
    cursor = conn.cursor()
    
    date_start = "2026-01-26 00:00:00"
    date_end = "2026-01-26 14:00:00"
    
    query = f'''
    SELECT 
        opportunities.name,
        opportunities.sales_stage,
        opportunities_audit.date_created as event_time,
        SUM(productsale.amount) as deal_amount,
        SUM(productsale.count) as deal_count,
        opportunities_audit.before_value_string,
        opportunities_audit.after_value_string
    FROM opportunities
    INNER JOIN productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN users ON users.id = opportunities.assigned_user_id
    INNER JOIN opportunities_audit ON opportunities_audit.parent_id = opportunities.id
    WHERE users.last_name = 'Тенятова'
    AND productsale.deleted = 0
    AND opportunities.deleted = 0
    AND opportunities.sales_stage IN ({TARGET_STAGES_SQL})
    AND opportunities_audit.date_created BETWEEN '{date_start}' AND '{date_end}'
    AND opportunities_audit.after_value_string IN ({TARGET_STAGES_SQL})
    AND (opportunities_audit.before_value_string NOT IN ({TARGET_STAGES_SQL}) OR opportunities_audit.before_value_string IS NULL)
    GROUP BY opportunities.id, opportunities_audit.id
    '''
    
    print("CHECKING DEALS FOR TROSHINA:")
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"{'DEAL NAME':30} | {'STAGE':20} | {'TIME':20} | {'AMOUNT':10} | {'COUNT':10} | {'EVENT'}")
    print("-" * 120)
    for row in rows:
        print(f"{row[0][:30]:30} | {row[1]:20} | {str(row[2]):20} | {int(row[3]):10} | {int(row[4]):10} | {row[5]} -> {row[6]}")

if __name__ == "__main__":
    check_troshina_deals()
