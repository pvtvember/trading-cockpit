"""
AI Mentor Module
================
Uses Claude to provide:
- Trade review and lessons
- Pattern detection in your trading
- Coaching recommendations
- Real-time trade advice
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import requests

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')


# ============================================================================
# CLAUDE API INTERACTION
# ============================================================================

def call_claude(prompt: str, system_prompt: str = None, max_tokens: int = 1500) -> str:
    """Call Claude API with prompt"""
    if not ANTHROPIC_API_KEY:
        return "AI not available - add ANTHROPIC_API_KEY"
    
    try:
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            return f"API error: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

MENTOR_SYSTEM_PROMPT = """You are an expert options swing trader with 20+ years of experience. You've seen every market condition and made (and learned from) every mistake.

Your role is to be a mentor - direct, honest, and focused on what actually makes money. No fluff, no generic advice. Every word should help the trader improve.

Your trading philosophy:
- Trade WITH the trend (A-tier continuation and base breakouts)
- Buy options when IV is LOW (cheap premium)
- Target delta 0.50+ for swing trades
- 30-45 DTE for time to be right
- Let winners run, cut losers fast
- Position size based on conviction (A-tier: full size, B: 75%, C: 50%)

When reviewing trades, focus on:
1. Was the setup quality correct? (A/B/C tier)
2. Was the entry timing right? (Execution readiness)
3. Was position sizing appropriate?
4. Was the exit optimal? (Too early? Too late? Followed rules?)
5. What's the actionable lesson?

Be specific. Use numbers. Reference their actual data."""


TRADE_REVIEW_SYSTEM = """You are reviewing a completed trade. Analyze what went right, what went wrong, and extract a specific, actionable lesson.

Be direct and specific. Don't sugarcoat - if they made a mistake, tell them clearly. But also acknowledge what they did well.

End with ONE clear lesson they should remember."""


PATTERN_DETECTION_SYSTEM = """You are analyzing a trader's history to find patterns - both good habits that make money and bad habits that lose money.

Look for:
- Which setup types work best for them
- Which setup types they should avoid
- Entry timing patterns
- Exit behavior patterns
- Position sizing consistency
- Emotional/behavioral patterns

Be specific with numbers. If they're 80% on A-tier squeezes but 40% on C-tier reversals, tell them to stop taking C-tier trades."""


# ============================================================================
# TRADE REVIEW
# ============================================================================

def review_trade(trade_data: Dict) -> Dict:
    """
    Generate AI review for a completed trade
    
    Returns: {'review': str, 'lessons': str, 'grade': str}
    """
    # Build context
    context = f"""
TRADE DETAILS:
- Symbol: {trade_data.get('symbol')}
- Direction: {trade_data.get('direction')}
- Setup Type: {trade_data.get('setup_type')} ({trade_data.get('tier')}-TIER)
- Entry Date: {trade_data.get('entry_date')}
- Entry Price: ${trade_data.get('entry_price')}
- Entry Delta: {trade_data.get('entry_delta')}
- Entry IV: {trade_data.get('entry_iv')}%

- Exit Date: {trade_data.get('exit_date')}  
- Exit Price: ${trade_data.get('exit_price')}
- Exit Reason: {trade_data.get('exit_reason')}
- Hold Days: {trade_data.get('hold_days')}

RESULT:
- P&L: ${trade_data.get('pnl_dollars'):,.2f} ({trade_data.get('pnl_percent'):+.1f}%)
- Target Hit: {'Yes' if trade_data.get('target_hit') else 'No'}
- Stop Hit: {'Yes' if trade_data.get('stop_hit') else 'No'}

SCAN DATA AT ENTRY:
{json.dumps(trade_data.get('scan_data_entry', {}), indent=2)[:1000]}
"""

    prompt = f"""Review this trade and provide:

1. WHAT WENT RIGHT (be specific)
2. WHAT WENT WRONG (be specific)  
3. GRADE (A/B/C/D/F)
4. KEY LESSON (one sentence they should remember)

{context}

Keep your response concise but specific. Reference the actual numbers."""

    review = call_claude(prompt, TRADE_REVIEW_SYSTEM, 800)
    
    # Extract grade (simple heuristic)
    grade = 'B'
    if 'Grade: A' in review or 'GRADE: A' in review:
        grade = 'A'
    elif 'Grade: C' in review or 'GRADE: C' in review:
        grade = 'C'
    elif 'Grade: D' in review or 'GRADE: D' in review:
        grade = 'D'
    elif 'Grade: F' in review or 'GRADE: F' in review:
        grade = 'F'
    
    # Extract lesson (last paragraph typically)
    paragraphs = review.strip().split('\n\n')
    lesson = paragraphs[-1] if paragraphs else review[:200]
    
    return {
        'review': review,
        'lessons': lesson,
        'grade': grade
    }


