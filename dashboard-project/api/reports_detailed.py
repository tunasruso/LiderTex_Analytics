import psycopg2
from psycopg2.extras import RealDictCursor
from api.config_prod import POSTGRES_CONFIG, CORP_TEAM_ID
from api.reports_3forms import REGION_TEAMS, TARGET_STAGES

# Format for SQL IN clause
TARGET_STAGES_SQL = ",".join([f"'{s}'" for s in TARGET_STAGES])

def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)

def get_hierarchy():
    """
    Returns a nested dictionary:
    {
        "RegionName": {
            "teams": [
                {"id": "...", "name": "...", "managers": [{"id": "...", "name": "..."}]}
            ]
        }
    }
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    hierarchy = {}
    
    # Pre-fetch all team names
    all_team_ids = []
    for r, t_ids in REGION_TEAMS.items():
        all_team_ids.extend(t_ids)
    all_team_ids.append(CORP_TEAM_ID)
    
    # Select Teams
    ids_str = "','".join(all_team_ids)
    cursor.execute(f"SELECT id, name FROM raw.teams WHERE id IN ('{ids_str}')")
    teams_map = {row['id']: row['name'] for row in cursor.fetchall()}
    
    # Select Users for these teams
    cursor.execute(f"SELECT id, team_id, first_name, last_name FROM raw.users WHERE team_id IN ('{ids_str}') AND deleted=0 AND status='Active'")
    users_rows = cursor.fetchall()
    conn.close()
    
    # Organize
    for region, t_ids in REGION_TEAMS.items():
        hierarchy[region] = []
        for tid in t_ids:
            if tid not in teams_map: continue
            
            # Find users for this team
            team_users = []
            for u in users_rows:
                if u['team_id'] == tid:
                    full_name = f"{u['last_name']} {u['first_name']}".strip()
                    team_users.append({'id': u['id'], 'name': full_name})
            
            # Sort users by name
            team_users.sort(key=lambda x: x['name'])
            
            hierarchy[region].append({
                'id': tid,
                'name': teams_map[tid],
                'managers': team_users
            })
            
    return hierarchy

def get_detailed_report(date, hour, region=None, team_id=None, manager_id=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    date_start = f"{date} 00:00:00"
    date_end = f"{date} {hour:02d}:00:00"
    
    where_clauses = [
        "productsale.deleted = 0",
        "opportunities.deleted = 0",
        f"opportunities.sales_stage IN ({TARGET_STAGES_SQL})"
    ]
    
    # Audit Logic (Time Travel)
    audit_subquery = f"""
    opportunities.id IN (
        SELECT parent_id FROM raw.opportunities_audit 
        WHERE opportunities_audit.parent_id = opportunities.id 
        AND opportunities_audit.date_created BETWEEN '{date_start}' AND '{date_end}'
        AND opportunities_audit.after_value_string IN ({TARGET_STAGES_SQL})
        AND (opportunities_audit.before_value_string NOT IN ({TARGET_STAGES_SQL}) OR opportunities_audit.before_value_string IS NULL)
    )
    """
    where_clauses.append(audit_subquery)
    
    # Filters
    if manager_id:
        where_clauses.append(f"users.id = '{manager_id}'")
    elif team_id:
        where_clauses.append(f"teams.id = '{team_id}'")
    elif region and region in REGION_TEAMS:
        r_ids = REGION_TEAMS[region]
        r_str = "','".join(r_ids)
        where_clauses.append(f"teams.id IN ('{r_str}')")
    else:
        # Default: All regions + Corp? Or just All Regions.
        # Let's show everything if no filter.
        all_ids = []
        for ids in REGION_TEAMS.values(): all_ids.extend(ids)
        all_ids.append(CORP_TEAM_ID)
        all_str = "','".join(all_ids)
        where_clauses.append(f"teams.id IN ('{all_str}')")

    where_sql = " AND ".join(where_clauses)
    
    # Replaced IF -> CASE WHEN
    # Replaced IFNULL -> COALESCE
    query = f"""
    SELECT 
        teams.name as team_name,
        CONCAT(users.last_name, ' ', users.first_name) as manager_name,
        
        -- METRICS (Same as debug_volga)
        SUM(CASE WHEN productcat.id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4') OR productcat.parent_category_id IN ('42ac50da-efa0-9baa-51cc-50efc73a1fc6','3fb2004f-ffe1-67b3-d797-65aa1f509de3','8d432105-5ecf-3fc7-8242-62b32dc497e8','f35511c6-0a8c-6ece-02cb-62b32d67dbf4') THEN productsale.count ELSE 0 END) AS per,
        SUM(CASE WHEN productcat.id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e') OR productcat.parent_category_id IN ('b7ece599-c211-52fd-2f30-5c21f1a851ca','bf4581e7-681a-75ce-2796-62baa764dcf7','d716ff1c-96e4-3451-f8a8-50efe14e851e') THEN productsale.count ELSE 0 END) AS obliv,
        SUM(CASE WHEN productcat.id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d') OR productcat.parent_category_id IN ('74bf507d-a38e-ea92-6d81-626a9915ed7d') THEN productsale.count ELSE 0 END) AS vaf,
        SUM(CASE WHEN productcat.id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1') OR productcat.parent_category_id IN ('c5d5d05c-a672-08bb-5f3b-59cb95299ef3','5ddd11ee-f0fe-39b3-8483-6613bc528163','aaa602e1-a42d-5972-7830-6736fd16cef1') THEN productsale.count ELSE 0 END) AS vetosh,
        SUM(CASE WHEN productcat.id IN ('56e605af-31df-9377-5322-50f0124b66d1') OR productcat.parent_category_id IN ('56e605af-31df-9377-5322-50f0124b66d1') THEN productsale.count ELSE 0 END) AS ruk,
        SUM(CASE WHEN productcat.id IN ('d2ca8d1d-e078-4276-c733-5488539d35e6','ad0cafb2-82e3-bd9f-7de8-643e911e5bff','2764ae01-c9f7-7b3e-78f4-643e91aafa06') THEN productsale.count ELSE 0 END) AS stretch,
        SUM(CASE WHEN productcat.id IN ('e0fcedd5-485c-e14d-9a80-54885389b508') OR productcat.parent_category_id IN ('e0fcedd5-485c-e14d-9a80-54885389b508') THEN productsale.count ELSE 0 END) AS bugs,
        SUM(CASE WHEN productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0') THEN productsale.count ELSE 0 END) AS china_pcs,
        SUM(CASE WHEN productcat.id IN ('5502e046-af74-daca-00cc-67f7c90060d0') OR productcat.parent_category_id IN ('5502e046-af74-daca-00cc-67f7c90060d0') THEN productsale.amount ELSE 0 END) AS china_rub,
        SUM(CASE WHEN product.own_prod = 0 THEN productsale.amount ELSE 0 END) as resale_rub,
        SUM(productsale.amount) AS allsum,
        SUM(productsale.amount) as gp
        
    FROM raw.opportunities
    INNER JOIN raw.productsale ON productsale.opportunity_id = opportunities.id 
    INNER JOIN raw.product ON productsale.product_id = product.id 
    INNER JOIN raw.productcat ON productcat.id = product.category_id 
    LEFT JOIN raw.users ON users.id = opportunities.assigned_user_id
    LEFT JOIN raw.teams ON teams.id = users.team_id
    WHERE {where_sql}
    GROUP BY teams.name, manager_name
    ORDER BY teams.name, manager_name
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows
