"""
Trading Cockpit v4 - Main Application
======================================
Swing Options Execution System with AI Mentor
"""

import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()

from db import (
    init_database, watchlist_add, watchlist_remove, watchlist_get_all,
    position_add, position_update, position_close, position_get_all, position_get,
    journal_get_all, journal_get_statistics, journal_update_review,
    settings_get, settings_set
)
from scanner import (
    scan_watchlist, get_cached_results, get_results_by_category,
    quick_scan_symbol, start_scanner, get_scan_stats, is_market_hours
)
from mentor import (
    review_trade, analyze_patterns, get_entry_advice, 
    get_exit_advice, generate_daily_briefing
)
from position_manager import analyze_position, analyze_portfolio
from market_monitor import get_market_snapshot, get_position_market_context
from news_service import get_position_news_summary
from positions_template import POSITIONS_HTML

app = Flask(__name__)

CAPITAL = float(os.getenv('TOTAL_CAPITAL', 100000))

init_database()
start_scanner()

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0a0a12">
    <title>Trading Cockpit v4</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#0a0a12,#1a1a2e);color:#e0e0e0;min-height:100vh;padding-bottom:70px}
        .header{background:rgba(0,0,0,0.4);padding:12px 15px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100;backdrop-filter:blur(10px)}
        .logo{font-weight:700;font-size:1.1em}.logo span{color:#00d4ff}
        .market-status{padding:4px 10px;border-radius:12px;font-size:0.75em;font-weight:600}
        .market-open{background:rgba(0,200,83,0.2);color:#00c853}
        .market-closed{background:rgba(255,82,82,0.2);color:#ff5252}
        .nav{display:flex;gap:5px;padding:10px 15px;overflow-x:auto}
        .nav-item{padding:8px 16px;border-radius:20px;background:rgba(255,255,255,0.05);color:#888;text-decoration:none;font-size:0.85em;font-weight:500;white-space:nowrap}
        .nav-item:hover{background:rgba(255,255,255,0.1);color:#fff}
        .nav-item.active{background:linear-gradient(135deg,#00d4ff,#0099cc);color:white}
        .nav-badge{background:#ff5252;color:white;font-size:0.7em;padding:2px 6px;border-radius:10px;margin-left:5px}
        .container{padding:15px;max-width:1400px;margin:0 auto}
        .card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;margin-bottom:12px;overflow:hidden}
        .card-header{padding:12px 15px;background:rgba(0,0,0,0.2);font-weight:600;font-size:0.9em;display:flex;justify-content:space-between;align-items:center}
        .card-body{padding:15px}
        .category-header{display:flex;align-items:center;gap:10px;padding:15px;margin-bottom:10px;border-radius:10px}
        .category-ready{background:linear-gradient(135deg,rgba(0,200,83,0.15),rgba(0,200,83,0.05));border-left:4px solid #00c853}
        .category-setting{background:linear-gradient(135deg,rgba(0,188,212,0.15),rgba(0,188,212,0.05));border-left:4px solid #00bcd4}
        .category-building{background:linear-gradient(135deg,rgba(255,193,7,0.15),rgba(255,193,7,0.05));border-left:4px solid #ffc107}
        .category-avoid{background:linear-gradient(135deg,rgba(255,82,82,0.15),rgba(255,82,82,0.05));border-left:4px solid #ff5252}
        .category-icon{font-size:1.5em}.category-title{font-weight:700;font-size:1.1em}.category-count{color:#888;font-size:0.85em}
        .setup-card{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:15px;margin-bottom:12px}
        .setup-card.tier-a{border-left:4px solid #00c853}
        .setup-card.tier-b{border-left:4px solid #00bcd4}
        .setup-card.tier-c{border-left:4px solid #ff9800}
        .setup-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
        .setup-symbol{font-size:1.3em;font-weight:700;color:#00d4ff}
        .setup-price{color:#888;font-size:0.9em;margin-left:10px}
        .setup-tier{font-size:1.2em;font-weight:700;padding:4px 12px;border-radius:8px}
        .tier-a-badge{background:rgba(0,200,83,0.2);color:#00c853}
        .tier-b-badge{background:rgba(0,188,212,0.2);color:#00bcd4}
        .tier-c-badge{background:rgba(255,152,0,0.2);color:#ff9800}
        .setup-type{display:inline-block;padding:4px 10px;border-radius:4px;font-size:0.8em;font-weight:600;margin-bottom:10px}
        .setup-call{background:rgba(0,200,83,0.15);color:#00c853}
        .setup-put{background:rgba(255,82,82,0.15);color:#ff5252}
        .setup-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
        .metric{background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center}
        .metric-label{font-size:0.7em;color:#888;margin-bottom:4px}
        .metric-value{font-weight:600;font-size:0.95em}
        .setup-analysis{background:rgba(123,44,191,0.1);border-radius:8px;padding:12px;margin-bottom:12px}
        .analysis-row{display:flex;justify-content:space-between;padding:4px 0;font-size:0.85em}
        .analysis-label{color:#888}
        .contract-box{background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,212,255,0.02));border:1px solid rgba(0,212,255,0.2);border-radius:10px;padding:15px;margin-bottom:12px}
        .contract-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
        .contract-title{font-size:0.8em;color:#00d4ff;font-weight:600}
        .contract-strike{font-size:1.2em;font-weight:700}
        .contract-details{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;font-size:0.85em}
        .contract-detail{display:flex;justify-content:space-between}
        .contract-detail-label{color:#888}
        .warnings{background:rgba(255,193,7,0.1);border-radius:8px;padding:10px;font-size:0.85em}
        .warning-item{color:#ffc107;padding:4px 0}
        .btn{padding:10px 20px;border:none;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;font-size:0.9em}
        .btn-primary{background:linear-gradient(135deg,#00d4ff,#0099cc);color:white}
        .btn-success{background:linear-gradient(135deg,#00c853,#009624);color:white}
        .btn-danger{background:linear-gradient(135deg,#ff5252,#d32f2f);color:white}
        .btn-secondary{background:rgba(255,255,255,0.1);color:#e0e0e0}
        .btn-sm{padding:6px 12px;font-size:0.8em}
        .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:15px}
        .stat-card{background:rgba(255,255,255,0.03);border-radius:10px;padding:15px;text-align:center}
        .stat-value{font-size:1.5em;font-weight:700}
        .stat-label{font-size:0.75em;color:#888;margin-top:4px}
        .journal-table{width:100%;border-collapse:collapse;font-size:0.85em}
        .journal-table th{text-align:left;padding:10px;background:rgba(0,0,0,0.3);color:#888;font-weight:500}
        .journal-table td{padding:12px 10px;border-bottom:1px solid rgba(255,255,255,0.05)}
        .mentor-card{background:linear-gradient(135deg,rgba(123,44,191,0.1),rgba(123,44,191,0.02));border:1px solid rgba(123,44,191,0.2)}
        .mentor-insight{padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)}
        .mentor-insight-title{font-weight:600;color:#7b2cbf;margin-bottom:8px;font-size:0.9em}
        .form-group{margin-bottom:15px}
        .form-group label{display:block;margin-bottom:6px;color:#888;font-size:0.85em}
        .form-group input,.form-group select{width:100%;padding:12px;border:1px solid rgba(255,255,255,0.1);border-radius:8px;background:rgba(0,0,0,0.3);color:white;font-size:1em}
        .modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center;padding:20px}
        .modal.active{display:flex}
        .modal-content{background:#1a1a2e;border-radius:16px;width:100%;max-width:500px}
        .modal-header{padding:15px 20px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center}
        .modal-body{padding:20px}
        .modal-close{background:none;border:none;color:#888;font-size:1.5em;cursor:pointer}
        .green{color:#00c853}.red{color:#ff5252}.yellow{color:#ffc107}.cyan{color:#00d4ff}.purple{color:#7b2cbf}
        .empty-state{text-align:center;padding:40px 20px;color:#888}
        .empty-state-icon{font-size:3em;margin-bottom:15px}
        @media(max-width:768px){.stats-grid{grid-template-columns:repeat(2,1fr)}.setup-metrics{grid-template-columns:repeat(2,1fr)}}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Trading <span>Cockpit</span> v4</div>
        <div style="display:flex;gap:10px;align-items:center">
            <span class="market-status {{ 'market-open' if is_market_open else 'market-closed' }}">{{ 'OPEN' if is_market_open else 'CLOSED' }}</span>
            <a href="/scan" class="btn btn-sm btn-primary">🔄</a>
        </div>
    </div>
    
    <div class="nav">
        <a href="/" class="nav-item {{ 'active' if tab == 'scanner' else '' }}">🔥 Scanner{% if ready_count %}<span class="nav-badge">{{ ready_count }}</span>{% endif %}</a>
        <a href="/positions" class="nav-item {{ 'active' if tab == 'positions' else '' }}">📊 Positions{% if position_count %}<span class="nav-badge">{{ position_count }}</span>{% endif %}</a>
        <a href="/journal" class="nav-item {{ 'active' if tab == 'journal' else '' }}">📝 Journal</a>
        <a href="/mentor" class="nav-item {{ 'active' if tab == 'mentor' else '' }}">🎓 Mentor</a>
        <a href="/settings" class="nav-item {{ 'active' if tab == 'settings' else '' }}">⚙️</a>
    </div>
    
    <div class="container">
        {% if tab == 'scanner' %}
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value green">{{ scan_stats.ready_now }}</div><div class="stat-label">READY NOW</div></div>
            <div class="stat-card"><div class="stat-value cyan">{{ scan_stats.setting_up }}</div><div class="stat-label">SETTING UP</div></div>
            <div class="stat-card"><div class="stat-value yellow">{{ scan_stats.building }}</div><div class="stat-label">BUILDING</div></div>
            <div class="stat-card"><div class="stat-value">{{ scan_stats.total }}</div><div class="stat-label">WATCHLIST</div></div>
        </div>
        
        <div style="margin-bottom:15px">
            <button class="btn btn-primary" onclick="openModal('add-stock')">➕ Add Stock</button>
            <span style="color:#888;font-size:0.8em;margin-left:15px">Last: {{ scan_stats.last_scan or 'Never' }}</span>
        </div>
        
        {% if categorized.READY_NOW %}
        <div class="category-header category-ready">
            <span class="category-icon">🔥</span>
            <div><div class="category-title">READY NOW</div><div class="category-count">{{ categorized.READY_NOW|length }} ready</div></div>
        </div>
        {% for r in categorized.READY_NOW %}
        <div class="setup-card tier-{{ r.tier|lower }}">
            <div class="setup-header">
                <div>
                    <span class="setup-symbol">{{ r.symbol }}</span>
                    <span class="setup-price">${{ '%.2f'|format(r.price) }}</span>
                    <span class="{{ 'green' if r.change_pct > 0 else 'red' }}">{{ '%+.1f'|format(r.change_pct) }}%</span>
                </div>
                <span class="setup-tier tier-{{ r.tier|lower }}-badge">{{ r.tier }}-TIER</span>
            </div>
            <span class="setup-type setup-{{ r.setup_direction|lower }}">{{ r.setup_direction }} {{ r.setup_type }}</span>
            <div class="setup-metrics">
                <div class="metric"><div class="metric-label">PRIORITY</div><div class="metric-value">{{ r.priority_score }}/150</div></div>
                <div class="metric"><div class="metric-label">EXEC</div><div class="metric-value {{ 'green' if r.exec_readiness >= 10 else 'yellow' }}">{{ r.exec_readiness }}/14</div></div>
                <div class="metric"><div class="metric-label">CONFLUENCE</div><div class="metric-value">{{ r.confluence_score }}/100</div></div>
            </div>
            <div class="setup-analysis">
                <div class="analysis-row"><span class="analysis-label">RS vs SPY</span><span class="{{ 'green' if r.relative_strength > 0.5 else 'red' if r.relative_strength < -0.5 else '' }}">{{ '%+.1f'|format(r.relative_strength) }}%</span></div>
                <div class="analysis-row"><span class="analysis-label">IV</span><span class="{{ 'green' if r.iv_percentile < 30 else 'red' if r.iv_percentile > 70 else '' }}">{{ '%.0f'|format(r.iv_percentile) }}%</span></div>
                <div class="analysis-row"><span class="analysis-label">RSI</span><span>{{ '%.0f'|format(r.rsi) }}</span></div>
                <div class="analysis-row"><span class="analysis-label">Squeeze</span><span>{{ 'YES (' + r.squeeze_bars|string + ')' if r.squeeze_on else 'No' }}</span></div>
            </div>
            {% if r.options and r.options.recommended_contract %}
            <div class="contract-box">
                <div class="contract-header">
                    <span class="contract-title">CONTRACT</span>
                    <span class="contract-strike">${{ '%.0f'|format(r.options.recommended_contract.strike) }} {{ r.setup_direction }}</span>
                </div>
                <div class="contract-details">
                    <div class="contract-detail"><span class="contract-detail-label">Exp</span><span>{{ r.options.recommended_contract.expiration }} ({{ r.options.recommended_contract.dte }}d)</span></div>
                    <div class="contract-detail"><span class="contract-detail-label">Delta</span><span>{{ '%.2f'|format(r.options.recommended_contract.delta or 0.5) }}</span></div>
                    <div class="contract-detail"><span class="contract-detail-label">Premium</span><span>${{ '%.2f'|format(r.options.recommended_contract.mid or 0) }}</span></div>
                    <div class="contract-detail"><span class="contract-detail-label">Contracts</span><span>{{ r.options.num_contracts }}</span></div>
                    <div class="contract-detail"><span class="contract-detail-label">Size</span><span>${{ '{:,.0f}'.format(r.options.total_premium) }}</span></div>
                    <div class="contract-detail"><span class="contract-detail-label">Target</span><span class="green">${{ '%.2f'|format(r.options.target_price) }}</span></div>
                </div>
            </div>
            {% endif %}
            {% if r.warnings %}<div class="warnings">{% for w in r.warnings %}<div class="warning-item">⚠️ {{ w }}</div>{% endfor %}</div>{% endif %}
            <div style="display:flex;gap:10px;margin-top:12px">
                <a href="/execute/{{ r.symbol }}" class="btn btn-success">🚀 Execute</a>
                <a href="/analyze/{{ r.symbol }}" class="btn btn-secondary">📊 Details</a>
            </div>
        </div>
        {% endfor %}
        {% endif %}
        
        {% if categorized.SETTING_UP %}
        <div class="category-header category-setting">
            <span class="category-icon">⏳</span>
            <div><div class="category-title">SETTING UP</div><div class="category-count">{{ categorized.SETTING_UP|length }}</div></div>
        </div>
        {% for r in categorized.SETTING_UP %}
        <div class="setup-card tier-{{ (r.tier or 'c')|lower }}">
            <div class="setup-header">
                <div><span class="setup-symbol">{{ r.symbol }}</span><span class="setup-price">${{ '%.2f'|format(r.price) }}</span></div>
                {% if r.tier %}<span class="setup-tier tier-{{ r.tier|lower }}-badge">{{ r.tier }}</span>{% endif %}
            </div>
            {% if r.setup_type %}<span class="setup-type setup-{{ r.setup_direction|lower }}">{{ r.setup_direction }} {{ r.setup_type }}</span>{% endif %}
            <div class="setup-metrics">
                <div class="metric"><div class="metric-label">EXEC</div><div class="metric-value yellow">{{ r.exec_readiness }}/14</div></div>
                <div class="metric"><div class="metric-label">SESSION</div><div class="metric-value">{{ r.session_phase }}</div></div>
                <div class="metric"><div class="metric-label">RSI</div><div class="metric-value">{{ '%.0f'|format(r.rsi) }}</div></div>
            </div>
        </div>
        {% endfor %}
        {% endif %}
        
        {% if categorized.BUILDING %}
        <div class="category-header category-building">
            <span class="category-icon">👀</span>
            <div><div class="category-title">BUILDING</div><div class="category-count">{{ categorized.BUILDING|length }}</div></div>
        </div>
        {% for r in categorized.BUILDING %}
        <div class="setup-card">
            <div class="setup-header"><span class="setup-symbol">{{ r.symbol }}</span><span class="setup-price">${{ '%.2f'|format(r.price) }}</span></div>
            <div style="font-size:0.85em;color:#888">{% if r.squeeze_bars > 0 %}Squeeze: {{ r.squeeze_bars }}/6 bars{% else %}Watching...{% endif %}</div>
        </div>
        {% endfor %}
        {% endif %}
        
        {% if categorized.AVOID %}
        <div class="category-header category-avoid">
            <span class="category-icon">❌</span>
            <div><div class="category-title">AVOID</div><div class="category-count">{{ categorized.AVOID|length }}</div></div>
        </div>
        {% for r in categorized.AVOID %}
        <div class="setup-card" style="opacity:0.6">
            <div class="setup-header"><span class="setup-symbol">{{ r.symbol }}</span><span class="setup-price">${{ '%.2f'|format(r.price) }}</span></div>
            {% if r.warnings %}<div class="warnings" style="margin-top:8px">{% for w in r.warnings %}<div class="warning-item">{{ w }}</div>{% endfor %}</div>{% endif %}
        </div>
        {% endfor %}
        {% endif %}
        
        {% if not scan_stats.total %}
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <h3>No Stocks</h3>
            <p style="margin:15px 0">Add stocks to scan</p>
            <button class="btn btn-primary" onclick="openModal('add-stock')">➕ Add Stock</button>
        </div>
        {% endif %}
        
        {% elif tab == 'positions' %}
        <h2 style="margin-bottom:15px">Open Positions</h2>
        {% if positions %}
        {% for p in positions %}
        <div class="card">
            <div class="card-header">
                <div><span style="font-weight:700">{{ p.symbol }}</span><span class="setup-type setup-{{ p.direction|lower }}" style="margin-left:10px">{{ p.direction }}</span></div>
                <span class="{{ 'green' if p.pnl_percent and p.pnl_percent > 0 else 'red' }}" style="font-size:1.2em;font-weight:700">{{ '%+.1f'|format(p.pnl_percent or 0) }}%</span>
            </div>
            <div class="card-body">
                <div class="setup-metrics">
                    <div class="metric"><div class="metric-label">ENTRY</div><div class="metric-value">${{ '%.2f'|format(p.entry_price or 0) }}</div></div>
                    <div class="metric"><div class="metric-label">CURRENT</div><div class="metric-value">${{ '%.2f'|format(p.current_price or p.entry_price or 0) }}</div></div>
                    <div class="metric"><div class="metric-label">P&L</div><div class="metric-value {{ 'green' if p.pnl_dollars and p.pnl_dollars > 0 else 'red' }}">${{ '{:,.0f}'.format(p.pnl_dollars or 0) }}</div></div>
                </div>
                <div style="margin-top:15px"><span style="color:#888;font-size:0.85em">{{ p.tier }}-TIER {{ p.setup_type }} | ${{ p.strike }} {{ p.expiration }}</span></div>
                <div style="display:flex;gap:10px;margin-top:12px">
                    <a href="/close/{{ p.id }}" class="btn btn-danger btn-sm">Close</a>
                    <a href="/analyze/{{ p.symbol }}" class="btn btn-secondary btn-sm">Check</a>
                </div>
            </div>
        </div>
        {% endfor %}
        {% else %}
        <div class="empty-state"><div class="empty-state-icon">📊</div><h3>No Open Positions</h3></div>
        {% endif %}
        
        {% elif tab == 'journal' %}
        <h2 style="margin-bottom:15px">Trading Journal</h2>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">{{ stats.overall.total_trades or 0 }}</div><div class="stat-label">TRADES</div></div>
            <div class="stat-card"><div class="stat-value {{ 'green' if stats.overall.win_rate and stats.overall.win_rate > 50 else 'red' }}">{{ '%.0f'|format(stats.overall.win_rate or 0) }}%</div><div class="stat-label">WIN RATE</div></div>
            <div class="stat-card"><div class="stat-value {{ 'green' if stats.overall.avg_return and stats.overall.avg_return > 0 else 'red' }}">{{ '%+.1f'|format(stats.overall.avg_return or 0) }}%</div><div class="stat-label">AVG RETURN</div></div>
            <div class="stat-card"><div class="stat-value {{ 'green' if stats.overall.total_pnl and stats.overall.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(stats.overall.total_pnl or 0) }}</div><div class="stat-label">TOTAL P&L</div></div>
        </div>
        {% if stats.by_setup %}
        <div class="card"><div class="card-header">📊 By Setup Type</div><div class="card-body">
            <table class="journal-table"><thead><tr><th>Setup</th><th>Trades</th><th>Win%</th><th>Avg</th><th>P&L</th></tr></thead><tbody>
            {% for s in stats.by_setup %}<tr><td>{{ s.tier }}-{{ s.setup_type }}</td><td>{{ s.trades }}</td><td class="{{ 'green' if s.win_rate > 60 else 'red' if s.win_rate < 50 else '' }}">{{ '%.0f'|format(s.win_rate) }}%</td><td class="{{ 'green' if s.avg_return > 0 else 'red' }}">{{ '%+.1f'|format(s.avg_return) }}%</td><td class="{{ 'green' if s.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(s.total_pnl) }}</td></tr>{% endfor %}
            </tbody></table>
        </div></div>
        {% endif %}
        <div class="card"><div class="card-header">📝 Recent Trades</div><div class="card-body">
            {% if journal %}
            <table class="journal-table"><thead><tr><th>Symbol</th><th>Setup</th><th>P&L</th><th>Days</th></tr></thead><tbody>
            {% for j in journal %}<tr><td><span style="font-weight:600">{{ j.symbol }}</span><span class="setup-type setup-{{ j.direction|lower }}" style="font-size:0.7em;padding:2px 6px;margin-left:5px">{{ j.direction }}</span></td><td>{{ j.tier }}-{{ j.setup_type or 'N/A' }}</td><td class="{{ 'green' if j.pnl_percent and j.pnl_percent > 0 else 'red' }}">{{ '%+.1f'|format(j.pnl_percent or 0) }}%</td><td>{{ j.hold_days or 0 }}d</td></tr>{% endfor %}
            </tbody></table>
            {% else %}<div class="empty-state"><p>No trades yet</p></div>{% endif %}
        </div></div>
        
        {% elif tab == 'mentor' %}
        <h2 style="margin-bottom:15px">🎓 AI Mentor</h2>
        <div class="card mentor-card"><div class="card-header">📋 Daily Briefing</div><div class="card-body">
            {% if briefing %}<div style="white-space:pre-wrap;font-size:0.95em;line-height:1.6">{{ briefing }}</div>
            {% else %}<p style="color:#888">Run scan for briefing</p><a href="/generate-briefing" class="btn btn-primary" style="margin-top:10px">Generate</a>{% endif %}
        </div></div>
        <div class="card mentor-card"><div class="card-header">🔍 Your Patterns</div><div class="card-body">
            {% if patterns %}<div style="white-space:pre-wrap;font-size:0.95em;line-height:1.6">{{ patterns.full_analysis }}</div>
            {% else %}<p style="color:#888">Need more trades for analysis</p><a href="/analyze-patterns" class="btn btn-secondary" style="margin-top:10px">Analyze</a>{% endif %}
        </div></div>
        
        {% elif tab == 'settings' %}
        <h2 style="margin-bottom:15px">⚙️ Settings</h2>
        <form method="POST" action="/settings">
            <div class="card"><div class="card-header">💰 Position Sizing</div><div class="card-body">
                <div class="form-group"><label>Capital ($)</label><input type="number" name="capital" value="{{ settings.capital or 100000 }}" step="1000"></div>
                <div class="form-group"><label>A-Tier Size (%)</label><input type="number" name="tier_a_pct" value="{{ settings.tier_a_pct or 30 }}" min="1" max="100"></div>
                <div class="form-group"><label>B-Tier Reduction (%)</label><input type="number" name="tier_b_reduction" value="{{ settings.tier_b_reduction or 25 }}" min="0" max="100"></div>
                <div class="form-group"><label>C-Tier Reduction (%)</label><input type="number" name="tier_c_reduction" value="{{ settings.tier_c_reduction or 50 }}" min="0" max="100"></div>
            </div></div>
            <div class="card"><div class="card-header">📊 Contract Prefs</div><div class="card-body">
                <div class="form-group"><label>Target Delta</label><input type="number" name="target_delta" value="{{ settings.target_delta or 0.50 }}" step="0.05" min="0.30" max="0.80"></div>
                <div class="form-group"><label>Min DTE</label><input type="number" name="min_dte" value="{{ settings.min_dte or 30 }}" min="7" max="90"></div>
                <div class="form-group"><label>Max DTE</label><input type="number" name="max_dte" value="{{ settings.max_dte or 45 }}" min="14" max="120"></div>
            </div></div>
            <button type="submit" class="btn btn-primary" style="width:100%">Save Settings</button>
        </form>
        <div class="card" style="margin-top:20px"><div class="card-header">📋 Watchlist ({{ watchlist|length }})</div><div class="card-body">
            {% for w in watchlist %}<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                <span>{{ w.symbol }} <span style="color:#888;font-size:0.8em">{{ w.sector }}</span></span>
                <a href="/watchlist/remove/{{ w.symbol }}" class="btn btn-danger btn-sm">✕</a>
            </div>{% endfor %}
        </div></div>
        {% endif %}
    </div>
    
    <div class="modal" id="add-stock">
        <div class="modal-content">
            <div class="modal-header"><h3>Add Stock</h3><button class="modal-close" onclick="closeModal('add-stock')">&times;</button></div>
            <div class="modal-body">
                <form method="POST" action="/watchlist/add">
                    <div class="form-group"><label>Symbol</label><input type="text" name="symbol" placeholder="AAPL" required style="text-transform:uppercase"></div>
                    <button type="submit" class="btn btn-primary" style="width:100%">Add</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        function openModal(id){document.getElementById(id).classList.add('active')}
        function closeModal(id){document.getElementById(id).classList.remove('active')}
    </script>
</body>
</html>
'''


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    categorized = get_results_by_category()
    scan_stats = get_scan_stats()
    positions = position_get_all('OPEN')
    return render_template_string(HTML,
        tab='scanner', categorized=categorized, scan_stats=scan_stats,
        is_market_open=is_market_hours(),
        ready_count=len(categorized.get('READY_NOW', [])),
        position_count=len(positions))

@app.route('/scan')
def trigger_scan():
    scan_watchlist(CAPITAL)
    return redirect(url_for('index'))

@app.route('/positions')
def positions_view():
    positions = position_get_all('OPEN')
    categorized = get_results_by_category()
    
    # Get enhanced portfolio analysis
    portfolio = None
    if positions:
        portfolio = analyze_portfolio(positions)
    
    # Build HTML with positions template embedded
    full_html = HTML.replace(
        '{% elif tab == \'positions\' %}',
        '{% elif tab == \'positions\' %}' + POSITIONS_HTML.replace("'''", "")
    )
    
    return render_template_string(HTML,
        tab='positions', positions=positions, portfolio=portfolio,
        is_market_open=is_market_hours(),
        ready_count=len(categorized.get('READY_NOW', [])),
        position_count=len(positions))

@app.route('/journal')
def journal_view():
    journal = journal_get_all(50)
    stats = journal_get_statistics()
    categorized = get_results_by_category()
    positions = position_get_all('OPEN')
    return render_template_string(HTML,
        tab='journal', journal=journal, stats=stats, is_market_open=is_market_hours(),
        ready_count=len(categorized.get('READY_NOW', [])),
        position_count=len(positions))

@app.route('/mentor')
def mentor_view():
    stats = journal_get_statistics()
    categorized = get_results_by_category()
    positions = position_get_all('OPEN')
    briefing = settings_get('daily_briefing')
    patterns = settings_get('pattern_analysis')
    return render_template_string(HTML,
        tab='mentor', stats=stats, briefing=briefing, patterns=patterns,
        is_market_open=is_market_hours(),
        ready_count=len(categorized.get('READY_NOW', [])),
        position_count=len(positions))

@app.route('/settings', methods=['GET', 'POST'])
def settings_view():
    if request.method == 'POST':
        settings_set('capital', float(request.form.get('capital', 100000)))
        settings_set('tier_a_pct', int(request.form.get('tier_a_pct', 30)))
        settings_set('tier_b_reduction', int(request.form.get('tier_b_reduction', 25)))
        settings_set('tier_c_reduction', int(request.form.get('tier_c_reduction', 50)))
        settings_set('target_delta', float(request.form.get('target_delta', 0.50)))
        settings_set('min_dte', int(request.form.get('min_dte', 30)))
        settings_set('max_dte', int(request.form.get('max_dte', 45)))
        return redirect(url_for('settings_view'))
    
    watchlist = watchlist_get_all()
    categorized = get_results_by_category()
    positions = position_get_all('OPEN')
    settings = {
        'capital': settings_get('capital', 100000),
        'tier_a_pct': settings_get('tier_a_pct', 30),
        'tier_b_reduction': settings_get('tier_b_reduction', 25),
        'tier_c_reduction': settings_get('tier_c_reduction', 50),
        'target_delta': settings_get('target_delta', 0.50),
        'min_dte': settings_get('min_dte', 30),
        'max_dte': settings_get('max_dte', 45)
    }
    return render_template_string(HTML,
        tab='settings', settings=settings, watchlist=watchlist,
        is_market_open=is_market_hours(),
        ready_count=len(categorized.get('READY_NOW', [])),
        position_count=len(positions))

@app.route('/watchlist/add', methods=['POST'])
def add_to_watchlist():
    symbol = request.form.get('symbol', '').upper().strip()
    if symbol:
        sector_map = {'AAPL':'Tech','MSFT':'Tech','NVDA':'Tech','GOOGL':'Tech','AMZN':'Consumer','TSLA':'Auto','META':'Tech','AMD':'Tech','JPM':'Fin','BAC':'Fin','SPY':'ETF','QQQ':'ETF','SNAP':'Tech','BIDU':'Tech'}
        watchlist_add(symbol, sector_map.get(symbol, 'Other'))
    return redirect(url_for('index'))

@app.route('/watchlist/remove/<symbol>')
def remove_from_watchlist(symbol):
    watchlist_remove(symbol.upper())
    return redirect(url_for('settings_view'))

@app.route('/execute/<symbol>')
def execute_trade(symbol):
    results = get_cached_results()
    scan_data = next((r for r in results if r['symbol'] == symbol.upper()), None)
    if not scan_data:
        return redirect(url_for('index'))
    
    opts = scan_data.get('options', {}) or {}
    contract = opts.get('recommended_contract', {}) or {}
    
    position_add({
        'symbol': symbol.upper(),
        'direction': scan_data.get('setup_direction', 'CALL'),
        'setup_type': scan_data.get('setup_type'),
        'tier': scan_data.get('tier'),
        'entry_price': contract.get('mid'),
        'entry_delta': contract.get('delta'),
        'entry_iv': scan_data.get('iv_percentile'),
        'entry_underlying': scan_data.get('price'),
        'strike': contract.get('strike'),
        'expiration': contract.get('expiration'),
        'contracts': opts.get('num_contracts', 1),
        'target_price': opts.get('target_price'),
        'stop_price': opts.get('stop_price'),
        'scan_data': scan_data
    })
    return redirect(url_for('positions_view'))

@app.route('/close/<pos_id>')
def close_position(pos_id):
    pos = position_get(pos_id)
    if not pos:
        return redirect(url_for('positions_view'))
    exit_price = float(request.args.get('price', pos.get('entry_price', 0)))
    position_close(pos_id, exit_price, 'MANUAL')
    
    journal_entries = journal_get_all(1)
    if journal_entries:
        review_data = review_trade(dict(journal_entries[0]))
        journal_update_review(journal_entries[0]['id'], review_data['review'], review_data['lessons'])
    return redirect(url_for('journal_view'))

@app.route('/analyze/<symbol>')
def analyze_symbol(symbol):
    result = quick_scan_symbol(symbol.upper())
    if not result:
        return jsonify({'error': 'Could not analyze'})
    advice = get_entry_advice(result, result.get('options'))
    result['ai_advice'] = advice
    return jsonify(result)

@app.route('/generate-briefing')
def generate_briefing_route():
    results = get_cached_results()
    stats = journal_get_statistics()
    positions = position_get_all('OPEN')
    briefing = generate_daily_briefing(results, stats, positions)
    settings_set('daily_briefing', briefing)
    return redirect(url_for('mentor_view'))

@app.route('/analyze-patterns')
def analyze_patterns_route():
    stats = journal_get_statistics()
    journal = journal_get_all(50)
    patterns = analyze_patterns(stats, journal)
    settings_set('pattern_analysis', patterns)
    return redirect(url_for('mentor_view'))

@app.route('/api/scan-results')
def api_scan_results():
    return jsonify(get_results_by_category())

@app.route('/api/positions')
def api_positions():
    return jsonify(position_get_all('OPEN'))

@app.route('/api/stats')
def api_stats():
    return jsonify(journal_get_statistics())

@app.route('/position/<symbol>')
def position_detail(symbol):
    """Detailed position view with news and market context"""
    positions = position_get_all('OPEN')
    pos = next((p for p in positions if p.get('symbol') == symbol.upper()), None)
    
    if not pos:
        return redirect(url_for('positions_view'))
    
    # Get detailed analysis
    analysis = analyze_position(pos)
    
    # Get market context
    market_context = get_position_market_context(symbol)
    
    # Get news
    dte = analysis.time.dte if analysis else 30
    news_summary = get_position_news_summary(symbol, dte)
    
    return jsonify({
        'position': analysis.to_dict() if analysis else {},
        'market_context': market_context,
        'news': news_summary
    })

@app.route('/api/portfolio')
def api_portfolio():
    """Get full portfolio analysis"""
    positions = position_get_all('OPEN')
    if not positions:
        return jsonify({'error': 'No positions'})
    
    portfolio = analyze_portfolio(positions)
    return jsonify(portfolio)

@app.route('/api/market')
def api_market():
    """Get market snapshot"""
    return jsonify(get_market_snapshot())


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'false').lower() == 'true')
