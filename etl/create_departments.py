import sys
import os
import psycopg2
from psycopg2.extras import execute_values

# Add path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config.settings import POSTGRES_CONFIG

# Mapping from Image
DEPARTMENT_MAPPING = {
    'Москва': [
        'Отдел продаж - 214 Общий Москва',
        'Отдел продаж - Москва ТП'
    ],
    'Отдел корпоративных продаж': [
        'Отдел корпоративных продаж'
    ],
    'Поволжье': [
        'Отдел продаж - 217,Оренбург,Казань,Уфа',
        'Отдел продаж - 217,Самара,Пенза,Ульяновск,Саратов',
        'Отдел продаж - 217 Поволжье'
    ],
    'Северо-Запад': [
        'Отдел продаж - 210 Санкт-Петербург'
    ],
    'Сибирь-Урал': [
        'Отдел продаж - 218,ЕКБ,Челябинск,Пермь',
        'Отдел продаж - 218,Красноярск,Тюмень,Омск',
        'Отдел продаж - 218,Новосибирск',
        'Отдел продаж - 218 Сибирь-Урал'
    ],
    'Центр': [
        'Отдел продаж - 222,Воронеж,Орел',
        'Отдел продаж - 222,Иваново,Нижний',
        'Отдел продаж - 222 Центр'
    ],
    'Юг': [
        'Отдел продаж - 211 Юг'
    ]
}

def create_departments():
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    # 1. Create Tables
    print("Creating mart.departments and links...")
    cur.execute("CREATE SCHEMA IF NOT EXISTS mart")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mart.departments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mart.team_department_map (
            team_name VARCHAR(255) PRIMARY KEY,
            department_id INTEGER REFERENCES mart.departments(id)
        )
    """)
    
    # 2. Insert Departments
    deps = list(DEPARTMENT_MAPPING.keys())
    # insert ignore or on conflict do nothing
    execute_values(cur, """
        INSERT INTO mart.departments (name) VALUES %s
        ON CONFLICT (name) DO NOTHING
    """, [(d,) for d in deps])
    
    # 3. Get Dep IDs
    cur.execute("SELECT name, id FROM mart.departments")
    dep_map = {row[0]: row[1] for row in cur.fetchall()}
    
    # 4. Insert Mappings
    mappings = []
    for dep_name, teams in DEPARTMENT_MAPPING.items():
        dep_id = dep_map[dep_name]
        for team in teams:
            mappings.append((team, dep_id))
            
    execute_values(cur, """
        INSERT INTO mart.team_department_map (team_name, department_id) VALUES %s
        ON CONFLICT (team_name) DO UPDATE SET department_id = EXCLUDED.department_id
    """, mappings)
    
    # 5. Create View dim_teams
    cur.execute("""
        CREATE OR REPLACE VIEW mart.dim_teams AS
        SELECT 
            t.id as team_id,
            t.name as team_name,
            d.id as department_id,
            d.name as department_name
        FROM raw.teams t
        LEFT JOIN mart.team_department_map m ON t.name = m.team_name
        LEFT JOIN mart.departments d ON m.department_id = d.id
    """)
    
    conn.commit()
    print("✅ Departments and Links created successfully.")
    conn.close()

if __name__ == "__main__":
    create_departments()
