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
from dashboard_template import DASHBOARD_HTML

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
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#000000">
    <title>Trading Cockpit</title>
    <style>
        :root {
            --bg-primary: #000000;
            --bg-secondary: #1c1c1e;
            --bg-tertiary: #2c2c2e;
            --bg-glass: rgba(28,28,30,0.72);
            --text-primary: #ffffff;
            --text-secondary: rgba(255,255,255,0.6);
            --text-tertiary: rgba(255,255,255,0.4);
            --accent: #0a84ff;
            --accent-green: #30d158;
            --accent-red: #ff453a;
            --accent-orange: #ff9f0a;
            --accent-purple: #bf5af2;
            --accent-cyan: #64d2ff;
            --border: rgba(255,255,255,0.08);
            --border-light: rgba(255,255,255,0.12);
            --shadow: 0 8px 32px rgba(0,0,0,0.4);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 20px;
            --transition: all 0.2s cubic-bezier(0.25,0.1,0.25,1);
        }
        
        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding-bottom: 100px;
            line-height: 1.4;
            -webkit-font-smoothing: antialiased;
        }
        
        /* Header */
        .header {
            background: var(--bg-glass);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border);
        }
        
        .logo {
            font-weight: 600;
            font-size: 1.1em;
            letter-spacing: -0.02em;
        }
        .logo span { color: var(--accent); }
        
        .market-status {
            padding: 5px 12px;
            border-radius: 100px;
            font-size: 0.7em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .market-open { background: rgba(48,209,88,0.15); color: var(--accent-green); }
        .market-closed { background: rgba(255,69,58,0.15); color: var(--accent-red); }
        
        /* Navigation */
        .nav {
            display: flex;
            gap: 8px;
            padding: 12px 20px;
            overflow-x: auto;
            scrollbar-width: none;
            -ms-overflow-style: none;
            background: var(--bg-primary);
            border-bottom: 1px solid var(--border);
        }
        .nav::-webkit-scrollbar { display: none; }
        
        .nav-item {
            padding: 10px 18px;
            border-radius: 100px;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.85em;
            font-weight: 500;
            white-space: nowrap;
            transition: var(--transition);
            border: 1px solid transparent;
        }
        .nav-item:hover { 
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }
        .nav-item.active {
            background: var(--accent);
            color: white;
            font-weight: 600;
        }
        .nav-badge {
            background: var(--accent-red);
            color: white;
            font-size: 0.65em;
            padding: 2px 7px;
            border-radius: 100px;
            margin-left: 6px;
            font-weight: 700;
        }
        
        /* Container */
        .container { padding: 20px; max-width: 1200px; margin: 0 auto; }
        
        /* Cards */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            margin-bottom: 16px;
            overflow: hidden;
            transition: var(--transition);
        }
        .card:hover { border-color: var(--border-light); }
        
        .card-header {
            padding: 16px 20px;
            background: rgba(0,0,0,0.2);
            font-weight: 600;
            font-size: 0.9em;
            display: flex;
            justify-content: space-between;
            align-items: center;
            letter-spacing: -0.01em;
        }
        .card-body { padding: 20px; }
        
        /* Category Headers */
        .category-header {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            border-radius: var(--radius-md);
            background: var(--bg-secondary);
            border: 1px solid var(--border);
        }
        .category-ready { border-left: 3px solid var(--accent-green); background: linear-gradient(90deg, rgba(48,209,88,0.08), transparent); }
        .category-setting { border-left: 3px solid var(--accent-cyan); background: linear-gradient(90deg, rgba(100,210,255,0.08), transparent); }
        .category-building { border-left: 3px solid var(--accent-orange); background: linear-gradient(90deg, rgba(255,159,10,0.08), transparent); }
        .category-avoid { border-left: 3px solid var(--accent-red); background: linear-gradient(90deg, rgba(255,69,58,0.08), transparent); }
        .category-icon { font-size: 1.4em; }
        .category-title { font-weight: 700; font-size: 1em; letter-spacing: -0.02em; }
        .category-count { color: var(--text-tertiary); font-size: 0.8em; }
        
        /* Setup Cards */
        .setup-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 20px;
            margin-bottom: 12px;
            transition: var(--transition);
        }
        .setup-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); border-color: var(--border-light); }
        .setup-card.tier-a { border-left: 3px solid var(--accent-green); }
        .setup-card.tier-b { border-left: 3px solid var(--accent-cyan); }
        .setup-card.tier-c { border-left: 3px solid var(--accent-orange); }
        
        .setup-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .setup-symbol { font-size: 1.4em; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
        .setup-price { color: var(--text-secondary); font-size: 0.9em; margin-left: 10px; }
        .setup-tier { font-size: 0.75em; font-weight: 700; padding: 6px 14px; border-radius: 100px; letter-spacing: 0.5px; }
        .tier-a-badge { background: rgba(48,209,88,0.15); color: var(--accent-green); }
        .tier-b-badge { background: rgba(100,210,255,0.15); color: var(--accent-cyan); }
        .tier-c-badge { background: rgba(255,159,10,0.15); color: var(--accent-orange); }
        
        .setup-type {
            display: inline-block;
            padding: 5px 12px;
            border-radius: var(--radius-sm);
            font-size: 0.75em;
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: 0.3px;
        }
        .setup-call { background: rgba(48,209,88,0.12); color: var(--accent-green); }
        .setup-put { background: rgba(255,69,58,0.12); color: var(--accent-red); }
        
        /* Metrics Grid */
        .setup-metrics { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-bottom: 16px; }
        .metric {
            background: var(--bg-tertiary);
            padding: 14px 12px;
            border-radius: var(--radius-md);
            text-align: center;
        }
        .metric-label { font-size: 0.65em; color: var(--text-tertiary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric-value { font-weight: 600; font-size: 1em; }
        
        /* Contract Box */
        .contract-box {
            background: linear-gradient(135deg, rgba(10,132,255,0.08), rgba(10,132,255,0.02));
            border: 1px solid rgba(10,132,255,0.2);
            border-radius: var(--radius-md);
            padding: 18px;
            margin-bottom: 16px;
        }
        .contract-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        .contract-title { font-size: 0.7em; color: var(--accent); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        .contract-strike { font-size: 1.3em; font-weight: 700; }
        .contract-details { display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; font-size: 0.85em; }
        .contract-detail { display: flex; justify-content: space-between; padding: 4px 0; }
        .contract-detail-label { color: var(--text-tertiary); }
        
        /* Warnings */
        .warnings {
            background: rgba(255,159,10,0.08);
            border-radius: var(--radius-md);
            padding: 14px;
            font-size: 0.85em;
        }
        .warning-item { color: var(--accent-orange); padding: 4px 0; }
        
        /* Buttons */
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: var(--radius-md);
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9em;
            transition: var(--transition);
            letter-spacing: -0.01em;
        }
        .btn:active { transform: scale(0.97); }
        .btn-primary { background: var(--accent); color: white; }
        .btn-primary:hover { background: #0077ed; }
        .btn-success { background: var(--accent-green); color: white; }
        .btn-success:hover { background: #28c04d; }
        .btn-danger { background: var(--accent-red); color: white; }
        .btn-danger:hover { background: #e63e35; }
        .btn-warning { background: var(--accent-orange); color: white; }
        .btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); }
        .btn-sm { padding: 8px 16px; font-size: 0.8em; border-radius: var(--radius-sm); }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 20px; }
        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 20px;
            text-align: center;
            transition: var(--transition);
        }
        .stat-card:hover { border-color: var(--border-light); }
        .stat-value { font-size: 1.8em; font-weight: 700; letter-spacing: -0.03em; }
        .stat-label { font-size: 0.7em; color: var(--text-tertiary); margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        /* Table */
        .journal-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        .journal-table th { text-align: left; padding: 14px 12px; background: var(--bg-tertiary); color: var(--text-secondary); font-weight: 500; font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.5px; }
        .journal-table td { padding: 16px 12px; border-bottom: 1px solid var(--border); }
        .journal-table tr:hover { background: rgba(255,255,255,0.02); }
        
        /* Mentor Card */
        .mentor-card {
            background: linear-gradient(135deg, rgba(191,90,242,0.08), rgba(191,90,242,0.02));
            border: 1px solid rgba(191,90,242,0.2);
        }
        .mentor-insight { padding: 18px; border-bottom: 1px solid var(--border); }
        .mentor-insight-title { font-weight: 600; color: var(--accent-purple); margin-bottom: 10px; font-size: 0.85em; }
        
        /* Forms */
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; margin-bottom: 8px; color: var(--text-secondary); font-size: 0.85em; font-weight: 500; }
        .form-group input, .form-group select {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 1em;
            transition: var(--transition);
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(10,132,255,0.2);
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg-secondary);
            border-radius: var(--radius-xl);
            width: 100%;
            max-width: 420px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            animation: modalIn 0.25s ease-out;
        }
        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95) translateY(10px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .modal-body { padding: 24px; }
        .modal-close { background: none; border: none; color: var(--text-tertiary); font-size: 1.3em; cursor: pointer; padding: 4px; }
        .modal-close:hover { color: var(--text-primary); }
        
        /* Colors */
        .green { color: var(--accent-green); }
        .red { color: var(--accent-red); }
        .yellow { color: var(--accent-orange); }
        .cyan { color: var(--accent-cyan); }
        .purple { color: var(--accent-purple); }
        
        /* Empty State */
        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-tertiary); }
        .empty-state-icon { font-size: 3.5em; margin-bottom: 20px; opacity: 0.5; }
        
        /* Responsive */
        @media(max-width:768px) {
            .stats-grid { grid-template-columns: repeat(2,1fr); }
            .setup-metrics { grid-template-columns: repeat(2,1fr); }
            .container { padding: 16px; }
            .card-body { padding: 16px; }
        }
        
        /* Animations */
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .pulse { animation: pulse 2s infinite; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
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
        <a href="/" class="nav-item {{ 'active' if tab == 'dashboard' else '' }}">🚀 Dashboard</a>
        <a href="/scanner" class="nav-item {{ 'active' if tab == 'scanner' else '' }}">🔥 Scanner{% if ready_count %}<span class="nav-badge">{{ ready_count }}</span>{% endif %}</a>
        <a href="/positions" class="nav-item {{ 'active' if tab == 'positions' else '' }}">📊 Positions{% if position_count %}<span class="nav-badge">{{ position_count }}</span>{% endif %}</a>
        <a href="/journal" class="nav-item {{ 'active' if tab == 'journal' else '' }}">📝 Journal</a>
        <a href="/mentor" class="nav-item {{ 'active' if tab == 'mentor' else '' }}">🎓 Mentor</a>
        <a href="/settings" class="nav-item {{ 'active' if tab == 'settings' else '' }}">⚙️</a>
    </div>
    
    <div class="container">
        {% if tab == 'dashboard' %}
        ''' + DASHBOARD_HTML + '''
        {% elif tab == 'scanner' %}
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
    """Dashboard - Command Center homepage"""
    from news_service import get_market_news
    
    categorized = get_results_by_category()
    scan_stats = get_scan_stats()
    positions = position_get_all('OPEN')
    stats = journal_get_statistics()
    
    # Get portfolio analysis
    portfolio = None
    if positions:
        portfolio = analyze_portfolio(positions)
    
    # Get market data
    market_snapshot = get_market_snapshot()
    
    # Build market summary
    market = {
        'risk_env': market_snapshot.get('internals', {}).get('risk_environment', 'NEUTRAL'),
        'vix': market_snapshot.get('vix', {}).get('vix', 15),
        'vix_regime': market_snapshot.get('vix', {}).get('regime', 'NORMAL'),
        'trend': market_snapshot.get('spy', {}).get('trend', 'NEUTRAL'),
        'breadth': market_snapshot.get('internals', {}).get('breadth', 'MIXED')
    }
    
    # Calculate energy score (0-100)
    energy_score = market_snapshot.get('internals', {}).get('risk_score', 50)
    energy_position = energy_score  # Position on the gauge
    
    # Build indices data
    indices = [
        {'symbol': 'SPY', 'price': market_snapshot.get('spy', {}).get('price', 0), 
         'change_pct': market_snapshot.get('spy', {}).get('change_pct', 0),
         'strength': 50 + market_snapshot.get('spy', {}).get('change_pct', 0) * 20},
        {'symbol': 'QQQ', 'price': 0, 'change_pct': market_snapshot.get('internals', {}).get('qqq_change', 0),
         'strength': 50 + market_snapshot.get('internals', {}).get('qqq_change', 0) * 20},
        {'symbol': 'VIX', 'price': market_snapshot.get('vix', {}).get('vix', 15), 
         'change_pct': market_snapshot.get('vix', {}).get('change_pct', 0),
         'strength': max(0, 100 - market_snapshot.get('vix', {}).get('vix', 15) * 3)},
        {'symbol': 'IWM', 'price': 0, 'change_pct': market_snapshot.get('internals', {}).get('iwm_change', 0),
         'strength': 50 + market_snapshot.get('internals', {}).get('iwm_change', 0) * 20}
    ]
    
    # Get sectors
    sectors = market_snapshot.get('sectors', [])[:11]
    
    # Get top setups
    ready_now = categorized.get('READY_NOW', [])
    top_setups = sorted(ready_now, key=lambda x: x.get('priority_score', 0), reverse=True)[:3]
    
    # Get news
    news = get_market_news(5)
    
    # Build alerts
    alerts = []
    if portfolio:
        for h in portfolio.get('heat_map', []):
            if h.get('health') == 'WEAK':
                alerts.append({'icon': '🔴', 'color': '#ff5252', 'message': f"{h['symbol']} health WEAK - review position"})
            if h.get('pnl_percent', 0) <= -40:
                alerts.append({'icon': '🔴', 'color': '#ff5252', 'message': f"{h['symbol']} near stop ({h['pnl_percent']:.0f}%)"})
    
    for setup in ready_now[:2]:
        alerts.append({'icon': '🟢', 'color': '#00c853', 'message': f"{setup['symbol']} {setup['tier']}-tier ready - exec {setup['exec_readiness']}/14"})
    
    # Get briefing
    briefing = settings_get('daily_briefing')
    
    return render_template_string(HTML,
        tab='dashboard',
        market=market,
        energy_score=energy_score,
        energy_position=energy_position,
        indices=indices,
        sectors=sectors,
        portfolio=portfolio,
        scan_stats=scan_stats,
        top_setups=top_setups,
        news=news,
        alerts=alerts,
        stats=stats,
        briefing=briefing,
        categorized=categorized,
        is_market_open=is_market_hours(),
        ready_count=len(ready_now),
        position_count=len(positions))

@app.route('/scanner')
def scanner_view():
    """Scanner tab - find setups"""
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

@app.route('/add-position', methods=['POST'])
def add_manual_position():
    """Add a discretionary/manual position"""
    symbol = request.form.get('symbol', '').upper().strip()
    direction = request.form.get('direction', 'CALL')
    contracts = int(request.form.get('contracts', 1))
    strike = float(request.form.get('strike', 0))
    expiration = request.form.get('expiration', '')
    entry_price = float(request.form.get('entry_price', 0))
    entry_underlying = float(request.form.get('entry_underlying', 0) or 0)
    entry_delta = float(request.form.get('entry_delta', 0) or 0.50)
    setup_type = request.form.get('setup_type', 'DISCRETIONARY')
    notes = request.form.get('notes', '')
    
    if not symbol or not strike or not expiration or not entry_price:
        return redirect(url_for('positions_view'))
    
    position_add({
        'symbol': symbol,
        'direction': direction,
        'setup_type': setup_type,
        'tier': 'D',  # Discretionary tier
        'entry_price': entry_price,
        'entry_delta': entry_delta,
        'entry_iv': None,
        'entry_underlying': entry_underlying,
        'strike': strike,
        'expiration': expiration,
        'contracts': contracts,
        'target_price': entry_price * 1.5,  # Default 50% target
        'stop_price': entry_price * 0.5,    # Default 50% stop
        'notes': notes,
        'scan_data': {'manual_entry': True, 'notes': notes}
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
