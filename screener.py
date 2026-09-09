import os
import certifi
import ssl
# Point Python / OpenSSL to certifi's CA bundle so HTTPS verification works reliably
os.environ['SSL_CERT_FILE'] = certifi.where()
# Create a reusable SSL context that uses certifi's CA file.
# Use this context with libraries that accept an SSLContext (e.g., smtplib.starttls(context=...))
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

import yfinance as yf
import pandas as pd
from google import genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import io
import time

# Import configuration
from config import (
    GEMINI_API_KEY,
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
    EMAIL_RECIPIENTS,
    EMAIL_SUBJECT,
    DROP_THRESHOLD,
    LOOKBACK_PERIOD,
    GEMINI_MODEL,
    MIN_UPSIDE_THRESHOLD,
    STOCKS_PER_GROUP,
    INDICES,
    DEBUG,
    validate_config,
    print_config
)

# Validate configuration on startup
validate_config()

if DEBUG:
    print_config()

# Setup request session with SSL verification
session = requests.Session()
session.verify = certifi.where()

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def fetch_ticker_list(url, column_name):
    """
    Fetch stock tickers from a Wikipedia table.
    
    Args:
        url: Wikipedia page URL
        column_name: Name of the column containing tickers (e.g., 'Symbol' or 'Ticker')
    
    Returns:
        List of tickers with dots replaced by dashes
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    page = session.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(page.text))
    df = tables[0]
    raw_tickers = df[column_name].tolist()
    tickers = [ticker.replace('.', '-') for ticker in raw_tickers]
    return tickers


def send_error_email(subject, error_message, dropped_stocks_summary):
    """
    Send error notification email.
    
    Args:
        subject: Email subject
        error_message: Error description
        dropped_stocks_summary: Summary of dropped stocks data
    """
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = ', '.join(EMAIL_RECIPIENTS)
    msg['Subject'] = subject
    
    error_body = f"""
    <html><body>
    <h2>{subject}</h2>
    <p>{error_message}</p>
    <p><strong>Stocks detected with >6% drop:</strong></p>
    <pre>{dropped_stocks_summary}</pre>
    <p>Please check manually or retry later.</p>
    </body></html>
    """
    msg.attach(MIMEText(error_body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(context=SSL_CONTEXT)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Error alert sent via email")
    except Exception as e:
        print(f"❌ Failed to send error email: {e}")


# --- 1. FETCH MARKET DATA ---
print("Loading market indices...")
tickers = fetch_ticker_list(INDICES["S&P 500"]["url"], INDICES["S&P 500"]["column"])
print(f"✅ {len(tickers)} S&P 500 stocks successfully loaded!")

tickers2 = fetch_ticker_list(INDICES["NASDAQ-100"]["url"], INDICES["NASDAQ-100"]["column"])
print(f"✅ {len(tickers2)} NASDAQ-100 stocks successfully loaded!")

tickers3 = fetch_ticker_list(INDICES["S&P 400"]["url"], INDICES["S&P 400"]["column"])
print(f"✅ {len(tickers3)} S&P 400 stocks successfully loaded!")

tickers4 = fetch_ticker_list(INDICES["S&P 600"]["url"], INDICES["S&P 600"]["column"])
print(f"✅ {len(tickers4)} S&P 600 stocks successfully loaded!")

print("Combining lists and removing duplicates...")
# Keep S&P membership metadata while deduplicating the analysis universe.
snp_membership = {}
for index_name, index_tickers in (
    ("S&P 500", tickers),
    ("S&P 400", tickers3),
    ("S&P 600", tickers4),
):
    for ticker in index_tickers:
        snp_membership.setdefault(ticker, []).append(index_name)

# 1. Combine the four lists.
all_tickers = tickers + tickers2 + tickers3 + tickers4
# 2. Remove duplicates while preserving the original order.
final_tickers = list(dict.fromkeys(all_tickers))
print(f"✅ {len(final_tickers)} UNIQUE stocks ready to be analyzed!")

##########################################################################################
##########################################################################################

print("DigForMe_USA is scanning U.S. markets...")

data = yf.download(final_tickers, period=LOOKBACK_PERIOD, interval="1d")
# 1. Read the last two closing prices.
close_prices = data['Close']
yesterday_close = close_prices.iloc[-2]
today_current = close_prices.iloc[-1]

# 2. Calculate the percentage change.
percent_change = ((today_current - yesterday_close) / yesterday_close) * 100

# 3. Combine price and percentage change into one table.
summary_df = pd.DataFrame({
    "Current_Price_$": today_current.round(2),
    "Drop_Percentage": percent_change
})
summary_df["S&P Membership"] = [
    ", ".join(snp_membership.get(ticker, [])) or "NASDAQ-100"
    for ticker in summary_df.index
]

# 4. Apply configurable drop filter
dropped_stocks = summary_df[
    summary_df['Drop_Percentage'] < DROP_THRESHOLD
].sort_values(by='Drop_Percentage').copy()


def fetch_mean_analyst_target(ticker):
    """Return Yahoo Finance's average analyst target for a ticker."""
    try:
        price_targets = yf.Ticker(ticker).get_analyst_price_targets()
        return price_targets.get("mean")
    except Exception as error:
        print(f"⚠️ Could not fetch analyst target for {ticker}: {error}")
        return None


