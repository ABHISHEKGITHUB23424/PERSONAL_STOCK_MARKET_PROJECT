# =============================================================================
# create_db.py — Python-based PostgreSQL database setup
# Run this ONCE before starting main.py
#
# Usage:  python create_db.py
# =============================================================================

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def try_connect(password: str):
    """Try connecting to PostgreSQL with the given password."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password=password,
    )


def main():
    # ── Step 1: Try to connect ────────────────────────────────────────────────
    conn = None
    for pwd in ["abhi", "Abhi"]:
        try:
            conn = try_connect(pwd)
            print(f"✓ Connected to PostgreSQL with password: '{pwd}'")
            # Save the working password to config.py
            update_config_password(pwd)
            break
        except psycopg2.OperationalError as e:
            print(f"✗ Password '{pwd}' failed: {e}")

    if conn is None:
        print("\n❌ Could not connect to PostgreSQL.")
        print("   Please check that PostgreSQL is running and the password is correct.")
        print("   Edit DB_PASSWORD in broker_service/config.py manually.")
        return

    # ── Step 2: Create database ───────────────────────────────────────────────
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        cur.execute("CREATE DATABASE stock_portfolio;")
        print("✓ Database 'stock_portfolio' created")
    except psycopg2.errors.DuplicateDatabase:
        print("✓ Database 'stock_portfolio' already exists — skipping")

    cur.close()
    conn.close()

    # ── Step 3: Connect to the new database and create table ──────────────────
    from config import DB_PASSWORD
    conn2 = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password=DB_PASSWORD,
        dbname="stock_portfolio",
    )
    cur2 = conn2.cursor()

    cur2.execute("""
        CREATE TABLE IF NOT EXISTS user_holdings (
            id            SERIAL PRIMARY KEY,
            ticker        VARCHAR(20)    NOT NULL,
            qty           INTEGER        NOT NULL,
            average_price NUMERIC(10, 2) NOT NULL,
            updated_at    TIMESTAMP      DEFAULT NOW()
        );
    """)
    print("✓ Table 'user_holdings' created (or already exists)")

    # ── Step 4: Seed data ─────────────────────────────────────────────────────
    cur2.execute("SELECT COUNT(*) FROM user_holdings;")
    count = cur2.fetchone()[0]

    if count == 0:
        seed = [
            ("AAPL",         10, 178.50),
            ("TSLA",          5, 172.30),
            ("GOOGL",         2, 156.80),
            ("MSFT",          8, 415.20),
            ("AMZN",          3, 189.40),
            ("NVDA",          6, 875.00),
            ("RELIANCE.NS",  15, 2850.00),
            ("TCS.NS",        4, 3920.00),
        ]
        cur2.executemany(
            "INSERT INTO user_holdings (ticker, qty, average_price) VALUES (%s, %s, %s);",
            seed
        )
        print(f"✓ Seeded {len(seed)} sample holdings into user_holdings")
    else:
        print(f"✓ user_holdings already has {count} rows — skipping seed")

    conn2.commit()

    # ── Step 5: Verify ────────────────────────────────────────────────────────
    cur2.execute("SELECT ticker, qty, average_price FROM user_holdings ORDER BY ticker;")
    rows = cur2.fetchall()
    print("\n── Current Holdings ──────────────────────────")
    print(f"  {'Ticker':<15} {'Qty':>5}  {'Avg Price':>12}")
    print(f"  {'-'*15}  {'-'*5}  {'-'*12}")
    for row in rows:
        print(f"  {row[0]:<15} {row[1]:>5}  {row[2]:>12}")

    cur2.close()
    conn2.close()

    print("\n✅ Database setup complete!")
    print("   You can now run:  python main.py")


def update_config_password(password: str):
    """Update the DB_PASSWORD in config.py with the working password."""
    import re
    with open("config.py", "r") as f:
        content = f.read()

    # Replace the DB_PASSWORD line
    updated = re.sub(
        r'DB_PASSWORD\s*=\s*".*?"',
        f'DB_PASSWORD = "{password}"',
        content
    )

    with open("config.py", "w") as f:
        f.write(updated)

    print(f"✓ Updated config.py with working password: '{password}'")


if __name__ == "__main__":
    main()
