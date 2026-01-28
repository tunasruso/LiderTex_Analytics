"""
Sales Plans Report Module
Queries PostgreSQL Analytics DB for monthly sales plans by region
"""
import psycopg2
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.config_prod import POSTGRES_CONFIG

# Category ID to Report Field mapping
# Based on gr_payrol_items.category_id values
CATEGORY_MAP = {
    'amount': 'revenue',
    'dirty_plan': 'gp',
    'resale': 'resale',
    'per_retail_sum': 'per',
    'obliv': 'obliv',
    'vaf': 'vaf',
    'vetosh': 'vetosh',
    'ruk': 'ruk',
    'stretch': 'stretch',
    'bugs': 'bugs',
    'china': 'china',
    'china_sum': 'china_sum'
}

def get_plans_by_region(year: int, month: int):
    """
    Returns sales plans aggregated by region
    Format: { 'Москва': {'revenue': X, 'gp': Y, ...}, ... }
    """
    import api.excel_plans_report as excel_plans_report
    from api.category_mapping import EXCEL_TO_KEY
    
    # 1. Fetch RAW Excel Data
    # We want territories plans? Or Warehouses? 
    # Usually Territory Plans are the sales targets for managers.
    raw_data = excel_plans_report.get_territories_plans(year, month)
    
    plans_by_region = {}
    
    # 2. Aggregations
    # Excel Data structure: { 'data': [ { 'region': '...', 'products': { 'CAT': {'revenue': ...} } } ] }
    
    for item in raw_data['data']:
        region = item['region']
        if not region: region = 'Команда без региона'
        
        # Normalize Region (Title Case)
        region = region.title()
        if 'Moskva' in region or 'Москва' in region: region = 'Москва'
        
        if region not in plans_by_region:
            plans_by_region[region] = {}
            
        products = item['products']
        
        for excel_cat, metrics in products.items():
            # Map Excel Key to Internal Key
            key = EXCEL_TO_KEY.get(excel_cat)
            
            # Special handling for "Total" or unmapped
            if not key:
                # If excel_cat is 'ИТОГО', skip or map to total? 
                # We usually want breakdowns.
                continue
                
            rev = metrics.get('revenue', 0)
            gp = metrics.get('gp', 0)
            
            # Accumulate Data
            if key == 'china':
                # Special mapping for China:
                # Frontend 'china' -> "Китай шт" (Qty)
                # Frontend 'china_sum' -> "Китай руб" (Rev)
                qty = metrics.get('quantity', 0)
                plans_by_region[region]['china'] = plans_by_region[region].get('china', 0) + qty
                
                plans_by_region[region]['china_sum'] = plans_by_region[region].get('china_sum', 0) + rev
            else:
                # Standard mapping: key -> Revenue
                plans_by_region[region][key] = plans_by_region[region].get(key, 0) + rev
            
            # Also store GP if needed (global 'gp' accumulator)
            plans_by_region[region]['gp'] = plans_by_region[region].get('gp', 0) + gp

    # Calculate totals
    totals = {}
    for region, metrics in plans_by_region.items():
        for key, val in metrics.items():
            totals[key] = totals.get(key, 0) + val
            
    return {
        'data': plans_by_region,
        'totals': totals
    }

if __name__ == "__main__":
    # Test
    now = datetime.now()
    result = get_plans_by_region(now.year, now.month)
    print(f"Plans for {now.year}-{now.month}:")
    for region, data in result['data'].items():
        print(f"  {region}: Revenue={data.get('revenue', 0):,.0f}")
    print(f"  TOTALS: Revenue={result['totals'].get('revenue', 0):,.0f}")
