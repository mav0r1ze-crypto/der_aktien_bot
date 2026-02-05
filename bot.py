import yfinance as yf
import os
import requests
import datetime
import pandas as pd

# 1. KONFIGURATION (Laden der GitHub Secrets)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Dein Depot
mein_depot = {
    "5CV.DE": 14, "P911.DE": 11, "GTBIF": 55, "IFX.DE": 32,
    "MBG.DE": 21, "0QF.DE": 11, "NVD.DE": 30, "SAP.DE": 10,
    "TLRY": 11, "LIN": 10
}

# Watchlist für Empfehlungen
kandidaten_pool = ["MSFT", "AAPL", "GOOGL", "AMZN", "TSLA", "META", "ALV.DE", "SIE.DE"]

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
        
        current_rsi = rsi.iloc[-1]
        current_price = hist['Close'].iloc[-1]
        
        return {
            "name": stock.info.get('shortName', ticker),
            "price": current_price,
            "rsi": current_rsi,
            "currency": stock.info.get('currency', 'EUR'),
            "news": stock.news[:1]  # Die aktuellste Nachricht
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
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False}
    requests.post(url, json=payload)

def main():
    heute = datetime.datetime.now()
    wochentag = heute.weekday()  # 0=Montag, 6=Sonntag
    
    bericht = f"🤖 *Depot-Check {heute.strftime('%d.%m.%Y')}*\n"
    bericht += "------------------------------------------\n\n"
    
    alarme = ""
    wochen_liste = ""
    
    # 2. DEPOT ANALYSIEREN
    for ticker in mein_depot:
        data = get_stock_data(ticker)
        if data:
            rsi = data['rsi']
            name = data['name']
            preis = f"{data['price']:.2f} {data['currency']}"
            
            # Alarme definieren
            status_emoji = ""
            if rsi > 70:
                status_emoji = "🔴 *ÜBERHITZT (Verkauf prüfen)*"
                alarme += f"{status_emoji}\n*{name}*\nPreis: {preis}\nRSI: {rsi:.1f}\n"
                if data['news']:
                    alarme += f"📰 News: [{data['news'][0]['title']}]({data['news'][0]['link']})\n\n"
            elif rsi < 30:
                status_emoji = "🟢 *GÜNSTIG (Kauf-Chance)*"
                alarme += f"{status_emoji}\n*{name}*\nPreis: {preis}\nRSI: {rsi:.1f}\n\n"
            
            # Für die Sonntags-Übersicht sammeln
            trend = "📈" if rsi > 50 else "📉"
            wochen_liste += f"{trend} {name[:12]}: {preis} (RSI: {rsi:.1f})\n"

    # 3. EMPFEHLUNGEN (Falls gewünscht)
    empfehlungen = ""
    if rsi > 70: # Nur wenn wir verkaufen könnten, suchen wir Ersatz
        empfehlungen = "\n💡 *Alternative Kauf-Kandidaten:*\n"
        for cand in kandidaten_pool[:5]:
            c_data = get_stock_data(cand)
            if c_data and c_data['rsi'] < 40:
                empfehlungen += f"• {c_data['name']} (RSI: {c_data['rsi']:.1f})\n"

    # 4. VERSAND-LOGIK
    # Sonntag (6): Immer den vollen Bericht
    if wochentag == 6:
        finaler_text = bericht + "📊 *Wochen-Zusammenfassung:*\n" + wochen_liste
        if alarme:
            finaler_text += "\n⚠️ *Aktuelle Signale:*\n" + alarme
        send_telegram_msg(finaler_text)
    
    # Unter der Woche: Nur bei Alarmen senden
    else:
        if alarme:
            finaler_text = bericht + "⚠️ *AKTION ERFORDERLICH:*\n\n" + alarme + empfehlungen
            send_telegram_msg(finaler_text)
        else:
            print("Keine Alarme, keine Nachricht gesendet.")

if __name__ == "__main__":
    main()
