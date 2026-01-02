"""
AI Trading Advisor - Expert Mentor Voice
=========================================
Replace your existing ai_advisor.py with this version.
Same functions, but speaks like a senior trading mentor.
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Simple cache
_cache = {}
_cache_expiry = {}

def get_cached(key):
    if key in _cache and time.time() < _cache_expiry.get(key, 0):
        return _cache[key]
    return None

def set_cached(key, value, ttl=300):
    _cache[key] = value
    _cache_expiry[key] = time.time() + ttl


@dataclass
class AdvisorBriefing:
    """Expert advisor briefing"""
    has_content: bool = False
    market_assessment: str = ""
    position_review: str = ""
    todays_playbook: str = ""
    risk_advisory: str = ""
    raw_response: str = ""
    generated_at: str = ""
    model_used: str = ""


class ExpertAdvisor:
    """
    AI Trading Advisor with expert mentor voice.
    Speaks with authority, gives specific actionable guidance.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY', '')
        self.model = model or os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
    
    def get_briefing(self, market_data: Dict, positions: List[Dict], 
                     journal_stats: Dict, watchlist_hot: List[Dict] = None) -> AdvisorBriefing:
        """
        Get expert trading briefing.
        
        Args:
            market_data: Dict with vix, spy_change, headline, etc.
            positions: List of position dicts with symbol, strike, type, pnl_pct, dte
            journal_stats: Dict with win_rate, total_pnl, total_trades
            watchlist_hot: Optional list of hot stocks from scanner
        
        Returns:
            AdvisorBriefing with parsed sections
        """
        
        # Check cache first
        cached = get_cached("advisor_briefing")
        if cached:
            return cached
        
        if not self.api_key:
            return AdvisorBriefing(has_content=False)
        
        # Build position summary
        if positions:
            pos_lines = []
            for p in positions:
                symbol = p.get('symbol', 'UNK')
                strike = p.get('strike', 0)
                ptype = 'C' if 'CALL' in p.get('type', '') else 'P'
                pnl = p.get('pnl_pct', p.get('pnl_percent', 0))
                dte = p.get('dte', 0)
                entry = p.get('entry_price', p.get('entry', 0))
                current = p.get('current_price', p.get('current', entry))
                delta = p.get('delta', 0.5)
                
                pos_lines.append(
                    f"- {symbol} {strike}{ptype}: {pnl:+.0f}% P&L, {dte} DTE, "
                    f"entry ${entry:.2f}, current ${current:.2f}, delta {delta:.2f}"
                )
            pos_summary = "\n".join(pos_lines)
        else:
            pos_summary = "No open positions - fully in cash."
        
        # Build watchlist summary
        if watchlist_hot:
            hot_lines = [f"- {h.get('symbol', '')}: {h.get('headline', '')} (Grade {h.get('grade', h.get('setup_quality', 'C'))})" 
                        for h in watchlist_hot[:5]]
            hot_summary = "\n".join(hot_lines)
        else:
            hot_summary = "No watchlist data available."
        
        # Extract market data
        vix = market_data.get('vix', market_data.get('vix_level', 18))
        spy_change = market_data.get('spy_change', market_data.get('spy_chg', 0))
        if isinstance(market_data.get('spy'), dict):
            spy_change = market_data['spy'].get('change_pct', 0)
        if isinstance(market_data.get('vix'), dict):
            vix = market_data['vix'].get('level', 18)
        
        # Journal stats
        win_rate = journal_stats.get('win_rate', 0)
        total_pnl = journal_stats.get('total_pnl', 0)
        total_trades = journal_stats.get('total_trades', journal_stats.get('trades', 0))
        profit_factor = journal_stats.get('profit_factor', 0)
        
        prompt = f"""You are a senior options trading advisor with 20+ years of experience managing institutional portfolios. You speak with authority and precision. Your guidance is direct, confident, and actionable - never vague.

CURRENT MARKET CONDITIONS:
- VIX: {vix:.1f}
- SPY: {spy_change:+.1f}% today
- IV Environment: {'Low - premiums cheap, favor buying' if vix < 16 else 'Normal' if vix < 22 else 'Elevated - premiums rich' if vix < 28 else 'High fear - caution warranted'}

CLIENT'S OPEN POSITIONS:
{pos_summary}

HOT WATCHLIST SETUPS:
{hot_summary}

CLIENT'S TRACK RECORD:
- Total trades: {total_trades}
- Win rate: {win_rate:.0f}%
- Cumulative P&L: ${total_pnl:,.0f}
- Profit factor: {profit_factor:.2f}

Provide a concise executive briefing with these exact sections:

**MARKET ASSESSMENT**
2-3 sentences on what current conditions mean for options trading. Reference VIX, trend, and what strategies are favored.

**POSITION MANAGEMENT**  
For each open position, give a specific recommendation: HOLD, ADD, TRIM, or EXIT. Include specific price triggers where relevant. If no positions, state the client is in cash and whether that's appropriate given conditions.

**TODAY'S PLAYBOOK**
1-2 specific, actionable opportunities. Name specific setups, strikes ranges, and timeframes. Be concrete, not generic.

**RISK ADVISORY**
The single most important risk to monitor today. Be specific - upcoming events, technical levels, or position-specific concerns.

Write as a senior advisor briefing a sophisticated client. Be direct and confident. No hedging language."""

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                text = response.json()["content"][0]["text"]
                
                # Parse sections
                briefing = AdvisorBriefing(
                    has_content=True,
                    raw_response=text,
                    generated_at=datetime.now().strftime("%I:%M %p"),
                    model_used=self.model
                )
                
                # Extract sections
                sections = {
                    "market_assessment": ["MARKET ASSESSMENT", "MARKET"],
                    "position_review": ["POSITION MANAGEMENT", "POSITIONS", "POSITION REVIEW"],
                    "todays_playbook": ["TODAY'S PLAYBOOK", "PLAYBOOK", "TODAY"],
                    "risk_advisory": ["RISK ADVISORY", "RISK", "WARNING"]
                }
                
                for attr, keywords in sections.items():
                    for keyword in keywords:
                        if keyword in text.upper():
                            # Find content after this keyword
                            start = text.upper().find(keyword)
                            if start != -1:
                                # Find the next section or end
                                end = len(text)
                                for other_keywords in sections.values():
                                    for other_kw in other_keywords:
                                        if other_kw != keyword:
                                            other_start = text.upper().find(other_kw, start + len(keyword))
                                            if other_start != -1 and other_start < end:
                                                end = other_start
                                
                                # Extract and clean
                                content = text[start:end]
                                # Remove the header line
                                lines = content.split('\n')
                                content = '\n'.join(lines[1:]).strip()
                                content = content.strip('*').strip()
                                
                                setattr(briefing, attr, content)
                                break
                
                # Cache for 5 minutes
                set_cached("advisor_briefing", briefing, 300)
                return briefing
                
            else:
                print(f"AI API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"AI request error: {e}")
        
        return AdvisorBriefing(has_content=False)
    
    def clear_cache(self):
        """Clear cached briefing to force refresh"""
        if "advisor_briefing" in _cache:
            del _cache["advisor_briefing"]


# ============== HELPER FUNCTION ==============

def get_advisor_briefing_dict(advisor, market_data, positions_dict, portfolio_risk, 
                               hot_list, journal_data, watchlist) -> Dict:
    """
    Compatibility wrapper - returns dict for template rendering.
    Works with existing cockpit.py templates.
    """
    
    # Convert positions dict to list
    positions_list = []
    if isinstance(positions_dict, dict):
        for pid, p in positions_dict.items():
            positions_list.append(p)
    else:
        positions_list = list(positions_dict) if positions_dict else []
    
    # Get journal stats
    if isinstance(journal_data, dict):
        journal_stats = journal_data.get('stats', journal_data)
    else:
        journal_stats = {'win_rate': 0, 'total_pnl': 0, 'total_trades': 0}
    
    # Get briefing
    briefing = advisor.get_briefing(market_data, positions_list, journal_stats, hot_list)
    
    return {
        'has_content': briefing.has_content,
        'headline': '🎯 Expert Trading Briefing',
        'market_summary': briefing.market_assessment[:200] + '...' if len(briefing.market_assessment) > 200 else briefing.market_assessment,
        'market_outlook': briefing.market_assessment,
        'position_review': briefing.position_review,
        'opportunities': briefing.todays_playbook,
        'what_to_do_today': briefing.todays_playbook,
        'what_to_avoid': briefing.risk_advisory,
        'warnings': [briefing.risk_advisory] if briefing.risk_advisory else [],
        'action_items': [briefing.todays_playbook] if briefing.todays_playbook else [],
        'risk_assessment': briefing.risk_advisory,
        'performance_insight': '',
        'generated_at': briefing.generated_at,
        'model': briefing.model_used,
        'raw': briefing.raw_response
    }


# ============== STANDALONE USAGE ==============

if __name__ == "__main__":
    # Test the advisor
    advisor = ExpertAdvisor()
    
    test_market = {"vix": 18.5, "spy_change": 0.6}
    test_positions = [
        {"symbol": "AAPL", "strike": 185, "type": "LONG_CALL", "pnl_pct": 12, "dte": 14, "entry_price": 3.50, "current_price": 3.92, "delta": 0.55}
    ]
    test_stats = {"win_rate": 62, "total_pnl": 4500, "total_trades": 28, "profit_factor": 1.8}
    
    print("Getting expert briefing...")
    briefing = advisor.get_briefing(test_market, test_positions, test_stats)
    
    if briefing.has_content:
        print("\n" + "="*50)
        print("MARKET ASSESSMENT:")
        print(briefing.market_assessment)
        print("\nPOSITION MANAGEMENT:")
        print(briefing.position_review)
        print("\nTODAY'S PLAYBOOK:")
        print(briefing.todays_playbook)
        print("\nRISK ADVISORY:")
        print(briefing.risk_advisory)
    else:
        print("No API key configured")


# ============== BACKWARDS COMPATIBILITY ==============
# These aliases ensure the new file works with existing cockpit.py

AITradingAdvisor = ExpertAdvisor  # Alias for backwards compatibility

