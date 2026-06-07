import sys
import os
import pandas as pd
import numpy as np
import torch
from datetime import datetime

import timesfm

# Add Kronos directory to python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "third_party", "Kronos"))
from data.database import Database

class TimesFMService:
    def __init__(self, db_path="data/stock_advisor.db", device=None):
        self.db = Database(db_path)
        self.device = device
        if self.device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
            
        print(f"Initializing TimesFMService on {self.device}...")
        self.model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
        
        # Move to device if needed (TimesFM handles some of this internally, but we can set backend)
        
        # Compile model
        self.max_context = 512
        self.max_horizon = 128
        self.model.compile(
            forecast_config=timesfm.ForecastConfig(
                max_context=self.max_context,
                max_horizon=self.max_horizon,
                return_backcast=True
            )
        )

    def predict(self, ticker: str, date: str = None, interval: str = "1d", lookback: int = 512, pred_len: int = 20, save_to_db: bool = True) -> dict:
        """
        Run TimesFM prediction with XReg (covariates) for a given ticker.
        """
        print(f"Running TimesFM prediction for {ticker} (date={date}, interval={interval}, lookback={lookback}, pred_len={pred_len})...")
        
        # 1. Fetch data from DB
        df = self.db.get_prices(ticker, interval=interval, end_date=date)
        if df is None or df.empty or len(df) < min(lookback, 32):
            print(f"Not enough data for {ticker}.")
            return None
            
        df_lookback = df.iloc[-lookback:].copy()
        
        # Prepare inputs
        closes = df_lookback['Close'].values.tolist()
        inputs = [closes]
        
        # 2. Fetch Macro XReg covariates
        macros = ["^TNX", "DX-Y.NYB", "^VIX"]
        dynamic_num_covariates = {}
        
        # Get latest timestamps
        timestamps = df_lookback.index
        
        for macro in macros:
            macro_df = self.db.get_prices(macro, interval=interval, end_date=date)
            if macro_df is not None and not macro_df.empty:
                # Align macro data to the target ticker's timestamps
                macro_aligned = macro_df.reindex(timestamps).ffill().bfill()
                
                # Exogenous variables need to cover both input window and horizon window.
                # Since we don't know future macro variables, we forward fill the last known value.
                past_cov = macro_aligned['Close'].values.tolist()
                future_cov = [past_cov[-1]] * pred_len
                full_cov = past_cov + future_cov
                dynamic_num_covariates[macro.replace("^", "")] = [full_cov]
                
        # 3. Forecast
        try:
            if dynamic_num_covariates:
                res = self.model.forecast_with_covariates(
                    inputs=inputs,
                    dynamic_numerical_covariates=dynamic_num_covariates,
                )
                if isinstance(res, tuple):
                    point_forecast, quantile_forecast = res
                else:
                    point_forecast = res
                    quantile_forecast = None
                    
                pred_close = point_forecast[0][:pred_len]
                if quantile_forecast is not None:
                    q_forecasts = quantile_forecast[0][:pred_len]
                else:
                    q_forecasts = None
            else:
                print("No covariates found. Falling back to basic forecast.")
                res = self.model.forecast(self.max_horizon, inputs)
                if isinstance(res, tuple):
                    point_forecast, quantile_forecast = res
                else:
                    point_forecast = res
                    quantile_forecast = None
                
                # When return_backcast=True, basic forecast returns (context + max_horizon) points
                pred_close = point_forecast[0][-self.max_horizon:][:pred_len]
                if quantile_forecast is not None:
                    q_forecasts = quantile_forecast[0][-self.max_horizon:][:pred_len]
                else:
                    q_forecasts = None
                    
            lower_bound = []
            upper_bound = []
            
            if q_forecasts is not None:
                # Default quantiles in timesfm 2.5: 0.1, 0.2 ... 0.9.
                for step in q_forecasts:
                    if len(step) > 9:
                        lower_bound.append(float(step[1]))
                        upper_bound.append(float(step[9]))
                    else:
                        lower_bound.append(float(step[0]))
                        upper_bound.append(float(step[-1]))
            else:
                lower_bound = pred_close.tolist()
                upper_bound = pred_close.tolist()
                
            # 4. Calculate probabilities & score
            last_actual_close = float(closes[-1])
            final_pred_close = float(pred_close[-1])
            
            price_change_pct = (final_pred_close - last_actual_close) / last_actual_close
            scale_factor = 10.0
            p = 1 / (1 + np.exp(-price_change_pct * scale_factor))
            score_k = (p - 0.5) * 200
            
            # Quantify uncertainty: Average spread between 90% and 10% bounds relative to price
            uncertainty_pct = 0
            if len(upper_bound) > 0 and len(lower_bound) > 0:
                spreads = [((u - l) / last_actual_close) for u, l in zip(upper_bound, lower_bound)]
                uncertainty_pct = sum(spreads) / len(spreads)
                
            raw_output = {
                "last_actual_close": last_actual_close,
                "final_pred_close": final_pred_close,
                "pred_close": pred_close.tolist(),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "uncertainty_pct": uncertainty_pct,
                "model": "TimesFM_2.5_200M"
            }
            
            pred_date_str = date if date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if save_to_db:
                # We save it into predictions but using a suffix for interval or we can alter the DB.
                # Let's save it to predictions with a unique 'interval' tag, or we just insert it.
                # The schema for predictions has ticker, date, interval.
                # We can save it as interval + "_timesfm"
                self.db.insert_prediction(
                    ticker=ticker,
                    interval=interval + "_tfm",
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
                "uncertainty_pct": float(uncertainty_pct),
                "raw_output": raw_output
            }
            
        except Exception as e:
            print(f"Error during TimesFM prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    service = TimesFMService()
    res = service.predict("2330.TW", pred_len=20)
    print(res)
