# Trading Cockpit Update Instructions
## Adding PostgreSQL + Expert AI Advisor

This update adds two things to your existing trading-cockpit:
1. **PostgreSQL database** - your data persists forever on Railway
2. **Expert AI Advisor** - speaks like a senior trading mentor

---

## Files to ADD (new files):

### `db.py` 
Copy this file to your trading-cockpit folder. It provides database functions.

---

## Files to REPLACE:

### `requirements.txt`
Replace with the new version (adds psycopg2-binary for PostgreSQL)

### `ai_advisor.py`
Replace with the new version (expert mentor voice instead of robot voice)

---

## Files to KEEP (don't change):
- cockpit.py
- market_regime.py
- portfolio_risk.py
- pro_manager.py
- scanner.py
- smart_analyzer.py
- trade_journal.py
- Procfile
- .env
- .gitignore

---

## After copying files:

### 1. Push to GitHub
In GitHub Desktop:
- You'll see changes (new db.py, updated requirements.txt, updated ai_advisor.py)
- Summary: "Add PostgreSQL + Expert AI"
- Click "Commit to main"
- Click "Push origin"

### 2. Add PostgreSQL in Railway
1. Go to Railway dashboard
2. Click your project
3. Click "+ New"
4. Select "Database" → "PostgreSQL"
5. Wait 30 seconds
6. Done! Railway auto-connects it

### 3. Your data now persists forever!
- Positions saved to database
- Journal saved to database  
- Watchlist saved to database
- Redeploys don't lose data

---

## How to use database in your code (optional advanced):

If you want to make other data persistent, use the PersistentDict class:

```python
from db import PersistentDict, PersistentList

# Instead of: my_data = {}
my_data = PersistentDict('my_data')

# Works exactly the same:
my_data['key'] = 'value'  # Auto-saves to database
del my_data['key']         # Auto-saves
```

---

## Testing locally:
- Locally it uses JSON files in /data folder
- On Railway it uses PostgreSQL
- Same code works both places!
