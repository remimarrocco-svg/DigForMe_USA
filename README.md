# DigForMe_USA 📈

Automated daily screener tracking >6% drops across ~1,500 US equities (S&P 500, 400, 600 & Nasdaq-100). Uses Google Gemini AI to evaluate fundamentals, analyst price targets, and news, automatically delivering executive HTML email reports.

## Features

- **Daily Market Scan**: Tracks 1,500+ US equities across major indices
- **AI-Powered Analysis**: Uses Google Gemini 3.5 Flash Lite to analyze dropped stocks
- **Smart Categorization**: Separates picks into "Core Quality & Growth" vs. "High-Risk/Speculative"
- **Email Delivery**: Sends formatted HTML reports directly to your inbox
- **Error Handling**: Graceful failures with email alerts

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
