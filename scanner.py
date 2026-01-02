"""
Scanner Module - Auto-Scanning Watchlist
=========================================
Scans watchlist every X minutes during market hours
Fetches data from Polygon and runs analysis engine
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import pytz

from analysis_engine import analyze_stock, OHLCV, AnalysisResult
from options_analytics import analyze_options, OptionsAnalysis
from db import watchlist_get_all, scan_save, scan_get_latest

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
SCAN_INTERVAL_MINUTES = int(os.getenv('SCAN_INTERVAL', 5))

# Cache for scan results
_scan_cache: Dict[str, Dict] = {}
_last_scan_time: Optional[datetime] = None
_scanner_thread: Optional[threading.Thread] = None
_scanner_running = False


# ============================================================================
# POLYGON DATA FETCHING
# ============================================================================

def fetch_bars(symbol: str, days: int = 252, timeframe: str = 'day') -> List[OHLCV]:
    """
    Fetch OHLCV bars from Polygon
    """
    if not POLYGON_API_KEY:
        return []
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timeframe}/{start_date}/{end_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 50000,
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"Polygon API error for {symbol}: {response.status_code}")
            return []
        
        data = response.json()
        bars = []
        
        for r in data.get('results', []):
            bars.append(OHLCV(
                timestamp=datetime.fromtimestamp(r['t'] / 1000),
                open=r['o'],
                high=r['h'],
                low=r['l'],
                close=r['c'],
                volume=r['v']
            ))
        
        return bars
        
    except Exception as e:
        print(f"Error fetching bars for {symbol}: {e}")
        return []

def fetch_spy_bars(days: int = 252) -> List[OHLCV]:
    """Fetch SPY bars for relative strength calculation"""
    return fetch_bars('SPY', days)


# ============================================================================
# SCANNING FUNCTIONS
# ============================================================================

def scan_symbol(symbol: str, spy_bars: List[OHLCV] = None, 
                capital: float = 100000) -> Optional[Dict]:
    """
    Complete scan of a single symbol
    Returns combined analysis result
    """
    # Fetch bars
    bars = fetch_bars(symbol)
    
    if not bars:
        return None
    
    # Get SPY bars if not provided
    if spy_bars is None:
        spy_bars = fetch_spy_bars()
    
    # Run technical analysis
    analysis = analyze_stock(symbol, bars, spy_bars)
    
    # Run options analysis if there's a setup
    options_analysis = None
    if analysis.setup_type and analysis.setup_direction:
        direction = analysis.setup_direction.lower()
        tier = analysis.tier or 'C'
        options_analysis = analyze_options(symbol, direction, tier, capital)
    
    # Combine results
    result = {
        'symbol': symbol,
        'scanned_at': datetime.now().isoformat(),
        
        # Category and sorting
        'category': analysis.category,
        'sort_priority': get_sort_priority(analysis),
        
        # Setup info
        'setup_type': analysis.setup_type,
        'setup_direction': analysis.setup_direction,
        'tier': analysis.tier,
        'priority_score': analysis.priority_score,
        'setup_factors': analysis.setup_factors,
        'max_factors': analysis.max_factors,
        
        # Execution
        'exec_readiness': analysis.exec_readiness,
        'exec_status': analysis.exec_status,
        'session_phase': analysis.session_phase,
        
        # Analysis
        'relative_strength': analysis.relative_strength,
        'rs_rating': analysis.rs_rating,
        'iv_percentile': analysis.iv_percentile,
        'iv_rating': analysis.iv_rating,
        'mtf_alignment': analysis.mtf_alignment,
        'momentum_quality': analysis.momentum_quality,
        'confluence_score': analysis.confluence_score,
        
        # Technicals
        'rsi': analysis.rsi,
        'squeeze_on': analysis.squeeze_on,
        'squeeze_bars': analysis.squeeze_bars,
        'consecutive_green': analysis.consecutive_green,
        'consecutive_red': analysis.consecutive_red,
        
        # Levels
        'support': analysis.support,
        'resistance': analysis.resistance,
        'vwap': analysis.vwap,
        'ema_21': analysis.ema_21,
        'sma_50': analysis.sma_50,
        'sma_200': analysis.sma_200,
        
        # Price
        'price': bars[-1].close if bars else 0,
        'change_pct': ((bars[-1].close - bars[-2].close) / bars[-2].close * 100) if len(bars) >= 2 else 0,
        
        # Warnings
        'warnings': analysis.warnings,
        
        # Options (if available)
        'options': options_analysis.to_dict() if options_analysis else None,
        
        # Raw technical data
        'technical_data': analysis.technical_data
    }
    
    # Save to database
    scan_save(symbol, result)
    
    return result

def get_sort_priority(analysis: AnalysisResult) -> int:
    """
    Calculate sort priority for ranking
    Higher = better
    """
    priority = 0
    
    # Category weight
    category_weight = {
        'READY_NOW': 1000,
        'SETTING_UP': 500,
        'BUILDING': 200,
        'WATCH': 100,
        'AVOID': 0
    }
    priority += category_weight.get(analysis.category, 0)
    
    # Tier weight
    tier_weight = {'A': 300, 'B': 200, 'C': 100}
    priority += tier_weight.get(analysis.tier or 'C', 0)
    
    # Priority score
    priority += analysis.priority_score
    
    # Execution readiness
    priority += analysis.exec_readiness * 10
    
    # Confluence
    priority += analysis.confluence_score
    
    return priority

def scan_watchlist(capital: float = 100000) -> List[Dict]:
    """
    Scan all symbols in watchlist
    Returns sorted list of results
    """
    global _scan_cache, _last_scan_time
    
    watchlist = watchlist_get_all()
    
    if not watchlist:
        return []
    
    # Fetch SPY once for all comparisons
    spy_bars = fetch_spy_bars()
    
    results = []
    
    for item in watchlist:
        symbol = item.get('symbol', '')
        if not symbol:
            continue
        
        # Rate limiting for Polygon API
        time.sleep(0.25)  # 4 calls per second max
        
        result = scan_symbol(symbol, spy_bars, capital)
        if result:
            results.append(result)
    
    # Sort by priority (highest first)
    results.sort(key=lambda x: x.get('sort_priority', 0), reverse=True)
    
    # Update cache
    _scan_cache = {r['symbol']: r for r in results}
    _last_scan_time = datetime.now()
    
    return results

def get_cached_results() -> List[Dict]:
    """Get cached scan results"""
    if not _scan_cache:
        return []
    
    results = list(_scan_cache.values())
    results.sort(key=lambda x: x.get('sort_priority', 0), reverse=True)
    return results

def get_results_by_category() -> Dict[str, List[Dict]]:
    """Get scan results grouped by category"""
    results = get_cached_results()
    
    categorized = {
        'READY_NOW': [],
        'SETTING_UP': [],
        'BUILDING': [],
        'WATCH': [],
        'AVOID': []
    }
    
    for r in results:
        category = r.get('category', 'WATCH')
        if category in categorized:
            categorized[category].append(r)
    
    return categorized


# ============================================================================
# AUTO-SCANNER (Background Thread)
# ============================================================================

def is_market_hours() -> bool:
    """Check if currently market hours (9:30 AM - 4:00 PM ET)"""
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    
    # Check if weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check time
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close

def scanner_loop():
    """Background scanner loop"""
    global _scanner_running
    
    capital = float(os.getenv('TOTAL_CAPITAL', 100000))
    
    while _scanner_running:
        try:
            if is_market_hours():
                print(f"[{datetime.now()}] Running auto-scan...")
                results = scan_watchlist(capital)
                print(f"[{datetime.now()}] Scanned {len(results)} symbols")
            else:
                print(f"[{datetime.now()}] Market closed, skipping scan")
        except Exception as e:
            print(f"[{datetime.now()}] Scanner error: {e}")
        
        # Wait for next interval
        time.sleep(SCAN_INTERVAL_MINUTES * 60)

def start_scanner():
    """Start background scanner thread"""
    global _scanner_thread, _scanner_running
    
    if _scanner_thread and _scanner_thread.is_alive():
        return  # Already running
    
    _scanner_running = True
    _scanner_thread = threading.Thread(target=scanner_loop, daemon=True)
    _scanner_thread.start()
    print(f"Scanner started (interval: {SCAN_INTERVAL_MINUTES} minutes)")

def stop_scanner():
    """Stop background scanner"""
    global _scanner_running
    _scanner_running = False
    print("Scanner stopped")


# ============================================================================
# MANUAL SCAN FUNCTIONS
# ============================================================================

def quick_scan_symbol(symbol: str) -> Optional[Dict]:
    """
    Quick scan of single symbol (uses cache if recent)
    """
    symbol = symbol.upper()
    
    # Check cache
    cached = _scan_cache.get(symbol)
    if cached:
        cached_time = datetime.fromisoformat(cached.get('scanned_at', '2000-01-01'))
        if (datetime.now() - cached_time).seconds < 300:  # 5 min cache
            return cached
    
    # Do fresh scan
    return scan_symbol(symbol)

def force_rescan(capital: float = 100000) -> List[Dict]:
    """Force immediate rescan of watchlist"""
    return scan_watchlist(capital)


# ============================================================================
# STATISTICS FUNCTIONS
# ============================================================================

def get_scan_stats() -> Dict:
    """Get statistics about current scans"""
    results = get_cached_results()
    
    if not results:
        return {
            'total': 0,
            'ready_now': 0,
            'setting_up': 0,
            'building': 0,
            'avoid': 0,
            'last_scan': None
        }
    
    categorized = get_results_by_category()
    
    return {
        'total': len(results),
        'ready_now': len(categorized['READY_NOW']),
        'setting_up': len(categorized['SETTING_UP']),
        'building': len(categorized['BUILDING']),
        'avoid': len(categorized['AVOID']),
        'last_scan': _last_scan_time.isoformat() if _last_scan_time else None,
        'avg_confluence': sum(r.get('confluence_score', 0) for r in results) / len(results) if results else 0
    }
