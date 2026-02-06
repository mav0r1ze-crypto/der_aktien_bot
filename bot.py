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

# Watchlist (Deine Favoriten + Big Tech)
aktien_im_blick = [
    "ALV.DE", "ENR.DE",              
    "AAPL", "MSFT", "GOOGL", "AMZN",  
    "META", "TSLA", "NVDA"            
]

def get_stock_data(ticker):
    """Holt Kursdaten, RSI und 200-Tage-Linie."""
    try:
        stock = yf.Ticker(ticker)
        # 1 Jahr Daten für SMA200 Berechnung
        hist = stock.history(period="1y")
        if len(hist) < 200: 
            hist = stock.history(period="max") # Falls Aktie neu ist
        
        if hist.empty: return None
        
        # RSI 14 Tage
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # SMA 200 & Performance
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change_pct = ((current_price / prev_price) - 1) * 100
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": current_price,
            "change": change_pct,
            "rsi": rsi,
            "above_sma200": current_price > sma200 if pd.notnull(sma200) else True,
            "currency": stock.info.get('currency', 'EUR')
        }
    except Exception as e:
        print(f"Fehler bei {ticker}: {e}")
        return None

def send_telegram_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    heute = datetime.datetime.now()
    wochentag = heute.weekday()
    
    bericht = f"🤖 *Börsen-Check {heute.strftime('%d.%m.%Y')}*\n"
    bericht += "------------------------------------------\n"
    
    depot_text = "\n💰 *DEIN DEPOT:*\n"
    blick_text = "\n👀 *AKTIEN IM BLICK:*\n"
    alarme = ""

    # 1. Depot Sektion
    for ticker in mein_depot:
        data = get_stock_data(ticker)
        if data:
            trend = "📈" if data['above_sma200'] else "📉"
            change_str = f"{data['change']:+.1f}%"
            depot_text += f"{trend} {data['name'][:10]}: {data['price']:.1f} {data['currency']} ({change_str})\n"
            
            if data['rsi'] > 75:
                alarme += f"🔥 *HEISS:* {data['name']} (RSI {data['rsi']:.0f})\n"
            elif data['rsi'] < 30:
                alarme += f"🧊 *KAUFCHANCE:* {data['name']} (RSI {data['rsi']:.0f})\n"

    # 2. Watchlist Sektion
    for ticker in aktien_im_blick:
        data = get_stock_data(ticker)
        if data:
            color = "🟢" if data['rsi'] < 35 else "🔴" if data['rsi'] > 70 else "⚪"
            change_str = f"{data['change']:+.1f}%"
            blick_text += f"{color} {data['name'][:10]}: {data['price']:.1f} | {change_str} | RSI: {data['rsi']:.0f}\n"

    # Finaler Textbau
    final_text = bericht
    if alarme:
        final_text += f"\n⚠️ *DEPOT-ALARME:*\n{alarme}"
    
    final_text += depot_text + blick_text

    # Senden (Sonntag immer, sonst Mo-Fr)
    if wochentag <= 4 or wochentag == 6:
        send_telegram_msg(final_text)

if __name__ == "__main__":
    main()
