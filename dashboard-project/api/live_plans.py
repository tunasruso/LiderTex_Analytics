import psycopg2
from datetime import datetime
import calendar
from api.config_prod import POSTGRES_CONFIG, CORP_TEAM_ID

# Copy from reports_3forms.py to ensure consistency
REGION_TEAMS = {
    'Москва': [
        'e0a42418-6a26-3adc-6c5b-55d431ddfad8', 
        'ac05cdee-3bb8-f9db-f061-687a515b7a44'
    ],
    'Северо-Запад': [
        '2c3965cc-926b-1f5e-4bb6-550aa8a02c6c'
    ],
    'Сибирь-Урал': [
        'be0f2c6f-7839-dd83-c2f1-65aa2bea1ea1', 'b6785fea-e055-ca93-4594-65aa2b3a0267', 
        '52042a38-7201-b7b0-9868-65a622c4a29f', '17b95305-c01e-1d8b-cdc7-65ae4e40a651'
    ],
    'Центр': [
        '944af9fe-3105-3a21-aa95-5f6aefc3a517', '85ad4646-f4fe-cfbb-414e-65aa63d60105', 
        'd6b53d22-d869-6b92-69e7-65ae4d331e0c'
    ],
    'Поволжье': [
        'e1bcfe3e-5b4f-6e4b-83b3-65aa1dd37aab', '126394f7-0570-a22b-873f-59314e2fb541', 
        '670da544-2c37-2c67-7f5b-65ae4e6f0feb'
    ],
    'Юг': [
        'b3f0f476-03f6-7f45-1d48-54230800c268'
    ]
}

# Hourly Distribution Curve (Percentage of Daily Plan per Hour)
# Keys: Region, Values: Dict {hour: percent/100}
# Based on user image
HOURLY_DISTRIBUTION = {
    'Default': {9: 0.08, 10: 0.10, 11: 0.15, 12: 0.15, 13: 0.10, 14: 0.15, 15: 0.15, 16: 0.06, 17: 0.06},
    'Поволжье': {9: 0.15, 10: 0.15, 11: 0.15, 12: 0.15, 13: 0.10, 14: 0.15, 15: 0.08, 16: 0.05, 17: 0.02},
    'Сибирь-Урал': {9: 0.20, 10: 0.15, 11: 0.20, 12: 0.12, 13: 0.20, 14: 0.08, 15: 0.03, 16: 0.02}
}
# Map regions to distribution keys
REGION_DIST_MAP = {
    'Москва': 'Default',
    'Северо-Запад': 'Default',
    'Центр': 'Default',
    'Юг': 'Default',
    'Поволжье': 'Поволжье',
    'Сибирь-Урал': 'Сибирь-Урал',
    'Отдел корпоративных продаж': 'Default'
}

