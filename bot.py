import yfinance as yf
import os
import requests
from datetime import datetime

# Daten aus den GitHub Secrets laden
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

mein_depot = {
    "5CV.DE": 14, "P911.DE": 11, "GTBIF": 55, "IFX.DE": 32,
    "MBG.DE": 21, "0QF.DE": 11, "NVD.DE": 30, "SAP.DE": 10,
    "TLRY": 11, "LIN": 10
}

def get_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty: return None
        
        # RSI Berechnung
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": hist['Close'].iloc[-1],
            "rsi": rsi.iloc[-1],
            "news": stock.news[:1] # Hol die aktuellste News
        }
    except: return None

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    bericht = f"🤖 *Depot-Check {datetime.now().strftime('%d.%m.%Y')}*\n\n"
    alarme = ""
    
    for ticker in mein_depot:
        d = get_data(ticker)
        if d:
            if d['rsi'] > 70:
                alarme += f"🔴 *VERKAUF:* {d['name']}\n(RSI: {d['rsi']:.1f} | Preis: {d['price']:.2f})\n"
                if d['news']: alarme += f"📰 News: [{d['news'][0]['title']}]({d['news'][0]['link']})\n\n"
            elif d['rsi'] < 30:
                alarme += f"🟢 *KAUF:* {d['name']}\n(RSI: {d['rsi']:.1f} | Preis: {d['price']:.2f})\n\n"

    if not alarme:
        bericht += "✅ Alles im grünen Bereich. Keine akuten RSI-Signale."
    else:
        bericht += "⚠️ *Handlungsbedarf:*\n\n" + alarme

    send_msg(bericht)

if __name__ == "__main__":
    main()
