"""
Trading Cockpit - Portfolio Risk Module
========================================
Aggregates risk across all positions to prevent overexposure.

Features:
- Portfolio Greeks (total delta, gamma, theta, vega)
- Sector/correlation analysis
- Max loss calculation
- Capital at risk tracking
- Position sizing recommendations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import math


class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PortfolioGreeks:
    """Aggregated portfolio Greeks"""
    total_delta: float = 0.0          # Net directional exposure
    total_gamma: float = 0.0          # Rate of delta change
    total_theta: float = 0.0          # Daily time decay ($)
    total_vega: float = 0.0           # Volatility exposure
    
    # Normalized metrics
    delta_dollars: float = 0.0        # Delta * notional value
    gamma_dollars: float = 0.0        # Gamma impact per 1% move
    
    # Interpretation
    directional_bias: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    
    @property
    def interpretation(self) -> str:
        if self.total_delta > 100:
            return f"Strong bullish bias (Δ {self.total_delta:.0f}) - consider hedging"
        elif self.total_delta > 50:
            return f"Bullish bias (Δ {self.total_delta:.0f})"
        elif self.total_delta < -100:
            return f"Strong bearish bias (Δ {self.total_delta:.0f}) - consider hedging"
        elif self.total_delta < -50:
            return f"Bearish bias (Δ {self.total_delta:.0f})"
        else:
            return f"Balanced exposure (Δ {self.total_delta:.0f})"


@dataclass
class SectorExposure:
    """Exposure by sector"""
    sector: str
    symbol_count: int = 0
    total_value: float = 0.0
    total_delta: float = 0.0
    pct_of_portfolio: float = 0.0
    symbols: List[str] = field(default_factory=list)


@dataclass
class CorrelationRisk:
    """Correlation and concentration risk"""
    # Sector concentration
    sectors: Dict[str, SectorExposure] = field(default_factory=dict)
    largest_sector: str = ""
    largest_sector_pct: float = 0.0
    
    # Concentration metrics
    concentration_score: float = 0.0   # 0-100, higher = more concentrated
    herfindahl_index: float = 0.0      # HHI for diversification
    
    # Correlation estimate
    avg_correlation: float = 0.0       # Estimated avg correlation
    diversification_benefit: float = 0.0
    
    @property
    def risk_level(self) -> RiskLevel:
        if self.concentration_score >= 80:
            return RiskLevel.CRITICAL
        elif self.concentration_score >= 60:
            return RiskLevel.HIGH
        elif self.concentration_score >= 40:
            return RiskLevel.ELEVATED
        elif self.concentration_score >= 20:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    @property
    def interpretation(self) -> str:
        if self.concentration_score >= 70:
            return f"⚠️ HIGH CONCENTRATION in {self.largest_sector} ({self.largest_sector_pct:.0f}%) - diversify!"
        elif self.concentration_score >= 50:
            return f"Moderate concentration in {self.largest_sector} ({self.largest_sector_pct:.0f}%)"
        else:
            return "Well diversified across sectors"


@dataclass
class RiskMetrics:
    """Key risk metrics"""
    # Capital metrics
    total_capital: float = 0.0         # Total account value
    capital_at_risk: float = 0.0       # $ at risk if all stops hit
    capital_at_risk_pct: float = 0.0   # % of account at risk
    
    # Max loss scenarios
    max_loss_all_stops: float = 0.0    # If all positions stopped out
    max_loss_10pct_drop: float = 0.0   # If market drops 10%
    max_loss_20pct_drop: float = 0.0   # If market drops 20%
    
    # Position metrics
    position_count: int = 0
    avg_position_size: float = 0.0
    largest_position: float = 0.0
    largest_position_pct: float = 0.0
    
    # Risk levels
    overall_risk: RiskLevel = RiskLevel.MODERATE
    
    @property
    def risk_color(self) -> str:
        colors = {
            RiskLevel.LOW: "green",
            RiskLevel.MODERATE: "yellow",
            RiskLevel.ELEVATED: "orange",
            RiskLevel.HIGH: "red",
            RiskLevel.CRITICAL: "red",
        }
        return colors.get(self.overall_risk, "white")


@dataclass
class PositionSizing:
    """Position sizing recommendations"""
    # Current state
    current_positions: int = 0
    max_recommended: int = 5
    can_add_position: bool = True
    
    # Sizing for next trade
    recommended_size_pct: float = 2.0   # % of capital for next trade
    recommended_contracts: int = 1
    max_risk_per_trade: float = 0.0     # Max $ to risk
    
    # Reasoning
    sizing_factors: List[str] = field(default_factory=list)


@dataclass
class PortfolioRiskSummary:
    """Complete portfolio risk summary"""
    # Greeks
    greeks: PortfolioGreeks = field(default_factory=PortfolioGreeks)
    
    # Concentration
    correlation: CorrelationRisk = field(default_factory=CorrelationRisk)
    
    # Risk metrics
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Sizing
    sizing: PositionSizing = field(default_factory=PositionSizing)
    
    # Overall
    overall_score: float = 50.0        # 0-100, higher = healthier
    headline: str = ""
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# Sector mappings
SECTOR_MAP = {
    # Technology
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
    'META': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology',
    'CRM': 'Technology', 'ADBE': 'Technology', 'ORCL': 'Technology', 'CSCO': 'Technology',
    'AVGO': 'Technology', 'TXN': 'Technology', 'QCOM': 'Technology', 'MU': 'Technology',
    'AMAT': 'Technology', 'LRCX': 'Technology', 'KLAC': 'Technology', 'MRVL': 'Technology',
    'TSM': 'Technology', 'ASML': 'Technology', 'BIDU': 'Technology', 'BABA': 'Technology',
    'JD': 'Technology', 'PDD': 'Technology', 'NTES': 'Technology',
    
    # Consumer Discretionary
    'AMZN': 'Consumer', 'TSLA': 'Consumer', 'HD': 'Consumer', 'NKE': 'Consumer',
    'MCD': 'Consumer', 'SBUX': 'Consumer', 'TGT': 'Consumer', 'LOW': 'Consumer',
    'COST': 'Consumer', 'WMT': 'Consumer', 'DIS': 'Consumer', 'NFLX': 'Consumer',
    
    # Financials
    'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
    'MS': 'Financials', 'C': 'Financials', 'BLK': 'Financials', 'SCHW': 'Financials',
    'V': 'Financials', 'MA': 'Financials', 'AXP': 'Financials', 'PYPL': 'Financials',
    
    # Healthcare
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'MRK': 'Healthcare',
    'ABBV': 'Healthcare', 'LLY': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare',
    
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
    'OXY': 'Energy', 'EOG': 'Energy', 'MPC': 'Energy', 'VLO': 'Energy',
    
    # Industrials
    'CAT': 'Industrials', 'BA': 'Industrials', 'HON': 'Industrials', 'UPS': 'Industrials',
    'UNP': 'Industrials', 'DE': 'Industrials', 'LMT': 'Industrials', 'RTX': 'Industrials',
    
    # Default
}


class PortfolioRiskAnalyzer:
    """Analyzes portfolio-level risk"""
    
    def __init__(self, positions: List = None, total_capital: float = 100000):
        self.positions = positions or []
        self.total_capital = total_capital
    
    def analyze(self) -> PortfolioRiskSummary:
        """Generate complete portfolio risk analysis"""
        summary = PortfolioRiskSummary()
        
        if not self.positions:
            summary.headline = "📊 No Open Positions"
            summary.recommendations = ["Portfolio is empty - look for opportunities"]
            return summary
        
        # Calculate Greeks
        self._calculate_greeks(summary)
        
        # Calculate correlation/concentration
        self._calculate_correlation(summary)
        
        # Calculate risk metrics
        self._calculate_risk_metrics(summary)
        
        # Position sizing
        self._calculate_sizing(summary)
        
        # Overall assessment
        self._calculate_overall(summary)
        
        return summary
    
    def _calculate_greeks(self, summary: PortfolioRiskSummary):
        """Aggregate portfolio Greeks"""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        
        for pos in self.positions:
            # Get position Greeks (multiply by quantity)
            qty = pos.quantity
            delta = (pos.greeks.delta or 0.5) * qty * 100
            gamma = (pos.greeks.gamma or 0.02) * qty * 100
            theta = (pos.greeks.theta or 0) * qty
            vega = (pos.greeks.vega or 0) * qty
            
            # Calls are positive delta, puts are negative
            if not pos.is_call:
                delta = -abs(delta)
            
            total_delta += delta
            total_gamma += gamma
            total_theta += theta
            total_vega += vega
        
        summary.greeks.total_delta = total_delta
        summary.greeks.total_gamma = total_gamma
        summary.greeks.total_theta = total_theta
        summary.greeks.total_vega = total_vega
        
        # Directional bias
        if total_delta > 50:
            summary.greeks.directional_bias = "BULLISH"
        elif total_delta < -50:
            summary.greeks.directional_bias = "BEARISH"
        else:
            summary.greeks.directional_bias = "NEUTRAL"
    
    def _calculate_correlation(self, summary: PortfolioRiskSummary):
        """Calculate sector concentration and correlation"""
        sectors = {}
        total_value = 0
        
        for pos in self.positions:
            symbol = pos.symbol
            sector = SECTOR_MAP.get(symbol, "Other")
            value = pos.current_option_price * pos.quantity * 100
            delta = (pos.greeks.delta or 0.5) * pos.quantity * 100
            
            if sector not in sectors:
                sectors[sector] = SectorExposure(sector=sector)
            
            sectors[sector].symbol_count += 1
            sectors[sector].total_value += value
            sectors[sector].total_delta += delta
            sectors[sector].symbols.append(symbol)
            total_value += value
        
        # Calculate percentages
        for sector_name, exposure in sectors.items():
            exposure.pct_of_portfolio = (exposure.total_value / total_value * 100) if total_value > 0 else 0
        
        summary.correlation.sectors = sectors
        
        # Find largest sector
        if sectors:
            largest = max(sectors.values(), key=lambda x: x.pct_of_portfolio)
            summary.correlation.largest_sector = largest.sector
            summary.correlation.largest_sector_pct = largest.pct_of_portfolio
        
        # Concentration score (HHI-based)
        hhi = sum((exp.pct_of_portfolio / 100) ** 2 for exp in sectors.values())
        summary.correlation.herfindahl_index = hhi
        
        # Normalize to 0-100 score
        # HHI of 1 = fully concentrated, HHI of 1/n = perfectly diversified
        n_sectors = len(sectors) if sectors else 1
        min_hhi = 1 / n_sectors
        summary.correlation.concentration_score = ((hhi - min_hhi) / (1 - min_hhi)) * 100 if n_sectors > 1 else 100
    
    def _calculate_risk_metrics(self, summary: PortfolioRiskSummary):
        """Calculate risk metrics"""
        summary.risk.total_capital = self.total_capital
        summary.risk.position_count = len(self.positions)
        
        total_at_risk = 0
        total_value = 0
        max_position = 0
        
        for pos in self.positions:
            value = pos.current_option_price * pos.quantity * 100
            total_value += value
            
            # Risk at stop (or max loss = full premium)
            stop_loss = getattr(pos.stops, 'risk_at_stop', value) if hasattr(pos, 'stops') else value
            total_at_risk += abs(stop_loss) if stop_loss else value
            
            if value > max_position:
                max_position = value
        
        summary.risk.capital_at_risk = total_at_risk
        summary.risk.capital_at_risk_pct = (total_at_risk / self.total_capital * 100) if self.total_capital > 0 else 0
        
        summary.risk.max_loss_all_stops = total_at_risk
        summary.risk.avg_position_size = total_value / len(self.positions) if self.positions else 0
        summary.risk.largest_position = max_position
        summary.risk.largest_position_pct = (max_position / self.total_capital * 100) if self.total_capital > 0 else 0
        
        # Determine overall risk level
        car_pct = summary.risk.capital_at_risk_pct
        if car_pct >= 25:
            summary.risk.overall_risk = RiskLevel.CRITICAL
        elif car_pct >= 15:
            summary.risk.overall_risk = RiskLevel.HIGH
        elif car_pct >= 10:
            summary.risk.overall_risk = RiskLevel.ELEVATED
        elif car_pct >= 5:
            summary.risk.overall_risk = RiskLevel.MODERATE
        else:
            summary.risk.overall_risk = RiskLevel.LOW
    
    def _calculate_sizing(self, summary: PortfolioRiskSummary):
        """Calculate position sizing recommendations"""
        summary.sizing.current_positions = len(self.positions)
        
        # Adjust max positions based on risk
        if summary.risk.overall_risk == RiskLevel.CRITICAL:
            summary.sizing.max_recommended = 2
            summary.sizing.can_add_position = False
        elif summary.risk.overall_risk == RiskLevel.HIGH:
            summary.sizing.max_recommended = 3
            summary.sizing.can_add_position = summary.sizing.current_positions < 3
        elif summary.risk.overall_risk == RiskLevel.ELEVATED:
            summary.sizing.max_recommended = 4
            summary.sizing.can_add_position = summary.sizing.current_positions < 4
        else:
            summary.sizing.max_recommended = 5
            summary.sizing.can_add_position = summary.sizing.current_positions < 5
        
        # Recommended size for next trade
        remaining_risk_budget = max(0, 10 - summary.risk.capital_at_risk_pct)
        summary.sizing.recommended_size_pct = min(2, remaining_risk_budget / 2)
        summary.sizing.max_risk_per_trade = self.total_capital * summary.sizing.recommended_size_pct / 100
        
        # Sizing factors
        factors = []
        if summary.risk.capital_at_risk_pct > 10:
            factors.append("⚠️ Already at risk limit - reduce before adding")
        if summary.correlation.concentration_score > 60:
            factors.append(f"⚠️ High {summary.correlation.largest_sector} concentration - diversify")
        if summary.greeks.total_delta > 200:
            factors.append("⚠️ High bullish delta - consider hedging or neutral trades")
        elif summary.greeks.total_delta < -200:
            factors.append("⚠️ High bearish delta - consider hedging or bullish trades")
        if summary.greeks.total_theta < -50:
            factors.append(f"⚠️ Theta bleeding ${abs(summary.greeks.total_theta):.0f}/day")
        
        summary.sizing.sizing_factors = factors
    
    def _calculate_overall(self, summary: PortfolioRiskSummary):
        """Calculate overall portfolio health"""
        score = 70  # Start at decent baseline
        warnings = []
        recommendations = []
        
        # Risk penalty
        if summary.risk.overall_risk == RiskLevel.CRITICAL:
            score -= 30
            warnings.append("🚨 CRITICAL: Capital at risk exceeds 25%")
            recommendations.append("Close losing positions immediately")
        elif summary.risk.overall_risk == RiskLevel.HIGH:
            score -= 20
            warnings.append("⚠️ HIGH RISK: Capital at risk exceeds 15%")
            recommendations.append("Reduce position sizes or close weakest positions")
        elif summary.risk.overall_risk == RiskLevel.ELEVATED:
            score -= 10
            warnings.append("📊 Elevated risk: Capital at risk ~10%")
        
        # Concentration penalty
        if summary.correlation.concentration_score > 70:
            score -= 15
            warnings.append(f"⚠️ Over-concentrated in {summary.correlation.largest_sector}")
            recommendations.append("Add positions in different sectors")
        elif summary.correlation.concentration_score > 50:
            score -= 8
        
        # Theta penalty
        if summary.greeks.total_theta < -100:
            score -= 10
            warnings.append(f"⏰ Heavy theta decay: ${abs(summary.greeks.total_theta):.0f}/day")
            recommendations.append("Close near-expiry positions or roll out")
        
        # Delta imbalance
        if abs(summary.greeks.total_delta) > 300:
            score -= 10
            warnings.append(f"📈 Large directional bet: Δ {summary.greeks.total_delta:.0f}")
            recommendations.append("Consider hedging with opposite direction")
        
        # Position count bonus/penalty
        if summary.sizing.current_positions == 0:
            score = 50
            recommendations.append("Look for high-probability setups")
        elif summary.sizing.current_positions <= 3:
            score += 5  # Good focus
        elif summary.sizing.current_positions > 6:
            score -= 5
            warnings.append("Too many positions - harder to manage")
        
        summary.overall_score = max(0, min(100, score))
        summary.warnings = warnings
        summary.recommendations = recommendations
        
        # Headline
        if score >= 70:
            summary.headline = "✅ Portfolio Health: GOOD"
        elif score >= 50:
            summary.headline = "🟡 Portfolio Health: MODERATE"
        elif score >= 30:
            summary.headline = "🟠 Portfolio Health: NEEDS ATTENTION"
        else:
            summary.headline = "🔴 Portfolio Health: CRITICAL"


def get_portfolio_risk_dict(positions: List, total_capital: float = 100000) -> Dict:
    """Get portfolio risk as dictionary for web interface"""
    analyzer = PortfolioRiskAnalyzer(positions, total_capital)
    summary = analyzer.analyze()
    
    return {
        'headline': summary.headline,
        'overall_score': summary.overall_score,
        'warnings': summary.warnings,
        'recommendations': summary.recommendations,
        
        'greeks': {
            'total_delta': summary.greeks.total_delta,
            'total_gamma': summary.greeks.total_gamma,
            'total_theta': summary.greeks.total_theta,
            'total_vega': summary.greeks.total_vega,
            'directional_bias': summary.greeks.directional_bias,
            'interpretation': summary.greeks.interpretation,
        },
        
        'correlation': {
            'sectors': {
                name: {
                    'symbol_count': exp.symbol_count,
                    'total_value': exp.total_value,
                    'pct_of_portfolio': exp.pct_of_portfolio,
                    'symbols': exp.symbols,
                }
                for name, exp in summary.correlation.sectors.items()
            },
            'largest_sector': summary.correlation.largest_sector,
            'largest_sector_pct': summary.correlation.largest_sector_pct,
            'concentration_score': summary.correlation.concentration_score,
            'risk_level': summary.correlation.risk_level.value,
            'interpretation': summary.correlation.interpretation,
        },
        
        'risk': {
            'total_capital': summary.risk.total_capital,
            'capital_at_risk': summary.risk.capital_at_risk,
            'capital_at_risk_pct': summary.risk.capital_at_risk_pct,
            'max_loss_all_stops': summary.risk.max_loss_all_stops,
            'position_count': summary.risk.position_count,
            'avg_position_size': summary.risk.avg_position_size,
            'largest_position': summary.risk.largest_position,
            'largest_position_pct': summary.risk.largest_position_pct,
            'overall_risk': summary.risk.overall_risk.value,
        },
        
        'sizing': {
            'current_positions': summary.sizing.current_positions,
            'max_recommended': summary.sizing.max_recommended,
            'can_add_position': summary.sizing.can_add_position,
            'recommended_size_pct': summary.sizing.recommended_size_pct,
            'max_risk_per_trade': summary.sizing.max_risk_per_trade,
            'sizing_factors': summary.sizing.sizing_factors,
        },
    }
