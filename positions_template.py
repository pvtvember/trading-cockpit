"""
Positions Page Template
=======================
Enhanced position management dashboard HTML
"""

POSITIONS_HTML = '''
<!-- ENHANCED POSITIONS TAB -->

<!-- Action Bar -->
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
    <div style="font-size:1.1em;font-weight:600">Active Positions</div>
    <button class="btn btn-primary" onclick="openModal('add-position')">➕ Add Position</button>
</div>

{% if portfolio %}
<!-- Portfolio Summary -->
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value">{{ portfolio.total_positions }}</div>
        <div class="stat-label">POSITIONS</div>
    </div>
    <div class="stat-card">
        <div class="stat-value {{ 'green' if portfolio.total_pnl > 0 else 'red' }}">${{ '{:,.0f}'.format(portfolio.total_pnl) }}</div>
        <div class="stat-label">TOTAL P&L</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{{ '{:,.0f}'.format(portfolio.total_delta) }}</div>
        <div class="stat-label">TOTAL DELTA</div>
    </div>
    <div class="stat-card">
        <div class="stat-value red">-${{ '{:,.0f}'.format(portfolio.daily_theta) }}</div>
        <div class="stat-label">DAILY THETA</div>
    </div>
</div>

{% if portfolio.correlation_warning %}
<div style="background:rgba(255,159,10,0.1);border-left:3px solid var(--accent-orange);padding:15px;border-radius:0 8px 8px 0;margin-bottom:15px">
    <div style="color:var(--accent-orange)">⚠️ CONCENTRATION RISK: Portfolio heavily weighted in one sector</div>
</div>
{% endif %}

<!-- Heat Map -->
{% if portfolio.heat_map %}
<div class="card">
    <div class="card-header">🗺️ Portfolio Heat Map</div>
    <div class="card-body">
        {% for h in portfolio.heat_map %}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;background:var(--bg-tertiary);border-radius:8px;margin-bottom:8px">
            <div>
                <span style="font-weight:700">{{ h.symbol }}</span>
                <span style="color:#888;font-size:0.85em;margin-left:8px">{{ h.direction }}</span>
            </div>
            <div style="display:flex;align-items:center;gap:15px">
                <span class="{{ 'green' if h.pnl_percent > 0 else 'red' }}" style="font-weight:600">{{ '%+.1f'|format(h.pnl_percent) }}%</span>
                <span style="padding:4px 8px;border-radius:4px;font-size:0.75em;font-weight:600;
                    {% if h.health == 'STRONG' %}background:rgba(0,200,83,0.2);color:#00c853
                    {% elif h.health == 'GOOD' %}background:rgba(0,188,212,0.2);color:#00bcd4
                    {% elif h.health == 'CAUTION' %}background:rgba(255,193,7,0.2);color:#ffc107
                    {% else %}background:rgba(255,82,82,0.2);color:#ff5252{% endif %}">{{ h.health }}</span>
                <a href="/position/{{ h.symbol }}" class="btn btn-sm btn-secondary">View</a>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}

<!-- Individual Position Cards -->
{% for pa in portfolio.positions_analysis %}
<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:16px;margin-bottom:20px;overflow:hidden">
    
    <!-- Header -->
    <div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,0,0,0.2));padding:20px;display:flex;justify-content:space-between;align-items:center">
        <div>
            <span style="font-size:1.5em;font-weight:700;color:#00d4ff">{{ pa.symbol }}</span>
            <span style="color:#888;font-size:0.9em;margin-left:10px">${{ pa.strike }} {{ pa.direction }} | {{ pa.expiration }}</span>
        </div>
        <div style="text-align:right">
            <div style="font-size:1.8em;font-weight:700" class="{{ 'green' if pa.pnl_percent > 0 else 'red' }}">{{ '%+.1f'|format(pa.pnl_percent) }}%</div>
            <div style="font-size:0.85em;color:#888">Day {{ pa.time.days_held }} of ~{{ pa.time.ai_hold_estimate }}</div>
        </div>
    </div>
    
    <!-- Overview Metrics -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">POSITION OVERVIEW</div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px">
            <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">ENTRY</div>
                <div style="font-weight:600">${{ '%.2f'|format(pa.entry_price) }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">CURRENT</div>
                <div style="font-weight:600">${{ '%.2f'|format(pa.current_price) }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">HIGH</div>
                <div style="font-weight:600">${{ '%.2f'|format(pa.high_price) }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">P&L</div>
                <div style="font-weight:600" class="{{ 'green' if pa.pnl_dollars > 0 else 'red' }}">${{ '{:,.0f}'.format(pa.pnl_dollars) }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">CONTRACTS</div>
                <div style="font-weight:600">{{ pa.contracts_remaining }}/{{ pa.contracts }}</div>
            </div>
        </div>
    </div>
    
    <!-- Profit Targets -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">🎯 PROFIT TARGETS</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
            <div style="background:{% if pa.targets.target_1.hit %}rgba(0,200,83,0.15);border:1px solid rgba(0,200,83,0.3){% else %}rgba(0,0,0,0.2){% endif %};padding:12px;border-radius:8px">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:0.75em;color:#888">TARGET 1</span>
                    <span style="font-weight:600;color:#00c853">+{{ pa.targets.target_1.pct|int }}%</span>
                </div>
                <div style="font-size:1.1em;font-weight:700">${{ '%.2f'|format(pa.targets.target_1.price) }}</div>
                <div style="font-size:0.75em;color:#00d4ff;margin-top:4px">Sell {{ pa.targets.target_1.contracts }} contracts</div>
            </div>
            <div style="background:{% if pa.targets.target_2.hit %}rgba(0,200,83,0.15);border:1px solid rgba(0,200,83,0.3){% else %}rgba(0,0,0,0.2){% endif %};padding:12px;border-radius:8px">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:0.75em;color:#888">TARGET 2</span>
                    <span style="font-weight:600;color:#00c853">+{{ pa.targets.target_2.pct|int }}%</span>
                </div>
                <div style="font-size:1.1em;font-weight:700">${{ '%.2f'|format(pa.targets.target_2.price) }}</div>
                <div style="font-size:0.75em;color:#00d4ff;margin-top:4px">Sell {{ pa.targets.target_2.contracts }} contracts</div>
            </div>
            <div style="background:{% if pa.targets.target_3.hit %}rgba(0,200,83,0.15);border:1px solid rgba(0,200,83,0.3){% else %}rgba(0,0,0,0.2){% endif %};padding:12px;border-radius:8px">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:0.75em;color:#888">RUNNER</span>
                    <span style="font-weight:600;color:#00c853">+{{ pa.targets.target_3.pct|int }}%</span>
                </div>
                <div style="font-size:1.1em;font-weight:700">${{ '%.2f'|format(pa.targets.target_3.price) }}</div>
                <div style="font-size:0.75em;color:#00d4ff;margin-top:4px">Hold {{ pa.targets.target_3.contracts }} contracts</div>
            </div>
        </div>
    </div>
    
    <!-- Stop Management -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">🛡️ STOP MANAGEMENT</div>
        <div style="background:linear-gradient(135deg,rgba(255,82,82,0.1),rgba(0,0,0,0.2));border:1px solid rgba(255,82,82,0.2);border-radius:10px;padding:15px">
            <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:0.9em">
                <span style="color:#888">Initial Stop</span>
                <span style="font-weight:600">${{ '%.2f'|format(pa.stops.initial_stop) }} ({{ pa.stops.initial_stop_pct|int }}%)</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:0.9em">
                <span style="color:#888">Breakeven</span>
                <span style="font-weight:600">${{ '%.2f'|format(pa.stops.breakeven_price) }} {% if pa.stops.breakeven_triggered %}✓{% endif %}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:0.9em">
                <span style="color:#888">Current Stop</span>
                <span style="font-weight:600;color:#ff5252">${{ '%.2f'|format(pa.stops.current_stop) }} ({{ '%+.0f'|format(pa.stops.current_stop_pct) }}%)</span>
            </div>
            {% if pa.pnl_percent > 30 %}
            <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:0.9em">
                <span style="color:#888">Trailing Stop (15%)</span>
                <span style="font-weight:600">${{ '%.2f'|format(pa.stops.trailing_stop) }}</span>
            </div>
            {% endif %}
            <div style="background:rgba(255,193,7,0.1);padding:10px;border-radius:8px;margin-top:10px;font-size:0.85em;color:#ffc107">
                💡 {{ pa.stops.stop_recommendation }}
            </div>
        </div>
    </div>
    
    <!-- Trade Health -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">📊 TRADE HEALTH</div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:15px">
            <div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                    <span style="color:#888;font-size:0.85em">Momentum</span>
                    <div style="display:flex;align-items:center;gap:8px">
                        <div style="width:80px;height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden">
                            <div style="width:{{ pa.health.momentum_score }}%;height:100%;background:{% if pa.health.momentum_score >= 70 %}#00c853{% elif pa.health.momentum_score >= 50 %}#00bcd4{% else %}#ff9800{% endif %};border-radius:4px"></div>
                        </div>
                        <span style="font-weight:600;font-size:0.85em">{{ pa.health.momentum_label }}</span>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                    <span style="color:#888;font-size:0.85em">Trend</span>
                    <div style="display:flex;align-items:center;gap:8px">
                        <div style="width:80px;height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden">
                            <div style="width:{{ pa.health.trend_score }}%;height:100%;background:{% if pa.health.trend_score >= 70 %}#00c853{% elif pa.health.trend_score >= 50 %}#00bcd4{% else %}#ff9800{% endif %};border-radius:4px"></div>
                        </div>
                        <span style="font-weight:600;font-size:0.85em">{{ pa.health.trend_label }}</span>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0">
                    <span style="color:#888;font-size:0.85em">RS vs SPY</span>
                    <span style="font-weight:600;font-size:0.85em" class="{{ 'green' if pa.health.rs_vs_spy > 0 else 'red' }}">{{ '%+.1f'|format(pa.health.rs_vs_spy) }}%</span>
                </div>
            </div>
            <div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                    <span style="color:#888;font-size:0.85em">Setup Valid</span>
                    <span style="font-weight:600;font-size:0.85em" class="{{ 'green' if pa.health.setup_still_valid else 'red' }}">{{ '✓ YES' if pa.health.setup_still_valid else '✗ NO' }}</span>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                    <span style="color:#888;font-size:0.85em">IV Regime</span>
                    <span style="font-weight:600;font-size:0.85em">{{ pa.health.iv_regime }}</span>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0">
                    <span style="color:#888;font-size:0.85em">Overall Health</span>
                    <span style="font-weight:600;font-size:0.85em;padding:2px 8px;border-radius:4px;
                        {% if pa.health.health_label == 'STRONG' %}background:rgba(0,200,83,0.2);color:#00c853
                        {% elif pa.health.health_label == 'GOOD' %}background:rgba(0,188,212,0.2);color:#00bcd4
                        {% elif pa.health.health_label == 'CAUTION' %}background:rgba(255,193,7,0.2);color:#ffc107
                        {% else %}background:rgba(255,82,82,0.2);color:#ff5252{% endif %}">{{ pa.health.health_label }}</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Greeks -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">📈 GREEKS & TIME</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
            <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">DELTA</div>
                <div style="font-size:1.1em;font-weight:600;margin-top:4px">{{ '%.2f'|format(pa.greeks.delta) }}</div>
                <div style="font-size:0.75em;margin-top:2px" class="{{ 'green' if pa.greeks.delta_change > 0 else 'red' }}">{{ '%+.2f'|format(pa.greeks.delta_change) }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">THETA/DAY</div>
                <div style="font-size:1.1em;font-weight:600;margin-top:4px;color:#ff5252">-${{ '%.0f'|format(pa.greeks.theta_daily_cost) }}</div>
                <div style="font-size:0.75em;margin-top:2px;color:#888">{{ '%.1f'|format(pa.greeks.theta_burn_pct) }}% burned</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">DTE</div>
                <div style="font-size:1.1em;font-weight:600;margin-top:4px">{{ pa.time.dte }}</div>
                <div style="font-size:0.75em;margin-top:2px;
                    {% if pa.time.theta_zone == 'SAFE' %}color:#00c853{% elif pa.time.theta_zone == 'CAUTION' %}color:#ffc107{% else %}color:#ff5252{% endif %}">{{ pa.time.theta_zone }}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center">
                <div style="font-size:0.7em;color:#888">EST. HOLD</div>
                <div style="font-size:1.1em;font-weight:600;margin-top:4px">~{{ pa.time.days_remaining }}d left</div>
                <div style="font-size:0.75em;margin-top:2px;color:#888">of {{ pa.time.ai_hold_estimate }}d</div>
            </div>
        </div>
    </div>
    
    <!-- Warnings -->
    {% if pa.warnings %}
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">⚠️ RISK SIGNALS</div>
        <div style="background:rgba(255,193,7,0.1);border-left:4px solid #ffc107;padding:15px;border-radius:0 8px 8px 0">
            {% for w in pa.warnings %}
            <div style="padding:6px 0;font-size:0.9em;color:#ffc107">{{ w }}</div>
            {% endfor %}
        </div>
    </div>
    {% endif %}
    
    <!-- AI Recommendation -->
    <div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="font-size:0.8em;color:#888;margin-bottom:10px;font-weight:600">🤖 AI ADVISOR</div>
        <div style="background:linear-gradient(135deg,rgba(123,44,191,0.15),rgba(123,44,191,0.05));border:1px solid rgba(123,44,191,0.3);border-radius:12px;padding:20px">
            <div style="font-size:1.2em;font-weight:700;margin-bottom:10px;
                {% if pa.recommendation == 'HOLD' %}color:#00d4ff
                {% elif pa.recommendation == 'TAKE_PARTIAL' %}color:#00c853
                {% elif pa.recommendation == 'MOVE_STOP' %}color:#ffc107
                {% else %}color:#ff5252{% endif %}">{{ pa.recommendation.replace('_', ' ') }}</div>
            <div style="font-size:0.95em;margin-bottom:12px;line-height:1.5">{{ pa.recommendation_reason }}</div>
            <div style="background:var(--bg-tertiary);padding:12px;border-radius:8px;font-size:0.9em">
                <strong>Next Action:</strong> {{ pa.next_action }}
            </div>
        </div>
    </div>
    
    <!-- Actions -->
    <div style="padding:15px">
        <div style="display:flex;gap:10px;flex-wrap:wrap">
            {% if pa.pnl_percent >= 25 and not pa.stops.breakeven_triggered %}
            <a href="/action/{{ pa.symbol }}/move-to-be" class="btn btn-warning btn-sm">Move to Breakeven</a>
            {% endif %}
            {% if pa.targets.target_1.hit and pa.contracts_remaining == pa.contracts %}
            <a href="/action/{{ pa.symbol }}/take-partial" class="btn btn-success btn-sm">Take 1/3 Profit</a>
            {% endif %}
            <a href="/close/{{ pa.symbol }}" class="btn btn-danger btn-sm">Close Position</a>
            <a href="/position/{{ pa.symbol }}" class="btn btn-secondary btn-sm">Full Analysis</a>
        </div>
    </div>
    
</div>
{% endfor %}

{% else %}
<div class="empty-state">
    <div class="empty-state-icon">📊</div>
    <h3 style="font-weight:600;margin-bottom:12px">No Open Positions</h3>
    <p style="margin:15px 0;color:var(--text-tertiary)">Add a position manually or find setups in the Scanner</p>
    <div style="display:flex;gap:12px;justify-content:center;margin-top:20px">
        <button class="btn btn-primary" onclick="openModal('add-position')">➕ Add Position</button>
        <a href="/scanner" class="btn btn-secondary">🔍 Go to Scanner</a>
    </div>
</div>
{% endif %}

<!-- Manual Position Entry Modal -->
<div class="modal" id="add-position">
    <div class="modal-content" style="max-width:480px">
        <div class="modal-header">
            <span>Add Position Manually</span>
            <button class="modal-close" onclick="closeModal('add-position')">&times;</button>
        </div>
        <div class="modal-body">
            <form action="/add-position" method="POST">
                <div class="form-group">
                    <label>Symbol *</label>
                    <input type="text" name="symbol" placeholder="AAPL" required style="text-transform:uppercase">
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                    <div class="form-group">
                        <label>Direction *</label>
                        <select name="direction" required>
                            <option value="CALL">CALL</option>
                            <option value="PUT">PUT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Contracts *</label>
                        <input type="number" name="contracts" value="1" min="1" required>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                    <div class="form-group">
                        <label>Strike Price *</label>
                        <input type="number" name="strike" step="0.5" placeholder="150" required>
                    </div>
                    <div class="form-group">
                        <label>Expiration *</label>
                        <input type="date" name="expiration" required>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                    <div class="form-group">
                        <label>Entry Price (per contract) *</label>
                        <input type="number" name="entry_price" step="0.01" placeholder="3.50" required>
                    </div>
                    <div class="form-group">
                        <label>Underlying Price</label>
                        <input type="number" name="entry_underlying" step="0.01" placeholder="152.50">
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                    <div class="form-group">
                        <label>Delta (optional)</label>
                        <input type="number" name="entry_delta" step="0.01" placeholder="0.50" min="0" max="1">
                    </div>
                    <div class="form-group">
                        <label>Setup Type</label>
                        <select name="setup_type">
                            <option value="DISCRETIONARY">Discretionary</option>
                            <option value="SQUEEZE">Squeeze</option>
                            <option value="BREAKOUT">Breakout</option>
                            <option value="CONTINUATION">Continuation</option>
                            <option value="REVERSAL">Reversal</option>
                            <option value="BASE_BREAKOUT">Base Breakout</option>
                            <option value="MOMENTUM">Momentum</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Notes (optional)</label>
                    <input type="text" name="notes" placeholder="Why did you enter this trade?">
                </div>
                
                <div style="display:flex;gap:12px;margin-top:20px">
                    <button type="submit" class="btn btn-success" style="flex:1">Add Position</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal('add-position')">Cancel</button>
                </div>
            </form>
        </div>
    </div>
</div>
'''
