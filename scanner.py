"""
Trading Cockpit - Smart Watchlist & AI Scanner
===============================================
AI-powered stock screening with:
- Watchlist management
- Technical analysis scoring
- News/catalyst detection
- Options contract recommendations
- "HOT LIST" ranking

Uses Claude API for AI analysis when available.
"""

import os
import json
import math
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import requests


class SetupQuality(Enum):
    """Quality rating for setups"""
    A_PLUS = "A+"      # Perfect setup - high conviction
    A = "A"            # Excellent setup
    B = "B"            # Good setup
    C = "C"            # Average setup
    D = "D"            # Weak setup
    F = "F"            # No setup / Avoid


class SignalStrength(Enum):
    """Signal strength"""
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    NEUTRAL = "NEUTRAL"
    WEAK_BEARISH = "WEAK_BEARISH"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class CatalystType(Enum):
    """Types of catalysts"""
    EARNINGS = "EARNINGS"
    FDA = "FDA"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    CONFERENCE = "CONFERENCE"
    ANALYST_RATING = "ANALYST_RATING"
    INSIDER_ACTIVITY = "INSIDER_ACTIVITY"
    NEWS = "NEWS"
    SECTOR_MOVE = "SECTOR_MOVE"
    TECHNICAL_BREAKOUT = "TECHNICAL_BREAKOUT"
    UNUSUAL_VOLUME = "UNUSUAL_VOLUME"
    OPTIONS_FLOW = "OPTIONS_FLOW"


@dataclass
class WatchlistStock:
    """A stock on the watchlist"""
    symbol: str
    name: str = ""
    sector: str = ""
    
    # User notes
    thesis: str = ""                    # Why watching this stock
    key_levels: Dict[str, float] = field(default_factory=dict)  # support, resistance, etc.
    alerts: List[str] = field(default_factory=list)
    
    # Settings
    active: bool = True
    priority: int = 1                   # 1=high, 2=medium, 3=low
    
    # Timestamps
    added_date: str = ""
    last_traded: str = ""


@dataclass
class TechnicalScore:
    """Technical analysis scoring"""
    # Trend
    trend_score: float = 0              # -100 to +100
    trend_direction: str = "NEUTRAL"
    above_20ema: bool = False
    above_50sma: bool = False
    above_200sma: bool = False
    ema_alignment: str = "MIXED"        # BULLISH, BEARISH, MIXED
    
    # Momentum
    momentum_score: float = 0           # -100 to +100
    rsi: float = 50
    rsi_signal: str = "NEUTRAL"         # OVERSOLD, NEUTRAL, OVERBOUGHT
    macd_signal: str = "NEUTRAL"        # BULLISH, BEARISH, NEUTRAL
    macd_histogram: float = 0
    
    # Volume
    volume_score: float = 0             # 0 to 100
    volume_ratio: float = 1.0           # vs 20-day avg
    volume_trend: str = "NORMAL"        # LOW, NORMAL, HIGH, CLIMACTIC
    
    # Volatility
    atr: float = 0
    atr_percent: float = 0              # ATR as % of price
    iv_rank: float = 50
    iv_percentile: float = 50
    
    # Pattern detection
    patterns: List[str] = field(default_factory=list)
    
    # Overall
    overall_score: float = 50           # 0 to 100
    signal: SignalStrength = SignalStrength.NEUTRAL


@dataclass
class Catalyst:
    """A catalyst event"""
    type: CatalystType
    date: str
    description: str
    impact: str = "MEDIUM"              # LOW, MEDIUM, HIGH
    source: str = ""


@dataclass
class OptionsRecommendation:
    """Recommended options contract"""
    direction: str                      # CALL or PUT
    strike: float
    expiration: str
    delta: float
    
    # Entry
    entry_price_low: float = 0
    entry_price_high: float = 0
    
    # Targets
    stock_target: float = 0
    stock_stop: float = 0
    profit_target_pct: float = 50
    stop_loss_pct: float = -30
    
    # Sizing
    suggested_dte: int = 30
    suggested_contracts: int = 1
    max_risk: float = 0
    
    # Reasoning
    reasoning: str = ""
    confidence: str = "MEDIUM"          # LOW, MEDIUM, HIGH


