-- =============================================================================
-- setup_db.sql — Run this ONCE to create the database and table
-- 
-- How to run:
--   Open pgAdmin or psql and run this file, OR:
--   psql -U postgres -f setup_db.sql
-- =============================================================================

-- Step 1: Create the database (run this as superuser)
-- If it already exists, this will error — that's fine, just skip it.
CREATE DATABASE stock_portfolio;

-- Step 2: Connect to it
\c stock_portfolio;

-- Step 3: Create the user_holdings table
CREATE TABLE IF NOT EXISTS user_holdings (
    id            SERIAL PRIMARY KEY,
    ticker        VARCHAR(20)    NOT NULL,
    qty           INTEGER        NOT NULL,
    average_price NUMERIC(10, 2) NOT NULL,
    updated_at    TIMESTAMP      DEFAULT NOW()
);

-- Step 4: Seed with sample portfolio data
INSERT INTO user_holdings (ticker, qty, average_price) VALUES
    ('AAPL',         10, 178.50),
    ('TSLA',          5, 172.30),
    ('GOOGL',         2, 156.80),
    ('MSFT',          8, 415.20),
    ('AMZN',          3, 189.40),
    ('NVDA',          6, 875.00),
    ('RELIANCE.NS',  15, 2850.00),
    ('TCS.NS',        4, 3920.00)
ON CONFLICT DO NOTHING;

-- Verify
SELECT * FROM user_holdings;
