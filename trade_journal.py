"""
Trading Cockpit - Trade Journal Module
======================================
Tracks trade history and performance analytics.

Features:
- Automatic trade logging
- Win rate, profit factor, expectancy
- Performance by setup type
- Performance by market regime
- Lessons learned tracking
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from statistics import mean, stdev


class TradeResult(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


class SetupType(Enum):
    BREAKOUT = "BREAKOUT"
    PULLBACK = "PULLBACK"
    REVERSAL = "REVERSAL"
    MOMENTUM = "MOMENTUM"
    EARNINGS = "EARNINGS"
    SWING = "SWING"
    SCALP = "SCALP"
    OTHER = "OTHER"


@dataclass
class TradeRecord:
    """Individual trade record"""
    # Identity
    id: str
    symbol: str
    
    # Trade details
    position_type: str               # LONG_CALL, LONG_PUT
    strike: float
    expiration: str
    quantity: int
    
    # Entry
    entry_date: str
    entry_stock_price: float
    entry_option_price: float
    entry_delta: float = 0.5
    entry_iv_rank: float = 50.0
    
    # Exit
    exit_date: str = ""
    exit_stock_price: float = 0.0
    exit_option_price: float = 0.0
    exit_reason: str = ""            # TARGET, STOP, TIME, MANUAL
    
    # P&L
    gross_pnl: float = 0.0
    fees: float = 0.0
    net_pnl: float = 0.0
    pnl_percent: float = 0.0
    
    # Context
    setup_type: str = "OTHER"
    market_regime: str = ""
    notes: str = ""
    lessons: str = ""
    
    # Scaling (if partial exits)
    partial_exits: List[Dict] = field(default_factory=list)
    
    # Result
    result: str = ""                 # WIN, LOSS, BREAKEVEN
    
    @property
    def hold_days(self) -> int:
        if not self.exit_date:
            return 0
        entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
        exit_dt = datetime.strptime(self.exit_date, "%Y-%m-%d")
        return (exit_dt - entry).days
    
    @property
    def is_closed(self) -> bool:
        return bool(self.exit_date)


@dataclass
class PerformanceStats:
    """Trading performance statistics"""
    # Basic stats
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    
    # Win rate
    win_rate: float = 0.0
    
    # P&L
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Ratios
    profit_factor: float = 0.0       # Gross profit / Gross loss
    expectancy: float = 0.0          # Expected $ per trade
    avg_risk_reward: float = 0.0
    
    # Streaks
    current_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    # Time
    avg_hold_days: float = 0.0
    avg_win_hold: float = 0.0
    avg_loss_hold: float = 0.0


@dataclass
class SetupPerformance:
    """Performance by setup type"""
    setup_type: str
    trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    expectancy: float = 0.0


@dataclass
class JournalSummary:
    """Complete journal summary"""
    # Overall stats
    stats: PerformanceStats = field(default_factory=PerformanceStats)
    
    # By setup
    by_setup: Dict[str, SetupPerformance] = field(default_factory=dict)
    
    # By direction
    calls_stats: PerformanceStats = field(default_factory=PerformanceStats)
    puts_stats: PerformanceStats = field(default_factory=PerformanceStats)
    
    # Time periods
    last_30_days: PerformanceStats = field(default_factory=PerformanceStats)
    last_7_days: PerformanceStats = field(default_factory=PerformanceStats)
    
    # Insights
    best_setup: str = ""
    worst_setup: str = ""
    edge_summary: str = ""
    improvement_areas: List[str] = field(default_factory=list)
    
    # Recent trades
    recent_trades: List[TradeRecord] = field(default_factory=list)


class TradeJournal:
    """Trade journal with persistence"""
    
    def __init__(self, journal_file: str = "trade_journal.json"):
        self.journal_file = Path(journal_file)
        self.trades: List[TradeRecord] = []
        self.load()
    
    def load(self):
        """Load trades from file"""
        if self.journal_file.exists():
            try:
                data = json.loads(self.journal_file.read_text())
                self.trades = [TradeRecord(**t) for t in data.get('trades', [])]
            except Exception as e:
                print(f"Error loading journal: {e}")
                self.trades = []
    
    def save(self):
        """Save trades to file"""
        try:
            data = {
                'trades': [asdict(t) for t in self.trades],
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.journal_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            print(f"Error saving journal: {e}")
    
    def add_trade(self, trade: TradeRecord):
        """Add a new trade"""
        self.trades.append(trade)
        self.save()
    
    def close_trade(self, trade_id: str, exit_price: float, exit_stock: float,
                    exit_reason: str, notes: str = "", lessons: str = ""):
        """Close an existing trade"""
        for trade in self.trades:
            if trade.id == trade_id and not trade.is_closed:
                trade.exit_date = datetime.now().strftime("%Y-%m-%d")
                trade.exit_option_price = exit_price
                trade.exit_stock_price = exit_stock
                trade.exit_reason = exit_reason
                trade.notes = notes
                trade.lessons = lessons
                
                # Calculate P&L
                trade.gross_pnl = (exit_price - trade.entry_option_price) * trade.quantity * 100
                trade.net_pnl = trade.gross_pnl - trade.fees
                trade.pnl_percent = ((exit_price - trade.entry_option_price) / trade.entry_option_price * 100) if trade.entry_option_price > 0 else 0
                
                # Determine result
                if trade.pnl_percent > 2:
                    trade.result = TradeResult.WIN.value
                elif trade.pnl_percent < -2:
                    trade.result = TradeResult.LOSS.value
                else:
                    trade.result = TradeResult.BREAKEVEN.value
                
                self.save()
                return trade
        return None
    
    def log_from_position(self, pos, exit_reason: str = "MANUAL"):
        """Create trade record from a position object"""
        trade = TradeRecord(
            id=pos.id,
            symbol=pos.symbol,
            position_type=pos.position_type.value if hasattr(pos.position_type, 'value') else str(pos.position_type),
            strike=pos.strike,
            expiration=pos.expiration,
            quantity=pos.quantity,
            entry_date=pos.entry_date,
            entry_stock_price=pos.entry_stock_price,
            entry_option_price=pos.entry_option_price,
            entry_delta=pos.greeks.entry_delta if hasattr(pos, 'greeks') else 0.5,
            entry_iv_rank=pos.greeks.iv_rank if hasattr(pos, 'greeks') else 50,
            exit_date=datetime.now().strftime("%Y-%m-%d"),
            exit_stock_price=pos.current_stock_price,
            exit_option_price=pos.current_option_price,
            exit_reason=exit_reason,
        )
        
        # Calculate P&L
        trade.gross_pnl = (trade.exit_option_price - trade.entry_option_price) * trade.quantity * 100
        trade.net_pnl = trade.gross_pnl
        trade.pnl_percent = pos.pnl_percent
        
        if trade.pnl_percent > 2:
            trade.result = TradeResult.WIN.value
        elif trade.pnl_percent < -2:
            trade.result = TradeResult.LOSS.value
        else:
            trade.result = TradeResult.BREAKEVEN.value
        
        self.add_trade(trade)
        return trade
    
    def get_summary(self, days: int = None) -> JournalSummary:
        """Get performance summary"""
        summary = JournalSummary()
        
        # Filter trades
        closed_trades = [t for t in self.trades if t.is_closed]
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            closed_trades = [
                t for t in closed_trades
                if datetime.strptime(t.exit_date, "%Y-%m-%d") >= cutoff
            ]
        
        if not closed_trades:
            return summary
        
        # Calculate overall stats
        summary.stats = self._calculate_stats(closed_trades)
        
        # By setup type
        setups = {}
        for trade in closed_trades:
            setup = trade.setup_type or "OTHER"
            if setup not in setups:
                setups[setup] = []
            setups[setup].append(trade)
        
        for setup, trades in setups.items():
            stats = self._calculate_stats(trades)
            summary.by_setup[setup] = SetupPerformance(
                setup_type=setup,
                trades=stats.total_trades,
                win_rate=stats.win_rate,
                total_pnl=stats.total_pnl,
                avg_pnl=stats.total_pnl / stats.total_trades if stats.total_trades else 0,
                expectancy=stats.expectancy
            )
        
        # By direction
        calls = [t for t in closed_trades if 'CALL' in t.position_type]
        puts = [t for t in closed_trades if 'PUT' in t.position_type]
        
        if calls:
            summary.calls_stats = self._calculate_stats(calls)
        if puts:
            summary.puts_stats = self._calculate_stats(puts)
        
        # Time periods
        now = datetime.now()
        last_30 = [t for t in closed_trades if datetime.strptime(t.exit_date, "%Y-%m-%d") >= now - timedelta(days=30)]
        last_7 = [t for t in closed_trades if datetime.strptime(t.exit_date, "%Y-%m-%d") >= now - timedelta(days=7)]
        
        if last_30:
            summary.last_30_days = self._calculate_stats(last_30)
        if last_7:
            summary.last_7_days = self._calculate_stats(last_7)
        
        # Insights
        if summary.by_setup:
            best = max(summary.by_setup.values(), key=lambda x: x.expectancy)
            worst = min(summary.by_setup.values(), key=lambda x: x.expectancy)
            summary.best_setup = f"{best.setup_type}: ${best.expectancy:.0f}/trade"
            summary.worst_setup = f"{worst.setup_type}: ${worst.expectancy:.0f}/trade"
        
        # Edge summary
        if summary.stats.expectancy > 0:
            summary.edge_summary = f"✅ Positive expectancy: ${summary.stats.expectancy:.0f}/trade"
        else:
            summary.edge_summary = f"⚠️ Negative expectancy: ${summary.stats.expectancy:.0f}/trade"
        
        # Improvement areas
        if summary.stats.win_rate < 50:
            summary.improvement_areas.append("Win rate below 50% - review entry criteria")
        if summary.stats.profit_factor < 1.5:
            summary.improvement_areas.append("Profit factor low - let winners run longer")
        if abs(summary.stats.avg_loss) > summary.stats.avg_win:
            summary.improvement_areas.append("Losses larger than wins - tighten stops")
        if summary.stats.max_loss_streak >= 3:
            summary.improvement_areas.append(f"Had {summary.stats.max_loss_streak} loss streak - review size/risk")
        
        # Recent trades
        summary.recent_trades = sorted(closed_trades, key=lambda x: x.exit_date, reverse=True)[:10]
        
        return summary
    
    def _calculate_stats(self, trades: List[TradeRecord]) -> PerformanceStats:
        """Calculate stats for a list of trades"""
        stats = PerformanceStats()
        stats.total_trades = len(trades)
        
        if not trades:
            return stats
        
        wins = [t for t in trades if t.result == TradeResult.WIN.value]
        losses = [t for t in trades if t.result == TradeResult.LOSS.value]
        
        stats.wins = len(wins)
        stats.losses = len(losses)
        stats.breakeven = stats.total_trades - stats.wins - stats.losses
        
        # Win rate
        stats.win_rate = (stats.wins / stats.total_trades * 100) if stats.total_trades > 0 else 0
        
        # P&L
        stats.total_pnl = sum(t.net_pnl for t in trades)
        
        if wins:
            win_pnls = [t.net_pnl for t in wins]
            stats.avg_win = mean(win_pnls)
            stats.largest_win = max(win_pnls)
        
        if losses:
            loss_pnls = [t.net_pnl for t in losses]
            stats.avg_loss = mean(loss_pnls)
            stats.largest_loss = min(loss_pnls)
        
        # Profit factor
        gross_profit = sum(t.net_pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.net_pnl for t in losses)) if losses else 1
        stats.profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        # Expectancy
        stats.expectancy = stats.total_pnl / stats.total_trades if stats.total_trades > 0 else 0
        
        # Hold times
        hold_days = [t.hold_days for t in trades if t.hold_days > 0]
        if hold_days:
            stats.avg_hold_days = mean(hold_days)
        
        win_holds = [t.hold_days for t in wins if t.hold_days > 0]
        loss_holds = [t.hold_days for t in losses if t.hold_days > 0]
        
        if win_holds:
            stats.avg_win_hold = mean(win_holds)
        if loss_holds:
            stats.avg_loss_hold = mean(loss_holds)
        
        # Streaks
        sorted_trades = sorted(trades, key=lambda x: x.exit_date)
        current = 0
        max_win = 0
        max_loss = 0
        
        for trade in sorted_trades:
            if trade.result == TradeResult.WIN.value:
                if current >= 0:
                    current += 1
                else:
                    current = 1
                max_win = max(max_win, current)
            elif trade.result == TradeResult.LOSS.value:
                if current <= 0:
                    current -= 1
                else:
                    current = -1
                max_loss = max(max_loss, abs(current))
        
        stats.current_streak = current
        stats.max_win_streak = max_win
        stats.max_loss_streak = max_loss
        
        return stats


def get_journal_dict(journal: TradeJournal = None, days: int = None) -> Dict:
    """Get journal summary as dictionary for web interface"""
    if journal is None:
        journal = TradeJournal()
    
    summary = journal.get_summary(days)
    
    return {
        'stats': {
            'total_trades': summary.stats.total_trades,
            'wins': summary.stats.wins,
            'losses': summary.stats.losses,
            'win_rate': summary.stats.win_rate,
            'total_pnl': summary.stats.total_pnl,
            'avg_win': summary.stats.avg_win,
            'avg_loss': summary.stats.avg_loss,
            'largest_win': summary.stats.largest_win,
            'largest_loss': summary.stats.largest_loss,
            'profit_factor': summary.stats.profit_factor,
            'expectancy': summary.stats.expectancy,
            'current_streak': summary.stats.current_streak,
            'max_win_streak': summary.stats.max_win_streak,
            'max_loss_streak': summary.stats.max_loss_streak,
            'avg_hold_days': summary.stats.avg_hold_days,
        },
        
        'by_setup': {
            setup: {
                'trades': perf.trades,
                'win_rate': perf.win_rate,
                'total_pnl': perf.total_pnl,
                'expectancy': perf.expectancy,
            }
            for setup, perf in summary.by_setup.items()
        },
        
        'calls_stats': {
            'total_trades': summary.calls_stats.total_trades,
            'win_rate': summary.calls_stats.win_rate,
            'total_pnl': summary.calls_stats.total_pnl,
            'expectancy': summary.calls_stats.expectancy,
        },
        
        'puts_stats': {
            'total_trades': summary.puts_stats.total_trades,
            'win_rate': summary.puts_stats.win_rate,
            'total_pnl': summary.puts_stats.total_pnl,
            'expectancy': summary.puts_stats.expectancy,
        },
        
        'last_30_days': {
            'total_trades': summary.last_30_days.total_trades,
            'win_rate': summary.last_30_days.win_rate,
            'total_pnl': summary.last_30_days.total_pnl,
            'expectancy': summary.last_30_days.expectancy,
        },
        
        'best_setup': summary.best_setup,
        'worst_setup': summary.worst_setup,
        'edge_summary': summary.edge_summary,
        'improvement_areas': summary.improvement_areas,
        
        'recent_trades': [
            {
                'id': t.id,
                'symbol': t.symbol,
                'position_type': t.position_type,
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'net_pnl': t.net_pnl,
                'pnl_percent': t.pnl_percent,
                'result': t.result,
                'exit_reason': t.exit_reason,
                'hold_days': t.hold_days,
            }
            for t in summary.recent_trades
        ],
    }
