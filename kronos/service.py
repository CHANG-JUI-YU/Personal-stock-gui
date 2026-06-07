import sys
import os
import pandas as pd
import numpy as np
import torch
from datetime import datetime

# Add Kronos directory to python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "third_party", "Kronos"))
from model import Kronos, KronosTokenizer, KronosPredictor
from data.database import Database

class KronosService:
    def __init__(self, db_path="data/stock_advisor.db", device=None):
        self.db = Database(db_path)
        self.device = device
        if self.device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
            
        print(f"Initializing KronosService on {self.device}...")
        self.tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
        self.model = Kronos.from_pretrained("NeoQuasar/Kronos-base")
        
        if self.device.startswith("cuda"):
            self.model = self.model.to(self.device)
            
        self.predictor = KronosPredictor(self.model, self.tokenizer, max_context=512)

    def _prepare_data(self, df: pd.DataFrame) -> tuple:
        """
        Prepare DataFrame for KronosPredictor.
        Expected yfinance df: index is Date, columns are Open, High, Low, Close, Volume.
        """
        kronos_df = df.copy()
        kronos_df.reset_index(inplace=True)
        
        # Rename columns to what Kronos expects
        kronos_df.rename(columns={
            "Date": "timestamps",
            "date": "timestamps",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)
        
        # Add amount column (required by Kronos if not present, though KronosPredictor adds it, it's safer to have)
        kronos_df["amount"] = kronos_df["close"] * kronos_df["volume"]
        
        # Ensure correct types
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            kronos_df[col] = kronos_df[col].astype(float)
        kronos_df['volume'] = kronos_df['volume'].astype(float)
        
        # Drop NaN values which break Kronos
        kronos_df.dropna(subset=price_cols, inplace=True)
        kronos_df.reset_index(drop=True, inplace=True)
        
        return kronos_df

    def predict(self, ticker: str, date: str = None, interval: str = "1d", lookback: int = 60, pred_len: int = 20, sample_count: int = 5, save_to_db: bool = True) -> dict:
        """
        Run Kronos prediction for a given ticker based on DB data.
        Returns prediction dict including up_prob and score_k.
        """
        print(f"Running Kronos prediction for {ticker} (date={date}, interval={interval}, lookback={lookback}, pred_len={pred_len})...")
        
        # 1. Fetch data from DB
        df = self.db.get_prices(ticker, interval=interval, end_date=date)
        if df is None or df.empty or len(df) < lookback:
            print(f"Not enough data for {ticker}. Have {len(df) if df is not None else 0} rows, need {lookback}.")
            return None
            
        # 2. Get the last `lookback` rows
        df_lookback = df.iloc[-lookback:].copy()
        
        # 3. Prepare data
        kronos_df = self._prepare_data(df_lookback)
        x_timestamp = pd.to_datetime(kronos_df['timestamps'])
        
        # 4. Generate future timestamps
        freq_map = {"1d": "B", "1h": "h", "15m": "15min", "5m": "5min"}
        freq = freq_map.get(interval, "B")
        
        last_date = x_timestamp.iloc[-1]
        if freq == "B":
            y_timestamp = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_len)
        elif interval == "1h":
            next_date = last_date + pd.Timedelta(hours=1)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        elif interval == "15m":
            next_date = last_date + pd.Timedelta(minutes=15)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        elif interval == "5m":
            next_date = last_date + pd.Timedelta(minutes=5)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        else:
            next_date = last_date + pd.Timedelta(days=1)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        
        # 5. Run inference
        try:
            pred_df = self.predictor.predict(
                df=kronos_df[['open', 'high', 'low', 'close', 'volume']],
                x_timestamp=x_timestamp,
                y_timestamp=pd.Series(y_timestamp),
                pred_len=pred_len,
                T=1.0,
                top_p=0.9,
                sample_count=sample_count
            )
            
            # 6. Calculate up_prob and score_k
            last_actual_close = kronos_df['close'].iloc[-1]
            final_pred_close = pred_df['close'].iloc[-1]
            
            price_change_pct = (final_pred_close - last_actual_close) / last_actual_close
            
            scale_factor = 10.0
            p = 1 / (1 + np.exp(-price_change_pct * scale_factor))
            
            score_k = (p - 0.5) * 200
            
            raw_output = {
                "last_actual_close": float(last_actual_close),
                "final_pred_close": float(final_pred_close),
                "price_change_pct": float(price_change_pct),
                "predictions": {str(k): v for k, v in pred_df.to_dict(orient="index").items()}
            }
            
            pred_date_str = date if date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if save_to_db:
                self.db.insert_prediction(
                    ticker=ticker,
                    interval=interval,
                    date=pred_date_str,
                    pred_len=pred_len,
                    up_prob=float(p),
                    score_k=float(score_k),
                    raw_output=raw_output
                )
                
            return {
                "ticker": ticker,
                "date": pred_date_str,
                "pred_len": pred_len,
                "up_prob": float(p),
                "score_k": float(score_k),
                "raw_output": raw_output
            }
            
        except Exception as e:
            print(f"Error during Kronos prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

    def predict_with_uncertainty(self, ticker: str, date: str = None, interval: str = "1d", lookback: int = 60, pred_len: int = 20, n_samples: int = 5, save_to_db: bool = True) -> dict:
        """
        Run multiple independent Kronos predictions to calculate confidence intervals and identify key time windows.
        """
        print(f"Running Kronos XAI prediction for {ticker} (date={date}, interval={interval}, samples={n_samples})...")
        
        df = self.db.get_prices(ticker, interval=interval, end_date=date)
        if df is None or df.empty or len(df) < lookback:
            print(f"Not enough data for {ticker}. Have {len(df) if df is not None else 0} rows, need {lookback}.")
            return None
            
        df_lookback = df.iloc[-lookback:].copy()
        kronos_df = self._prepare_data(df_lookback)
        x_timestamp = pd.to_datetime(kronos_df['timestamps'])
        
        freq_map = {"1d": "B", "1h": "h", "15m": "15min", "5m": "5min"}
        freq = freq_map.get(interval, "B")
        
        last_date = x_timestamp.iloc[-1]
        if freq == "B":
            y_timestamp = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_len)
        elif interval == "1h":
            next_date = last_date + pd.Timedelta(hours=1)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        elif interval == "15m":
            next_date = last_date + pd.Timedelta(minutes=15)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        elif interval == "5m":
            next_date = last_date + pd.Timedelta(minutes=5)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        else:
            next_date = last_date + pd.Timedelta(days=1)
            y_timestamp = pd.date_range(start=next_date, periods=pred_len, freq=freq)
        
        try:
            samples = []
            for i in range(n_samples):
                print(f"Sampling {i+1}/{n_samples}...")
                pred_df = self.predictor.predict(
                    df=kronos_df[['open', 'high', 'low', 'close', 'volume']],
                    x_timestamp=x_timestamp,
                    y_timestamp=pd.Series(y_timestamp),
                    pred_len=pred_len,
                    T=1.0,
                    top_p=0.9,
                    sample_count=1,
                    verbose=False
                )
                samples.append(pred_df['close'].values)
            
            samples_arr = np.array(samples)  # Shape: (n_samples, pred_len)
            mean_close = np.mean(samples_arr, axis=0)
            std_close = np.std(samples_arr, axis=0)
            
            # Calculate 95% confidence interval (~1.96 std)
            upper_bound = mean_close + 1.96 * std_close
            lower_bound = mean_close - 1.96 * std_close
            
            # Identify key time windows (indices with the highest standard deviation / uncertainty)
            # Find the top 3 days with maximum variance
            top_std_indices = np.argsort(std_close)[-3:][::-1]
            key_windows = []
            for idx in top_std_indices:
                key_windows.append({
                    "date": str(y_timestamp[idx]),
                    "std": float(std_close[idx]),
                    "mean_price": float(mean_close[idx])
                })
            
            last_actual_close = float(kronos_df['close'].iloc[-1])
            final_mean_close = float(mean_close[-1])
            
            raw_output = {
                "last_actual_close": last_actual_close,
                "y_timestamps": [str(d) for d in y_timestamp],
                "mean_close": mean_close.tolist(),
                "std_close": std_close.tolist(),
                "upper_bound": upper_bound.tolist(),
                "lower_bound": lower_bound.tolist(),
                "key_windows": key_windows,
                "all_samples": samples_arr.tolist()
            }
            
            pred_date_str = date if date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            price_change_pct = (final_mean_close - last_actual_close) / last_actual_close
            p = 1 / (1 + np.exp(-price_change_pct * 10.0))
            score_k = (p - 0.5) * 200
            
            if save_to_db:
                self.db.insert_prediction(
                    ticker=ticker,
                    interval=interval,
                    date=pred_date_str,
                    pred_len=pred_len,
                    up_prob=float(p),
                    score_k=float(score_k),
                    raw_output=raw_output
                )
                
            return {
                "ticker": ticker,
                "date": pred_date_str,
                "pred_len": pred_len,
                "mean_close": mean_close.tolist(),
                "upper_bound": upper_bound.tolist(),
                "lower_bound": lower_bound.tolist(),
                "key_windows": key_windows,
                "raw_output": raw_output
            }
            
        except Exception as e:
            print(f"Error during Kronos XAI prediction: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    from datetime import datetime
    
    # Test Service
    service = KronosService()
    result = service.predict("2330.TW", pred_len=20, sample_count=1)
    
    if result:
        print(f"\nPrediction for 2330.TW:")
        print(f"Up Probability: {result['up_prob']:.4f}")
        print(f"Score K: {result['score_k']:.2f}")
        print(f"Last Close: {result['raw_output']['last_actual_close']}")
        print(f"Pred Close: {result['raw_output']['final_pred_close']}")
