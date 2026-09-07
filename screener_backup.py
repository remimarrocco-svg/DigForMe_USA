import os
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
from google import genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl  # <--- NOUVEAU
ssl._create_default_https_context = ssl._create_unverified_context ## --- LIGNE MAGIQUE POUR REGLER LE PROBLEME SUR MAC ---
import requests
import io

# Load the hidden variables from the .env file
load_dotenv()

# Securely grab the API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FETCH MARKET DATA ---
print("Aspiration des 500 actions du S&P 500 depuis Wikipedia...")

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 1. On télécharge la page web
page_web = requests.get(url, headers=headers)

# 2. On emballe le HTML avec io.StringIO pour que Pandas le lise parfaitement
tables = pd.read_html(io.StringIO(page_web.text))

# 3. Récupérer et nettoyer les tickers
df_sp500 = tables[0]
raw_tickers = df_sp500['Symbol'].tolist()
tickers = [ticker.replace('.', '-') for ticker in raw_tickers]

print(f"✅ {len(tickers)} actions chargées avec succès !")

print("DigForMe is scanning global markets...")

data = yf.download(tickers, period="2d", interval="1d")
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

# 4. Apply 8% drop filter
dropped_stocks = summary_df[summary_df['Drop_Percentage'] < -8].sort_values(by='Drop_Percentage')

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

Do not wrap the response in ```html code blocks, just return the raw HTML code.
"""
import time
# Retry temporary Gemini service failures with exponential backoff.
for attempt in range(5):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        break
    except Exception:
        if attempt == 4:
            raise
        wait_seconds = 2 ** attempt
        print(f"Gemini unavailable. Retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)

print("\n================ DigForMe DAILY AI REPORT ================\n")
print(response.text)

# --- 4. ENVOI DE L'EMAIL VIA GMAIL ---
print("\nPréparation de l'envoi de l'email...")

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
    server.starttls()  # Sécurise la connexion
    server.login(sender_email, app_password)
    server.send_message(msg)
    server.quit()
    print("✅ SUCCÈS : L'email a été envoyé avec succès !")
except Exception as e:
    print(f"❌ ERREUR lors de l'envoi de l'email : {e}")