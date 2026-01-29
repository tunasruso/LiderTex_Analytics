-- Excel Plans Schema - mart schema for imported Excel sales plans

-- 1. Territories Plan
CREATE TABLE IF NOT EXISTS mart.excel_plans_territories (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    region VARCHAR(255),
    territory VARCHAR(255),  -- Manager/territory name
    product_group VARCHAR(255),  -- ПЕРЧАТКИ, ОБЛИВ, etc.
    metric_type VARCHAR(50),  -- 'revenue', 'quantity', 'gp'
    plan_value NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(year, month, region, territory, product_group, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_excel_territories_date 
    ON mart.excel_plans_territories(year, month, region);
CREATE INDEX IF NOT EXISTS idx_excel_territories_territory 
    ON mart.excel_plans_territories(territory);
CREATE INDEX IF NOT EXISTS idx_excel_territories_product 
    ON mart.excel_plans_territories(product_group);

-- 2. Warehouses Plan
CREATE TABLE IF NOT EXISTS mart.excel_plans_warehouses (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    region VARCHAR(255),
    warehouse VARCHAR(255),  -- Склад name
    product_group VARCHAR(255),
    metric_type VARCHAR(50),  -- 'revenue', 'quantity', 'gp'
    plan_value NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(year, month, region, warehouse, product_group, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_excel_warehouses_date 
    ON mart.excel_plans_warehouses(year, month, region);
CREATE INDEX IF NOT EXISTS idx_excel_warehouses_warehouse 
    ON mart.excel_plans_warehouses(warehouse);
CREATE INDEX IF NOT EXISTS idx_excel_warehouses_product 
    ON mart.excel_plans_warehouses(product_group);
