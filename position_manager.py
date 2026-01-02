"""
Position Manager Module
=======================
Active trade management:
- Real-time position health scoring
- Stop management (initial, breakeven, trailing)
- Profit target zones with scaled exits
- Greeks tracking and decay analysis
- AI hold time estimation
- Exit quality scoring
"""

import os
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from analysis_engine import analyze_stock, OHLCV, AnalysisResult
from options_analytics import get_underlying_quote, calculate_bs_greeks

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class StopManagement:
    """Stop loss management data"""
    initial_stop: float
    initial_stop_pct: float
    current_stop: float
    current_stop_pct: float
    breakeven_price: float
    breakeven_triggered: bool
    trailing_stop: float
    trailing_stop_pct: float
    highest_price: float
    stop_recommendation: str
    stop_action: str  # HOLD, MOVE_TO_BE, TRAIL, EXIT

@dataclass
class ProfitTargets:
    """Scaled profit target zones"""
    target_1_price: float
    target_1_pct: float
    target_1_underlying: float
    target_1_hit: bool
    target_1_contracts: int  # How many to sell at T1
    
    target_2_price: float
    target_2_pct: float
    target_2_underlying: float
    target_2_hit: bool
    target_2_contracts: int
    
    target_3_price: float
    target_3_pct: float
    target_3_underlying: float
    target_3_hit: bool
    target_3_contracts: int  # Runner

@dataclass
class GreeksSnapshot:
    """Current Greeks state"""
    delta: float
    delta_entry: float
    delta_change: float
    gamma: float
    theta: float
    theta_daily_cost: float
    theta_total_burned: float
    theta_burn_pct: float
    vega: float
    iv_current: float
    iv_entry: float
    iv_change: float

@dataclass 
class TimeAnalysis:
    """Time-based analysis"""
    days_held: int
    ai_hold_estimate: int  # Estimated total hold days
    days_remaining: int
    dte: int
    theta_zone: str  # SAFE (>21), CAUTION (14-21), DANGER (<14)
    time_recommendation: str

@dataclass
class TradeHealth:
    """Overall trade health metrics"""
    momentum_score: int  # 0-100
    momentum_label: str
    trend_score: int
    trend_label: str
    rs_score: int
    rs_vs_spy: float
    setup_still_valid: bool
    iv_regime: str  # EXPANDING, STABLE, CONTRACTING
    liquidity_score: int
    liquidity_label: str
    overall_health: int  # 0-100
    health_label: str  # STRONG, GOOD, CAUTION, WEAK

