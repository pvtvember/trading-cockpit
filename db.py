"""
Database Module - PostgreSQL Persistence
=========================================
All data persists across deployments:
- Watchlist
- Positions
- Journal entries
- Scan history
- Statistics
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Try PostgreSQL, fallback to JSON for local dev
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DATABASE_URL = os.getenv('DATABASE_URL')

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_connection():
    """Get PostgreSQL connection"""
    if not DATABASE_URL or not HAS_POSTGRES:
        return None
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize all database tables"""
    conn = get_connection()
    if not conn:
        print("No database connection - using in-memory storage")
        return False
    
    try:
        cur = conn.cursor()
        
        # Watchlist table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol VARCHAR(10) PRIMARY KEY,
                sector VARCHAR(50),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Positions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id VARCHAR(50) PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                setup_type VARCHAR(50),
                tier VARCHAR(1),
                strike DECIMAL(10,2),
                expiration DATE,
                contracts INTEGER,
                entry_price DECIMAL(10,4),
                entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                entry_delta DECIMAL(5,4),
                entry_iv DECIMAL(5,2),
                entry_underlying DECIMAL(10,2),
                target_price DECIMAL(10,4),
                stop_price DECIMAL(10,4),
                status VARCHAR(20) DEFAULT 'OPEN',
                current_price DECIMAL(10,4),
                current_delta DECIMAL(5,4),
                current_underlying DECIMAL(10,2),
                pnl_dollars DECIMAL(12,2),
                pnl_percent DECIMAL(8,2),
                notes TEXT,
                scan_data JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Journal table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS journal (
                id SERIAL PRIMARY KEY,
                position_id VARCHAR(50),
                symbol VARCHAR(10) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                setup_type VARCHAR(50),
                tier VARCHAR(1),
                strike DECIMAL(10,2),
                expiration DATE,
                contracts INTEGER,
                entry_price DECIMAL(10,4),
                entry_date TIMESTAMP,
                entry_delta DECIMAL(5,4),
                entry_iv DECIMAL(5,2),
                entry_underlying DECIMAL(10,2),
                exit_price DECIMAL(10,4),
                exit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_delta DECIMAL(5,4),
                exit_underlying DECIMAL(10,2),
                exit_reason VARCHAR(50),
                pnl_dollars DECIMAL(12,2),
                pnl_percent DECIMAL(8,2),
                hold_days INTEGER,
                target_hit BOOLEAN,
                stop_hit BOOLEAN,
                ai_review TEXT,
                lessons TEXT,
                tags TEXT[],
                scan_data_entry JSONB,
                scan_data_exit JSONB
            )
        ''')
        
        # Scan history table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category VARCHAR(20),
                setup_type VARCHAR(50),
                tier VARCHAR(1),
                priority_score INTEGER,
                exec_readiness INTEGER,
                confluence_score INTEGER,
                technical_data JSONB,
                options_data JSONB,
                recommendation JSONB,
                UNIQUE(symbol, scanned_at)
            )
        ''')
        
        # Statistics cache table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                key VARCHAR(100) PRIMARY KEY,
                value JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Settings table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Populate default watchlist if empty
        _populate_default_watchlist()
        
        print("Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False


def _populate_default_watchlist():
    """Add default high-liquidity options stocks to watchlist if empty"""
    # Check if watchlist is empty
    existing = watchlist_get_all()
    if existing:
        return  # Already has symbols
    
    # High liquidity options stocks - excellent for swing trading
    DEFAULT_WATCHLIST = [
        # Mega Cap Tech - Ultra Liquid
        ('AAPL', 'Technology'),
        ('MSFT', 'Technology'),
        ('NVDA', 'Technology'),
        ('GOOGL', 'Technology'),
        ('AMZN', 'Consumer'),
        ('META', 'Technology'),
        ('TSLA', 'Consumer'),
        
        # Semiconductor - High Beta
        ('AMD', 'Technology'),
        ('INTC', 'Technology'),
        ('MU', 'Technology'),
        ('QCOM', 'Technology'),
        
        # Software/Cloud
        ('CRM', 'Technology'),
        ('NOW', 'Technology'),
        ('ADBE', 'Technology'),
        
        # Financials
        ('JPM', 'Financials'),
        ('BAC', 'Financials'),
        ('GS', 'Financials'),
        
        # Consumer/Retail
        ('NFLX', 'Communication'),
        ('DIS', 'Communication'),
        ('NKE', 'Consumer'),
        ('SBUX', 'Consumer'),
        
        # Chinese Tech - High Volatility
        ('BABA', 'Technology'),
        ('BIDU', 'Technology'),
        ('JD', 'Consumer'),
        ('PDD', 'Consumer'),
        
        # Social Media
        ('SNAP', 'Communication'),
        ('PINS', 'Communication'),
        
        # Energy - For Rotation
        ('XOM', 'Energy'),
        ('CVX', 'Energy'),
        
        # ETFs - For Market Plays
        ('SPY', 'Index'),
        ('QQQ', 'Index'),
        ('IWM', 'Index'),
    ]
    
    for symbol, sector in DEFAULT_WATCHLIST:
        watchlist_add(symbol, sector, 'Default - High liquidity options')
    
    print(f"Populated default watchlist with {len(DEFAULT_WATCHLIST)} symbols")

# ============================================================================
# WATCHLIST OPERATIONS
# ============================================================================

# In-memory fallback
_memory_watchlist = {}
_memory_positions = {}
_memory_journal = []
_memory_scans = {}

def watchlist_add(symbol: str, sector: str = '', notes: str = '') -> bool:
    """Add symbol to watchlist"""
    symbol = symbol.upper().strip()
    
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO watchlist (symbol, sector, notes)
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    sector = EXCLUDED.sector,
                    notes = EXCLUDED.notes,
                    active = TRUE
            ''', (symbol, sector, notes))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Watchlist add error: {e}")
            return False
    else:
        _memory_watchlist[symbol] = {
            'symbol': symbol,
            'sector': sector,
            'notes': notes,
            'added_at': datetime.now().isoformat()
        }
        return True

def watchlist_remove(symbol: str) -> bool:
    """Remove symbol from watchlist"""
    symbol = symbol.upper().strip()
    
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('UPDATE watchlist SET active = FALSE WHERE symbol = %s', (symbol,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Watchlist remove error: {e}")
            return False
    else:
        _memory_watchlist.pop(symbol, None)
        return True

def watchlist_get_all() -> List[Dict]:
    """Get all active watchlist symbols"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM watchlist WHERE active = TRUE ORDER BY added_at DESC')
            results = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            print(f"Watchlist get error: {e}")
            return []
    else:
        return list(_memory_watchlist.values())

# ============================================================================
# POSITIONS OPERATIONS
# ============================================================================

def position_add(position_data: Dict) -> str:
    """Add new position"""
    import uuid
    pos_id = position_data.get('id') or f"{position_data['symbol']}_{uuid.uuid4().hex[:8]}"
    
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO positions (
                    id, symbol, direction, setup_type, tier, strike, expiration,
                    contracts, entry_price, entry_delta, entry_iv, entry_underlying,
                    target_price, stop_price, scan_data, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN'
                )
            ''', (
                pos_id,
                position_data['symbol'],
                position_data.get('direction', 'CALL'),
                position_data.get('setup_type'),
                position_data.get('tier'),
                position_data.get('strike'),
                position_data.get('expiration'),
                position_data.get('contracts', 1),
                position_data.get('entry_price'),
                position_data.get('entry_delta'),
                position_data.get('entry_iv'),
                position_data.get('entry_underlying'),
                position_data.get('target_price'),
                position_data.get('stop_price'),
                Json(position_data.get('scan_data', {}))
            ))
            conn.commit()
            cur.close()
            conn.close()
            return pos_id
        except Exception as e:
            print(f"Position add error: {e}")
            return None
    else:
        _memory_positions[pos_id] = {**position_data, 'id': pos_id, 'status': 'OPEN'}
        return pos_id