@dataclass
class StockAnalysis:
    """Complete analysis for a stock"""
    symbol: str
    name: str = ""
    
    # Price data
    price: float = 0
    change: float = 0
    change_pct: float = 0
    high_52w: float = 0
    low_52w: float = 0
    
    # Technical
    technicals: TechnicalScore = field(default_factory=TechnicalScore)
    
    # Catalysts
    catalysts: List[Catalyst] = field(default_factory=list)
    upcoming_earnings: str = ""
    days_to_earnings: int = -1
    
    # AI Analysis
    ai_summary: str = ""
    ai_bull_case: str = ""
    ai_bear_case: str = ""
    ai_recommendation: str = ""
    
    # Options recommendation
    options_rec: Optional[OptionsRecommendation] = None
    
    # Hot List scoring
    hot_score: float = 0                # 0 to 100
    setup_quality: SetupQuality = SetupQuality.C
    
    # Flags
    is_hot: bool = False
    alerts: List[str] = field(default_factory=list)
    
    # Timestamp
    analyzed_at: str = ""


@dataclass 
class HotListEntry:
    """Entry in the hot list"""
    rank: int
    symbol: str
    name: str
    price: float
    change_pct: float
    hot_score: float
    setup_quality: str
    signal: str
    headline: str                       # Short reason why it's hot
    options_rec: Optional[Dict] = None


