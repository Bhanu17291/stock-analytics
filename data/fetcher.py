def fetch_stock_info(ticker: str) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": "1d", "interval": "1d"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        return {
            "name": meta.get("longName", meta.get("shortName", ticker)),
            "sector": "N/A",
            "market_cap": 0,
            "pe_ratio": 0,
            "52w_high": meta.get("fiftyTwoWeekHigh", 0),
            "52w_low": meta.get("fiftyTwoWeekLow", 0),
            "current_price": meta.get("regularMarketPrice", 0),
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return {}