def position_update(pos_id: str, updates: Dict) -> bool:
    """Update position data"""
    conn = get_connection()
    if conn:
        try:
            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = %s")
                values.append(value)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(pos_id)
            
            cur = conn.cursor()
            cur.execute(f'''
                UPDATE positions SET {', '.join(set_clauses)}
                WHERE id = %s
            ''', values)
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Position update error: {e}")
            return False
    else:
        if pos_id in _memory_positions:
            _memory_positions[pos_id].update(updates)
        return True

def position_close(pos_id: str, exit_price: float, exit_reason: str = 'MANUAL') -> bool:
    """Close position and log to journal"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get position data
            cur.execute('SELECT * FROM positions WHERE id = %s', (pos_id,))
            pos = cur.fetchone()
            
            if not pos:
                return False
            
            # Calculate P&L
            entry_price = float(pos['entry_price'] or 0)
            contracts = int(pos['contracts'] or 1)
            pnl_dollars = (exit_price - entry_price) * contracts * 100
            pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            
            # Calculate hold days
            entry_date = pos['entry_date']
            hold_days = (datetime.now() - entry_date).days if entry_date else 0
            
            # Check if target/stop hit
            target_hit = exit_price >= float(pos['target_price'] or 999999)
            stop_hit = exit_price <= float(pos['stop_price'] or 0)
            
            # Insert into journal
            cur.execute('''
                INSERT INTO journal (
                    position_id, symbol, direction, setup_type, tier, strike, expiration,
                    contracts, entry_price, entry_date, entry_delta, entry_iv, entry_underlying,
                    exit_price, exit_reason, pnl_dollars, pnl_percent, hold_days,
                    target_hit, stop_hit, scan_data_entry
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            ''', (
                pos_id, pos['symbol'], pos['direction'], pos['setup_type'], pos['tier'],
                pos['strike'], pos['expiration'], pos['contracts'], pos['entry_price'],
                pos['entry_date'], pos['entry_delta'], pos['entry_iv'], pos['entry_underlying'],
                exit_price, exit_reason, pnl_dollars, pnl_percent, hold_days,
                target_hit, stop_hit, pos['scan_data']
            ))
            
            # Update position status
            cur.execute('''
                UPDATE positions SET 
                    status = 'CLOSED',
                    current_price = %s,
                    pnl_dollars = %s,
                    pnl_percent = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (exit_price, pnl_dollars, pnl_percent, pos_id))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Position close error: {e}")
            return False
    else:
        if pos_id in _memory_positions:
            pos = _memory_positions[pos_id]
            entry_price = float(pos.get('entry_price', 0))
            contracts = int(pos.get('contracts', 1))
            pnl_dollars = (exit_price - entry_price) * contracts * 100
            pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            
            _memory_journal.append({
                **pos,
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pnl_dollars': pnl_dollars,
                'pnl_percent': pnl_percent,
                'exit_date': datetime.now().isoformat()
            })
            pos['status'] = 'CLOSED'
        return True

def position_get_all(status: str = 'OPEN') -> List[Dict]:
    """Get all positions with given status"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('''
                SELECT * FROM positions 
                WHERE status = %s 
                ORDER BY entry_date DESC
            ''', (status,))
            results = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            print(f"Position get error: {e}")
            return []
    else:
        return [p for p in _memory_positions.values() if p.get('status') == status]

def position_get(pos_id: str) -> Optional[Dict]:
    """Get single position by ID"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM positions WHERE id = %s', (pos_id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"Position get error: {e}")
            return None
    else:
        return _memory_positions.get(pos_id)

# ============================================================================
# JOURNAL OPERATIONS
# ============================================================================

def journal_get_all(limit: int = 100) -> List[Dict]:
    """Get journal entries"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('''
                SELECT * FROM journal 
                ORDER BY exit_date DESC 
                LIMIT %s
            ''', (limit,))
            results = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            print(f"Journal get error: {e}")
            return []
    else:
        return _memory_journal[-limit:]

def journal_update_review(journal_id: int, ai_review: str, lessons: str) -> bool:
    """Update journal entry with AI review"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                UPDATE journal SET ai_review = %s, lessons = %s
                WHERE id = %s
            ''', (ai_review, lessons, journal_id))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Journal update error: {e}")
            return False
    return True

