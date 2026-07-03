# =============================================================================
# main.py — FastAPI App: REST endpoints + WebSocket server + Background drip
#
# Run with:  python main.py
#            uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# =============================================================================

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Set

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
from portfolio import (
    setup_portfolio_table, get_all_holdings,
    get_monitored_stocks, add_monitored_stock, remove_monitored_stock
)
from velocity import calculate_velocity
from redis_writer import drip_feed
import neutralizer
import zerodha_client
from fastapi.responses import HTMLResponse

# ── Feed Factory ───────────────────────────────────────────────────────────────
# This is where config.FEED_MODULE selects which feed to use.
# To switch to KiteTicker: set FEED_MODULE = "kite" in config.py
def load_feed():
    if config.FEED_MODULE == "yfinance":
        from feed.yfinance_feed import YFinanceFeed
        return YFinanceFeed()
    elif config.FEED_MODULE == "kite":
        from feed.kite_feed import KiteFeed
        return KiteFeed()
    else:
        raise ValueError(f"Unknown feed module: {config.FEED_MODULE}")


# ── Shared State ───────────────────────────────────────────────────────────────
active_tickers:  Dict[str, float] = {}   # { "AAPL": 182.34 }
active_drips:    Dict[str, asyncio.Task] = {}   # { "AAPL": <Task> }
ws_subscribers:  Dict[str, Set[WebSocket]] = {}  # { "AAPL": {ws1, ws2} }


# ── Startup / Shutdown ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("  Brokerage Simulation Service - Starting up")
    print(f"  Feed: {load_feed().get_feed_name()}")
    print("=" * 60)

    # Setup PostgreSQL table (creates + seeds if needed)
    try:
        setup_portfolio_table()
    except Exception as e:
        print(f"[DB] WARNING: Could not connect to PostgreSQL: {e}")
        print("[DB] Portfolio endpoint will return an error until DB is available.")

    print("\n" + "=" * 60)
    print(" [ACTION REQUIRED] LINK ZERODHA ")
    print(" Please click the link below on this computer to log in:")
    print(f" {zerodha_client.get_login_url()}")
    print("=" * 60 + "\n")

    # Start a background broadcaster for all connected WebSocket clients
    asyncio.create_task(broadcast_loop())

    yield  # ← App is running here

    # Cleanup: cancel all running drip tasks
    for task in active_drips.values():
        task.cancel()
    print("[Shutdown] All drip tasks cancelled.")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Brokerage Simulation Service",
    description="Mock brokerage backend for the Stock Portfolio app. "
                "Replace FEED_MODULE in config.py to go live with KiteTicker.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST: Health Check ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "feed": load_feed().get_feed_name(),
        "time": datetime.now().isoformat(),
    }


# ── REST: Portfolio ────────────────────────────────────────────────────────────
@app.get("/portfolio", tags=["Portfolio"])
def get_portfolio():
    try:
        # 1. Try to fetch from real Zerodha account first
        if zerodha_client.is_logged_in():
            data = zerodha_client.fetch_real_holdings()
            return {
                "source": "Zerodha API",
                "count": len(data),
                "holdings": data,
            }
            
        # 2. Fallback to postgres mock data
        holdings = get_all_holdings()
        return {
            "source": "postgresql:user_holdings",
            "count": len(holdings),
            "holdings": holdings,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

# ── REST: Zerodha Auth ─────────────────────────────────────────────────────────
@app.get("/zerodha/auth_url", tags=["Zerodha Auth"])
def get_zerodha_login():
    """Returns the Zerodha Login URL to open in the browser"""
    return {"url": zerodha_client.get_login_url()}

@app.get("/login", tags=["Zerodha Auth"])
def handle_zerodha_callback(request_token: str = None, action: str = None, status: str = None):
    """Callback URL for Zerodha to hit after a successful user login"""
    if not request_token:
        return HTMLResponse("<h1>Login Failed</h1><p>No request token provided by Zerodha.</p>")
        
    success = zerodha_client.generate_session(request_token)
    if success:
        return HTMLResponse(
            "<h1>Login Successful! ✅</h1>"
            "<p>Your Zerodha account is now securely linked to the engine.</p>"
            "<p>You can close this window and return to the Flutter app.</p>"
        )
    else:
        return HTMLResponse("<h1>Login Failed ❌</h1><p>Failed to exchange token with Zerodha.</p>")

# ── REST: Monitor Stocks ───────────────────────────────────────────────────────
class MonitorRequest(BaseModel):
    ticker: str
    stop_loss: float
    initial_ltp: float

@app.get("/monitor/{user_id}", tags=["Monitor"])
def fetch_monitor(user_id: str):
    try:
        stocks = get_monitored_stocks(user_id)
        return {"status": "success", "monitored_stocks": stocks}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

@app.post("/monitor/{user_id}", tags=["Monitor"])
def add_monitor(user_id: str, req: MonitorRequest):
    try:
        add_monitored_stock(user_id, req.ticker.upper(), req.stop_loss, req.initial_ltp)
        return {"status": "success", "message": f"Added {req.ticker} for {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

@app.delete("/monitor/{user_id}/{ticker}", tags=["Monitor"])
def remove_monitor(user_id: str, ticker: str):
    try:
        remove_monitored_stock(user_id, ticker.upper())
        return {"status": "success", "message": f"Removed {ticker} for {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


# ── REST: Start a Ticker Feed ──────────────────────────────────────────────────
@app.post("/feed/start/{ticker}", tags=["Feed"])
async def start_feed(ticker: str):
    """
    Starts a drip-feed for the given ticker.
    Fetches 1m data from yfinance and begins pushing 1 tick/second into Redis.
    """
    ticker = ticker.upper()

    if ticker in active_drips and not active_drips[ticker].done():
        return {"status": "already_running", "ticker": ticker}

    feed = load_feed()
    ticks = feed.get_ticks(ticker)

    if not ticks:
        raise HTTPException(
            status_code=404,
            detail=f"No tick data found for ticker '{ticker}'. "
                   f"Make sure it's a valid yfinance symbol."
        )

    task = asyncio.create_task(drip_feed(ticker, ticks, active_tickers))
    active_drips[ticker] = task

    return {
        "status": "started",
        "ticker": ticker,
        "total_ticks": len(ticks),
        "feed": feed.get_feed_name(),
        "message": f"Dripping {len(ticks)} ticks at 1 tick/second. "
                   f"Connect to ws://localhost:{config.SERVER_PORT}/ws/{ticker}"
    }


# ── REST: Stop a Ticker Feed ───────────────────────────────────────────────────
@app.post("/feed/stop/{ticker}", tags=["Feed"])
async def stop_feed(ticker: str):
    """Stops an active drip-feed for the given ticker."""
    ticker = ticker.upper()

    if ticker not in active_drips or active_drips[ticker].done():
        raise HTTPException(status_code=404, detail=f"No active feed for {ticker}")

    active_drips[ticker].cancel()
    del active_drips[ticker]
    active_tickers.pop(ticker, None)

    return {"status": "stopped", "ticker": ticker}


# ── REST: Velocity ─────────────────────────────────────────────────────────────
@app.get("/velocity/{ticker}", tags=["Analytics"])
def get_velocity(ticker: str):
    """
    Returns the calculated price velocity (change per hour)
    based on the last 60 ticks in Redis.
    """
    ticker = ticker.upper()
    v = calculate_velocity(ticker)

    if v is None:
        return {
            "ticker": ticker,
            "velocity": None,
            "message": "Not enough data yet. Start feed and wait 60 seconds."
        }

    return {
        "ticker": ticker,
        "velocity_per_hour": v,
        "direction": "UP 📈" if v > 0 else ("DOWN 📉" if v < 0 else "FLAT ➡️"),
    }


# ── REST: Active Feeds ─────────────────────────────────────────────────────────
@app.get("/feed/active", tags=["Feed"])
def list_active_feeds():
    return {
        "active": {
            ticker: {"current_price": active_tickers.get(ticker)}
            for ticker, task in active_drips.items()
            if not task.done()
        }
    }


# ── REST: Neutralize ───────────────────────────────────────────────────────────
@app.get("/neutralize/{ticker}", tags=["Analytics"])
def check_neutralize(ticker: str):
    """
    Runs the News-Momentum Verification Engine for a given ticker.
    Call this when a stop-loss is hit to find out if this hedge is safe to buy.
    """
    ticker = ticker.upper()
    try:
        result = neutralizer.verify_hedge_candidate(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neutralization engine error: {str(e)}")



# ── WebSocket: Live Ticks ──────────────────────────────────────────────────────
@app.websocket("/ws/{ticker}")
async def websocket_endpoint(websocket: WebSocket, ticker: str):
    """
    Flutter connects here to receive live ticks.

    Sends JSON every second:
    {
        "ticker": "AAPL",
        "price": 182.34,
        "velocity_per_hour": +12.5,
        "direction": "UP 📈",
        "timestamp": "2024-01-01T12:00:00"
    }

    Auto-starts the drip feed if not already running.
    """
    ticker = ticker.upper()
    await websocket.accept()
    print(f"[WebSocket] Flutter connected for {ticker}")

    # Auto-start the feed if not running
    if ticker not in active_drips or active_drips[ticker].done():
        feed = load_feed()
        ticks = feed.get_ticks(ticker)
        if ticks:
            task = asyncio.create_task(drip_feed(ticker, ticks, active_tickers))
            active_drips[ticker] = task

    # Register this WebSocket
    if ticker not in ws_subscribers:
        ws_subscribers[ticker] = set()
    ws_subscribers[ticker].add(websocket)

    try:
        # Keep the connection alive; the broadcast_loop() sends the data
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print(f"[WebSocket] Flutter disconnected from {ticker}")
    finally:
        ws_subscribers.get(ticker, set()).discard(websocket)


# ── Background: Broadcast Loop ────────────────────────────────────────────────
async def broadcast_loop():
    """
    Runs forever. Every second, sends the latest price + velocity
    to all connected WebSocket clients.
    """
    while True:
        for ticker, subscribers in list(ws_subscribers.items()):
            if not subscribers:
                continue

            price    = active_tickers.get(ticker)
            velocity = calculate_velocity(ticker)

            if price is None:
                continue

            payload = json.dumps({
                "ticker":           ticker,
                "price":            round(price, 4),
                "velocity_per_hour": velocity,
                "direction":        ("UP 📈" if (velocity or 0) > 0
                                     else ("DOWN 📉" if (velocity or 0) < 0
                                           else "FLAT ➡️")),
                "timestamp":        datetime.now().isoformat(),
            })

            dead = set()
            for ws in subscribers:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)

            subscribers -= dead  # Remove disconnected clients

        await asyncio.sleep(1)


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=False,  # Set True for development
    )