@dataclass
class PositionAnalysis:
    """Complete position analysis"""
    # Basic info
    symbol: str
    direction: str
    strike: float
    expiration: str
    contracts: int
    contracts_remaining: int
    
    # P&L
    entry_price: float
    current_price: float
    high_price: float
    pnl_dollars: float
    pnl_percent: float
    
    # Underlying
    underlying_price: float
    underlying_entry: float
    underlying_change_pct: float
    
    # Components
    stops: StopManagement
    targets: ProfitTargets
    greeks: GreeksSnapshot
    time: TimeAnalysis
    health: TradeHealth
    
    # Partial exits
    partial_exits: List[Dict]
    
    # AI Recommendation
    recommendation: str  # HOLD, TAKE_PARTIAL, MOVE_STOP, EXIT
    recommendation_reason: str
    next_action: str
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'strike': self.strike,
            'expiration': self.expiration,
            'contracts': self.contracts,
            'contracts_remaining': self.contracts_remaining,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'high_price': self.high_price,
            'pnl_dollars': self.pnl_dollars,
            'pnl_percent': self.pnl_percent,
            'underlying_price': self.underlying_price,
            'underlying_entry': self.underlying_entry,
            'underlying_change_pct': self.underlying_change_pct,
            'stops': {
                'initial_stop': self.stops.initial_stop,
                'initial_stop_pct': self.stops.initial_stop_pct,
                'current_stop': self.stops.current_stop,
                'current_stop_pct': self.stops.current_stop_pct,
                'breakeven_price': self.stops.breakeven_price,
                'breakeven_triggered': self.stops.breakeven_triggered,
                'trailing_stop': self.stops.trailing_stop,
                'trailing_stop_pct': self.stops.trailing_stop_pct,
                'highest_price': self.stops.highest_price,
                'stop_recommendation': self.stops.stop_recommendation,
                'stop_action': self.stops.stop_action
            },
            'targets': {
                'target_1': {
                    'price': self.targets.target_1_price,
                    'pct': self.targets.target_1_pct,
                    'underlying': self.targets.target_1_underlying,
                    'hit': self.targets.target_1_hit,
                    'contracts': self.targets.target_1_contracts
                },
                'target_2': {
                    'price': self.targets.target_2_price,
                    'pct': self.targets.target_2_pct,
                    'underlying': self.targets.target_2_underlying,
                    'hit': self.targets.target_2_hit,
                    'contracts': self.targets.target_2_contracts
                },
                'target_3': {
                    'price': self.targets.target_3_price,
                    'pct': self.targets.target_3_pct,
                    'underlying': self.targets.target_3_underlying,
                    'hit': self.targets.target_3_hit,
                    'contracts': self.targets.target_3_contracts
                }
            },
            'greeks': {
                'delta': self.greeks.delta,
                'delta_entry': self.greeks.delta_entry,
                'delta_change': self.greeks.delta_change,
                'gamma': self.greeks.gamma,
                'theta': self.greeks.theta,
                'theta_daily_cost': self.greeks.theta_daily_cost,
                'theta_total_burned': self.greeks.theta_total_burned,
                'theta_burn_pct': self.greeks.theta_burn_pct,
                'vega': self.greeks.vega,
                'iv_current': self.greeks.iv_current,
                'iv_entry': self.greeks.iv_entry,
                'iv_change': self.greeks.iv_change
            },
            'time': {
                'days_held': self.time.days_held,
                'ai_hold_estimate': self.time.ai_hold_estimate,
                'days_remaining': self.time.days_remaining,
                'dte': self.time.dte,
                'theta_zone': self.time.theta_zone,
                'time_recommendation': self.time.time_recommendation
            },
            'health': {
                'momentum_score': self.health.momentum_score,
                'momentum_label': self.health.momentum_label,
                'trend_score': self.health.trend_score,
                'trend_label': self.health.trend_label,
                'rs_score': self.health.rs_score,
                'rs_vs_spy': self.health.rs_vs_spy,
                'setup_still_valid': self.health.setup_still_valid,
                'iv_regime': self.health.iv_regime,
                'liquidity_score': self.health.liquidity_score,
                'liquidity_label': self.health.liquidity_label,
                'overall_health': self.health.overall_health,
                'health_label': self.health.health_label
            },
            'partial_exits': self.partial_exits,
            'recommendation': self.recommendation,
            'recommendation_reason': self.recommendation_reason,
            'next_action': self.next_action,
            'warnings': self.warnings
        }


# ============================================================================
# STOP MANAGEMENT
# ============================================================================