def journal_get_statistics() -> Dict:
    """Calculate trading statistics from journal"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Overall stats
            cur.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl_dollars > 0 THEN 1 END) as winners,
                    COUNT(CASE WHEN pnl_dollars <= 0 THEN 1 END) as losers,
                    COALESCE(AVG(pnl_percent), 0) as avg_return,
                    COALESCE(SUM(pnl_dollars), 0) as total_pnl,
                    COALESCE(AVG(CASE WHEN pnl_dollars > 0 THEN pnl_percent END), 0) as avg_win,
                    COALESCE(AVG(CASE WHEN pnl_dollars <= 0 THEN pnl_percent END), 0) as avg_loss,
                    COALESCE(AVG(hold_days), 0) as avg_hold_days
                FROM journal
            ''')
            overall = dict(cur.fetchone())
            
            # Calculate win rate and profit factor
            total = overall['total_trades'] or 1
            overall['win_rate'] = (overall['winners'] / total) * 100
            
            # By setup type
            cur.execute('''
                SELECT 
                    setup_type,
                    tier,
                    COUNT(*) as trades,
                    COUNT(CASE WHEN pnl_dollars > 0 THEN 1 END) as winners,
                    COALESCE(AVG(pnl_percent), 0) as avg_return,
                    COALESCE(SUM(pnl_dollars), 0) as total_pnl
                FROM journal
                WHERE setup_type IS NOT NULL
                GROUP BY setup_type, tier
                ORDER BY total_pnl DESC
            ''')
            by_setup = [dict(r) for r in cur.fetchall()]
            for s in by_setup:
                s['win_rate'] = (s['winners'] / s['trades']) * 100 if s['trades'] > 0 else 0
            
            # By direction
            cur.execute('''
                SELECT 
                    direction,
                    COUNT(*) as trades,
                    COUNT(CASE WHEN pnl_dollars > 0 THEN 1 END) as winners,
                    COALESCE(AVG(pnl_percent), 0) as avg_return,
                    COALESCE(SUM(pnl_dollars), 0) as total_pnl
                FROM journal
                GROUP BY direction
            ''')
            by_direction = [dict(r) for r in cur.fetchall()]
            for d in by_direction:
                d['win_rate'] = (d['winners'] / d['trades']) * 100 if d['trades'] > 0 else 0
            
            # Recent performance (last 30 days)
            cur.execute('''
                SELECT 
                    COUNT(*) as trades,
                    COUNT(CASE WHEN pnl_dollars > 0 THEN 1 END) as winners,
                    COALESCE(AVG(pnl_percent), 0) as avg_return,
                    COALESCE(SUM(pnl_dollars), 0) as total_pnl
                FROM journal
                WHERE exit_date > NOW() - INTERVAL '30 days'
            ''')
            recent = dict(cur.fetchone())
            recent['win_rate'] = (recent['winners'] / recent['trades']) * 100 if recent['trades'] > 0 else 0
            
            cur.close()
            conn.close()
            
            return {
                'overall': overall,
                'by_setup': by_setup,
                'by_direction': by_direction,
                'recent_30d': recent
            }
            
        except Exception as e:
            print(f"Statistics error: {e}")
            return {'overall': {}, 'by_setup': [], 'by_direction': [], 'recent_30d': {}}
    else:
        # Basic in-memory stats
        trades = _memory_journal
        winners = [t for t in trades if t.get('pnl_dollars', 0) > 0]
        return {
            'overall': {
                'total_trades': len(trades),
                'winners': len(winners),
                'win_rate': (len(winners) / len(trades) * 100) if trades else 0,
                'total_pnl': sum(t.get('pnl_dollars', 0) for t in trades)
            },
            'by_setup': [],
            'by_direction': [],
            'recent_30d': {}
        }

# ============================================================================
# SCAN HISTORY OPERATIONS
# ============================================================================

def scan_save(symbol: str, scan_data: Dict) -> bool:
    """Save scan result"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO scan_history (
                    symbol, category, setup_type, tier, priority_score,
                    exec_readiness, confluence_score, technical_data,
                    options_data, recommendation
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                symbol,
                scan_data.get('category'),
                scan_data.get('setup_type'),
                scan_data.get('tier'),
                scan_data.get('priority_score'),
                scan_data.get('exec_readiness'),
                scan_data.get('confluence_score'),
                Json(scan_data.get('technical', {})),
                Json(scan_data.get('options', {})),
                Json(scan_data.get('recommendation', {}))
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Scan save error: {e}")
            return False
    else:
        _memory_scans[symbol] = scan_data
        return True

def scan_get_latest(symbol: str) -> Optional[Dict]:
    """Get most recent scan for symbol"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('''
                SELECT * FROM scan_history 
                WHERE symbol = %s 
                ORDER BY scanned_at DESC 
                LIMIT 1
            ''', (symbol,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"Scan get error: {e}")
            return None
    else:
        return _memory_scans.get(symbol)

# ============================================================================
# SETTINGS OPERATIONS
# ============================================================================

def settings_get(key: str, default: Any = None) -> Any:
    """Get setting value"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT value FROM settings WHERE key = %s', (key,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result['value'] if result else default
        except Exception as e:
            return default
    return default

def settings_set(key: str, value: Any) -> bool:
    """Set setting value"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            ''', (key, Json(value)))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Settings set error: {e}")
            return False
    return False

# Initialize database on import
init_database()
