# -*- coding: utf-8 -*-
"""
MiroFish Runner - Lightweight wrapper to run TradingAgents with pre-analyzed KRONOS/TimesFM data.
"""

import os
import json
import logging
from typing import Dict, Any

from data.database import Database
from trading_agents.adapter import RealTradingAgents
from TradingAgents.tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

class MiroFishRunner:
    def __init__(self, db_path="data/stock_advisor.db"):
        self.db = Database(db_path)
        self.ta_runner = None
        self.config = DEFAULT_CONFIG.copy()
        
    def _initialize_runner(self, debate_rounds: int, risk_rounds: int):
        """Lazy initialization of RealTradingAgents with specific config."""
        # Override config rounds
        self.config["max_debate_rounds"] = debate_rounds
        self.config["max_risk_discuss_rounds"] = risk_rounds
        
        # Override with env vars from GUI settings
        if os.getenv("OPENAI_BASE_URL"):
            self.config["backend_url"] = os.getenv("OPENAI_BASE_URL")
            
        custom_model = os.getenv("OPENAI_MODEL_NAME")
        if custom_model:
            self.config["deep_think_llm"] = custom_model
            self.config["quick_think_llm"] = custom_model
            
        provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER")
        if provider:
            self.config["llm_provider"] = provider
            
        self.ta_runner = RealTradingAgents(config=self.config, skip_analysts=True)

    def _parse_ta_report(self, file_path: str) -> dict:
        """
        Parses pre-analyzed TradingAgents reports from disk and extracts the four analysts' text sections.
        """
        if not os.path.exists(file_path):
            return {}
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading report file {file_path}: {e}")
            return {}
            
        sections = {
            "market_report": "## Market Analyst",
            "sentiment_report": "## Sentiment Analyst",
            "news_report": "## News Analyst",
            "fundamentals_report": "## Fundamentals Analyst"
        }
        
        reports = {}
        
        for key, header in sections.items():
            start_idx = content.find(header)
            if start_idx == -1:
                reports[key] = ""
                continue
                
            content_start = start_idx + len(header)
            next_section_idx = -1
            search_pos = content_start
            while True:
                pos = content.find("## ", search_pos)
                if pos == -1:
                    break
                next_section_idx = pos
                break
                
            if next_section_idx != -1:
                reports[key] = content[content_start:next_section_idx].strip()
            else:
                reports[key] = content[content_start:].strip()
                
        return reports

    def run_simulation(self, ticker: str, interval: str, date: str,
                       debate_rounds: int = 1, risk_rounds: int = 1,
                       what_if_event: str = None) -> dict:
        """
        Fetches DB data, builds context, and runs TradingAgents graph with pre-analyzed reports.
        """
        # Fetch pre-analyzed data from DB for context injection
        kronos_pred = self.db.get_latest_prediction(ticker, interval)
        tfm_pred = self.db.get_latest_prediction(ticker, f"{interval}_tfm")
        ta_report = self.db.get_ta_report(ticker, interval, date)
        
        # Build context prompt
        context_lines = [
            f"KRONOS XAI PRE-ANALYSIS REPORT FOR {ticker}",
            f"Date: {date} | Interval: {interval}",
        ]
        if what_if_event:
            context_lines.append(f"What-If Shock: {what_if_event}")
        context_lines.append("-" * 40)
        
        if kronos_pred:
            change = kronos_pred.get('score_k', 0)
            context_lines.append(f"Kronos Score: {change:+.2f}")
            context_lines.append(f"Kronos Up Prob: {kronos_pred.get('up_prob', 0):.2%}")
            
        if tfm_pred:
            context_lines.append(f"TimesFM Up Prob: {tfm_pred.get('up_prob', 0):.2%}")
            
        if ta_report:
            ta_data = ta_report.get("ta_data", {})
            if isinstance(ta_data, str):
                try:
                    ta_data = json.loads(ta_data)
                except:
                    pass
            if isinstance(ta_data, dict):
                rsi = ta_data.get("RSI", "N/A")
                macd = ta_data.get("MACD_Hist", "N/A")
                context_lines.append(f"Technical Analysis: RSI={rsi}, MACD_Hist={macd}")
                
        context_str = "\n".join(context_lines)
        
        # Inject context via an environment variable
        os.environ["KRONOS_PRE_ANALYSIS_CONTEXT"] = context_str
        
        # Search for pre-analyzed report files on disk
        import glob
        import re
        from datetime import datetime
        
        report_dir = "reports"
        exact_filename = f"TA_Report_{ticker}_{interval}_{date}.md"
        exact_path = os.path.join(report_dir, exact_filename)
        
        target_path = None
        if os.path.exists(exact_path):
            target_path = exact_path
            logger.info(f"Found exact match report: {exact_path}")
        else:
            pattern = os.path.join(report_dir, f"TA_Report_{ticker}_{interval}_*.md")
            matching_files = glob.glob(pattern)
            
            best_file = None
            best_diff = None
            
            try:
                base_dt = datetime.strptime(date, "%Y-%m-%d")
            except:
                base_dt = None
                
            for file_path in matching_files:
                filename = os.path.basename(file_path)
                match = re.search(r"TA_Report_.*?_.*?_(.*?)\.md", filename)
                if match:
                    file_date_str = match.group(1)
                    if base_dt:
                        try:
                            file_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
                            if file_dt <= base_dt:
                                diff = (base_dt - file_dt).days
                                if best_diff is None or diff < best_diff:
                                    best_diff = diff
                                    best_file = file_path
                        except:
                            pass
                    else:
                        best_file = file_path
                        
            if best_file:
                target_path = best_file
                logger.info(f"No exact match. Using closest report: {best_file}")
            elif matching_files:
                target_path = matching_files[0]
                logger.info(f"No match <= date. Defaulting to first match: {target_path}")
                
        analyst_reports = {}
        if target_path:
            logger.info(f"Parsing report content from {target_path}")
            analyst_reports = self._parse_ta_report(target_path)
        else:
            logger.warning(f"No pre-analyzed report files found for {ticker} in reports/.")
            
        # Run Real Trading Agents with pre-analyzed reports
        self._initialize_runner(debate_rounds, risk_rounds)
        result = self.ta_runner.analyze(ticker, date, interval, analyst_reports=analyst_reports, what_if_event=what_if_event)
        
        # Extract debate log if possible from curr_state
        debate_log = {}
        curr_state = getattr(self.ta_runner.ta, 'curr_state', None)
        if curr_state:
            inv_state = curr_state.get('investment_debate_state', {})
            risk_state = curr_state.get('risk_debate_state', {})
            
            debate_log = {
                "bull": inv_state.get('bull_history', []),
                "bear": inv_state.get('bear_history', []),
                "judge": inv_state.get('judge_decision', ''),
                "risk_aggressive": risk_state.get('aggressive_history', []),
                "risk_conservative": risk_state.get('conservative_history', []),
                "risk_neutral": risk_state.get('neutral_history', []),
                "risk_judge": risk_state.get('judge_decision', '')
            }
            
        return {
            "action": result.get("agents", {}).get("Portfolio Manager", {}).get("action", "HOLD"),
            "confidence": result.get("agents", {}).get("Portfolio Manager", {}).get("confidence", 0.5),
            "reports": result.get("agents", {}),
            "debate": debate_log,
            "context_injected": context_str
        }

