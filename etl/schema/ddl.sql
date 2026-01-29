-- Create Schema
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

-- 1. TEAMS
CREATE TABLE IF NOT EXISTS raw.teams (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    assigned_user_id UUID
);

-- 2. USERS
CREATE TABLE IF NOT EXISTS raw.users (
    id UUID PRIMARY KEY,
    user_name VARCHAR(60),
    first_name VARCHAR(30),
    last_name VARCHAR(30),
    is_admin BOOLEAN,
    status VARCHAR(25),
    team_id UUID,
    deleted BOOLEAN DEFAULT FALSE,
    date_entered TIMESTAMP,
    date_modified TIMESTAMP
);

-- 3. PRODUCT CATEGORIES
CREATE TABLE IF NOT EXISTS raw.productcat (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    parent_category_id UUID,
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- 4. PRODUCTS
CREATE TABLE IF NOT EXISTS raw.product (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    category_id UUID,
    own_prod INT, -- Keeping as int for simple filtering (0/1)
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- 5. OPPORTUNITIES (Base + CSTM flattened for analytics convenience, or separate?)
-- Let's keep separate to match source exactly for the "raw" layer, safer for ETL.
CREATE TABLE IF NOT EXISTS raw.opportunities (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    date_closed DATE,
    assigned_user_id UUID,
    sales_stage VARCHAR(50),
    opportunity_type VARCHAR(255),
    amount NUMERIC,
    deleted BOOLEAN DEFAULT FALSE
);

-- 6. OPPORTUNITIES_AUDIT
CREATE TABLE IF NOT EXISTS raw.opportunities_audit (
    id UUID PRIMARY KEY,
    parent_id UUID,
    date_created TIMESTAMP,
    field_name VARCHAR(100),
    before_value_string VARCHAR(255),
    after_value_string VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_audit_parent ON raw.opportunities_audit(parent_id);
CREATE INDEX IF NOT EXISTS idx_audit_date ON raw.opportunities_audit(date_created);

-- 7. PRODUCT SALE (Line Items)
CREATE TABLE IF NOT EXISTS raw.productsale (
    id UUID PRIMARY KEY,
    opportunity_id UUID,
    product_id UUID,
    count NUMERIC,
    amount NUMERIC,
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_ps_opp ON raw.productsale(opportunity_id);

-- 8. META (Sync State)
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.sync_state (
    table_name VARCHAR(255) PRIMARY KEY,
    last_sync_timestamp TIMESTAMP
);

-- 9. PLANS (Payroll)
CREATE TABLE IF NOT EXISTS raw.gr_payrol (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    year VARCHAR(10),
    month VARCHAR(10),
    assigned_user_id UUID,
    date_entered TIMESTAMP,
    date_modified TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- 10. PLAN ITEMS
CREATE TABLE IF NOT EXISTS raw.gr_payrol_items (
    id UUID PRIMARY KEY,
    salary_id UUID, 
    category_id UUID,
    plan INTEGER,
    checked INTEGER
);

-- 11. WORKDAYS
CREATE TABLE IF NOT EXISTS raw.gr_workdays (
    year VARCHAR(10),
    month VARCHAR(10),
    days TEXT,
    PRIMARY KEY (year, month)
);