dropped_stocks["Consensus_Target_$"] = [
    fetch_mean_analyst_target(ticker) for ticker in dropped_stocks.index
]
dropped_stocks["Implied_Upside_%"] = (
    (dropped_stocks["Consensus_Target_$"] - dropped_stocks["Current_Price_$"])
    / dropped_stocks["Current_Price_$"]
) * 100
dropped_stocks["Consensus_Target_$"] = dropped_stocks["Consensus_Target_$"].round(2)
dropped_stocks["Implied_Upside_%"] = dropped_stocks["Implied_Upside_%"].round(2)

############## CANCEL THE RUN IF NO STOCKS DROPPED MORE THAN THRESHOLD ##############################
if dropped_stocks.empty:
    print(f"⚠️  No stocks dropped more than {DROP_THRESHOLD}% today. Exiting.")
    exit(0)


# 5. Transforming in text for Gemini
dropped_stocks_summary = dropped_stocks.to_string()

print("\n--- DROPPED STOCKS DETECTED ---")
print(dropped_stocks_summary)

# --- 2. SEND TO GEMINI FOR ANALYSIS ---
print(f"\nSending data to {GEMINI_MODEL} for analysis...")

prompt = f"""
You are an expert equity research assistant. Below is a list of global stocks that dropped today compared to yesterday's close, along with their percentage drop:

{dropped_stocks_summary}

Your Task:
Analyze the provided stocks and categorize your top selections into two distinct groups based on the supplied analyst target upside (minimum {MIN_UPSIDE_THRESHOLD}% upside):

--- GROUP 1: Core Quality & Growth ---
- Select {STOCKS_PER_GROUP} high-market-cap, fundamental-first companies (e.g., LLY, ASML, NVDA, TSM).
- Focus on strong balance sheets, high moat, and lower long-term risk.

--- GROUP 2: High-Risk / Speculative Plays ---
- Select {STOCKS_PER_GROUP} high-volatility or growth plays (e.g., PLTR, COIN, MSTR, small/mid-cap tickers).
- Focus on high-beta rebound potential where sharp drops present tactical swing opportunities.

Format Requirements:
For each stock selected, provide:
- Ticker & Company Name, ([insert S&P Membership])
- Today's Price and Consensus Target using exactly this HTML format, replacing the example values with the actual values from the data. Do not estimate, recalculate, or alter the supplied target [...]
    Today's Price: <b><u>$266.51</u></b> (<span style="color: red; font-weight: bold;">-6.73%</span>)
    Consensus Target: <b><u>$450.00</u></b> (<span style="color: green; font-weight: bold;">+68.85%</span>)
- Write a 2–3 sentence thesis covering:
  1. The company's business model and how it makes money.
  2. The most likely reason for today's price drop. Clearly distinguish confirmed facts from possible explanations.
  3. An opportunity rating from 0/10 to 10/10, where 10/10 represents the strongest buying opportunity.
- End with: Opportunity Rating: X/10
Keep the report concise, executive, and structured with clear headers for Group 1 and Group 2.

You MUST format the entire output in raw HTML. Do not use Markdown (no ** or ##). 
- Use <h2> for Group headers (color them DarkBlue).
- Use <ul> and <li> for the stocks.
- Make the Tickers <b>bold</b>.
- Wrap the entire thesis sentence in <i>...</i>.
- Keep the exact labels "Today's Price:" and "Consensus Target:" shown in the example.
- Keep the drop percentage red and the implied upside percentage green as shown in the example.
- Use the supplied Consensus_Target_$ and Implied_Upside_% values exactly; do not use outside knowledge or invent replacement values.
- If Consensus_Target_$ or Implied_Upside_% is unavailable, write "Unavailable" instead of estimating it.
- Include the current stock price provided in the data.
- Jump one line between each stock for clarity. 

Do not wrap the response in ```html code blocks, just return the raw HTML code.
"""

# Retry temporary Gemini service failures with exponential backoff.
try:
    for attempt in range(9):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            break
        except Exception:
            if attempt == 8:
                raise
            wait_seconds = 2 ** attempt
            print(f"Gemini unavailable. Retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)
except Exception as e:
    print(f"❌ ERROR: Gemini failed after 9 retries: {e}")
    print("Sending alert email with dropped stocks data...")
    send_error_email(
        "⚠️ DigForMe_USA - ERROR: Gemini API Failed",
        f"The Gemini API failed to analyze today's dropped stocks after 9 retry attempts. Error: {e}",
        dropped_stocks_summary
    )
    exit(1)

# Validate Gemini response
if not response.text or not response.text.strip():
    print("❌ ERROR: Gemini returned empty response.")
    print("Sending alert email with dropped stocks data...")
    send_error_email(
        "⚠️ DigForMe_USA - ERROR: Gemini returned empty response",
        "The Gemini API returned an empty response.",
        dropped_stocks_summary
    )
    exit(1)

print("\n================ DigForMe DAILY AI REPORT ================\n")
print(response.text)

# --- 3. SEND THE EMAIL VIA GMAIL ---
print("\nGetting the email ready...")

# Build the email.
msg = MIMEMultipart()
msg['From'] = GMAIL_USER
msg['To'] = ', '.join(EMAIL_RECIPIENTS)
msg['Subject'] = EMAIL_SUBJECT

# Add Gemini's generated report to the email body.
msg.attach(MIMEText(response.text, 'html'))

# Connect to Gmail and send the message.
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls(context=SSL_CONTEXT)
    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✅ SUCCESS: Email was sent successfully!")
except Exception as e:
    print(f"❌ ERROR while sending the email: {e}")
