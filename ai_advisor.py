"""
Trading Cockpit - AI Trading Advisor
=====================================
Claude-powered advisor that analyzes ALL your data:
- Market conditions
- Open positions
- Portfolio risk
- Watchlist opportunities
- Trade journal performance

Provides a comprehensive daily briefing and real-time advice.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import requests


@dataclass
class AdvisorBriefing:
    """Complete AI advisor briefing"""
    # Summary
    headline: str = ""
    market_summary: str = ""
    
    # Sections
    market_outlook: str = ""
    position_review: str = ""
    risk_assessment: str = ""
    opportunities: str = ""
    action_items: List[str] = field(default_factory=list)
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Detailed advice
    what_to_do_today: str = ""
    what_to_avoid: str = ""
    
    # Performance insight
    performance_insight: str = ""
    
    # Raw response
    full_response: str = ""
    
    # Meta
    generated_at: str = ""
    model_used: str = ""


class AITradingAdvisor:
    """
    Claude-powered trading advisor that sees everything
    and provides actionable advice.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        # Allow user to specify model - default to Opus 4.5 if available
        self.model = model or os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def set_model(self, model: str):
        """Change the model (e.g., to opus)"""
        self.model = model
    
    def get_briefing(self, 
                     market_data: Dict,
                     positions: Dict,
                     portfolio_risk: Dict,
                     hot_list: List[Dict],
                     journal_stats: Dict,
                     watchlist: List[Dict]) -> AdvisorBriefing:
        """
        Generate comprehensive AI briefing based on all data.
        """
        briefing = AdvisorBriefing(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            model_used=self.model
        )
        
        if not self.api_key:
            briefing.headline = "⚠️ AI Advisor Not Connected"
            briefing.market_summary = "Add your ANTHROPIC_API_KEY to .env to enable AI advisor"
            briefing.action_items = ["Add ANTHROPIC_API_KEY to .env file"]
            return briefing
        
        # Build comprehensive prompt
        prompt = self._build_prompt(market_data, positions, portfolio_risk, 
                                    hot_list, journal_stats, watchlist)
        
        # Call Claude
        try:
            response = self._call_claude(prompt)
            briefing = self._parse_response(response, briefing)
        except Exception as e:
            briefing.headline = f"⚠️ AI Error: {str(e)[:50]}"
            briefing.market_summary = "Could not generate AI briefing. Check API key."
        
        return briefing
    
    def _build_prompt(self, market: Dict, positions: Dict, risk: Dict,
                      hot_list: List, journal: Dict, watchlist: List) -> str:
        """Build comprehensive prompt with all data"""
        
        # Format positions
        pos_text = "No open positions."
        if positions:
            pos_lines = []
            for pid, p in positions.items():
                pos_lines.append(f"- {p.get('symbol')} {p.get('strike')}{p.get('type','')[:1]}: "
                               f"{p.get('pnl_percent', 0):+.0f}% P&L, {p.get('dte', 0)} DTE, "
                               f"Score: {p.get('score_grade', 'N/A')}, Status: {p.get('status', 'N/A')}")
            pos_text = "\n".join(pos_lines)
        
        # Format hot list
        hot_text = "No hot setups currently."
        if hot_list:
            hot_lines = []
            for h in hot_list[:5]:
                rec = h.get('options_rec', {})
                hot_lines.append(f"- {h.get('symbol')}: Score {h.get('hot_score', 0):.0f}, "
                               f"Quality: {h.get('setup_quality')}, Signal: {h.get('signal')}, "
                               f"Rec: {rec.get('direction', 'N/A')} ${rec.get('strike', 'N/A')}")
            hot_text = "\n".join(hot_lines)
        
        # Format watchlist
        wl_text = f"{len(watchlist)} stocks" if watchlist else "Empty"
        
        prompt = f"""You are an expert options trading advisor. Analyze this trader's complete situation and provide actionable advice.

## CURRENT MARKET CONDITIONS
- Regime: {market.get('regime', 'Unknown')}
- Headline: {market.get('headline', 'N/A')}
- VIX: {market.get('vix', {}).get('level', 'N/A')} ({market.get('vix', {}).get('regime', 'N/A')})
- SPY: {market.get('spy', {}).get('direction', 'N/A')}, {market.get('spy', {}).get('change_pct', 0):+.1f}%
- Strategy Bias: {market.get('strategy', {}).get('bias', 'N/A')}
- Preferred Direction: {market.get('strategy', {}).get('preferred_direction', 'N/A')}

## OPEN POSITIONS
{pos_text}

## PORTFOLIO RISK
- Total Delta: {risk.get('greeks', {}).get('total_delta', 0):.0f}
- Daily Theta: ${risk.get('greeks', {}).get('total_theta', 0):.0f}/day
- Capital at Risk: {risk.get('risk', {}).get('capital_at_risk_pct', 0):.1f}%
- Position Count: {risk.get('risk', {}).get('position_count', 0)}
- Risk Level: {risk.get('risk', {}).get('overall_risk', 'N/A')}
- Concentration: {risk.get('correlation', {}).get('largest_sector', 'N/A')} ({risk.get('correlation', {}).get('largest_sector_pct', 0):.0f}%)

## HOT LIST (Best Setups)
{hot_text}

## WATCHLIST
{wl_text}

## TRADING PERFORMANCE (Historical)
- Total Trades: {journal.get('stats', {}).get('total_trades', 0)}
- Win Rate: {journal.get('stats', {}).get('win_rate', 0):.0f}%
- Profit Factor: {journal.get('stats', {}).get('profit_factor', 0):.2f}
- Expectancy: ${journal.get('stats', {}).get('expectancy', 0):.0f}/trade
- Current Streak: {journal.get('stats', {}).get('current_streak', 0)}

---

Based on ALL of this data, provide a comprehensive trading briefing. Be specific, actionable, and direct. This trader needs clear guidance.

Format your response EXACTLY like this:

HEADLINE: [One powerful sentence summarizing the day's outlook]

MARKET_OUTLOOK:
[2-3 sentences on market conditions and what they mean for trading today]

POSITION_REVIEW:
[Review each open position - what to do with each one specifically]

RISK_ASSESSMENT:
[Assess current portfolio risk - is it too high/low? What adjustments needed?]

OPPORTUNITIES:
[Which hot list stocks look best? What specific trades to consider?]

ACTION_ITEMS:
- [Specific action 1]
- [Specific action 2]
- [Specific action 3]
- [Add more as needed]

WARNINGS:
- [Warning 1 if any]
- [Warning 2 if any]

WHAT_TO_DO_TODAY:
[Clear, specific instructions for today's trading session]

WHAT_TO_AVOID:
[What NOT to do today based on conditions]

PERFORMANCE_INSIGHT:
[One insight about their trading performance and how to improve]

Be direct and specific. No fluff. This is real money."""

        return prompt
    
    def _call_claude(self, prompt: str) -> str:
        """Call Claude API"""
        response = requests.post(
            self.base_url,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": self.model,
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text[:100]}")
        
        result = response.json()
        return result['content'][0]['text']
    
    def _parse_response(self, response: str, briefing: AdvisorBriefing) -> AdvisorBriefing:
        """Parse Claude's response into structured briefing"""
        briefing.full_response = response
        
        # Parse sections
        sections = {
            'HEADLINE:': 'headline',
            'MARKET_OUTLOOK:': 'market_outlook',
            'POSITION_REVIEW:': 'position_review',
            'RISK_ASSESSMENT:': 'risk_assessment',
            'OPPORTUNITIES:': 'opportunities',
            'WHAT_TO_DO_TODAY:': 'what_to_do_today',
            'WHAT_TO_AVOID:': 'what_to_avoid',
            'PERFORMANCE_INSIGHT:': 'performance_insight',
        }
        
        current_section = None
        current_content = []
        
        for line in response.split('\n'):
            line_stripped = line.strip()
            
            # Check if this is a section header
            found_section = False
            for header, attr in sections.items():
                if line_stripped.startswith(header):
                    # Save previous section
                    if current_section:
                        setattr(briefing, current_section, '\n'.join(current_content).strip())
                    current_section = attr
                    # Get content after header on same line
                    content_after = line_stripped[len(header):].strip()
                    current_content = [content_after] if content_after else []
                    found_section = True
                    break
            
            if not found_section and current_section:
                current_content.append(line)
            
            # Parse action items
            if line_stripped.startswith('ACTION_ITEMS:'):
                current_section = None
            elif current_section is None and line_stripped.startswith('- '):
                if 'WARNING' not in response[response.find(line_stripped)-20:response.find(line_stripped)]:
                    briefing.action_items.append(line_stripped[2:])
            
            # Parse warnings
            if 'WARNINGS:' in line_stripped:
                current_section = 'warnings_section'
            elif current_section == 'warnings_section' and line_stripped.startswith('- '):
                briefing.warnings.append(line_stripped[2:])
            elif current_section == 'warnings_section' and line_stripped and not line_stripped.startswith('-'):
                if any(line_stripped.startswith(h) for h in sections.keys()):
                    current_section = None
        
        # Save last section
        if current_section and current_section not in ['warnings_section']:
            setattr(briefing, current_section, '\n'.join(current_content).strip())
        
        # Set market summary from outlook
        briefing.market_summary = briefing.market_outlook[:200] if briefing.market_outlook else ""
        
        return briefing
    
    def get_quick_advice(self, question: str, context: Dict) -> str:
        """Get quick advice on a specific question"""
        if not self.api_key:
            return "AI advisor not connected. Add ANTHROPIC_API_KEY to .env"
        
        prompt = f"""You are an expert options trading advisor. Answer this specific question concisely.

CONTEXT:
- Market: {context.get('market_regime', 'Unknown')}
- VIX: {context.get('vix', 'N/A')}
- Open Positions: {context.get('position_count', 0)}
- Capital at Risk: {context.get('capital_at_risk', 0):.1f}%

QUESTION: {question}

Give a direct, actionable answer in 2-3 sentences."""

        try:
            response = self._call_claude(prompt)
            return response
        except Exception as e:
            return f"Error: {str(e)}"
    
    def analyze_trade_idea(self, symbol: str, direction: str, 
                          stock_analysis: Dict, market_data: Dict) -> Dict:
        """Get AI analysis of a specific trade idea"""
        if not self.api_key:
            return {"error": "AI not connected"}
        
        prompt = f"""Analyze this trade idea and give your recommendation.

TRADE IDEA:
- Symbol: {symbol}
- Direction: {direction}
- Current Price: ${stock_analysis.get('price', 0):.2f}
- Technical Score: {stock_analysis.get('hot_score', 0):.0f}/100
- Setup Quality: {stock_analysis.get('setup_quality', 'N/A')}
- Trend: {stock_analysis.get('technicals', {}).get('trend_direction', 'N/A')}
- RSI: {stock_analysis.get('technicals', {}).get('rsi', 50):.0f}
- Volume: {stock_analysis.get('technicals', {}).get('volume_ratio', 1):.1f}x average

MARKET CONTEXT:
- Regime: {market_data.get('regime', 'Unknown')}
- VIX: {market_data.get('vix', {}).get('level', 'N/A')}
- Market Bias: {market_data.get('strategy', {}).get('bias', 'N/A')}

Respond in this format:
VERDICT: [TAKE THE TRADE / WAIT / PASS]
CONFIDENCE: [HIGH / MEDIUM / LOW]
REASONING: [2-3 sentences why]
IF_TAKING: [Specific entry, target, stop recommendations]
RISK: [Key risk to watch]"""

        try:
            response = self._call_claude(prompt)
            
            # Parse response
            result = {
                'verdict': '',
                'confidence': '',
                'reasoning': '',
                'if_taking': '',
                'risk': '',
                'raw': response
            }
            
            for line in response.split('\n'):
                if line.startswith('VERDICT:'):
                    result['verdict'] = line.replace('VERDICT:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    result['confidence'] = line.replace('CONFIDENCE:', '').strip()
                elif line.startswith('REASONING:'):
                    result['reasoning'] = line.replace('REASONING:', '').strip()
                elif line.startswith('IF_TAKING:'):
                    result['if_taking'] = line.replace('IF_TAKING:', '').strip()
                elif line.startswith('RISK:'):
                    result['risk'] = line.replace('RISK:', '').strip()
            
            return result
        except Exception as e:
            return {"error": str(e)}


def get_advisor_briefing_dict(advisor: AITradingAdvisor,
                               market: Dict, positions: Dict, risk: Dict,
                               hot_list: List, journal: Dict, watchlist: List) -> Dict:
    """Get advisor briefing as dictionary for web interface"""
    briefing = advisor.get_briefing(market, positions, risk, hot_list, journal, watchlist)
    
    return {
        'headline': briefing.headline,
        'market_summary': briefing.market_summary,
        'market_outlook': briefing.market_outlook,
        'position_review': briefing.position_review,
        'risk_assessment': briefing.risk_assessment,
        'opportunities': briefing.opportunities,
        'action_items': briefing.action_items,
        'warnings': briefing.warnings,
        'what_to_do_today': briefing.what_to_do_today,
        'what_to_avoid': briefing.what_to_avoid,
        'performance_insight': briefing.performance_insight,
        'generated_at': briefing.generated_at,
        'model_used': briefing.model_used,
        'has_content': bool(briefing.headline and 'Not Connected' not in briefing.headline),
    }
