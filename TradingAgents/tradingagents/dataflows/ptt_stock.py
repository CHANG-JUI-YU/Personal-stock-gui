import logging
import requests
from parsel import Selector

logger = logging.getLogger(__name__)

def fetch_ptt_stock_posts(ticker: str) -> str:
    """Fetch recent posts from PTT Stock board related to the ticker."""
    try:
        base_ticker = ticker.replace('.TW', '').replace('.TWO', '')
        # Use over18 cookie just in case
        url = f"https://www.ptt.cc/bbs/Stock/search?q={base_ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        cookies = {'over18': '1'}
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        response.raise_for_status()
        
        sel = Selector(response.text)
        posts = sel.css('div.r-ent')
        
        results = []
        for post in posts:
            title = post.css('div.title a::text').get()
            if not title:
                continue
            title = title.strip()
            
            # Push counts (nrec)
            push = post.css('div.nrec span::text').get()
            push_str = f"人氣: {push}" if push else "無"
            
            date = post.css('div.meta div.date::text').get()
            date_str = date.strip() if date else ""
            
            results.append(f"[{push_str}] {title} ({date_str})")
            
        if not results:
            return "No recent posts found for this ticker on PTT Stock."
            
        # Limit to top 20 posts
        return "\n".join(results[:20])
    except Exception as e:
        logger.warning(f"Failed to fetch PTT Stock posts for {ticker}: {e}")
        return "<unavailable>"
