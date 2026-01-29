from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
import asyncio
import os

from api.database import get_db, Base, engine
from api.models import Sale

# Import migrated logic
import api.reports_3forms as reports_3forms
import api.reports_detailed as reports_detailed
import api.plans_report as plans_report
import api.daily_plans as daily_plans
import api.excel_plans_report as excel_plans_report
import api.hourly_analytics as hourly_analytics

# Base table creation (for Sale model if still needed)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Database initialization failed: {e}")

app = FastAPI(title="LiderTex Analytics API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/debug-env")
def debug_env():
    import pymysql
    import psycopg2
    from api.config_prod import DB_CONFIG, POSTGRES_CONFIG
    
    status = {
        "env_vars": {
            "DB_HOST": "SET" if os.getenv("DB_HOST") else "MISSING",
            "DB_USER": "SET" if os.getenv("DB_USER") else "MISSING"
        },
        "connections": {}
    }
    
    # Test Postgres
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        conn.close()
        status["connections"]["postgres"] = "OK"
    except Exception as e:
        status["connections"]["postgres"] = f"ERROR: {str(e)}"
        
    return status

# --- Reports Endpoints (from original app.py) ---

@app.get("/api/data")
async def get_data(hour: int = 14, region: str = None, team_id: str = None, manager_id: str = None, date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    current_dt = datetime.strptime(date, "%Y-%m-%d")
    yesterday_dt = current_dt - timedelta(days=1)
    yesterday_date = yesterday_dt.strftime("%Y-%m-%d")
    
    try:
        # Run sync functions in threadpool
        loop = asyncio.get_event_loop()
        current_data = await loop.run_in_executor(None, reports_3forms.get_report_form1, date, hour, region, team_id, manager_id)
        yesterday_data = await loop.run_in_executor(None, reports_3forms.get_report_form1, yesterday_date, hour, region, team_id, manager_id)
        
        return {
            "meta": {
                "date": date,
                "hour": hour,
                "timestamp": datetime.now().isoformat()
            },
            "data": current_data,
            "comparison": yesterday_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hierarchy")
async def get_hierarchy():
    try:
        return reports_detailed.get_hierarchy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/details")
async def get_details(region: str=None, team_id: str=None, manager_id: str=None, date: str=None, hour: int=14):
    if not date: 
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        return reports_detailed.get_detailed_report(date, hour, region, team_id, manager_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plans")
async def get_plans(year: int = None, month: int = None):
    now = datetime.now()
    if not year: year = now.year
    if not month: month = now.month
    try:
        return plans_report.get_plans_by_region(year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/daily-plans")
async def get_daily_plans(date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        return daily_plans.get_daily_plans_breakdown(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel-plans/territories")
async def get_excel_territories_plans(year: int = None, month: int = None, region: str = None):
    now = datetime.now()
    if not year: year = now.year
    if not month: month = now.month
    try:
        return excel_plans_report.get_territories_plans(year, month, region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel-plans/warehouses")
async def get_excel_warehouses_plans(year: int = None, month: int = None, region: str = None):
    now = datetime.now()
    if not year: year = now.year
    if not month: month = now.month
    try:
        return excel_plans_report.get_warehouses_plans(year, month, region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hourly-analytics")
async def get_hourly_analytics_endpoint(date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, hourly_analytics.get_hourly_report_data, date)
        return dict(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
