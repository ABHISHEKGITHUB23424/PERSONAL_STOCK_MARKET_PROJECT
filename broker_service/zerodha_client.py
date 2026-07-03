import config
from kiteconnect import KiteConnect

# Singleton state
_kite = None
_access_token = None

def get_kite_instance():
    global _kite
    if _kite is None:
        _kite = KiteConnect(api_key=config.KITE_API_KEY)
        if _access_token:
            _kite.set_access_token(_access_token)
    return _kite

def get_login_url():
    kite = get_kite_instance()
    return kite.login_url()

def generate_session(request_token: str):
    global _access_token
    kite = get_kite_instance()
    
    # Exchanging request token for an access token
    try:
        data = kite.generate_session(request_token, api_secret=config.KITE_API_SECRET)
        _access_token = data["access_token"]
        kite.set_access_token(_access_token)
        print(f"[Zerodha] Successfully logged in! Access token stored.")
        return True
    except Exception as e:
        print(f"[Zerodha] Login failed: {e}")
        return False

def is_logged_in():
    return _access_token is not None

def fetch_real_holdings():
    if not is_logged_in():
        raise Exception("Not logged into Zerodha Kite")
    
    kite = get_kite_instance()
    try:
        raw_holdings = kite.holdings()
        
        # Format it exactly like the PostgreSQL dicts so the Flutter app doesn't break
        formatted_holdings = []
        for h in raw_holdings:
            # We only want to show holdings where quantity > 0
            if h.get("quantity", 0) > 0:
                formatted_holdings.append({
                    "ticker": h["tradingsymbol"],
                    "qty": h["quantity"],
                    "average_price": float(h["average_price"])
                })
        
        # Sort alphabetically by ticker
        formatted_holdings.sort(key=lambda x: x["ticker"])
        return formatted_holdings
    except Exception as e:
        print(f"[Zerodha] Failed to fetch holdings: {e}")
        raise e
