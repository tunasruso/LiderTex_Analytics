#!/usr/bin/env python3
"""
Hourly Sales Report Engine
Факт продаж с разбивкой по регионам и сравнением с предыдущим рабочим днём

Использование:
    python3 hourly_sales_report.py
    python3 hourly_sales_report.py --date 2026-01-26 --compare-date 2026-01-23
"""

import pymysql
import json
from datetime import datetime, timedelta
import argparse

# Конфигурация подключения
DB_CONFIG = {
    'host': '100.100.54.21',
    'port': 3307,
    'user': 'exchange',
    'password': 'OVs7MG13v!',
    'database': 'crm',
    'connect_timeout': 30
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_hourly_sales(cursor, target_date, hour_cutoff=None):
    """Получить продажи за дату с опциональным ограничением по часу"""
    
    hour_filter = f"AND HOUR(o.date_modified) < {hour_cutoff}" if hour_cutoff else ""
    
    query = f'''
    SELECT 
        COALESCE(r.name, 'БЕЗ РЕГИОНА') as region,
        COUNT(*) as deals_count,
        ROUND(SUM(o.amount), 0) as total_amount,
        ROUND(SUM(o.amount_net), 0) as total_net
    FROM opportunities o
    JOIN accounts a ON o.account_id = a.id
    LEFT JOIN accounts_cstm ac ON a.id = ac.id_c
    LEFT JOIN routs r ON ac.routs_c = r.id
    WHERE o.sales_stage = 'Closed Won'
      AND o.deleted = 0
      AND DATE(o.date_closed) = '{target_date}'
      {hour_filter}
    GROUP BY r.name
    ORDER BY total_amount DESC
    '''
    
    cursor.execute(query)
    return {row[0]: {'deals': row[1], 'amount': row[2], 'amount_net': row[3] or 0} 
            for row in cursor.fetchall()}

def get_day_total(cursor, target_date):
    """Получить общий итог за день (без фильтра по часам)"""
    query = f'''
    SELECT COUNT(*), ROUND(SUM(amount), 0)
    FROM opportunities
    WHERE sales_stage = 'Closed Won'
      AND deleted = 0
      AND DATE(date_closed) = '{target_date}'
    '''
    cursor.execute(query)
    row = cursor.fetchone()
    return {'deals': row[0], 'amount': row[1] or 0}

def generate_report(report_date='2026-01-26', compare_date='2026-01-23', hour_cutoff=None):
    """Генерация отчёта сравнения"""
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Автоопределение часа если не указан
    if hour_cutoff is None:
        # Используем текущий час (Москва UTC+3, сервер может быть UTC)
        hour_cutoff = datetime.now().hour + 3  # Примерная корректировка
        if hour_cutoff > 23:
            hour_cutoff = 23
    
    # Данные за сегодня
    today_data = get_hourly_sales(cursor, report_date, hour_cutoff)
    today_full = get_day_total(cursor, report_date)
    
    # Данные за день сравнения
    compare_data = get_hourly_sales(cursor, compare_date, hour_cutoff)
    compare_full = get_day_total(cursor, compare_date)
    
    conn.close()
    
    # Объединяем все регионы
    all_regions = set(today_data.keys()) | set(compare_data.keys())
    
    results = []
    for region in all_regions:
        t = today_data.get(region, {'deals': 0, 'amount': 0, 'amount_net': 0})
        c = compare_data.get(region, {'deals': 0, 'amount': 0, 'amount_net': 0})
        
        diff_amount = t['amount'] - c['amount']
        diff_pct = ((t['amount'] / c['amount']) - 1) * 100 if c['amount'] > 0 else (100 if t['amount'] > 0 else 0)
        
        results.append({
            'region': region,
            'today_deals': t['deals'],
            'today_amount': t['amount'],
            'compare_deals': c['deals'],
            'compare_amount': c['amount'],
            'diff_amount': diff_amount,
            'diff_pct': round(diff_pct, 1)
        })
    
    # Сортировка по сумме
    results.sort(key=lambda x: x['today_amount'], reverse=True)
    
    # Итоги
    total_today = sum(r['today_amount'] for r in results)
    total_compare = sum(r['compare_amount'] for r in results)
    total_diff_pct = ((total_today / total_compare) - 1) * 100 if total_compare > 0 else 0
    
    report = {
        'report_date': report_date,
        'compare_date': compare_date,
        'hour_cutoff': hour_cutoff,
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'today_hourly': total_today,
            'compare_hourly': total_compare,
            'diff_percent': round(total_diff_pct, 1),
            'today_full_day': today_full['amount'],
            'compare_full_day': compare_full['amount']
        },
        'regions': results
    }
    
    return report

def print_report(report):
    """Красивый вывод отчёта"""
    print('=' * 90)
    print(f"ФАКТ ПРОДАЖ: {report['report_date']} vs {report['compare_date']}")
    print(f"Данные с 00:00 до {report['hour_cutoff']:02d}:00")
    print('=' * 90)
    print()
    
    print(f"{'Регион':50} | {'Сегодня':>12} | {'Сравн.':>12} | {'Динамика':>10}")
    print('-' * 90)
    
    for r in report['regions'][:25]:
        region = r['region'][:50]
        sign = '+' if r['diff_pct'] >= 0 else ''
        print(f"{region:50} | {r['today_amount']:>12,.0f} | {r['compare_amount']:>12,.0f} | {sign}{r['diff_pct']:>9.1f}%")
    
    print('-' * 90)
    s = report['summary']
    sign = '+' if s['diff_percent'] >= 0 else ''
    print(f"{'ИТОГО (до часа)':50} | {s['today_hourly']:>12,.0f} | {s['compare_hourly']:>12,.0f} | {sign}{s['diff_percent']:>9.1f}%")
    print(f"{'ИТОГО (весь день)':50} | {s['today_full_day']:>12,.0f} | {s['compare_full_day']:>12,.0f} |")
    print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Hourly Sales Report')
    parser.add_argument('--date', default='2026-01-26', help='Report date (YYYY-MM-DD)')
    parser.add_argument('--compare-date', default='2026-01-23', help='Compare date (YYYY-MM-DD)')
    parser.add_argument('--hour', type=int, default=None, help='Hour cutoff (0-23)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    report = generate_report(args.date, args.compare_date, args.hour)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
