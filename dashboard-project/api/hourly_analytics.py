import psycopg2
import pymysql
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.config_prod import POSTGRES_CONFIG, DB_CONFIG
from api.reports_3forms import TARGET_STAGES
import api.daily_plans as daily_plans
import api.excel_plans_report as excel_plans_report
import api.category_mapping as category_mapping

def get_mysql_conn():
    return pymysql.connect(**DB_CONFIG)

def get_day_facts_with_timing(date_str: str) -> List[Dict]:
    """
    Get all sales for the day with the timestamp of when they entered the target stage.
    Uses category_mapping for proper category identification.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    date_start = f"{date_str} 00:00:00"
    date_end = f"{date_str} 23:59:59"
    target_stages_str = ",".join([f"'{s}'" for s in TARGET_STAGES])
    
    query = f"""
    SELECT 
        teams.name as team_name,
        product.id as product_id,
        product.own_prod,
        productcat.id as cat_id,
        productcat.parent_category_id as parent_cat_id,
        productsale.amount as revenue,
        productsale.amount - (productsale.count * IFNULL(product.cost, 0)) as gp,
        productsale.count as count,
        MIN(opportunities_audit.date_created) as won_time
    FROM opportunities
    INNER JOIN productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN product ON productsale.product_id = product.id 
    INNER JOIN productcat ON productcat.id = product.category_id 
    LEFT JOIN users ON users.id = opportunities.assigned_user_id
    LEFT JOIN teams ON teams.id = users.team_id
    INNER JOIN opportunities_audit ON opportunities_audit.parent_id = opportunities.id
    WHERE 
        opportunities.deleted = 0
        AND productsale.deleted = 0
        AND opportunities_audit.date_created BETWEEN '{date_start}' AND '{date_end}'
        AND opportunities_audit.after_value_string IN ({target_stages_str})
        AND (opportunities_audit.before_value_string NOT IN ({target_stages_str}) OR opportunities_audit.before_value_string IS NULL)
    GROUP BY productsale.id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_hourly_report_data(date_str: str) -> Dict[str, Any]:
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    year, month = date_obj.year, date_obj.month
    
    # [FIX] Load Mappings from Postgres to link Excel Territories <-> CRM Teams
    pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
    pg_cur = pg_conn.cursor()
    pg_cur.execute("SELECT lower(territory), team_name, region FROM mart.territory_teams_mapping")
    mapping_rows = pg_cur.fetchall()
    pg_conn.close()
    
    # Maps:
    terr_to_team = {row[0]: row[1] for row in mapping_rows if row[0]}
    team_to_region = {row[1]: row[2] for row in mapping_rows if row[1]}
    
    # 1. Get Monthly Plans from Excel (Territory Level)
    year, month, _ = date_str.split('-')
    raw_excel_data = excel_plans_report.get_territories_plans(int(year), int(month))
    
    # AGGREGATE Plans by Team (since Facts are by Team)
    # Key: (Region, EntityName) -> { cat: rev }
    # EntityName = Team Name (if mapped) OR Territory Name (if orphan)
    team_cat_plans = {} 
    team_meta = {} # EntityName -> Region
    
    # Also separate dict for Region Totals (unchanged logic)
    region_cat_totals = {}
    
    for item in raw_excel_data['data']:
        excel_region = item['region']
        region_norm = daily_plans.REPORT_REGION_NAMES.get(excel_region.upper(), excel_region)
        
        terr = item['territory']
        products = item['products']
        
        # Mapping: Terr -> Team
        mapped_team = terr_to_team.get(terr.lower().strip())
        final_key = mapped_team if mapped_team else terr
        final_region = region_norm
        
        # Store metadata
        team_meta[final_key] = final_region
        
        if region_norm not in region_cat_totals:
             region_cat_totals[region_norm] = {}
             
        if (final_region, final_key) not in team_cat_plans:
            team_cat_plans[(final_region, final_key)] = {}
            
        for group, metrics in products.items():
            rev = metrics.get('revenue', 0)
            key = category_mapping.EXCEL_TO_KEY.get(
                group.upper() if isinstance(group, str) else group, 
                None
            )
            if not key: continue
            
            if key in ['per','obliv','vaf','vetosh','ruk','stretch','bugs','china','resale']:
                region_cat_totals[final_region][key] = region_cat_totals[final_region].get(key, 0) + rev
                team_cat_plans[(final_region, final_key)][key] = team_cat_plans[(final_region, final_key)].get(key, 0) + rev


    # 2. Get Dynamic Region Daily Plans (Hourly Breakdown) from daily_plans
    # This returns correct aggregated targets (e.g. 6.4M for Moscow) distributed to categories
    region_daily_data = daily_plans.get_daily_plans_breakdown(date_str)
    # Structure: result['hourly_breakdown'][region]['09:00']['per'] = Cumulative Target amount

    # 3. Get Facts
    raw_facts = get_day_facts_with_timing(date_str)
    
    hours = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    report_data = {}
    
    # All display keys
    all_cat_keys = ['resale','per','obliv','vaf','vetosh','ruk','stretch','bugs','china','china_sum']
    
    for h in hours:
        hour_str = f"{h:02d}:00"
        cutoff_dt = datetime.strptime(f"{date_str} {h}:00:00", "%Y-%m-%d %H:%M:%S")
        
        # Aggregate Facts for this hour snapshot
        current_facts = {}  # { territory: { cat: { rev, gp } } }
        
        for row in raw_facts:
            if row['won_time'] and row['won_time'] <= cutoff_dt:
                 # 2. Determine Category
                cat_key = category_mapping.determine_category(row)
                
                # Filter out unknown categories
                if not cat_key:
                    continue
                
                territory = row['team_name'] or 'Unknown'
                if territory not in current_facts: current_facts[territory] = {}
                if cat_key not in current_facts[territory]: current_facts[territory][cat_key] = {'rev': 0, 'gp': 0}
                
                current_facts[territory][cat_key]['rev'] += float(row['revenue'] or 0)
                current_facts[territory][cat_key]['gp'] += float(row['gp'] or 0)

        # Build Rows
        report_data[h] = []
        
        # Unique territories from plans + facts
        # Keys are now Team Names (from Plan Aggregation and Fact)
        # Or orphan Territory Names
        all_entities = set(team_meta.keys()) | set(current_facts.keys())
        
        for entity in sorted(all_entities):
            row = {'territory': entity}
            
            # Determine Region
            # 1. From Plan Meta
            region = team_meta.get(entity)
            
            # 2. From Fact Mapping (DB)
            if not region and entity in team_to_region:
                region = team_to_region[entity]
                
            # 3. Fallback Heuristic
            if not region:
                 # Clean name for heuristic
                 ename = entity.upper()
                 if 'МОСКВА' in ename or 'БАЛАШИХА' in ename or '214' in ename: region = 'МОСКВА'
                 elif 'СЕВЕРО-ЗАПАД' in ename or 'ПЕТЕРБУРГ' in ename or '210' in ename: region = 'СЕВЕРО-ЗАПАД'
                 elif 'ПОВОЛЖЬЕ' in ename or '217' in ename: region = 'ПОВОЛЖЬЕ'
                 elif 'ЦЕНТР' in ename or '222' in ename: region = 'ЦЕНТР'
                 elif 'ЮГ' in ename or '211' in ename: region = 'ЮГ'
                 elif 'СИБИРЬ' in ename or 'УРАЛ' in ename or '218' in ename: region = 'СИБИРЬ-УРАЛ'
                 else: region = 'МОСКВА' # Fallback default
            
            # Normalize Region for Frontend Consistency
            region = daily_plans.REPORT_REGION_NAMES.get(region.upper(), region)

            row['region'] = region

            total_region_gp = 0
            if region in region_daily_data.get('daily_totals', {}):
                 total_region_gp = region_daily_data['daily_totals'][region].get('gp', 0)
            
            # Simple Proportional Distribution of GP Plan to Territory based on Revenue Share
            # Simple Proportional Distribution of GP Plan to Territory based on Revenue Share
            # We must sum up total region revenue from our categories if 'total' key isn't explicitly set
            reg_total_rev_excel = 0
            for v in region_cat_totals.get(region, {}).values():
                 reg_total_rev_excel += v
            
            entity_total_rev_excel = 0
            current_entity_plans = team_cat_plans.get((region, entity), {})
            for val in current_entity_plans.values():
                 entity_total_rev_excel += val
            
            share = 0
            if reg_total_rev_excel > 0:
                share = entity_total_rev_excel / reg_total_rev_excel
            
            row['gp_plan'] = int(total_region_gp * share)

            for cat_key in all_cat_keys:
                # PLAN CALCULATION
                # 1. Get Region Cumulative Plan for this Category/Hour
                reg_hourly_plan = 0
                if region in region_daily_data['hourly_breakdown']:
                    rb = region_daily_data['hourly_breakdown'][region]
                    if hour_str in rb:
                        reg_hourly_plan = rb[hour_str].get(cat_key, 0)
                    else:
                        # Fallback: if hour > max available, use max
                        if rb:
                            max_h_str = max(rb.keys())
                            if h > int(max_h_str.split(':')[0]):
                                reg_hourly_plan = rb[max_h_str].get(cat_key, 0)
                
                # 2. Calculate Territory Weight for this Category
                # Weight = EntityMonthly / RegionMonthlyTotal
                entity_monthly = current_entity_plans.get(cat_key, 0)
                reg_monthly_total = region_cat_totals.get(region, {}).get(cat_key, 0)
                
                weight = 0
                if reg_monthly_total > 0:
                    weight = entity_monthly / reg_monthly_total
                
                # 3. Entity Plan = Region Plan * Weight
                plan_rev = reg_hourly_plan * weight
                
                row[f'{cat_key}_plan_revenue'] = int(plan_rev)
                row[f'{cat_key}_plan_gp'] = 0 
                
                # Fact
                f_data = current_facts.get(entity, {}).get(cat_key, {})
                row[f'{cat_key}_fact_revenue'] = f_data.get('rev', 0)
                row[f'{cat_key}_fact_gp'] = f_data.get('gp', 0)
                
            report_data[h].append(row)
            
    return report_data
