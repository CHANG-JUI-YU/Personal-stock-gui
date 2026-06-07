import sys
import os
import time
import pandas as pd
import yfinance as yf
import torch

# Add Kronos directory to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "Kronos"))

from model import Kronos, KronosTokenizer, KronosPredictor

def test_kronos():
    print("PyTorch version:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device name:", torch.cuda.get_device_name(0))
        device = "cuda:0"
    else:
        device = "cpu"

    print("\n--- Step 1: Downloading 2330.TW data via yfinance ---")
    df = yf.download("2330.TW", period="3y", interval="1d")
    df.reset_index(inplace=True)
    
    # yfinance columns might be MultiIndex if not careful, but usually simple for one ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Rename columns to lowercase for Kronos
    df.rename(columns={
        "Date": "timestamps",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    }, inplace=True)
    
    # Add amount column (optional, can be zero, or open*volume approx)
    df["amount"] = df["close"] * df["volume"]
    
    # Drop rows with NaN in price columns
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    
    print(f"Data shape: {df.shape}")
    print(df[["timestamps", "open", "high", "low", "close"]].tail())
    
    print("\n--- Step 2: Loading Kronos Model ---")
    start_time = time.time()
    
    # Load tokenizer and model
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    
    if device == "cuda:0":
        model = model.to(device)
        
    predictor = KronosPredictor(model, tokenizer, max_context=512)
    
    load_time = time.time() - start_time
    print(f"Model loaded in {load_time:.2f} seconds.")
    
    if device == "cuda:0":
        allocated = torch.cuda.memory_allocated() / 1024**2
        reserved = torch.cuda.memory_reserved() / 1024**2
        print(f"VRAM Allocated: {allocated:.2f} MB")
        print(f"VRAM Reserved:  {reserved:.2f} MB")
        
    print("\n--- Step 3: Inference Test ---")
    lookback = 400
    pred_len = 20
    
    if len(df) < lookback:
        print(f"Not enough data! Need at least {lookback} rows.")
        return
        
    x_df = df.iloc[-lookback:].copy()
    x_df.reset_index(drop=True, inplace=True)
    x_timestamp = x_df['timestamps']
    
    # Create future timestamps (skipping weekends for simplicity, though pandas bdate_range is better)
    last_date = x_timestamp.iloc[-1]
    y_timestamp = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_len)
    
    print(f"Lookback data shape: {x_df.shape}")
    print(f"Predicting next {pred_len} periods...")
    
    start_time = time.time()
    pred_df = predictor.predict(
        df=x_df[['open', 'high', 'low', 'close']],
        x_timestamp=x_timestamp,
        y_timestamp=pd.Series(y_timestamp),
        pred_len=pred_len,
        T=1.0,
        top_p=0.9,
        sample_count=1
    )
    infer_time = time.time() - start_time
    
    print(f"Inference completed in {infer_time:.2f} seconds.")
    if device == "cuda:0":
        peak = torch.cuda.max_memory_allocated() / 1024**2
        print(f"Peak VRAM during inference: {peak:.2f} MB")
        
    print("\n--- Inference Results Head ---")
    print(pred_df.head())
    
    print("\n--- Feasibility Test Success ---")

if __name__ == "__main__":
    test_kronos()