# ============================================================================
# PATTERN ANALYSIS
# ============================================================================

def analyze_patterns(statistics: Dict, recent_trades: List[Dict]) -> Dict:
    """
    Analyze trading patterns and generate coaching advice
    
    Returns: {'strengths': list, 'weaknesses': list, 'recommendations': list, 'focus': str}
    """
    # Build context from statistics
    overall = statistics.get('overall', {})
    by_setup = statistics.get('by_setup', [])
    by_direction = statistics.get('by_direction', [])
    recent = statistics.get('recent_30d', {})
    
    context = f"""
OVERALL STATISTICS:
- Total Trades: {overall.get('total_trades', 0)}
- Win Rate: {overall.get('win_rate', 0):.1f}%
- Average Return: {overall.get('avg_return', 0):+.1f}%
- Total P&L: ${overall.get('total_pnl', 0):,.2f}
- Average Win: {overall.get('avg_win', 0):+.1f}%
- Average Loss: {overall.get('avg_loss', 0):.1f}%
- Average Hold Days: {overall.get('avg_hold_days', 0):.1f}

BY SETUP TYPE:
"""
    for setup in by_setup:
        context += f"- {setup.get('tier', '?')}-TIER {setup.get('setup_type', 'Unknown')}: {setup.get('trades', 0)} trades, {setup.get('win_rate', 0):.0f}% win rate, {setup.get('avg_return', 0):+.1f}% avg\n"

    context += f"""
BY DIRECTION:
"""
    for d in by_direction:
        context += f"- {d.get('direction', 'Unknown')}: {d.get('trades', 0)} trades, {d.get('win_rate', 0):.0f}% win rate, ${d.get('total_pnl', 0):,.2f}\n"

    context += f"""
LAST 30 DAYS:
- Trades: {recent.get('trades', 0)}
- Win Rate: {recent.get('win_rate', 0):.1f}%
- Average Return: {recent.get('avg_return', 0):+.1f}%
- P&L: ${recent.get('total_pnl', 0):,.2f}

RECENT TRADES:
"""
    for trade in recent_trades[:10]:
        context += f"- {trade.get('symbol')} {trade.get('direction')} {trade.get('setup_type')}: {trade.get('pnl_percent', 0):+.1f}%\n"

    prompt = f"""Analyze this trader's patterns and provide:

1. STRENGTHS (what they do well - be specific with numbers)
2. WEAKNESSES (what costs them money - be specific)
3. TOP 3 RECOMMENDATIONS (actionable, specific)
4. THIS MONTH'S FOCUS (one thing to work on)

{context}

Be direct. Use their actual numbers. If they should stop doing something, say it clearly."""

    analysis = call_claude(prompt, PATTERN_DETECTION_SYSTEM, 1000)
    
    # Parse into structured format (simplified)
    return {
        'full_analysis': analysis,
        'generated_at': datetime.now().isoformat()
    }


# ============================================================================
# REAL-TIME TRADE ADVICE
# ============================================================================

def get_entry_advice(scan_result: Dict, options_analysis: Dict = None) -> str:
    """
    Get AI advice on whether to enter a trade
    """
    context = f"""
SETUP FOUND:
- Symbol: {scan_result.get('symbol')}
- Category: {scan_result.get('category')}
- Setup: {scan_result.get('tier')}-TIER {scan_result.get('setup_type')}
- Direction: {scan_result.get('setup_direction')}
- Priority Score: {scan_result.get('priority_score')}/150
- Confluence Score: {scan_result.get('confluence_score')}/100

EXECUTION:
- Exec Readiness: {scan_result.get('exec_readiness')}/14 ({scan_result.get('exec_status')})
- Session: {scan_result.get('session_phase')}

ANALYSIS:
- RS vs SPY: {scan_result.get('relative_strength', 0):+.1f}% ({scan_result.get('rs_rating')})
- IV: {scan_result.get('iv_percentile', 50):.0f}% ({scan_result.get('iv_rating')})
- RSI: {scan_result.get('rsi', 50):.1f}
- Squeeze: {'YES (' + str(scan_result.get('squeeze_bars', 0)) + ' bars)' if scan_result.get('squeeze_on') else 'No'}
- MTF: {scan_result.get('mtf_alignment')}

WARNINGS:
{', '.join(scan_result.get('warnings', [])) or 'None'}
"""

    if options_analysis:
        context += f"""
RECOMMENDED CONTRACT:
- Strike: ${options_analysis.get('recommended_contract', {}).get('strike')}
- Expiration: {options_analysis.get('recommended_contract', {}).get('expiration')} ({options_analysis.get('recommended_contract', {}).get('dte')} DTE)
- Delta: {options_analysis.get('recommended_contract', {}).get('delta')}
- Premium: ${options_analysis.get('recommended_contract', {}).get('mid')}

POSITION:
- Size: {options_analysis.get('num_contracts')} contracts (${options_analysis.get('total_premium'):,.2f})
- Max Loss: ${options_analysis.get('max_loss'):,.2f}
- Target: ${options_analysis.get('target_price'):.2f} (+{options_analysis.get('target_pct'):.0f}%)
- Stop: ${options_analysis.get('stop_price'):.2f} ({options_analysis.get('stop_pct'):.0f}%)
- R:R: {options_analysis.get('risk_reward'):.1f}:1

IV CONTEXT:
- IV Percentile: {options_analysis.get('iv_percentile'):.0f}%
- Expected Move (30d): ${options_analysis.get('expected_move_30d'):.2f} ({options_analysis.get('expected_move_pct'):.1f}%)
- Theta Cost (7d): ${options_analysis.get('theta_cost_7d'):.2f} ({options_analysis.get('theta_pct_7d'):.1f}% of position)
- Liquidity: {options_analysis.get('liquidity_rating')}
"""

    prompt = f"""Based on this setup, should the trader enter? 

Provide a DECISION (ENTER / WAIT / SKIP) and brief explanation (2-3 sentences max).

If ENTER, mention the key factor that makes it good.
If WAIT, say what should change before entry.
If SKIP, say why this isn't worth the risk.

{context}"""

    return call_claude(prompt, MENTOR_SYSTEM_PROMPT, 300)


