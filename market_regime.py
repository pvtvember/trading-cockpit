"""
Trading Cockpit - Market Regime & Analysis Module
==================================================
Tracks overall market conditions to adjust trading strategy.

Components:
- VIX analysis (level, term structure, percentile)
- SPY/QQQ trend and momentum
- Market breadth (advance/decline, new highs/lows)
- Sector rotation
- Fear & Greed proxy
- Strategy recommendations based on regime
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta


class MarketRegime(Enum):
    """Overall market regime classification"""
    RISK_ON_BULL = "RISK_ON_BULL"           # Low VIX, strong uptrend - aggressive calls
    STEADY_BULL = "STEADY_BULL"             # Normal VIX, uptrend - standard calls
    CAUTIOUS_BULL = "CAUTIOUS_BULL"         # Elevated VIX, weak uptrend - smaller size
    NEUTRAL_CHOP = "NEUTRAL_CHOP"           # Range-bound, no clear direction
    CAUTIOUS_BEAR = "CAUTIOUS_BEAR"         # Elevated VIX, weak downtrend
    STEADY_BEAR = "STEADY_BEAR"             # Normal VIX, downtrend - standard puts
    RISK_OFF_BEAR = "RISK_OFF_BEAR"         # High VIX, strong downtrend - aggressive puts
    CRASH = "CRASH"                          # VIX spike, panic selling
    RECOVERY = "RECOVERY"                    # VIX falling from highs, bounce


class TrendDirection(Enum):
    STRONG_UP = "STRONG_UP"
    UP = "UP"
    WEAK_UP = "WEAK_UP"
    NEUTRAL = "NEUTRAL"
    WEAK_DOWN = "WEAK_DOWN"
    DOWN = "DOWN"
    STRONG_DOWN = "STRONG_DOWN"


class VolatilityRegime(Enum):
    VERY_LOW = "VERY_LOW"       # VIX < 12
    LOW = "LOW"                 # VIX 12-15
    NORMAL = "NORMAL"           # VIX 15-20
    ELEVATED = "ELEVATED"       # VIX 20-25
    HIGH = "HIGH"               # VIX 25-35
    EXTREME = "EXTREME"         # VIX > 35


@dataclass
class VIXAnalysis:
    """VIX and volatility analysis"""
    level: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    
    # Historical context
    percentile_30d: float = 50.0      # Where is VIX vs last 30 days
    percentile_1y: float = 50.0       # Where is VIX vs last year
    
    # Term structure
    vix_9d: float = 0.0               # VIX9D (near-term)
    vix_3m: float = 0.0               # VIX3M (3-month)
    term_structure: str = "CONTANGO"  # CONTANGO, BACKWARDATION, FLAT
    
    # Regime
    regime: VolatilityRegime = VolatilityRegime.NORMAL
    
    @property
    def regime_color(self) -> str:
        colors = {
            VolatilityRegime.VERY_LOW: "green",
            VolatilityRegime.LOW: "green",
            VolatilityRegime.NORMAL: "yellow",
            VolatilityRegime.ELEVATED: "orange",
            VolatilityRegime.HIGH: "red",
            VolatilityRegime.EXTREME: "red",
        }
        return colors.get(self.regime, "white")
    
    @property
    def interpretation(self) -> str:
        if self.regime == VolatilityRegime.VERY_LOW:
            return "Complacency - good for buying options cheap"
        elif self.regime == VolatilityRegime.LOW:
            return "Calm markets - favorable for directional plays"
        elif self.regime == VolatilityRegime.NORMAL:
            return "Normal conditions - standard strategies"
        elif self.regime == VolatilityRegime.ELEVATED:
            return "Uncertainty rising - reduce size, widen stops"
        elif self.regime == VolatilityRegime.HIGH:
            return "Fear elevated - be defensive, consider puts"
        else:
            return "Panic mode - wait for VIX to peak before buying"


@dataclass
class MarketTrend:
    """Trend analysis for major indices"""
    symbol: str = "SPY"
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    
    # Moving averages
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_50: float = 0.0
    sma_200: float = 0.0
    
    # Trend metrics
    direction: TrendDirection = TrendDirection.NEUTRAL
    above_200sma: bool = True
    ema_alignment: str = "MIXED"      # BULLISH (9>21>50), BEARISH (9<21<50), MIXED
    
    # Momentum
    rsi: float = 50.0
    macd_histogram: float = 0.0
    macd_signal: str = "NEUTRAL"
    
    # Distance from key levels
    pct_from_high: float = 0.0        # % below 52-week high
    pct_from_low: float = 0.0         # % above 52-week low
    pct_from_200sma: float = 0.0      # % from 200 SMA
    
    @property
    def health_score(self) -> float:
        """0-100 score of market health"""
        score = 50
        
        # Trend contribution
        if self.direction in [TrendDirection.STRONG_UP, TrendDirection.UP]:
            score += 20
        elif self.direction in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
            score -= 20
        
        # Above 200 SMA is bullish
        if self.above_200sma:
            score += 10
        else:
            score -= 10
        
        # RSI
        if 40 <= self.rsi <= 60:
            score += 5  # Healthy, not overbought/oversold
        elif self.rsi > 70:
            score -= 5  # Overbought risk
        elif self.rsi < 30:
            score += 10  # Oversold bounce opportunity
        
        # MACD
        if self.macd_signal == "BULLISH":
            score += 10
        elif self.macd_signal == "BEARISH":
            score -= 10
        
        return max(0, min(100, score))


@dataclass
class MarketBreadth:
    """Market breadth indicators"""
    # Advance/Decline
    advancers: int = 0
    decliners: int = 0
    unchanged: int = 0
    ad_ratio: float = 1.0
    ad_line_trend: str = "NEUTRAL"    # RISING, FALLING, NEUTRAL
    
    # New Highs/Lows
    new_highs: int = 0
    new_lows: int = 0
    hl_ratio: float = 1.0
    
    # Percent above moving averages
    pct_above_200sma: float = 50.0
    pct_above_50sma: float = 50.0
    pct_above_20sma: float = 50.0
    
    # McClellan Oscillator (simplified)
    mcclellan: float = 0.0
    
    @property
    def breadth_score(self) -> float:
        """0-100 breadth health score"""
        score = 50
        
        # A/D ratio
        if self.ad_ratio > 2:
            score += 20
        elif self.ad_ratio > 1.5:
            score += 10
        elif self.ad_ratio < 0.5:
            score -= 20
        elif self.ad_ratio < 0.67:
            score -= 10
        
        # New highs vs lows
        if self.new_highs > self.new_lows * 2:
            score += 15
        elif self.new_lows > self.new_highs * 2:
            score -= 15
        
        # Participation
        if self.pct_above_200sma > 70:
            score += 10
        elif self.pct_above_200sma < 30:
            score -= 10
        
        return max(0, min(100, score))
    
    @property
    def interpretation(self) -> str:
        if self.breadth_score >= 70:
            return "Strong participation - healthy rally"
        elif self.breadth_score >= 55:
            return "Decent breadth - market supported"
        elif self.breadth_score >= 45:
            return "Mixed breadth - be selective"
        elif self.breadth_score >= 30:
            return "Weak breadth - rally on thin ice"
        else:
            return "Poor breadth - distribution underway"


@dataclass
class SectorAnalysis:
    """Sector rotation and relative strength"""
    sectors: Dict[str, Dict] = field(default_factory=dict)
    # Format: {"XLK": {"name": "Technology", "change": 1.2, "rs_rank": 1, "trend": "UP"}}
    
    leading: List[str] = field(default_factory=list)
    lagging: List[str] = field(default_factory=list)
    rotation_signal: str = "NEUTRAL"  # RISK_ON, RISK_OFF, NEUTRAL
    
    @property
    def interpretation(self) -> str:
        if self.rotation_signal == "RISK_ON":
            return "Money flowing to growth/cyclicals - bullish"
        elif self.rotation_signal == "RISK_OFF":
            return "Money flowing to defensives - cautious"
        else:
            return "Mixed rotation - no clear signal"


@dataclass
class StrategyRecommendation:
    """Trading strategy adjustments based on regime"""
    # Position sizing
    size_multiplier: float = 1.0      # 0.5 = half size, 1.5 = 1.5x size
    max_positions: int = 5
    
    # Direction bias
    bias: str = "NEUTRAL"             # BULLISH, BEARISH, NEUTRAL
    preferred_direction: str = "CALLS"  # CALLS, PUTS, BOTH, NONE
    
    # Risk management
    stop_multiplier: float = 1.0      # 0.75 = tighter stops, 1.25 = wider
    profit_taking: str = "NORMAL"     # AGGRESSIVE, NORMAL, PATIENT
    
    # Options specifics
    min_dte: int = 14
    max_dte: int = 45
    target_delta: float = 0.50
    iv_rank_preference: str = "LOW"   # LOW, ANY, HIGH
    
    # Specific recommendations
    recommendations: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)


@dataclass
class MarketSnapshot:
    """Complete market snapshot"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Components
    regime: MarketRegime = MarketRegime.NEUTRAL_CHOP
    vix: VIXAnalysis = field(default_factory=VIXAnalysis)
    spy: MarketTrend = field(default_factory=MarketTrend)
    qqq: MarketTrend = field(default_factory=MarketTrend)
    breadth: MarketBreadth = field(default_factory=MarketBreadth)
    sectors: SectorAnalysis = field(default_factory=SectorAnalysis)
    strategy: StrategyRecommendation = field(default_factory=StrategyRecommendation)
    
    # Overall scores
    overall_score: float = 50.0       # 0-100 market health
    risk_level: str = "MODERATE"      # LOW, MODERATE, ELEVATED, HIGH
    
    # Key messages
    headline: str = ""
    summary: str = ""
    key_levels: Dict[str, float] = field(default_factory=dict)


