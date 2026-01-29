"""
Excel Plans Report Module - Query Excel-based sales plans
"""
import psycopg2
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from etl.config.settings import POSTGRES_CONFIG

def get_territories_plans(year, month, region=None):
    """
    Get sales plans by territory for a given month
    Returns: {
        'data': [{region, territory, manager, products: {group: {revenue, quantity, gp}}}],
        'regions': [list of unique regions],
        'totals': {product_group: {revenue: X, quantity: Y, gp: Z}}
    }
    """
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    where_clause = "WHERE year = %s AND month = %s"
    params = [year, month]
    
    if region:
        where_clause += " AND region = %s"
        params.append(region)
    
    query = f"""
    SELECT region, territory, manager, product_group, metric_type, plan_value
    FROM mart.excel_plans_territories
    {where_clause}
    ORDER BY region, territory, product_group
    """
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    # Build nested structure: region -> (territory, manager) -> product_group -> metrics
    regions_data = {}
    totals = {}
    territory_managers = {}  # Map (region, territory) -> manager
    
    for region_name, territory, manager, product_group, metric_type, plan_value in rows:
        reg = region_name if region_name else 'Без региона'
        
        if reg not in regions_data:
            regions_data[reg] = {}
        
        if territory not in regions_data[reg]:
            regions_data[reg][territory] = {}
        
        if product_group not in regions_data[reg][territory]:
            regions_data[reg][territory][product_group] = {}
        
        regions_data[reg][territory][product_group][metric_type] = float(plan_value or 0)
        
        # Store manager
        territory_managers[(reg, territory)] = manager
        
        # Accumulate totals
        if product_group not in totals:
            totals[product_group] = {'revenue': 0, 'quantity': 0, 'gp': 0}
        totals[product_group][metric_type] = totals[product_group].get(metric_type, 0) + float(plan_value or 0)
    
    # Convert to list format
    data = []
    for reg, territories in regions_data.items():
        for territory, products in territories.items():
            data.append({
                'region': reg,
                'territory': territory,
                'manager': territory_managers.get((reg, territory), ''),
                'products': products
            })
    
    return {
        'data': data,
        'regions': list(regions_data.keys()),
        'totals': totals
    }

def get_warehouses_plans(year, month, region=None):
    """
    Get sales plans by warehouse for a given month
    Returns: {
        'data': [{region, warehouse, products: {group: {revenue, quantity, gp}}}],
        'regions': [list of unique regions],
        'totals': {product_group: {revenue: X, quantity: Y, gp: Z}}
    }
    """
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    where_clause = "WHERE year = %s AND month = %s"
    params = [year, month]
    
    if region:
        where_clause += " AND region = %s"
        params.append(region)
    
    query = f"""
    SELECT region, warehouse, product_group, metric_type, plan_value
    FROM mart.excel_plans_warehouses
    {where_clause}
    ORDER BY region, warehouse, product_group
    """
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    # Build nested structure: region -> warehouse -> product_group -> metrics
    regions_data = {}
    totals = {}
    
    for region_name, warehouse, product_group, metric_type, plan_value in rows:
        # Determine region from warehouse name or region column
        if region_name:
            reg = region_name
        elif warehouse:
            # Extract region from warehouse name pattern like "Склад Казань" -> need to match to region
            # For now, use 'Без региона' if region is null
            reg = 'Без региона'
        else:
            reg = 'Без региона'
        
        if reg not in regions_data:
            regions_data[reg] = {}
        
        if warehouse not in regions_data[reg]:
            regions_data[reg][warehouse] = {}
        
        if product_group not in regions_data[reg][warehouse]:
            regions_data[reg][warehouse][product_group] = {}
        
        regions_data[reg][warehouse][product_group][metric_type] = float(plan_value or 0)
        
        # Accumulate totals
        if product_group not in totals:
            totals[product_group] = {'revenue': 0, 'quantity': 0, 'gp': 0}
        totals[product_group][metric_type] = totals[product_group].get(metric_type, 0) + float(plan_value or 0)
    
    # Convert to list format
    data = []
    for reg, warehouses in regions_data.items():
        for warehouse, products in warehouses.items():
            data.append({
                'region': reg,
                'warehouse': warehouse,
                'products': products
            })
    
    return {
        'data': data,
        'regions': list(regions_data.keys()),
        'totals': totals
    }

if __name__ == "__main__":
    # Test
    result = get_territories_plans(2026, 1)
    print(f"Territories: {len(result['data'])} territories")
    print(f"Total Revenue: {sum(p.get('revenue', 0) for p in result['totals'].values()):,.0f}")
    
    result = get_warehouses_plans(2026, 1)
    print(f"Warehouses: {len(result['data'])} warehouses")
    print(f"Total Revenue: {sum(p.get('revenue', 0) for p in result['totals'].values()):,.0f}")
