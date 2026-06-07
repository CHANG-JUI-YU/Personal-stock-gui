import re

def setup_taiwan_source():
    """
    Monkey-patch the TradingAgents symbol_utils to automatically append '.TW' 
    to 4-digit Taiwanese stock codes so that the LLM agents and data collectors 
    can correctly query Yahoo Finance.
    """
    try:
        import TradingAgents.tradingagents.dataflows.symbol_utils as symbol_utils
        
        original_normalize_symbol = symbol_utils.normalize_symbol
        
        def new_normalize_symbol(symbol: str) -> str:
            # First apply original normalizations
            sym = original_normalize_symbol(symbol)
            
            # If it's a pure 4-digit code (e.g. 2330) and doesn't already have a suffix
            if re.match(r'^\d{4}$', sym):
                return f"{sym}.TW"
                
            return sym
            
        symbol_utils.normalize_symbol = new_normalize_symbol
        print("Successfully monkey-patched TradingAgents for Taiwan stocks (.TW).")
    except ImportError as e:
        print(f"Warning: Could not patch TradingAgents symbol_utils. Real mode may fail for TW stocks. {e}")
