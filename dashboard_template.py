"""
Dashboard Template
==================
Cockpit-style overview homepage with market energy visualization
"""

DASHBOARD_HTML = '''
<!-- DASHBOARD TAB - COMMAND CENTER -->

<!-- Market Energy Gauge -->
<div class="card" style="background:linear-gradient(135deg,rgba(10,132,255,0.06),rgba(191,90,242,0.06));border-color:rgba(10,132,255,0.15);margin-bottom:24px">
    <div class="card-body" style="text-align:center;padding:32px 24px">
        <div style="font-size:0.75em;color:var(--text-tertiary);margin-bottom:20px;text-transform:uppercase;letter-spacing:1.5px;font-weight:600">Market Energy</div>
        
        <!-- Energy Bar -->
        <div style="position:relative;height:44px;background:linear-gradient(90deg,#ff453a 0%,#ff9f0a 30%,#ffd60a 50%,#30d158 70%,#30d158 100%);border-radius:22px;margin:0 auto;max-width:500px;box-shadow:0 4px 24px rgba(0,0,0,0.3)">
            <div style="position:absolute;left:{{ energy_position }}%;top:-6px;transform:translateX(-50%);transition:left 0.5s cubic-bezier(0.25,0.1,0.25,1)">
                <div style="width:4px;height:56px;background:white;border-radius:2px;box-shadow:0 0 16px rgba(255,255,255,0.6)"></div>
                <div style="background:white;color:var(--bg-primary);padding:6px 16px;border-radius:100px;font-weight:700;font-size:0.85em;margin-top:8px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.3)">{{ energy_score }}</div>
            </div>
        </div>
        
        <div style="display:flex;justify-content:space-between;max-width:500px;margin:18px auto 0;font-size:0.7em;color:var(--text-tertiary);font-weight:500;letter-spacing:0.5px">
            <span>FEAR</span>
            <span>NEUTRAL</span>
            <span>GREED</span>
        </div>
        
        <!-- Environment Pills -->
        <div style="display:flex;justify-content:center;gap:12px;margin-top:24px;flex-wrap:wrap">
            <div style="background:var(--bg-tertiary);padding:10px 18px;border-radius:100px;font-size:0.8em;border:1px solid var(--border)">
                <span style="color:var(--text-tertiary)">Environment</span>
                <span style="font-weight:600;margin-left:6px;color:{% if market.risk_env == 'RISK-ON' %}var(--accent-green){% elif market.risk_env == 'RISK-OFF' %}var(--accent-red){% else %}var(--accent-orange){% endif %}">{{ market.risk_env }}</span>
            </div>
            <div style="background:var(--bg-tertiary);padding:10px 18px;border-radius:100px;font-size:0.8em;border:1px solid var(--border)">
                <span style="color:var(--text-tertiary)">VIX</span>
                <span style="font-weight:600;margin-left:6px;color:{% if market.vix < 15 %}var(--accent-green){% elif market.vix > 25 %}var(--accent-red){% else %}var(--accent-orange){% endif %}">{{ '%.1f'|format(market.vix) }}</span>
                <span style="color:var(--text-tertiary);font-size:0.85em;margin-left:4px">({{ market.vix_regime }})</span>
            </div>
            <div style="background:var(--bg-tertiary);padding:10px 18px;border-radius:100px;font-size:0.8em;border:1px solid var(--border)">
                <span style="color:var(--text-tertiary)">Trend</span>
                <span style="font-weight:600;margin-left:6px;color:{% if 'BULL' in market.trend %}var(--accent-green){% elif 'BEAR' in market.trend %}var(--accent-red){% else %}var(--accent-orange){% endif %}">{{ market.trend }}</span>
            </div>
        </div>
    </div>
</div>

<!-- Index Cards Row -->
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">
    {% for idx in indices %}
    <div class="card" style="text-align:center;padding:20px 16px">
        <div style="font-size:0.75em;color:var(--text-tertiary);margin-bottom:8px;font-weight:500;letter-spacing:0.5px">{{ idx.symbol }}</div>
        <div style="font-size:1.5em;font-weight:700;letter-spacing:-0.02em">{% if idx.symbol != 'VIX' %}${% endif %}{{ '%.2f'|format(idx.price) }}</div>
        <div style="font-size:0.95em;font-weight:600;margin:8px 0" class="{{ 'green' if idx.change_pct > 0 else 'red' }}">
            {{ '▲' if idx.change_pct > 0 else '▼' }} {{ '%+.2f'|format(idx.change_pct) }}%
        </div>
        <div style="height:6px;background:var(--bg-tertiary);border-radius:3px;overflow:hidden">
            <div style="height:100%;width:{{ [idx.strength, 100]|min }}%;background:{% if idx.change_pct > 0.5 %}var(--accent-green){% elif idx.change_pct > 0 %}rgba(48,209,88,0.6){% elif idx.change_pct > -0.5 %}var(--accent-orange){% else %}var(--accent-red){% endif %};border-radius:3px;transition:width 0.5s"></div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Main Content Grid -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px">
    
    <!-- Opportunities Panel -->
    <div class="card">
        <div class="card-header">
            <span>🔥 Today's Opportunities</span>
            <a href="/scanner" class="btn btn-sm btn-primary">View All</a>
        </div>
        <div class="card-body">
            <div style="margin-bottom:18px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <span style="font-weight:600;color:var(--accent-green);font-size:0.9em">READY NOW</span>
                    <span style="font-size:1.4em;font-weight:700">{{ scan_stats.ready_now }}</span>
                </div>
                <div style="height:8px;background:var(--bg-tertiary);border-radius:4px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.ready_now / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,var(--accent-green),#69f0ae);border-radius:4px"></div>
                </div>
            </div>
            
            <div style="margin-bottom:18px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <span style="font-weight:600;color:var(--accent-cyan);font-size:0.9em">SETTING UP</span>
                    <span style="font-size:1.4em;font-weight:700">{{ scan_stats.setting_up }}</span>
                </div>
                <div style="height:8px;background:var(--bg-tertiary);border-radius:4px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.setting_up / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,var(--accent-cyan),#a2e4ff);border-radius:4px"></div>
                </div>
            </div>
            
            <div style="margin-bottom:18px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <span style="font-weight:600;color:var(--accent-orange);font-size:0.9em">BUILDING</span>
                    <span style="font-size:1.4em;font-weight:700">{{ scan_stats.building }}</span>
                </div>
                <div style="height:8px;background:var(--bg-tertiary);border-radius:4px;overflow:hidden">
                    <div style="height:100%;width:{{ (scan_stats.building / (scan_stats.total or 1) * 100)|int }}%;background:linear-gradient(90deg,var(--accent-orange),#ffc864);border-radius:4px"></div>
                </div>
            </div>
            
            {% if top_setups %}
            <div style="margin-top:24px;padding-top:20px;border-top:1px solid var(--border)">
                <div style="font-size:0.7em;color:var(--text-tertiary);margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600">Top Setup Today</div>
                {% for setup in top_setups[:1] %}
                <div style="background:linear-gradient(135deg,rgba(48,209,88,0.08),transparent);border:1px solid rgba(48,209,88,0.2);border-radius:var(--radius-md);padding:16px">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <span style="font-weight:700;color:var(--text-primary);font-size:1.2em">{{ setup.symbol }}</span>
                            <span style="background:rgba(48,209,88,0.15);color:var(--accent-green);padding:4px 10px;border-radius:100px;font-size:0.7em;font-weight:600;margin-left:10px">{{ setup.tier }}-TIER</span>
                        </div>
                        <span style="font-weight:700;font-size:1.1em;color:var(--accent-green)">{{ setup.exec_readiness }}/14</span>
                    </div>
                    <div style="font-size:0.85em;color:var(--text-secondary);margin-top:10px">{{ setup.setup_type }}</div>
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
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:20px">
                <div style="background:var(--bg-tertiary);padding:16px;border-radius:var(--radius-md);text-align:center">
                    <div style="font-size:0.65em;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.5px">Open</div>
                    <div style="font-size:1.6em;font-weight:700;margin-top:4px">{{ portfolio.total_positions }}</div>
                </div>
                <div style="background:var(--bg-tertiary);padding:16px;border-radius:var(--radius-md);text-align:center">
                    <div style="font-size:0.65em;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.5px">Total P&L</div>
                    <div style="font-size:1.6em;font-weight:700;margin-top:4px" class="{{ 'green' if portfolio.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(portfolio.total_pnl) }}</div>
                </div>
            </div>
            
            <!-- Position Mini Bars -->
            {% for h in portfolio.heat_map[:4] %}
            <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)">
                <div style="width:55px;font-weight:600;font-size:0.95em">{{ h.symbol }}</div>
                <div style="flex:1;height:24px;background:var(--bg-tertiary);border-radius:4px;overflow:hidden;position:relative">
                    {% if h.pnl_percent > 0 %}
                    <div style="position:absolute;left:50%;width:{{ (h.pnl_percent / 2)|min(50) }}%;height:100%;background:linear-gradient(90deg,var(--accent-green),#69f0ae);border-radius:0 4px 4px 0"></div>
                    {% else %}
                    <div style="position:absolute;right:50%;width:{{ (h.pnl_percent|abs / 2)|min(50) }}%;height:100%;background:linear-gradient(270deg,var(--accent-red),#ff8a80);border-radius:4px 0 0 4px"></div>
                    {% endif %}
                    <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.15)"></div>
                </div>
                <div style="width:55px;text-align:right;font-weight:600;font-size:0.9em" class="{{ 'green' if h.pnl_percent > 0 else 'red' }}">{{ '%+.0f'|format(h.pnl_percent) }}%</div>
                <div style="width:24px;text-align:center">
                    {% if h.health == 'STRONG' %}🟢{% elif h.health == 'GOOD' %}🟢{% elif h.health == 'CAUTION' %}🟡{% else %}🔴{% endif %}
                </div>
            </div>
            {% endfor %}
            
            {% else %}
            <div style="text-align:center;padding:40px 20px;color:var(--text-tertiary)">
                <div style="font-size:2.5em;margin-bottom:16px;opacity:0.5">📊</div>
                <div style="font-size:0.95em">No open positions</div>
                <a href="/scanner" class="btn btn-primary btn-sm" style="margin-top:20px">Find Setups</a>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Sector Rotation -->
<div class="card" style="margin-bottom:24px">
    <div class="card-header">📈 Sector Rotation</div>
    <div class="card-body">
        <div style="display:flex;gap:10px;flex-wrap:wrap">
            {% for sector in sectors %}
            <div style="flex:1;min-width:90px;background:{% if sector.change_pct > 1 %}rgba(48,209,88,0.12){% elif sector.change_pct > 0 %}rgba(48,209,88,0.06){% elif sector.change_pct > -0.5 %}rgba(255,159,10,0.08){% else %}rgba(255,69,58,0.08){% endif %};padding:14px 10px;border-radius:var(--radius-md);text-align:center;border:1px solid var(--border)">
                <div style="font-weight:700;font-size:0.85em">{{ sector.etf }}</div>
                <div style="font-size:0.65em;color:var(--text-tertiary);margin-top:2px">{{ sector.name[:10] }}</div>
                <div style="font-weight:700;margin-top:6px;font-size:0.9em" class="{{ 'green' if sector.change_pct > 0 else 'red' }}">{{ '%+.1f'|format(sector.change_pct) }}%</div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- AI Briefing -->
<div class="card mentor-card" style="margin-bottom:24px">
    <div class="card-header">
        <span>🤖 AI Morning Briefing</span>
        <a href="/generate-briefing" class="btn btn-sm btn-secondary">Refresh</a>
    </div>
    <div class="card-body">
        {% if briefing %}
        <div style="font-size:0.95em;line-height:1.7;white-space:pre-wrap;color:var(--text-secondary)">{{ briefing }}</div>
        {% else %}
        <div style="text-align:center;padding:30px;color:var(--text-tertiary)">
            <p style="margin-bottom:16px">Generate your morning briefing to get AI-powered insights</p>
            <a href="/generate-briefing" class="btn btn-primary">Generate Briefing</a>
        </div>
        {% endif %}
    </div>
</div>

<!-- Bottom Grid: News + Alerts + Performance -->
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
    
    <!-- Market Pulse -->
    <div class="card">
        <div class="card-header">📰 Market Pulse</div>
        <div class="card-body" style="padding:12px 20px">
            {% if news %}
            {% for item in news[:4] %}
            <div style="padding:12px 0;border-bottom:1px solid var(--border)">
                <div style="font-size:0.85em;line-height:1.4;margin-bottom:6px">{{ item.title[:55] }}{% if item.title|length > 55 %}...{% endif %}</div>
                <div style="font-size:0.7em;color:var(--text-tertiary)">{{ item.time_ago }} • {{ item.source }}</div>
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align:center;padding:24px;color:var(--text-tertiary);font-size:0.85em">
                No recent news
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Alerts -->
    <div class="card">
        <div class="card-header">⚠️ Alerts</div>
        <div class="card-body" style="padding:12px 20px">
            {% if alerts %}
            {% for alert in alerts[:5] %}
            <div style="padding:10px 0;border-bottom:1px solid var(--border);font-size:0.85em">
                <span style="margin-right:8px">{{ alert.icon }}</span>
                <span style="color:{{ alert.color }}">{{ alert.message }}</span>
            </div>
            {% endfor %}
            {% else %}
            <div style="text-align:center;padding:24px;color:var(--text-tertiary);font-size:0.85em">
                ✅ No alerts - all clear
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Your Performance -->
    <div class="card">
        <div class="card-header">📊 Your Edge (30d)</div>
        <div class="card-body">
            {% if stats and stats.get('total_trades', 0) > 0 %}
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
                <div style="text-align:center">
                    <div style="font-size:1.6em;font-weight:700">{{ stats.total_trades }}</div>
                    <div style="font-size:0.65em;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.5px">Trades</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:1.6em;font-weight:700" class="{{ 'green' if stats.win_rate > 50 else 'red' }}">{{ '%.0f'|format(stats.win_rate) }}%</div>
                    <div style="font-size:0.65em;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.5px">Win Rate</div>
                </div>
            </div>
            <div style="text-align:center;padding:14px;background:var(--bg-tertiary);border-radius:var(--radius-md)">
                <div style="font-size:0.65em;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.5px">Total P&L</div>
                <div style="font-size:1.4em;font-weight:700;margin-top:4px" class="{{ 'green' if stats.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(stats.total_pnl or 0) }}</div>
            </div>
            {% else %}
            <div style="text-align:center;padding:24px;color:var(--text-tertiary);font-size:0.85em">
                Complete trades to build stats
            </div>
            {% endif %}
        </div>
    </div>
</div>
'''
