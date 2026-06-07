from data.database import Database
from decision.rule_based import RuleBasedDecision
from trading_agents.taiwan_source import setup_taiwan_source

class DecisionAgentV1:
    def __init__(self, db_path="data/stock_advisor.db"):
        self.db = Database(db_path)
        self.fusion = RuleBasedDecision()
        
        # Patch data source for Taiwan stocks
        setup_taiwan_source()
            
    def get_decision(self, ticker: str, date: str, interval: str = "1d",
                     w_kronos: float = None, w_timesfm: float = None,
                     w_ta: float = None) -> dict:
        """
        1. Fetch Kronos and TimesFM predictions from DB
        2. Fetch TA Report from DB
        3. Run Fusion logic
        """
        # 1. Fetch Kronos & TimesFM
        kronos_pred = self.db.get_prediction(ticker, interval, date)
        tfm_pred = self.db.get_prediction(ticker, f"{interval}_tfm", date)
        
        if not kronos_pred and not tfm_pred:
            print(f"No Kronos or TimesFM prediction found for {ticker} on {date} (interval: {interval}). Run prediction services first.")
            return None
            
        # 2. Fetch TA Report from DB
        ta_result = self.db.get_ta_report(ticker, interval, date)
        if not ta_result:
            print(f"No TA Report found for {ticker} on {date} (interval: {interval}). TA weight will be ignored.")
            
        # 3. Fusion
        from decision.rule_based import RuleBasedDecision
        fusion = RuleBasedDecision(w_kronos=w_kronos, w_timesfm=w_timesfm, w_ta=w_ta)
        decision = fusion.evaluate(kronos_pred, tfm_pred, ta_result)
        
        decision_dict = decision.to_dict()
        
        # 4. Risk Check
        from decision.risk_manager import RiskManager
        prices_df = self.db.get_prices(ticker, interval)
        risk_mgr = RiskManager()
        decision_dict = risk_mgr.evaluate(decision_dict, prices_df, self.db, ticker, interval)
        
        self.db.insert_decision(ticker, interval, date, decision_dict)
        
        return decision_dict

if __name__ == "__main__":
    from datetime import datetime
    
    # default test with Mock
    agent = DecisionAgentV1(mock_ta=True)
    date = datetime.now().strftime('%Y-%m-%d')
    res = agent.get_decision("2330.TW", date)
    
    if res:
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
