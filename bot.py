import yfinance as yf
import os
import requests
import datetime
import pandas as pd

# 1. KONFIGURATION (Laden der GitHub Secrets oder Umgebungsvariablen)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Dein aktuelles Depot
mein_depot = {
    "5CV.DE": 14, "P911.DE": 11, "GTBIF": 55, "IFX.DE": 32,
    "MBG.DE": 21, "0QF.DE": 11, "NVD.DE": 30, "SAP.DE": 10,
    "TLRY": 11, "LIN": 10
}

# Deine Watchlist (Favoriten + Big Tech)
aktien_im_blick = [
    "ALV.DE", "ENR.DE",              # Favoriten DE
    "AAPL", "MSFT", "GOOGL", "AMZN",  # Big Tech USA
    "META", "TSLA", "NVDA"            # Big Tech USA
]

def get_stock_data(ticker):
    """Holt Preis, RSI und Trend-Daten für ein Symbol."""
    try:
        stock = yf.Ticker(ticker)
        # Wir laden 12 Monate, um den 200-Tage-Schnitt (SMA200) zu berechnen
        hist = stock.history(period="1y")
        if hist.empty:
            return None
        
        # --- RSI Berechnung (14 Tage) ---
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # --- SMA 200 (Trend-Linie) ---
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        current_price = hist['Close'].iloc[-1]
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": current_price,
            "rsi": rsi.iloc[-1],
            "sma200": sma200,
            "above_sma200": current_price > sma200 if pd.notnull(sma200) else None,
            "currency": stock.info.get('currency', 'EUR')
        }
    except Exception as e:
        print(f"Fehler bei {ticker}: {e}")
        return None

def send_telegram_msg(text):
    """Sendet die Nachricht an deinen Telegram Bot."""
    if not TOKEN or not CHAT_ID:
        print("Fehler: TOKEN oder CHAT_ID nicht gesetzt!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def main():
    heute = datetime.datetime.now()
    wochentag = heute.weekday()
    
    header = f"🤖 *Börsen-Check {heute.strftime('%d.%m.%Y')}*\n"
    header += "------------------------------------------\n"
    
    depot_text = "💰 *DEIN DEPOT:*\n"
    blick_text = "👀 *AKTIEN IM BLICK (Tech & Favoriten):*\n"
    alarme = ""

    # --- 1. DEPOT ANALYSIEREN ---
    for ticker in mein_depot:
        data = get_stock_data(ticker)
        if data:
            rsi, name = data['rsi'], data['name']
            preis = f"{data['price']:.2f} {data['currency']}"
            trend = "📈" if data['above_sma200'] else "📉"
            depot_text += f"{trend} {name[:12]}: {preis} (RSI: {rsi:.1f})\n"
            
            if rsi > 75:
                alarme += f"🔥 *HEISS:* {name} (RSI {rsi:.1f})\n"
            elif rsi < 30:
                alarme += f"🧊 *KAUFCHANCE:* {name} (RSI {rsi:.1f})\n"

    # --- 2. WATCHLIST ANALYSIEREN ---
    for ticker in aktien_im_blick:
        data = get_stock_data(ticker)
        if data:
            rsi, name = data['rsi'], data['name']
            preis = f"{data['price']:.2f} {data['currency']}"
            # Status-Emoji basierend auf RSI
            emoji = "🟢" if rsi < 35 else "🔴" if rsi > 70 else "⚪"
            blick_text += f"{emoji} *{name[:12]}*: {preis} | RSI: {rsi:.1f}\n"

    # --- 3. VERSAND ---
    finaler_bericht = header
    if alarme:
        finaler_bericht += f"\n⚠️ *DEPOT-SIGNALE:*\n{alarme}\n"
    
    finaler_bericht += f"\n{depot_text}\n{blick_text}"
    
    # Anleitung: Sonntag immer, sonst nur bei Alarmen oder Marktaktivität
    if wochentag == 6 or alarme or blick_text:
        send_telegram_msg(finaler_bericht)
    else:
        print("Keine kritischen Signale heute.")

if __name__ == "__main__":
    main()

