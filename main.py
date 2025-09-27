import time
import requests
import pandas as pd
import pytz
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import io
import logging

# ================== CONFIG ==================
TELEGRAM_TOKEN = "8462939843:AAEvcFCJKaZqTawZKwPyidvDoy4kFO1j6So"
TELEGRAM_CHAT_ID = "1343842801"

# Symbols
CRYPTO = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "DOGE-USD", "XRP-USD"]
INDIA_STOCKS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# Timeframes (Yahoo supported)
TIMEFRAMES = {"15m": "15m", "30m": "30m", "1h": "60m", "4h": "1h", "1d": "1d"}

# ============================================

# ✅ Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ✅ Telegram
def send_telegram_message(text, img_buf=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

        if img_buf:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            img_buf.seek(0)
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": img_buf})
        logging.info("Telegram alert sent.")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ✅ Doji detector
def is_doji(open_, high, low, close):
    body = abs(close - open_)
    rng = high - low
    return body <= 0.2 * rng

# ✅ Breakout check
def detect_breakouts(df):
    alerts = []
    for i in range(2, len(df)):
        cndl = df.iloc[i - 1]
        prev = df.iloc[i - 2]

        # Doji
        if is_doji(cndl["Open"], cndl["High"], cndl["Low"], cndl["Close"]):
            if df.iloc[i]["Close"] > cndl["High"]:
                alerts.append(("Doji Breakout 🔼", cndl))
            elif df.iloc[i]["Close"] < cndl["Low"]:
                alerts.append(("Doji Breakdown 🔽", cndl))

        # Inside candle
        if (cndl["High"] < prev["High"]) and (cndl["Low"] > prev["Low"]):
            if df.iloc[i]["Close"] > cndl["High"]:
                alerts.append(("Inside Candle Breakout 🔼", cndl))
            elif df.iloc[i]["Close"] < cndl["Low"]:
                alerts.append(("Inside Candle Breakdown 🔽", cndl))

        # Consolidation (3+ small candles)
        cons = df.iloc[i - 4:i - 1]
        if all(is_doji(r["Open"], r["High"], r["Low"], r["Close"]) for _, r in cons.iterrows()):
            if df.iloc[i]["Close"] > cons["High"].max():
                alerts.append(("🔥 Consolidation Breakout 🔼", cndl))
            elif df.iloc[i]["Close"] < cons["Low"].min():
                alerts.append(("🔥 Consolidation Breakdown 🔽", cndl))

    return alerts

# ✅ Plot chart
def plot_chart(df, title):
    plt.figure(figsize=(6, 3))
    plt.plot(df["Close"].tail(30))
    plt.title(title)
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    return buf

# ✅ Scanner
def scan_market():
    for symbol in CRYPTO + INDIA_STOCKS:
        for tf_name, tf in TIMEFRAMES.items():
            try:
                df = yf.download(symbol, period="30d", interval=tf, progress=False)
                df.reset_index(inplace=True)
                alerts = detect_breakouts(df)

                for text, cndl in alerts:
                    msg = f"📊 {symbol} | {tf_name}\n{text}\nClose={cndl['Close']}"
                    img = plot_chart(df, f"{symbol} - {tf_name}")
                    send_telegram_message(msg, img)
            except Exception as e:
                logging.error(f"Error scanning {symbol}-{tf_name}: {e}")

# ✅ Scheduler
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler.add_job(scan_market, "interval", minutes=5)
scheduler.start()

logging.info("🚀 Trading bot started on Deta Space.")
while True:
    time.sleep(60)

