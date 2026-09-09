"""
Configuration management for DigForMe_USA screener.
Loads settings from .env file with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# API & AUTHENTICATION
# ============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

if not GMAIL_USER or not GMAIL_APP_PASSWORD:
    raise ValueError("❌ GMAIL_USER or GMAIL_APP_PASSWORD not found in .env file")

# ============================================================================
# SCREENING PARAMETERS
# ============================================================================
# Minimum drop percentage to trigger analysis (e.g., -6.0 for 6% drop)
DROP_THRESHOLD = float(os.environ.get("DROP_THRESHOLD", "-6.0"))

# Number of days to fetch historical data
LOOKBACK_PERIOD = os.environ.get("LOOKBACK_PERIOD", "2d")

# ============================================================================
# GEMINI AI CONFIGURATION
# ============================================================================
# Model to use for analysis
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Minimum analyst target upside threshold for inclusion (percentage)
MIN_UPSIDE_THRESHOLD = float(os.environ.get("MIN_UPSIDE_THRESHOLD", "15.0"))

# Number of stocks per category (Group 1 & 2)
STOCKS_PER_GROUP = int(os.environ.get("STOCKS_PER_GROUP", "4"))

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
# Recipient email addresses (comma-separated for multiple recipients)
EMAIL_RECIPIENTS = [
    email.strip() 
    for email in os.environ.get("EMAIL_RECIPIENTS", "").split(",") 
    if email.strip()
]

# If no recipients specified, default to sender
if not EMAIL_RECIPIENTS:
    EMAIL_RECIPIENTS = [GMAIL_USER]

EMAIL_SUBJECT = os.environ.get(
    "EMAIL_SUBJECT", 
    "DigForMe_USA - Daily AI Stock Report 📈"
)

# ============================================================================
# MARKET INDICES TO TRACK
# ============================================================================
INDICES = {
    "S&P 500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "column": "Symbol"
    },
    "NASDAQ-100": {
        "url": "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
        "column": "Ticker"
    },
    "S&P 400": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "column": "Symbol"
    },
    "S&P 600": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        "column": "Symbol"
    }
}

# ============================================================================
# LOGGING & DEBUGGING
# ============================================================================
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
VERBOSE = os.environ.get("VERBOSE", "False").lower() == "true"


def validate_config():
    """Validate that all required configuration is present."""
    required = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    }
    
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"❌ Missing required config: {', '.join(missing)}")
    
    if not EMAIL_RECIPIENTS:
        raise ValueError("❌ EMAIL_RECIPIENTS is empty. Set EMAIL_RECIPIENTS in .env")
    
    if DROP_THRESHOLD >= 0:
        raise ValueError("❌ DROP_THRESHOLD must be negative (e.g., -6.0)")


def print_config():
    """Print active configuration (for debugging)."""
    print("\n" + "="*70)
    print("DigForMe_USA Configuration")
    print("="*70)
    print(f"Gemini Model:        {GEMINI_MODEL}")
    print(f"Drop Threshold:      {DROP_THRESHOLD}%")
    print(f"Min Upside:          {MIN_UPSIDE_THRESHOLD}%")
    print(f"Stocks per Group:    {STOCKS_PER_GROUP}")
    print(f"Email Recipients:    {', '.join(EMAIL_RECIPIENTS)}")
    print(f"Debug Mode:          {DEBUG}")
    print("="*70 + "\n")


if __name__ == "__main__":
    validate_config()
    print_config()
