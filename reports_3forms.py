#!/usr/bin/env python3
"""
3 формы отчётов по продажам LiderTeks
Обновленная логика (Step 580):
- Строгий список команд
- Статусы "4 стадии и выше" (Shipment performance+)
- Корпоративные продажи отдельно
"""

import pymysql
import json
from datetime import datetime, timedelta
import argparse

from config import DB_CONFIG, CORP_TEAM_ID

# Строгий маппинг команд (User provided)
REGION_TEAMS = {
    'Москва': [
        'e0a42418-6a26-3adc-6c5b-55d431ddfad8', # Отдел продаж - 214 Общий Москва
        'ac05cdee-3bb8-f9db-f061-687a515b7a44'  # Отдел продаж - Москва ТП
    ],
    'Северо-Запад': [
        '2c3965cc-926b-1f5e-4bb6-550aa8a02c6c'  # Отдел продаж - 210 Санкт-Петербург
    ],
    'Сибирь-Урал': [
        'be0f2c6f-7839-dd83-c2f1-65aa2bea1ea1', # 218,ЕКБ,Челябинск,Пермь
        'b6785fea-e055-ca93-4594-65aa2b3a0267', # 218,Красноярск,Тюмень,Омск
        '52042a38-7201-b7b0-9868-65a622c4a29f', # 218,Новосибирск
        '17b95305-c01e-1d8b-cdc7-65ae4e40a651'  # 218 Сибирь-Урал
    ],
    'Центр': [
        '944af9fe-3105-3a21-aa95-5f6aefc3a517', # 222,Воронеж,Орел
        '85ad4646-f4fe-cfbb-414e-65aa63d60105', # 222,Иваново,Нижний
        'd6b53d22-d869-6b92-69e7-65ae4d331e0c'  # 222 Центр
    ],
    'Поволжье': [
        'e1bcfe3e-5b4f-6e4b-83b3-65aa1dd37aab', # 217,Оренбург,Казань,Уфа
        '126394f7-0570-a22b-873f-59314e2fb541', # 217,Самара,Пенза,Ульяновск,Саратов
        '670da544-2c37-2c67-7f5b-65ae4e6f0feb'  # 217 Поволжье
    ],
    'Юг': [
        'b3f0f476-03f6-7f45-1d48-54230800c268'  # Отдел продаж - 211 Юг
    ]
}

CORP_TEAM_ID = 'c613f93d-974f-5cc7-5593-681887d59aaa' # Отдел корпоративных продаж

# Статусы "4 и выше" (уточненный список)
TARGET_STAGES = [
    'Shipment expectation',
    'Order send',
    'Closed Won'
]
STAGES_SQL = "'" + "','".join(TARGET_STAGES) + "'"

def get_connection():
    return pymysql.connect(**DB_CONFIG)


# Новый функционал: планы и ГП (Step 843)
try:
    with open('plans.json', 'r', encoding='utf-8') as f:
        PLANS = json.load(f)
except Exception:
    PLANS = {}