def calculate_stops(entry_price: float, current_price: float, high_price: float,
                   pnl_percent: float, tier: str = 'B') -> StopManagement:
    """
    Calculate stop management levels
    
    Stop Strategy:
    - Initial: -50% from entry
    - Breakeven: Move to entry price when +25-30%
    - Trailing: 15% below highest price once profitable
    """
    # Initial stop (-50%)
    initial_stop = entry_price * 0.50
    initial_stop_pct = -50.0
    
    # Track highest price
    highest = max(high_price, current_price)
    
    # Breakeven price
    breakeven = entry_price
    breakeven_triggered = pnl_percent >= 25
    
    # Trailing stop (15% below high)
    trailing_pct = 0.15
    trailing_stop = highest * (1 - trailing_pct) if pnl_percent > 0 else initial_stop
    trailing_stop_pct = ((trailing_stop - entry_price) / entry_price) * 100
    
    # Determine current stop and recommendation
    if pnl_percent < 0:
        # Losing - use initial stop
        current_stop = initial_stop
        current_stop_pct = initial_stop_pct
        stop_action = 'HOLD'
        if pnl_percent <= -40:
            stop_recommendation = "Approaching stop. Review thesis - exit if setup invalidated."
        else:
            stop_recommendation = f"Initial stop at ${initial_stop:.2f} (-50%). Hold unless setup breaks."
    
    elif pnl_percent < 25:
        # Small profit - still on initial stop but watching
        current_stop = initial_stop
        current_stop_pct = initial_stop_pct
        stop_action = 'HOLD'
        stop_recommendation = f"Profitable but not enough to move stop. Initial stop ${initial_stop:.2f}."
    
    elif pnl_percent < 50:
        # Good profit - move to breakeven
        current_stop = breakeven
        current_stop_pct = 0
        stop_action = 'MOVE_TO_BE'
        stop_recommendation = f"MOVE STOP TO BREAKEVEN (${breakeven:.2f}) - Lock in risk-free trade."
    
    else:
        # Strong profit - trail stop
        current_stop = trailing_stop
        current_stop_pct = trailing_stop_pct
        stop_action = 'TRAIL'
        stop_recommendation = f"TRAIL STOP to ${trailing_stop:.2f} ({trailing_stop_pct:+.0f}%) - 15% below high."
    
    return StopManagement(
        initial_stop=initial_stop,
        initial_stop_pct=initial_stop_pct,
        current_stop=current_stop,
        current_stop_pct=current_stop_pct,
        breakeven_price=breakeven,
        breakeven_triggered=breakeven_triggered,
        trailing_stop=trailing_stop,
        trailing_stop_pct=trailing_stop_pct,
        highest_price=highest,
        stop_recommendation=stop_recommendation,
        stop_action=stop_action
    )


# ============================================================================
# PROFIT TARGETS
# ============================================================================

def calculate_targets(entry_price: float, current_price: float, 
                     contracts: int, underlying_entry: float,
                     underlying_current: float, delta: float = 0.50) -> ProfitTargets:
    """
    Calculate scaled profit targets
    
    Target Strategy:
    - T1: +50% - Sell 1/3
    - T2: +100% - Sell 1/3
    - T3: +150% - Runner (remaining 1/3)
    """
    # Contract allocation
    t1_contracts = contracts // 3
    t2_contracts = contracts // 3
    t3_contracts = contracts - t1_contracts - t2_contracts  # Remainder as runner
    
    # Option price targets
    t1_price = entry_price * 1.50  # +50%
    t2_price = entry_price * 2.00  # +100%
    t3_price = entry_price * 2.50  # +150%
    
    # Underlying targets (approximation using delta)
    # Option move ≈ Underlying move × Delta
    if delta > 0:
        t1_underlying_move = (t1_price - entry_price) / delta
        t2_underlying_move = (t2_price - entry_price) / delta
        t3_underlying_move = (t3_price - entry_price) / delta
    else:
        t1_underlying_move = underlying_entry * 0.05
        t2_underlying_move = underlying_entry * 0.08
        t3_underlying_move = underlying_entry * 0.12
    
    t1_underlying = underlying_entry + t1_underlying_move
    t2_underlying = underlying_entry + t2_underlying_move
    t3_underlying = underlying_entry + t3_underlying_move
    
    # Check if targets hit
    t1_hit = current_price >= t1_price
    t2_hit = current_price >= t2_price
    t3_hit = current_price >= t3_price
    
    return ProfitTargets(
        target_1_price=t1_price,
        target_1_pct=50.0,
        target_1_underlying=t1_underlying,
        target_1_hit=t1_hit,
        target_1_contracts=t1_contracts,
        target_2_price=t2_price,
        target_2_pct=100.0,
        target_2_underlying=t2_underlying,
        target_2_hit=t2_hit,
        target_2_contracts=t2_contracts,
        target_3_price=t3_price,
        target_3_pct=150.0,
        target_3_underlying=t3_underlying,
        target_3_hit=t3_hit,
        target_3_contracts=t3_contracts
    )


# ============================================================================
# GREEKS ANALYSIS
# ============================================================================

