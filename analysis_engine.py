"""
Analysis Engine - Pine Script Logic in Python
==============================================
Replicates the logic from:
- Options Swing Dashboard v5 (8 setup types, tier, priority)
- Enhanced Analysis Module v1 (RS, IV, MTF, sector, momentum)
- Execution Intelligence HUD v1 (session, CVD, VWAP, microstructure)
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pytz

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OHLCV:
    """Single bar of price data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class AnalysisResult:
    """Complete analysis output"""
    symbol: str
    
    # Category (READY_NOW, SETTING_UP, BUILDING, AVOID)
    category: str
    
    # Setup detection (from Dashboard v5)
    setup_type: Optional[str]  # CONTINUATION, SQUEEZE, BREAKOUT, etc.
    setup_direction: Optional[str]  # CALL or PUT
    tier: Optional[str]  # A, B, C
    priority_score: int  # 0-150
    setup_factors: int
    max_factors: int
    
    # Execution readiness (from Execution HUD)
    exec_readiness: int  # 0-14
    exec_status: str  # GO, READY, CAUTION, WAIT
    session_phase: str
    
    # Enhanced analysis
    relative_strength: float  # vs SPY
    rs_rating: str
    iv_percentile: float
    iv_rating: str
    mtf_alignment: str
    momentum_quality: int
    
    # Technical levels
    support: Optional[float]
    resistance: Optional[float]
    vwap: Optional[float]
    ema_21: float
    sma_50: float
    sma_200: float
    
    # Indicators
    rsi: float
    squeeze_on: bool
    squeeze_bars: int
    consecutive_green: int
    consecutive_red: int
    
    # Warnings
    warnings: List[str]
    
    # Confluence score (combined)
    confluence_score: int  # 0-100
    
    # Raw data for debugging
    technical_data: Dict
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'category': self.category,
            'setup_type': self.setup_type,
            'setup_direction': self.setup_direction,
            'tier': self.tier,
            'priority_score': self.priority_score,
            'setup_factors': self.setup_factors,
            'max_factors': self.max_factors,
            'exec_readiness': self.exec_readiness,
            'exec_status': self.exec_status,
            'session_phase': self.session_phase,
            'relative_strength': self.relative_strength,
            'rs_rating': self.rs_rating,
            'iv_percentile': self.iv_percentile,
            'iv_rating': self.iv_rating,
            'mtf_alignment': self.mtf_alignment,
            'momentum_quality': self.momentum_quality,
            'support': self.support,
            'resistance': self.resistance,
            'vwap': self.vwap,
            'ema_21': self.ema_21,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'rsi': self.rsi,
            'squeeze_on': self.squeeze_on,
            'squeeze_bars': self.squeeze_bars,
            'consecutive_green': self.consecutive_green,
            'consecutive_red': self.consecutive_red,
            'warnings': self.warnings,
            'confluence_score': self.confluence_score,
            'technical_data': self.technical_data
        }


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

def ema(data: List[float], period: int) -> List[float]:
    """Exponential Moving Average"""
    if len(data) < period:
        return [data[0]] * len(data) if data else []
    
    multiplier = 2 / (period + 1)
    result = [sum(data[:period]) / period]  # SMA for first value
    
    for i in range(period, len(data)):
        result.append((data[i] - result[-1]) * multiplier + result[-1])
    
    # Pad beginning with first EMA value
    return [result[0]] * (period - 1) + result

def sma(data: List[float], period: int) -> List[float]:
    """Simple Moving Average"""
    if len(data) < period:
        return [sum(data) / len(data)] * len(data) if data else []
    
    result = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(sum(data[:i+1]) / (i + 1))
        else:
            result.append(sum(data[i-period+1:i+1]) / period)
    return result