class MarketAnalyzer:
    """Analyzes market conditions and determines regime"""
    
    def __init__(self, api=None):
        self.api = api
    
    def analyze(self) -> MarketSnapshot:
        """Generate complete market analysis"""
        snapshot = MarketSnapshot()
        
        if self.api:
            # Fetch real data
            self._fetch_vix_data(snapshot)
            self._fetch_spy_data(snapshot)
            self._fetch_qqq_data(snapshot)
            self._fetch_breadth_data(snapshot)
        else:
            # Use defaults/demo data
            self._set_demo_data(snapshot)
        
        # Determine regime
        self._determine_regime(snapshot)
        
        # Generate strategy recommendations
        self._generate_strategy(snapshot)
        
        # Calculate overall score
        self._calculate_overall(snapshot)
        
        return snapshot
    
    def _fetch_vix_data(self, snapshot: MarketSnapshot):
        """Fetch VIX data from API"""
        try:
            vix_data = self.api.get_stock_snapshot("VIX")
            if vix_data and vix_data.get('price'):
                snapshot.vix.level = vix_data['price']
                snapshot.vix.change = vix_data.get('change', 0)
                snapshot.vix.change_pct = vix_data.get('change_pct', 0)
                
                # Determine regime based on level
                level = snapshot.vix.level
                if level < 12:
                    snapshot.vix.regime = VolatilityRegime.VERY_LOW
                elif level < 15:
                    snapshot.vix.regime = VolatilityRegime.LOW
                elif level < 20:
                    snapshot.vix.regime = VolatilityRegime.NORMAL
                elif level < 25:
                    snapshot.vix.regime = VolatilityRegime.ELEVATED
                elif level < 35:
                    snapshot.vix.regime = VolatilityRegime.HIGH
                else:
                    snapshot.vix.regime = VolatilityRegime.EXTREME
        except Exception as e:
            print(f"VIX fetch error: {e}")
    
    def _fetch_spy_data(self, snapshot: MarketSnapshot):
        """Fetch SPY data and calculate trend"""
        try:
            # Current price
            spy_data = self.api.get_stock_snapshot("SPY")
            if spy_data and spy_data.get('price'):
                snapshot.spy.symbol = "SPY"
                snapshot.spy.price = spy_data['price']
                snapshot.spy.change = spy_data.get('change', 0)
                snapshot.spy.change_pct = spy_data.get('change_pct', 0)
            
            # Historical data for MAs
            history = self.api.get_stock_history("SPY", 250)
            if history and len(history) > 50:
                closes = [bar['c'] for bar in history]
                
                # Calculate EMAs
                snapshot.spy.ema_9 = self._calc_ema(closes, 9)
                snapshot.spy.ema_21 = self._calc_ema(closes, 21)
                snapshot.spy.ema_50 = self._calc_ema(closes, 50)
                
                # SMA 200
                if len(closes) >= 200:
                    snapshot.spy.sma_200 = sum(closes[-200:]) / 200
                    snapshot.spy.above_200sma = snapshot.spy.price > snapshot.spy.sma_200
                    snapshot.spy.pct_from_200sma = ((snapshot.spy.price - snapshot.spy.sma_200) / snapshot.spy.sma_200) * 100
                
                # RSI
                snapshot.spy.rsi = self._calc_rsi(closes)
                
                # Determine trend
                snapshot.spy.direction = self._determine_trend(
                    snapshot.spy.price,
                    snapshot.spy.ema_9,
                    snapshot.spy.ema_21,
                    snapshot.spy.ema_50
                )
                
                # EMA alignment
                if snapshot.spy.ema_9 > snapshot.spy.ema_21 > snapshot.spy.ema_50:
                    snapshot.spy.ema_alignment = "BULLISH"
                elif snapshot.spy.ema_9 < snapshot.spy.ema_21 < snapshot.spy.ema_50:
                    snapshot.spy.ema_alignment = "BEARISH"
                else:
                    snapshot.spy.ema_alignment = "MIXED"
                    
        except Exception as e:
            print(f"SPY fetch error: {e}")
    
    def _fetch_qqq_data(self, snapshot: MarketSnapshot):
        """Fetch QQQ data"""
        try:
            qqq_data = self.api.get_stock_snapshot("QQQ")
            if qqq_data and qqq_data.get('price'):
                snapshot.qqq.symbol = "QQQ"
                snapshot.qqq.price = qqq_data['price']
                snapshot.qqq.change = qqq_data.get('change', 0)
                snapshot.qqq.change_pct = qqq_data.get('change_pct', 0)
            
            history = self.api.get_stock_history("QQQ", 100)
            if history and len(history) > 20:
                closes = [bar['c'] for bar in history]
                snapshot.qqq.rsi = self._calc_rsi(closes)
                snapshot.qqq.ema_21 = self._calc_ema(closes, 21)
                snapshot.qqq.direction = self._determine_trend(
                    snapshot.qqq.price,
                    self._calc_ema(closes, 9),
                    snapshot.qqq.ema_21,
                    self._calc_ema(closes, 50) if len(closes) >= 50 else snapshot.qqq.ema_21
                )
        except Exception as e:
            print(f"QQQ fetch error: {e}")
    
    def _fetch_breadth_data(self, snapshot: MarketSnapshot):
        """Fetch market breadth - simplified"""
        # In a real implementation, you'd fetch from a breadth data provider
        # For now, estimate based on SPY/QQQ
        spy_bullish = snapshot.spy.direction in [TrendDirection.STRONG_UP, TrendDirection.UP]
        qqq_bullish = snapshot.qqq.direction in [TrendDirection.STRONG_UP, TrendDirection.UP]
        
        if spy_bullish and qqq_bullish:
            snapshot.breadth.ad_ratio = 1.8
            snapshot.breadth.pct_above_200sma = 65
        elif not spy_bullish and not qqq_bullish:
            snapshot.breadth.ad_ratio = 0.6
            snapshot.breadth.pct_above_200sma = 35
        else:
            snapshot.breadth.ad_ratio = 1.0
            snapshot.breadth.pct_above_200sma = 50
    
    def _set_demo_data(self, snapshot: MarketSnapshot):
        """Set demo/default data when no API"""
        snapshot.vix.level = 16.5
        snapshot.vix.regime = VolatilityRegime.NORMAL
        
        snapshot.spy.symbol = "SPY"
        snapshot.spy.price = 595.0
        snapshot.spy.change_pct = 0.45
        snapshot.spy.direction = TrendDirection.UP
        snapshot.spy.rsi = 58
        snapshot.spy.above_200sma = True
        snapshot.spy.ema_alignment = "BULLISH"
        
        snapshot.qqq.symbol = "QQQ"
        snapshot.qqq.price = 520.0
        snapshot.qqq.change_pct = 0.62
        snapshot.qqq.direction = TrendDirection.UP
        snapshot.qqq.rsi = 55
        
        snapshot.breadth.ad_ratio = 1.5
        snapshot.breadth.pct_above_200sma = 62
    
    def _determine_regime(self, snapshot: MarketSnapshot):
        """Determine overall market regime"""
        vix_level = snapshot.vix.level
        spy_trend = snapshot.spy.direction
        
        # Crash detection
        if vix_level > 35 and spy_trend in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
            snapshot.regime = MarketRegime.CRASH
        
        # Recovery (VIX falling from high)
        elif vix_level > 25 and snapshot.vix.change < -2:
            snapshot.regime = MarketRegime.RECOVERY
        
        # Risk-on bull (low VIX + strong uptrend)
        elif vix_level < 15 and spy_trend in [TrendDirection.STRONG_UP, TrendDirection.UP]:
            snapshot.regime = MarketRegime.RISK_ON_BULL
        
        # Steady bull
        elif vix_level < 20 and spy_trend in [TrendDirection.STRONG_UP, TrendDirection.UP, TrendDirection.WEAK_UP]:
            snapshot.regime = MarketRegime.STEADY_BULL
        
        # Cautious bull
        elif vix_level < 25 and spy_trend in [TrendDirection.WEAK_UP, TrendDirection.NEUTRAL]:
            snapshot.regime = MarketRegime.CAUTIOUS_BULL
        
        # Risk-off bear
        elif vix_level > 25 and spy_trend in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
            snapshot.regime = MarketRegime.RISK_OFF_BEAR
        
        # Steady bear
        elif spy_trend in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
            snapshot.regime = MarketRegime.STEADY_BEAR
        
        # Cautious bear
        elif spy_trend in [TrendDirection.WEAK_DOWN]:
            snapshot.regime = MarketRegime.CAUTIOUS_BEAR
        
        # Neutral/chop
        else:
            snapshot.regime = MarketRegime.NEUTRAL_CHOP
    
    def _generate_strategy(self, snapshot: MarketSnapshot):
        """Generate strategy recommendations based on regime"""
        regime = snapshot.regime
        strategy = snapshot.strategy
        
        if regime == MarketRegime.RISK_ON_BULL:
            strategy.size_multiplier = 1.25
            strategy.max_positions = 6
            strategy.bias = "BULLISH"
            strategy.preferred_direction = "CALLS"
            strategy.stop_multiplier = 1.1
            strategy.profit_taking = "PATIENT"
            strategy.min_dte = 21
            strategy.max_dte = 60
            strategy.target_delta = 0.55
            strategy.iv_rank_preference = "LOW"
            strategy.recommendations = [
                "Aggressive call buying on pullbacks",
                "Let winners run - market supports",
                "Buy breakouts with volume",
                "Focus on leading sectors (Tech, Consumer Discretionary)"
            ]
            strategy.avoid = [
                "Fighting the trend with puts",
                "Over-hedging in low VIX environment"
            ]
        
        elif regime == MarketRegime.STEADY_BULL:
            strategy.size_multiplier = 1.0
            strategy.max_positions = 5
            strategy.bias = "BULLISH"
            strategy.preferred_direction = "CALLS"
            strategy.stop_multiplier = 1.0
            strategy.profit_taking = "NORMAL"
            strategy.recommendations = [
                "Standard call buying strategy",
                "Buy dips to 21 EMA",
                "Take partial profits at +50%",
                "Trail stops as positions profit"
            ]
            strategy.avoid = [
                "Chasing extended moves",
                "Ignoring stop losses"
            ]
        
        elif regime == MarketRegime.CAUTIOUS_BULL:
            strategy.size_multiplier = 0.75
            strategy.max_positions = 4
            strategy.bias = "NEUTRAL"
            strategy.preferred_direction = "CALLS"
            strategy.stop_multiplier = 0.85
            strategy.profit_taking = "AGGRESSIVE"
            strategy.recommendations = [
                "Reduce position sizes",
                "Take profits quickly (+30-40%)",
                "Tighter stops",
                "Focus on strongest stocks only"
            ]
            strategy.avoid = [
                "Averaging down",
                "Full-size positions",
                "Weaker stocks hoping for catch-up"
            ]
        
        elif regime == MarketRegime.NEUTRAL_CHOP:
            strategy.size_multiplier = 0.5
            strategy.max_positions = 3
            strategy.bias = "NEUTRAL"
            strategy.preferred_direction = "BOTH"
            strategy.stop_multiplier = 0.75
            strategy.profit_taking = "AGGRESSIVE"
            strategy.recommendations = [
                "Reduce activity - choppy markets hurt",
                "Play both directions (range trading)",
                "Quick scalps only",
                "Wait for clearer trend"
            ]
            strategy.avoid = [
                "Holding for big moves",
                "Trend-following strategies",
                "Large positions"
            ]
        
        elif regime == MarketRegime.CAUTIOUS_BEAR:
            strategy.size_multiplier = 0.75
            strategy.max_positions = 4
            strategy.bias = "BEARISH"
            strategy.preferred_direction = "PUTS"
            strategy.stop_multiplier = 0.85
            strategy.profit_taking = "AGGRESSIVE"
            strategy.recommendations = [
                "Small put positions on bounces",
                "Quick profits - don't get greedy",
                "Watch for bear market rallies",
                "Protect any long positions"
            ]
            strategy.avoid = [
                "Bottom fishing with calls",
                "Holding losers hoping for recovery"
            ]
        
        elif regime == MarketRegime.STEADY_BEAR:
            strategy.size_multiplier = 1.0
            strategy.max_positions = 5
            strategy.bias = "BEARISH"
            strategy.preferred_direction = "PUTS"
            strategy.recommendations = [
                "Put buying on rallies to resistance",
                "Short bounces to declining MAs",
                "Trail stops on winning puts",
                "Focus on weakest sectors"
            ]
            strategy.avoid = [
                "Trying to call the bottom",
                "Holding calls against the trend"
            ]
        
        elif regime == MarketRegime.RISK_OFF_BEAR:
            strategy.size_multiplier = 1.25
            strategy.max_positions = 4
            strategy.bias = "BEARISH"
            strategy.preferred_direction = "PUTS"
            strategy.stop_multiplier = 1.2
            strategy.profit_taking = "PATIENT"
            strategy.min_dte = 30
            strategy.recommendations = [
                "Aggressive put buying",
                "Let winners run - trend is your friend",
                "VIX calls as hedge",
                "Cash is a position - be selective"
            ]
            strategy.avoid = [
                "Catching falling knives",
                "Counter-trend calls",
                "Averaging down on longs"
            ]
        
        elif regime == MarketRegime.CRASH:
            strategy.size_multiplier = 0.5
            strategy.max_positions = 2
            strategy.bias = "BEARISH"
            strategy.preferred_direction = "NONE"
            strategy.recommendations = [
                "PRESERVE CAPITAL - mostly cash",
                "Wait for VIX to peak",
                "Small put positions only if must trade",
                "Watch for capitulation signals"
            ]
            strategy.avoid = [
                "Buying calls into the crash",
                "Large positions in any direction",
                "Panic selling existing positions at lows"
            ]
        
        elif regime == MarketRegime.RECOVERY:
            strategy.size_multiplier = 0.75
            strategy.max_positions = 4
            strategy.bias = "BULLISH"
            strategy.preferred_direction = "CALLS"
            strategy.profit_taking = "AGGRESSIVE"
            strategy.recommendations = [
                "Start small long positions",
                "Buy quality on weakness",
                "Take profits quickly - bounces can fail",
                "Watch VIX for confirmation"
            ]
            strategy.avoid = [
                "Going all-in immediately",
                "Assuming V-bottom recovery"
            ]
    
    def _calculate_overall(self, snapshot: MarketSnapshot):
        """Calculate overall market score and set messages"""
        # Combine scores
        spy_score = snapshot.spy.health_score
        breadth_score = snapshot.breadth.breadth_score
        
        # VIX contribution (inverted - lower is better for bulls)
        vix_score = 100 - min(100, snapshot.vix.level * 2)
        
        snapshot.overall_score = (spy_score * 0.4 + breadth_score * 0.3 + vix_score * 0.3)
        
        # Risk level
        if snapshot.overall_score >= 70:
            snapshot.risk_level = "LOW"
        elif snapshot.overall_score >= 55:
            snapshot.risk_level = "MODERATE"
        elif snapshot.overall_score >= 40:
            snapshot.risk_level = "ELEVATED"
        else:
            snapshot.risk_level = "HIGH"
        
        # Generate headline
        regime_names = {
            MarketRegime.RISK_ON_BULL: "🟢 RISK ON - Full Steam Ahead",
            MarketRegime.STEADY_BULL: "🟢 STEADY BULL - Normal Operations",
            MarketRegime.CAUTIOUS_BULL: "🟡 CAUTIOUS - Reduce Size",
            MarketRegime.NEUTRAL_CHOP: "🟡 CHOPPY - Be Patient",
            MarketRegime.CAUTIOUS_BEAR: "🟠 CAUTION - Bearish Tilt",
            MarketRegime.STEADY_BEAR: "🔴 BEAR MARKET - Trade Puts",
            MarketRegime.RISK_OFF_BEAR: "🔴 RISK OFF - Defensive Mode",
            MarketRegime.CRASH: "🚨 CRASH - Preserve Capital",
            MarketRegime.RECOVERY: "🟡 RECOVERY - Cautious Buying",
        }
        snapshot.headline = regime_names.get(snapshot.regime, "⚪ ANALYZING...")
        
        # Summary
        snapshot.summary = f"SPY {snapshot.spy.direction.value} | VIX {snapshot.vix.level:.1f} ({snapshot.vix.regime.value}) | RSI {snapshot.spy.rsi:.0f}"
    
    def _calc_ema(self, values: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(values) < period:
            return values[-1] if values else 0
        
        mult = 2 / (period + 1)
        ema = sum(values[:period]) / period
        
        for price in values[period:]:
            ema = (price - ema) * mult + ema
        
        return ema
    
    def _calc_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50.0
        
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _determine_trend(self, price: float, ema9: float, ema21: float, ema50: float) -> TrendDirection:
        """Determine trend direction"""
        if price > ema9 > ema21 > ema50:
            pct_above = (price - ema50) / ema50 * 100
            return TrendDirection.STRONG_UP if pct_above > 5 else TrendDirection.UP
        
        if price < ema9 < ema21 < ema50:
            pct_below = (ema50 - price) / ema50 * 100
            return TrendDirection.STRONG_DOWN if pct_below > 5 else TrendDirection.DOWN
        
        if price > ema21:
            return TrendDirection.WEAK_UP
        elif price < ema21:
            return TrendDirection.WEAK_DOWN
        
        return TrendDirection.NEUTRAL


def get_market_snapshot_dict(api=None) -> Dict:
    """Get market snapshot as dictionary for web interface"""
    analyzer = MarketAnalyzer(api)
    snapshot = analyzer.analyze()
    
    return {
        'timestamp': snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'regime': snapshot.regime.value,
        'headline': snapshot.headline,
        'summary': snapshot.summary,
        'overall_score': snapshot.overall_score,
        'risk_level': snapshot.risk_level,
        
        'vix': {
            'level': snapshot.vix.level,
            'change': snapshot.vix.change,
            'change_pct': snapshot.vix.change_pct,
            'regime': snapshot.vix.regime.value,
            'interpretation': snapshot.vix.interpretation,
            'percentile_30d': snapshot.vix.percentile_30d,
        },
        
        'spy': {
            'price': snapshot.spy.price,
            'change_pct': snapshot.spy.change_pct,
            'direction': snapshot.spy.direction.value,
            'rsi': snapshot.spy.rsi,
            'above_200sma': snapshot.spy.above_200sma,
            'ema_alignment': snapshot.spy.ema_alignment,
            'health_score': snapshot.spy.health_score,
        },
        
        'qqq': {
            'price': snapshot.qqq.price,
            'change_pct': snapshot.qqq.change_pct,
            'direction': snapshot.qqq.direction.value,
            'rsi': snapshot.qqq.rsi,
        },
        
        'breadth': {
            'ad_ratio': snapshot.breadth.ad_ratio,
            'pct_above_200sma': snapshot.breadth.pct_above_200sma,
            'score': snapshot.breadth.breadth_score,
            'interpretation': snapshot.breadth.interpretation,
        },
        
        'strategy': {
            'size_multiplier': snapshot.strategy.size_multiplier,
            'max_positions': snapshot.strategy.max_positions,
            'bias': snapshot.strategy.bias,
            'preferred_direction': snapshot.strategy.preferred_direction,
            'stop_multiplier': snapshot.strategy.stop_multiplier,
            'profit_taking': snapshot.strategy.profit_taking,
            'min_dte': snapshot.strategy.min_dte,
            'max_dte': snapshot.strategy.max_dte,
            'target_delta': snapshot.strategy.target_delta,
            'recommendations': snapshot.strategy.recommendations,
            'avoid': snapshot.strategy.avoid,
        },
    }
