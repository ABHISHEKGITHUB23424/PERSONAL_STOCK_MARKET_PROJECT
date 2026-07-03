import urllib.request, json, time
time.sleep(1)

# Test 1: Health
try:
    r = urllib.request.urlopen("http://localhost:8000/")
    data = json.loads(r.read())
    print("1. HEALTH CHECK:")
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Health check failed: {e}")

# Test 2: Portfolio
try:
    r = urllib.request.urlopen("http://localhost:8000/portfolio")
    data = json.loads(r.read())
    print("\n2. PORTFOLIO ENDPOINT:")
    print(f"   Status  : {data['status']}")
    print(f"   Source  : {data['source']}")
    print(f"   Holdings: {data['count']} stocks")
    for h in data["holdings"]:
        print(f"   {h['ticker']:<15} qty={h['qty']:>4}  avg_price={h['average_price']}")
except Exception as e:
    print(f"Portfolio failed: {e}")
