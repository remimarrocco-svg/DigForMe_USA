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
from dotenv import load_dotenv
from google import genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import io
session = requests.Session()
session.verify = certifi.where()

# Load the hidden variables from the .env file
load_dotenv()

# Securely grab the API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FETCH MARKET DATA ---
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


# --- 2. FETCH MARKET DATA ---
tickers = fetch_ticker_list('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 'Symbol')
print(f"✅ {len(tickers)} S&P500 stocks succesfuly loaded!")

tickers2 = fetch_ticker_list('https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies', 'Ticker')
print(f"✅ {len(tickers2)} NASDAQ-100 stocks succesfuly loaded!")

tickers3 = fetch_ticker_list('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies', 'Symbol')
print(f"✅ {len(tickers3)} S&P400 stocks succesfuly loaded!")

tickers4 = fetch_ticker_list('https://en.wikipedia.org/wiki/List_of_S%26P_600_companies', 'Symbol')
print(f"✅ {len(tickers4)} S&P600 stocks succesfuly loaded!")
##########################################################################################

print("Lists' fusion for duplicate deletion...")
# 1. On additionne les 4 listes
all_tickers = tickers + tickers2 + tickers3 + tickers4
# 2. On transforme en 'set' pour tuer les doublons, puis on repasse en liste
final_tickers = list(set(all_tickers))
print(f"✅ {len(final_tickers)} UNIQUES stocks ready to be analyzed!")

##########################################################################################
##########################################################################################


print("DigForMe is scanning global markets...")

data = yf.download(final_tickers, period="2d", interval="1d")
# 1. On récupère les données avec la sécurité de lire par la fin
close_prices = data['Close']
yesterday_close = close_prices.iloc[-2]
today_current = close_prices.iloc[-1]

# 2. On calcule le pourcentage
percent_change = ((today_current - yesterday_close) / yesterday_close) * 100

# 3. On fusionne le prix et le pourcentage dans un seul tableau
summary_df = pd.DataFrame({
    "Current_Price_$": today_current.round(2),
    "Drop_Percentage": percent_change
})

# 4. Apply 6% drop filter
dropped_stocks = summary_df[summary_df['Drop_Percentage'] < -6].sort_values(by='Drop_Percentage')

# 5. On transforme en texte pour Gemini
dropped_stocks_summary = dropped_stocks.to_string()

print("\n--- DROPPED STOCKS DETECTED ---")
print(dropped_stocks_summary)

# --- 3. SEND TO GEMINI FOR ANALYSIS ---
print("\nSending data to Gemini Pro for analysis...")

prompt = f"""
You are an expert equity research assistant. Below is a list of global stocks that dropped today compared to yesterday's close, along with their percentage drop:

{dropped_stocks_summary}

Your Task:
Analyze the provided stocks and categorize your top selections into two distinct groups based on potential price target upside (minimum 15% upside to consensus mean target):

--- GROUP 1: Core Quality & Growth ---
- Select 4 high-market-cap, fundamental-first companies (e.g., LLY, ASML, NVDA, TSM).
- Focus on strong balance sheets, high moat, and lower long-term risk.

--- GROUP 2: High-Risk / Speculative Plays ---
- Select 4 high-volatility or growth plays (e.g., PLTR, COIN, MSTR, small/mid-cap tickers).
- Focus on high-beta rebound potential where sharp drops present tactical swing opportunities.

Format Requirements:
For each stock selected, provide:
- Ticker & Company Name
- Today's value and Drop %
- Estimated Consensus Target & Implied Upside %
- 1-Sentence Thesis (Why this drop represents an opportunity)

Keep the report concise, executive, and structured with clear headers for Group 1 and Group 2.

You MUST format the entire output in raw HTML. Do not use Markdown (no ** or ##). 
- Use <h2> for Group headers (color them DarkBlue).
- Use <ul> and <li> for the stocks.
- Make the Tickers <b>bold</b>.
- Color the "Today's Drop" percentage in <span style="color: red; font-weight: bold;">red</span>.
- Color the "Implied Upside" percentage in <span style="color: green; font-weight: bold;">green</span>.
- Include the current stock price provided in the data.
- Jump one line between each stock for clarity. 

Do not wrap the response in ```html code blocks, just return the raw HTML code.
"""
import time
# Retry temporary Gemini service failures with exponential backoff.
for attempt in range(10):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        break
    except Exception:
        if attempt == 9:
            raise
        wait_seconds = 2 ** attempt
        print(f"Gemini unavailable. Retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)

print("\n================ DigForMe DAILY AI REPORT ================\n")
print(response.text)

# --- 4. ENVOI DE L'EMAIL VIA GMAIL ---
print("\nGetting the email ready...")

sender_email = os.environ.get("GMAIL_USER")
app_password = os.environ.get("GMAIL_APP_PASSWORD")
receiver_email = sender_email  # Le rapport s'envoie à vous-même

# Structuration de l'email
msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = "DigForMe - Daily AI Stock Report 📈"

# Ajout du texte généré par Gemini dans le corps du mail
msg.attach(MIMEText(response.text, 'html'))

# Connexion aux serveurs de Google et envoi
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls(context=SSL_CONTEXT) # Sécurise la connexion
    server.login(sender_email, app_password)
    server.send_message(msg)
    server.quit()
    print("✅ SUCCESS : The email has been sent successfully!")
except Exception as e:
    print(f"❌ ERROR while sending the email : {e}")