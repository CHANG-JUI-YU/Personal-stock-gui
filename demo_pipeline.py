import sys
import os
import torch
import pandas as pd
from data.database import Database
from data.collector import DataCollector
from kronos.service import KronosService
from kronos.timesfm_service import TimesFMService
from decision.agent import DecisionAgentV1

def run_full_pipeline(ticker="2330.TW", interval="1d"):
    print(f"=== Starting Full Pipeline for {ticker} ({interval}) ===")
    
    # 1. Initialize Database
    db = Database()
    db.init_db()
    
    # 2. Collect Data
    print("\n[1/4] Collecting Data...")
    collector = DataCollector(db_path=db.db_path)
    collector.fetch_historical_data(ticker, interval=interval, lookback_days=60)
    
    # 3. Kronos & TimesFM Prediction
    print("\n[2/4] Running Kronos Prediction...")
    k_service = KronosService(db_path=db.db_path)
    k_res = k_service.predict(ticker, interval=interval, lookback=60, pred_len=20)
    if k_res:
        print(f"Kronos Score: {k_res['score_k']:.2f} (Up Prob: {k_res['up_prob']:.4f})")
    else:
        print("Kronos Prediction Failed.")
        
    print("\n[2.5/4] Running TimesFM Prediction with XReg...")
    tfm_service = TimesFMService(db_path=db.db_path)
    tfm_res = tfm_service.predict(ticker, interval=interval, lookback=512, pred_len=20)
    if tfm_res:
        print(f"TimesFM Score: {tfm_res['score_k']:.2f} (Up Prob: {tfm_res['up_prob']:.4f}, Uncertainty: {tfm_res['uncertainty_pct']*100:.2f}%)")
    else:
        print("TimesFM Prediction Failed.")
    
    # 4. Decision Agent Fusion (using Real TradingAgents if configured)
    print("\n[3/4] Running Decision Agent Fusion...")
    
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 3. TA Report Phase
    print("\n--- 3. Running TradingAgents Analysis ---")
    mock_ta = not bool(os.getenv("OPENAI_API_KEY"))
    if mock_ta:
        from trading_agents.adapter import MockTradingAgents
        ta = MockTradingAgents()
    else:
        from trading_agents.adapter import RealTradingAgents
        ta = RealTradingAgents()
        
    ta_report = ta.analyze(ticker, date=date_str, interval=interval)
    if ta_report:
        db.insert_ta_report(ticker, interval, date_str, ta_report)
        print("TA Report generated and saved to DB.")

    # 4. Final Decision Phase
    print("\n--- 4. Running Decision Agent ---")
    agent = DecisionAgentV1(db_path=db.db_path)
    d_res = agent.get_decision(ticker, date=date_str, interval=interval)
    
    if not d_res:
        print("Decision Agent Fusion Failed.")
        return
        
    # 5. Output Results
    print("\n[4/4] Final Decision Results:")
    print(f"Ticker: {ticker}")
    print(f"Action: {d_res.get('action')}")
    print(f"Final Score: {d_res.get('final_score'):.2f}")
    
    print("\nEvidence:")
    for line in d_res.get('evidence', []):
        print(f" - {line}")

if __name__ == "__main__":
    # Load .env if exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
        
    ticker = sys.argv[1] if len(sys.argv) > 1 else "2330.TW"
    run_full_pipeline(ticker)
