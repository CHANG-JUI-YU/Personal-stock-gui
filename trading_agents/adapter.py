import pandas as pd
import numpy as np
from datetime import datetime
from data.database import Database

class MockTradingAgents:
    def __init__(self, db_path="data/stock_advisor.db"):
        self.db = Database(db_path)
        
    def analyze(self, ticker: str, date: str = None, interval: str = "1d") -> dict:
        """
        Mock analysis using basic RSI and MACD rules to return a structured output
        that mimics the TradingAgents API.
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        df = self.db.get_prices(ticker, interval=interval, end_date=date)
        if df is not None and not df.empty:
            df = df.tail(100)
        
        ta_action = "HOLD"
        confidence = 0.5
        reasoning = []
        
        if df is None or len(df) < 30:
            reasoning.append("資料不足，無法進行技術分析。")
        else:
            # calculate RSI (14)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # calculate MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd.iloc[-1] - signal.iloc[-1]
            
            # rules
            if current_rsi < 30 and macd_hist > 0:
                ta_action = "BUY"
                confidence = 0.8
                reasoning.append(f"RSI 處於超賣區間 ({current_rsi:.1f}) 且 MACD 柱狀圖翻正，呈現強烈買進訊號。")
            elif current_rsi > 70 and macd_hist < 0:
                ta_action = "SELL"
                confidence = 0.8
                reasoning.append(f"RSI 處於超買區間 ({current_rsi:.1f}) 且 MACD 柱狀圖翻黑，呈現強烈賣出訊號。")
            else:
                if macd_hist > 0:
                    ta_action = "BUY"
                    confidence = 0.6
                    reasoning.append(f"MACD 柱狀圖為正，但 RSI 處於中立區間 ({current_rsi:.1f})，建議偏多操作。")
                elif macd_hist < 0:
                    ta_action = "SELL"
                    confidence = 0.6
                    reasoning.append(f"MACD 柱狀圖為負，且 RSI 處於中立區間 ({current_rsi:.1f})，建議偏空操作。")
                else:
                    reasoning.append("各項技術指標皆呈現中立，無明顯趨勢。")
                
        return {
            "ticker": ticker,
            "date": date,
            "agents": {
                "Technical Analyst": {
                    "action": ta_action,
                    "confidence": confidence,
                    "reasoning": " ".join(reasoning)
                }
            }
        }


class RealTradingAgents:
    def __init__(self, config=None, skip_analysts=False):
        # We only import the real module when instantiated to avoid failing if .env is missing 
        # or module isn't fully installed during mock mode.
        import os
        from TradingAgents.tradingagents.graph.trading_graph import TradingAgentsGraph
        from TradingAgents.tradingagents.default_config import DEFAULT_CONFIG
        
        self.config = config or DEFAULT_CONFIG.copy()
        self.config["output_language"] = "Traditional Chinese (繁體中文)"
        
        # Override config based on custom env vars set in Settings UI
        if os.getenv("OPENAI_BASE_URL"):
            self.config["backend_url"] = os.getenv("OPENAI_BASE_URL")
            
        custom_model = os.getenv("OPENAI_MODEL_NAME")
        if custom_model:
            self.config["deep_think_llm"] = custom_model
            self.config["quick_think_llm"] = custom_model
            
        provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER")
        if provider:
            self.config["llm_provider"] = provider
            # Map the generic OPENAI_API_KEY to the provider's expected env var
            # since the Settings UI only provides a single API Key field.
            provider_env_map = {
                "deepseek": "DEEPSEEK_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GOOGLE_API_KEY",
                "xai": "XAI_API_KEY",
                "minimax": "MINIMAX_API_KEY",
                "qwen": "DASHSCOPE_API_KEY",
                "glm": "ZHIPU_API_KEY",
                "azure": "AZURE_OPENAI_API_KEY"
            }
            expected_key = provider_env_map.get(provider)
            if expected_key and not os.getenv(expected_key) and os.getenv("OPENAI_API_KEY"):
                os.environ[expected_key] = os.getenv("OPENAI_API_KEY")
            
        # Check if an API key is set before proceeding
        if not any(os.getenv(k) for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY"]):
            print("Warning: No LLM API key detected in environment. TradingAgents may fail.")
            
        if skip_analysts:
            self.ta = TradingAgentsGraph(selected_analysts=[], debug=False, config=self.config)
        else:
            self.ta = TradingAgentsGraph(debug=False, config=self.config)
        
    def analyze(self, ticker: str, date: str = None, interval: str = "1d", analyst_reports: dict = None, what_if_event: str = None) -> dict:
        """
        Calls the real TradingAgents pipeline and parses the multi-agent reports 
        into the structured format used by the Decision Agent.
        """
        if interval != "1d":
            print(f"Note: RealTradingAgents focuses on macro/daily fundamentals but will run alongside the {interval} Kronos prediction.")
            # We don't skip it anymore, we let it run so it contributes to the final score.
            
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        if analyst_reports:
            if what_if_event:
                print(f"Running Real TradingAgents (What-If Simulation Mode) for {ticker} on {date} using pre-analyzed reports. Event: {what_if_event}...")
            else:
                print(f"Running Real TradingAgents (Simulation Mode) for {ticker} on {date} using pre-analyzed reports...")
        else:
            print(f"Running Real TradingAgents for {ticker} on {date}...")
            
        final_state, decision_str = self.ta.propagate(ticker, date, analyst_reports=analyst_reports, what_if_event=what_if_event)
        
        action_map = {
            "Buy": "BUY",
            "Overweight": "BUY",
            "Hold": "HOLD",
            "Underweight": "SELL",
            "Sell": "SELL"
        }
        
        conf_map = {
            "Buy": 0.9,
            "Overweight": 0.6,
            "Hold": 0.5,
            "Underweight": 0.6,
            "Sell": 0.9
        }
        
        parsed_action = action_map.get(decision_str)
        parsed_conf = conf_map.get(decision_str)
        
        # Fallback for free-text output when structured output fails
        if parsed_action is None:
            decision_str_lower = str(decision_str).lower()
            if "buy" in decision_str_lower or "overweight" in decision_str_lower:
                parsed_action = "BUY"
                parsed_conf = 0.6
            elif "sell" in decision_str_lower or "underweight" in decision_str_lower:
                parsed_action = "SELL"
                parsed_conf = 0.6
            else:
                parsed_action = "HOLD"
                parsed_conf = 0.5
        
        agents_dict = {
            "Portfolio Manager": {
                "action": parsed_action,
                "confidence": parsed_conf,
                "reasoning": final_state.get("final_trade_decision", f"Final rating: {decision_str}")
            }
        }
        
        # Add sub-agent reports. To avoid diluting the mean confidence in RuleBasedDecision, 
        # we assign them the same action and confidence as the Portfolio Manager.
        for key, role_name in [
            ("market_report", "Market Analyst"), 
            ("sentiment_report", "Sentiment Analyst"),
            ("news_report", "News Analyst"),
            ("fundamentals_report", "Fundamentals Analyst")
        ]:
            if key in final_state and final_state[key]:
                agents_dict[role_name] = {
                    "action": parsed_action,
                    "confidence": parsed_conf,
                    "reasoning": final_state[key]
                }
                
        return {
            "ticker": ticker,
            "date": date,
            "agents": agents_dict
        }
