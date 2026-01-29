
import sys
import os
import psycopg2
from datetime import datetime
from api.config_prod import POSTGRES_CONFIG
import api.daily_plans as daily_plans
import api.excel_plans_report as excel_plans_report

# Helper to print localized
def debug_moscow_per():
    date_str = "2026-01-29"
    print(f"--- Debugging for {date_str} ---")
    
    # 1. Check Working Days
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    total, remaining = daily_plans.get_remaining_working_days(date_obj)
    print(f"Total Working Days: {total}")
    print(f"Remaining Working Days: {remaining}")
    
    # 2. Get Plan for Moscow
    year, month = 2026, 1
    monthly_data = daily_plans.get_monthly_plans(year, month)
    print(f"Available Regions in Plan: {list(monthly_data.keys())}")
    


    # Handle case sensitivity
    raw_key = 'МОСКВА' if 'МОСКВА' in monthly_data else 'Москва'
    msk_data = monthly_data[raw_key]
    
    print(f"Using Plan Key: {raw_key}")
    
    # 2b. Print all categories in plan
    # print(f"Plan Categories: {msk_data['categories']}")
    cat_plan = msk_data['categories'].get('per', 0)
    print(f"Monthly Plan (Moscow - Per): {cat_plan}")
    
    # 3. Get Fact
    facts = daily_plans.get_actual_sales_ytd(date_obj)
    print(f"Available Regions in Fact: {list(facts.keys())}")
    
    # Fact uses Normalized 'Москва'
    msk_fact_data = facts.get('Москва', {})
    msk_fact = msk_fact_data.get('per', {}).get('revenue', 0)
    
    print(f"Fact YTD (Moscow - Per): {msk_fact}")
    
    # 4. Calc (Static)
    daily = daily_plans.calculate_daily_target(cat_plan, total)
    print(f"Calculated Daily Target (Static): {daily}")
    print(f"   = {int(cat_plan)} / {total}")

if __name__ == "__main__":
    try:
        debug_moscow_per()
    except Exception as e:
        print(f"Error: {e}")
