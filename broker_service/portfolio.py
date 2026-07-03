# =============================================================================
# portfolio.py — PostgreSQL Portfolio Management
#
# Manages the user_holdings table:
#   - Creates the table on startup if it doesn't exist
#   - Seeds it with sample holdings
#   - Provides fetch functions for the FastAPI endpoint
# =============================================================================

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
import config


def get_db_connection():
    """Open and return a PostgreSQL connection."""
    if config.DATABASE_URL:
        return psycopg2.connect(config.DATABASE_URL)
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )



def setup_portfolio_table():
    """
    Create the user_holdings table if it doesn't exist,
    then seed it with sample data if empty.
    """
    conn = get_db_connection()
    cur  = conn.cursor()

    # ── Create table ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_holdings (
            id            SERIAL PRIMARY KEY,
            ticker        VARCHAR(20)    NOT NULL,
            qty           INTEGER        NOT NULL,
            average_price NUMERIC(10, 2) NOT NULL,
            updated_at    TIMESTAMP      DEFAULT NOW()
        );
    """)

    # ── Seed with sample data if table is empty ────────────────────────────
    cur.execute("SELECT COUNT(*) FROM user_holdings;")
    count = cur.fetchone()[0]

    if count == 0:
        seed_data = [
            ("AAPL",   10, 178.50),
            ("TSLA",    5, 172.30),
            ("GOOGL",   2, 156.80),
            ("MSFT",    8, 415.20),
            ("AMZN",    3, 189.40),
            ("NVDA",    6, 875.00),
            ("RELIANCE.NS", 15, 2850.00),
            ("TCS.NS",   4, 3920.00),
        ]

        cur.executemany(
            "INSERT INTO user_holdings (ticker, qty, average_price) "
            "VALUES (%s, %s, %s);",
            seed_data,
        )
        print(f"[Portfolio] Seeded {len(seed_data)} holdings into user_holdings")

    # ── Create Monitor table ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitored_stocks (
            id            SERIAL PRIMARY KEY,
            user_id       VARCHAR(255)   NOT NULL,
            ticker        VARCHAR(20)    NOT NULL,
            stop_loss     NUMERIC(10, 2) NOT NULL,
            initial_ltp   NUMERIC(10, 2) NOT NULL,
            created_at    TIMESTAMP      DEFAULT NOW(),
            UNIQUE(user_id, ticker)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[Portfolio] Table setup complete [OK]")


def get_all_holdings() -> List[Dict[str, Any]]:
    """
    Fetch all holdings from user_holdings.
    Returns a list of dicts — exactly like a real broker API response.
    """
    conn = get_db_connection()
    cur  = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            ticker,
            qty,
            CAST(average_price AS FLOAT) AS average_price,
            updated_at
        FROM user_holdings
        ORDER BY ticker;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [dict(row) for row in rows]


def get_monitored_stocks(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur  = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ticker, CAST(stop_loss AS FLOAT) AS stop_loss, CAST(initial_ltp AS FLOAT) AS initial_ltp
        FROM monitored_stocks WHERE user_id = %s ORDER BY ticker;
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


def add_monitored_stock(user_id: str, ticker: str, stop_loss: float, initial_ltp: float):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO monitored_stocks (user_id, ticker, stop_loss, initial_ltp)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, ticker) DO UPDATE SET stop_loss = EXCLUDED.stop_loss, initial_ltp = EXCLUDED.initial_ltp;
    """, (user_id, ticker, stop_loss, initial_ltp))
    conn.commit()
    cur.close()
    conn.close()


def remove_monitored_stock(user_id: str, ticker: str):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM monitored_stocks WHERE user_id = %s AND ticker = %s;", (user_id, ticker))
    conn.commit()
    cur.close()
    conn.close()