def get_report_form1(target_date, hour_cutoff):
    """Optimized: Fetch all data in ONE SQL query + GP + Resale"""
    conn = get_connection()
    cursor = conn.cursor()
    
    date_start = f"{target_date} 00:00:00"
    date_end = f"{target_date} {hour_cutoff:02d}:00:00"
    
    # Construct Region CASE logic
    region_case = "CASE "
    all_team_ids = []
    
    for region, ids in REGION_TEAMS.items():
        quoted_ids = [f"'{x}'" for x in ids]
        all_team_ids.extend(quoted_ids)
        ids_in = ",".join(quoted_ids)
        region_case += f"WHEN teams.id IN ({ids_in}) THEN '{region}' "
    
    # Add Corp team
    region_case += f"WHEN teams.id = '{CORP_TEAM_ID}' THEN 'Отдел корпоративных продаж' "
    region_case += "ELSE 'Other' END"
    
    # Join all IDs for WHERE clause
    all_ids_str = ",".join(all_team_ids) + f",'{CORP_TEAM_ID}'"
    
    query = f'''
    SELECT 
        {region_case} as region_name,
        
        -- Existing Categories (Count)
        SUM(IF(productcat.id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4') 
            OR productcat.parent_category_id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4'), 
            productsale.count, 0)) AS per,
        SUM(IF(productcat.id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e') 
            OR productcat.parent_category_id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e'), 
            productsale.count, 0)) AS obliv,
        SUM(IF(productcat.id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d') 
            OR productcat.parent_category_id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d'), 
            productsale.count, 0)) AS vaf,
        SUM(IF(productcat.id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1') 
            OR productcat.parent_category_id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1'), 
            productsale.count, 0)) AS vetosh,
        SUM(IF(productcat.id IN ('56e605af-31df-9377-5322-50f0124b66d1') 
            OR productcat.parent_category_id IN ('56e605af-31df-9377-5322-50f0124b66d1'), 
            productsale.count, 0)) AS ruk,
        SUM(IF(productcat.id IN ('d2ca8d1d-e078-4276-c733-5488539d35e6','ad0cafb2-82e3-bd9f-7de8-643e911e5bff','2764ae01-c9f7-7b3e-78f4-643e91aafa06'), 
            productsale.count, 0)) AS stretch,
        SUM(IF(productcat.id IN ('e0fcedd5-485c-e14d-9a80-54885389b508') 
            OR productcat.parent_category_id IN ('e0fcedd5-485c-e14d-9a80-54885389b508'), 
            productsale.count, 0)) AS bugs,
        SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') 
            OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), 
            productsale.count, 0)) AS china,
            
        -- New Metrics
        ROUND(SUM(productsale.amount), 0) AS allsum,
        
        -- Gross Profit (Margin): Amount - (Count * Cost)
        ROUND(SUM(productsale.amount - (productsale.count * IFNULL(product.cost, 0))), 0) as gp,
        
        -- Resale (OwnProd = 0)
        ROUND(SUM(IF(product.own_prod = 0, productsale.amount, 0)), 0) as resale,
        
        -- China SUM (Rubles)
        ROUND(SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') 
            OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), 
            productsale.amount, 0)), 0) AS china_sum
            
    FROM opportunities
    INNER JOIN productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN product ON productsale.product_id = product.id 
    INNER JOIN productcat ON productcat.id = product.category_id 
    LEFT JOIN users ON users.id = opportunities.assigned_user_id
    LEFT JOIN teams ON teams.id = users.team_id
    WHERE productsale.deleted = 0
    AND opportunities.deleted = 0
    AND teams.id IN ({all_ids_str})
    AND opportunities.sales_stage IN ({STAGES_SQL})
    AND opportunities.id IN (
        SELECT parent_id FROM opportunities_audit 
        WHERE opportunities_audit.parent_id = opportunities.id 
        AND opportunities_audit.date_created BETWEEN '{date_start}' AND '{date_end}'
        AND opportunities_audit.after_value_string IN ({STAGES_SQL})
        AND (opportunities_audit.before_value_string NOT IN ({STAGES_SQL}) OR opportunities_audit.before_value_string IS NULL)
    )
    GROUP BY region_name
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    results = {}
    
    # Process results into dictionary
    for row in rows:
        region = row[0]
        # Fact values
        fact = {
            'per': int(row[1] or 0),
            'obliv': int(row[2] or 0),
            'vaf': int(row[3] or 0),
            'vetosh': int(row[4] or 0),
            'ruk': int(row[5] or 0),
            'stretch': int(row[6] or 0),
            'bugs': int(row[7] or 0),
            'china': int(row[8] or 0),
            'allsum': int(row[9] or 0),
            'gp': int(row[10] or 0),  # GP
            'resale': int(row[11] or 0), # Resale
            'china_sum': int(row[12] or 0) # China RUB
        }
        
        # Merge with Plan
        plan = PLANS.get(region, {})
        
        # Calculate Percentages
        merged = {}
        for key in fact:
            f_val = fact[key]
            p_val = plan.get(key, 0)
            gp_val = plan.get('gp', 0) if key == 'gp' else 0 # Explicit mapping check
            
            # Map keys to plan keys if different names used in plan.json?
            # Im using same keys in plans.json: revenue (allsum), gp, resale, etc.
            # Fix keys mismatch:
            # fact['allsum'] vs plan['revenue']
            
            p_val = 0
            if key == 'allsum': p_val = plan.get('revenue', 0)
            elif key == 'china_sum': p_val = plan.get('china_sum', 0)
            else: p_val = plan.get(key, 0)
            
            pct = 0
            if p_val > 0:
                pct = round((f_val / p_val) * 100, 1)
                
            merged[key] = {'fact': f_val, 'plan': p_val, 'pct': pct}
            
        results[region] = merged
        
    return results

def print_form1(data, target_date, hour):
    # Simplified print for CLI debug (only main metrics)
    print('=' * 100)
    print(f'ФОРМА 1 (NEW): ФАКТ ПРОДАЖ за {target_date} на {hour:02d}:00')
    print('=' * 100)
    print(f"{'РЕГИОН':20} | {'ВЫРУЧКА (ФАКТ)':>15} | {'ГП (ФАКТ)':>15} | {'ПЕРЕКУП (ФАКТ)':>15}")
    
    regions = ['Москва', 'Северо-Запад', 'Сибирь-Урал', 'Центр', 'Поволжье', 'Юг', 'Отдел корпоративных продаж']
    
    for r in regions:
        if r not in data: continue
        d = data[r]
        rev = d['allsum']['fact']
        gp = d['gp']['fact']
        resale = d['resale']['fact']
        print(f"{r:20} | {rev:>15,} | {gp:>15,} | {resale:>15,}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2026-01-26')
    parser.add_argument('--hour', type=int, default=14)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    
    data = get_report_form1(args.date, args.hour)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_form1(data, args.date, args.hour)
