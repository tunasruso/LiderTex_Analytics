import pymysql
import argparse
import datetime

from config import DB_CONFIG, CORP_TEAM_ID

# Volga IDs
VOLGA_IDS = [
    'e1bcfe3e-5b4f-6e4b-83b3-65aa1dd37aab', 
    '126394f7-0570-a22b-873f-59314e2fb541', 
    '670da544-2c37-2c67-7f5b-65ae4e6f0feb'
]

TARGET_STAGES_SQL = "'Order send','Closed Won'"
CORP_TEAM_ID = 'c613f93d-974f-5cc7-5593-681887d59aaa'

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def debug_volga(target_date, hour_cutoff):
    conn = get_connection()
    cursor = conn.cursor()
    
    date_start = f"{target_date} 00:00:00"
    date_end = f"{target_date} {hour_cutoff:02d}:00:00"
    ids_str = "','".join(VOLGA_IDS)
    
    query = f'''
    SELECT 
        teams.name as team_name,
        CONCAT(users.last_name, ' ', users.first_name) as manager_name,
        
        -- Categories Count
        SUM(IF(productcat.id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4') OR productcat.parent_category_id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4'), productsale.count, 0)) AS per,
        SUM(IF(productcat.id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e') OR productcat.parent_category_id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e'), productsale.count, 0)) AS obliv,
        SUM(IF(productcat.id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d') OR productcat.parent_category_id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d'), productsale.count, 0)) AS vaf,
        SUM(IF(productcat.id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1') OR productcat.parent_category_id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1'), productsale.count, 0)) AS vetosh,
        SUM(IF(productcat.id IN ('56e605af-31df-9377-5322-50f0124b66d1') OR productcat.parent_category_id IN ('56e605af-31df-9377-5322-50f0124b66d1'), productsale.count, 0)) AS ruk,
        SUM(IF(productcat.id IN ('d2ca8d1d-e078-4276-c733-5488539d35e6','ad0cafb2-82e3-bd9f-7de8-643e911e5bff','2764ae01-c9f7-7b3e-78f4-643e91aafa06'), productsale.count, 0)) AS stretch,
        SUM(IF(productcat.id IN ('e0fcedd5-485c-e14d-9a80-54885389b508') OR productcat.parent_category_id IN ('e0fcedd5-485c-e14d-9a80-54885389b508'), productsale.count, 0)) AS bugs,
        
        -- China (Pcs and Rub included in columns in excel)
        SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), productsale.count, 0)) AS china_pcs,
        SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), productsale.amount, 0)) AS china_rub,
        
        -- Resale RUB
        SUM(IF(product.own_prod = 0, productsale.amount, 0)) as resale_rub,
        
        -- Total Revenue
        SUM(productsale.amount) AS allsum,
        
        -- GP
        SUM(productsale.amount - (productsale.count * IFNULL(product.cost, 0))) as gp
        
    FROM opportunities
    INNER JOIN productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN product ON productsale.product_id = product.id 
    INNER JOIN productcat ON productcat.id = product.category_id 
    LEFT JOIN users ON users.id = opportunities.assigned_user_id
    LEFT JOIN teams ON teams.id = users.team_id
    WHERE productsale.deleted = 0
    AND opportunities.deleted = 0
    AND teams.id IN ('{ids_str}')
    AND opportunities.sales_stage IN ({TARGET_STAGES_SQL})
    AND opportunities.id IN (
        SELECT parent_id FROM opportunities_audit 
        WHERE opportunities_audit.parent_id = opportunities.id 
        AND opportunities_audit.date_created BETWEEN '{date_start}' AND '{date_end}'
        AND opportunities_audit.after_value_string IN ({TARGET_STAGES_SQL})
        AND (opportunities_audit.before_value_string NOT IN ({TARGET_STAGES_SQL}) OR opportunities_audit.before_value_string IS NULL)
    )
    GROUP BY teams.name, manager_name
    ORDER BY teams.name, manager_name
    '''
    
    print(f"DEBUGGING VOLGA: {date_start} to {date_end}")
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"{'TEAM':40} | {'MANAGER':20} | {'REV':>10} | {'GP':>10} | {'PER':>6} | {'OBLIV':>6} | {'VAF':>6}")
    print("-" * 120)
    
    total_rev = 0
    
    for row in rows:
        team = row[0][:40]
        mgr = row[1][:20] if row[1] else "None"
        rev = int(row[12] or 0)
        gp = int(row[13] or 0)
        
        per = int(row[2] or 0)
        obliv = int(row[3] or 0)
        vaf = int(row[4] or 0)
        
        print(f"{team:40} | {mgr:20} | {rev:>10,} | {gp:>10,} | {per:>6} | {obliv:>6} | {vaf:>6}")
        total_rev += rev
        
    print("-" * 120)
    print(f"TOTAL REVENUE: {total_rev:,}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2026-01-26')
    parser.add_argument('--hour', type=int, default=14)
    args = parser.parse_args()
    
    debug_volga(args.date, args.hour)
