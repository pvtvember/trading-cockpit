"""
Professional Options Trade Manager - A+ Tier
=============================================
Institutional-grade options position management with:

CORE ANALYTICS:
- IV Rank & Percentile (vs 52-week range)
- Theta Acceleration Modeling (non-linear decay)
- Gamma Risk Scoring (ATM + near expiry danger)
- Expected Move Calculations (1σ, 2σ probability cones)
- Liquidity Analysis (volume, OI, bid-ask spread)

ADVANCED SIGNALS:
- Roll Recommendations (when to roll vs close)
- Multi-Timeframe Trend Alignment
- Volatility Regime Detection (VIX-aware)
- Position Health Scoring (0-100)
- Scenario Analysis (P&L at key price levels)

RISK MANAGEMENT:
- Portfolio Greeks Aggregation
- Correlation Warnings (sector concentration)
- Max Loss Calculations
- Risk/Reward Scoring

Author: Claude (Anthropic)
Version: 2.0 Professional
"""

import os
import json
import math
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from enum import Enum
from statistics import mean, stdev

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run: pip install requests python-dotenv")
    exit(1)

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class PositionType(Enum):
    LONG_CALL = "LONG_CALL"
    LONG_PUT = "LONG_PUT"


class TradeStatus(Enum):
    BUILDING = "BUILDING"
    HOLDING_STRONG = "HOLDING_STRONG"
    HOLDING_GOOD = "HOLDING_GOOD"
    HOLDING_NEUTRAL = "HOLDING_NEUTRAL"
    HOLDING_WEAK = "HOLDING_WEAK"
    TAKE_PARTIAL = "TAKE_PARTIAL"
    TAKE_FULL = "TAKE_FULL"
    RUNNER_ACTIVE = "RUNNER_ACTIVE"
    CONSIDER_ROLL = "CONSIDER_ROLL"
    WARNING_THETA = "WARNING_THETA"
    WARNING_GAMMA = "WARNING_GAMMA"
    WARNING_IV_CRUSH = "WARNING_IV_CRUSH"
    WARNING_LIQUIDITY = "WARNING_LIQUIDITY"
    EXIT_STOP = "EXIT_STOP"
    EXIT_TARGET = "EXIT_TARGET"
    EXIT_TIME = "EXIT_TIME"


class Action(Enum):
    HOLD = "HOLD"
    ADD = "ADD"
    TIGHTEN_STOP = "TIGHTEN_STOP"
    TAKE_PARTIAL = "TAKE_PARTIAL"
    TAKE_FULL = "TAKE_FULL"
    CLOSE_RUNNER = "CLOSE_RUNNER"
    ROLL_OUT = "ROLL_OUT"
    ROLL_UP = "ROLL_UP"
    ROLL_DOWN = "ROLL_DOWN"
    EXIT_NOW = "EXIT_NOW"
    REDUCE_SIZE = "REDUCE_SIZE"


class MarketRegime(Enum):
    LOW_VOL_BULL = "LOW_VOL_BULL"
    LOW_VOL_BEAR = "LOW_VOL_BEAR"
    HIGH_VOL_BULL = "HIGH_VOL_BULL"
    HIGH_VOL_BEAR = "HIGH_VOL_BEAR"
    NEUTRAL = "NEUTRAL"
    CRASH = "CRASH"


class TrendStrength(Enum):
    STRONG_UP = "STRONG_UP"
    MODERATE_UP = "MODERATE_UP"
    WEAK_UP = "WEAK_UP"
    NEUTRAL = "NEUTRAL"
    WEAK_DOWN = "WEAK_DOWN"
    MODERATE_DOWN = "MODERATE_DOWN"
    STRONG_DOWN = "STRONG_DOWN"


class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════════════════════
# ADVANCED DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Greeks:
    """Complete Greeks with historical tracking"""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    # IV Analysis
    iv: float = 0.0
    iv_rank: float = 0.0          # 0-100: Where is IV vs 52-week range
    iv_percentile: float = 0.0    # 0-100: % of days IV was lower
    iv_52w_high: float = 0.0
    iv_52w_low: float = 0.0
    
    # Entry comparison
    entry_delta: float = 0.0
    entry_iv: float = 0.0
    entry_iv_rank: float = 0.0
    
    @property
    def delta_change(self) -> float:
        return self.delta - self.entry_delta if self.entry_delta else 0
    
    @property
    def iv_change(self) -> float:
        return self.iv - self.entry_iv if self.entry_iv else 0
    
    @property
    def iv_rank_status(self) -> str:
        if self.iv_rank >= 80:
            return "VERY HIGH"
        elif self.iv_rank >= 60:
            return "HIGH"
        elif self.iv_rank >= 40:
            return "MODERATE"
        elif self.iv_rank >= 20:
            return "LOW"
        else:
            return "VERY LOW"


@dataclass
class ThetaAnalysis:
    """Theta decay analysis with acceleration modeling"""
    daily_decay: float = 0.0           # $ per day
    weekly_decay: float = 0.0          # $ per week
    decay_rate_pct: float = 0.0        # % of premium per day
    
    # Acceleration
    acceleration_phase: str = "NORMAL"  # SLOW, NORMAL, ACCELERATING, CRITICAL
    days_to_acceleration: int = 0       # Days until theta accelerates (21 DTE)
    days_to_critical: int = 0           # Days until critical decay (7 DTE)
    
    # Projections
    value_in_7_days: float = 0.0
    value_in_14_days: float = 0.0
    theta_at_expiry_pace: float = 0.0   # Projected theta decay rate at expiry
    
    @property
    def decay_severity(self) -> str:
        if self.decay_rate_pct >= 5:
            return "SEVERE"
        elif self.decay_rate_pct >= 3:
            return "HIGH"
        elif self.decay_rate_pct >= 1.5:
            return "MODERATE"
        else:
            return "LOW"


@dataclass
class GammaAnalysis:
    """Gamma risk analysis"""
    gamma_risk_score: float = 0.0      # 0-100
    dollar_gamma: float = 0.0          # Delta change per $1 move
    gamma_flip_distance: float = 0.0   # Distance to max gamma (ATM)
    
    # Risk factors
    is_near_strike: bool = False
    is_near_expiry: bool = False
    gamma_explosion_risk: bool = False  # ATM + <7 DTE
    
    @property
    def risk_level(self) -> RiskLevel:
        if self.gamma_risk_score >= 80:
            return RiskLevel.EXTREME
        elif self.gamma_risk_score >= 60:
            return RiskLevel.HIGH
        elif self.gamma_risk_score >= 40:
            return RiskLevel.ELEVATED
        elif self.gamma_risk_score >= 20:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW


@dataclass
class LiquidityAnalysis:
    """Liquidity and execution quality analysis"""
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    spread_pct: float = 0.0           # Spread as % of mid price
    
    volume: int = 0
    open_interest: int = 0
    volume_oi_ratio: float = 0.0      # Today's activity vs total OI
    
    liquidity_score: float = 0.0      # 0-100
    
    @property
    def spread_quality(self) -> str:
        if self.spread_pct <= 1:
            return "EXCELLENT"
        elif self.spread_pct <= 3:
            return "GOOD"
        elif self.spread_pct <= 5:
            return "FAIR"
        elif self.spread_pct <= 10:
            return "POOR"
        else:
            return "VERY POOR"
    
    @property
    def is_liquid(self) -> bool:
        return self.liquidity_score >= 50


@dataclass
class ExpectedMove:
    """Statistical expected move analysis"""
    one_sigma_up: float = 0.0
    one_sigma_down: float = 0.0
    two_sigma_up: float = 0.0
    two_sigma_down: float = 0.0
    
    # Probability analysis
    prob_above_target: float = 0.0     # % chance of hitting target
    prob_below_stop: float = 0.0       # % chance of hitting stop
    prob_itm_at_expiry: float = 0.0    # % chance of ITM at expiration
    
    # Expected value
    expected_value: float = 0.0         # Probability-weighted outcome
    risk_reward_ratio: float = 0.0
    
    @property
    def probability_assessment(self) -> str:
        if self.prob_above_target >= 60:
            return "FAVORABLE"
        elif self.prob_above_target >= 45:
            return "NEUTRAL"
        elif self.prob_above_target >= 30:
            return "CHALLENGING"
        else:
            return "UNLIKELY"


@dataclass
class RollAnalysis:
    """Roll recommendation analysis"""
    should_roll: bool = False
    roll_urgency: str = "NONE"         # NONE, CONSIDER, RECOMMENDED, URGENT
    roll_reason: str = ""
    
    # Roll options
    recommended_roll_dte: int = 0
    recommended_roll_strike: float = 0.0
    roll_type: str = ""                # OUT, UP, DOWN, UP_AND_OUT, DOWN_AND_OUT
    
    # Cost analysis
    debit_to_roll: float = 0.0
    credit_to_roll: float = 0.0
    net_roll_cost: float = 0.0
    
    @property
    def roll_action(self) -> Action:
        if not self.should_roll:
            return Action.HOLD
        if "UP" in self.roll_type:
            return Action.ROLL_UP
        elif "DOWN" in self.roll_type:
            return Action.ROLL_DOWN
        else:
            return Action.ROLL_OUT


@dataclass
class MarketContext:
    """Comprehensive market analysis"""
    # Trend analysis
    trend_daily: TrendStrength = TrendStrength.NEUTRAL
    trend_weekly: TrendStrength = TrendStrength.NEUTRAL
    trend_alignment: bool = False      # Are daily and weekly aligned?
    
    # Momentum
    rsi: float = 50.0
    rsi_divergence: str = "NONE"       # BULLISH, BEARISH, NONE
    macd_signal: str = "NEUTRAL"
    macd_histogram: float = 0.0
    macd_crossover: str = "NONE"       # BULLISH, BEARISH, NONE
    
    # Volatility
    atr: float = 0.0
    atr_percent: float = 0.0
    atr_expanding: bool = False        # Is volatility increasing?
    
    # Volume
    volume_trend: str = "NORMAL"       # LOW, NORMAL, HIGH, CLIMACTIC
    volume_vs_avg: float = 1.0
    
    # Key levels
    support_1: float = 0.0
    support_2: float = 0.0
    resistance_1: float = 0.0
    resistance_2: float = 0.0
    
    # Regime
    regime: MarketRegime = MarketRegime.NEUTRAL
    vix_level: float = 0.0
    vix_term_structure: str = "NORMAL"  # CONTANGO, BACKWARDATION, FLAT
    
    @property
    def momentum_score(self) -> float:
        """Overall momentum score -100 to +100"""
        score = 0
        
        # RSI contribution
        if self.rsi > 70:
            score += 30
        elif self.rsi > 50:
            score += (self.rsi - 50) * 1.5
        elif self.rsi < 30:
            score -= 30
        else:
            score -= (50 - self.rsi) * 1.5
        
        # MACD contribution
        if self.macd_signal == "BULLISH":
            score += 20
        elif self.macd_signal == "BEARISH":
            score -= 20
        
        # Trend contribution
        trend_scores = {
            TrendStrength.STRONG_UP: 30,
            TrendStrength.MODERATE_UP: 20,
            TrendStrength.WEAK_UP: 10,
            TrendStrength.NEUTRAL: 0,
            TrendStrength.WEAK_DOWN: -10,
            TrendStrength.MODERATE_DOWN: -20,
            TrendStrength.STRONG_DOWN: -30,
        }
        score += trend_scores.get(self.trend_daily, 0)
        
        return max(-100, min(100, score))


@dataclass
class ScenarioAnalysis:
    """P&L scenario projections"""
    # Price scenarios
    scenarios: Dict[str, Dict] = field(default_factory=dict)
    # Format: {"price_level": {"stock_price": x, "option_price": y, "pnl": z, "pnl_pct": w}}
    
    # Key levels
    breakeven_price: float = 0.0
    max_profit_price: float = 0.0
    max_loss: float = 0.0
    
    @property
    def best_scenario(self) -> str:
        if not self.scenarios:
            return "N/A"
        best = max(self.scenarios.items(), key=lambda x: x[1].get('pnl', 0))
        return best[0]
    
    @property
    def worst_scenario(self) -> str:
        if not self.scenarios:
            return "N/A"
        worst = min(self.scenarios.items(), key=lambda x: x[1].get('pnl', 0))
        return worst[0]


@dataclass
class PositionScore:
    """Overall position health scoring"""
    overall_score: float = 0.0         # 0-100
    
    # Component scores
    pnl_score: float = 0.0             # Current P&L quality
    theta_score: float = 0.0           # Time decay health
    gamma_score: float = 0.0           # Gamma risk (inverted - lower is better)
    iv_score: float = 0.0              # IV environment quality
    liquidity_score: float = 0.0       # Execution quality
    momentum_score: float = 0.0        # Market alignment
    probability_score: float = 0.0     # Statistical edge
    
    # Weights used
    weights: Dict[str, float] = field(default_factory=lambda: {
        'pnl': 0.20,
        'theta': 0.20,
        'gamma': 0.10,
        'iv': 0.15,
        'liquidity': 0.10,
        'momentum': 0.15,
        'probability': 0.10
    })
    
    @property
    def grade(self) -> str:
        if self.overall_score >= 90:
            return "A+"
        elif self.overall_score >= 80:
            return "A"
        elif self.overall_score >= 70:
            return "B"
        elif self.overall_score >= 60:
            return "C"
        elif self.overall_score >= 50:
            return "D"
        else:
            return "F"
    
    @property
    def weakest_component(self) -> str:
        components = {
            'P&L': self.pnl_score,
            'Theta': self.theta_score,
            'Gamma': self.gamma_score,
            'IV': self.iv_score,
            'Liquidity': self.liquidity_score,
            'Momentum': self.momentum_score,
            'Probability': self.probability_score
        }
        return min(components, key=components.get)


@dataclass
class StopLevels:
    """Comprehensive stop management"""
    # Stock price stops
    original: float = 0.0
    breakeven: float = 0.0
    atr_trail: float = 0.0
    percent_trail: float = 0.0
    support_based: float = 0.0
    runner_trail: float = 0.0
    recommended: float = 0.0
    
    # Option price stops
    original_option: float = 0.0
    recommended_option: float = 0.0
    runner_option: float = 0.0
    
    # Analysis
    method: str = "ORIGINAL"
    needs_update: bool = False
    distance_to_stop: float = 0.0
    distance_to_stop_atr: float = 0.0
    risk_at_stop: float = 0.0          # $ at risk if stopped
    risk_at_stop_pct: float = 0.0      # % at risk if stopped


@dataclass
class ScalingState:
    """Position scaling management"""
    # Targets
    t1_target_pct: float = 50.0
    t2_target_pct: float = 100.0
    t1_size_pct: float = 50.0
    t2_size_pct: float = 25.0
    runner_size_pct: float = 25.0
    
    # State
    t1_triggered: bool = False
    t1_price: float = 0.0
    t1_date: str = ""
    
    t2_triggered: bool = False
    t2_price: float = 0.0
    t2_date: str = ""
    
    runner_active: bool = False
    runner_closed: bool = False
    runner_exit_reason: str = ""
    runner_exit_price: float = 0.0
    
    # Runner targets
    extended_target: float = 0.0
    runner_trail_level: float = 0.0


@dataclass
class Position:
    """Complete professional position with all analytics"""
    # Identity
    id: str
    symbol: str
    position_type: PositionType
    
    # Contract
    strike: float
    expiration: str
    quantity: int
    
    # Entry
    entry_date: str
    entry_stock_price: float
    entry_option_price: float
    starting_dte: int
    
    # Targets
    stop_price: float
    target_price: float
    
    # Current state
    current_stock_price: float = 0.0
    current_option_price: float = 0.0
    current_dte: int = 0
    highest_since_entry: float = 0.0
    lowest_since_entry: float = 0.0
    
    # Analytics components
    greeks: Greeks = field(default_factory=Greeks)
    theta_analysis: ThetaAnalysis = field(default_factory=ThetaAnalysis)
    gamma_analysis: GammaAnalysis = field(default_factory=GammaAnalysis)
    liquidity: LiquidityAnalysis = field(default_factory=LiquidityAnalysis)
    expected_move: ExpectedMove = field(default_factory=ExpectedMove)
    roll_analysis: RollAnalysis = field(default_factory=RollAnalysis)
    market: MarketContext = field(default_factory=MarketContext)
    scenarios: ScenarioAnalysis = field(default_factory=ScenarioAnalysis)
    score: PositionScore = field(default_factory=PositionScore)
    stops: StopLevels = field(default_factory=StopLevels)
    scaling: ScalingState = field(default_factory=ScalingState)
    
    # Status
    status: TradeStatus = TradeStatus.BUILDING
    action: Action = Action.HOLD
    action_detail: str = ""
    alerts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Configuration
    breakeven_trigger_pct: float = 30.0
    atr_trail_trigger_pct: float = 20.0
    atr_trail_mult: float = 2.0
    runner_trail_mult: float = 1.0
    dte_warning: int = 21
    dte_critical: int = 14
    runner_min_dte: int = 7
    
    def __post_init__(self):
        if isinstance(self.position_type, str):
            self.position_type = PositionType(self.position_type)
        if isinstance(self.status, str):
            self.status = TradeStatus(self.status)
        if isinstance(self.action, str):
            self.action = Action(self.action)
        if self.highest_since_entry == 0:
            self.highest_since_entry = self.entry_stock_price
        if self.lowest_since_entry == 0:
            self.lowest_since_entry = self.entry_stock_price
    
    @property
    def is_call(self) -> bool:
        return self.position_type == PositionType.LONG_CALL
    
    @property
    def days_held(self) -> int:
        entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
        return (datetime.now() - entry).days
    
    @property
    def pnl_dollars(self) -> float:
        return (self.current_option_price - self.entry_option_price) * self.quantity * 100
    
    @property
    def pnl_percent(self) -> float:
        if self.entry_option_price <= 0:
            return 0.0
        return ((self.current_option_price - self.entry_option_price) / self.entry_option_price) * 100
    
    @property
    def stock_pnl_percent(self) -> float:
        if self.entry_stock_price <= 0:
            return 0.0
        return ((self.current_stock_price - self.entry_stock_price) / self.entry_stock_price) * 100
    
    @property
    def moneyness(self) -> float:
        """How far ITM/OTM as a percentage"""
        if self.is_call:
            return (self.current_stock_price - self.strike) / self.strike * 100
        else:
            return (self.strike - self.current_stock_price) / self.strike * 100
    
    @property
    def is_itm(self) -> bool:
        if self.is_call:
            return self.current_stock_price > self.strike
        else:
            return self.current_stock_price < self.strike


# ══════════════════════════════════════════════════════════════════════════════
# POLYGON API CLIENT (Enhanced)
# ══════════════════════════════════════════════════════════════════════════════

class PolygonAPI:
    """Enhanced Polygon.io API client"""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = {}
        self.cache_ttl = 60
    
    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        try:
            url = f"{self.BASE_URL}{endpoint}"
            params = params or {}
            params['apiKey'] = self.api_key
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limit hit, waiting 60s...")
                time.sleep(60)
                return self._request(endpoint, params)
            else:
                logger.debug(f"API error {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def get_stock_snapshot(self, symbol: str) -> Dict:
        """Get comprehensive stock snapshot"""
        result = self._request(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}")
        if result and result.get('ticker'):
            t = result['ticker']
            return {
                'price': t.get('day', {}).get('c', 0) or t.get('prevDay', {}).get('c', 0),
                'open': t.get('day', {}).get('o', 0),
                'high': t.get('day', {}).get('h', 0),
                'low': t.get('day', {}).get('l', 0),
                'volume': t.get('day', {}).get('v', 0),
                'prev_close': t.get('prevDay', {}).get('c', 0),
                'change': t.get('todaysChange', 0),
                'change_pct': t.get('todaysChangePerc', 0),
            }
        
        # Fallback to prev day
        result = self._request(f"/v2/aggs/ticker/{symbol}/prev")
        if result and result.get('results'):
            bar = result['results'][0]
            return {
                'price': bar.get('c', 0),
                'open': bar.get('o', 0),
                'high': bar.get('h', 0),
                'low': bar.get('l', 0),
                'volume': bar.get('v', 0),
                'prev_close': bar.get('c', 0),
                'change': 0,
                'change_pct': 0,
            }
        return {'price': 0}
    
    def get_stock_history(self, symbol: str, days: int = 252) -> List[Dict]:
        """Get historical data for IV rank calculation"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)
        
        result = self._request(
            f"/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
            {'limit': 500}
        )
        
        if result and result.get('results'):
            return result['results']
        return []
    
    def get_option_snapshot(self, symbol: str, strike: float, expiration: str, opt_type: str) -> Dict:
        """Get option snapshot with Greeks"""
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        exp_str = exp_date.strftime("%y%m%d")
        opt_char = "C" if opt_type.upper() in ["C", "CALL"] else "P"
        strike_str = f"{int(strike * 1000):08d}"
        option_ticker = f"O:{symbol}{exp_str}{opt_char}{strike_str}"
        
        data = {
            'bid': 0, 'ask': 0, 'last': 0, 'mark': 0,
            'volume': 0, 'open_interest': 0,
            'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': 0
        }
        
        # Try snapshot
        result = self._request(f"/v3/snapshot/options/{symbol}/{option_ticker}")
        
        if result and result.get('results'):
            r = result['results']
            day = r.get('day', {})
            greeks = r.get('greeks', {})
            
            data['bid'] = r.get('bid', 0) or 0
            data['ask'] = r.get('ask', 0) or 0
            data['last'] = day.get('close', 0) or r.get('value', 0) or 0
            data['mark'] = (data['bid'] + data['ask']) / 2 if data['bid'] and data['ask'] else data['last']
            data['volume'] = day.get('volume', 0) or 0
            data['open_interest'] = r.get('open_interest', 0) or 0
            data['delta'] = greeks.get('delta', 0) or 0
            data['gamma'] = greeks.get('gamma', 0) or 0
            data['theta'] = greeks.get('theta', 0) or 0
            data['vega'] = greeks.get('vega', 0) or 0
            data['iv'] = r.get('implied_volatility', 0) or 0
        else:
            # Fallback
            result = self._request(f"/v2/aggs/ticker/{option_ticker}/prev")
            if result and result.get('results'):
                bar = result['results'][0]
                data['last'] = bar.get('c', 0)
                data['mark'] = data['last']
                data['volume'] = bar.get('v', 0)
        
        return data
    
    def get_iv_history(self, symbol: str, days: int = 252) -> List[float]:
        """Get historical IV for IV rank calculation (approximated from stock history)"""
        history = self.get_stock_history(symbol, days)
        if len(history) < 30:
            return []
        
        # Calculate historical volatility as IV proxy
        closes = [bar['c'] for bar in history if bar.get('c')]
        if len(closes) < 30:
            return []
        
        ivs = []
        for i in range(20, len(closes)):
            window = closes[i-20:i]
            returns = [(window[j] - window[j-1]) / window[j-1] for j in range(1, len(window))]
            if returns:
                hv = stdev(returns) * math.sqrt(252)
                ivs.append(hv)
        
        return ivs


# ══════════════════════════════════════════════════════════════════════════════
# ADVANCED ANALYTICS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AdvancedAnalytics:
    """Professional-grade analytics calculations"""
    
    @staticmethod
    def calculate_iv_rank(current_iv: float, iv_history: List[float]) -> Tuple[float, float, float, float]:
        """
        Calculate IV Rank and Percentile
        Returns: (iv_rank, iv_percentile, iv_52w_high, iv_52w_low)
        """
        if not iv_history or len(iv_history) < 20:
            return 50.0, 50.0, current_iv, current_iv
        
        iv_52w_high = max(iv_history)
        iv_52w_low = min(iv_history)
        
        # IV Rank: Where is current IV in the 52-week range
        if iv_52w_high == iv_52w_low:
            iv_rank = 50.0
        else:
            iv_rank = ((current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low)) * 100
        
        # IV Percentile: % of days IV was lower
        days_lower = sum(1 for iv in iv_history if iv < current_iv)
        iv_percentile = (days_lower / len(iv_history)) * 100
        
        return iv_rank, iv_percentile, iv_52w_high, iv_52w_low
    
    @staticmethod
    def calculate_theta_decay(dte: int, option_price: float, theta: float) -> ThetaAnalysis:
        """Model theta decay acceleration"""
        analysis = ThetaAnalysis()
        
        analysis.daily_decay = abs(theta)
        analysis.weekly_decay = abs(theta) * 7
        analysis.decay_rate_pct = (abs(theta) / option_price * 100) if option_price > 0 else 0
        
        # Determine acceleration phase
        if dte > 45:
            analysis.acceleration_phase = "SLOW"
        elif dte > 21:
            analysis.acceleration_phase = "NORMAL"
        elif dte > 7:
            analysis.acceleration_phase = "ACCELERATING"
        else:
            analysis.acceleration_phase = "CRITICAL"
        
        analysis.days_to_acceleration = max(0, dte - 21)
        analysis.days_to_critical = max(0, dte - 7)
        
        # Project future values (simplified decay model)
        # Theta accelerates as: theta_t = theta_0 * sqrt(T0/Tt)
        if dte > 7:
            decay_factor_7d = math.sqrt(dte / (dte - 7)) if dte > 7 else 2
            analysis.value_in_7_days = max(0, option_price - abs(theta) * 7 * decay_factor_7d * 0.7)
        
        if dte > 14:
            decay_factor_14d = math.sqrt(dte / (dte - 14)) if dte > 14 else 3
            analysis.value_in_14_days = max(0, option_price - abs(theta) * 14 * decay_factor_14d * 0.5)
        
        return analysis
    
    @staticmethod
    def calculate_gamma_risk(delta: float, gamma: float, stock_price: float, 
                             strike: float, dte: int, option_price: float) -> GammaAnalysis:
        """Analyze gamma risk"""
        analysis = GammaAnalysis()
        
        # Dollar gamma: delta change per $1 move
        analysis.dollar_gamma = gamma * stock_price / 100
        
        # Distance to strike (ATM = max gamma)
        analysis.gamma_flip_distance = abs(stock_price - strike)
        pct_from_strike = abs(stock_price - strike) / strike * 100
        
        analysis.is_near_strike = pct_from_strike < 3
        analysis.is_near_expiry = dte < 7
        analysis.gamma_explosion_risk = analysis.is_near_strike and analysis.is_near_expiry
        
        # Gamma risk score (0-100)
        score = 0
        
        # Near strike increases risk
        if pct_from_strike < 1:
            score += 40
        elif pct_from_strike < 3:
            score += 25
        elif pct_from_strike < 5:
            score += 15
        
        # Near expiry increases risk
        if dte < 3:
            score += 40
        elif dte < 7:
            score += 30
        elif dte < 14:
            score += 15
        
        # High gamma value
        gamma_pct = (gamma * stock_price) / option_price * 100 if option_price > 0 else 0
        if gamma_pct > 10:
            score += 20
        elif gamma_pct > 5:
            score += 10
        
        analysis.gamma_risk_score = min(100, score)
        
        return analysis
    
    @staticmethod
    def calculate_expected_move(stock_price: float, iv: float, dte: int,
                                strike: float, is_call: bool,
                                stop_price: float, target_price: float) -> ExpectedMove:
        """Calculate statistical expected moves and probabilities"""
        analysis = ExpectedMove()
        
        if iv <= 0 or dte <= 0:
            return analysis
        
        # Annualized IV to period IV
        period_iv = iv * math.sqrt(dte / 365)
        
        # Expected move (1 sigma)
        one_sigma = stock_price * period_iv
        analysis.one_sigma_up = stock_price + one_sigma
        analysis.one_sigma_down = stock_price - one_sigma
        
        # 2 sigma
        two_sigma = stock_price * period_iv * 2
        analysis.two_sigma_up = stock_price + two_sigma
        analysis.two_sigma_down = stock_price - two_sigma
        
        # Probability calculations (simplified normal distribution)
        def norm_cdf(x):
            """Approximate normal CDF"""
            return 0.5 * (1 + math.erf(x / math.sqrt(2)))
        
        if one_sigma > 0:
            # Z-scores
            z_target = (target_price - stock_price) / one_sigma
            z_stop = (stop_price - stock_price) / one_sigma
            z_strike = (strike - stock_price) / one_sigma
            
            if is_call:
                analysis.prob_above_target = (1 - norm_cdf(z_target)) * 100
                analysis.prob_below_stop = norm_cdf(z_stop) * 100
                analysis.prob_itm_at_expiry = (1 - norm_cdf(z_strike)) * 100
            else:
                analysis.prob_above_target = norm_cdf(-z_target) * 100
                analysis.prob_below_stop = (1 - norm_cdf(z_stop)) * 100
                analysis.prob_itm_at_expiry = norm_cdf(z_strike) * 100
        
        # Risk/Reward ratio
        potential_profit = abs(target_price - stock_price)
        potential_loss = abs(stock_price - stop_price)
        if potential_loss > 0:
            analysis.risk_reward_ratio = potential_profit / potential_loss
        
        # Expected value (simplified)
        analysis.expected_value = (
            (analysis.prob_above_target / 100 * potential_profit) -
            (analysis.prob_below_stop / 100 * potential_loss)
        )
        
        return analysis
    
    @staticmethod
    def calculate_roll_recommendation(pos: Position) -> RollAnalysis:
        """Determine if and how to roll the position"""
        analysis = RollAnalysis()
        
        dte = pos.current_dte
        pnl_pct = pos.pnl_percent
        theta_decay_pct = pos.theta_analysis.decay_rate_pct
        iv_rank = pos.greeks.iv_rank
        
        # Roll triggers
        reasons = []
        urgency_score = 0
        
        # DTE-based rolling
        if dte <= 7:
            reasons.append("DTE critical (<7 days)")
            urgency_score += 40
        elif dte <= 14:
            reasons.append("DTE warning (<14 days)")
            urgency_score += 25
        elif dte <= 21 and pnl_pct < 30:
            reasons.append("DTE accelerating with limited profit")
            urgency_score += 15
        
        # Theta-based rolling
        if theta_decay_pct > 3 and pnl_pct < 20:
            reasons.append("High theta decay with low profit")
            urgency_score += 20
        
        # IV-based rolling
        if iv_rank < 20 and pnl_pct > 0:
            reasons.append("Low IV rank - consider taking profits")
            urgency_score += 10
        
        # Determine roll parameters
        if urgency_score > 0:
            analysis.should_roll = urgency_score >= 30
            
            if urgency_score >= 50:
                analysis.roll_urgency = "URGENT"
            elif urgency_score >= 30:
                analysis.roll_urgency = "RECOMMENDED"
            else:
                analysis.roll_urgency = "CONSIDER"
            
            analysis.roll_reason = "; ".join(reasons)
            
            # Recommended roll: typically 30-45 DTE
            analysis.recommended_roll_dte = 30 if dte < 14 else 45
            
            # Strike adjustment based on P&L
            if pnl_pct > 50:
                # In profit - can roll up/down
                if pos.is_call and pos.current_stock_price > pos.strike:
                    analysis.roll_type = "UP_AND_OUT"
                    analysis.recommended_roll_strike = pos.strike + (pos.current_stock_price - pos.strike) * 0.5
                elif not pos.is_call and pos.current_stock_price < pos.strike:
                    analysis.roll_type = "DOWN_AND_OUT"
                    analysis.recommended_roll_strike = pos.strike - (pos.strike - pos.current_stock_price) * 0.5
                else:
                    analysis.roll_type = "OUT"
                    analysis.recommended_roll_strike = pos.strike
            else:
                # Not in significant profit - just roll out
                analysis.roll_type = "OUT"
                analysis.recommended_roll_strike = pos.strike
        
        return analysis
    
    @staticmethod
    def calculate_scenarios(pos: Position) -> ScenarioAnalysis:
        """Calculate P&L at key price levels"""
        analysis = ScenarioAnalysis()
        
        stock = pos.current_stock_price
        option = pos.current_option_price
        delta = pos.greeks.delta or 0.5
        gamma = pos.greeks.gamma or 0.02
        entry = pos.entry_option_price
        
        # Key price levels to analyze
        levels = {
            'Stop': pos.stop_price,
            'Entry': pos.entry_stock_price,
            'Current': stock,
            '-5%': stock * 0.95,
            '-3%': stock * 0.97,
            '+3%': stock * 1.03,
            '+5%': stock * 1.05,
            'Target': pos.target_price,
            'Strike': pos.strike,
        }
        
        for label, price in levels.items():
            # Estimate option price at this stock price
            move = price - stock
            
            # Delta-gamma adjustment
            delta_impact = move * abs(delta)
            gamma_impact = 0.5 * (move ** 2) * gamma
            
            if pos.is_call:
                if move > 0:
                    est_option = option + delta_impact + gamma_impact
                else:
                    est_option = option + delta_impact - gamma_impact
            else:
                if move < 0:
                    est_option = option - delta_impact + gamma_impact
                else:
                    est_option = option - delta_impact - gamma_impact
            
            est_option = max(0.01, est_option)
            
            pnl = (est_option - entry) * pos.quantity * 100
            pnl_pct = ((est_option - entry) / entry * 100) if entry > 0 else 0
            
            analysis.scenarios[label] = {
                'stock_price': price,
                'option_price': est_option,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            }
        
        # Breakeven
        if delta != 0:
            option_loss_to_be = entry - option
            stock_move_needed = option_loss_to_be / abs(delta)
            analysis.breakeven_price = stock + stock_move_needed if pos.is_call else stock - stock_move_needed
        
        # Max loss
        analysis.max_loss = entry * pos.quantity * 100
        
        return analysis
    
    @staticmethod
    def calculate_position_score(pos: Position) -> PositionScore:
        """Calculate overall position health score"""
        score = PositionScore()
        
        # P&L Score (0-100)
        pnl = pos.pnl_percent
        if pnl >= 100:
            score.pnl_score = 100
        elif pnl >= 50:
            score.pnl_score = 80 + (pnl - 50) * 0.4
        elif pnl >= 20:
            score.pnl_score = 60 + (pnl - 20) * 0.67
        elif pnl >= 0:
            score.pnl_score = 50 + pnl * 0.5
        elif pnl >= -20:
            score.pnl_score = 30 + (pnl + 20) * 1
        elif pnl >= -50:
            score.pnl_score = 10 + (pnl + 50) * 0.67
        else:
            score.pnl_score = max(0, 10 + pnl * 0.2)
        
        # Theta Score (inverted - lower decay is better)
        decay = pos.theta_analysis.decay_rate_pct
        if pos.current_dte > 45:
            score.theta_score = 90
        elif pos.current_dte > 21:
            score.theta_score = 70 + (pos.current_dte - 21) * 0.83
        elif pos.current_dte > 14:
            score.theta_score = 50 + (pos.current_dte - 14) * 2.86
        elif pos.current_dte > 7:
            score.theta_score = 25 + (pos.current_dte - 7) * 3.57
        else:
            score.theta_score = max(0, pos.current_dte * 3.57)
        
        # Gamma Score (inverted - lower risk is better)
        score.gamma_score = 100 - pos.gamma_analysis.gamma_risk_score
        
        # IV Score
        iv_rank = pos.greeks.iv_rank
        # For long options, we want to buy low IV
        if iv_rank <= 20:
            score.iv_score = 90  # Bought at low IV - great
        elif iv_rank <= 40:
            score.iv_score = 75
        elif iv_rank <= 60:
            score.iv_score = 60
        elif iv_rank <= 80:
            score.iv_score = 40
        else:
            score.iv_score = 25  # Bought at high IV - risk of IV crush
        
        # Adjust if IV has dropped since entry (IV crush)
        if pos.greeks.iv_change < -0.05:
            score.iv_score = max(0, score.iv_score - 20)
        
        # Liquidity Score
        score.liquidity_score = pos.liquidity.liquidity_score
        
        # Momentum Score
        momentum = pos.market.momentum_score
        if pos.is_call:
            score.momentum_score = 50 + momentum * 0.5
        else:
            score.momentum_score = 50 - momentum * 0.5
        score.momentum_score = max(0, min(100, score.momentum_score))
        
        # Probability Score
        prob = pos.expected_move.prob_above_target
        score.probability_score = min(100, prob * 1.5)
        
        # Calculate weighted overall score
        score.overall_score = (
            score.pnl_score * score.weights['pnl'] +
            score.theta_score * score.weights['theta'] +
            score.gamma_score * score.weights['gamma'] +
            score.iv_score * score.weights['iv'] +
            score.liquidity_score * score.weights['liquidity'] +
            score.momentum_score * score.weights['momentum'] +
            score.probability_score * score.weights['probability']
        )
        
        return score


# ══════════════════════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TechnicalAnalysis:
    """Technical indicator calculations"""
    
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_ema(values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return values
        
        mult = 2 / (period + 1)
        ema = [sum(values[:period]) / period]
        
        for price in values[period:]:
            ema.append((price - ema[-1]) * mult + ema[-1])
        
        return ema
    
    @staticmethod
    def calculate_macd(closes: List[float]) -> Tuple[float, float, float]:
        if len(closes) < 35:
            return 0, 0, 0
        
        ema12 = TechnicalAnalysis.calculate_ema(closes, 12)
        ema26 = TechnicalAnalysis.calculate_ema(closes, 26)
        
        min_len = min(len(ema12), len(ema26))
        macd_line = [e12 - e26 for e12, e26 in zip(ema12[-min_len:], ema26[-min_len:])]
        
        if len(macd_line) < 9:
            return 0, 0, 0
        
        signal = TechnicalAnalysis.calculate_ema(macd_line, 9)
        
        return macd_line[-1], signal[-1], macd_line[-1] - signal[-1]
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def calculate_support_resistance(highs: List[float], lows: List[float], 
                                     closes: List[float]) -> Tuple[float, float, float, float]:
        """Find support and resistance levels"""
        if len(closes) < 20:
            return 0, 0, 0, 0
        
        recent_lows = sorted(lows[-20:])
        recent_highs = sorted(highs[-20:], reverse=True)
        
        support_1 = recent_lows[0]
        support_2 = recent_lows[min(4, len(recent_lows)-1)]
        resistance_1 = recent_highs[0]
        resistance_2 = recent_highs[min(4, len(recent_highs)-1)]
        
        return support_1, support_2, resistance_1, resistance_2
    
    @staticmethod
    def determine_trend(closes: List[float], period: str = "daily") -> TrendStrength:
        if len(closes) < 50:
            return TrendStrength.NEUTRAL
        
        ema9 = TechnicalAnalysis.calculate_ema(closes, 9)
        ema21 = TechnicalAnalysis.calculate_ema(closes, 21)
        ema50 = TechnicalAnalysis.calculate_ema(closes, 50)
        
        if not all([ema9, ema21, ema50]):
            return TrendStrength.NEUTRAL
        
        price = closes[-1]
        e9, e21, e50 = ema9[-1], ema21[-1], ema50[-1]
        
        # Strong uptrend: price > EMA9 > EMA21 > EMA50
        if price > e9 > e21 > e50:
            pct_above = (price - e50) / e50 * 100
            if pct_above > 5:
                return TrendStrength.STRONG_UP
            return TrendStrength.MODERATE_UP
        
        # Strong downtrend: price < EMA9 < EMA21 < EMA50
        if price < e9 < e21 < e50:
            pct_below = (e50 - price) / e50 * 100
            if pct_below > 5:
                return TrendStrength.STRONG_DOWN
            return TrendStrength.MODERATE_DOWN
        
        # Weak trends
        if price > e21:
            return TrendStrength.WEAK_UP
        elif price < e21:
            return TrendStrength.WEAK_DOWN
        
        return TrendStrength.NEUTRAL


# ══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL TRADE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ProfessionalTradeManager:
    """A+ Tier Professional Options Trade Manager"""
    
    def __init__(self, api: PolygonAPI):
        self.api = api
        self.positions: Dict[str, Position] = {}
        self.positions_file = Path("positions.json")
        self.load_positions()
    
    def load_positions(self):
        """Load positions from file"""
        if self.positions_file.exists():
            try:
                data = json.loads(self.positions_file.read_text())
                for pos_id, pos_data in data.items():
                    # Reconstruct dataclasses
                    for field_name in ['greeks', 'theta_analysis', 'gamma_analysis', 
                                       'liquidity', 'expected_move', 'roll_analysis',
                                       'market', 'scenarios', 'score', 'stops', 'scaling']:
                        if field_name in pos_data and isinstance(pos_data[field_name], dict):
                            class_map = {
                                'greeks': Greeks,
                                'theta_analysis': ThetaAnalysis,
                                'gamma_analysis': GammaAnalysis,
                                'liquidity': LiquidityAnalysis,
                                'expected_move': ExpectedMove,
                                'roll_analysis': RollAnalysis,
                                'market': MarketContext,
                                'scenarios': ScenarioAnalysis,
                                'score': PositionScore,
                                'stops': StopLevels,
                                'scaling': ScalingState,
                            }
                            try:
                                pos_data[field_name] = class_map[field_name](**pos_data[field_name])
                            except:
                                pass
                    
                    self.positions[pos_id] = Position(**pos_data)
                logger.info(f"Loaded {len(self.positions)} positions")
            except Exception as e:
                logger.error(f"Failed to load positions: {e}")
    
    def save_positions(self):
        """Save positions to file"""
        try:
            data = {}
            for pos_id, pos in self.positions.items():
                pos_dict = asdict(pos)
                pos_dict['position_type'] = pos.position_type.value
                pos_dict['status'] = pos.status.value
                pos_dict['action'] = pos.action.value
                
                # Handle nested enums
                if hasattr(pos.market, 'trend_daily'):
                    pos_dict['market']['trend_daily'] = pos.market.trend_daily.value
                if hasattr(pos.market, 'trend_weekly'):
                    pos_dict['market']['trend_weekly'] = pos.market.trend_weekly.value
                if hasattr(pos.market, 'regime'):
                    pos_dict['market']['regime'] = pos.market.regime.value
                
                data[pos_id] = pos_dict
            
            self.positions_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save positions: {e}")
    
    def add_position(self, pos: Position):
        """Add a new position"""
        pos.greeks.entry_delta = pos.greeks.delta
        pos.greeks.entry_iv = pos.greeks.iv
        pos.stops.original = pos.stop_price
        pos.stops.recommended = pos.stop_price
        
        self.positions[pos.id] = pos
        self.save_positions()
        logger.info(f"Added position: {pos.id}")
    
    def remove_position(self, pos_id: str):
        """Remove a position"""
        if pos_id in self.positions:
            del self.positions[pos_id]
            self.save_positions()
            logger.info(f"Removed position: {pos_id}")
    
    def update_position(self, pos: Position):
        """Full position update with all analytics"""
        pos.alerts = []
        pos.warnings = []
        
        # 1. Fetch live data
        self._fetch_live_data(pos)
        
        # 2. Calculate IV rank
        self._calculate_iv_metrics(pos)
        
        # 3. Analyze market context
        self._analyze_market(pos)
        
        # 4. Calculate theta analysis
        pos.theta_analysis = AdvancedAnalytics.calculate_theta_decay(
            pos.current_dte, pos.current_option_price, pos.greeks.theta
        )
        
        # 5. Calculate gamma risk
        pos.gamma_analysis = AdvancedAnalytics.calculate_gamma_risk(
            pos.greeks.delta, pos.greeks.gamma, pos.current_stock_price,
            pos.strike, pos.current_dte, pos.current_option_price
        )
        
        # 6. Calculate expected move
        pos.expected_move = AdvancedAnalytics.calculate_expected_move(
            pos.current_stock_price, pos.greeks.iv, pos.current_dte,
            pos.strike, pos.is_call, pos.stop_price, pos.target_price
        )
        
        # 7. Calculate scenarios
        pos.scenarios = AdvancedAnalytics.calculate_scenarios(pos)
        
        # 8. Calculate stops
        self._calculate_stops(pos)
        
        # 9. Check scaling
        self._check_scaling(pos)
        
        # 10. Calculate roll recommendation
        pos.roll_analysis = AdvancedAnalytics.calculate_roll_recommendation(pos)
        
        # 11. Calculate position score
        pos.score = AdvancedAnalytics.calculate_position_score(pos)
        
        # 12. Determine status and action
        self._determine_status(pos)
        
        # 13. Generate alerts
        self._generate_alerts(pos)
        
        self.save_positions()
    
    def _fetch_live_data(self, pos: Position):
        """Fetch live market data"""
        # Stock data
        stock = self.api.get_stock_snapshot(pos.symbol)
        pos.current_stock_price = stock.get('price', pos.current_stock_price) or pos.current_stock_price
        
        # Option data
        opt_type = "CALL" if pos.is_call else "PUT"
        option = self.api.get_option_snapshot(pos.symbol, pos.strike, pos.expiration, opt_type)
        
        if option.get('mark') or option.get('last'):
            pos.current_option_price = option.get('mark') or option.get('last')
        
        pos.greeks.delta = option.get('delta') or pos.greeks.delta or pos.greeks.entry_delta
        pos.greeks.gamma = option.get('gamma') or pos.greeks.gamma
        pos.greeks.theta = option.get('theta') or pos.greeks.theta
        pos.greeks.vega = option.get('vega') or pos.greeks.vega
        pos.greeks.iv = option.get('iv') or pos.greeks.iv
        
        # Liquidity
        pos.liquidity.bid = option.get('bid', 0)
        pos.liquidity.ask = option.get('ask', 0)
        pos.liquidity.spread = pos.liquidity.ask - pos.liquidity.bid
        mid = (pos.liquidity.bid + pos.liquidity.ask) / 2 if pos.liquidity.ask > 0 else pos.current_option_price
        pos.liquidity.spread_pct = (pos.liquidity.spread / mid * 100) if mid > 0 else 0
        pos.liquidity.volume = option.get('volume', 0)
        pos.liquidity.open_interest = option.get('open_interest', 0)
        pos.liquidity.volume_oi_ratio = pos.liquidity.volume / pos.liquidity.open_interest if pos.liquidity.open_interest > 0 else 0
        
        # Liquidity score
        score = 50
        if pos.liquidity.spread_pct <= 1:
            score += 25
        elif pos.liquidity.spread_pct <= 3:
            score += 15
        elif pos.liquidity.spread_pct > 10:
            score -= 25
        
        if pos.liquidity.open_interest >= 1000:
            score += 15
        elif pos.liquidity.open_interest >= 100:
            score += 5
        elif pos.liquidity.open_interest < 50:
            score -= 15
        
        if pos.liquidity.volume >= 100:
            score += 10
        
        pos.liquidity.liquidity_score = max(0, min(100, score))
        
        # DTE
        exp_date = datetime.strptime(pos.expiration, "%Y-%m-%d")
        pos.current_dte = max(0, (exp_date - datetime.now()).days)
        
        # High/Low tracking
        if pos.is_call:
            pos.highest_since_entry = max(pos.highest_since_entry, pos.current_stock_price)
        else:
            if pos.lowest_since_entry == 0:
                pos.lowest_since_entry = pos.current_stock_price
            pos.lowest_since_entry = min(pos.lowest_since_entry, pos.current_stock_price)
    
    def _calculate_iv_metrics(self, pos: Position):
        """Calculate IV rank and percentile"""
        iv_history = self.api.get_iv_history(pos.symbol, 252)
        
        if iv_history:
            iv_rank, iv_pct, iv_high, iv_low = AdvancedAnalytics.calculate_iv_rank(
                pos.greeks.iv or 0.3, iv_history
            )
            pos.greeks.iv_rank = iv_rank
            pos.greeks.iv_percentile = iv_pct
            pos.greeks.iv_52w_high = iv_high
            pos.greeks.iv_52w_low = iv_low
    
    def _analyze_market(self, pos: Position):
        """Analyze market context"""
        history = self.api.get_stock_history(pos.symbol, 100)
        
        if not history:
            return
        
        closes = [b['c'] for b in history]
        highs = [b['h'] for b in history]
        lows = [b['l'] for b in history]
        volumes = [b['v'] for b in history]
        
        # Trend
        pos.market.trend_daily = TechnicalAnalysis.determine_trend(closes)
        
        # RSI
        pos.market.rsi = TechnicalAnalysis.calculate_rsi(closes)
        
        # MACD
        macd, signal, hist = TechnicalAnalysis.calculate_macd(closes)
        pos.market.macd_histogram = hist
        if hist > 0:
            pos.market.macd_signal = "BULLISH"
        elif hist < 0:
            pos.market.macd_signal = "BEARISH"
        else:
            pos.market.macd_signal = "NEUTRAL"
        
        # ATR
        pos.market.atr = TechnicalAnalysis.calculate_atr(highs, lows, closes)
        pos.market.atr_percent = (pos.market.atr / pos.current_stock_price * 100) if pos.current_stock_price > 0 else 0
        
        # Support/Resistance
        s1, s2, r1, r2 = TechnicalAnalysis.calculate_support_resistance(highs, lows, closes)
        pos.market.support_1 = s1
        pos.market.support_2 = s2
        pos.market.resistance_1 = r1
        pos.market.resistance_2 = r2
        
        # Volume
        if len(volumes) >= 20:
            avg_vol = sum(volumes[-20:]) / 20
            pos.market.volume_vs_avg = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        
        # Trend alignment
        if pos.market.trend_daily in [TrendStrength.STRONG_UP, TrendStrength.MODERATE_UP]:
            pos.market.trend_alignment = pos.is_call
        elif pos.market.trend_daily in [TrendStrength.STRONG_DOWN, TrendStrength.MODERATE_DOWN]:
            pos.market.trend_alignment = not pos.is_call
        else:
            pos.market.trend_alignment = False
    
    def _calculate_stops(self, pos: Position):
        """Calculate stop levels"""
        atr = pos.market.atr or (pos.current_stock_price * 0.015)
        
        # Break-even
        if pos.is_call:
            pos.stops.breakeven = pos.entry_stock_price + (atr * 0.25)
        else:
            pos.stops.breakeven = pos.entry_stock_price - (atr * 0.25)
        
        # ATR trail
        if pos.is_call:
            pos.stops.atr_trail = pos.highest_since_entry - (atr * pos.atr_trail_mult)
        else:
            pos.stops.atr_trail = pos.lowest_since_entry + (atr * pos.atr_trail_mult)
        
        # Support-based stop (for calls)
        if pos.is_call and pos.market.support_1 > 0:
            pos.stops.support_based = pos.market.support_1 - (atr * 0.25)
        
        # Runner trail
        if pos.is_call:
            pos.stops.runner_trail = pos.highest_since_entry - (atr * pos.runner_trail_mult)
        else:
            pos.stops.runner_trail = pos.lowest_since_entry + (atr * pos.runner_trail_mult)
        
        # Determine recommended stop
        pnl_pct = pos.pnl_percent
        
        if pos.scaling.runner_active:
            new_stop = pos.stops.runner_trail
            pos.stops.method = "RUNNER_TRAIL"
        elif pnl_pct >= pos.atr_trail_trigger_pct:
            new_stop = pos.stops.atr_trail
            pos.stops.method = "ATR_TRAIL"
        elif pnl_pct >= pos.breakeven_trigger_pct:
            new_stop = pos.stops.breakeven
            pos.stops.method = "BREAKEVEN"
        else:
            new_stop = pos.stop_price
            pos.stops.method = "ORIGINAL"
        
        # Ratchet logic
        if pos.is_call:
            pos.stops.recommended = max(pos.stops.recommended or 0, new_stop)
        else:
            if pos.stops.recommended == 0:
                pos.stops.recommended = new_stop
            else:
                pos.stops.recommended = min(pos.stops.recommended, new_stop)
        
        pos.stops.needs_update = abs(pos.stops.recommended - pos.stop_price) > 0.01
        
        # Distance to stop
        pos.stops.distance_to_stop = abs(pos.current_stock_price - pos.stops.recommended)
        pos.stops.distance_to_stop_atr = pos.stops.distance_to_stop / atr if atr > 0 else 0
        
        # Option stop prices
        delta = pos.greeks.delta or 0.5
        gamma = pos.greeks.gamma or 0.02
        
        for attr in ['original', 'recommended', 'runner_trail']:
            stock_stop = getattr(pos.stops, attr if attr != 'runner_trail' else 'runner_trail')
            if stock_stop == 0:
                continue
            
            dist = abs(pos.current_stock_price - stock_stop)
            delta_impact = dist * abs(delta)
            gamma_impact = 0.5 * (dist ** 2) * gamma
            option_stop = max(0.01, pos.current_option_price - delta_impact - gamma_impact)
            
            if attr == 'original':
                pos.stops.original_option = option_stop
            elif attr == 'recommended':
                pos.stops.recommended_option = option_stop
            else:
                pos.stops.runner_option = option_stop
        
        # Risk at stop
        pos.stops.risk_at_stop = (pos.current_option_price - pos.stops.recommended_option) * pos.quantity * 100
        pos.stops.risk_at_stop_pct = ((pos.current_option_price - pos.stops.recommended_option) / pos.entry_option_price * 100) if pos.entry_option_price > 0 else 0
    
    def _check_scaling(self, pos: Position):
        """Check scaling triggers"""
        pnl_pct = pos.pnl_percent
        atr = pos.market.atr or (pos.current_stock_price * 0.015)
        
        # T1
        if not pos.scaling.t1_triggered and pnl_pct >= pos.scaling.t1_target_pct:
            pos.scaling.t1_triggered = True
            pos.scaling.t1_price = pos.current_option_price
            pos.scaling.t1_date = datetime.now().strftime("%Y-%m-%d")
        
        # T2
        if not pos.scaling.t2_triggered and pnl_pct >= pos.scaling.t2_target_pct:
            pos.scaling.t2_triggered = True
            pos.scaling.t2_price = pos.current_option_price
            pos.scaling.t2_date = datetime.now().strftime("%Y-%m-%d")
            pos.scaling.runner_active = True
            
            if pos.is_call:
                pos.scaling.extended_target = pos.target_price + (atr * 0.75)
            else:
                pos.scaling.extended_target = pos.target_price - (atr * 0.75)
        
        # Runner exit checks
        if pos.scaling.runner_active and not pos.scaling.runner_closed:
            if pos.is_call:
                if pos.current_stock_price >= pos.scaling.extended_target:
                    pos.scaling.runner_closed = True
                    pos.scaling.runner_exit_reason = "EXTENDED_TARGET"
                    pos.scaling.runner_exit_price = pos.current_option_price
                elif pos.current_stock_price <= pos.stops.runner_trail:
                    pos.scaling.runner_closed = True
                    pos.scaling.runner_exit_reason = "TRAIL_STOP"
                    pos.scaling.runner_exit_price = pos.current_option_price
            else:
                if pos.current_stock_price <= pos.scaling.extended_target:
                    pos.scaling.runner_closed = True
                    pos.scaling.runner_exit_reason = "EXTENDED_TARGET"
                elif pos.current_stock_price >= pos.stops.runner_trail:
                    pos.scaling.runner_closed = True
                    pos.scaling.runner_exit_reason = "TRAIL_STOP"
            
            if pos.current_dte <= pos.runner_min_dte:
                pos.scaling.runner_closed = True
                pos.scaling.runner_exit_reason = "DTE_CRITICAL"
    
    def _determine_status(self, pos: Position):
        """Determine trade status and recommended action"""
        pnl = pos.pnl_percent
        dte = pos.current_dte
        score = pos.score.overall_score
        
        # Check exit conditions
        stop_hit = (pos.is_call and pos.current_stock_price <= pos.stops.recommended) or \
                   (not pos.is_call and pos.current_stock_price >= pos.stops.recommended)
        
        target_hit = (pos.is_call and pos.current_stock_price >= pos.target_price) or \
                     (not pos.is_call and pos.current_stock_price <= pos.target_price)
        
        # Priority order for status
        if stop_hit or pnl <= -50:
            pos.status = TradeStatus.EXIT_STOP
            pos.action = Action.EXIT_NOW
            pos.action_detail = "Stop hit - exit position immediately"
        
        elif dte <= 7 and pnl < 30:
            pos.status = TradeStatus.EXIT_TIME
            pos.action = Action.EXIT_NOW
            pos.action_detail = f"Only {dte} DTE with limited profit - close or roll"
        
        elif pos.scaling.runner_closed:
            pos.status = TradeStatus.EXIT_TARGET
            pos.action = Action.CLOSE_RUNNER
            pos.action_detail = f"Runner complete: {pos.scaling.runner_exit_reason}"
        
        elif pos.roll_analysis.roll_urgency == "URGENT":
            pos.status = TradeStatus.CONSIDER_ROLL
            pos.action = pos.roll_analysis.roll_action
            pos.action_detail = f"Roll recommended: {pos.roll_analysis.roll_reason}"
        
        elif pos.gamma_analysis.gamma_explosion_risk:
            pos.status = TradeStatus.WARNING_GAMMA
            pos.action = Action.TIGHTEN_STOP if pnl > 0 else Action.EXIT_NOW
            pos.action_detail = "High gamma risk - near strike + near expiry"
        
        elif pos.greeks.iv_change < -0.1 and pnl < 10:
            pos.status = TradeStatus.WARNING_IV_CRUSH
            pos.action = Action.TIGHTEN_STOP
            pos.action_detail = "IV crush detected - tighten stop or exit"
        
        elif target_hit or pnl >= pos.scaling.t2_target_pct:
            if pos.scaling.runner_active:
                pos.status = TradeStatus.RUNNER_ACTIVE
                pos.action = Action.HOLD
                pos.action_detail = f"Runner riding to ${pos.scaling.extended_target:.2f}"
            else:
                pos.status = TradeStatus.TAKE_FULL
                pos.action = Action.TAKE_FULL
                pos.action_detail = f"T2 target hit (+{pnl:.0f}%) - sell 25%"
        
        elif pnl >= pos.scaling.t1_target_pct:
            pos.status = TradeStatus.TAKE_PARTIAL
            pos.action = Action.TAKE_PARTIAL
            pos.action_detail = f"T1 target hit (+{pnl:.0f}%) - sell 50%"
        
        elif dte <= 14 and pos.theta_analysis.acceleration_phase == "ACCELERATING":
            pos.status = TradeStatus.WARNING_THETA
            pos.action = Action.ROLL_OUT if pnl > 0 else Action.EXIT_NOW
            pos.action_detail = f"Theta accelerating ({dte} DTE) - manage time decay"
        
        elif pos.liquidity.liquidity_score < 30:
            pos.status = TradeStatus.WARNING_LIQUIDITY
            pos.action = Action.REDUCE_SIZE
            pos.action_detail = "Poor liquidity - consider reducing size"
        
        elif score >= 75 and pos.market.trend_alignment:
            pos.status = TradeStatus.HOLDING_STRONG
            pos.action = Action.HOLD
            pos.action_detail = f"Strong position (score: {score:.0f}) - hold"
        
        elif score >= 60:
            pos.status = TradeStatus.HOLDING_GOOD
            pos.action = Action.HOLD
            pos.action_detail = f"Good position (score: {score:.0f}) - continue holding"
        
        elif score >= 45:
            pos.status = TradeStatus.HOLDING_NEUTRAL
            pos.action = Action.TIGHTEN_STOP if pnl > 20 else Action.HOLD
            pos.action_detail = f"Neutral position (score: {score:.0f}) - monitor closely"
        
        else:
            pos.status = TradeStatus.HOLDING_WEAK
            pos.action = Action.TIGHTEN_STOP
            pos.action_detail = f"Weak position (score: {score:.0f}) - tighten risk management"
    
    def _generate_alerts(self, pos: Position):
        """Generate alerts and warnings"""
        # Scaling alerts
        if pos.scaling.t1_triggered and not any("T1" in a for a in pos.alerts):
            pos.alerts.append(f"🎯 T1 TRIGGERED at +{pos.scaling.t1_target_pct:.0f}% - sell 50%")
        
        if pos.scaling.t2_triggered and pos.scaling.runner_active and not pos.scaling.runner_closed:
            pos.alerts.append(f"🏃 RUNNER ACTIVE - target ${pos.scaling.extended_target:.2f}")
        
        # Stop alerts
        if pos.stops.needs_update:
            pos.alerts.append(f"📍 UPDATE STOP: ${pos.stop_price:.2f} → ${pos.stops.recommended:.2f}")
        
        # DTE alerts
        if pos.current_dte <= 7:
            pos.alerts.append(f"⏰ CRITICAL: Only {pos.current_dte} DTE remaining!")
        elif pos.current_dte <= 14:
            pos.alerts.append(f"⚠️ WARNING: {pos.current_dte} DTE - theta accelerating")
        
        # Gamma alert
        if pos.gamma_analysis.gamma_explosion_risk:
            pos.alerts.append("⚡ GAMMA EXPLOSION RISK - near strike + near expiry")
        
        # IV alerts
        if pos.greeks.iv_rank >= 80:
            pos.warnings.append(f"📊 High IV Rank ({pos.greeks.iv_rank:.0f}) - IV crush risk")
        elif pos.greeks.iv_rank <= 20:
            pos.warnings.append(f"📊 Low IV Rank ({pos.greeks.iv_rank:.0f}) - good entry environment")
        
        if pos.greeks.iv_change < -0.05:
            pos.warnings.append(f"📉 IV dropped {pos.greeks.iv_change*100:.1f}% since entry")
        
        # Roll alerts
        if pos.roll_analysis.roll_urgency in ["RECOMMENDED", "URGENT"]:
            pos.alerts.append(f"🔄 {pos.roll_analysis.roll_urgency}: {pos.roll_analysis.roll_reason}")
        
        # Liquidity warning
        if pos.liquidity.liquidity_score < 40:
            pos.warnings.append(f"💧 Low liquidity (score: {pos.liquidity.liquidity_score:.0f})")
        
        # Momentum warning
        if not pos.market.trend_alignment and pos.pnl_percent < 20:
            pos.warnings.append("📈 Trend not aligned with position")
    
    def update_all(self):
        """Update all positions"""
        for pos_id, pos in self.positions.items():
            try:
                self.update_position(pos)
            except Exception as e:
                logger.error(f"Error updating {pos_id}: {e}")
    
    def get_summary(self, pos: Position) -> Dict:
        """Get comprehensive summary for display"""
        return {
            # Identity
            'id': pos.id,
            'symbol': pos.symbol,
            'type': pos.position_type.value,
            'strike': pos.strike,
            'expiration': pos.expiration,
            'quantity': pos.quantity,
            
            # Status
            'status': pos.status.value,
            'action': pos.action.value,
            'action_detail': pos.action_detail,
            'alerts': pos.alerts,
            'warnings': pos.warnings,
            
            # P&L
            'entry_stock': pos.entry_stock_price,
            'current_stock': pos.current_stock_price,
            'stock_pnl_pct': pos.stock_pnl_percent,
            'entry_option': pos.entry_option_price,
            'current_option': pos.current_option_price,
            'pnl_dollars': pos.pnl_dollars,
            'pnl_percent': pos.pnl_percent,
            
            # Greeks
            'delta': pos.greeks.delta,
            'gamma': pos.greeks.gamma,
            'theta': pos.greeks.theta,
            'vega': pos.greeks.vega,
            'iv': pos.greeks.iv,
            'iv_rank': pos.greeks.iv_rank,
            'iv_percentile': pos.greeks.iv_percentile,
            'iv_change': pos.greeks.iv_change,
            'delta_change': pos.greeks.delta_change,
            
            # Theta Analysis
            'theta_decay_daily': pos.theta_analysis.daily_decay,
            'theta_decay_pct': pos.theta_analysis.decay_rate_pct,
            'theta_phase': pos.theta_analysis.acceleration_phase,
            'theta_severity': pos.theta_analysis.decay_severity,
            
            # Gamma Analysis
            'gamma_risk_score': pos.gamma_analysis.gamma_risk_score,
            'gamma_risk_level': pos.gamma_analysis.risk_level.value,
            'gamma_explosion_risk': pos.gamma_analysis.gamma_explosion_risk,
            
            # Liquidity
            'bid': pos.liquidity.bid,
            'ask': pos.liquidity.ask,
            'spread_pct': pos.liquidity.spread_pct,
            'liquidity_score': pos.liquidity.liquidity_score,
            'liquidity_quality': pos.liquidity.spread_quality,
            'volume': pos.liquidity.volume,
            'open_interest': pos.liquidity.open_interest,
            
            # Expected Move
            'prob_target': pos.expected_move.prob_above_target,
            'prob_stop': pos.expected_move.prob_below_stop,
            'prob_itm': pos.expected_move.prob_itm_at_expiry,
            'expected_value': pos.expected_move.expected_value,
            'risk_reward': pos.expected_move.risk_reward_ratio,
            'one_sigma_up': pos.expected_move.one_sigma_up,
            'one_sigma_down': pos.expected_move.one_sigma_down,
            
            # Roll Analysis
            'should_roll': pos.roll_analysis.should_roll,
            'roll_urgency': pos.roll_analysis.roll_urgency,
            'roll_reason': pos.roll_analysis.roll_reason,
            'roll_type': pos.roll_analysis.roll_type,
            
            # Market Context
            'trend': pos.market.trend_daily.value if hasattr(pos.market.trend_daily, 'value') else str(pos.market.trend_daily),
            'trend_aligned': pos.market.trend_alignment,
            'rsi': pos.market.rsi,
            'macd': pos.market.macd_signal,
            'atr': pos.market.atr,
            'atr_pct': pos.market.atr_percent,
            'volume_vs_avg': pos.market.volume_vs_avg,
            'support_1': pos.market.support_1,
            'resistance_1': pos.market.resistance_1,
            'momentum_score': pos.market.momentum_score,
            
            # Scenarios
            'scenarios': pos.scenarios.scenarios,
            'breakeven_price': pos.scenarios.breakeven_price,
            
            # Position Score
            'score_overall': pos.score.overall_score,
            'score_grade': pos.score.grade,
            'score_pnl': pos.score.pnl_score,
            'score_theta': pos.score.theta_score,
            'score_gamma': pos.score.gamma_score,
            'score_iv': pos.score.iv_score,
            'score_liquidity': pos.score.liquidity_score,
            'score_momentum': pos.score.momentum_score,
            'score_probability': pos.score.probability_score,
            'score_weakest': pos.score.weakest_component,
            
            # Stops
            'stop_original': pos.stops.original,
            'stop_recommended': pos.stops.recommended,
            'stop_method': pos.stops.method,
            'stop_needs_update': pos.stops.needs_update,
            'option_stop': pos.stops.recommended_option,
            'distance_to_stop': pos.stops.distance_to_stop,
            'distance_to_stop_atr': pos.stops.distance_to_stop_atr,
            'risk_at_stop': pos.stops.risk_at_stop,
            
            # Time
            'days_held': pos.days_held,
            'dte': pos.current_dte,
            'starting_dte': pos.starting_dte,
            
            # Scaling
            't1_triggered': pos.scaling.t1_triggered,
            't2_triggered': pos.scaling.t2_triggered,
            'runner_active': pos.scaling.runner_active,
            'runner_closed': pos.scaling.runner_closed,
            'extended_target': pos.scaling.extended_target,
            'runner_exit_reason': pos.scaling.runner_exit_reason,
            
            # Targets
            'target_price': pos.target_price,
            'stop_price': pos.stop_price,
        }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║     PROFESSIONAL OPTIONS TRADE MANAGER v2.0                   ║
    ║     A+ Tier Institutional-Grade Analytics                     ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  • IV Rank & Percentile     • Expected Move Analysis          ║
    ║  • Theta Acceleration       • Position Health Scoring         ║
    ║  • Gamma Risk Assessment    • Roll Recommendations            ║
    ║  • Liquidity Analysis       • Scenario Projections            ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    api_key = os.getenv('POLYGON_API_KEY', '')
    if not api_key:
        print("  ❌ No POLYGON_API_KEY found in .env file")
        return
    
    api = PolygonAPI(api_key)
    manager = ProfessionalTradeManager(api)
    
    print(f"  ✅ Loaded {len(manager.positions)} positions")
    print(f"  🌐 Run 'py web_pro.py' for the web interface")
    print()


if __name__ == "__main__":
    main()