def rsi(closes: List[float], period: int = 14) -> float:
    """Relative Strength Index"""
    if len(closes) < period + 1:
        return 50.0
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range"""
    if len(closes) < 2:
        return highs[0] - lows[0] if highs and lows else 0
    
    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges)
    
    return sum(true_ranges[-period:]) / period

def stdev(data: List[float], period: int) -> float:
    """Standard Deviation"""
    if len(data) < period:
        return 0.0
    
    subset = data[-period:]
    mean = sum(subset) / len(subset)
    variance = sum((x - mean) ** 2 for x in subset) / len(subset)
    return math.sqrt(variance)

def bollinger_bands(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[float, float, float]:
    """Bollinger Bands - returns (upper, middle, lower)"""
    if len(closes) < period:
        return closes[-1] * 1.02, closes[-1], closes[-1] * 0.98
    
    middle = sum(closes[-period:]) / period
    std = stdev(closes, period)
    
    return middle + std * mult, middle, middle - std * mult

def keltner_channels(highs: List[float], lows: List[float], closes: List[float], 
                     period: int = 20, mult: float = 1.5) -> Tuple[float, float, float]:
    """Keltner Channels - returns (upper, middle, lower)"""
    ema_vals = ema(closes, period)
    middle = ema_vals[-1] if ema_vals else closes[-1]
    
    atr_val = atr(highs, lows, closes, period)
    
    return middle + atr_val * mult, middle, middle - atr_val * mult

def pivot_high(highs: List[float], left: int = 10, right: int = 3) -> Optional[float]:
    """Find pivot high"""
    if len(highs) < left + right + 1:
        return None
    
    pivot_idx = len(highs) - right - 1
    pivot_val = highs[pivot_idx]
    
    # Check if it's higher than all surrounding bars
    for i in range(pivot_idx - left, pivot_idx):
        if highs[i] >= pivot_val:
            return None
    for i in range(pivot_idx + 1, pivot_idx + right + 1):
        if i < len(highs) and highs[i] >= pivot_val:
            return None
    
    return pivot_val

def pivot_low(lows: List[float], left: int = 10, right: int = 3) -> Optional[float]:
    """Find pivot low"""
    if len(lows) < left + right + 1:
        return None
    
    pivot_idx = len(lows) - right - 1
    pivot_val = lows[pivot_idx]
    
    for i in range(pivot_idx - left, pivot_idx):
        if lows[i] <= pivot_val:
            return None
    for i in range(pivot_idx + 1, pivot_idx + right + 1):
        if i < len(lows) and lows[i] <= pivot_val:
            return None
    
    return pivot_val

def calculate_vwap(highs: List[float], lows: List[float], closes: List[float], 
                   volumes: List[float]) -> float:
    """Volume Weighted Average Price"""
    if not volumes or sum(volumes) == 0:
        return closes[-1] if closes else 0
    
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    cum_tp_vol = sum(tp * v for tp, v in zip(typical_prices, volumes))
    cum_vol = sum(volumes)
    
    return cum_tp_vol / cum_vol if cum_vol > 0 else typical_prices[-1]


# ============================================================================
# SETUP DETECTION (Dashboard v5 Logic)
# ============================================================================

class SetupDetector:
    """Detects the 8 setup types from Dashboard v5"""
    
    def __init__(self, bars: List[OHLCV], spy_bars: List[OHLCV] = None):
        self.bars = bars
        self.spy_bars = spy_bars or []
        
        if not bars:
            return
            
        # Extract price arrays
        self.opens = [b.open for b in bars]
        self.highs = [b.high for b in bars]
        self.lows = [b.low for b in bars]
        self.closes = [b.close for b in bars]
        self.volumes = [b.volume for b in bars]
        
        # Calculate indicators
        self._calculate_indicators()
        
    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        closes = self.closes
        highs = self.highs
        lows = self.lows
        volumes = self.volumes
        
        # Moving averages
        self.ema_21 = ema(closes, 21)[-1] if len(closes) >= 21 else closes[-1]
        self.sma_50 = sma(closes, 50)[-1] if len(closes) >= 50 else closes[-1]
        self.sma_200 = sma(closes, 200)[-1] if len(closes) >= 200 else closes[-1]
        
        # RSI
        self.rsi_val = rsi(closes, 14)
        
        # ATR
        self.atr_val = atr(highs, lows, closes, 14)
        
        # Volume
        vol_sma = sma(volumes, 20)
        self.vol_ratio = volumes[-1] / vol_sma[-1] if vol_sma[-1] > 0 else 1.0
        self.vol_spike = self.vol_ratio >= 1.5
        self.vol_dry = self.vol_ratio <= 0.7
        
        # Price position
        self.close = closes[-1]
        self.above_ema21 = self.close > self.ema_21
        self.above_sma50 = self.close > self.sma_50
        self.above_sma200 = self.close > self.sma_200
        
        # EMA Stack
        self.emas_bull = self.ema_21 > self.sma_50 > self.sma_200
        self.emas_bear = self.ema_21 < self.sma_50 < self.sma_200
        
        # Distance from 21 EMA (in ATR units)
        self.dist_from_ema = (self.close - self.ema_21) / self.atr_val if self.atr_val > 0 else 0
        self.stretched_up = self.dist_from_ema > 1.5
        self.stretched_down = self.dist_from_ema < -1.5
        self.extended_up = self.dist_from_ema > 3.0
        self.extended_down = self.dist_from_ema < -3.0
        
        # Bollinger and Keltner for squeeze
        self.bb_upper, self.bb_mid, self.bb_lower = bollinger_bands(closes, 20, 2.0)
        self.kc_upper, self.kc_mid, self.kc_lower = keltner_channels(highs, lows, closes, 20, 1.5)
        
        # Squeeze detection
        self.squeeze_on = self.bb_lower > self.kc_lower and self.bb_upper < self.kc_upper
        
        # Count squeeze bars
        self.squeeze_bars = 0
        for i in range(len(closes) - 1, max(0, len(closes) - 20), -1):
            subset_closes = closes[:i+1]
            subset_highs = highs[:i+1]
            subset_lows = lows[:i+1]
            
            if len(subset_closes) < 20:
                break
                
            bb_u, _, bb_l = bollinger_bands(subset_closes, 20, 2.0)
            kc_u, _, kc_l = keltner_channels(subset_highs, subset_lows, subset_closes, 20, 1.5)
            
            if bb_l > kc_l and bb_u < kc_u:
                self.squeeze_bars += 1
            else:
                break
        
        # Squeeze momentum
        self.squeeze_mom = closes[-1] - (max(highs[-20:]) + min(lows[-20:])) / 2 if len(closes) >= 20 else 0
        self.squeeze_mom_rising = self.squeeze_mom > 0 and len(closes) > 1
        
        # Consecutive days
        self.consec_green = 0
        self.consec_red = 0
        for i in range(len(closes) - 1, 0, -1):
            if closes[i] > self.opens[i]:
                if self.consec_red == 0:
                    self.consec_green += 1
                else:
                    break
            else:
                if self.consec_green == 0:
                    self.consec_red += 1
                else:
                    break
        
        # Pivot levels
        self.resistance = pivot_high(highs, 10, 3)
        self.support = pivot_low(lows, 10, 3)
        
        # Higher lows / Lower highs
        if len(lows) >= 15:
            self.higher_lows = min(lows[-5:]) > min(lows[-15:-5])
        else:
            self.higher_lows = False
            
        if len(highs) >= 15:
            self.lower_highs = max(highs[-5:]) < max(highs[-15:-5])
        else:
            self.lower_highs = False
        
        # Consolidation detection
        if len(highs) >= 5:
            recent_range = max(highs[-5:]) - min(lows[-5:])
            avg_range = self.atr_val * 5
            self.in_consolidation = recent_range < avg_range * 0.7
            self.consol_bars = sum(1 for i in range(min(20, len(closes))) 
                                   if i > 0 and abs(closes[-i] - closes[-i-1]) < self.atr_val * 0.5)
        else:
            self.in_consolidation = False
            self.consol_bars = 0
        
        # RSI states
        self.rsi_oversold = self.rsi_val < 30
        self.rsi_overbought = self.rsi_val > 70
        self.rsi_mid_low = 30 <= self.rsi_val < 45
        self.rsi_mid_high = 55 < self.rsi_val <= 70
        
        # RSI divergence (simplified)
        if len(closes) >= 10:
            price_lower = min(lows[-5:]) < min(lows[-10:-5])
            price_higher = max(highs[-5:]) > max(highs[-10:-5])
            # Would need RSI history for proper divergence
            self.bull_divergence = price_lower and self.rsi_val > 35
            self.bear_divergence = price_higher and self.rsi_val < 65
        else:
            self.bull_divergence = False
            self.bear_divergence = False
        
        # Parabolic move detection
        if len(closes) >= 20:
            pct_20 = (closes[-1] - closes[-20]) / closes[-20] * 100
            pct_10 = (closes[-1] - closes[-10]) / closes[-10] * 100
            self.parabolic_up = pct_20 > 40 or pct_10 > 25
            self.parabolic_down = pct_20 < -40 or pct_10 < -25
        else:
            self.parabolic_up = False
            self.parabolic_down = False
        
        # Volume profile approximation
        self.vwap = calculate_vwap(highs[-50:], lows[-50:], closes[-50:], volumes[-50:]) if len(closes) >= 50 else closes[-1]
        
    def detect_setups(self) -> Tuple[Optional[str], Optional[str], Optional[str], int, int, int]:
        """
        Detect best setup
        Returns: (setup_type, direction, tier, priority_score, factors, max_factors)
        """
        call_setups = []
        put_setups = []
        
        # A-TIER SETUPS
        
        # Call Continuation
        factors, max_f = self._check_call_continuation()
        if factors >= 7:
            call_setups.append(('CONTINUATION', 'A', factors, max_f, self._calc_priority(100, factors, max_f)))
        
        # Call Base Breakout
        factors, max_f = self._check_call_base_breakout()
        if factors >= 6:
            call_setups.append(('BASE_BREAKOUT', 'A', factors, max_f, self._calc_priority(100, factors, max_f)))
        
        # Put Continuation
        factors, max_f = self._check_put_continuation()
        if factors >= 7:
            put_setups.append(('CONTINUATION', 'A', factors, max_f, self._calc_priority(100, factors, max_f)))
        
        # Put Base Breakdown
        factors, max_f = self._check_put_base_breakdown()
        if factors >= 6:
            put_setups.append(('BASE_BREAKDOWN', 'A', factors, max_f, self._calc_priority(100, factors, max_f)))
        
        # B-TIER SETUPS
        
        # Call Squeeze
        factors, max_f = self._check_call_squeeze()
        if factors >= 5:
            call_setups.append(('SQUEEZE', 'B', factors, max_f, self._calc_priority(70, factors, max_f)))
        
        # Call Breakout
        factors, max_f = self._check_call_breakout()
        if factors >= 5:
            call_setups.append(('BREAKOUT', 'B', factors, max_f, self._calc_priority(70, factors, max_f)))
        
        # Put Squeeze
        factors, max_f = self._check_put_squeeze()
        if factors >= 5:
            put_setups.append(('SQUEEZE', 'B', factors, max_f, self._calc_priority(70, factors, max_f)))
        
        # Put Breakout
        factors, max_f = self._check_put_breakout()
        if factors >= 5:
            put_setups.append(('BREAKOUT', 'B', factors, max_f, self._calc_priority(70, factors, max_f)))
        
        # C-TIER SETUPS
        
        # Call Reversal
        factors, max_f = self._check_call_reversal()
        if factors >= 5:
            call_setups.append(('REVERSAL', 'C', factors, max_f, self._calc_priority(40, factors, max_f)))
        
        # Put Reversal
        factors, max_f = self._check_put_reversal()
        if factors >= 5:
            put_setups.append(('REVERSAL', 'C', factors, max_f, self._calc_priority(40, factors, max_f)))
        
        # Find best setup by priority
        all_setups = [(s[0], 'CALL', s[1], s[2], s[3], s[4]) for s in call_setups]
        all_setups += [(s[0], 'PUT', s[1], s[2], s[3], s[4]) for s in put_setups]
        
        if not all_setups:
            return None, None, None, 0, 0, 0
        
        # Sort by priority descending
        all_setups.sort(key=lambda x: x[5], reverse=True)
        best = all_setups[0]
        
        return best[0], best[1], best[2], best[5], best[3], best[4]
    
    def _calc_priority(self, base: int, factors: int, max_factors: int) -> int:
        """Calculate priority score"""
        factor_bonus = int((factors * 30) / max_factors)
        context_bonus = 0
        if self.emas_bull and self.above_sma50:
            context_bonus += 10
        if self.in_consolidation:
            context_bonus += 5
        if self.vol_spike:
            context_bonus += 5
        return base + factor_bonus + context_bonus
    
    def _check_call_continuation(self) -> Tuple[int, int]:
        """Check for call continuation setup"""
        factors = 0
        max_factors = 12
        
        # Healthy uptrend
        if self.higher_lows and self.emas_bull:
            factors += 3
        # Pullback to EMA
        if self.close <= self.ema_21 * 1.01 and self.above_sma50:
            factors += 2
        # Orderly pullback
        if self.consol_bars >= 3:
            factors += 1
        # RSI OK
        if 40 <= self.rsi_val <= 65:
            factors += 1
        # Structure
        if self.higher_lows:
            factors += 1
        # Not parabolic
        if not self.parabolic_up and not self.extended_up:
            factors += 1
        # Has base
        if self.consol_bars >= 5:
            factors += 1
        # Weekly OK (simplified - assume OK if daily is bullish)
        if self.emas_bull:
            factors += 2
        
        return factors, max_factors
    
    def _check_call_base_breakout(self) -> Tuple[int, int]:
        """Check for call base breakout setup"""
        factors = 0
        max_factors = 11
        
        # Has base
        if self.consol_bars >= 5:
            factors += 3
        # Breaking out
        if len(self.highs) >= 5:
            base_high = max(self.highs[-5:])
            if self.close > base_high * 0.99:
                factors += 2
        # Volume
        if self.vol_spike or self.vol_ratio > 1.0:
            factors += 2
        # RSI
        if 45 < self.rsi_val < 75:
            factors += 1
        # Structure
        if self.higher_lows:
            factors += 1
        # Not extended
        if not self.extended_up:
            factors += 1
        # Trend OK
        if self.above_sma50 or self.emas_bull:
            factors += 1
        
        return factors, max_factors
    
    def _check_call_squeeze(self) -> Tuple[int, int]:
        """Check for call squeeze setup"""
        factors = 0
        max_factors = 9
        
        # In squeeze
        if self.squeeze_on or self.squeeze_bars >= 6:
            factors += 3
        # Momentum up
        if self.squeeze_mom > 0 and self.squeeze_mom_rising:
            factors += 2
        # Trend OK
        if self.above_ema21 or self.above_sma50:
            factors += 1
        # RSI OK
        if 40 < self.rsi_val < 70:
            factors += 1
        # Volume
        if self.vol_ratio > 1.0:
            factors += 1
        # Weekly OK
        if self.emas_bull or self.above_sma200:
            factors += 1
        
        return factors, max_factors
    
    def _check_call_breakout(self) -> Tuple[int, int]:
        """Check for call breakout setup"""
        factors = 0
        max_factors = 8
        
        # At resistance or breaking
        near_res = self.resistance and abs(self.close - self.resistance) < self.atr_val * 1.5
        if near_res or (self.resistance and self.close > self.resistance):
            factors += 2
        # Volume spike on green
        if self.vol_spike and self.close > self.opens[-1]:
            factors += 2
        # RSI
        if 50 < self.rsi_val < 70:
            factors += 1
        # Trend OK
        if self.above_sma50 or self.emas_bull:
            factors += 1
        # Compressed
        if self.in_consolidation or self.squeeze_on:
            factors += 1
        # Not extended
        if not self.extended_up and not self.parabolic_up:
            factors += 1
        
        return factors, max_factors
    
    def _check_call_reversal(self) -> Tuple[int, int]:
        """Check for call reversal setup"""
        factors = 0
        max_factors = 9
        
        # RSI oversold
        if self.rsi_oversold or self.rsi_mid_low:
            factors += 2
        # Stretched down
        if self.stretched_down:
            factors += 1
        # Consecutive red
        if self.consec_red >= 3:
            factors += 1
        # At support
        near_sup = self.support and abs(self.close - self.support) < self.atr_val * 1.5
        if near_sup or self.close <= self.sma_200:
            factors += 2
        # Volume
        if self.vol_spike or self.vol_dry:
            factors += 1
        # RSI turning
        if self.rsi_val > 30:
            factors += 1
        # Weekly OK
        if self.above_sma200:
            factors += 1
        
        return factors, max_factors
    
    def _check_put_continuation(self) -> Tuple[int, int]:
        """Check for put continuation setup"""
        factors = 0
        max_factors = 12
        
        # Healthy downtrend
        if self.lower_highs and self.emas_bear:
            factors += 3
        # Bounce to EMA
        if self.close >= self.ema_21 * 0.99 and not self.above_sma50:
            factors += 2
        # Orderly bounce
        if self.consol_bars >= 3:
            factors += 1
        # RSI OK
        if 35 <= self.rsi_val <= 60:
            factors += 1
        # Structure
        if self.lower_highs:
            factors += 1
        # Not parabolic
        if not self.parabolic_down and not self.extended_down:
            factors += 1
        # Has base
        if self.consol_bars >= 5:
            factors += 1
        # Weekly OK
        if self.emas_bear:
            factors += 2
        
        return factors, max_factors
    
    def _check_put_base_breakdown(self) -> Tuple[int, int]:
        """Check for put base breakdown setup"""
        factors = 0
        max_factors = 11
        
        # Has base
        if self.consol_bars >= 5:
            factors += 3
        # Breaking down
        if len(self.lows) >= 5:
            base_low = min(self.lows[-5:])
            if self.close < base_low * 1.01:
                factors += 2
        # Volume
        if self.vol_spike or self.vol_ratio > 1.0:
            factors += 2
        # RSI
        if 25 < self.rsi_val < 55:
            factors += 1
        # Structure
        if self.lower_highs:
            factors += 1
        # Not extended
        if not self.extended_down:
            factors += 1
        # Trend OK
        if not self.above_sma50 or self.emas_bear:
            factors += 1
        
        return factors, max_factors
    
    def _check_put_squeeze(self) -> Tuple[int, int]:
        """Check for put squeeze setup"""
        factors = 0
        max_factors = 9
        
        # In squeeze
        if self.squeeze_on or self.squeeze_bars >= 6:
            factors += 3
        # Momentum down
        if self.squeeze_mom < 0:
            factors += 2
        # Trend OK
        if not self.above_ema21 or not self.above_sma50:
            factors += 1
        # RSI OK
        if 30 < self.rsi_val < 60:
            factors += 1
        # Volume
        if self.vol_ratio > 1.0:
            factors += 1
        # Weekly OK
        if self.emas_bear or not self.above_sma200:
            factors += 1
        
        return factors, max_factors
    
    def _check_put_breakout(self) -> Tuple[int, int]:
        """Check for put breakout (breakdown) setup"""
        factors = 0
        max_factors = 8
        
        # At support or breaking
        near_sup = self.support and abs(self.close - self.support) < self.atr_val * 1.5
        if near_sup or (self.support and self.close < self.support):
            factors += 2
        # Volume spike on red
        if self.vol_spike and self.close < self.opens[-1]:
            factors += 2
        # RSI
        if 30 < self.rsi_val < 50:
            factors += 1
        # Trend OK
        if not self.above_sma50 or self.emas_bear:
            factors += 1
        # Compressed
        if self.in_consolidation or self.squeeze_on:
            factors += 1
        # Not extended
        if not self.extended_down and not self.parabolic_down:
            factors += 1
        
        return factors, max_factors
    
    def _check_put_reversal(self) -> Tuple[int, int]:
        """Check for put reversal setup"""
        factors = 0
        max_factors = 9
        
        # RSI overbought
        if self.rsi_overbought or self.rsi_mid_high:
            factors += 2
        # Stretched up
        if self.stretched_up:
            factors += 1
        # Consecutive green
        if self.consec_green >= 3:
            factors += 1
        # At resistance
        near_res = self.resistance and abs(self.close - self.resistance) < self.atr_val * 1.5
        if near_res or self.close >= self.sma_200 * 1.1:
            factors += 2
        # Volume
        if self.vol_spike or self.vol_dry:
            factors += 1
        # RSI turning
        if self.rsi_val < 70:
            factors += 1
        # Weekly OK
        if not self.above_sma200:
            factors += 1
        
        return factors, max_factors
    
    def get_warnings(self) -> List[str]:
        """Get warning messages"""
        warnings = []
        
        if self.parabolic_up:
            warnings.append("PARABOLIC UP - Wait for base")
        if self.parabolic_down:
            warnings.append("PARABOLIC DOWN - Wait for base")
        if self.extended_up:
            warnings.append("OVEREXTENDED UP - Mean reversion risk")
        if self.extended_down:
            warnings.append("OVEREXTENDED DOWN - Mean reversion risk")
        if self.consec_green >= 5:
            warnings.append(f"{self.consec_green} CONSECUTIVE GREEN - Exhaustion risk")
        if self.consec_red >= 5:
            warnings.append(f"{self.consec_red} CONSECUTIVE RED - Exhaustion risk")
        if self.rsi_overbought:
            warnings.append("RSI OVERBOUGHT")
        if self.rsi_oversold:
            warnings.append("RSI OVERSOLD")
        
        return warnings


# ============================================================================
# EXECUTION READINESS (Execution HUD Logic)
# ============================================================================

class ExecutionAnalyzer:
    """Analyzes execution readiness from Execution HUD"""
    
    def __init__(self, bars: List[OHLCV], spy_bars: List[OHLCV] = None):
        self.bars = bars
        self.spy_bars = spy_bars or []
        
        if not bars:
            return
        
        self.closes = [b.close for b in bars]
        self.highs = [b.high for b in bars]
        self.lows = [b.low for b in bars]
        self.volumes = [b.volume for b in bars]
        self.opens = [b.open for b in bars]
        
        self._calculate_execution_metrics()
    
    def _calculate_execution_metrics(self):
        """Calculate execution-related metrics"""
        
        # Session timing
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        self.hour = now.hour
        self.minute = now.minute
        self.time_of_day = self.hour * 100 + self.minute
        
        self.session_phase = self._get_session_phase()
        self.session_quality = self._get_session_quality()
        
        # VWAP
        self.vwap = calculate_vwap(self.highs[-50:], self.lows[-50:], self.closes[-50:], self.volumes[-50:])
        self.above_vwap = self.closes[-1] > self.vwap
        
        # CVD proxy (cumulative volume delta)
        self.cvd_rising = self._calculate_cvd_trend()
        
        # Relative strength vs SPY
        self.relative_strength = self._calculate_relative_strength()
        
        # ATR for context
        self.atr_val = atr(self.highs, self.lows, self.closes, 14)
        
        # VWAP bands
        vwap_std = stdev(self.closes, 20)
        self.vwap_upper = self.vwap + vwap_std * 1.5
        self.vwap_lower = self.vwap - vwap_std * 1.5
        self.at_vwap_upper = self.closes[-1] >= self.vwap_upper
        self.at_vwap_lower = self.closes[-1] <= self.vwap_lower
        
        # RSI for momentum
        self.rsi_val = rsi(self.closes, 14)
        self.rsi_ob = self.rsi_val > 70
        self.rsi_os = self.rsi_val < 30
    
    def _get_session_phase(self) -> str:
        """Determine current session phase"""
        tod = self.time_of_day
        
        if tod < 930:
            return "PRE-MARKET"
        elif tod < 1000:
            return "OPEN DRIVE"
        elif tod < 1130:
            return "MORNING"
        elif tod < 1400:
            return "MIDDAY CHOP"
        elif tod < 1530:
            return "AFTERNOON"
        elif tod < 1600:
            return "POWER HOUR"
        else:
            return "AFTER HOURS"
    
    def _get_session_quality(self) -> int:
        """Rate session quality 0-3"""
        phase = self.session_phase
        if phase == "MORNING":
            return 3
        elif phase in ["AFTERNOON", "POWER HOUR"]:
            return 2
        elif phase == "OPEN DRIVE":
            return 1
        else:
            return 0
    
    def _calculate_cvd_trend(self) -> bool:
        """Calculate if CVD is rising (buying pressure)"""
        if len(self.closes) < 5:
            return True
        
        # CVD proxy using candle close position
        cvd = 0
        for i in range(-5, 0):
            bar_range = self.highs[i] - self.lows[i]
            if bar_range > 0:
                close_pos = (self.closes[i] - self.lows[i]) / bar_range
                delta = self.volumes[i] * (close_pos - 0.5) * 2
                cvd += delta
        
        return cvd > 0
    
    def _calculate_relative_strength(self) -> float:
        """Calculate relative strength vs SPY"""
        if not self.spy_bars or len(self.spy_bars) < 2:
            return 0.0
        
        spy_closes = [b.close for b in self.spy_bars]
        
        stock_return = (self.closes[-1] - self.closes[0]) / self.closes[0] * 100
        spy_return = (spy_closes[-1] - spy_closes[0]) / spy_closes[0] * 100
        
        return stock_return - spy_return
    
    def calculate_exec_score(self, direction: str = 'CALL') -> Tuple[int, str]:
        """
        Calculate execution readiness score
        Returns: (score 0-14, status)
        """
        score = 0
        
        # Session timing (0-3)
        score += self.session_quality
        
        # Not in blocked periods (+1)
        if self.session_phase not in ["PRE-MARKET", "AFTER HOURS", "MIDDAY CHOP"]:
            score += 1
        
        if direction == 'CALL':
            # VWAP context (+1-2)
            if self.above_vwap:
                score += 1
            if self.above_vwap and not self.at_vwap_upper:
                score += 1
            
            # CVD (+1-2)
            if self.cvd_rising:
                score += 2
            
            # Relative strength (+1-2)
            if self.relative_strength > 0:
                score += 1
            if self.relative_strength > 0.5:
                score += 1
            
            # Momentum (+1-2)
            if 50 < self.rsi_val < 70:
                score += 2
            elif 40 < self.rsi_val <= 50:
                score += 1
            
            # Penalties
            if self.rsi_ob:
                score -= 2
            if self.at_vwap_upper:
                score -= 1
                
        else:  # PUT
            # VWAP context (+1-2)
            if not self.above_vwap:
                score += 1
            if not self.above_vwap and not self.at_vwap_lower:
                score += 1
            
            # CVD (+1-2)
            if not self.cvd_rising:
                score += 2
            
            # Relative strength (+1-2)
            if self.relative_strength < 0:
                score += 1
            if self.relative_strength < -0.5:
                score += 1
            
            # Momentum (+1-2)
            if 30 < self.rsi_val < 50:
                score += 2
            elif 50 <= self.rsi_val < 60:
                score += 1
            
            # Penalties
            if self.rsi_os:
                score -= 2
            if self.at_vwap_lower:
                score -= 1
        
        # Midday penalty
        if self.session_phase == "MIDDAY CHOP":
            score -= 1
        
        score = max(0, min(14, score))
        
        # Determine status
        if score >= 10:
            status = "GO"
        elif score >= 7:
            status = "READY"
        elif score >= 4:
            status = "CAUTION"
        else:
            status = "WAIT"
        
        return score, status


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_stock(symbol: str, bars: List[OHLCV], spy_bars: List[OHLCV] = None) -> AnalysisResult:
    """
    Complete stock analysis combining all three dashboards
    """
    if not bars:
        return AnalysisResult(
            symbol=symbol,
            category='AVOID',
            setup_type=None,
            setup_direction=None,
            tier=None,
            priority_score=0,
            setup_factors=0,
            max_factors=0,
            exec_readiness=0,
            exec_status='WAIT',
            session_phase='UNKNOWN',
            relative_strength=0,
            rs_rating='N/A',
            iv_percentile=50,
            iv_rating='NEUTRAL',
            mtf_alignment='UNKNOWN',
            momentum_quality=0,
            support=None,
            resistance=None,
            vwap=None,
            ema_21=0,
            sma_50=0,
            sma_200=0,
            rsi=50,
            squeeze_on=False,
            squeeze_bars=0,
            consecutive_green=0,
            consecutive_red=0,
            warnings=['No data available'],
            confluence_score=0,
            technical_data={}
        )
    
    # Setup detection
    setup_detector = SetupDetector(bars, spy_bars)
    setup_type, direction, tier, priority, factors, max_factors = setup_detector.detect_setups()
    warnings = setup_detector.get_warnings()
    
    # Execution analysis
    exec_analyzer = ExecutionAnalyzer(bars, spy_bars)
    exec_score, exec_status = exec_analyzer.calculate_exec_score(direction or 'CALL')
    
    # Relative strength
    rs = exec_analyzer.relative_strength
    if rs > 1.5:
        rs_rating = "STRONG OUTPERFORM"
    elif rs > 0.5:
        rs_rating = "OUTPERFORM"
    elif rs < -1.5:
        rs_rating = "WEAK UNDERPERFORM"
    elif rs < -0.5:
        rs_rating = "UNDERPERFORM"
    else:
        rs_rating = "NEUTRAL"
    
    # IV percentile (would need options data - use HV proxy)
    closes = [b.close for b in bars]
    if len(closes) >= 20:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        hv = stdev(returns, min(20, len(returns))) * math.sqrt(252) * 100
        # Simplified percentile (would need historical HV)
        iv_percentile = min(100, max(0, hv * 2))  # Very rough approximation
    else:
        iv_percentile = 50
    
    if iv_percentile < 30:
        iv_rating = "LOW - Buy Premium"
    elif iv_percentile > 70:
        iv_rating = "HIGH - Sell Premium"
    else:
        iv_rating = "NEUTRAL"
    
    # MTF alignment (simplified - would need multiple timeframe data)
    if setup_detector.emas_bull and setup_detector.above_sma200:
        mtf_alignment = "ALL BULLISH"
    elif setup_detector.emas_bear and not setup_detector.above_sma200:
        mtf_alignment = "ALL BEARISH"
    else:
        mtf_alignment = "MIXED"
    
    # Momentum quality
    mom_quality = 0
    if setup_detector.rsi_val > 50:
        mom_quality += 25
    if setup_detector.vol_ratio > 1.0:
        mom_quality += 25
    if setup_detector.higher_lows:
        mom_quality += 25
    if exec_analyzer.cvd_rising:
        mom_quality += 25
    
    # Determine category
    if setup_type and tier in ['A', 'B'] and exec_score >= 10:
        category = 'READY_NOW'
    elif setup_type and exec_score >= 5:
        category = 'SETTING_UP'
    elif setup_detector.squeeze_bars >= 3 or setup_detector.consol_bars >= 3:
        category = 'BUILDING'
    elif warnings:
        category = 'AVOID'
    else:
        category = 'WATCH'
    
    # Confluence score
    confluence = 0
    if setup_type:
        confluence += 30
    if tier == 'A':
        confluence += 20
    elif tier == 'B':
        confluence += 10
    confluence += min(30, exec_score * 2)
    if rs > 0.5:
        confluence += 10
    if iv_percentile < 40:
        confluence += 10
    
    return AnalysisResult(
        symbol=symbol,
        category=category,
        setup_type=setup_type,
        setup_direction=direction,
        tier=tier,
        priority_score=priority,
        setup_factors=factors,
        max_factors=max_factors,
        exec_readiness=exec_score,
        exec_status=exec_status,
        session_phase=exec_analyzer.session_phase,
        relative_strength=rs,
        rs_rating=rs_rating,
        iv_percentile=iv_percentile,
        iv_rating=iv_rating,
        mtf_alignment=mtf_alignment,
        momentum_quality=mom_quality,
        support=setup_detector.support,
        resistance=setup_detector.resistance,
        vwap=exec_analyzer.vwap,
        ema_21=setup_detector.ema_21,
        sma_50=setup_detector.sma_50,
        sma_200=setup_detector.sma_200,
        rsi=setup_detector.rsi_val,
        squeeze_on=setup_detector.squeeze_on,
        squeeze_bars=setup_detector.squeeze_bars,
        consecutive_green=setup_detector.consec_green,
        consecutive_red=setup_detector.consec_red,
        warnings=warnings,
        confluence_score=confluence,
        technical_data={
            'vol_ratio': setup_detector.vol_ratio,
            'atr': setup_detector.atr_val,
            'dist_from_ema': setup_detector.dist_from_ema,
            'above_vwap': exec_analyzer.above_vwap,
            'cvd_rising': exec_analyzer.cvd_rising
        }
    )
