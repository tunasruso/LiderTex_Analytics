#!/usr/bin/env python3
"""
Sales Report by Product Categories
Отчёт продаж с разбивкой по категориям товаров, командам и менеджерам

Использование:
    python3 sales_report_by_categories.py --date-start 2026-01-26 --date-end 2026-01-26
    python3 sales_report_by_categories.py --json
"""

import pymysql
import json
from datetime import datetime
import argparse

# Конфигурация подключения
DB_CONFIG = {
    'host': '100.100.54.21',
    'port': 3307,
    'user': 'exchange',
    'password': 'OVs7MG13v!',
    'database': 'crm',
    'connect_timeout': 60
}

# UUID категорий для классификации товаров
CATEGORIES = {
    'per': {  # Перчатки х/б
        'ids': [
            '42ac50da-efa0-9baa-51cc-50efc73a1fc6',
            '3fb2004f-ffe1-67b3-d797-65aa1f509de3',
            '8d432105-5ecf-3fc7-8242-62b32dc497e8',
            'f35511c6-0a8c-6ece-02cb-62b32d67dbf4'
        ],
        'name': 'Перчатки х/б'
    },
    'ruk': {  # Рукавицы
        'ids': ['56e605af-31df-9377-5322-50f0124b66d1'],
        'product_ids': [
            'd2ce11bf-8b1d-f983-8bda-50f01578752c',
            'f475045f-b2ac-7a7d-cce6-5296ed1df430',
            '10cf1f0e-1d53-1707-a72f-5c766eec4b8d',
            '8e93811a-e6e9-e8be-712d-50f01412e6db',
            'a498009d-eb1b-618e-6b03-57442be792cf',
            'b1ca376a-d940-3eb7-1b82-50f0186322bf',
            '59ddf14a-7906-44e9-bf05-580f265bd891',
            '98b5c6ff-d833-861d-fe10-5178edc2bfb4',
            'de48d2c0-42c0-9f4c-2113-5a7d5e017e72',
            'eeef745f-89bb-7b77-aaaf-5443d6fba3e0',
            'ee493828-89d0-5092-f050-5a0e9c845025',
            '922b2ad9-ca81-d4c7-3a88-5a1ea4e4a340',
            '616c84e6-dcac-de58-9b8a-54e0c86d01d5',
            'b763d802-6535-6073-4bd0-5672c1dfb4bb',
            'd201cc4d-f52d-3a85-e595-5a1295f28df7',
            'b4dcac13-b7dd-7b1c-91ce-50f017f3ba80'
        ],
        'name': 'Рукавицы'
    },
    'vaf': {  # Вафельное полотно
        'ids': ['74bf507d-a38e-ea92-6d81-626a9915ed7d'],
        'name': 'Вафельное полотно'
    },
    'obliv': {  # Обливные перчатки
        'ids': [
            'b7ece599-c211-52fd-2f30-5c21f1a851ca',
            'bf4581e7-681a-75ce-2796-62baa764dcf7',
            'd716ff1c-96e4-3451-f8a8-50efe14e851e'
        ],
        'name': 'Перчатки спец.'
    },
    'vetosh': {  # Ветошь
        'ids': [
            'c5d5d05c-a672-08bb-5f3b-59cb95299ef3',
            '5ddd11ee-f0fe-39b3-8483-6613bc528163',
            'aaa602e1-a42d-5972-7830-6736fd16cef1'
        ],
        'product_ids': [
            'cdcf27ae-b7cd-38e6-14f0-50f003593239',
            '796c7093-cf5c-ffbc-3bae-56727abe0964'
        ],
        'name': 'Ветошь'
    },
    'stretch': {  # Стрейч
        'ids': [
            'd2ca8d1d-e078-4276-c733-5488539d35e6',
            'ad0cafb2-82e3-bd9f-7de8-643e911e5bff',
            '2764ae01-c9f7-7b3e-78f4-643e91aafa06'
        ],
        'product_ids': [
            'e11ff355-c7f2-4c90-b584-5256604b4b04',
            '88538027-50db-3dd0-e0da-5f28053e57ad',
            'cbeaa605-185a-6c4a-767f-6053554e8675',
            'de2d057b-b351-fe7c-20a0-63db822cfeac',
            'eee460cb-7983-7d33-d4ec-625fc34b74bc'
        ],
        'name': 'Стрейч'
    },
    'bugs': {  # Мешки
        'ids': ['e0fcedd5-485c-e14d-9a80-54885389b508'],
        'name': 'Мешки'
    },
    'china': {  # Китай
        'ids': ['5502e046-af74-daca-00cc-67f7c90060d0'],
        'name': 'Китай'
    }
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def generate_category_sql_case(cat_key, cat_config, count_or_amount='count'):
    """Генерирует CASE WHEN для категории"""
    conditions = []
    
    # Категории по id
    if 'ids' in cat_config and cat_config['ids']:
        ids_str = "','".join(cat_config['ids'])
        conditions.append(f"productcat.id IN ('{ids_str}')")
        conditions.append(f"productcat.parent_category_id IN ('{ids_str}')")
    
    # Отдельные продукты
    if 'product_ids' in cat_config and cat_config['product_ids']:
        prod_ids_str = "','".join(cat_config['product_ids'])
        conditions.append(f"product.id IN ('{prod_ids_str}')")
    
    if not conditions:
        return "0"
    
    return f"SUM(IF({' OR '.join(conditions)}, productsale.{count_or_amount}, 0))"

def get_sales_report(date_start, date_end, team_ids=None):
    """Основной запрос отчёта"""
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Форматируем даты для SQL
    date_start_sql = f"{date_start} 00:00:00"
    date_end_sql = f"{date_end} 23:59:59"
    
    # Фильтр по командам
    team_filter = ""
    if team_ids:
        ids_str = "','".join(team_ids)
        team_filter = f"AND teams.id IN ('{ids_str}')"
    else:
        # По умолчанию все команды category='retail'
        team_filter = "AND teams.category = 'retail'"
    
    # Основной запрос
    query = f'''
    SELECT 
        teams.id as team_id,
        teams.name as team_name,
        CONCAT(users.last_name, ' ', users.first_name) as user_name,
        users.id as user_id,
        
        -- Категории (количество)
        SUM(IF(productcat.id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4') 
            OR productcat.parent_category_id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4'), 
            productsale.count, 0)) AS per,
            
        SUM(IF(productcat.id IN ('56e605af-31df-9377-5322-50f0124b66d1') 
            OR productcat.parent_category_id IN ('56e605af-31df-9377-5322-50f0124b66d1')
            OR product.id IN ('d2ce11bf-8b1d-f983-8bda-50f01578752c','f475045f-b2ac-7a7d-cce6-5296ed1df430','10cf1f0e-1d53-1707-a72f-5c766eec4b8d','8e93811a-e6e9-e8be-712d-50f01412e6db','a498009d-eb1b-618e-6b03-57442be792cf','b1ca376a-d940-3eb7-1b82-50f0186322bf','59ddf14a-7906-44e9-bf05-580f265bd891','98b5c6ff-d833-861d-fe10-5178edc2bfb4','de48d2c0-42c0-9f4c-2113-5a7d5e017e72','eeef745f-89bb-7b77-aaaf-5443d6fba3e0','ee493828-89d0-5092-f050-5a0e9c845025','922b2ad9-ca81-d4c7-3a88-5a1ea4e4a340','616c84e6-dcac-de58-9b8a-54e0c86d01d5','b763d802-6535-6073-4bd0-5672c1dfb4bb','d201cc4d-f52d-3a85-e595-5a1295f28df7','b4dcac13-b7dd-7b1c-91ce-50f017f3ba80'),
            productsale.count, 0)) AS ruk,
            
        SUM(IF(productcat.id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d') 
            OR productcat.parent_category_id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d'), 
            productsale.count, 0)) AS vaf,
            
        SUM(IF(productcat.id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e') 
            OR productcat.parent_category_id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e'), 
            productsale.count, 0)) AS obliv,
            
        SUM(IF(productcat.id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1') 
            OR productcat.parent_category_id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1')
            OR product.id IN ('cdcf27ae-b7cd-38e6-14f0-50f003593239','796c7093-cf5c-ffbc-3bae-56727abe0964'), 
            productsale.count, 0)) AS vetosh,
            
        SUM(IF(productcat.id IN ('d2ca8d1d-e078-4276-c733-5488539d35e6','ad0cafb2-82e3-bd9f-7de8-643e911e5bff','2764ae01-c9f7-7b3e-78f4-643e91aafa06') 
            OR product.id IN ('e11ff355-c7f2-4c90-b584-5256604b4b04','88538027-50db-3dd0-e0da-5f28053e57ad','cbeaa605-185a-6c4a-767f-6053554e8675','de2d057b-b351-fe7c-20a0-63db822cfeac','eee460cb-7983-7d33-d4ec-625fc34b74bc'), 
            productsale.count, 0)) AS stretch,
            
        SUM(IF(productcat.id IN ('e0fcedd5-485c-e14d-9a80-54885389b508') 
            OR productcat.parent_category_id IN ('e0fcedd5-485c-e14d-9a80-54885389b508'), 
            productsale.count, 0)) AS bugs,
            
        SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') 
            OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), 
            productsale.count, 0)) AS china,
            
        ROUND(SUM(IF(productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') 
            OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0'), 
            productsale.amount, 0)), 0) AS china_amount,
            
        ROUND(SUM(productsale.amount), 0) as allsum
        
    FROM opportunities
    INNER JOIN productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN product ON productsale.product_id = product.id 
    INNER JOIN productcat ON productcat.id = product.category_id 
    LEFT JOIN productcat AS cat2 ON cat2.id = productcat.parent_category_id
    LEFT JOIN users ON users.id = opportunities.assigned_user_id
    LEFT JOIN teams ON teams.id = users.team_id
    
    WHERE productsale.deleted = 0
    AND opportunities.deleted = 0
    AND opportunities.sales_stage IN ('Shipment expectation', 'Order send', 'Closed Won')
    AND opportunities.id IN (
        SELECT parent_id 
        FROM opportunities_audit 
        WHERE opportunities_audit.parent_id = opportunities.id 
        AND opportunities_audit.date_created BETWEEN '{date_start_sql}' AND '{date_end_sql}'
        AND opportunities_audit.after_value_string = 'Shipment expectation'
    )
    {team_filter}
    
    GROUP BY teams.name, CONCAT(users.last_name, users.first_name)
    ORDER BY teams.name, CONCAT(users.last_name, users.first_name) ASC
    '''
    
    cursor.execute(query)
    sales_data = cursor.fetchall()
    
    # Запрос грязной прибыли
    dp_query = f'''
    SELECT 
        ROUND(SUM(DirtyProfitSave.dirty_profit), 0) as dp,
        users.id as user_id
    FROM DirtyProfitSave
    LEFT JOIN opportunities ON opportunities.id = DirtyProfitSave.opportunity_id
    LEFT JOIN users ON users.id = opportunities.assigned_user_id
    LEFT JOIN teams ON teams.id = users.team_id
    
    WHERE opportunities.deleted = 0
    AND opportunities.sales_stage IN ('Shipment expectation', 'Order send', 'Closed Won')
    AND opportunities.id IN (
        SELECT parent_id 
        FROM opportunities_audit 
        WHERE opportunities_audit.parent_id = opportunities.id 
        AND opportunities_audit.date_created BETWEEN '{date_start_sql}' AND '{date_end_sql}'
        AND opportunities_audit.after_value_string = 'Shipment expectation'
    )
    {team_filter}
    
    GROUP BY teams.name, CONCAT(users.last_name, users.first_name)
    ORDER BY teams.name, CONCAT(users.last_name, users.first_name) ASC
    '''
    
    cursor.execute(dp_query)
    dp_data = {row['user_id']: row['dp'] for row in cursor.fetchall()}
    
    conn.close()
    
    # Объединяем данные
    for row in sales_data:
        row['dirty_profit'] = dp_data.get(row['user_id'], 0)
    
    return sales_data

def print_report(data, date_start, date_end):
    """Вывод отчёта в консоль"""
    print('=' * 120)
    print(f'ОТЧЁТ ПРОДАЖ ПО КАТЕГОРИЯМ: {date_start} - {date_end}')
    print('=' * 120)
    
    # Заголовки
    print(f"{'Отдел':30} | {'Менеджер':25} | {'Пер':>6} | {'Рук':>5} | {'Ваф':>5} | {'Обл':>5} | {'Вет':>5} | {'Стр':>5} | {'Меш':>5} | {'Кит':>5} | {'Сумма':>12} | {'ГП':>10}")
    print('-' * 120)
    
    current_team = None
    team_totals = {}
    
    for row in data:
        if row['team_name'] != current_team:
            if current_team:
                print('-' * 120)
            current_team = row['team_name']
        
        team = (row['team_name'] or 'Без отдела')[:30]
        user = (row['user_name'] or 'Без менеджера')[:25]
        
        print(f"{team:30} | {user:25} | {int(row['per'] or 0):>6} | {int(row['ruk'] or 0):>5} | {int(row['vaf'] or 0):>5} | {int(row['obliv'] or 0):>5} | {int(row['vetosh'] or 0):>5} | {int(row['stretch'] or 0):>5} | {int(row['bugs'] or 0):>5} | {int(row['china'] or 0):>5} | {int(row['allsum'] or 0):>12,} | {int(row['dirty_profit'] or 0):>10,}")
    
    print('=' * 120)
    
    # Итоги
    totals = {
        'per': sum(int(r['per'] or 0) for r in data),
        'ruk': sum(int(r['ruk'] or 0) for r in data),
        'vaf': sum(int(r['vaf'] or 0) for r in data),
        'obliv': sum(int(r['obliv'] or 0) for r in data),
        'vetosh': sum(int(r['vetosh'] or 0) for r in data),
        'stretch': sum(int(r['stretch'] or 0) for r in data),
        'bugs': sum(int(r['bugs'] or 0) for r in data),
        'china': sum(int(r['china'] or 0) for r in data),
        'allsum': sum(int(r['allsum'] or 0) for r in data),
        'dirty_profit': sum(int(r['dirty_profit'] or 0) for r in data)
    }
    
    print(f"{'ИТОГО':30} | {'':25} | {totals['per']:>6} | {totals['ruk']:>5} | {totals['vaf']:>5} | {totals['obliv']:>5} | {totals['vetosh']:>5} | {totals['stretch']:>5} | {totals['bugs']:>5} | {totals['china']:>5} | {totals['allsum']:>12,} | {totals['dirty_profit']:>10,}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sales Report by Categories')
    parser.add_argument('--date-start', default='2026-01-26', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--date-end', default='2026-01-26', help='End date (YYYY-MM-DD)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    data = get_sales_report(args.date_start, args.date_end)
    
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print_report(data, args.date_start, args.date_end)
