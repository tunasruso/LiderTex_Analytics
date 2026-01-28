from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import date

from .database import get_db, Base, engine
from .models import Sale

# Create tables if they don't exist (for dev/demo purposes)
# In production, use Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sales Dashboard API")

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "https://dashboard-project.vercel.app",
    "*" # Allow all for simplicity in this demo, restrict in prod
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/data")
def get_all_data(db: Session = Depends(get_db)):
    sales = db.query(Sale).order_by(Sale.date.desc()).limit(100).all()
    return sales

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    # Total Revenue
    total_sales = db.query(func.sum(Sale.amount)).scalar() or 0
    
    # Sales by Region
    sales_by_region = db.query(
        Sale.region, 
        func.sum(Sale.amount).label("total")
    ).group_by(Sale.region).all()
    
    # Sales by Product (Top 5)
    top_products = db.query(
        Sale.product,
        func.sum(Sale.amount).label("total")
    ).group_by(Sale.product).order_by(func.sum(Sale.amount).desc()).limit(5).all()
    
    # Sales Trend (Daily)
    trend = db.query(
        Sale.date,
        func.sum(Sale.amount).label("total")
    ).group_by(Sale.date).order_by(Sale.date).all()

    return {
        "total_revenue": total_sales,
        "by_region": [{"region": r, "amount": float(a)} for r, a in sales_by_region],
        "top_products": [{"product": p, "amount": float(a)} for p, a in top_products],
        "trend": [{"date": d.isoformat(), "amount": float(a)} for d, a in trend]
    }

@app.get("/api/data/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale
