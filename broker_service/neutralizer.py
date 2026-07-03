from typing import Dict, Any, Optional
import velocity
import news_engine
from redis_writer import get_redis_client, get_last_n_ticks

def verify_hedge_candidate(ticker: str) -> Dict[str, Any]:
    """
    The News-Momentum Verification Engine.
    Prevents the "Buy on Rumor, Sell on News" trap by ensuring that 
    the live price action and volume agree with the positive news.
    """
    print(f"\n[Neutralizer] Analyzing hedge candidate: {ticker}")
    
    # 1. Fetch News Sentiment
    print(f"[Neutralizer]   -> Fetching news sentiment...")
    news_data = news_engine.fetch_company_news(ticker)
    sentiment = news_data.get("sentiment_score", 0.0)
    
    if sentiment < 0.5:
        return {
            "status": "REJECTED",
            "reason": f"News isn't positive enough (Score: {sentiment})",
            "ticker": ticker
        }
    print(f"[Neutralizer]   -> PASSED: Positive News Found (Score: {sentiment})")

    # 2. Check Live Market Data (VWAP)
    print(f"[Neutralizer]   -> Calculating VWAP...")
    vwap = velocity.calculate_vwap(ticker)
    
    if vwap is None:
        return {
            "status": "WAITING",
            "reason": "Not enough tick data to calculate VWAP yet.",
            "ticker": ticker
        }

    # Get current price
    client = get_redis_client()
    ticks = get_last_n_ticks(client, ticker, 1)
    if not ticks:
        return {
            "status": "WAITING",
            "reason": "No live price available.",
            "ticker": ticker
        }
    
    current_price = ticks[-1]["price"]
    
    if current_price < vwap:
        return {
            "status": "REJECTED",
            "reason": f"TRAP DETECTED: Price ({current_price}) is below VWAP ({vwap}). Smart money is selling.",
            "ticker": ticker
        }
    print(f"[Neutralizer]   -> PASSED: Price ({current_price}) > VWAP ({vwap})")

    # 3. Check Relative Volume (RVOL)
    print(f"[Neutralizer]   -> Checking Relative Volume...")
    rvol = velocity.calculate_relative_volume(ticker)
    
    if rvol is None:
        return {
            "status": "WAITING",
            "reason": "Not enough volume data yet.",
            "ticker": ticker
        }
        
    if rvol < 1.1: # Expecting at least a 10% surge in volume on news
        return {
            "status": "REJECTED",
            "reason": f"TRAP DETECTED: Low relative volume ({rvol}x). Fake price spike.",
            "ticker": ticker
        }
    print(f"[Neutralizer]   -> PASSED: Strong Volume Surge ({rvol}x normal)")

    # 4. Check Price Velocity (is it actively climbing?)
    print(f"[Neutralizer]   -> Checking Price Velocity...")
    vel = velocity.calculate_velocity(ticker)
    
    if vel is not None and vel < 0:
         return {
            "status": "REJECTED",
            "reason": "TRAP DETECTED: Price is already dropping despite the news.",
            "ticker": ticker
        }
    print(f"[Neutralizer]   -> PASSED: Positive upward momentum.")

    # 5. APPROVED!
    return {
        "status": "APPROVED",
        "reason": "High volume, price above VWAP, positive news. Safe to suggest.",
        "ticker": ticker,
        "metrics": {
            "sentiment": sentiment,
            "vwap": vwap,
            "current_price": current_price,
            "rvol": rvol,
            "velocity": vel
        }
    }
