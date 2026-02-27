import os
import json
import time
from typing import Dict, Any
from yahooquery import Ticker

# Cache setup for fundamentals (updates quarterly, so caching is aggressive)
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'fundamentals_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_fundamentals(symbol: str) -> Dict[str, Any]:
    """
    Fetches fundamental data (CANSLIM metrics) for a given symbol using yahooquery.
    Caches the result to disk to avoid API rate limiting.
    
    Args:
        symbol (str): The stock ticker (e.g., 'RELIANCE.NS')
        
    Returns:
        dict: {
            'revenueGrowth': float,
            'earningsGrowth': float,
            'returnOnEquity': float,
            'valid': bool
        }
    """
    # Standardize symbol
    if not symbol.endswith('.NS'):
        symbol = f"{symbol}.NS"
        
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_fundamentals.json")
    
    # 1. Check cache first (Valid for 7 days to capture rolling quarterly updates)
    if os.path.exists(cache_file):
        file_age_days = (time.time() - os.path.getmtime(cache_file)) / 86400
        if file_age_days < 7:
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass # Fallback to fetch
                
    # 2. Fetch from API
    result = {
        'revenueGrowth': 0.0,
        'earningsGrowth': 0.0,
        'returnOnEquity': 0.0,
        'valid': False
    }
    
    try:
        ticker = Ticker(symbol)
        
        # We need financial_data (for revenue/earnings growth) and key_stats (for ROE)
        fin_data = ticker.financial_data
        key_stats = ticker.key_stats
        
        # Handle dict wrapping that yahooquery uses
        if isinstance(fin_data, dict) and symbol in fin_data:
            fd = fin_data[symbol]
            if isinstance(fd, dict):
                result['revenueGrowth'] = fd.get('revenueGrowth', 0.0) or 0.0
                result['earningsGrowth'] = fd.get('earningsGrowth', 0.0) or 0.0
                
        if isinstance(key_stats, dict) and symbol in key_stats:
            ks = key_stats[symbol]
            if isinstance(ks, dict):
                result['returnOnEquity'] = ks.get('returnOnEquity', 0.0) or 0.0
                
        # Mark as valid if we got any non-zero data
        if result['revenueGrowth'] != 0 or result['earningsGrowth'] != 0 or result['returnOnEquity'] != 0:
            result['valid'] = True
            
        # 3. Save to cache
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=4)
            
    except Exception as e:
        # Failsafe: return default 0s if API blocks/fails
        print(f"  ⚠️ Fundamental API Error [{symbol}]: {str(e)}")
        
    return result
