import yfinance as yf
import os
import requests
import datetime
import pandas as pd

# 1. KONFIGURATION
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

mein_depot = {
    "5CV.DE": 14, "P911.DE": 11, "GTBIF": 55, "IFX.DE": 32,
    "MBG.DE": 21, "0QF.DE": 11, "NVD.DE": 30, "SAP.DE": 10,
    "TLRY": 11, "LIN": 10
}

aktien_im_blick = [
    "ALV.DE", "ENR.DE",              
    "AAPL", "MSFT", "GOOGL", "AMZN",  
    "META", "TSLA", "NVDA"            
]

# 2. IPO WATCHLIST 2026 (News-Status)
ipo_kandidaten = {
    "OpenAI": "Bewertung ~$500Mrd. | IPO-Gerüchte für Q4 2026 verdichten sich.",
    "Anthropic": "Valuation ~$350Mrd. | Claude-Hype treibt Vorbereitungen für 2026.",
    "SpaceX": "Ziel >$1Bio. | Musk deutet Juni 2026 an (eventuell Starlink Spin-off).",
    "Canva": "Profitabel & ~$42Mrd. wert. | IPO im Frühjahr/Sommer 2026 wahrscheinlich.",
    "Strava": "Vertrauliche IPO-Anmeldung bereits im Jan 2026 erfolgt.",
    "Databricks": "Bewertung ~$134Mrd. | Stärkster Software-Kandidat für H2 2026."
}

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        # RSI 14
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # SMA 200 & Tagesänderung
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change_pct = ((current_price / prev_price) - 1) * 100
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": current_price,
            "change": change_pct,
            "rsi": rsi.iloc[-1],
            "above_sma200": current_price > sma200 if pd.notnull(sma200) else None,
            "currency": stock.info.get('currency', 'EUR')
        }
    except Exception: return None

def send_telegram_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def main():
    heute = datetime.datetime.now()
    wochentag = heute.weekday()
    
    final_text = f"🤖 *Börsen-Check {heute.strftime('%d.%m.%Y')}*\n"
    final_text += "------------------------------------------\n"
    
    # Sektion: Depot
    final_text += "\n💰 *DEIN DEPOT:*\n"
    for ticker in mein_depot:
        data = get_stock_data(ticker)
        if data:
            trend = "📈" if data['above_sma200'] else "📉"
            change_str = f"{data['change']:+.1f}%"
            final_text += f"{trend} {data['name'][:10]}: {data['price']:.1f} {data['currency']} ({change_str})\n"

    # Sektion: Watchlist
    final_text += "\n👀 *AKTIEN IM BLICK:*\n"
    for ticker in aktien_im_blick:
        data = get_stock_data(ticker)
        if data:
            color = "🟢" if data['rsi'] < 35 else "🔴" if data['rsi'] > 70 else "⚪"
            final_text += f"{color} {data['name'][:10]}: {data['price']:.1f} | RSI: {data['rsi']:.0f}\n"

    # Sektion: IPO News 2026
    final_text += "\n🚀 *IPO-WATCH 2026:*\n"
    for name, status in ipo_kandidaten.items():
        final_text += f"• *{name}*: {status}\n"

    # Versand-Logik (Sonntags immer, sonst bei News/Handel)
    if wochentag == 6 or True: # True zum Testen, später wieder auf Alarme einschränken
        send_telegram_msg(final_text)

if __name__ == "__main__":
    main()
