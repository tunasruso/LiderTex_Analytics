from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import reports_3forms
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
async def get_data():
    now = datetime.now()
    # For demo/debug, use fixed date or current date
    # target_date = now.strftime("%Y-%m-%d")
    target_date = "2026-01-26" # Locked to user context
    hour = 14 # Locked to user context
    
    # Calculate yesterday
    current_dt = datetime.strptime(target_date, "%Y-%m-%d")
    yesterday_dt = current_dt - timedelta(days=1)
    yesterday_date = yesterday_dt.strftime("%Y-%m-%d")
    
    try:
        current_data = reports_3forms.get_report_form1(target_date, hour)
        yesterday_data = reports_3forms.get_report_form1(yesterday_date, hour)
        
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

if __name__ == "__main__":
    import uvicorn
    print("Starting LiderTex Analytics Dashboard...")
    print("Open http://127.0.0.1:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
