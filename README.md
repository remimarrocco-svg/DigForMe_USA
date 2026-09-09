# DigForMe_USA 📈

Automated daily screener tracking >6% drops across ~1,500 US equities (S&P 500, 400, 600 & Nasdaq-100). Uses Google Gemini AI to evaluate fundamentals, analyst price targets, and news, automatically delivering executive HTML email reports.

The goal is to detect undervalued stocks trading >15% below analyst price targets, identifying high-probability bounce-back candidates following sharp daily drops

## Features

- **Daily Market Scan**: Tracks 1,500+ US equities across major indices
- **AI-Powered Analysis**: Uses Google Gemini to analyze dropped stocks with customizable models
- **Smart Categorization**: Separates picks into "Core Quality & Growth" vs. "High-Risk/Speculative"
- **Email Delivery**: Sends formatted HTML reports directly to your inbox
- **Error Handling**: Graceful failures with email alerts
- **Fully Configurable**: Adjust thresholds, recipients, and AI parameters without touching code

## Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Gmail account with App Password (for sending emails)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/remimarrocco-svg/DigForMe_USA.git
   cd DigForMe_USA
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your `.env` file from the template:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your credentials:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GMAIL_USER=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=your_app_specific_password
   EMAIL_RECIPIENTS=your_email@gmail.com
   ```

5. Run the screener:
   ```bash
   python screener.py
   ```

## Configuration

All settings are managed via `.env` file. See `.env.example` for all available options.

### Required Settings
- `GEMINI_API_KEY` - Your Google Gemini API key
- `GMAIL_USER` - Your Gmail address
- `GMAIL_APP_PASSWORD` - Gmail app-specific password (not your main password)
- `EMAIL_RECIPIENTS` - Email address(es) to receive reports (comma-separated)

### Optional Settings
- `DROP_THRESHOLD` - Minimum stock drop % to include (default: `-6.0`)
- `GEMINI_MODEL` - AI model to use (default: `gemini-3.5-flash-lite`)
- `MIN_UPSIDE_THRESHOLD` - Minimum analyst target upside % (default: `15.0`)
- `STOCKS_PER_GROUP` - Stocks analyzed per category (default: `4`)
- `LOOKBACK_PERIOD` - Historical data window (default: `2d`)
- `DEBUG` - Enable verbose logging (default: `False`)

## How It Works

1. **Fetch Market Data**: Downloads 2-day price history for 1,500+ equities
2. **Filter Drops**: Identifies stocks with drops exceeding `DROP_THRESHOLD`
3. **Fetch Analyst Targets**: Retrieves consensus price targets from Yahoo Finance
4. **AI Analysis**: Sends filtered data to Gemini for in-depth thesis generation
5. **Send Report**: Delivers formatted HTML email with actionable insights

## Output Example

The daily report includes:
- **Group 1: Core Quality & Growth** – Lower-risk, high-quality companies with upside potential
- **Group 2: High-Risk/Speculative** – Volatile plays with outsized rebound potential
- For each stock: ticker, current price, consensus target, implied upside, and investment thesis

## Scheduling

### GitHub Actions (Automated ✅)

This repository includes a GitHub Actions workflow that runs daily at **7:00 AM PDT** (weekdays only).

**To set up:**

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `GEMINI_API_KEY`
   - `GMAIL_USER`
   - `GMAIL_APP_PASSWORD`
   - `EMAIL_RECIPIENTS`

3. (Optional) Customize the workflow in `.github/workflows/daily-run.yml`

**Manual Trigger:** Go to **Actions** tab → **DigForMe Daily Screener** → **Run workflow**

### Local Machine (Manual)

Run anytime with:
```bash
python screener.py
```

### Cron (Linux/Mac)

Add to crontab (`crontab -e`):
```bash
# Run every weekday at 7:00 AM
0 7 * * 1-5 cd /path/to/DigForMe_USA && python screener.py
```

## Security Notes

- **Never commit `.env`** – API keys and passwords stay local only
- **Use App Passwords for Gmail** – Enable 2FA, then generate an app-specific password
- **Gemini API costs** – Monitor usage to avoid unexpected charges
- `.env` is protected by `.gitignore` automatically

## Project Structure

```
DigForMe_USA/
├── screener.py           # Main script
├── config.py             # Configuration loader
├── .env.example          # Configuration template (commit this)
├── .env                  # Your credentials (never commit!)
├── .gitignore            # Prevents accidental credential commits
├── requirements.txt      # Python dependencies
├── .github/
│   └── workflows/
│       └── daily-run.yml # GitHub Actions automation
└── README.md            # This file
```

## Limitations & Known Issues

- Analyst targets may be unavailable for small-cap stocks; these display as "Unavailable"
- Wikipedia list parsing is fragile; consider switching to a more reliable source (e.g., SEC EDGAR API)
- No position sizing or risk management guidance provided (educational use only)
- Email delivery requires stable internet connection

## Contributing

Contributions welcome! Possible improvements:
- Support for international markets
- Real-time data ingestion instead of end-of-day
- Multi-asset class screening (crypto, commodities, etc.)
- Database logging of historical reports
- Slack/Discord notifications alternative to email
- Performance optimization for large ticker universes

## Troubleshooting

**"GEMINI_API_KEY not found"**
- Ensure `.env` file exists and contains `GEMINI_API_KEY=...`

**"No stocks dropped more than X% today"**
- This is normal on calm market days; script exits gracefully
- Adjust `DROP_THRESHOLD` in `.env` if needed

**Email not sending**
- Verify Gmail 2FA is enabled
- Generate a new app-specific password
- Check `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env`

**GitHub Actions not running**
- Check repository **Actions** tab for workflow status
- Verify secrets are set in **Settings** → **Secrets and variables** → **Actions**
- Check workflow run logs for error details


## Author

Created by [Rémi Marrocco, PhD](https://github.com/remimarrocco-svg)

---

**Disclaimer**: This tool is for educational and informational purposes only. Not financial advice. Always conduct your own due diligence before investing.