def analyze_greeks(entry_delta: float, entry_iv: float, current_price: float,
                  entry_price: float, underlying_price: float, strike: float,
                  dte: int, contracts: int, days_held: int,
                  direction: str = 'call') -> GreeksSnapshot:
    """Analyze Greeks and decay"""
    
    # Calculate current Greeks
    T = dte / 365 if dte > 0 else 0.01
    iv = entry_iv / 100 if entry_iv else 0.35
    
    greeks = calculate_bs_greeks(
        underlying_price, strike, T, 0.05, iv, direction
    )
    
    delta = greeks['delta']
    gamma = greeks['gamma']
    theta = greeks['theta']
    vega = greeks['vega']
    
    # Delta change from entry
    delta_change = delta - (entry_delta or 0.50)
    
    # Theta cost analysis
    theta_daily = abs(theta) * contracts * 100
    theta_burned = theta_daily * days_held
    theta_burn_pct = (theta_burned / (entry_price * contracts * 100)) * 100 if entry_price > 0 else 0
    
    # IV change (simplified - would need actual IV tracking)
    iv_current = iv * 100
    iv_change = 0  # Would track actual IV changes
    
    return GreeksSnapshot(
        delta=delta,
        delta_entry=entry_delta or 0.50,
        delta_change=delta_change,
        gamma=gamma,
        theta=theta,
        theta_daily_cost=theta_daily,
        theta_total_burned=theta_burned,
        theta_burn_pct=theta_burn_pct,
        vega=vega,
        iv_current=iv_current,
        iv_entry=entry_iv or 35,
        iv_change=iv_change
    )


# ============================================================================
# TIME ANALYSIS
# ============================================================================

def analyze_time(entry_date: datetime, dte: int, tier: str = 'B',
                setup_type: str = None, pnl_percent: float = 0) -> TimeAnalysis:
    """Analyze time factors and estimate hold duration"""
    
    # Days held
    if entry_date:
        days_held = (datetime.now() - entry_date).days
    else:
        days_held = 0
    
    # AI hold estimate based on setup type and tier
    hold_estimates = {
        'A': {'CONTINUATION': 7, 'BASE_BREAKOUT': 10, 'SQUEEZE': 5},
        'B': {'SQUEEZE': 7, 'BREAKOUT': 5, 'CONTINUATION': 8},
        'C': {'REVERSAL': 3, 'DIVERGENCE': 5}
    }
    
    default_hold = 7
    if tier in hold_estimates and setup_type in hold_estimates[tier]:
        ai_hold = hold_estimates[tier][setup_type]
    else:
        ai_hold = default_hold
    
    # Adjust based on P&L
    if pnl_percent >= 50:
        ai_hold = min(ai_hold, days_held + 2)  # Close to exit
    elif pnl_percent < -25:
        ai_hold = min(ai_hold, days_held + 1)  # May need to exit soon
    
    days_remaining = max(0, ai_hold - days_held)
    
    # Theta zone
    if dte > 21:
        theta_zone = 'SAFE'
        time_rec = "Time decay manageable. No urgency from theta."
    elif dte > 14:
        theta_zone = 'CAUTION'
        time_rec = "Theta accelerating. Consider exit within 1 week."
    else:
        theta_zone = 'DANGER'
        time_rec = "HIGH THETA DECAY. Exit soon or roll position."
    
    return TimeAnalysis(
        days_held=days_held,
        ai_hold_estimate=ai_hold,
        days_remaining=days_remaining,
        dte=dte,
        theta_zone=theta_zone,
        time_recommendation=time_rec
    )


# ============================================================================
# TRADE HEALTH
# ============================================================================