class SmartScanner:
    """
    AI-powered stock scanner that analyzes watchlist
    and generates hot list with options recommendations
    """
    
    def __init__(self, api=None, anthropic_key: str = None):
        self.api = api
        self.anthropic_key = anthropic_key or os.getenv('ANTHROPIC_API_KEY')
        self.watchlist_file = Path("watchlist.json")
        self.watchlist: Dict[str, WatchlistStock] = {}
        self.load_watchlist()
    
    def load_watchlist(self):
        """Load watchlist from file"""
        if self.watchlist_file.exists():
            try:
                data = json.loads(self.watchlist_file.read_text())
                self.watchlist = {
                    s['symbol']: WatchlistStock(**s) 
                    for s in data.get('stocks', [])
                }
            except Exception as e:
                print(f"Error loading watchlist: {e}")
    
    def save_watchlist(self):
        """Save watchlist to file"""
        try:
            data = {
                'stocks': [asdict(s) for s in self.watchlist.values()],
                'updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.watchlist_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error saving watchlist: {e}")
    
    def add_to_watchlist(self, symbol: str, name: str = "", sector: str = "", 
                         thesis: str = "", priority: int = 1) -> WatchlistStock:
        """Add stock to watchlist"""
        stock = WatchlistStock(
            symbol=symbol.upper(),
            name=name,
            sector=sector,
            thesis=thesis,
            priority=priority,
            added_date=datetime.now().strftime("%Y-%m-%d")
        )
        self.watchlist[stock.symbol] = stock
        self.save_watchlist()
        return stock
    
    def remove_from_watchlist(self, symbol: str):
        """Remove stock from watchlist"""
        symbol = symbol.upper()
        if symbol in self.watchlist:
            del self.watchlist[symbol]
            self.save_watchlist()
    
    def analyze_stock(self, symbol: str) -> StockAnalysis:
        """Perform complete analysis on a stock"""
        analysis = StockAnalysis(
            symbol=symbol.upper(),
            analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Get price data
        if self.api:
            self._fetch_price_data(analysis)
            self._calculate_technicals(analysis)
            self._check_catalysts(analysis)
        else:
            self._set_demo_data(analysis)
        
        # Calculate hot score
        self._calculate_hot_score(analysis)
        
        # Generate options recommendation
        self._generate_options_rec(analysis)
        
        # AI analysis if available
        if self.anthropic_key:
            self._get_ai_analysis(analysis)
        
        return analysis
    
    def _fetch_price_data(self, analysis: StockAnalysis):
        """Fetch current price data"""
        try:
            data = self.api.get_stock_snapshot(analysis.symbol)
            if data:
                analysis.price = data.get('price', 0)
                analysis.change = data.get('change', 0)
                analysis.change_pct = data.get('change_pct', 0)
                analysis.name = data.get('name', analysis.symbol)
        except Exception as e:
            print(f"Price fetch error for {analysis.symbol}: {e}")
    
    def _calculate_technicals(self, analysis: StockAnalysis):
        """Calculate technical indicators"""
        try:
            # Get historical data
            history = self.api.get_stock_history(analysis.symbol, 100)
            if not history or len(history) < 20:
                return
            
            closes = [bar['c'] for bar in history]
            volumes = [bar['v'] for bar in history]
            highs = [bar['h'] for bar in history]
            lows = [bar['l'] for bar in history]
            
            tech = analysis.technicals
            price = analysis.price or closes[-1]
            
            # Moving averages
            ema_20 = self._calc_ema(closes, 20)
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else closes[-1]
            sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else closes[-1]
            
            tech.above_20ema = price > ema_20
            tech.above_50sma = price > sma_50
            tech.above_200sma = price > sma_200
            
            # EMA alignment
            ema_9 = self._calc_ema(closes, 9)
            ema_21 = self._calc_ema(closes, 21)
            if ema_9 > ema_21 > sma_50:
                tech.ema_alignment = "BULLISH"
            elif ema_9 < ema_21 < sma_50:
                tech.ema_alignment = "BEARISH"
            else:
                tech.ema_alignment = "MIXED"
            
            # Trend score
            trend_score = 0
            if tech.above_20ema: trend_score += 25
            if tech.above_50sma: trend_score += 25
            if tech.above_200sma: trend_score += 25
            if tech.ema_alignment == "BULLISH": trend_score += 25
            elif tech.ema_alignment == "BEARISH": trend_score -= 50
            tech.trend_score = trend_score
            
            if trend_score >= 75:
                tech.trend_direction = "STRONG_UP"
            elif trend_score >= 50:
                tech.trend_direction = "UP"
            elif trend_score >= 25:
                tech.trend_direction = "WEAK_UP"
            elif trend_score <= -50:
                tech.trend_direction = "STRONG_DOWN"
            elif trend_score <= -25:
                tech.trend_direction = "DOWN"
            else:
                tech.trend_direction = "NEUTRAL"
            
            # RSI
            tech.rsi = self._calc_rsi(closes)
            if tech.rsi < 30:
                tech.rsi_signal = "OVERSOLD"
            elif tech.rsi > 70:
                tech.rsi_signal = "OVERBOUGHT"
            else:
                tech.rsi_signal = "NEUTRAL"
            
            # MACD
            ema_12 = self._calc_ema(closes, 12)
            ema_26 = self._calc_ema(closes, 26)
            macd_line = ema_12 - ema_26
            
            # Simplified MACD signal
            prev_closes = closes[:-1]
            prev_ema_12 = self._calc_ema(prev_closes, 12)
            prev_ema_26 = self._calc_ema(prev_closes, 26)
            prev_macd = prev_ema_12 - prev_ema_26
            
            tech.macd_histogram = macd_line - prev_macd
            if macd_line > 0 and tech.macd_histogram > 0:
                tech.macd_signal = "BULLISH"
            elif macd_line < 0 and tech.macd_histogram < 0:
                tech.macd_signal = "BEARISH"
            else:
                tech.macd_signal = "NEUTRAL"
            
            # Momentum score
            mom_score = 0
            if tech.rsi_signal == "OVERSOLD": mom_score += 30  # Bounce potential
            elif tech.rsi_signal == "OVERBOUGHT": mom_score -= 20
            elif 40 <= tech.rsi <= 60: mom_score += 10  # Healthy
            
            if tech.macd_signal == "BULLISH": mom_score += 40
            elif tech.macd_signal == "BEARISH": mom_score -= 40
            
            tech.momentum_score = mom_score
            
            # Volume
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]
            tech.volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if tech.volume_ratio > 2.5:
                tech.volume_trend = "CLIMACTIC"
                tech.volume_score = 100
            elif tech.volume_ratio > 1.5:
                tech.volume_trend = "HIGH"
                tech.volume_score = 75
            elif tech.volume_ratio > 0.7:
                tech.volume_trend = "NORMAL"
                tech.volume_score = 50
            else:
                tech.volume_trend = "LOW"
                tech.volume_score = 25
            
            # ATR
            atr_sum = 0
            for i in range(1, min(15, len(closes))):
                tr = max(
                    highs[-i] - lows[-i],
                    abs(highs[-i] - closes[-i-1]),
                    abs(lows[-i] - closes[-i-1])
                )
                atr_sum += tr
            tech.atr = atr_sum / 14
            tech.atr_percent = (tech.atr / price * 100) if price > 0 else 0
            
            # Pattern detection (simplified)
            patterns = []
            
            # Breakout detection
            recent_high = max(highs[-20:])
            if price > recent_high * 0.98:
                patterns.append("NEAR_BREAKOUT")
            if price > recent_high:
                patterns.append("BREAKOUT")
            
            # Pullback to EMA
            if tech.above_50sma and abs(price - ema_21) / ema_21 < 0.02:
                patterns.append("PULLBACK_TO_21EMA")
            
            # Squeeze (low ATR)
            if tech.atr_percent < 2:
                patterns.append("SQUEEZE")
            
            # Reversal (oversold + bullish divergence hint)
            if tech.rsi < 35 and price > closes[-5]:
                patterns.append("POTENTIAL_REVERSAL")
            
            tech.patterns = patterns
            
            # Overall technical score
            tech.overall_score = (
                (tech.trend_score + 100) / 2 * 0.35 +  # Normalize to 0-100
                (tech.momentum_score + 100) / 2 * 0.30 +
                tech.volume_score * 0.20 +
                (50 if patterns else 30) * 0.15
            )
            
            # Signal
            if tech.overall_score >= 75:
                tech.signal = SignalStrength.STRONG_BULLISH
            elif tech.overall_score >= 60:
                tech.signal = SignalStrength.BULLISH
            elif tech.overall_score >= 52:
                tech.signal = SignalStrength.WEAK_BULLISH
            elif tech.overall_score <= 25:
                tech.signal = SignalStrength.STRONG_BEARISH
            elif tech.overall_score <= 40:
                tech.signal = SignalStrength.BEARISH
            elif tech.overall_score <= 48:
                tech.signal = SignalStrength.WEAK_BEARISH
            else:
                tech.signal = SignalStrength.NEUTRAL
                
        except Exception as e:
            print(f"Technical calc error for {analysis.symbol}: {e}")
    
    def _check_catalysts(self, analysis: StockAnalysis):
        """Check for upcoming catalysts"""
        # In production, you'd fetch from earnings calendars, news APIs, etc.
        # For now, we'll add placeholder logic
        
        catalysts = []
        
        # High volume = potential catalyst
        if analysis.technicals.volume_ratio > 2:
            catalysts.append(Catalyst(
                type=CatalystType.UNUSUAL_VOLUME,
                date=datetime.now().strftime("%Y-%m-%d"),
                description=f"Volume {analysis.technicals.volume_ratio:.1f}x average",
                impact="MEDIUM"
            ))
        
        # Technical breakout
        if "BREAKOUT" in analysis.technicals.patterns:
            catalysts.append(Catalyst(
                type=CatalystType.TECHNICAL_BREAKOUT,
                date=datetime.now().strftime("%Y-%m-%d"),
                description="Breaking out of recent range",
                impact="HIGH"
            ))
        
        analysis.catalysts = catalysts
    
    def _set_demo_data(self, analysis: StockAnalysis):
        """Set demo data when no API available"""
        import random
        analysis.price = random.uniform(50, 500)
        analysis.change_pct = random.uniform(-3, 3)
        analysis.technicals.overall_score = random.uniform(30, 80)
        analysis.technicals.rsi = random.uniform(30, 70)
        analysis.technicals.trend_direction = random.choice(["UP", "NEUTRAL", "DOWN"])
    
    def _calculate_hot_score(self, analysis: StockAnalysis):
        """Calculate hot score for ranking"""
        score = 0
        alerts = []
        
        tech = analysis.technicals
        
        # Technical score contribution (40%)
        score += tech.overall_score * 0.40
        
        # Momentum bonus (20%)
        if tech.signal in [SignalStrength.STRONG_BULLISH, SignalStrength.BULLISH]:
            score += 20
            alerts.append("🔥 Bullish momentum")
        elif tech.signal in [SignalStrength.STRONG_BEARISH, SignalStrength.BEARISH]:
            score += 15  # Bearish setups can be hot too (for puts)
            alerts.append("📉 Bearish momentum")
        
        # Pattern bonus (15%)
        if "BREAKOUT" in tech.patterns:
            score += 15
            alerts.append("🚀 Breakout!")
        elif "NEAR_BREAKOUT" in tech.patterns:
            score += 10
            alerts.append("👀 Near breakout")
        elif "PULLBACK_TO_21EMA" in tech.patterns:
            score += 12
            alerts.append("📍 Pullback to 21 EMA")
        elif "SQUEEZE" in tech.patterns:
            score += 8
            alerts.append("🔄 Squeeze forming")
        
        # Volume bonus (15%)
        if tech.volume_trend == "CLIMACTIC":
            score += 15
            alerts.append("📊 Climactic volume")
        elif tech.volume_trend == "HIGH":
            score += 10
            alerts.append("📊 High volume")
        
        # RSI bonus (10%)
        if tech.rsi < 35:
            score += 10
            alerts.append("💰 Oversold bounce candidate")
        elif 45 <= tech.rsi <= 55:
            score += 5  # Healthy, not extended
        
        # Catalyst bonus
        for cat in analysis.catalysts:
            if cat.impact == "HIGH":
                score += 10
            elif cat.impact == "MEDIUM":
                score += 5
        
        analysis.hot_score = min(100, score)
        analysis.alerts = alerts
        
        # Determine setup quality
        if score >= 80:
            analysis.setup_quality = SetupQuality.A_PLUS
            analysis.is_hot = True
        elif score >= 70:
            analysis.setup_quality = SetupQuality.A
            analysis.is_hot = True
        elif score >= 60:
            analysis.setup_quality = SetupQuality.B
            analysis.is_hot = True
        elif score >= 50:
            analysis.setup_quality = SetupQuality.C
        elif score >= 40:
            analysis.setup_quality = SetupQuality.D
        else:
            analysis.setup_quality = SetupQuality.F
    
    def _generate_options_rec(self, analysis: StockAnalysis):
        """Generate options contract recommendation"""
        if analysis.hot_score < 50:
            return  # Don't recommend for weak setups
        
        tech = analysis.technicals
        price = analysis.price
        atr = tech.atr or (price * 0.02)
        
        # Determine direction
        if tech.signal in [SignalStrength.STRONG_BULLISH, SignalStrength.BULLISH, SignalStrength.WEAK_BULLISH]:
            direction = "CALL"
            target = price + (2.5 * atr)
            stop = price - (1.5 * atr)
            delta = 0.55 if analysis.setup_quality in [SetupQuality.A_PLUS, SetupQuality.A] else 0.50
        else:
            direction = "PUT"
            target = price - (2.5 * atr)
            stop = price + (1.5 * atr)
            delta = -0.55 if analysis.setup_quality in [SetupQuality.A_PLUS, SetupQuality.A] else -0.50
        
        # Calculate strike (ITM based on delta)
        if direction == "CALL":
            # For 0.55 delta call, strike slightly ITM
            strike = round(price * 0.97 / 5) * 5  # Round to $5 increments
        else:
            strike = round(price * 1.03 / 5) * 5
        
        # DTE based on setup quality
        if analysis.setup_quality == SetupQuality.A_PLUS:
            dte = 21  # Can go shorter with high conviction
        elif analysis.setup_quality == SetupQuality.A:
            dte = 30
        else:
            dte = 45  # More time for less certain setups
        
        # Calculate expiration date
        exp_date = datetime.now() + timedelta(days=dte)
        # Find next Friday
        days_until_friday = (4 - exp_date.weekday()) % 7
        exp_date = exp_date + timedelta(days=days_until_friday)
        
        # Estimate option price (simplified)
        itm_amount = abs(price - strike)
        time_value = price * 0.02 * math.sqrt(dte / 365)  # Rough estimate
        est_price = itm_amount + time_value
        
        # Confidence
        if analysis.setup_quality in [SetupQuality.A_PLUS, SetupQuality.A]:
            confidence = "HIGH"
        elif analysis.setup_quality == SetupQuality.B:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Build reasoning
        reasons = []
        if tech.trend_direction in ["STRONG_UP", "UP"]:
            reasons.append("Uptrend intact")
        if tech.macd_signal == "BULLISH":
            reasons.append("MACD bullish")
        if tech.patterns:
            reasons.append(f"Pattern: {tech.patterns[0]}")
        if tech.volume_trend in ["HIGH", "CLIMACTIC"]:
            reasons.append("Strong volume")
        
        analysis.options_rec = OptionsRecommendation(
            direction=direction,
            strike=strike,
            expiration=exp_date.strftime("%Y-%m-%d"),
            delta=delta,
            entry_price_low=est_price * 0.95,
            entry_price_high=est_price * 1.05,
            stock_target=target,
            stock_stop=stop,
            profit_target_pct=50 if confidence == "HIGH" else 40,
            stop_loss_pct=-25 if confidence == "HIGH" else -30,
            suggested_dte=dte,
            reasoning="; ".join(reasons),
            confidence=confidence
        )
    
    def _get_ai_analysis(self, analysis: StockAnalysis):
        """Get AI-powered analysis from Claude"""
        if not self.anthropic_key:
            return
        
        try:
            prompt = f"""Analyze this stock for a short-term options trade (1-4 weeks):

Symbol: {analysis.symbol}
Price: ${analysis.price:.2f}
Change: {analysis.change_pct:+.1f}%
Trend: {analysis.technicals.trend_direction}
RSI: {analysis.technicals.rsi:.0f}
MACD: {analysis.technicals.macd_signal}
Volume: {analysis.technicals.volume_ratio:.1f}x average
Patterns: {', '.join(analysis.technicals.patterns) or 'None'}
Setup Score: {analysis.hot_score:.0f}/100

Provide a brief analysis in this exact format:
SUMMARY: (1 sentence overall view)
BULL_CASE: (1 sentence why it could go up)
BEAR_CASE: (1 sentence why it could go down)
RECOMMENDATION: (BUY CALLS / BUY PUTS / WAIT / AVOID) with 1 sentence reason"""

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result['content'][0]['text']
                
                # Parse response
                for line in text.split('\n'):
                    if line.startswith('SUMMARY:'):
                        analysis.ai_summary = line.replace('SUMMARY:', '').strip()
                    elif line.startswith('BULL_CASE:'):
                        analysis.ai_bull_case = line.replace('BULL_CASE:', '').strip()
                    elif line.startswith('BEAR_CASE:'):
                        analysis.ai_bear_case = line.replace('BEAR_CASE:', '').strip()
                    elif line.startswith('RECOMMENDATION:'):
                        analysis.ai_recommendation = line.replace('RECOMMENDATION:', '').strip()
                        
        except Exception as e:
            print(f"AI analysis error: {e}")
    
    def scan_watchlist(self) -> List[StockAnalysis]:
        """Scan entire watchlist and return analyses"""
        analyses = []
        
        for symbol in self.watchlist:
            if self.watchlist[symbol].active:
                try:
                    analysis = self.analyze_stock(symbol)
                    analyses.append(analysis)
                    time.sleep(0.25)  # Rate limiting
                except Exception as e:
                    print(f"Error analyzing {symbol}: {e}")
        
        return sorted(analyses, key=lambda x: x.hot_score, reverse=True)
    
    def get_hot_list(self, limit: int = 10) -> List[HotListEntry]:
        """Get top hot stocks from watchlist"""
        analyses = self.scan_watchlist()
        hot_list = []
        
        for i, analysis in enumerate(analyses[:limit]):
            if analysis.hot_score >= 50:  # Only include decent setups
                entry = HotListEntry(
                    rank=i + 1,
                    symbol=analysis.symbol,
                    name=analysis.name,
                    price=analysis.price,
                    change_pct=analysis.change_pct,
                    hot_score=analysis.hot_score,
                    setup_quality=analysis.setup_quality.value,
                    signal=analysis.technicals.signal.value,
                    headline=analysis.alerts[0] if analysis.alerts else "Setup forming",
                    options_rec={
                        'direction': analysis.options_rec.direction,
                        'strike': analysis.options_rec.strike,
                        'expiration': analysis.options_rec.expiration,
                        'confidence': analysis.options_rec.confidence,
                        'target': analysis.options_rec.stock_target,
                        'stop': analysis.options_rec.stock_stop,
                    } if analysis.options_rec else None
                )
                hot_list.append(entry)
        
        return hot_list
    
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


# Helper functions for web interface
def get_scanner_data(scanner: SmartScanner) -> Dict:
    """Get scanner data for web interface"""
    watchlist = [
        {
            'symbol': s.symbol,
            'name': s.name,
            'sector': s.sector,
            'thesis': s.thesis,
            'priority': s.priority,
            'active': s.active,
        }
        for s in scanner.watchlist.values()
    ]
    
    return {
        'watchlist': watchlist,
        'watchlist_count': len(watchlist),
    }


def get_hot_list_data(scanner: SmartScanner) -> Dict:
    """Get hot list data for web interface"""
    hot_list = scanner.get_hot_list(10)
    
    return {
        'hot_list': [
            {
                'rank': h.rank,
                'symbol': h.symbol,
                'name': h.name,
                'price': h.price,
                'change_pct': h.change_pct,
                'hot_score': h.hot_score,
                'setup_quality': h.setup_quality,
                'signal': h.signal,
                'headline': h.headline,
                'options_rec': h.options_rec,
            }
            for h in hot_list
        ],
        'scanned_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_stock_analysis_data(scanner: SmartScanner, symbol: str) -> Dict:
    """Get detailed analysis for a single stock"""
    analysis = scanner.analyze_stock(symbol)
    
    return {
        'symbol': analysis.symbol,
        'name': analysis.name,
        'price': analysis.price,
        'change_pct': analysis.change_pct,
        'hot_score': analysis.hot_score,
        'setup_quality': analysis.setup_quality.value,
        'is_hot': analysis.is_hot,
        'alerts': analysis.alerts,
        
        'technicals': {
            'trend_direction': analysis.technicals.trend_direction,
            'trend_score': analysis.technicals.trend_score,
            'rsi': analysis.technicals.rsi,
            'rsi_signal': analysis.technicals.rsi_signal,
            'macd_signal': analysis.technicals.macd_signal,
            'volume_ratio': analysis.technicals.volume_ratio,
            'volume_trend': analysis.technicals.volume_trend,
            'atr': analysis.technicals.atr,
            'atr_percent': analysis.technicals.atr_percent,
            'ema_alignment': analysis.technicals.ema_alignment,
            'above_200sma': analysis.technicals.above_200sma,
            'patterns': analysis.technicals.patterns,
            'overall_score': analysis.technicals.overall_score,
            'signal': analysis.technicals.signal.value,
        },
        
        'catalysts': [
            {
                'type': c.type.value,
                'date': c.date,
                'description': c.description,
                'impact': c.impact,
            }
            for c in analysis.catalysts
        ],
        
        'ai': {
            'summary': analysis.ai_summary,
            'bull_case': analysis.ai_bull_case,
            'bear_case': analysis.ai_bear_case,
            'recommendation': analysis.ai_recommendation,
        },
        
        'options_rec': {
            'direction': analysis.options_rec.direction,
            'strike': analysis.options_rec.strike,
            'expiration': analysis.options_rec.expiration,
            'delta': analysis.options_rec.delta,
            'entry_low': analysis.options_rec.entry_price_low,
            'entry_high': analysis.options_rec.entry_price_high,
            'stock_target': analysis.options_rec.stock_target,
            'stock_stop': analysis.options_rec.stock_stop,
            'profit_target_pct': analysis.options_rec.profit_target_pct,
            'stop_loss_pct': analysis.options_rec.stop_loss_pct,
            'dte': analysis.options_rec.suggested_dte,
            'reasoning': analysis.options_rec.reasoning,
            'confidence': analysis.options_rec.confidence,
        } if analysis.options_rec else None,
        
        'analyzed_at': analysis.analyzed_at,
    }
