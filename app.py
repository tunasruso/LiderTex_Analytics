from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import reports_3forms
import reports_detailed
import plans_report
import daily_plans
import excel_plans_report
import hourly_analytics
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/data")
async def get_data(hour: int = 14, region: str = None, team_id: str = None, manager_id: str = None, date: str = None):
    today_str = datetime.now().strftime("%Y-%m-%d")
    if not date:
        date = today_str # Default to today
    
    target_date = date
    # hour is passed as arg
    
    # Calculate yesterday
    current_dt = datetime.strptime(target_date, "%Y-%m-%d")
    yesterday_dt = current_dt - timedelta(days=1)
    yesterday_date = yesterday_dt.strftime("%Y-%m-%d")
    
    try:
        current_data = reports_3forms.get_report_form1(target_date, hour, region, team_id, manager_id)
        yesterday_data = reports_3forms.get_report_form1(yesterday_date, hour, region, team_id, manager_id)
        
        return {
            "meta": {
                "date": target_date,
                "hour": hour,
                "timestamp": now.isoformat()
            },
            "data": current_data,
            "comparison": yesterday_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        return "<h1>Error: templates/index.html not found</h1>"
    with open(template_path, encoding="utf-8") as f:
        return f.read()

@app.get("/details", response_class=HTMLResponse)
async def read_details():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html") # Reuse index for now, or new file
    # User wants a new tab. I'll create templates/details.html.
    # But for now, let's point to details.html
    template_path = os.path.join(os.path.dirname(__file__), "templates", "details.html")
    if not os.path.exists(template_path):
        return "<h1>Error: templates/details.html not found</h1>"
    with open(template_path, encoding="utf-8") as f:
        return f.read()

@app.get("/api/hierarchy")
async def get_hierarchy():
    try:
        return reports_detailed.get_hierarchy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/details")
async def get_details(region: str=None, team_id: str=None, manager_id: str=None, date: str=None, hour: int=14):
    if not date: date = "2026-01-26"
    try:
        return reports_detailed.get_detailed_report(date, hour, region, team_id, manager_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plans")
async def get_plans(year: int = None, month: int = None):
    """Get sales plans by region for a specific month"""
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    try:
        return plans_report.get_plans_by_region(year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/daily-plans")
async def get_daily_plans(date: str = None):
    """Get daily plan breakdown by hour for a specific date"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        return daily_plans.get_daily_plans_breakdown(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel-plans/territories")
async def get_excel_territories_plans(year: int = None, month: int = None, region: str = None):
    """Get Excel-based territory plans"""
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    try:
        return excel_plans_report.get_territories_plans(year, month, region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel-plans/warehouses")
async def get_excel_warehouses_plans(year: int = None, month: int = None, region: str = None):
    """Get Excel-based warehouse plans"""
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    try:
        return excel_plans_report.get_warehouses_plans(year, month, region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hourly-analytics")
async def get_hourly_analytics_endpoint(date: str = None):
    """Get Hourly Plan vs Fact by Territory"""
    from fastapi import Query
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        # Run in threadpool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, hourly_analytics.get_hourly_report_data, date)
        return dict(data) # Ensure it returns JSON serializable dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans", response_class=HTMLResponse)
async def read_plans():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "plans.html")
    if not os.path.exists(template_path):
        return "<h1>Error: templates/plans.html not found</h1>"
    with open(template_path, encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    print("Starting LiderTex Analytics Dashboard...")
    print("Open http://127.0.0.1:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