def get_exit_advice(position_data: Dict, current_scan: Dict = None) -> str:
    """
    Get AI advice on whether to exit a position
    """
    context = f"""
CURRENT POSITION:
- Symbol: {position_data.get('symbol')}
- Direction: {position_data.get('direction')}
- Setup: {position_data.get('tier')}-TIER {position_data.get('setup_type')}
- Entry Price: ${position_data.get('entry_price')}
- Current Price: ${position_data.get('current_price')}
- P&L: {position_data.get('pnl_percent', 0):+.1f}%
- Days Held: {position_data.get('days_held', 0)}
- DTE Remaining: {position_data.get('dte_remaining', 30)}

TARGETS:
- Target Price: ${position_data.get('target_price')} ({position_data.get('target_pct', 100):+.0f}%)
- Stop Price: ${position_data.get('stop_price')} ({position_data.get('stop_pct', -50):.0f}%)
"""

    if current_scan:
        context += f"""
CURRENT SCAN:
- Setup Still Valid: {current_scan.get('setup_type') is not None}
- Current Confluence: {current_scan.get('confluence_score', 0)}/100
- Warnings: {', '.join(current_scan.get('warnings', [])) or 'None'}
- RSI: {current_scan.get('rsi', 50):.1f}
"""

    prompt = f"""Based on this position, should the trader exit?

Provide a DECISION (HOLD / TAKE PROFITS / CLOSE) and brief explanation (2-3 sentences max).

{context}"""

    return call_claude(prompt, MENTOR_SYSTEM_PROMPT, 300)


# ============================================================================
# DAILY BRIEFING
# ============================================================================

def generate_daily_briefing(scan_results: List[Dict], statistics: Dict, 
                            positions: List[Dict]) -> str:
    """
    Generate morning briefing with AI insights
    """
    # Summarize scan results
    ready_now = [r for r in scan_results if r.get('category') == 'READY_NOW']
    setting_up = [r for r in scan_results if r.get('category') == 'SETTING_UP']
    
    # Current positions summary
    positions_summary = ""
    total_pnl = 0
    for p in positions:
        pnl = p.get('pnl_percent', 0)
        total_pnl += pnl
        positions_summary += f"- {p.get('symbol')} {p.get('direction')}: {pnl:+.1f}%\n"
    
    context = f"""
TODAY'S SCAN:
- Ready Now: {len(ready_now)} setups
- Setting Up: {len(setting_up)} setups

TOP OPPORTUNITIES:
"""
    for r in ready_now[:3]:
        context += f"- {r.get('symbol')}: {r.get('tier')}-TIER {r.get('setup_type')} | Exec: {r.get('exec_status')} | Confluence: {r.get('confluence_score')}\n"

    context += f"""
CURRENT POSITIONS ({len(positions)} open):
{positions_summary if positions_summary else 'No open positions'}
Total Unrealized P&L: {total_pnl:+.1f}%

YOUR STATS (Last 30 Days):
- Win Rate: {statistics.get('recent_30d', {}).get('win_rate', 0):.0f}%
- P&L: ${statistics.get('recent_30d', {}).get('total_pnl', 0):,.2f}
"""

    prompt = f"""Generate a brief morning briefing for this trader.

Include:
1. Market stance for today (1 sentence)
2. Top action item (1 specific thing to do)
3. What to avoid today (1 specific warning)
4. Position management note (if they have positions)

Keep it SHORT - this is a quick morning read.

{context}"""

    return call_claude(prompt, MENTOR_SYSTEM_PROMPT, 400)
