import logging
import requests
from parsel import Selector

logger = logging.getLogger(__name__)

def fetch_yahoo_tw_news(ticker: str) -> str:
    """Fetch aggregated Taiwan financial news from Yahoo Finance TW."""
    try:
        # Strip .TW or .TWO if present, as Yahoo TW quote URLs use the raw symbol
        base_ticker = ticker.replace('.TW', '').replace('.TWO', '')
        url = f"https://tw.stock.yahoo.com/quote/{base_ticker}/news"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        sel = Selector(response.text)
        # Yahoo TW stock news titles
        titles = sel.css('h3 a::text, h3::text, a.Fw\\(b\\)::text').getall()
        
        # Clean up and deduplicate
        cleaned = []
        for t in titles:
            t = t.strip()
            # Filter out navigation links which are usually very short
            if t and len(t) > 6 and t not in cleaned:
                cleaned.append(t)
                
        if not cleaned:
            return "No recent news found for this ticker on Yahoo Finance Taiwan."
            
        # Format for LLM
        lines = []
        for title in cleaned[:20]: # Limit to top 20 news
            lines.append(f"- {title}")
            
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Failed to fetch Yahoo TW news for {ticker}: {e}")
        return "<unavailable>"
