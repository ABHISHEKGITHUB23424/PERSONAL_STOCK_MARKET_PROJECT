"""
test_websocket.py — Full integration test
  1. Starts the AAPL drip feed
  2. Connects WebSocket and prints 10 live ticks
"""
import asyncio
import json
import urllib.request


async def test():
    import websockets

    ticker = "AAPL"

    # ── Step 1: Start the feed ────────────────────────────────────────────────
    print(f"Starting {ticker} feed via POST /feed/start/{ticker} ...")
    print("(yfinance download may take 5-15 seconds — please wait)\n")
    try:
        req = urllib.request.Request(
            f"http://localhost:8000/feed/start/{ticker}",
            method="POST"
        )
        req.add_header("Content-Length", "0")
        r = urllib.request.urlopen(req, timeout=60)
        data = json.loads(r.read())
        print(f"✓ Feed started: {data['status']}")
        print(f"  Ticks loaded : {data.get('total_ticks', '?')}")
        print(f"  Feed source  : {data.get('feed', '?')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Feed start HTTP {e.code}: {body}")
        if e.code not in (200, 409):  # 409 = already running is OK
            return
    except Exception as e:
        print(f"Feed start failed: {e}")
        return

    # ── Step 2: Connect WebSocket ─────────────────────────────────────────────
    print(f"\nConnecting ws://localhost:8000/ws/{ticker} ...")
    print("-" * 60)
    print(f"  {'#':>3}  {'Price':>12}  {'Velocity/hr':>14}  Direction")
    print(f"  {'-'*3}  {'-'*12}  {'-'*14}  ---------")

    uri = f"ws://localhost:8000/ws/{ticker}"
    try:
        async with websockets.connect(uri, ping_interval=None) as ws:
            received = 0
            while received < 10:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    d = json.loads(msg)
                    vel = d.get("velocity_per_hour")
                    vel_str = f"{vel:+.4f}" if vel is not None else "  (building...)"
                    print(f"  {received+1:>3}  {d['price']:>12.4f}  {vel_str:>14}  {d['direction']}")
                    received += 1
                except asyncio.TimeoutError:
                    print("  (waiting for tick...)")
    except Exception as e:
        print(f"WebSocket error: {e}")
        return

    print("-" * 60)
    print("\n✅ WebSocket test PASSED — System is fully working!")
    print(f"\nYou can now connect your Flutter app to:")
    print(f"  WebSocket : ws://localhost:8000/ws/AAPL")
    print(f"  Portfolio : GET http://localhost:8000/portfolio")
    print(f"  Velocity  : GET http://localhost:8000/velocity/AAPL")
    print(f"  Swagger   : http://localhost:8000/docs")


asyncio.run(test())
