"""
Dashboard Template
==================
Cockpit-style overview homepage with market energy visualization
"""

DASHBOARD_HTML = '''
<!-- DASHBOARD TAB - COMMAND CENTER -->

<!-- Market Energy Gauge -->
<div class="card" style="background:linear-gradient(135deg,rgba(0,212,255,0.05),rgba(123,44,191,0.05));border:1px solid rgba(0,212,255,0.2);margin-bottom:20px">
    <div class="card-body" style="text-align:center;padding:25px">
        <div style="font-size:0.85em;color:#888;margin-bottom:15px;text-transform:uppercase;letter-spacing:1px">Market Energy</div>
        
        <!-- Energy Bar -->
        <div style="position:relative;height:40px;background:linear-gradient(90deg,#ff5252 0%,#ff9800 25%,#ffc107 40%,#8bc34a 60%,#00c853 75%,#00c853 100%);border-radius:20px;margin:0 auto;max-width:600px">
            <div style="position:absolute;left:{{ energy_position }}%;top:-5px;transform:translateX(-50%);transition:left 0.5s">
                <div style="width:4px;height:50px;background:white;border-radius:2px;box-shadow:0 0 10px rgba(255,255,255,0.5)"></div>
                <div style="background:white;color:#1a1a2e;padding:4px 12px;border-radius:12px;font-weight:700;font-size:0.85em;margin-top:5px;white-space:nowrap">{{ energy_score }}</div>
            </div>
        </div>
        
        <div style="display:flex;justify-content:space-between;max-width:600px;margin:15px auto 0;font-size:0.75em;color:#888">
            <span>FEAR</span>
            <span>NEUTRAL</span>
            <span>GREED</span>
        </div>
        
        <!-- Environment Summary -->
        <div style="display:flex;justify-content:center;gap:20px;margin-top:20px;flex-wrap:wrap">
            <div style="background:rgba(0,0,0,0.3);padding:8px 16px;border-radius:20px;font-size:0.85em">
                <span style="color:#888">Environment:</span>
                <span style="font-weight:600;color:{% if market.risk_env == 'RISK-ON' %}#00c853{% elif market.risk_env == 'RISK-OFF' %}#ff5252{% else %}#ffc107{% endif %}">{{ market.risk_env }}</span>
            </div>
            <div style="background:rgba(0,0,0,0.3);padding:8px 16px;border-radius:20px;font-size:0.85em">
                <span style="color:#888">VIX:</span>
                <span style="font-weight:600;color:{% if market.vix < 15 %}#00c853{% elif market.vix > 25 %}#ff5252{% else %}#ffc107{% endif %}">{{ '%.1f'|format(market.vix) }} ({{ market.vix_regime }})</span>
            </div>
            <div style="background:rgba(0,0,0,0.3);padding:8px 16px;border-radius:20px;font-size:0.85em">
                <span style="color:#888">Trend:</span>
                <span style="font-weight:600;color:{% if 'BULL' in market.trend %}#00c853{% elif 'BEAR' in market.trend %}#ff5252{% else %}#ffc107{% endif %}">{{ market.trend }}</span>
            </div>
            <div style="background:rgba(0,0,0,0.3);padding:8px 16px;border-radius:20px;font-size:0.85em">
                <span style="color:#888">Breadth:</span>
                <span style="font-weight:600">{{ market.breadth }}</span>
            </div>
        </div>
    </div>
</div>

<!-- Index Cards Row -->
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px">
    {% for idx in indices %}
    <div class="card" style="text-align:center;padding:15px">
        <div style="font-size:0.8em;color:#888;margin-bottom:5px">{{ idx.symbol }}</div>
        <div style="font-size:1.4em;font-weight:700">${{ '%.2f'|format(idx.price) }}</div>
        <div style="font-size:0.95em;font-weight:600;margin:5px 0" class="{{ 'green' if idx.change_pct > 0 else 'red' }}">
            {{ '▲' if idx.change_pct > 0 else '▼' }} {{ '%+.2f'|format(idx.change_pct) }}%
        </div>
        <div style="height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden">
            <div style="height:100%;width:{{ idx.strength }}%;background:{% if idx.change_pct > 0.5 %}#00c853{% elif idx.change_pct > 0 %}#8bc34a{% elif idx.change_pct > -0.5 %}#ffc107{% else %}#ff5252{% endif %};border-radius:4px"></div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Main Content Grid -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px">
    
    <!-- Opportunities Panel -->
    <div class="card">
        <div class="card-header">
            <span>🔥 Today's Opportunities</span>
            <a href="/scanner" class="btn btn-sm btn-primary">View All</a>
        </div>
        <div class="card-body">
            <div style="margin-bottom:15px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600;color:#00c853">READY NOW</span>
                    <span style="font-size:1.2em;font-weight:700">{{ scan_stats.ready_now }}</span>
                </div>
                <div style="height:12px;background:rgba(255,255,255,0.1);border-radius:6px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.ready_now / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,#00c853,#69f0ae);border-radius:6px"></div>
                </div>
            </div>
            
            <div style="margin-bottom:15px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600;color:#00bcd4">SETTING UP</span>
                    <span style="font-size:1.2em;font-weight:700">{{ scan_stats.setting_up }}</span>
                </div>
                <div style="height:12px;background:rgba(255,255,255,0.1);border-radius:6px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.setting_up / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,#00bcd4,#4dd0e1);border-radius:6px"></div>
                </div>
            </div>
            
            <div style="margin-bottom:15px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600;color:#ffc107">BUILDING</span>
                    <span style="font-size:1.2em;font-weight:700">{{ scan_stats.building }}</span>
                </div>
                <div style="height:12px;background:rgba(255,255,255,0.1);border-radius:6px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.building / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,#ffc107,#ffeb3b);border-radius:6px"></div>
                </div>
            </div>
            
            {% if top_setups %}
            <div style="margin-top:20px;padding-top:15px;border-top:1px solid rgba(255,255,255,0.1)">
                <div style="font-size:0.8em;color:#888;margin-bottom:10px">TOP SETUP TODAY</div>
                {% for setup in top_setups[:1] %}
                <div style="background:rgba(0,200,83,0.1);border:1px solid rgba(0,200,83,0.2);border-radius:10px;padding:12px">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <span style="font-weight:700;color:#00d4ff;font-size:1.1em">{{ setup.symbol }}</span>
                            <span style="background:rgba(0,200,83,0.2);color:#00c853;padding:2px 8px;border-radius:4px;font-size:0.75em;margin-left:8px">{{ setup.tier }}-TIER</span>
                        </div>
                        <span style="font-weight:600">{{ setup.exec_readiness }}/14</span>
                    </div>
                    <div style="font-size:0.85em;color:#888;margin-top:8px">{{ setup.setup_type }} | Priority: {{ setup.priority_score }}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Positions Panel -->
    <div class="card">
        <div class="card-header">
            <span>📊 Your Positions</span>
            <a href="/positions" class="btn btn-sm btn-secondary">Manage</a>
        </div>
        <div class="card-body">
            {% if portfolio %}
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:15px">
                <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                    <div style="font-size:0.7em;color:#888">OPEN</div>
                    <div style="font-size:1.4em;font-weight:700">{{ portfolio.total_positions }}</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                    <div style="font-size:0.7em;color:#888">TOTAL P&L</div>
                    <div style="font-size:1.4em;font-weight:700" class="{{ 'green' if portfolio.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(portfolio.total_pnl) }}</div>
                </div>
            </div>
            
            <!-- Position Mini Bars -->
            {% for h in portfolio.heat_map[:4] %}
            <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                <div style="width:60px;font-weight:600">{{ h.symbol }}</div>
                <div style="flex:1;height:20px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden;position:relative">
                    {% if h.pnl_percent > 0 %}
                    <div style="position:absolute;left:50%;width:{{ (h.pnl_percent / 2)|min(50) }}%;height:100%;background:linear-gradient(90deg,#00c853,#69f0ae);border-radius:0 4px 4px 0"></div>
                    {% else %}
                    <div style="position:absolute;right:50%;width:{{ (h.pnl_percent|abs / 2)|min(50) }}%;height:100%;background:linear-gradient(90deg,#ff5252,#ff8a80);border-radius:4px 0 0 4px"></div>
                    {% endif %}
                    <div style="position:absolute;left:50%;top:0;bottom:0;width:2px;background:rgba(255,255,255,0.3)"></div>
                </div>
                <div style="width:60px;text-align:right;font-weight:600" class="{{ 'green' if h.pnl_percent > 0 else 'red' }}">{{ '%+.0f'|format(h.pnl_percent) }}%</div>
                <div style="width:20px;text-align:center">
                    {% if h.health == 'STRONG' %}🟢{% elif h.health == 'GOOD' %}🟢{% elif h.health == 'CAUTION' %}🟡{% else %}🔴{% endif %}
                </div>
            </div>
            {% endfor %}
            
            {% else %}
            <div style="text-align:center;padding:30px;color:#888">
                <div style="font-size:2em;margin-bottom:10px">📊</div>
                <div>No open positions</div>
                <a href="/scanner" class="btn btn-primary btn-sm" style="margin-top:15px">Find Setups</a>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Sector Rotation -->
<div class="card" style="margin-bottom:20px">
    <div class="card-header">📈 Sector Rotation</div>
    <div class="card-body">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
            {% for sector in sectors %}
            <div style="flex:1;min-width:100px;background:{% if sector.change_pct > 1 %}rgba(0,200,83,0.2){% elif sector.change_pct > 0 %}rgba(0,200,83,0.1){% elif sector.change_pct > -0.5 %}rgba(255,193,7,0.1){% else %}rgba(255,82,82,0.1){% endif %};padding:10px;border-radius:8px;text-align:center">
                <div style="font-weight:700;font-size:0.85em">{{ sector.etf }}</div>
                <div style="font-size:0.7em;color:#888">{{ sector.name[:12] }}</div>
                <div style="font-weight:600;margin-top:4px" class="{{ 'green' if sector.change_pct > 0 else 'red' }}">{{ '%+.1f'|format(sector.change_pct) }}%</div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- AI Briefing -->
<div class="card" style="background:linear-gradient(135deg,rgba(123,44,191,0.1),rgba(123,44,191,0.02));border:1px solid rgba(123,44,191,0.2);margin-bottom:20px">
    <div class="card-header">
        <span>🤖 AI Morning Briefing</span>
        <a href="/generate-briefing" class="btn btn-sm btn-secondary">Refresh</a>
    </div>
    <div class="card-body">
        {% if briefing %}
        <div style="font-size:0.95em;line-height:1.7;white-space:pre-wrap">{{ briefing }}</div>
        {% else %}
        <div style="text-align:center;padding:20px;color:#888">
            <p>Generate your morning briefing to get AI-powered insights</p>
            <a href="/generate-briefing" class="btn btn-primary" style="margin-top:10px">Generate Briefing</a>
        </div>
        {% endif %}
    </div>
</div>

<!-- Bottom Grid: News + Alerts + Performance -->
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px">
    
    <!-- Market Pulse -->
    <div class="card">
        <div class="card-header">📰 Market Pulse</div>
        <div class="card-body">
            {% if news %}
            {% for item in news[:4] %}
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.85em">
                <div style="margin-bottom:4px">{{ item.title[:60] }}{% if item.title|length > 60 %}...{% endif %}</div>
                <div style="font-size:0.75em;color:#888">{{ item.time_ago }} • {{ item.source }}</div>
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align:center;padding:20px;color:#888;font-size:0.85em">
                No recent news
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Alerts -->
    <div class="card">
        <div class="card-header">⚠️ Alerts</div>
        <div class="card-body">
            {% if alerts %}
            {% for alert in alerts[:5] %}
            <div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.85em">
                <span style="margin-right:8px">{{ alert.icon }}</span>
                <span style="color:{{ alert.color }}">{{ alert.message }}</span>
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align:center;padding:20px;color:#888;font-size:0.85em">
                ✅ No alerts - all clear
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Your Performance -->
    <div class="card">
        <div class="card-header">📊 Your Edge (30d)</div>
        <div class="card-body">
            {% if stats.recent_30d %}
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px">
                <div style="text-align:center">
                    <div style="font-size:1.5em;font-weight:700">{{ stats.recent_30d.trades }}</div>
                    <div style="font-size:0.7em;color:#888">Trades</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:1.5em;font-weight:700" class="{{ 'green' if stats.recent_30d.win_rate > 50 else 'red' }}">{{ '%.0f'|format(stats.recent_30d.win_rate) }}%</div>
                    <div style="font-size:0.7em;color:#888">Win Rate</div>
                </div>
            </div>
            <div style="text-align:center;padding:10px;background:rgba(0,0,0,0.2);border-radius:8px">
                <div style="font-size:0.7em;color:#888">Total P&L</div>
                <div style="font-size:1.3em;font-weight:700" class="{{ 'green' if stats.recent_30d.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(stats.recent_30d.total_pnl) }}</div>
            </div>
            {% if stats.by_setup %}
            <div style="margin-top:15px;padding-top:15px;border-top:1px solid rgba(255,255,255,0.1)">
                <div style="font-size:0.75em;color:#888;margin-bottom:8px">BEST SETUP</div>
                {% set best = stats.by_setup|sort(attribute='win_rate', reverse=true)|first %}
                <div style="font-size:0.85em">
                    <span style="color:#00c853">🏆</span> {{ best.tier }}-{{ best.setup_type }}: {{ '%.0f'|format(best.win_rate) }}%
                </div>
            </div>
            {% endif %}
            {% else %}
            <div style="text-align:center;padding:20px;color:#888;font-size:0.85em">
                Complete trades to build stats
            </div>
            {% endif %}
        </div>
    </div>
</div>
'''
