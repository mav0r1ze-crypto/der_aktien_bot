import yfinance as yf
import os
import requests
import datetime
import pandas as pd

# 1. KONFIGURATION
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Dein Depot
mein_depot = {
    "5CV.DE": 14, "P911.DE": 11, "GTBIF": 55, "IFX.DE": 32,
    "MBG.DE": 21, "0QF.DE": 11, "NVD.DE": 30, "SAP.DE": 10,
    "TLRY": 11, "LIN": 10
}

# EXTRA: Aktien im Blick (Allianz & Siemens Energy fest gesetzt)
aktien_im_blick = ["ALV.DE", "ENR.DE", "MSFT", "AAPL"] 

def get_stock_data(ticker):
    """Holt Preis, RSI und News für ein Symbol."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty:
            return None
        
        # RSI Berechnung
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": hist['Close'].iloc[-1],
            "rsi": rsi.iloc[-1],
            "currency": stock.info.get('currency', 'EUR'),
            "news": stock.news[:1]
        }
    except Exception as e:
        print(f"Fehler bei {ticker}: {e}")
        return None

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    heute = datetime.datetime.now()
    wochentag = heute.weekday()
    
    # --- SEKTION 1: DEPOT ANALYSE ---
    depot_bericht = ""
    alarme = ""
    for ticker in mein_depot:
        data = get_stock_data(ticker)
        if data:
            rsi, name = data['rsi'], data['name']
            preis = f"{data['price']:.2f} {data['currency']}"
            trend = "📈" if rsi > 50 else "📉"
            depot_bericht += f"{trend} {name[:12]}: {preis} (RSI: {rsi:.1f})\n"
            
            if rsi > 70:
                alarme += f"🔴 *ÜBERHITZT:* {name} ({preis})\n"
            elif rsi < 30:
                alarme += f"🟢 *KAUFCHANCE:* {name} ({preis})\n"

    # --- SEKTION 2: AKTIEN IM BLICK (Allianz, Siemens Energy etc.) ---
    blick_bericht = ""
    for ticker in aktien_im_blick:
        data = get_stock_data(ticker)
        if data:
            rsi, name = data['rsi'], data['name']
            preis = f"{data['price']:.2f} {data['currency']}"
            # Spezielle Formatierung für deine Favoriten
            status = "🔥" if rsi > 65 else "🧊" if rsi < 35 else "➡️"
            blick_bericht += f"{status} *{name}*: {preis} (RSI: {rsi:.1f})\n"

    # --- NACHRICHT ZUSAMMENBAUEN ---
    header = f"🤖 *Börsen-Update {heute.strftime('%d.%m.%Y')}*\n"
    header += "------------------------------------------\n"
    
    finaler_text = header
    
    if alarme:
        finaler_text += f"\n⚠️ *DEPOT-SIGNALE:*\n{alarme}\n"
    
    finaler_text += f"\n💰 *DEIN DEPOT:*\n{depot_bericht}"
    finaler_text += f"\n👀 *AKTIEN IM BLICK:*\n{blick_bericht}"

    # VERSAND-LOGIK: 
    # Sonntags immer, unter der Woche nur wenn Alarme existieren ODER es ein Favorit-Update gibt
    if wochentag == 6 or alarme or blick_bericht:
        send_telegram_msg(finaler_text)
    else:
        print("Keine relevanten Änderungen heute.")

if __name__ == "__main__":
    main()
