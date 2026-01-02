"""
News Service Module
===================
Fetches news, catalysts, and earnings data:
- Polygon News API for headlines
- Earnings calendar detection
- Sentiment analysis
- Catalyst alerts
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import re

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')


# ============================================================================
# NEWS FETCHING
# ============================================================================

def fetch_stock_news(symbol: str, limit: int = 5) -> List[Dict]:
    """
    Fetch recent news for a stock from Polygon
    """
    if not POLYGON_API_KEY:
        return []
    
    try:
        url = "https://api.polygon.io/v2/reference/news"
        params = {
            'ticker': symbol.upper(),
            'limit': limit,
            'order': 'desc',
            'sort': 'published_utc',
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        news_items = []
        
        for item in data.get('results', []):
            # Parse published time
            pub_time = item.get('published_utc', '')
            try:
                pub_dt = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                time_ago = get_time_ago(pub_dt)
            except:
                time_ago = 'Recently'
            
            # Simple sentiment analysis
            title = item.get('title', '')
            description = item.get('description', '')
            sentiment = analyze_sentiment(title + ' ' + description)
            
            news_items.append({
                'title': title,
                'description': description[:200] + '...' if len(description) > 200 else description,
                'source': item.get('publisher', {}).get('name', 'Unknown'),
                'url': item.get('article_url', ''),
                'published': pub_time,
                'time_ago': time_ago,
                'sentiment': sentiment,
                'tickers': item.get('tickers', [])
            })
        
        return news_items
        
    except Exception as e:
        print(f"News fetch error: {e}")
        return []


def get_time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable time ago"""
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}m ago"
    
    return "Just now"


def analyze_sentiment(text: str) -> str:
    """
    Simple keyword-based sentiment analysis
    Returns: POSITIVE, NEGATIVE, or NEUTRAL
    """
    text_lower = text.lower()
    
    positive_words = [
        'surge', 'jump', 'rally', 'gain', 'rise', 'soar', 'boost', 'upgrade',
        'beat', 'exceed', 'strong', 'growth', 'profit', 'success', 'bullish',
        'breakthrough', 'record', 'high', 'outperform', 'buy', 'positive',
        'partnership', 'deal', 'contract', 'expansion', 'innovation'
    ]
    
    negative_words = [
        'drop', 'fall', 'decline', 'loss', 'down', 'plunge', 'crash', 'downgrade',
        'miss', 'weak', 'concern', 'risk', 'warning', 'bearish', 'sell',
        'lawsuit', 'investigation', 'cut', 'layoff', 'bankruptcy', 'default',
        'delay', 'cancel', 'recall', 'fine', 'penalty', 'negative'
    ]
    
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count + 1:
        return 'POSITIVE'
    elif neg_count > pos_count + 1:
        return 'NEGATIVE'
    else:
        return 'NEUTRAL'


# ============================================================================
# EARNINGS DETECTION
# ============================================================================

# Static earnings calendar (would be fetched from API in production)
# Format: 'SYMBOL': 'YYYY-MM-DD'
EARNINGS_CALENDAR = {
    # Tech
    'AAPL': '2025-01-30', 'MSFT': '2025-01-28', 'GOOGL': '2025-02-04',
    'AMZN': '2025-02-06', 'META': '2025-01-29', 'NVDA': '2025-02-26',
    'AMD': '2025-01-28', 'TSLA': '2025-01-29', 'NFLX': '2025-01-21',
    # Social/Communication
    'SNAP': '2025-02-04', 'PINS': '2025-02-06', 'DIS': '2025-02-05',
    # Financials
    'JPM': '2025-01-15', 'BAC': '2025-01-16', 'GS': '2025-01-15',
    # Chinese Tech
    'BIDU': '2025-02-20', 'BABA': '2025-02-20', 'JD': '2025-03-06',
    # Others
    'BA': '2025-01-28', 'CAT': '2025-01-30', 'XOM': '2025-01-31',
}


def get_earnings_date(symbol: str) -> Optional[Dict]:
    """
    Get earnings date for a symbol
    """
    symbol = symbol.upper()
    
    # Check static calendar first
    if symbol in EARNINGS_CALENDAR:
        date_str = EARNINGS_CALENDAR[symbol]
        try:
            earnings_date = datetime.strptime(date_str, '%Y-%m-%d')
            days_until = (earnings_date - datetime.now()).days
            
            return {
                'date': date_str,
                'days_until': days_until,
                'is_soon': days_until <= 14,
                'is_imminent': days_until <= 5,
                'source': 'calendar'
            }
        except:
            pass
    
    # Try Polygon API for earnings
    if POLYGON_API_KEY:
        try:
            url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
            params = {'apiKey': POLYGON_API_KEY}
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json().get('results', {})
                # Polygon doesn't directly provide earnings, but we can check news
                pass
        except:
            pass
    
    return None


