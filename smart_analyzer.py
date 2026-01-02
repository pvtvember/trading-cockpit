"""
Smart Trade Analyzer - Price Action Based Recommendations
=========================================================
Adds intelligent "WHAT TO DO NOW" recommendations based on:
- Actual price action and support/resistance
- ATR-based stop and target extensions
- Time decay urgency
- Risk/reward optimization
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import math


class Urgency(Enum):
    IMMEDIATE = "IMMEDIATE"      # Do it now
    TODAY = "TODAY"              # Before close
    THIS_WEEK = "THIS_WEEK"      # Within a few days
    MONITOR = "MONITOR"          # Keep watching
    NONE = "NONE"                # No action needed


class ActionType(Enum):
    SELL_FULL = "SELL_FULL"
    SELL_PARTIAL = "SELL_PARTIAL"
    SELL_HALF = "SELL_HALF"
    UPDATE_STOP = "UPDATE_STOP"
    ROLL_POSITION = "ROLL_POSITION"
    HOLD = "HOLD"
    ADD_TO_POSITION = "ADD_TO_POSITION"
    CLOSE_RUNNER = "CLOSE_RUNNER"


@dataclass
class PriceLevel:
    """A significant price level"""
    price: float
    level_type: str          # SUPPORT, RESISTANCE, PIVOT, TARGET, STOP
    strength: str            # STRONG, MODERATE, WEAK
    source: str              # ATR, SWING, FIBO, VWAP, EMA
    description: str = ""


@dataclass 
class SmartTarget:
    """Intelligent target recommendation"""
    price: float
    option_price: float
    pnl_at_target: float
    pnl_pct_at_target: float
    probability: float       # % chance of hitting
    reasoning: str
    source: str              # ATR_EXTENSION, RESISTANCE, FIBO, etc.


@dataclass
class SmartStop:
    """Intelligent stop recommendation"""
    stock_price: float
    option_price: float
    loss_at_stop: float
    loss_pct_at_stop: float
    reasoning: str
    source: str              # ATR_TRAIL, SUPPORT, BREAKEVEN, etc.


@dataclass
class ActionItem:
    """A specific action to take"""
    action_type: ActionType
    urgency: Urgency
    title: str
    description: str
    details: List[str] = field(default_factory=list)
    
    # Specific values if applicable
    size_pct: float = 0       # % of position to act on
    price_target: float = 0   # Price to execute at
    option_price: float = 0   # Option price at execution
    

@dataclass
class TradeRecommendation:
    """Complete trade recommendation"""
    # Summary
    headline: str
    summary: str
    confidence: str          # HIGH, MEDIUM, LOW
    
    # Primary action
    primary_action: ActionItem
    
    # Secondary actions
    secondary_actions: List[ActionItem] = field(default_factory=list)
    
    # Smart levels
    smart_stops: List[SmartStop] = field(default_factory=list)
    smart_targets: List[SmartTarget] = field(default_factory=list)
    key_levels: List[PriceLevel] = field(default_factory=list)
    
    # Risk metrics
    current_risk: float = 0      # $ at risk
    risk_pct: float = 0          # % at risk
    reward_potential: float = 0  # $ potential
    risk_reward: float = 0       # R:R ratio
    
    # Reasoning
    bull_case: str = ""
    bear_case: str = ""
    key_factors: List[str] = field(default_factory=list)


class SmartAnalyzer:
    """
    Analyzes positions and generates intelligent recommendations
    based on actual price action and market data
    """
    
    @staticmethod
    def analyze_position(pos, market_data: Dict = None) -> TradeRecommendation:
        """Generate smart recommendations for a position"""
        
        # Extract key data
        pnl_pct = pos.pnl_percent
        dte = pos.current_dte
        stock = pos.current_stock_price
        option = pos.current_option_price
        entry_option = pos.entry_option_price
        delta = pos.greeks.delta or 0.5
        gamma = pos.greeks.gamma or 0.02
        atr = pos.market.atr or (stock * 0.015)
        
        is_call = pos.is_call
        is_profitable = pnl_pct > 0
        
        # Calculate key levels
        key_levels = SmartAnalyzer._calculate_key_levels(pos, atr)
        
        # Calculate smart stops
        smart_stops = SmartAnalyzer._calculate_smart_stops(pos, atr, key_levels)
        
        # Calculate smart targets
        smart_targets = SmartAnalyzer._calculate_smart_targets(pos, atr, key_levels)
        
        # Determine the primary recommendation
        recommendation = SmartAnalyzer._generate_recommendation(
            pos, pnl_pct, dte, atr, key_levels, smart_stops, smart_targets
        )
        
        return recommendation
    
    @staticmethod
    def _calculate_key_levels(pos, atr: float) -> List[PriceLevel]:
        """Calculate key support/resistance levels"""
        levels = []
        stock = pos.current_stock_price
        entry = pos.entry_stock_price
        
        # Entry level
        levels.append(PriceLevel(
            price=entry,
            level_type="PIVOT",
            strength="STRONG",
            source="ENTRY",
            description="Your entry point"
        ))
        
        # ATR-based support levels
        levels.append(PriceLevel(
            price=stock - atr,
            level_type="SUPPORT",
            strength="MODERATE",
            source="ATR",
            description="1 ATR below current"
        ))
        
        levels.append(PriceLevel(
            price=stock - (2 * atr),
            level_type="SUPPORT",
            strength="STRONG",
            source="ATR",
            description="2 ATR below current"
        ))
        
        # ATR-based resistance levels
        levels.append(PriceLevel(
            price=stock + atr,
            level_type="RESISTANCE",
            strength="MODERATE",
            source="ATR",
            description="1 ATR above current"
        ))
        
        levels.append(PriceLevel(
            price=stock + (2 * atr),
            level_type="RESISTANCE",
            strength="STRONG",
            source="ATR",
            description="2 ATR above current"
        ))
        
        # Highest since entry (swing high)
        if pos.highest_since_entry > stock:
            levels.append(PriceLevel(
                price=pos.highest_since_entry,
                level_type="RESISTANCE",
                strength="STRONG",
                source="SWING",
                description="Recent swing high"
            ))
        
        # Market-based support/resistance
        if pos.market.support_1 > 0:
            levels.append(PriceLevel(
                price=pos.market.support_1,
                level_type="SUPPORT",
                strength="STRONG",
                source="MARKET",
                description="Key support level"
            ))
        
        if pos.market.resistance_1 > 0:
            levels.append(PriceLevel(
                price=pos.market.resistance_1,
                level_type="RESISTANCE",
                strength="STRONG",
                source="MARKET",
                description="Key resistance level"
            ))
        
        # Original stop and target
        levels.append(PriceLevel(
            price=pos.stop_price,
            level_type="STOP",
            strength="STRONG",
            source="PLAN",
            description="Original stop loss"
        ))
        
        levels.append(PriceLevel(
            price=pos.target_price,
            level_type="TARGET",
            strength="STRONG",
            source="PLAN",
            description="Original target"
        ))
        
        # Strike price
        levels.append(PriceLevel(
            price=pos.strike,
            level_type="PIVOT",
            strength="STRONG",
            source="STRIKE",
            description="Option strike price"
        ))
        
        return sorted(levels, key=lambda x: x.price)
    
    @staticmethod
    def _calculate_smart_stops(pos, atr: float, levels: List[PriceLevel]) -> List[SmartStop]:
        """Calculate intelligent stop recommendations"""
        stops = []
        stock = pos.current_stock_price
        option = pos.current_option_price
        entry_option = pos.entry_option_price
        delta = pos.greeks.delta or 0.5
        gamma = pos.greeks.gamma or 0.02
        pnl_pct = pos.pnl_percent
        
        def calc_option_at_stop(stop_price: float) -> float:
            """Calculate option price at a given stock stop"""
            dist = abs(stock - stop_price)
            delta_impact = dist * abs(delta)
            gamma_impact = 0.5 * (dist ** 2) * gamma
            return max(0.01, option - delta_impact - gamma_impact)
        
        def calc_pnl_at_stop(opt_price: float) -> tuple:
            pnl = (opt_price - entry_option) * pos.quantity * 100
            pnl_pct = ((opt_price - entry_option) / entry_option * 100) if entry_option > 0 else 0
            return pnl, pnl_pct
        
        # 1. Breakeven Stop (if in profit)
        if pnl_pct > 20:
            be_stop = pos.entry_stock_price + (atr * 0.25) if pos.is_call else pos.entry_stock_price - (atr * 0.25)
            opt_at_be = calc_option_at_stop(be_stop)
            pnl, pnl_p = calc_pnl_at_stop(opt_at_be)
            
            stops.append(SmartStop(
                stock_price=be_stop,
                option_price=opt_at_be,
                loss_at_stop=pnl,
                loss_pct_at_stop=pnl_p,
                reasoning="Lock in breakeven - you're up enough to protect your entry",
                source="BREAKEVEN"
            ))
        
        # 2. ATR Trail Stop (tightest reasonable)
        atr_stop = (pos.highest_since_entry - atr) if pos.is_call else (pos.lowest_since_entry + atr)
        opt_at_atr = calc_option_at_stop(atr_stop)
        pnl, pnl_p = calc_pnl_at_stop(opt_at_atr)
        
        stops.append(SmartStop(
            stock_price=atr_stop,
            option_price=opt_at_atr,
            loss_at_stop=pnl,
            loss_pct_at_stop=pnl_p,
            reasoning=f"Tight trail: 1 ATR (${atr:.2f}) below recent high",
            source="ATR_TIGHT"
        ))
        
        # 3. Standard ATR Trail (2x ATR)
        atr_stop_2 = (pos.highest_since_entry - 2*atr) if pos.is_call else (pos.lowest_since_entry + 2*atr)
        opt_at_atr2 = calc_option_at_stop(atr_stop_2)
        pnl, pnl_p = calc_pnl_at_stop(opt_at_atr2)
        
        stops.append(SmartStop(
            stock_price=atr_stop_2,
            option_price=opt_at_atr2,
            loss_at_stop=pnl,
            loss_pct_at_stop=pnl_p,
            reasoning=f"Standard trail: 2 ATR (${2*atr:.2f}) - gives room to breathe",
            source="ATR_STANDARD"
        ))
        
        # 4. Support-based stop (if available)
        support_levels = [l for l in levels if l.level_type == "SUPPORT" and l.price < stock]
        if support_levels:
            nearest_support = max(support_levels, key=lambda x: x.price)
            support_stop = nearest_support.price - (atr * 0.25)  # Just below support
            opt_at_sup = calc_option_at_stop(support_stop)
            pnl, pnl_p = calc_pnl_at_stop(opt_at_sup)
            
            stops.append(SmartStop(
                stock_price=support_stop,
                option_price=opt_at_sup,
                loss_at_stop=pnl,
                loss_pct_at_stop=pnl_p,
                reasoning=f"Below support at ${nearest_support.price:.2f} ({nearest_support.source})",
                source="SUPPORT"
            ))
        
        # 5. Profit-lock stop (if up significantly)
        if pnl_pct > 40:
            # Lock in at least 50% of gains
            lock_pct = 0.5
            target_lock = entry_option + (option - entry_option) * lock_pct
            # Work backwards to find stock price
            # Simplified: just use a tighter trail
            lock_stop = stock - (atr * 0.5) if pos.is_call else stock + (atr * 0.5)
            opt_at_lock = calc_option_at_stop(lock_stop)
            pnl, pnl_p = calc_pnl_at_stop(opt_at_lock)
            
            stops.append(SmartStop(
                stock_price=lock_stop,
                option_price=opt_at_lock,
                loss_at_stop=pnl,
                loss_pct_at_stop=pnl_p,
                reasoning=f"Profit lock: Protect at least +{pnl_p:.0f}% of your +{pnl_pct:.0f}% gain",
                source="PROFIT_LOCK"
            ))
        
        return stops
    
    @staticmethod
    def _calculate_smart_targets(pos, atr: float, levels: List[PriceLevel]) -> List[SmartTarget]:
        """Calculate intelligent target recommendations"""
        targets = []
        stock = pos.current_stock_price
        option = pos.current_option_price
        entry_option = pos.entry_option_price
        delta = pos.greeks.delta or 0.5
        gamma = pos.greeks.gamma or 0.02
        iv = pos.greeks.iv or 0.3
        dte = pos.current_dte
        
        def calc_option_at_target(target_price: float) -> float:
            """Estimate option price at target (simplified)"""
            dist = target_price - stock if pos.is_call else stock - target_price
            delta_impact = dist * abs(delta)
            gamma_impact = 0.5 * (dist ** 2) * gamma
            # Subtract some theta decay
            theta_impact = abs(pos.greeks.theta or 0) * min(dte, 7)
            return max(0.01, option + delta_impact + gamma_impact - theta_impact)
        
        def calc_probability(target_price: float) -> float:
            """Estimate probability of hitting target"""
            if iv <= 0 or dte <= 0:
                return 50.0
            
            period_iv = iv * math.sqrt(dte / 365)
            one_sigma = stock * period_iv
            
            if one_sigma <= 0:
                return 50.0
            
            dist_to_target = abs(target_price - stock)
            z_score = dist_to_target / one_sigma
            
            # Approximate probability (simplified)
            if z_score <= 0.5:
                return 70
            elif z_score <= 1.0:
                return 50
            elif z_score <= 1.5:
                return 30
            elif z_score <= 2.0:
                return 15
            else:
                return 5
        
        def calc_pnl_at_target(opt_price: float) -> tuple:
            pnl = (opt_price - entry_option) * pos.quantity * 100
            pnl_pct = ((opt_price - entry_option) / entry_option * 100) if entry_option > 0 else 0
            return pnl, pnl_pct
        
        # 1. Conservative target (+1 ATR)
        t1 = stock + atr if pos.is_call else stock - atr
        opt1 = calc_option_at_target(t1)
        pnl1, pnl_p1 = calc_pnl_at_target(opt1)
        prob1 = calc_probability(t1)
        
        targets.append(SmartTarget(
            price=t1,
            option_price=opt1,
            pnl_at_target=pnl1,
            pnl_pct_at_target=pnl_p1,
            probability=prob1,
            reasoning=f"Conservative: +1 ATR move, {prob1:.0f}% probability",
            source="ATR_1X"
        ))
        
        # 2. Moderate target (+1.5 ATR)
        t2 = stock + (1.5 * atr) if pos.is_call else stock - (1.5 * atr)
        opt2 = calc_option_at_target(t2)
        pnl2, pnl_p2 = calc_pnl_at_target(opt2)
        prob2 = calc_probability(t2)
        
        targets.append(SmartTarget(
            price=t2,
            option_price=opt2,
            pnl_at_target=pnl2,
            pnl_pct_at_target=pnl_p2,
            probability=prob2,
            reasoning=f"Moderate: +1.5 ATR move, {prob2:.0f}% probability",
            source="ATR_1.5X"
        ))
        
        # 3. Aggressive target (+2 ATR)
        t3 = stock + (2 * atr) if pos.is_call else stock - (2 * atr)
        opt3 = calc_option_at_target(t3)
        pnl3, pnl_p3 = calc_pnl_at_target(opt3)
        prob3 = calc_probability(t3)
        
        targets.append(SmartTarget(
            price=t3,
            option_price=opt3,
            pnl_at_target=pnl3,
            pnl_pct_at_target=pnl_p3,
            probability=prob3,
            reasoning=f"Aggressive: +2 ATR move, {prob3:.0f}% probability",
            source="ATR_2X"
        ))
        
        # 4. Resistance-based target
        resistance_levels = [l for l in levels if l.level_type == "RESISTANCE" and l.price > stock]
        if resistance_levels:
            nearest_res = min(resistance_levels, key=lambda x: x.price)
            opt_r = calc_option_at_target(nearest_res.price)
            pnl_r, pnl_pr = calc_pnl_at_target(opt_r)
            prob_r = calc_probability(nearest_res.price)
            
            targets.append(SmartTarget(
                price=nearest_res.price,
                option_price=opt_r,
                pnl_at_target=pnl_r,
                pnl_pct_at_target=pnl_pr,
                probability=prob_r,
                reasoning=f"Next resistance: {nearest_res.description}",
                source="RESISTANCE"
            ))
        
        # 5. Original target
        opt_orig = calc_option_at_target(pos.target_price)
        pnl_orig, pnl_p_orig = calc_pnl_at_target(opt_orig)
        prob_orig = calc_probability(pos.target_price)
        
        targets.append(SmartTarget(
            price=pos.target_price,
            option_price=opt_orig,
            pnl_at_target=pnl_orig,
            pnl_pct_at_target=pnl_p_orig,
            probability=prob_orig,
            reasoning="Your original target",
            source="ORIGINAL"
        ))
        
        return sorted(targets, key=lambda x: x.price if pos.is_call else -x.price)
    
    @staticmethod
    def _generate_recommendation(pos, pnl_pct: float, dte: int, atr: float,
                                  levels: List[PriceLevel], 
                                  stops: List[SmartStop],
                                  targets: List[SmartTarget]) -> TradeRecommendation:
        """Generate the primary recommendation"""
        
        stock = pos.current_stock_price
        option = pos.current_option_price
        entry_option = pos.entry_option_price
        
        # Determine urgency and action based on conditions
        actions = []
        key_factors = []
        
        # Factor 1: Time decay urgency
        if dte <= 7:
            key_factors.append(f"⚠️ CRITICAL: Only {dte} DTE - theta decay severe")
            urgency = Urgency.IMMEDIATE
        elif dte <= 14:
            key_factors.append(f"⚠️ WARNING: {dte} DTE - theta accelerating")
            urgency = Urgency.TODAY
        elif dte <= 21:
            key_factors.append(f"📅 {dte} DTE - entering acceleration zone")
            urgency = Urgency.THIS_WEEK
        else:
            key_factors.append(f"✅ {dte} DTE - time decay manageable")
            urgency = Urgency.MONITOR
        
        # Factor 2: P&L status
        if pnl_pct >= 100:
            key_factors.append(f"🎯 DOUBLED UP: +{pnl_pct:.0f}% - protect these gains!")
        elif pnl_pct >= 50:
            key_factors.append(f"🎯 T1 HIT: +{pnl_pct:.0f}% - take partial profits")
        elif pnl_pct >= 25:
            key_factors.append(f"📈 Good profit: +{pnl_pct:.0f}% - consider tightening stop")
        elif pnl_pct >= 0:
            key_factors.append(f"📊 Slight profit: +{pnl_pct:.0f}% - monitor closely")
        elif pnl_pct >= -25:
            key_factors.append(f"📉 Small loss: {pnl_pct:.0f}% - stick to plan")
        else:
            key_factors.append(f"🔴 Significant loss: {pnl_pct:.0f}% - evaluate stop")
        
        # Factor 3: Trend alignment
        trend = pos.market.trend_daily
        trend_str = trend.value if hasattr(trend, 'value') else str(trend)
        if pos.is_call and 'UP' in trend_str:
            key_factors.append(f"✅ Trend aligned: {trend_str}")
        elif not pos.is_call and 'DOWN' in trend_str:
            key_factors.append(f"✅ Trend aligned: {trend_str}")
        else:
            key_factors.append(f"⚠️ Trend not aligned: {trend_str}")
        
        # Generate primary action
        if dte <= 7 and pnl_pct > 0:
            primary = ActionItem(
                action_type=ActionType.SELL_FULL,
                urgency=Urgency.IMMEDIATE,
                title="EXIT NOW - Take Your Profit",
                description=f"With only {dte} DTE and +{pnl_pct:.0f}% profit, theta will destroy your gains",
                details=[
                    f"Current value: ${option:.2f}",
                    f"Profit: ${(option - entry_option) * pos.quantity * 100:.0f}",
                    "Don't let a winner become a loser"
                ],
                size_pct=100,
                price_target=stock,
                option_price=option
            )
            headline = "🚨 EXIT NOW"
            summary = f"Take your +{pnl_pct:.0f}% profit - {dte} DTE means theta will eat your gains"
            confidence = "HIGH"
            
        elif dte <= 7 and pnl_pct <= 0:
            primary = ActionItem(
                action_type=ActionType.SELL_FULL,
                urgency=Urgency.IMMEDIATE,
                title="CUT THE LOSS",
                description=f"With {dte} DTE and {pnl_pct:.0f}%, time decay will make this worse",
                details=[
                    f"Current value: ${option:.2f}",
                    f"Loss: ${(option - entry_option) * pos.quantity * 100:.0f}",
                    "Accept the loss, preserve capital"
                ],
                size_pct=100,
                price_target=stock,
                option_price=option
            )
            headline = "🛑 CUT LOSS"
            summary = f"Exit with {pnl_pct:.0f}% loss - {dte} DTE means no recovery likely"
            confidence = "HIGH"
            
        elif pnl_pct >= 100:
            primary = ActionItem(
                action_type=ActionType.SELL_PARTIAL,
                urgency=Urgency.TODAY,
                title="TAKE 75% OFF - You Doubled!",
                description="You've doubled your money. Lock it in.",
                details=[
                    "Sell 75% to realize gains",
                    "Keep 25% as a runner",
                    f"Move stop to breakeven on runner"
                ],
                size_pct=75,
                price_target=stock,
                option_price=option
            )
            headline = "💰 DOUBLE! TAKE PROFITS"
            summary = f"+{pnl_pct:.0f}% is a home run - sell 75%, keep 25% as runner"
            confidence = "HIGH"
            
        elif pnl_pct >= 50:
            primary = ActionItem(
                action_type=ActionType.SELL_HALF,
                urgency=Urgency.TODAY,
                title="SELL 50% - T1 Target Hit",
                description="First target hit - take half off and let the rest ride",
                details=[
                    f"Sell 50% at ${option:.2f}",
                    f"Lock in ${(option - entry_option) * pos.quantity * 50:.0f} profit",
                    "Move stop to breakeven on remainder"
                ],
                size_pct=50,
                price_target=stock,
                option_price=option
            )
            headline = "🎯 T1 HIT - SELL HALF"
            summary = f"+{pnl_pct:.0f}% hit first target - sell 50%, protect the rest"
            confidence = "HIGH"
            
        elif pnl_pct >= 30 and dte <= 14:
            # Profitable but time running out
            best_stop = stops[0] if stops else None
            primary = ActionItem(
                action_type=ActionType.SELL_PARTIAL,
                urgency=Urgency.TODAY,
                title="TAKE SOME - Time Running Out",
                description=f"Good profit but only {dte} DTE - reduce risk",
                details=[
                    "Sell 50-75% to lock in gains",
                    "Keep small runner if bullish",
                    f"Trail stop to ${best_stop.stock_price:.2f}" if best_stop else "Tighten stop"
                ],
                size_pct=50,
                price_target=stock,
                option_price=option
            )
            headline = "⏰ TIME RUNNING - TAKE SOME"
            summary = f"+{pnl_pct:.0f}% with {dte} DTE - sell at least half"
            confidence = "MEDIUM"
            
        elif pnl_pct >= 20:
            best_stop = stops[0] if stops else None
            primary = ActionItem(
                action_type=ActionType.UPDATE_STOP,
                urgency=Urgency.TODAY,
                title="TIGHTEN STOP - Protect Gains",
                description="Lock in some profit with a trailing stop",
                details=[
                    f"Move stop to ${best_stop.stock_price:.2f}" if best_stop else "Tighten stop",
                    f"This locks in {best_stop.loss_pct_at_stop:.0f}% if stopped" if best_stop else "",
                    "Let winner run with protection"
                ],
                size_pct=0,
                price_target=best_stop.stock_price if best_stop else 0,
                option_price=best_stop.option_price if best_stop else 0
            )
            headline = "📍 TRAIL STOP"
            summary = f"+{pnl_pct:.0f}% - protect with stop at ${best_stop.stock_price:.2f}" if best_stop else f"+{pnl_pct:.0f}% - tighten stop"
            confidence = "MEDIUM"
            
        elif pnl_pct >= 0:
            primary = ActionItem(
                action_type=ActionType.HOLD,
                urgency=Urgency.MONITOR,
                title="HOLD - Stick to Plan",
                description="Position working, follow your trade plan",
                details=[
                    "Keep original stop in place",
                    f"Target: ${pos.target_price:.2f}",
                    "Reassess if DTE drops below 21"
                ],
                size_pct=0
            )
            headline = "✋ HOLD POSITION"
            summary = f"+{pnl_pct:.0f}% - on track, continue holding"
            confidence = "MEDIUM"
            
        elif pnl_pct > -25:
            primary = ActionItem(
                action_type=ActionType.HOLD,
                urgency=Urgency.MONITOR,
                title="HOLD - Within Normal Range",
                description="Small drawdown is normal - stick to your stop",
                details=[
                    f"Stop at ${pos.stop_price:.2f}",
                    "Don't panic sell",
                    "Thesis still valid unless stop hit"
                ],
                size_pct=0
            )
            headline = "✋ HOLD - NORMAL DRAWDOWN"
            summary = f"{pnl_pct:.0f}% is within normal range - trust your stop"
            confidence = "MEDIUM"
            
        else:
            primary = ActionItem(
                action_type=ActionType.SELL_FULL,
                urgency=Urgency.TODAY,
                title="EVALUATE EXIT",
                description="Significant loss - is your thesis still valid?",
                details=[
                    f"Currently down {abs(pnl_pct):.0f}%",
                    "If thesis broken, exit",
                    "If stop not hit, can hold if confident"
                ],
                size_pct=100
            )
            headline = "🔴 EVALUATE POSITION"
            summary = f"Down {abs(pnl_pct):.0f}% - check if thesis still valid"
            confidence = "LOW"
        
        # Build secondary actions
        secondary = []
        
        # Add stop update as secondary if not primary
        if primary.action_type != ActionType.UPDATE_STOP and stops:
            best_stop = stops[0]
            secondary.append(ActionItem(
                action_type=ActionType.UPDATE_STOP,
                urgency=Urgency.TODAY,
                title=f"Update Stop to ${best_stop.stock_price:.2f}",
                description=best_stop.reasoning,
                details=[f"Option stop: ${best_stop.option_price:.2f}"],
                price_target=best_stop.stock_price,
                option_price=best_stop.option_price
            ))
        
        # Calculate risk metrics
        best_stop = stops[0] if stops else None
        best_target = targets[-1] if targets else None  # Last target is usually most aggressive
        
        current_risk = abs((option - (best_stop.option_price if best_stop else entry_option * 0.5)) * pos.quantity * 100)
        reward_potential = abs((best_target.option_price - option) * pos.quantity * 100) if best_target else 0
        risk_reward = reward_potential / current_risk if current_risk > 0 else 0
        
        # Bull/Bear cases
        bull_case = f"Stock continues to ${targets[0].price:.2f} → +{targets[0].pnl_pct_at_target:.0f}% (${targets[0].pnl_at_target:.0f})" if targets else ""
        bear_case = f"Stock drops to ${stops[0].stock_price:.2f} → {stops[0].loss_pct_at_stop:.0f}% (${stops[0].loss_at_stop:.0f})" if stops else ""
        
        return TradeRecommendation(
            headline=headline,
            summary=summary,
            confidence=confidence,
            primary_action=primary,
            secondary_actions=secondary,
            smart_stops=stops,
            smart_targets=targets,
            key_levels=levels,
            current_risk=current_risk,
            risk_pct=(current_risk / (option * pos.quantity * 100) * 100) if option > 0 else 0,
            reward_potential=reward_potential,
            risk_reward=risk_reward,
            bull_case=bull_case,
            bear_case=bear_case,
            key_factors=key_factors
        )


def get_recommendation_dict(pos) -> Dict:
    """Get recommendation as a dictionary for the web interface"""
    rec = SmartAnalyzer.analyze_position(pos)
    
    return {
        'headline': rec.headline,
        'summary': rec.summary,
        'confidence': rec.confidence,
        
        'primary_action': {
            'type': rec.primary_action.action_type.value,
            'urgency': rec.primary_action.urgency.value,
            'title': rec.primary_action.title,
            'description': rec.primary_action.description,
            'details': rec.primary_action.details,
            'size_pct': rec.primary_action.size_pct,
            'price_target': rec.primary_action.price_target,
            'option_price': rec.primary_action.option_price,
        },
        
        'secondary_actions': [
            {
                'type': a.action_type.value,
                'title': a.title,
                'description': a.description,
                'price_target': a.price_target,
                'option_price': a.option_price,
            }
            for a in rec.secondary_actions
        ],
        
        'smart_stops': [
            {
                'stock_price': s.stock_price,
                'option_price': s.option_price,
                'loss_at_stop': s.loss_at_stop,
                'loss_pct': s.loss_pct_at_stop,
                'reasoning': s.reasoning,
                'source': s.source,
            }
            for s in rec.smart_stops
        ],
        
        'smart_targets': [
            {
                'price': t.price,
                'option_price': t.option_price,
                'pnl': t.pnl_at_target,
                'pnl_pct': t.pnl_pct_at_target,
                'probability': t.probability,
                'reasoning': t.reasoning,
                'source': t.source,
            }
            for t in rec.smart_targets
        ],
        
        'key_levels': [
            {
                'price': l.price,
                'type': l.level_type,
                'strength': l.strength,
                'source': l.source,
                'description': l.description,
            }
            for l in rec.key_levels
        ],
        
        'risk_metrics': {
            'current_risk': rec.current_risk,
            'risk_pct': rec.risk_pct,
            'reward_potential': rec.reward_potential,
            'risk_reward': rec.risk_reward,
        },
        
        'bull_case': rec.bull_case,
        'bear_case': rec.bear_case,
        'key_factors': rec.key_factors,
    }