def analyze_health(analysis: AnalysisResult, entry_setup: str,
                  iv_entry: float, iv_current: float) -> TradeHealth:
    """Analyze overall trade health"""
    
    # Momentum score
    if analysis:
        mom_score = analysis.momentum_quality
        if analysis.technical_data.get('cvd_rising'):
            mom_score += 20
        mom_score = min(100, mom_score)
    else:
        mom_score = 50
    
    if mom_score >= 70:
        mom_label = 'STRONG'
    elif mom_score >= 50:
        mom_label = 'MODERATE'
    elif mom_score >= 30:
        mom_label = 'WEAK'
    else:
        mom_label = 'FADING'
    
    # Trend score
    trend_score = 50
    if analysis:
        if analysis.technical_data.get('above_vwap'):
            trend_score += 20
        if analysis.rsi > 50:
            trend_score += 15
        if analysis.mtf_alignment == 'ALL BULLISH':
            trend_score += 15
    
    if trend_score >= 70:
        trend_label = 'BULLISH'
    elif trend_score >= 50:
        trend_label = 'NEUTRAL'
    else:
        trend_label = 'BEARISH'
    
    # RS score
    rs_vs_spy = analysis.relative_strength if analysis else 0
    rs_score = 50 + int(rs_vs_spy * 10)
    rs_score = max(0, min(100, rs_score))
    
    # Setup still valid
    setup_valid = True
    if analysis:
        if analysis.setup_type == entry_setup:
            setup_valid = True
        elif analysis.setup_type is not None:
            setup_valid = True  # Different setup but still has one
        else:
            setup_valid = analysis.confluence_score >= 40
    
    # IV regime
    iv_change = (iv_current - iv_entry) if iv_entry else 0
    if iv_change > 5:
        iv_regime = 'EXPANDING'
    elif iv_change < -5:
        iv_regime = 'CONTRACTING'
    else:
        iv_regime = 'STABLE'
    
    # Liquidity (simplified)
    liq_score = 70  # Would need actual bid/ask data
    liq_label = 'GOOD'
    
    # Overall health
    overall = (mom_score * 0.3 + trend_score * 0.3 + rs_score * 0.2 + 
               (100 if setup_valid else 40) * 0.2)
    overall = int(overall)
    
    if overall >= 75:
        health_label = 'STRONG'
    elif overall >= 55:
        health_label = 'GOOD'
    elif overall >= 40:
        health_label = 'CAUTION'
    else:
        health_label = 'WEAK'
    
    return TradeHealth(
        momentum_score=mom_score,
        momentum_label=mom_label,
        trend_score=trend_score,
        trend_label=trend_label,
        rs_score=rs_score,
        rs_vs_spy=rs_vs_spy,
        setup_still_valid=setup_valid,
        iv_regime=iv_regime,
        liquidity_score=liq_score,
        liquidity_label=liq_label,
        overall_health=overall,
        health_label=health_label
    )


# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================

def generate_recommendation(pnl_percent: float, stops: StopManagement,
                           targets: ProfitTargets, health: TradeHealth,
                           time: TimeAnalysis, warnings: List[str]) -> Tuple[str, str, str]:
    """
    Generate trade recommendation
    
    Returns: (recommendation, reason, next_action)
    """
    # Check for exit signals
    if health.overall_health < 40 and pnl_percent < 10:
        return ('EXIT', 
                'Setup deteriorating and minimal profit. Cut losses.',
                'Close position at market.')
    
    if time.theta_zone == 'DANGER' and pnl_percent < 30:
        return ('EXIT',
                'High theta decay zone with insufficient profit.',
                'Close or roll to later expiration.')
    
    # Check for earnings warning
    earnings_warning = any('EARNINGS' in w for w in warnings)
    if earnings_warning and time.days_remaining <= 2:
        return ('EXIT',
                'Earnings imminent. Exit to avoid IV crush.',
                'Close position before earnings announcement.')
    
    # Check targets
    if targets.target_1_hit and not targets.target_2_hit:
        return ('TAKE_PARTIAL',
                f'Target 1 (+50%) reached.',
                f'Sell {targets.target_1_contracts} contracts, trail stop to {stops.trailing_stop:.2f}.')
    
    if targets.target_2_hit and not targets.target_3_hit:
        return ('TAKE_PARTIAL',
                'Target 2 (+100%) reached.',
                f'Sell {targets.target_2_contracts} contracts, let runner ride.')
    
    if targets.target_3_hit:
        return ('EXIT',
                'All targets hit. Excellent trade!',
                'Close remaining position, book profits.')
    
    # Check stop management
    if stops.stop_action == 'MOVE_TO_BE' and pnl_percent >= 25:
        return ('MOVE_STOP',
                f'Up {pnl_percent:.0f}%. Time to eliminate risk.',
                f'Move stop to breakeven (${stops.breakeven_price:.2f}).')
    
    if stops.stop_action == 'TRAIL' and pnl_percent >= 50:
        return ('MOVE_STOP',
                f'Strong profit ({pnl_percent:.0f}%). Trail to lock gains.',
                f'Trail stop to ${stops.trailing_stop:.2f} (15% below high).')
    
    # Default - hold
    if health.health_label in ['STRONG', 'GOOD']:
        return ('HOLD',
                'Trade healthy. Thesis intact.',
                'Monitor for target or stop triggers.')
    else:
        return ('HOLD',
                'Trade intact but showing weakness.',
                'Watch closely. Tighten stop if deterioration continues.')