def check_earnings_risk(symbol: str, dte: int) -> Dict:
    """
    Check if earnings falls within option expiration
    """
    earnings = get_earnings_date(symbol)
    
    if not earnings:
        return {
            'has_earnings': False,
            'risk_level': 'UNKNOWN',
            'warning': None
        }
    
    days_until = earnings['days_until']
    
    # Check if earnings is before expiration
    if days_until > dte:
        return {
            'has_earnings': True,
            'date': earnings['date'],
            'days_until': days_until,
            'risk_level': 'NONE',
            'warning': None,
            'message': f"Earnings {earnings['date']} is after your expiration"
        }
    
    # Earnings is within the trade window
    if days_until <= 3:
        risk_level = 'CRITICAL'
        warning = f"⛔ EARNINGS IN {days_until} DAYS ({earnings['date']}) - EXIT NOW or risk IV crush"
    elif days_until <= 7:
        risk_level = 'HIGH'
        warning = f"🔴 EARNINGS IN {days_until} DAYS ({earnings['date']}) - Plan exit before"
    elif days_until <= 14:
        risk_level = 'MODERATE'
        warning = f"🟡 EARNINGS IN {days_until} DAYS ({earnings['date']}) - Be aware"
    else:
        risk_level = 'LOW'
        warning = f"🟢 EARNINGS {earnings['date']} ({days_until} days) - Monitor as it approaches"
    
    return {
        'has_earnings': True,
        'date': earnings['date'],
        'days_until': days_until,
        'risk_level': risk_level,
        'warning': warning,
        'within_expiration': True
    }


# ============================================================================
# CATALYST DETECTION
# ============================================================================

def detect_catalysts(symbol: str, news: List[Dict] = None) -> List[Dict]:
    """
    Detect potential catalysts from news
    """
    if news is None:
        news = fetch_stock_news(symbol, 10)
    
    catalysts = []
    
    # Catalyst keywords
    catalyst_patterns = {
        'FDA': ['fda', 'approval', 'drug', 'clinical trial', 'phase'],
        'DEAL': ['acquisition', 'merger', 'buyout', 'deal', 'partnership'],
        'PRODUCT': ['launch', 'release', 'announce', 'unveil', 'new product'],
        'LEGAL': ['lawsuit', 'settlement', 'investigation', 'sec', 'doj'],
        'GUIDANCE': ['guidance', 'outlook', 'forecast', 'raised', 'lowered'],
        'ANALYST': ['upgrade', 'downgrade', 'price target', 'rating'],
        'EXECUTIVE': ['ceo', 'cfo', 'resign', 'hire', 'executive'],
    }
    
    for item in news:
        text = (item.get('title', '') + ' ' + item.get('description', '')).lower()
        
        for catalyst_type, keywords in catalyst_patterns.items():
            if any(kw in text for kw in keywords):
                catalysts.append({
                    'type': catalyst_type,
                    'headline': item.get('title'),
                    'time_ago': item.get('time_ago'),
                    'sentiment': item.get('sentiment'),
                    'url': item.get('url')
                })
                break  # One catalyst per news item
    
    return catalysts


# ============================================================================
# POSITION NEWS SUMMARY
# ============================================================================

def get_position_news_summary(symbol: str, dte: int = 30) -> Dict:
    """
    Get complete news and catalyst summary for a position
    """
    # Fetch news
    news = fetch_stock_news(symbol, 10)
    
    # Check earnings
    earnings = check_earnings_risk(symbol, dte)
    
    # Detect catalysts
    catalysts = detect_catalysts(symbol, news)
    
    # Overall sentiment from recent news
    sentiments = [n.get('sentiment', 'NEUTRAL') for n in news[:5]]
    pos_count = sentiments.count('POSITIVE')
    neg_count = sentiments.count('NEGATIVE')
    
    if pos_count > neg_count + 1:
        overall_sentiment = 'POSITIVE'
    elif neg_count > pos_count + 1:
        overall_sentiment = 'NEGATIVE'
    else:
        overall_sentiment = 'NEUTRAL'
    
    # Build warnings
    warnings = []
    
    if earnings.get('warning'):
        warnings.append(earnings['warning'])
    
    # Check for negative catalysts
    neg_catalysts = [c for c in catalysts if c.get('sentiment') == 'NEGATIVE']
    for cat in neg_catalysts[:2]:
        warnings.append(f"📰 {cat['type']}: {cat['headline'][:50]}...")
    
    # Positive signals
    positives = []
    pos_catalysts = [c for c in catalysts if c.get('sentiment') == 'POSITIVE']
    for cat in pos_catalysts[:2]:
        positives.append(f"📰 {cat['type']}: {cat['headline'][:50]}...")
    
    return {
        'news': news[:5],
        'earnings': earnings,
        'catalysts': catalysts,
        'overall_sentiment': overall_sentiment,
        'warnings': warnings,
        'positives': positives,
        'has_risk': len(warnings) > 0 or earnings.get('risk_level') in ['HIGH', 'CRITICAL']
    }


# ============================================================================
# MARKET-WIDE NEWS
# ============================================================================

def get_market_news(limit: int = 10) -> List[Dict]:
    """
    Get general market news
    """
    # Fetch news for major indices/tickers
    all_news = []
    
    for ticker in ['SPY', 'QQQ']:
        news = fetch_stock_news(ticker, 5)
        all_news.extend(news)
    
    # Sort by time and dedupe
    seen_titles = set()
    unique_news = []
    
    for item in all_news:
        title = item.get('title', '')
        if title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(item)
    
    # Sort by published date
    unique_news.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    return unique_news[:limit]
