import yfinance as yf
import pandas as pd
from data.database import Database
from datetime import datetime, timedelta

class DataCollector:
    def __init__(self, db_path="data/stock_advisor.db"):
        self.db = Database(db_path)

    def fetch_historical_data(self, ticker: str, interval: str = "1d", start_date: str = None, end_date: str = None, lookback_days: int = 1000):
        """
        Fetch historical data for a ticker using yfinance and save to DB.
        If start_date is not provided, fetches data for the last `lookback_days` calendar days.
        """
        # Sanitize ticker (replace comma with dot, remove spaces, take first token if multiple)
        ticker = ticker.replace(',', '.').strip().upper().split()[0]
        
        # Enforce yfinance limits based on interval
        if interval == '1h':
            lookback_days = min(lookback_days, 720) # Max 730 days
        elif interval in ['1m', '2m', '5m', '15m', '30m', '90m']:
            lookback_days = min(lookback_days, 59) # Max 60 days
            
        if not start_date:
            # Default to fetching more calendar days to ensure we get enough trading days
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
        print(f"Fetching {interval} data for {ticker} from {start_date} to {end_date if end_date else 'today'}")
        
        # Download data
        try:
            df = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False)
            
            if df.empty:
                print(f"No data fetched for {ticker}.")
                return False
                
            # Handle multi-index columns if they exist (sometimes yf returns multi-index when there's one ticker)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Ensure columns are what we expect
            expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_cols:
                if col not in df.columns:
                    print(f"Missing expected column {col} in fetched data.")
                    return False
                    
            df = df[expected_cols]
            
            # Forward fill missing values
            df = df.ffill()
            
            # Insert into database
            self.db.insert_prices(ticker, interval, df)
            print(f"Successfully saved {len(df)} rows for {ticker} (interval: {interval}).")
            
            # Fetch macro indicators for XReg
            self._fetch_macro_indicators(interval=interval, start_date=start_date, end_date=end_date)
            
            return True
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return False

    def _fetch_macro_indicators(self, interval: str, start_date: str, end_date: str = None):
        """Fetch macro indicators to be used as exogenous variables (XReg)."""
        macros = ["^TNX", "DX-Y.NYB", "^VIX"]
        for macro in macros:
            print(f"Fetching macro indicator {macro}...")
            try:
                df = yf.download(macro, start=start_date, end=end_date, interval=interval, progress=False)
                if df.empty:
                    print(f"No data fetched for {macro}.")
                    continue
                    
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                    
                expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                for col in expected_cols:
                    if col not in df.columns:
                        # Some indices don't have Volume, fill with 0
                        if col == 'Volume':
                            df[col] = 0
                        else:
                            df[col] = df['Close'] if 'Close' in df.columns else 0
                            
                df = df[expected_cols].ffill().bfill()
                self.db.insert_prices(macro, interval, df)
                print(f"Successfully saved macro {macro}.")
            except Exception as e:
                print(f"Error fetching macro {macro}: {e}")

if __name__ == "__main__":
    # Test the collector
    collector = DataCollector()
    collector.fetch_historical_data("2330.TW", lookback_days=400)
    
    # Test retrieval
    db = Database()
    df = db.get_prices("2330.TW")
    print(f"\nRetrieved {len(df)} rows from DB:")
    print(df.tail())
