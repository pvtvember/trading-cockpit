"""
Market Monitor Module
=====================
Tracks market-wide signals:
- VIX and volatility regime
- Sector performance (XLK, XLF, XLE, etc.)
- Market internals (breadth, SPY trend)
- Risk environment assessment
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')


# ============================================================================
# SECTOR ETFs
# ============================================================================

SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLI': 'Industrials',
    'XLB': 'Materials',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLC': 'Communication Services'
}

STOCK_TO_SECTOR = {
    # Technology
    'AAPL': 'XLK', 'MSFT': 'XLK', 'NVDA': 'XLK', 'AMD': 'XLK', 'INTC': 'XLK',
    'GOOGL': 'XLC', 'GOOG': 'XLC', 'META': 'XLC', 'NFLX': 'XLC', 'DIS': 'XLC',
    'SNAP': 'XLC', 'PINS': 'XLC', 'TWTR': 'XLC',
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF', 'GS': 'XLF', 'MS': 'XLF', 'WFC': 'XLF', 'C': 'XLF',
    # Energy
    'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'SLB': 'XLE', 'OXY': 'XLE',
    # Healthcare
    'JNJ': 'XLV', 'UNH': 'XLV', 'PFE': 'XLV', 'MRK': 'XLV', 'ABBV': 'XLV',
    # Consumer
    'AMZN': 'XLY', 'TSLA': 'XLY', 'HD': 'XLY', 'NKE': 'XLY', 'MCD': 'XLY',
    'WMT': 'XLP', 'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP', 'COST': 'XLP',
    # Industrials
    'CAT': 'XLI', 'BA': 'XLI', 'UPS': 'XLI', 'HON': 'XLI', 'GE': 'XLI',
    # Chinese Tech
    'BIDU': 'XLC', 'BABA': 'XLY', 'JD': 'XLY', 'PDD': 'XLY',
}


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_quote(symbol: str) -> Dict:
    """Fetch current quote for symbol"""
    if not POLYGON_API_KEY:
        return {'price': 0, 'change': 0, 'change_pct': 0}
    
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        response = requests.get(url, params={'apiKey': POLYGON_API_KEY}, timeout=5)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                r = results[0]
                prev_close = r.get('c', 0)
                open_price = r.get('o', prev_close)
                change = prev_close - open_price
                change_pct = (change / open_price * 100) if open_price else 0
                
                return {
                    'price': prev_close,
                    'open': open_price,
                    'high': r.get('h', 0),
                    'low': r.get('l', 0),
                    'volume': r.get('v', 0),
                    'change': change,
                    'change_pct': change_pct
                }
        return {'price': 0, 'change': 0, 'change_pct': 0}
    except:
        return {'price': 0, 'change': 0, 'change_pct': 0}


def fetch_vix() -> Dict:
    """Fetch VIX data"""
    quote = fetch_quote('VIX')
    
    vix = quote.get('price', 0)
    
    # Determine VIX regime
    if vix < 15:
        regime = 'LOW'
        signal = 'RISK-ON'
        description = 'Low volatility - favorable for long options'
    elif vix < 20:
        regime = 'NORMAL'
        signal = 'NEUTRAL'
        description = 'Normal volatility environment'
    elif vix < 25:
        regime = 'ELEVATED'
        signal = 'CAUTION'
        description = 'Elevated volatility - reduce position size'
    elif vix < 30:
        regime = 'HIGH'
        signal = 'DEFENSIVE'
        description = 'High volatility - consider hedges or cash'
    else:
        regime = 'EXTREME'
        signal = 'RISK-OFF'
        description = 'Extreme fear - wait for stabilization'
    
    return {
        'vix': vix,
        'change': quote.get('change', 0),
        'change_pct': quote.get('change_pct', 0),
        'regime': regime,
        'signal': signal,
        'description': description
    }


def fetch_spy_analysis() -> Dict:
    """Fetch SPY data and trend analysis"""
    quote = fetch_quote('SPY')
    
    price = quote.get('price', 0)
    change_pct = quote.get('change_pct', 0)
    
    # Simple trend assessment
    if change_pct > 0.5:
        trend = 'BULLISH'
        signal = 'RISK-ON'
    elif change_pct > 0:
        trend = 'SLIGHTLY BULLISH'
        signal = 'NEUTRAL-BULLISH'
    elif change_pct > -0.5:
        trend = 'SLIGHTLY BEARISH'
        signal = 'NEUTRAL-BEARISH'
    else:
        trend = 'BEARISH'
        signal = 'RISK-OFF'
    
    return {
        'price': price,
        'change': quote.get('change', 0),
        'change_pct': change_pct,
        'trend': trend,
        'signal': signal
    }


def fetch_sector_performance() -> List[Dict]:
    """Fetch all sector ETF performance"""
    sectors = []
    
    for etf, name in SECTOR_ETFS.items():
        quote = fetch_quote(etf)
        sectors.append({
            'etf': etf,
            'name': name,
            'price': quote.get('price', 0),
            'change_pct': quote.get('change_pct', 0)
        })
    
    # Sort by performance
    sectors.sort(key=lambda x: x['change_pct'], reverse=True)
    
    return sectors


def get_stock_sector(symbol: str) -> Dict:
    """Get sector info for a stock"""
    etf = STOCK_TO_SECTOR.get(symbol.upper(), 'SPY')
    name = SECTOR_ETFS.get(etf, 'Market')
    
    quote = fetch_quote(etf)
    
    return {
        'etf': etf,
        'name': name,
        'change_pct': quote.get('change_pct', 0),
        'favorable': quote.get('change_pct', 0) > 0
    }


# ============================================================================
# MARKET INTERNALS
# ============================================================================

def get_market_internals() -> Dict:
    """
    Get market internals assessment
    
    In production, would include:
    - Advance/Decline ratio
    - New highs/lows
    - Put/call ratio
    - McClellan Oscillator
    
    For now, using proxies
    """
    spy = fetch_spy_analysis()
    vix = fetch_vix()
    
    # Simple breadth proxy using QQQ vs SPY
    qqq = fetch_quote('QQQ')
    iwm = fetch_quote('IWM')  # Small caps
    
    spy_pct = spy.get('change_pct', 0)
    qqq_pct = qqq.get('change_pct', 0)
    iwm_pct = iwm.get('change_pct', 0)
    
    # Breadth assessment
    if iwm_pct > spy_pct and qqq_pct > 0:
        breadth = 'BROAD RALLY'
        breadth_signal = 'BULLISH'
    elif iwm_pct < spy_pct - 0.5:
        breadth = 'NARROW (Large Caps Only)'
        breadth_signal = 'CAUTION'
    elif spy_pct < 0 and iwm_pct < 0:
        breadth = 'BROAD SELLING'
        breadth_signal = 'BEARISH'
    else:
        breadth = 'MIXED'
        breadth_signal = 'NEUTRAL'
    
    # Overall risk assessment
    risk_score = 50  # Neutral baseline
    
    # VIX impact
    if vix['regime'] == 'LOW':
        risk_score += 20
    elif vix['regime'] == 'ELEVATED':
        risk_score -= 10
    elif vix['regime'] in ['HIGH', 'EXTREME']:
        risk_score -= 30
    
    # Trend impact
    if spy['trend'] == 'BULLISH':
        risk_score += 15
    elif spy['trend'] == 'BEARISH':
        risk_score -= 15
    
    # Breadth impact
    if breadth_signal == 'BULLISH':
        risk_score += 10
    elif breadth_signal == 'BEARISH':
        risk_score -= 10
    
    risk_score = max(0, min(100, risk_score))
    
    if risk_score >= 70:
        risk_env = 'RISK-ON'
        risk_desc = 'Favorable environment for long positions'
    elif risk_score >= 50:
        risk_env = 'NEUTRAL'
        risk_desc = 'Normal conditions - trade setups as they come'
    elif risk_score >= 30:
        risk_env = 'CAUTIOUS'
        risk_desc = 'Elevated risk - reduce size, tighten stops'
    else:
        risk_env = 'RISK-OFF'
        risk_desc = 'Unfavorable - consider cash or hedges'
    
    return {
        'spy': spy,
        'vix': vix,
        'qqq_change': qqq_pct,
        'iwm_change': iwm_pct,
        'breadth': breadth,
        'breadth_signal': breadth_signal,
        'risk_score': risk_score,
        'risk_environment': risk_env,
        'risk_description': risk_desc
    }


# ============================================================================
# POSITION CONTEXT
# ============================================================================

def get_position_market_context(symbol: str) -> Dict:
    """
    Get market context relevant to a specific position
    """
    # Overall market
    internals = get_market_internals()
    
    # Sector specific
    sector = get_stock_sector(symbol)
    
    # Build context
    warnings = []
    positives = []
    
    # Market warnings
    if internals['risk_environment'] == 'RISK-OFF':
        warnings.append('MARKET: Risk-off environment - consider reducing exposure')
    elif internals['risk_environment'] == 'CAUTIOUS':
        warnings.append('MARKET: Elevated caution - tighter stops recommended')
    
    if internals['vix']['regime'] in ['HIGH', 'EXTREME']:
        warnings.append(f"VIX: {internals['vix']['vix']:.1f} ({internals['vix']['regime']}) - high volatility")
    
    # Sector context
    if sector['change_pct'] < -1:
        warnings.append(f"SECTOR: {sector['name']} ({sector['etf']}) down {sector['change_pct']:.1f}%")
    elif sector['change_pct'] > 1:
        positives.append(f"SECTOR: {sector['name']} ({sector['etf']}) up +{sector['change_pct']:.1f}%")
    
    # Market positives
    if internals['risk_environment'] == 'RISK-ON':
        positives.append('MARKET: Risk-on environment - favorable for longs')
    
    if internals['vix']['regime'] == 'LOW':
        positives.append(f"VIX: {internals['vix']['vix']:.1f} (LOW) - cheap options")
    
    if internals['spy']['trend'] == 'BULLISH':
        positives.append(f"SPY: +{internals['spy']['change_pct']:.1f}% - bullish trend")
    
    return {
        'market': internals,
        'sector': sector,
        'warnings': warnings,
        'positives': positives,
        'overall_favorable': len(positives) >= len(warnings)
    }


# ============================================================================
# CORRELATION CHECK
# ============================================================================

def check_portfolio_correlation(positions: List[Dict]) -> Dict:
    """
    Check portfolio correlation/concentration risk
    """
    if not positions:
        return {'warning': False, 'message': 'No positions'}
    
    # Count by sector
    sector_counts = {}
    direction_counts = {'CALL': 0, 'PUT': 0}
    
    for pos in positions:
        symbol = pos.get('symbol', '')
        direction = pos.get('direction', 'CALL')
        
        sector_etf = STOCK_TO_SECTOR.get(symbol, 'OTHER')
        sector_name = SECTOR_ETFS.get(sector_etf, 'Other')
        
        sector_counts[sector_name] = sector_counts.get(sector_name, 0) + 1
        direction_counts[direction] = direction_counts.get(direction, 0) + 1
    
    # Check concentration
    total = len(positions)
    warnings = []
    
    for sector, count in sector_counts.items():
        pct = count / total * 100
        if pct >= 60:
            warnings.append(f"HIGH CONCENTRATION: {pct:.0f}% in {sector}")
        elif pct >= 40 and count >= 2:
            warnings.append(f"MODERATE CONCENTRATION: {pct:.0f}% in {sector}")
    
    # Direction bias
    call_pct = direction_counts['CALL'] / total * 100 if total > 0 else 0
    if call_pct >= 80:
        warnings.append(f"DIRECTIONAL BIAS: {call_pct:.0f}% CALLS - highly bullish")
    elif call_pct <= 20:
        warnings.append(f"DIRECTIONAL BIAS: {100-call_pct:.0f}% PUTS - highly bearish")
    
    return {
        'sector_breakdown': sector_counts,
        'direction_breakdown': direction_counts,
        'warnings': warnings,
        'concentrated': len(warnings) > 0
    }


# ============================================================================
# FULL MARKET SNAPSHOT
# ============================================================================

def get_market_snapshot() -> Dict:
    """
    Complete market snapshot for dashboard
    """
    vix = fetch_vix()
    spy = fetch_spy_analysis()
    sectors = fetch_sector_performance()
    internals = get_market_internals()
    
    # Top/bottom sectors
    top_sectors = sectors[:3]
    bottom_sectors = sectors[-3:]
    
    return {
        'timestamp': datetime.now().isoformat(),
        'vix': vix,
        'spy': spy,
        'sectors': sectors,
        'top_sectors': top_sectors,
        'bottom_sectors': bottom_sectors,
        'internals': internals,
        'summary': {
            'risk_environment': internals['risk_environment'],
            'vix_regime': vix['regime'],
            'market_trend': spy['trend'],
            'breadth': internals['breadth']
        }
    }