# ============================================================================
# MAIN ANALYSIS FUNCTION  
# ============================================================================

def analyze_position(position: Dict, bars: List[OHLCV] = None,
                    spy_bars: List[OHLCV] = None) -> PositionAnalysis:
    """
    Complete position analysis
    
    Parameters:
    - position: Position data from database
    - bars: OHLCV data for underlying (optional, will fetch if not provided)
    - spy_bars: SPY bars for relative strength
    """
    from scanner import fetch_bars, fetch_spy_bars
    
    symbol = position.get('symbol', '')
    direction = position.get('direction', 'CALL')
    strike = float(position.get('strike', 0))
    expiration = position.get('expiration', '')
    contracts = int(position.get('contracts', 1))
    entry_price = float(position.get('entry_price', 0))
    entry_delta = float(position.get('entry_delta', 0) or 0.50)
    entry_iv = float(position.get('entry_iv', 0) or 35)
    entry_underlying = float(position.get('entry_underlying', 0))
    setup_type = position.get('setup_type', '')
    tier = position.get('tier', 'B')
    
    # Parse entry date
    entry_date_raw = position.get('entry_date')
    if isinstance(entry_date_raw, str):
        try:
            entry_date = datetime.fromisoformat(entry_date_raw.replace('Z', '+00:00'))
        except:
            entry_date = datetime.now() - timedelta(days=3)
    elif isinstance(entry_date_raw, datetime):
        entry_date = entry_date_raw
    else:
        entry_date = datetime.now() - timedelta(days=3)
    
    # Get current underlying price
    quote = get_underlying_quote(symbol)
    underlying_price = quote.get('price', entry_underlying)
    
    if underlying_price == 0:
        underlying_price = entry_underlying or 100
    
    # Calculate DTE
    try:
        if isinstance(expiration, str):
            exp_date = datetime.strptime(expiration[:10], '%Y-%m-%d')
        else:
            exp_date = expiration
        dte = (exp_date - datetime.now()).days
    except:
        dte = 30
    
    # Estimate current option price (simplified - would use real quote in production)
    # Using delta approximation: option_change ≈ underlying_change × delta
    underlying_change = underlying_price - entry_underlying if entry_underlying else 0
    option_change_estimate = underlying_change * entry_delta
    current_price = max(0.01, entry_price + option_change_estimate)
    
    # Track high price (would be stored in DB in production)
    high_price = position.get('high_price', current_price)
    if current_price > high_price:
        high_price = current_price
    
    # P&L
    pnl_dollars = (current_price - entry_price) * contracts * 100
    pnl_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
    
    # Underlying change
    underlying_change_pct = ((underlying_price - entry_underlying) / entry_underlying * 100) if entry_underlying else 0
    
    # Get technical analysis
    if bars is None:
        bars = fetch_bars(symbol, 60)
    if spy_bars is None:
        spy_bars = fetch_spy_bars(60)
    
    analysis = None
    if bars:
        analysis = analyze_stock(symbol, bars, spy_bars)
    
    # Calculate all components
    stops = calculate_stops(entry_price, current_price, high_price, pnl_percent, tier)
    targets = calculate_targets(entry_price, current_price, contracts, 
                               entry_underlying, underlying_price, entry_delta)
    greeks = analyze_greeks(entry_delta, entry_iv, current_price, entry_price,
                           underlying_price, strike, dte, contracts,
                           (datetime.now() - entry_date).days, direction.lower())
    time_analysis = analyze_time(entry_date, dte, tier, setup_type, pnl_percent)
    health = analyze_health(analysis, setup_type, entry_iv, greeks.iv_current)
    
    # Gather warnings
    warnings = []
    if analysis and analysis.warnings:
        warnings.extend(analysis.warnings)
    if time_analysis.theta_zone == 'DANGER':
        warnings.append(f"THETA DANGER: Only {dte} DTE remaining")
    if health.health_label == 'WEAK':
        warnings.append("WEAK: Trade health deteriorating")
    
    # Get partial exits (would come from DB)
    partial_exits = position.get('partial_exits', [])
    contracts_remaining = contracts - sum(p.get('contracts', 0) for p in partial_exits)
    
    # Generate recommendation
    rec, reason, action = generate_recommendation(
        pnl_percent, stops, targets, health, time_analysis, warnings
    )
    
    return PositionAnalysis(
        symbol=symbol,
        direction=direction,
        strike=strike,
        expiration=expiration,
        contracts=contracts,
        contracts_remaining=contracts_remaining,
        entry_price=entry_price,
        current_price=current_price,
        high_price=high_price,
        pnl_dollars=pnl_dollars,
        pnl_percent=pnl_percent,
        underlying_price=underlying_price,
        underlying_entry=entry_underlying,
        underlying_change_pct=underlying_change_pct,
        stops=stops,
        targets=targets,
        greeks=greeks,
        time=time_analysis,
        health=health,
        partial_exits=partial_exits,
        recommendation=rec,
        recommendation_reason=reason,
        next_action=action,
        warnings=warnings
    )


