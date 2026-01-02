"""
Trading Cockpit v2 - Deployment Ready
======================================
Mobile + Web responsive dashboard with AI Advisor
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from dotenv import load_dotenv

from market_regime import get_market_snapshot_dict
from portfolio_risk import get_portfolio_risk_dict
from trade_journal import TradeJournal, get_journal_dict
from scanner import SmartScanner, get_scanner_data, get_hot_list_data, get_stock_analysis_data
from ai_advisor import AITradingAdvisor, get_advisor_briefing_dict

try:
    from pro_manager import ProfessionalTradeManager, PolygonAPI, Position, PositionType
    from smart_analyzer import get_recommendation_dict
    HAS_MANAGER = True
except:
    HAS_MANAGER = False

load_dotenv()
app = Flask(__name__)

# ========== CACHING FOR SPEED ==========
_cache = {}
_cache_expiry = {}

def cache_get(key):
    """Get cached value if not expired"""
    if key in _cache and time.time() < _cache_expiry.get(key, 0):
        return _cache[key]
    return None

def cache_set(key, value, ttl=60):
    """Cache value with TTL in seconds"""
    _cache[key] = value
    _cache_expiry[key] = time.time() + ttl

# ========================================

# ========== DATABASE-BACKED STORAGE ==========
from db import db_load, db_save

# Load positions from database on startup
stored_positions = db_load('positions', {})
stored_watchlist = db_load('watchlist', {})
stored_journal = db_load('journal', [])

def save_positions():
    """Save positions to database"""
    db_save('positions', stored_positions)

def save_watchlist():
    """Save watchlist to database"""
    db_save('watchlist', stored_watchlist)

def save_journal():
    """Save journal to database"""
    db_save('journal', stored_journal)

# =============================================

api_key = os.getenv('POLYGON_API_KEY', '')
anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
api = None
manager = None

if api_key and HAS_MANAGER:
    try:
        api = PolygonAPI(api_key)
        manager = ProfessionalTradeManager(api)
    except Exception as e:
        print(f"Manager init error: {e}")

journal = TradeJournal()
scanner = SmartScanner(api, anthropic_key)

# Load watchlist from database into scanner
if stored_watchlist:
    scanner.watchlist = stored_watchlist

claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
advisor = AITradingAdvisor(anthropic_key, claude_model)

CAPITAL = float(os.getenv('TOTAL_CAPITAL', 100000))

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#0a0a12">
    <title>Trading Cockpit</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        *{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
        html{font-size:16px}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a12;color:#e0e0e0;min-height:100vh;min-height:-webkit-fill-available;padding-bottom:70px}
        
        /* Mobile-first navigation */
        .nav{background:linear-gradient(135deg,#12121f,#1a1a2e);padding:12px 15px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.1);position:sticky;top:0;z-index:100}
        .nav-brand{font-size:1.1em;font-weight:700;background:linear-gradient(90deg,#00d4ff,#7b2cbf);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .nav-refresh{background:rgba(0,212,255,0.2);border:none;padding:8px 12px;border-radius:6px;color:#00d4ff;font-size:0.85em}
        
        /* Bottom tab bar for mobile */
        .tab-bar{display:none;position:fixed;bottom:0;left:0;right:0;background:#12121f;border-top:1px solid rgba(255,255,255,0.1);padding:8px 0;padding-bottom:max(8px,env(safe-area-inset-bottom));z-index:100}
        .tab-bar-inner{display:flex;justify-content:space-around;max-width:500px;margin:0 auto}
        .tab-item{display:flex;flex-direction:column;align-items:center;text-decoration:none;color:#666;font-size:0.7em;padding:4px 8px}
        .tab-item.active{color:#00d4ff}
        .tab-icon{font-size:1.4em;margin-bottom:2px}
        
        /* Desktop tabs */
        .nav-tabs{display:flex;gap:5px}
        .nav-tab{padding:8px 14px;background:rgba(255,255,255,0.05);border:none;border-radius:6px;color:#888;cursor:pointer;font-size:0.8em;text-decoration:none;white-space:nowrap}
        .nav-tab:hover{background:rgba(255,255,255,0.1);color:#fff}
        .nav-tab.active{background:rgba(0,212,255,0.2);color:#00d4ff}
        
        /* Core components */
        .btn{padding:10px 18px;border:none;border-radius:8px;cursor:pointer;font-size:0.9em;font-weight:600;text-decoration:none;display:inline-block;touch-action:manipulation}
        .btn-primary{background:linear-gradient(135deg,#00d4ff,#0099cc);color:white}
        .btn-secondary{background:rgba(255,255,255,0.1);color:white}
        .btn-sm{padding:8px 14px;font-size:0.85em}
        .btn-danger{background:#ff5252;color:white}
        .container{max-width:1400px;margin:0 auto;padding:12px}
        .grid{display:grid;grid-template-columns:1fr;gap:12px}
        .card{background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(255,255,255,0.08);overflow:hidden}
        .card-header{padding:14px 16px;border-bottom:1px solid rgba(255,255,255,0.08);font-weight:600;font-size:0.95em;display:flex;justify-content:space-between;align-items:center}
        .card-body{padding:16px}
        
        /* Banner */
        .banner{background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(123,44,191,0.1));border:2px solid rgba(0,212,255,0.3);border-radius:12px;padding:16px;margin-bottom:12px}
        .banner-headline{font-size:1.2em;font-weight:700;margin-bottom:4px;line-height:1.3}
        .banner-sub{color:#aaa;font-size:0.85em}
        
        /* Stats grid */
        .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}
        .stat{background:rgba(0,0,0,0.3);padding:10px 8px;border-radius:8px;text-align:center}
        .stat-label{font-size:0.6em;color:#888;text-transform:uppercase;letter-spacing:0.5px}
        .stat-value{font-size:1.2em;font-weight:700;margin-top:2px}
        
        /* Rows */
        .row{display:flex;justify-content:space-between;padding:8px 0;font-size:0.9em;border-bottom:1px solid rgba(255,255,255,0.05)}
        .row:last-child{border-bottom:none}
        .label{color:#888}
        
        /* Colors */
        .green{color:#00c853}.red{color:#ff5252}.yellow{color:#ffc107}.orange{color:#ff9800}.blue{color:#00d4ff}.purple{color:#7b2cbf}
        
        /* Boxes */
        .rec-box{background:rgba(0,0,0,0.3);border-radius:8px;padding:12px;margin-top:10px}
        .rec-title{font-size:0.75em;color:#00d4ff;margin-bottom:8px;text-transform:uppercase}
        .rec-item{padding:4px 0;font-size:0.9em;padding-left:18px;position:relative}
        .rec-item:before{content:"→";position:absolute;left:0;color:#00c853}
        
        /* Gauge */
        .gauge{background:rgba(255,255,255,0.1);border-radius:4px;height:8px;margin-top:5px;overflow:hidden}
        .gauge-fill{height:100%;border-radius:4px}
        .g-green{background:linear-gradient(90deg,#00c853,#69f0ae)}
        .g-yellow{background:linear-gradient(90deg,#ffc107,#ffca28)}
        .g-red{background:linear-gradient(90deg,#f44336,#e57373)}
        
        /* Warning */
        .warn{background:rgba(255,152,0,0.1);border-left:3px solid #ff9800;padding:12px;border-radius:0 8px 8px 0;margin-top:10px;font-size:0.9em}
        
        /* Hot List */
        .hot-item{background:rgba(255,255,255,0.02);border-radius:10px;padding:14px;margin-bottom:10px;border-left:4px solid transparent}
        .hot-item.a-plus{border-left-color:#00c853}
        .hot-item.a{border-left-color:#69f0ae}
        .hot-item.b{border-left-color:#ffc107}
        .hot-item.c{border-left-color:#888}
        .hot-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px}
        .hot-rank{font-size:1.4em;font-weight:700;color:#00d4ff;margin-right:8px}
        .hot-symbol{font-size:1.1em;font-weight:700}
        .hot-score{background:rgba(0,212,255,0.2);padding:4px 10px;border-radius:4px;font-weight:600;font-size:0.85em}
        .hot-details{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}
        .hot-detail{font-size:0.85em}
        .hot-action{background:rgba(0,200,83,0.15);padding:12px;border-radius:8px;margin-top:10px}
        .hot-action-title{font-weight:600;color:#00c853;margin-bottom:5px;font-size:0.9em}
        
        /* Watchlist */
        .wl-item{display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(255,255,255,0.02);border-radius:8px;margin-bottom:8px}
        .wl-symbol{font-weight:700}
        .wl-actions{display:flex;gap:8px}
        
        /* Modal */
        .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);z-index:1000;justify-content:center;align-items:flex-end;padding:0}
        .modal.active{display:flex}
        .modal-content{background:#1a1a2e;border-radius:20px 20px 0 0;padding:20px;width:100%;max-height:90vh;overflow-y:auto;animation:slideUp 0.3s ease}
        @keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
        .modal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding-bottom:15px;border-bottom:1px solid rgba(255,255,255,0.1)}
        .modal-close{background:none;border:none;color:#888;font-size:1.8em;cursor:pointer;padding:5px}
        .form-group{margin-bottom:12px}
        .form-group label{display:block;margin-bottom:5px;color:#888;font-size:0.85em}
        .form-group input,.form-group select,.form-group textarea{width:100%;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;background:#1a1a2e;color:white;font-size:1em;-webkit-appearance:none;appearance:none}
        .form-group select{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23888' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:36px}
        .form-group select option{background:#1a1a2e;color:white}
        .form-group input::placeholder{color:#666}
        .form-group input:focus,.form-group select:focus{outline:none;border-color:#00d4ff}
        
        /* AI Advisor specific */
        .ai-section{background:rgba(0,0,0,0.2);border-radius:10px;padding:14px;margin-bottom:12px}
        .ai-section-title{font-weight:600;margin-bottom:10px;font-size:0.9em;color:#00d4ff}
        .action-item{padding:8px 0;padding-left:20px;position:relative;font-size:0.9em}
        .action-item:before{content:"→";position:absolute;left:0;color:#00c853}
        .warning-item{padding:6px 0;color:#ff5252;font-size:0.9em}
        
        /* Desktop styles */
        @media(min-width:768px){
            .tab-bar{display:none!important}
            .nav-tabs{display:flex!important}
            .grid{grid-template-columns:repeat(2,1fr)}
            .container{padding:20px}
            .stats{grid-template-columns:repeat(6,1fr)}
            .hot-details{grid-template-columns:repeat(3,1fr)}
            .modal-content{max-width:500px;border-radius:16px;margin:auto}
            .banner-headline{font-size:1.5em}
            body{padding-bottom:0}
        }
        
        @media(min-width:1200px){
            .grid{grid-template-columns:repeat(3,1fr)}
            .hot-details{grid-template-columns:repeat(6,1fr)}
        }
        
        /* Mobile styles */
        @media(max-width:767px){
            .nav-tabs{display:none!important}
            .tab-bar{display:block!important}
            .grid{grid-template-columns:1fr}
            .card-span-2{grid-column:span 1}
        }
        
        /* Pull to refresh indicator */
        .ptr-indicator{text-align:center;padding:10px;color:#00d4ff;display:none}
        .ptr-indicator.active{display:block}
    </style>
</head>
<body>
    <!-- Top Nav -->
    <div class="nav">
        <div class="nav-brand">📊 Trading Cockpit</div>
        <div class="nav-tabs">
            <a href="/" class="nav-tab {{ 'active' if tab == 'dashboard' else '' }}">Dashboard</a>
            <a href="/advisor" class="nav-tab {{ 'active' if tab == 'advisor' else '' }}">🤖 AI Advisor</a>
            <a href="/scanner" class="nav-tab {{ 'active' if tab == 'scanner' else '' }}">🔥 Scanner</a>
            <a href="/positions" class="nav-tab {{ 'active' if tab == 'positions' else '' }}">Positions</a>
            <a href="/market" class="nav-tab {{ 'active' if tab == 'market' else '' }}">Market</a>
            <a href="/risk" class="nav-tab {{ 'active' if tab == 'risk' else '' }}">Risk</a>
            <a href="/journal" class="nav-tab {{ 'active' if tab == 'journal' else '' }}">Journal</a>
        </div>
        <a href="/refresh" class="nav-refresh">🔄</a>
    </div>
    
    <!-- Bottom Tab Bar (Mobile) -->
    <div class="tab-bar">
        <div class="tab-bar-inner">
            <a href="/" class="tab-item {{ 'active' if tab == 'dashboard' else '' }}"><span class="tab-icon">📊</span>Home</a>
            <a href="/advisor" class="tab-item {{ 'active' if tab == 'advisor' else '' }}"><span class="tab-icon">🤖</span>AI</a>
            <a href="/scanner" class="tab-item {{ 'active' if tab == 'scanner' else '' }}"><span class="tab-icon">🔥</span>Scan</a>
            <a href="/positions" class="tab-item {{ 'active' if tab == 'positions' else '' }}"><span class="tab-icon">📈</span>Trades</a>
            <a href="/market" class="tab-item {{ 'active' if tab == 'market' else '' }}"><span class="tab-icon">🌍</span>Market</a>
        </div>
    </div>
    
    <div class="container">
        {% if tab == 'dashboard' %}
        <!-- DASHBOARD -->
        <div class="banner">
            <div class="banner-headline">{{ market.headline }}</div>
            <div class="banner-sub">{{ market.summary }}</div>
            <div class="stats">
                <div class="stat"><div class="stat-label">VIX</div><div class="stat-value {{ 'green' if market.vix.level < 15 else 'yellow' if market.vix.level < 20 else 'orange' if market.vix.level < 25 else 'red' }}">{{ '%.1f'|format(market.vix.level) }}</div></div>
                <div class="stat"><div class="stat-label">SPY</div><div class="stat-value {{ 'green' if market.spy.change_pct > 0 else 'red' }}">{{ '%+.1f'|format(market.spy.change_pct) }}%</div></div>
                <div class="stat"><div class="stat-label">Positions</div><div class="stat-value">{{ portfolio.risk.position_count }}</div></div>
                <div class="stat"><div class="stat-label">P&L</div><div class="stat-value {{ 'green' if total_pnl >= 0 else 'red' }}">${{ '%+.0f'|format(total_pnl) }}</div></div>
                <div class="stat"><div class="stat-label">Hot</div><div class="stat-value orange">{{ hot_count }}</div></div>
                <div class="stat"><div class="stat-label">Win%</div><div class="stat-value">{{ '%.0f'|format(journal_data.stats.win_rate) }}%</div></div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Hot List Preview -->
            <div class="card">
                <div class="card-header">🔥 Hot List <a href="/scanner" class="btn btn-sm btn-secondary">View All</a></div>
                <div class="card-body">
                    {% if hot_list %}
                    {% for h in hot_list[:3] %}
                    <div class="hot-item {{ 'a-plus' if h.setup_quality == 'A+' else 'a' if h.setup_quality == 'A' else 'b' if h.setup_quality == 'B' else 'c' }}">
                        <div class="hot-header">
                            <div><span class="hot-rank">#{{ h.rank }}</span><span class="hot-symbol">{{ h.symbol }}</span></div>
                            <span class="hot-score">{{ h.setup_quality }}</span>
                        </div>
                        <div style="font-size:0.85em;color:#aaa;">{{ h.headline }}</div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p style="color:#888;text-align:center;padding:20px;">Add stocks to watchlist</p>
                    {% endif %}
                </div>
            </div>
            
            <!-- Strategy -->
            <div class="card">
                <div class="card-header">📋 Strategy</div>
                <div class="card-body">
                    <div class="row"><span class="label">Bias</span><span class="{{ 'green' if market.strategy.bias == 'BULLISH' else 'red' if market.strategy.bias == 'BEARISH' else 'yellow' }}">{{ market.strategy.bias }}</span></div>
                    <div class="row"><span class="label">Direction</span><span>{{ market.strategy.preferred_direction }}</span></div>
                    <div class="row"><span class="label">Size</span><span>{{ '%.0f'|format(market.strategy.size_multiplier * 100) }}%</span></div>
                    <div class="rec-box">
                        <div class="rec-title">✓ Do</div>
                        {% for rec in market.strategy.recommendations[:2] %}
                        <div class="rec-item">{{ rec }}</div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            
            <!-- Positions -->
            <div class="card">
                <div class="card-header">📈 Positions</div>
                <div class="card-body">
                    {% if positions %}
                    {% for pid, p in positions.items() %}
                    <div style="background:rgba(255,255,255,0.02);border-radius:8px;padding:12px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;">
                            <span style="font-weight:700;">{{ p.symbol }} {{ p.strike }}{{ 'C' if 'CALL' in p.type else 'P' }}</span>
                            <span class="{{ 'green' if p.pnl_percent >= 0 else 'red' }}">{{ '%+.0f'|format(p.pnl_percent) }}%</span>
                        </div>
                        <div style="font-size:0.8em;color:#888;margin-top:4px;">{{ p.dte }} DTE</div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p style="color:#888;text-align:center;padding:20px;">No positions</p>
                    {% endif %}
                </div>
            </div>
            
            <!-- Risk -->
            <div class="card">
                <div class="card-header">⚠️ Risk</div>
                <div class="card-body">
                    <div class="row"><span class="label">Delta</span><span class="{{ 'green' if portfolio.greeks.total_delta > 0 else 'red' }}">{{ '%.0f'|format(portfolio.greeks.total_delta) }}</span></div>
                    <div class="row"><span class="label">Theta</span><span class="red">${{ '%.0f'|format(portfolio.greeks.total_theta) }}/day</span></div>
                    <div class="row"><span class="label">At Risk</span><span>{{ '%.1f'|format(portfolio.risk.capital_at_risk_pct) }}%</span></div>
                    <div class="gauge"><div class="gauge-fill {{ 'g-green' if portfolio.risk.capital_at_risk_pct < 5 else 'g-yellow' if portfolio.risk.capital_at_risk_pct < 10 else 'g-red' }}" style="width:{{ [portfolio.risk.capital_at_risk_pct * 4, 100]|min }}%"></div></div>
                </div>
            </div>
        </div>
        
        {% elif tab == 'advisor' %}
        <!-- AI ADVISOR -->
        <div class="banner" style="border-color:rgba(123,44,191,0.4);">
            <div class="banner-headline">🤖 AI Trading Advisor</div>
            <div class="banner-sub">Opus 4.5 analyzing your trading</div>
        </div>
        
        {% if ai_briefing.has_content %}
        <div class="card" style="margin-bottom:12px;border-left:4px solid #7b2cbf;">
            <div class="card-body">
                <h3 style="margin-bottom:12px;">{{ ai_briefing.headline }}</h3>
                <p style="color:#aaa;margin-bottom:16px;">{{ ai_briefing.market_summary }}</p>
                
                {% if ai_briefing.action_items %}
                <div class="ai-section" style="background:rgba(0,200,83,0.1);">
                    <div class="ai-section-title" style="color:#00c853;">⚡ ACTION ITEMS</div>
                    {% for item in ai_briefing.action_items %}
                    <div class="action-item">{{ item }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if ai_briefing.warnings %}
                <div class="ai-section" style="background:rgba(255,82,82,0.1);">
                    <div class="ai-section-title" style="color:#ff5252;">⚠️ WARNINGS</div>
                    {% for warn in ai_briefing.warnings %}
                    <div class="warning-item">• {{ warn }}</div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">🌍 Market</div>
                <div class="card-body"><p style="font-size:0.9em;">{{ ai_briefing.market_outlook }}</p></div>
            </div>
            <div class="card">
                <div class="card-header">📈 Positions</div>
                <div class="card-body"><p style="font-size:0.9em;white-space:pre-line;">{{ ai_briefing.position_review }}</p></div>
            </div>
            <div class="card">
                <div class="card-header" style="color:#00c853;">✅ Do Today</div>
                <div class="card-body"><p style="font-size:0.9em;white-space:pre-line;">{{ ai_briefing.what_to_do_today }}</p></div>
            </div>
            <div class="card">
                <div class="card-header" style="color:#ff5252;">🚫 Avoid</div>
                <div class="card-body"><p style="font-size:0.9em;white-space:pre-line;">{{ ai_briefing.what_to_avoid }}</p></div>
            </div>
            <div class="card">
                <div class="card-header">🔥 Opportunities</div>
                <div class="card-body"><p style="font-size:0.9em;white-space:pre-line;">{{ ai_briefing.opportunities }}</p></div>
            </div>
            <div class="card">
                <div class="card-header">💡 Insight</div>
                <div class="card-body"><p style="font-size:0.9em;">{{ ai_briefing.performance_insight }}</p></div>
            </div>
        </div>
        
        <div style="margin-top:12px;text-align:center;">
            <a href="/advisor?refresh=1" class="btn btn-primary">🔄 Refresh</a>
            <div style="color:#666;font-size:0.75em;margin-top:8px;">{{ ai_briefing.generated_at }}</div>
        </div>
        
        {% else %}
        <div class="card">
            <div class="card-body" style="text-align:center;padding:40px;">
                <div style="font-size:3em;margin-bottom:15px;">🤖</div>
                <h3>AI Not Connected</h3>
                <p style="color:#888;margin-top:10px;">Add ANTHROPIC_API_KEY to .env</p>
            </div>
        </div>
        {% endif %}
        
        {% elif tab == 'scanner' %}
        <!-- SCANNER -->
        <div class="banner">
            <div class="banner-headline">🔥 Hot List</div>
            <div class="banner-sub">AI-powered stock screening</div>
        </div>
        
        <div style="margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap;">
            <button class="btn btn-primary" onclick="openModal('add-watchlist')">➕ Add Stock</button>
            <a href="/scan" class="btn btn-secondary">🔄 Scan</a>
        </div>
        
        {% if hot_list %}
        {% for h in hot_list %}
        <div class="hot-item {{ 'a-plus' if h.setup_quality == 'A+' else 'a' if h.setup_quality == 'A' else 'b' if h.setup_quality == 'B' else 'c' }}">
            <div class="hot-header">
                <div>
                    <span class="hot-rank">#{{ h.rank }}</span>
                    <span class="hot-symbol">{{ h.symbol }}</span>
                    <span class="{{ 'green' if h.change_pct > 0 else 'red' }}" style="margin-left:8px;font-size:0.85em;">{{ '%+.1f'|format(h.change_pct) }}%</span>
                </div>
                <span class="hot-score">{{ h.setup_quality }} ({{ '%.0f'|format(h.hot_score) }})</span>
            </div>
            <div style="font-size:0.9em;color:#aaa;margin:8px 0;">{{ h.headline }}</div>
            {% if h.options_rec %}
            <div class="hot-action">
                <div class="hot-action-title">📋 Trade</div>
                <span class="{{ 'green' if h.options_rec.direction == 'CALL' else 'red' }}">{{ h.options_rec.direction }}</span>
                ${{ h.options_rec.strike }} exp {{ h.options_rec.expiration }}
            </div>
            {% endif %}
            <div style="margin-top:10px;">
                <a href="/analyze/{{ h.symbol }}" class="btn btn-sm btn-secondary">Details</a>
            </div>
        </div>
        {% endfor %}
        {% else %}
        <div class="card"><div class="card-body" style="text-align:center;padding:40px;color:#888;">Add stocks and scan</div></div>
        {% endif %}
        
        <div class="card" style="margin-top:15px;">
            <div class="card-header">📋 Watchlist ({{ watchlist|length }})</div>
            <div class="card-body">
                {% for w in watchlist %}
                <div class="wl-item">
                    <span class="wl-symbol">{{ w.symbol }}</span>
                    <a href="/remove-watchlist/{{ w.symbol }}" class="btn btn-sm btn-danger">✗</a>
                </div>
                {% endfor %}
            </div>
        </div>
        
        {% elif tab == 'positions' %}
        <!-- POSITIONS -->
        <div style="margin-bottom:12px;"><a href="/add" class="btn btn-primary">➕ Add Position</a></div>
        {% if positions %}
        {% for pid, p in positions.items() %}
        <div class="card" style="margin-bottom:12px;">
            <div class="card-header">
                <span>{{ p.symbol }} {{ p.strike }}{{ 'C' if 'CALL' in p.type else 'P' }}</span>
                <span class="{{ 'green' if p.pnl_percent >= 0 else 'red' }}" style="font-size:1.2em;">{{ '%+.1f'|format(p.pnl_percent) }}%</span>
            </div>
            <div class="card-body">
                {% if p.rec %}<div class="banner" style="margin-bottom:12px;padding:12px;"><strong>{{ p.rec.headline }}</strong></div>{% endif %}
                <div class="row"><span class="label">Entry</span><span>${{ '%.2f'|format(p.entry_option) }}</span></div>
                <div class="row"><span class="label">Current</span><span>${{ '%.2f'|format(p.current_option) }}</span></div>
                <div class="row"><span class="label">DTE</span><span class="{{ 'red' if p.dte <= 7 else '' }}">{{ p.dte }}</span></div>
                <div class="row"><span class="label">Delta</span><span>{{ '%.2f'|format(p.delta) }}</span></div>
                <div style="margin-top:12px;display:flex;gap:10px;">
                    <a href="/close/{{ pid }}" class="btn btn-primary btn-sm">Close</a>
                    <a href="/delete/{{ pid }}" class="btn btn-sm btn-danger">Delete</a>
                </div>
            </div>
        </div>
        {% endfor %}
        {% else %}
        <div class="card"><div class="card-body" style="text-align:center;padding:40px;color:#888;">No positions</div></div>
        {% endif %}
        
        {% elif tab == 'market' %}
        <!-- MARKET -->
        <div class="banner"><div class="banner-headline">{{ market.headline }}</div></div>
        <div class="grid">
            <div class="card">
                <div class="card-header">📊 VIX</div>
                <div class="card-body">
                    <div style="font-size:2.5em;text-align:center;font-weight:700;" class="{{ 'green' if market.vix.level < 15 else 'yellow' if market.vix.level < 20 else 'red' }}">{{ '%.1f'|format(market.vix.level) }}</div>
                    <p style="text-align:center;color:#888;margin-top:8px;font-size:0.85em;">{{ market.vix.interpretation }}</p>
                </div>
            </div>
            <div class="card">
                <div class="card-header">📈 SPY</div>
                <div class="card-body">
                    <div class="row"><span class="label">Price</span><span>${{ '%.2f'|format(market.spy.price) }}</span></div>
                    <div class="row"><span class="label">Change</span><span class="{{ 'green' if market.spy.change_pct > 0 else 'red' }}">{{ '%+.2f'|format(market.spy.change_pct) }}%</span></div>
                    <div class="row"><span class="label">Trend</span><span>{{ market.spy.direction }}</span></div>
                    <div class="row"><span class="label">RSI</span><span>{{ '%.0f'|format(market.spy.rsi) }}</span></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">📋 Strategy</div>
                <div class="card-body">
                    <div class="row"><span class="label">Bias</span><span class="{{ 'green' if market.strategy.bias == 'BULLISH' else 'red' if market.strategy.bias == 'BEARISH' else 'yellow' }}">{{ market.strategy.bias }}</span></div>
                    <div class="row"><span class="label">Trade</span><span>{{ market.strategy.preferred_direction }}</span></div>
                    <div class="row"><span class="label">Size</span><span>{{ '%.0f'|format(market.strategy.size_multiplier * 100) }}%</span></div>
                </div>
            </div>
        </div>
        
        {% elif tab == 'risk' %}
        <!-- RISK -->
        <div class="banner"><div class="banner-headline">{{ portfolio.headline }}</div></div>
        <div class="grid">
            <div class="card">
                <div class="card-header">Greeks</div>
                <div class="card-body">
                    <div class="row"><span class="label">Delta</span><span>{{ '%.0f'|format(portfolio.greeks.total_delta) }}</span></div>
                    <div class="row"><span class="label">Gamma</span><span>{{ '%.2f'|format(portfolio.greeks.total_gamma) }}</span></div>
                    <div class="row"><span class="label">Theta</span><span class="red">${{ '%.0f'|format(portfolio.greeks.total_theta) }}/day</span></div>
                    <div class="row"><span class="label">Vega</span><span>{{ '%.0f'|format(portfolio.greeks.total_vega) }}</span></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">Capital at Risk</div>
                <div class="card-body">
                    <div style="font-size:2.5em;text-align:center;font-weight:700;">{{ '%.1f'|format(portfolio.risk.capital_at_risk_pct) }}%</div>
                    <div class="gauge"><div class="gauge-fill {{ 'g-green' if portfolio.risk.capital_at_risk_pct < 5 else 'g-yellow' if portfolio.risk.capital_at_risk_pct < 10 else 'g-red' }}" style="width:{{ [portfolio.risk.capital_at_risk_pct * 4, 100]|min }}%"></div></div>
                    <p style="text-align:center;color:#888;margin-top:8px;font-size:0.85em;">Target: < 10%</p>
                </div>
            </div>
        </div>
        {% if portfolio.warnings %}
        <div class="card" style="margin-top:12px;">
            <div class="card-header" style="color:#ff9800;">⚠️ Warnings</div>
            <div class="card-body">
                {% for w in portfolio.warnings %}
                <div style="padding:8px 0;color:#ff9800;">• {{ w }}</div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% elif tab == 'journal' %}
        <!-- JOURNAL -->
        <div class="stats" style="margin-bottom:12px;">
            <div class="stat"><div class="stat-label">P&L</div><div class="stat-value {{ 'green' if journal_data.stats.total_pnl >= 0 else 'red' }}">${{ '%.0f'|format(journal_data.stats.total_pnl) }}</div></div>
            <div class="stat"><div class="stat-label">Trades</div><div class="stat-value">{{ journal_data.stats.total_trades }}</div></div>
            <div class="stat"><div class="stat-label">Win%</div><div class="stat-value">{{ '%.0f'|format(journal_data.stats.win_rate) }}%</div></div>
            <div class="stat"><div class="stat-label">PF</div><div class="stat-value">{{ '%.1f'|format(journal_data.stats.profit_factor) }}</div></div>
            <div class="stat"><div class="stat-label">Expect</div><div class="stat-value">${{ '%.0f'|format(journal_data.stats.expectancy) }}</div></div>
            <div class="stat"><div class="stat-label">Streak</div><div class="stat-value">{{ journal_data.stats.current_streak }}</div></div>
        </div>
        <div class="card">
            <div class="card-header">Recent Trades</div>
            <div class="card-body">
                {% if journal_data.recent_trades %}
                {% for t in journal_data.recent_trades %}
                <div class="row">
                    <span>{{ t.symbol }} ({{ t.exit_date }})</span>
                    <span class="{{ 'green' if t.net_pnl >= 0 else 'red' }}">${{ '%+.0f'|format(t.net_pnl) }}</span>
                </div>
                {% endfor %}
                {% else %}
                <p style="color:#888;text-align:center;">No trades yet</p>
                {% endif %}
            </div>
        </div>
        
        {% elif tab == 'analysis' %}
        <!-- ANALYSIS -->
        <div class="banner">
            <div class="banner-headline">{{ analysis.symbol }}</div>
            <div class="banner-sub">${{ '%.2f'|format(analysis.price) }} <span class="{{ 'green' if analysis.change_pct > 0 else 'red' }}">{{ '%+.1f'|format(analysis.change_pct) }}%</span></div>
        </div>
        
        <div class="card" style="margin-bottom:12px;">
            <div class="card-body" style="text-align:center;">
                <div style="font-size:3em;font-weight:700;color:{{ '#00c853' if analysis.setup_quality in ['A+','A'] else '#ffc107' if analysis.setup_quality == 'B' else '#888' }};">{{ analysis.setup_quality }}</div>
                <div style="margin-top:8px;">Score: {{ '%.0f'|format(analysis.hot_score) }}/100</div>
                <div class="gauge" style="margin-top:10px;"><div class="gauge-fill g-green" style="width:{{ analysis.hot_score }}%"></div></div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">📈 Technicals</div>
                <div class="card-body">
                    <div class="row"><span class="label">Trend</span><span>{{ analysis.technicals.trend_direction }}</span></div>
                    <div class="row"><span class="label">RSI</span><span>{{ '%.0f'|format(analysis.technicals.rsi) }}</span></div>
                    <div class="row"><span class="label">MACD</span><span>{{ analysis.technicals.macd_signal }}</span></div>
                    <div class="row"><span class="label">Volume</span><span>{{ '%.1f'|format(analysis.technicals.volume_ratio) }}x</span></div>
                </div>
            </div>
            {% if analysis.options_rec %}
            <div class="card">
                <div class="card-header">📋 Trade Rec</div>
                <div class="card-body">
                    <div style="text-align:center;margin-bottom:12px;">
                        <span class="{{ 'green' if analysis.options_rec.direction == 'CALL' else 'red' }}" style="font-size:1.3em;font-weight:700;">{{ analysis.options_rec.direction }}</span>
                        <div style="margin-top:4px;">${{ analysis.options_rec.strike }} exp {{ analysis.options_rec.expiration }}</div>
                    </div>
                    <div class="row"><span class="label">Target</span><span class="green">${{ '%.2f'|format(analysis.options_rec.stock_target) }}</span></div>
                    <div class="row"><span class="label">Stop</span><span class="red">${{ '%.2f'|format(analysis.options_rec.stock_stop) }}</span></div>
                    <div class="row"><span class="label">Confidence</span><span>{{ analysis.options_rec.confidence }}</span></div>
                </div>
            </div>
            {% endif %}
        </div>
        <div style="margin-top:12px;"><a href="/scanner" class="btn btn-secondary">← Back</a></div>
        {% endif %}
    </div>
    
    <!-- Modal -->
    <div class="modal" id="add-watchlist">
        <div class="modal-content">
            <div class="modal-header"><h3>Add to Watchlist</h3><button class="modal-close" onclick="closeModal('add-watchlist')">×</button></div>
            <form action="/add-watchlist" method="POST">
                <div class="form-group">
                    <label>Stock Symbol</label>
                    <input type="text" name="symbol" required autocapitalize="characters" autocomplete="off" placeholder="AAPL, TSLA, NVDA..." style="text-transform:uppercase">
                </div>
                <p style="color:#888;font-size:0.8em;margin-bottom:15px;">Sector and other data will be auto-detected</p>
                <button type="submit" class="btn btn-primary" style="width:100%;">Add Stock</button>
            </form>
        </div>
    </div>
    
    <script>
        function openModal(id){document.getElementById(id).classList.add('active')}
        function closeModal(id){document.getElementById(id).classList.remove('active')}
        document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target.classList.contains('modal'))closeModal(e.target.id)}));
    </script>
</body>
</html>
'''

def get_data(force_refresh=False):
    """Get all data with caching (60 second TTL)"""
    cache_key = 'page_data'
    
    # Return cached if available and not forcing refresh
    if not force_refresh:
        cached = cache_get(cache_key)
        if cached:
            return cached
    
    # Fetch fresh data
    market = get_market_snapshot_dict(api)
    positions = {}
    pos_list = []
    total_pnl = 0
    if manager:
        for pid, pos in manager.positions.items():
            try:
                summary = manager.get_summary(pos)
                summary['rec'] = get_recommendation_dict(pos) if HAS_MANAGER else None
                positions[pid] = summary
                pos_list.append(pos)
                total_pnl += summary.get('pnl_dollars', 0)
            except: pass
    portfolio = get_portfolio_risk_dict(pos_list, CAPITAL)
    journal_data = get_journal_dict(journal)
    try:
        hot_list = get_hot_list_data(scanner).get('hot_list', [])
    except:
        hot_list = []
    
    # Cache the result for 60 seconds
    result = (market, positions, portfolio, journal_data, total_pnl, hot_list)
    cache_set(cache_key, result, 60)
    return result

@app.route('/')
def dashboard():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    return render_template_string(HTML, tab='dashboard', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/advisor')
def advisor_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    ai_briefing = get_advisor_briefing_dict(advisor, market, positions, portfolio, hot_list, journal_data, list(scanner.watchlist.values()))
    return render_template_string(HTML, tab='advisor', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()), ai_briefing=ai_briefing)

@app.route('/scanner')
def scanner_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    return render_template_string(HTML, tab='scanner', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/scan')
def scan():
    try: scanner.scan_watchlist()
    except: pass
    return redirect(url_for('scanner_tab'))

@app.route('/analyze/<symbol>')
def analyze(symbol):
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    analysis = get_stock_analysis_data(scanner, symbol.upper())
    return render_template_string(HTML, tab='analysis', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()), analysis=analysis)

@app.route('/add-watchlist', methods=['POST'])
def add_watchlist():
    symbol = request.form.get('symbol', '').upper().strip()
    if symbol:
        # Auto-detect sector based on common stocks
        sector_map = {
            # Technology
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
            'META': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology',
            'CRM': 'Technology', 'ADBE': 'Technology', 'ORCL': 'Technology', 'CSCO': 'Technology',
            'AVGO': 'Technology', 'TXN': 'Technology', 'QCOM': 'Technology', 'MU': 'Technology',
            'NFLX': 'Technology', 'TSLA': 'Technology', 'UBER': 'Technology', 'LYFT': 'Technology',
            # Healthcare
            'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
            'MRK': 'Healthcare', 'LLY': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare',
            'BMY': 'Healthcare', 'AMGN': 'Healthcare', 'GILD': 'Healthcare', 'MRNA': 'Healthcare',
            # Financials
            'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
            'MS': 'Financials', 'C': 'Financials', 'BLK': 'Financials', 'SCHW': 'Financials',
            'AXP': 'Financials', 'V': 'Financials', 'MA': 'Financials', 'PYPL': 'Financials',
            # Consumer
            'AMZN': 'Consumer', 'WMT': 'Consumer', 'HD': 'Consumer', 'NKE': 'Consumer',
            'MCD': 'Consumer', 'SBUX': 'Consumer', 'TGT': 'Consumer', 'COST': 'Consumer',
            'DIS': 'Consumer', 'CMCSA': 'Consumer', 'PEP': 'Consumer', 'KO': 'Consumer',
            # Energy
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
            'EOG': 'Energy', 'OXY': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy',
            # Industrial
            'CAT': 'Industrial', 'BA': 'Industrial', 'HON': 'Industrial', 'UPS': 'Industrial',
            'DE': 'Industrial', 'GE': 'Industrial', 'MMM': 'Industrial', 'LMT': 'Industrial',
            # ETFs
            'SPY': 'ETF', 'QQQ': 'ETF', 'IWM': 'ETF', 'DIA': 'ETF', 'VTI': 'ETF',
            'XLF': 'ETF', 'XLE': 'ETF', 'XLK': 'ETF', 'ARKK': 'ETF', 'GLD': 'ETF',
        }
        sector = sector_map.get(symbol, 'Other')
        
        scanner.add_to_watchlist(symbol, '', sector, '')
        # Save to database
        stored_watchlist[symbol] = {'symbol': symbol, 'sector': sector}
        save_watchlist()
    return redirect(url_for('scanner_tab'))

@app.route('/remove-watchlist/<symbol>')
def remove_watchlist(symbol):
    scanner.remove_from_watchlist(symbol)
    # Remove from database
    if symbol in stored_watchlist:
        del stored_watchlist[symbol]
        save_watchlist()
    return redirect(url_for('scanner_tab'))

@app.route('/positions')
def positions_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    # Merge database positions with manager positions
    all_positions = {**stored_positions, **positions}
    return render_template_string(HTML, tab='positions', market=market, positions=all_positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/add', methods=['GET', 'POST'])
def add_position():
    if request.method == 'POST':
        try:
            symbol = request.form.get('symbol', '').upper()
            pos_type = request.form.get('type', 'LONG_CALL')
            strike = float(request.form.get('strike', 0))
            expiration = request.form.get('expiration', '')
            contracts = int(request.form.get('contracts', 1))
            entry_price = float(request.form.get('entry_price', 0))
            
            if symbol and strike and entry_price:
                # Create unique position ID
                import uuid
                pos_id = f"{symbol}_{strike}_{uuid.uuid4().hex[:6]}"
                
                # Save to database
                stored_positions[pos_id] = {
                    'symbol': symbol,
                    'type': pos_type,
                    'strike': strike,
                    'expiration': expiration,
                    'contracts': contracts,
                    'entry_option': entry_price,
                    'current_option': entry_price,
                    'entry_price': entry_price,  # for display
                    'pnl_percent': 0,
                    'pnl_dollars': 0,
                    'dte': 30,  # placeholder
                    'delta': 0.50,  # placeholder
                    'created': datetime.now().isoformat()
                }
                save_positions()
                
                # Also add to manager if available
                if manager:
                    try:
                        from pro_manager import Position, PositionType
                        ptype = PositionType.LONG_CALL if 'CALL' in pos_type else PositionType.LONG_PUT
                        pos = Position(
                            symbol=symbol,
                            position_type=ptype,
                            strike=strike,
                            expiration=expiration,
                            contracts=contracts,
                            entry_option_price=entry_price
                        )
                        manager.add_position(pos)
                    except:
                        pass
                
            return redirect(url_for('positions_tab'))
        except Exception as e:
            print(f"Add position error: {e}")
            return redirect(url_for('positions_tab'))
    
    # GET - show form
    add_form = '''
    <!DOCTYPE html><html><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Add Position</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,sans-serif;background:#0a0a12;color:#e0e0e0;min-height:100vh;padding:20px}
        .container{max-width:500px;margin:0 auto}
        h1{margin-bottom:20px;color:#00d4ff}
        .form-group{margin-bottom:15px}
        label{display:block;margin-bottom:5px;color:#888}
        input,select{width:100%;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;background:rgba(255,255,255,0.05);color:white;font-size:1em}
        .btn{padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-weight:600;margin-right:10px}
        .btn-primary{background:linear-gradient(135deg,#00d4ff,#0099cc);color:white}
        .btn-secondary{background:rgba(255,255,255,0.1);color:white;text-decoration:none;display:inline-block}
    </style>
    </head><body>
    <div class="container">
        <h1>➕ Add Position</h1>
        <form method="POST">
            <div class="form-group"><label>Symbol</label><input type="text" name="symbol" required placeholder="AAPL" style="text-transform:uppercase"></div>
            <div class="form-group"><label>Type</label><select name="type"><option value="LONG_CALL">Long Call</option><option value="LONG_PUT">Long Put</option></select></div>
            <div class="form-group"><label>Strike Price</label><input type="number" name="strike" step="0.5" required placeholder="150"></div>
            <div class="form-group"><label>Expiration</label><input type="date" name="expiration" required></div>
            <div class="form-group"><label>Contracts</label><input type="number" name="contracts" value="1" min="1"></div>
            <div class="form-group"><label>Entry Price (per contract)</label><input type="number" name="entry_price" step="0.01" required placeholder="3.50"></div>
            <button type="submit" class="btn btn-primary">Add Position</button>
            <a href="/positions" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    </body></html>
    '''
    return add_form

@app.route('/market')
def market_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    return render_template_string(HTML, tab='market', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/risk')
def risk_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    return render_template_string(HTML, tab='risk', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/journal')
def journal_tab():
    market, positions, portfolio, journal_data, total_pnl, hot_list = get_data()
    return render_template_string(HTML, tab='journal', market=market, positions=positions, portfolio=portfolio, journal_data=journal_data, total_pnl=total_pnl, hot_list=hot_list, hot_count=len(hot_list), watchlist=list(scanner.watchlist.values()))

@app.route('/refresh')
def refresh():
    # Clear cache to force fresh data
    global _cache, _cache_expiry
    _cache = {}
    _cache_expiry = {}
    if manager and api: manager.update_all()
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/delete/<pos_id>')
def delete(pos_id):
    # Remove from database
    if pos_id in stored_positions:
        del stored_positions[pos_id]
        save_positions()
    # Also remove from manager
    if manager: 
        try:
            manager.remove_position(pos_id)
        except:
            pass
    return redirect(url_for('positions_tab'))

@app.route('/close/<pos_id>')
def close(pos_id):
    # Log to journal and remove from database
    if pos_id in stored_positions:
        pos_data = stored_positions[pos_id]
        # Add to journal
        stored_journal.append({
            'symbol': pos_data.get('symbol', ''),
            'type': pos_data.get('type', ''),
            'entry_price': pos_data.get('entry_option', 0),
            'exit_price': pos_data.get('current_option', pos_data.get('entry_option', 0)),
            'pnl': pos_data.get('pnl_dollars', 0),
            'net_pnl': pos_data.get('pnl_dollars', 0),
            'exit_date': datetime.now().strftime('%Y-%m-%d'),
            'exit_reason': 'MANUAL'
        })
        save_journal()
        del stored_positions[pos_id]
        save_positions()
    
    # Also handle manager positions
    if manager and pos_id in manager.positions:
        pos = manager.positions[pos_id]
        journal.log_from_position(pos, "MANUAL")
        manager.remove_position(pos_id)
    return redirect(url_for('positions_tab'))

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Trading Cockpit",
        "short_name": "Cockpit",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a12",
        "theme_color": "#0a0a12",
        "icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n  🚀 Trading Cockpit running on port {port}")
    print(f"  📱 Mobile + Web ready!\n")
    app.run(host='0.0.0.0', port=port, debug=False)
