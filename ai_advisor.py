"""
AI Trading Advisor - Expert Mentor Voice
=========================================
Speaks like a senior trading mentor with 20+ years experience.
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

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
    has_content: bool = False
    market_assessment: str = ""
    position_review: str = ""
    todays_playbook: str = ""
    risk_advisory: str = ""
    raw_response: str = ""
    generated_at: str = ""
    model_used: str = ""


class ExpertAdvisor:
    """AI Trading Advisor with expert mentor voice."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY', '')
        self.model = model or os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
    
    def get_briefing(self, market_data: Dict, positions: List[Dict], 
                     journal_stats: Dict, watchlist_hot: List[Dict] = None) -> AdvisorBriefing:
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
                ptype = 'C' if 'CALL' in str(p.get('type', '')) else 'P'
                pnl = p.get('pnl_pct', p.get('pnl_percent', 0))
                dte = p.get('dte', 0)
                pos_lines.append(f"- {symbol} {strike}{ptype}: {pnl:+.0f}% P&L, {dte} DTE")
            pos_summary = "\n".join(pos_lines)
        else:
            pos_summary = "No open positions - fully in cash."
        
        # Extract market data
        vix = 18
        spy_change = 0
        if isinstance(market_data.get('vix'), dict):
            vix = market_data['vix'].get('level', 18)
        else:
            vix = market_data.get('vix', 18)
        if isinstance(market_data.get('spy'), dict):
            spy_change = market_data['spy'].get('change_pct', 0)
        else:
            spy_change = market_data.get('spy_change', market_data.get('spy_chg', 0))
        
        win_rate = journal_stats.get('win_rate', 0)
        total_pnl = journal_stats.get('total_pnl', 0)
        total_trades = journal_stats.get('total_trades', journal_stats.get('trades', 0))
        
        prompt = f"""You are a senior options trading advisor with 20+ years experience. You speak with authority and precision. Be direct and actionable.

MARKET CONDITIONS:
- VIX: {vix:.1f}
- SPY: {spy_change:+.1f}% today

CLIENT'S POSITIONS:
{pos_summary}

CLIENT'S TRACK RECORD:
- Trades: {total_trades}, Win rate: {win_rate:.0f}%, P&L: ${total_pnl:,.0f}

Provide a brief executive briefing:

1. **MARKET ASSESSMENT** - What conditions mean for options trading today (2-3 sentences)
2. **POSITION MANAGEMENT** - Specific recommendation for each position: HOLD, TRIM, ADD, or EXIT
3. **TODAY'S PLAYBOOK** - 1-2 specific actionable opportunities
4. **RISK ADVISORY** - Key risk to monitor today

Be concise and professional. No fluff."""

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
                briefing = AdvisorBriefing(
                    has_content=True,
                    raw_response=text,
                    generated_at=datetime.now().strftime("%I:%M %p"),
                    model_used=self.model
                )
                
                # Simple section extraction
                sections = ["MARKET ASSESSMENT", "POSITION MANAGEMENT", "TODAY'S PLAYBOOK", "RISK ADVISORY"]
                current_section = None
                current_content = []
                
                for line in text.split('\n'):
                    line_upper = line.upper()
                    found_section = None
                    for s in sections:
                        if s in line_upper:
                            found_section = s
                            break
                    
                    if found_section:
                        if current_section and current_content:
                            content = '\n'.join(current_content).strip()
                            if "MARKET" in current_section:
                                briefing.market_assessment = content
                            elif "POSITION" in current_section:
                                briefing.position_review = content
                            elif "PLAYBOOK" in current_section:
                                briefing.todays_playbook = content
                            elif "RISK" in current_section:
                                briefing.risk_advisory = content
                        current_section = found_section
                        current_content = []
                    elif current_section:
                        current_content.append(line)
                
                # Save last section
                if current_section and current_content:
                    content = '\n'.join(current_content).strip()
                    if "MARKET" in current_section:
                        briefing.market_assessment = content
                    elif "POSITION" in current_section:
                        briefing.position_review = content
                    elif "PLAYBOOK" in current_section:
                        briefing.todays_playbook = content
                    elif "RISK" in current_section:
                        briefing.risk_advisory = content
                
                set_cached("advisor_briefing", briefing, 300)
                return briefing
                
        except Exception as e:
            print(f"AI error: {e}")
        
        return AdvisorBriefing(has_content=False)
    
    def clear_cache(self):
        if "advisor_briefing" in _cache:
            del _cache["advisor_briefing"]


# Backwards compatibility alias
AITradingAdvisor = ExpertAdvisor


def get_advisor_briefing_dict(advisor, market_data, positions_dict, portfolio_risk, 
                               hot_list, journal_data, watchlist) -> Dict:
    """Compatibility wrapper for existing cockpit.py"""
    positions_list = []
    if isinstance(positions_dict, dict):
        for pid, p in positions_dict.items():
            positions_list.append(p)
    else:
        positions_list = list(positions_dict) if positions_dict else []
    
    if isinstance(journal_data, dict):
        journal_stats = journal_data.get('stats', journal_data)
    else:
        journal_stats = {'win_rate': 0, 'total_pnl': 0, 'total_trades': 0}
    
    briefing = advisor.get_briefing(market_data, positions_list, journal_stats, hot_list)
    
    return {
        'has_content': briefing.has_content,
        'headline': '🎯 Expert Trading Briefing',
        'market_summary': briefing.market_assessment[:200] if briefing.market_assessment else '',
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