# ============================================================================
# PORTFOLIO ANALYSIS
# ============================================================================

def analyze_portfolio(positions: List[Dict]) -> Dict:
    """
    Analyze entire portfolio
    
    Returns portfolio-level metrics and heat map
    """
    if not positions:
        return {
            'total_positions': 0,
            'total_value': 0,
            'total_pnl': 0,
            'total_delta': 0,
            'daily_theta': 0,
            'sector_exposure': {},
            'correlation_warning': False,
            'positions_analysis': []
        }
    
    analyses = []
    total_pnl = 0
    total_delta = 0
    daily_theta = 0
    sector_counts = {}
    
    for pos in positions:
        analysis = analyze_position(pos)
        analyses.append(analysis)
        
        total_pnl += analysis.pnl_dollars
        total_delta += analysis.greeks.delta * analysis.contracts_remaining * 100
        daily_theta += analysis.greeks.theta_daily_cost
        
        # Track sector (simplified)
        sector = pos.get('sector', 'Other')
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    # Check correlation warning
    max_sector = max(sector_counts.values()) if sector_counts else 0
    correlation_warning = max_sector >= 3 or (max_sector / len(positions)) > 0.6
    
    # Build heat map
    heat_map = []
    for a in analyses:
        heat_map.append({
            'symbol': a.symbol,
            'direction': a.direction,
            'pnl_percent': a.pnl_percent,
            'health': a.health.health_label,
            'health_score': a.health.overall_health,
            'recommendation': a.recommendation,
            'top_warning': a.warnings[0] if a.warnings else None
        })
    
    # Sort by health (worst first for attention)
    heat_map.sort(key=lambda x: x['health_score'])
    
    return {
        'total_positions': len(positions),
        'total_pnl': total_pnl,
        'total_delta': total_delta,
        'daily_theta': daily_theta,
        'sector_exposure': sector_counts,
        'correlation_warning': correlation_warning,
        'heat_map': heat_map,
        'positions_analysis': [a.to_dict() for a in analyses]
    }
