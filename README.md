# Trading Cockpit v2

AI-powered options trading dashboard with Claude Opus 4.5 advisor.

## Features
- 🤖 AI Trading Advisor (Claude Opus 4.5)
- 🔥 Smart Scanner & Hot List
- 📈 Position Management
- 🌍 Market Regime Analysis
- ⚠️ Portfolio Risk Dashboard
- 📝 Trade Journal

## Deploy to Railway

1. Fork this repo
2. Connect Railway to GitHub
3. Add environment variables:
   - `POLYGON_API_KEY` - Your Polygon.io API key
   - `ANTHROPIC_API_KEY` - Your Anthropic API key
   - `CLAUDE_MODEL` - `claude-opus-4-20250514`
   - `TOTAL_CAPITAL` - Your trading capital

## Local Development

```bash
pip install -r requirements.txt
python cockpit.py
```

Open http://localhost:5000
