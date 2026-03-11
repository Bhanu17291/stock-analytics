def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "outputsize": "full",
            "apikey": API_KEY
        }
        r = requests.get(BASE_URL, params=params)
        data = r.json()
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            print(f"No time series data for {ticker}: {data}")
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(ts, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df = df.astype(float)

        # Filter by period
        period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
        days = period_days.get(period, 180)
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()