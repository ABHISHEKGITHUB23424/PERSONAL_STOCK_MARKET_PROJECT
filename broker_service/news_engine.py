import requests
import config
from typing import Dict, Any

def fetch_company_news(ticker: str) -> Dict[str, Any]:
    """
    Fetches the latest news and sentiment for a company.
    This is a mock implementation that simulates an API call to Finnhub or MarketAux.
    In production, replace this with the actual API call using config.NEWS_API_KEY.
    """
    # Simulate an API call latency
    import time
    time.sleep(0.5)

    # We strip the '.NS' or '.BSE' for the US-based news APIs
    clean_ticker = ticker.split('.')[0]
    
    url = f"https://finnhub.io/api/v1/company-news?symbol={clean_ticker}&from=2023-01-01&to=2023-01-31&token={config.FINNHUB_API_KEY}"
    
    try:
        # 1. First fetch the news articles
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            news_items = response.json()
            if news_items and len(news_items) > 0:
                latest_headline = news_items[0].get('headline', 'No headline')
                
                # 2. To get sentiment, Finnhub has a news sentiment endpoint
                sentiment_url = f"https://finnhub.io/api/v1/news-sentiment?symbol={clean_ticker}&token={config.FINNHUB_API_KEY}"
                sent_resp = requests.get(sentiment_url, timeout=5)
                
                score = 0.5  # Default neutral
                if sent_resp.status_code == 200:
                    sent_data = sent_resp.json()
                    # Calculate a simple 0.0 to 1.0 score based on bullish vs bearish percent
                    bullish = sent_data.get('sentiment', {}).get('bullishPercent', 0.5)
                    score = bullish
                
                print(f"[NewsEngine] Successfully fetched live news for {clean_ticker}")
                return {
                    "ticker": ticker,
                    "headline": latest_headline,
                    "sentiment_score": score,
                    "source": "Finnhub"
                }
    except Exception as e:
        print(f"[NewsEngine] Failed to fetch live news: {e}")

    print(f"[NewsEngine] Falling back to mock sentiment for {clean_ticker}")
    return {
        "ticker": ticker,
        "headline": f"{clean_ticker} signs major new strategic partnership",
        "sentiment_score": 0.85,  # Fallback to a positive mock score
        "source": "MockNewsAPI"
    }

def get_news_sentiment(ticker: str) -> float:
    """Returns just the sentiment score for the given ticker."""
    news_data = fetch_company_news(ticker)
    return news_data.get("sentiment_score", 0.0)