class LivePlanService:
    def __init__(self):
        self.conn = psycopg2.connect(**POSTGRES_CONFIG)

    def __del__(self):
        self.conn.close()

    def get_team_region(self, team_id):
        if team_id == CORP_TEAM_ID:
            return 'Отдел корпоративных продаж'
        for region, teams in REGION_TEAMS.items():
            if team_id in teams:
                return region
        return 'Other'

    def get_working_days(self, year, month):
        """Returns list of status codes (1=Work, 2=Holiday) for the month"""
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT days FROM raw.gr_workdays WHERE year='{year}' AND month='{month}'")
            row = cursor.fetchone()
            if row:
                return [int(x) for x in row[0].split(',')]
            return []

    def get_remaining_working_days(self, date_obj):
        """Calculates involved working days: 
           1. Total working days in month
           2. Working days LEFT (including today)
        """
        year = str(date_obj.year)
        month = str(date_obj.month)
        day = date_obj.day
        
        days_map = self.get_working_days(year, month)
        
        # If no map found, assume standard Mon-Fri
        if not days_map:
            # Fallback logic could be added here, but for now return None or Estimate
            # print(f"Warning: No workday map for {year}-{month}")
            _, num_days = calendar.monthrange(int(year), int(month))
            # Mock map (1=Work, 2=Weekend)
            days_map = []
            for d in range(1, num_days + 1):
                dt = datetime(int(year), int(month), d)
                days_map.append(2 if dt.weekday() >= 5 else 1)

        total_work_days = days_map.count(1)
        
        # Remaining includes TODAY
        # List index is 0-based, so day 1 is index 0
        future_days = days_map[day-1:] 
        remaining_work_days = future_days.count(1)
        
        return total_work_days, remaining_work_days

    def get_monthly_plans(self, year, month):
        """Fetches plans for all users for specific month, aggregated by Region"""
        query = f"""
        SELECT 
            u.team_id,
            pi.category_id, 
            SUM(pi.plan) as total_plan
        FROM raw.gr_payrol p
        JOIN mart.users u ON u.id = p.assigned_user_id
        JOIN raw.gr_payrol_items pi ON pi.salary_id = p.id
        WHERE p.year = '{year}' AND p.month = '{month}'
        AND p.deleted = 0
        GROUP BY u.team_id, pi.category_id
        """
        
        plans_by_region = {}
        
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for team_id, category, value in rows:
                region = self.get_team_region(team_id)
                if region == 'Other': continue
                
                if region not in plans_by_region:
                    plans_by_region[region] = {}
                
                # Normalize keys to match dashboard expectation
                key = category
                if category == 'amount': key = 'revenue'
                elif category == 'dirty_plan': key = 'gp'
                # Add mappings for others if needed strictly, otherwise keep as is
                # The dashboard uses: revenue, gp, resale, per, obliv, vaf, vetosh...
                # Check DB keys: per_retail_sum, etc.
                
                if category == 'per_retail_sum': key = 'per'
                elif category == 'obliv': key = 'obliv' # Same
                elif category == 'vetosh': key = 'vetosh' # Same
                # ... Map others strictly if they differ
                
                plans_by_region[region][key] = plans_by_region[region].get(key, 0) + int(value)

        return plans_by_region

    def calculate_live_metrics(self, region_data, plans, remaining_days, ytd_fact_yesterday, current_hour):
        """
        Enriches region_data with calculated Daily Plan (Target Now).
        
        Logic:
        1. Daily_Plan_Total = (MonthPlan - YTD_Fact_Yesterday) / Remaining_Days
        2. Hourly_Curve = Cumulative Sum of percentages up to Current_Hour
        3. Target_Now = Daily_Plan_Total * Hourly_Curve
        """
        
        # Determine Cumulative Percentage for the current hour
        # Cache cumulative per region
        cumulative_pct_map = {}
        for region_key, dist_key in REGION_DIST_MAP.items():
            dist = HOURLY_DISTRIBUTION.get(dist_key, HOURLY_DISTRIBUTION['Default'])
            cum_pct = 0.0
            # Sum up percentages for hours <= current_hour
            for h, p in dist.items():
                if h <= current_hour:
                    cum_pct += p
            cumulative_pct_map[region_key] = min(cum_pct, 1.0) # Cap at 100%

        for region, metrics in region_data.items():
            r_plan = plans.get(region, {})
            # Get YTD yesterday for this region
            r_ytd = ytd_fact_yesterday.get(region, {})
            
            # Get Cumulative Pct for this region
            hourly_factor = cumulative_pct_map.get(region, 0.0)
            
            for key, val_obj in metrics.items():
                plan_key = key
                if key == 'allsum': plan_key = 'revenue'
                if key == 'china_sum': plan_key = 'china_sum'
                
                month_plan = r_plan.get(plan_key, 0)
                fact_now = val_obj['fact']
                
                # Get Yesterday's YTD Fact specifically for this metric
                # ytd_fact_yesterday has same structure as region_data: {region: {metric: {fact: X}}}
                ytd_val_obj = r_ytd.get(key, {'fact': 0})
                fact_yesterday = ytd_val_obj.get('fact', 0)
                
                # Formula: Daily_Plan_Total = (MonthPlan - Fact_Yesterday) / Remaining_Days
                daily_plan_total = 0
                if remaining_days > 0 and month_plan > fact_yesterday:
                    daily_plan_total = int((month_plan - fact_yesterday) / remaining_days)
                elif remaining_days > 0 and month_plan <= fact_yesterday:
                    daily_plan_total = 0
                
                # Target for Current Hour
                target_now = int(daily_plan_total * hourly_factor)
                
                # Update the object
                val_obj['plan'] = month_plan
                val_obj['daily_plan'] = target_now # This is now "Plan Day (Target Now)"
                
                # Recalculate percent logic (Pace)
                # Percent = Fact / Target_Now
                if target_now > 0:
                    val_obj['pct'] = round((fact_now / target_now) * 100, 1)
                else:
                    # Special case: If target is 0 but we have sales -> High pct? Or 0?
                    # If daily plan is 0 (Month plan matched), then pct is effectively infinite.
                    val_obj['pct'] = 0 if fact_now == 0 else 100.0 # Or mark as done

        return region_data

if __name__ == "__main__":
    # Test
    svc = LivePlanService()
    now = datetime.now()
    # Mock date for testing if needed, or use real
    # now = datetime(2026, 1, 26) 
    
    print(f"--- Live Plans Test for {now.strftime('%Y-%m-%d')} ---")
    
    tot, rem = svc.get_remaining_working_days(now)
    print(f"Working Days: Total={tot}, Remaining={rem}")
    
    plans = svc.get_monthly_plans(now.year, now.month)
    print("\n--- Aggregated Plans (Sample) ---")
    for r, p in list(plans.items())[:2]:
        print(f"{r}: Revenue={p.get('revenue', 0)}, GP={p.get('gp', 0)}")
