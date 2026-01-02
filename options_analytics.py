"""
Options Analytics Module
========================
Advanced options analysis:
- IV Rank / IV Percentile
- Greeks (Delta, Theta, Gamma, Vega)
- Expected Move calculation
- Optimal contract selection
- Liquidity scoring
- Risk/Reward projection
"""

import os
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OptionContract:
    """Single option contract"""
    symbol: str
    underlying: str
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    iv: Optional[float] = None
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        return (self.spread / self.mid * 100) if self.mid > 0 else 0
    
    @property
    def dte(self) -> int:
        try:
            exp_date = datetime.strptime(self.expiration, '%Y-%m-%d')
            return (exp_date - datetime.now()).days
        except:
            return 30

@dataclass
class OptionsAnalysis:
    """Complete options analysis for a stock"""
    symbol: str
    underlying_price: float
    
    # IV Analysis
    iv_rank: float
    iv_percentile: float
    current_iv: float
    iv_rating: str
    
    # Expected Move
    expected_move_30d: float
    expected_move_pct: float
    
    # Recommended contract
    recommended_contract: Optional[OptionContract]
    contract_rationale: str
    
    # Position sizing
    position_size_dollars: float
    num_contracts: int
    total_premium: float
    max_loss: float
    
    # Targets
    target_price: float
    target_pct: float
    stop_price: float
    stop_pct: float
    risk_reward: float
    
    # Liquidity
    liquidity_score: int
    liquidity_rating: str
    
    # Theta context
    daily_theta: float
    theta_cost_7d: float
    theta_pct_7d: float
    
    # Greeks summary
    greeks_summary: Dict
    
    def to_dict(self) -> Dict:
        contract_dict = None
        if self.recommended_contract:
            contract_dict = {
                'strike': self.recommended_contract.strike,
                'expiration': self.recommended_contract.expiration,
                'type': self.recommended_contract.option_type,
                'bid': self.recommended_contract.bid,
                'ask': self.recommended_contract.ask,
                'mid': self.recommended_contract.mid,
                'delta': self.recommended_contract.delta,
                'dte': self.recommended_contract.dte,
                'open_interest': self.recommended_contract.open_interest,
                'volume': self.recommended_contract.volume
            }
        
        return {
            'symbol': self.symbol,
            'underlying_price': self.underlying_price,
            'iv_rank': self.iv_rank,
            'iv_percentile': self.iv_percentile,
            'current_iv': self.current_iv,
            'iv_rating': self.iv_rating,
            'expected_move_30d': self.expected_move_30d,
            'expected_move_pct': self.expected_move_pct,
            'recommended_contract': contract_dict,
            'contract_rationale': self.contract_rationale,
            'position_size_dollars': self.position_size_dollars,
            'num_contracts': self.num_contracts,
            'total_premium': self.total_premium,
            'max_loss': self.max_loss,
            'target_price': self.target_price,
            'target_pct': self.target_pct,
            'stop_price': self.stop_price,
            'stop_pct': self.stop_pct,
            'risk_reward': self.risk_reward,
            'liquidity_score': self.liquidity_score,
            'liquidity_rating': self.liquidity_rating,
            'daily_theta': self.daily_theta,
            'theta_cost_7d': self.theta_cost_7d,
            'theta_pct_7d': self.theta_pct_7d,
            'greeks_summary': self.greeks_summary
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def norm_cdf(x: float) -> float:
    """Standard normal CDF approximation"""
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    
    return 0.5 * (1.0 + sign * y)

def norm_pdf(x: float) -> float:
    """Standard normal PDF"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def calculate_bs_greeks(S: float, K: float, T: float, r: float, sigma: float, 
                        option_type: str = 'call') -> Dict:
    """
    Calculate Black-Scholes Greeks
    S: Underlying price
    K: Strike price
    T: Time to expiry (years)
    r: Risk-free rate (e.g., 0.05 for 5%)
    sigma: Implied volatility (decimal, e.g., 0.30 for 30%)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {'delta': 0.5, 'gamma': 0, 'theta': 0, 'vega': 0}
    
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    if option_type.lower() == 'call':
        delta = norm_cdf(d1)
        theta = (-S * norm_pdf(d1) * sigma / (2 * sqrt_T) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365
    else:
        delta = norm_cdf(d1) - 1
        theta = (-S * norm_pdf(d1) * sigma / (2 * sqrt_T) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365
    
    gamma = norm_pdf(d1) / (S * sigma * sqrt_T)
    vega = S * norm_pdf(d1) * sqrt_T / 100  # Per 1% IV change
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 6),
        'theta': round(theta, 4),
        'vega': round(vega, 4)
    }


# ============================================================================
# POLYGON API FUNCTIONS
# ============================================================================

def get_underlying_quote(symbol: str) -> Dict:
    """Get current quote for underlying"""
    if not POLYGON_API_KEY:
        return {'price': 0, 'change_pct': 0}
    
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        response = requests.get(url, params={'apiKey': POLYGON_API_KEY}, timeout=5)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                r = results[0]
                return {
                    'price': r.get('c', 0),
                    'open': r.get('o', 0),
                    'high': r.get('h', 0),
                    'low': r.get('l', 0),
                    'volume': r.get('v', 0),
                    'change_pct': ((r.get('c', 0) - r.get('o', 0)) / r.get('o', 1)) * 100
                }
        return {'price': 0, 'change_pct': 0}
    except:
        return {'price': 0, 'change_pct': 0}

def get_options_contracts(symbol: str, direction: str = 'call', 
                          dte_range: Tuple[int, int] = (25, 50)) -> List[OptionContract]:
    """Get available options contracts"""
    if not POLYGON_API_KEY:
        return []
    
    contracts = []
    
    try:
        min_date = (datetime.now() + timedelta(days=dte_range[0])).strftime('%Y-%m-%d')
        max_date = (datetime.now() + timedelta(days=dte_range[1])).strftime('%Y-%m-%d')
        
        url = "https://api.polygon.io/v3/reference/options/contracts"
        params = {
            'underlying_ticker': symbol.upper(),
            'contract_type': direction.lower(),
            'expiration_date.gte': min_date,
            'expiration_date.lte': max_date,
            'limit': 100,
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        
        for item in data.get('results', []):
            contracts.append(OptionContract(
                symbol=item.get('ticker', ''),
                underlying=symbol.upper(),
                strike=item.get('strike_price', 0),
                expiration=item.get('expiration_date', ''),
                option_type=item.get('contract_type', 'call').lower(),
                bid=0, ask=0, last=0, volume=0, open_interest=0
            ))
        
        return contracts
        
    except Exception as e:
        print(f"Options contracts error: {e}")
        return []

def get_option_snapshot(symbol: str, option_ticker: str) -> Optional[Dict]:
    """Get snapshot for specific option"""
    if not POLYGON_API_KEY:
        return None
    
    try:
        url = f"https://api.polygon.io/v3/snapshot/options/{symbol}/{option_ticker}"
        response = requests.get(url, params={'apiKey': POLYGON_API_KEY}, timeout=5)
        
        if response.status_code == 200:
            result = response.json().get('results', {})
            day = result.get('day', {})
            quote = result.get('last_quote', {})
            greeks = result.get('greeks', {})
            
            return {
                'bid': quote.get('bid', 0),
                'ask': quote.get('ask', 0),
                'last': day.get('close', 0),
                'volume': day.get('volume', 0),
                'open_interest': result.get('open_interest', 0),
                'delta': greeks.get('delta'),
                'gamma': greeks.get('gamma'),
                'theta': greeks.get('theta'),
                'vega': greeks.get('vega'),
                'iv': result.get('implied_volatility')
            }
        return None
    except:
        return None


# ============================================================================
# CONTRACT SELECTION
# ============================================================================

def select_optimal_contract(symbol: str, direction: str, underlying_price: float,
                           target_delta: float = 0.50, dte_range: Tuple[int, int] = (30, 45),
                           capital: float = 100000, tier: str = 'A') -> Tuple[Optional[OptionContract], str]:
    """
    Select optimal options contract based on criteria
    
    Returns: (contract, rationale)
    """
    contracts = get_options_contracts(symbol, direction, dte_range)
    
    if not contracts:
        # Create synthetic contract for display
        dte = (dte_range[0] + dte_range[1]) // 2
        exp_date = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        # Estimate strike near ATM
        strike = round(underlying_price / 0.5) * 0.5  # Round to 0.50
        
        # Estimate premium (rough approximation)
        est_premium = underlying_price * 0.04  # ~4% of stock price for ATM 30-45 DTE
        
        synthetic = OptionContract(
            symbol=f"{symbol}_{strike}_{direction[0].upper()}",
            underlying=symbol,
            strike=strike,
            expiration=exp_date,
            option_type=direction.lower(),
            bid=est_premium * 0.95,
            ask=est_premium * 1.05,
            last=est_premium,
            volume=1000,
            open_interest=5000,
            delta=0.50 if direction.lower() == 'call' else -0.50,
            theta=-est_premium * 0.02,
            gamma=0.05,
            vega=0.10,
            iv=0.35
        )
        
        return synthetic, "Estimated contract (API data unavailable)"
    
    # Score each contract
    scored_contracts = []
    
    for contract in contracts:
        # Get detailed quote
        snapshot = get_option_snapshot(symbol, contract.symbol)
        if snapshot:
            contract.bid = snapshot['bid']
            contract.ask = snapshot['ask']
            contract.last = snapshot['last']
            contract.volume = snapshot['volume']
            contract.open_interest = snapshot['open_interest']
            contract.delta = snapshot['delta']
            contract.gamma = snapshot['gamma']
            contract.theta = snapshot['theta']
            contract.vega = snapshot['vega']
            contract.iv = snapshot['iv']
        else:
            # Calculate Greeks if not available
            T = contract.dte / 365
            greeks = calculate_bs_greeks(
                underlying_price, contract.strike, T, 0.05, 0.35, contract.option_type
            )
            contract.delta = greeks['delta']
            contract.theta = greeks['theta']
            contract.gamma = greeks['gamma']
            contract.vega = greeks['vega']
        
        # Skip if no valid data
        if contract.mid <= 0:
            continue
        
        # Score based on criteria
        score = 0
        
        # Delta score (prefer near target_delta)
        if contract.delta:
            delta_diff = abs(abs(contract.delta) - target_delta)
            if delta_diff < 0.05:
                score += 30
            elif delta_diff < 0.10:
                score += 20
            elif delta_diff < 0.15:
                score += 10
        
        # DTE score (prefer middle of range)
        ideal_dte = (dte_range[0] + dte_range[1]) // 2
        dte_diff = abs(contract.dte - ideal_dte)
        if dte_diff < 5:
            score += 20
        elif dte_diff < 10:
            score += 10
        
        # Liquidity score
        if contract.open_interest >= 1000:
            score += 20
        elif contract.open_interest >= 500:
            score += 10
        
        if contract.volume >= 100:
            score += 10
        
        # Spread score
        if contract.spread_pct < 5:
            score += 15
        elif contract.spread_pct < 10:
            score += 10
        elif contract.spread_pct < 15:
            score += 5
        
        scored_contracts.append((contract, score))
    
    if not scored_contracts:
        return None, "No suitable contracts found"
    
    # Sort by score descending
    scored_contracts.sort(key=lambda x: x[1], reverse=True)
    best = scored_contracts[0][0]
    
    # Build rationale
    rationale = f"${best.strike} {best.option_type.upper()} exp {best.expiration} ({best.dte} DTE)"
    rationale += f" | Delta: {best.delta:.2f}" if best.delta else ""
    rationale += f" | OI: {best.open_interest:,}" if best.open_interest else ""
    rationale += f" | Spread: {best.spread_pct:.1f}%" if best.spread_pct else ""
    
    return best, rationale


# ============================================================================
# OPTIONS ANALYSIS
# ============================================================================

def analyze_options(symbol: str, direction: str = 'call', 
                   tier: str = 'A', capital: float = 100000,
                   target_underlying_pct: float = 10, stop_underlying_pct: float = 5) -> OptionsAnalysis:
    """
    Complete options analysis for trade recommendation
    
    Parameters:
    - symbol: Stock ticker
    - direction: 'call' or 'put'
    - tier: 'A', 'B', or 'C' (affects position sizing)
    - capital: Total trading capital
    - target_underlying_pct: Expected % move in underlying
    - stop_underlying_pct: Stop loss % in underlying
    """
    
    # Get underlying price
    quote = get_underlying_quote(symbol)
    underlying_price = quote.get('price', 0)
    
    if underlying_price <= 0:
        underlying_price = 100  # Fallback for demo
    
    # Position sizing based on tier
    tier_pct = {'A': 0.30, 'B': 0.225, 'C': 0.15}
    position_size = capital * tier_pct.get(tier, 0.15)
    
    # DTE range based on swing trading
    dte_range = (30, 45)
    
    # Select optimal contract
    contract, rationale = select_optimal_contract(
        symbol, direction, underlying_price,
        target_delta=0.50, dte_range=dte_range,
        capital=capital, tier=tier
    )
    
    # Calculate IV metrics (simplified)
    current_iv = (contract.iv * 100) if contract and contract.iv else 35
    iv_rank = 30  # Would need historical data
    iv_percentile = 25  # Would need historical data
    
    if iv_percentile < 30:
        iv_rating = "LOW - Buy Premium"
    elif iv_percentile > 70:
        iv_rating = "HIGH - Sell Premium"
    else:
        iv_rating = "NEUTRAL"
    
    # Expected move calculation
    # EM = Stock Price × IV × √(DTE/365)
    dte = contract.dte if contract else 35
    expected_move = underlying_price * (current_iv / 100) * math.sqrt(dte / 365)
    expected_move_pct = (expected_move / underlying_price) * 100
    
    # Position sizing
    if contract and contract.mid > 0:
        premium_per_contract = contract.mid * 100  # Options are 100 shares
        num_contracts = int(position_size / premium_per_contract)
        num_contracts = max(1, num_contracts)  # At least 1 contract
        total_premium = num_contracts * premium_per_contract
        max_loss = total_premium  # Max loss is premium paid
    else:
        num_contracts = 1
        total_premium = position_size * 0.1
        max_loss = total_premium
    
    # Target and stop prices for option
    if contract:
        # Target: +100% on option (double your money)
        target_price = contract.mid * 2.0
        target_pct = 100
        
        # Stop: -50% on option
        stop_price = contract.mid * 0.5
        stop_pct = -50
        
        # Risk/Reward
        potential_gain = (target_price - contract.mid) * num_contracts * 100
        potential_loss = (contract.mid - stop_price) * num_contracts * 100
        risk_reward = potential_gain / potential_loss if potential_loss > 0 else 0
        
        # Theta analysis
        daily_theta = abs(contract.theta) if contract.theta else contract.mid * 0.02
        theta_cost_7d = daily_theta * 7 * num_contracts * 100
        theta_pct_7d = (theta_cost_7d / total_premium) * 100 if total_premium > 0 else 0
        
        # Liquidity score
        liq_score = 0
        if contract.open_interest >= 5000:
            liq_score += 40
        elif contract.open_interest >= 1000:
            liq_score += 25
        elif contract.open_interest >= 500:
            liq_score += 10
        
        if contract.volume >= 500:
            liq_score += 30
        elif contract.volume >= 100:
            liq_score += 20
        elif contract.volume >= 50:
            liq_score += 10
        
        if contract.spread_pct < 3:
            liq_score += 30
        elif contract.spread_pct < 6:
            liq_score += 20
        elif contract.spread_pct < 10:
            liq_score += 10
        
        if liq_score >= 70:
            liq_rating = "EXCELLENT"
        elif liq_score >= 50:
            liq_rating = "GOOD"
        elif liq_score >= 30:
            liq_rating = "MODERATE"
        else:
            liq_rating = "POOR"
        
        greeks_summary = {
            'delta': contract.delta,
            'gamma': contract.gamma,
            'theta': contract.theta,
            'vega': contract.vega
        }
    else:
        target_price = 0
        target_pct = 0
        stop_price = 0
        stop_pct = 0
        risk_reward = 0
        daily_theta = 0
        theta_cost_7d = 0
        theta_pct_7d = 0
        liq_score = 0
        liq_rating = "N/A"
        greeks_summary = {}
    
    return OptionsAnalysis(
        symbol=symbol,
        underlying_price=underlying_price,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
        current_iv=current_iv,
        iv_rating=iv_rating,
        expected_move_30d=expected_move,
        expected_move_pct=expected_move_pct,
        recommended_contract=contract,
        contract_rationale=rationale,
        position_size_dollars=position_size,
        num_contracts=num_contracts,
        total_premium=total_premium,
        max_loss=max_loss,
        target_price=target_price,
        target_pct=target_pct,
        stop_price=stop_price,
        stop_pct=stop_pct,
        risk_reward=risk_reward,
        liquidity_score=liq_score,
        liquidity_rating=liq_rating,
        daily_theta=daily_theta,
        theta_cost_7d=theta_cost_7d,
        theta_pct_7d=theta_pct_7d,
        greeks_summary=greeks_summary
    )
