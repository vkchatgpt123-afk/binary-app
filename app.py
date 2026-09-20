import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V4.9.4 — COMBINED CONTROL BOX FIX
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V4.9.4",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS STYLING
# =========================================================

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #1a4b7c 0%, #0a192f 50%, #02060d 100%);
    color: white;
}

.block-container {
    max-width: 410px !important;
    padding: 0.4rem 0.4rem 0.4rem 0.4rem !important;
}

/* Single Container Box for Controls */
.control-box {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 6px;
    padding: 6px 8px 2px 8px;
    margin-bottom: 6px;
}

/* Force side-by-side elements inside control box */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    width: 50% !important;
    flex: 1 1 50% !important;
    min-width: 50% !important;
    max-width: 50% !important;
}

/* Selectbox compact styling */
.stSelectbox label {
    color: #64ffda !important;
    font-size: 8px !important;
    font-weight: bold;
    margin-bottom: 2px !important;
}

div[data-baseweb="select"] > div {
    background-color: #0a192f !important;
    color: white !important;
    border: 1px solid #64ffda !important;
    border-radius: 4px !important;
    min-height: 28px !important;
}

div[data-baseweb="select"] span {
    color: #64ffda !important;
    font-size: 10px !important;
    font-weight: bold;
}

/* Highly Highlighted Signal Box */
.signal {
    border-radius: 6px;
    padding: 8px;
    margin: 6px 0;
    text-align: center;
    font-size: 15px;
    font-weight: 900;
    letter-spacing: 1px;
    box-shadow: 0 0 15px rgba(100, 255, 218, 0.4);
}

.up {
    background: linear-gradient(135deg, #00b09b, #96c93d);
    border: 2px solid #64ffda;
    color: #000000;
}

.down {
    background: linear-gradient(135deg, #ff416c, #ff4b2b);
    border: 2px solid #ff4b2b;
    color: #ffffff;
}

.wait {
    background: linear-gradient(135deg, #f7b733, #fc4a1a);
    border: 2px solid #f7b733;
    color: #111111;
}

/* Status Bar */
.status {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 5px;
    margin: 4px 0;
    text-align: center;
    font-size: 9px;
    font-weight: bold;
}

.reason {
    color: #a8b2d1;
    font-size: 8px;
    margin-top: 2px;
}

/* Metrics & Indicators Grid */
.grid-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 4px 0;
}

.grid-card {
    flex: 1 1 calc(50% - 4px);
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 6px;
    text-align: center;
}

.grid-title {
    color: #8892b0;
    font-size: 8px;
    font-weight: bold;
}

.grid-value {
    color: #ffffff;
    font-size: 11px;
    font-weight: 900;
}

/* Detailed Indicators Box wrapper */
.indicators-wrapper {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 6px;
    margin: 4px 0;
}

.ind-main-title {
    color: #64ffda;
    font-size: 9px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 5px;
}

.footer {
    color: #8892b0;
    text-align: center;
    font-size: 7px;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# PAIRS & TIMEFRAME (INSIDE ONE SINGLE BOX)
# =========================================================

PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X", "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X", "GBP/JPY": "GBPJPY=X"
}

TIMEFRAMES = {
    "5m": "5m", "15m": "15m", "30m": "30m", "1H": "60m"
}

st.markdown('<div class="control-box">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    pair = st.selectbox("PAIR", list(PAIRS.keys()))
with col2:
    timeframe = st.selectbox("TIMEFRAME", list(TIMEFRAMES.keys()))
st.markdown('</div>', unsafe_allow_html=True)

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]

# =========================================================
# DATA LOADING & ANALYSIS
# =========================================================

@st.cache_data(ttl=20)
def get_data(symbol, interval):
    try:
        df = yf.download(symbol, period="7d", interval=interval, progress=False, auto_adjust=False, threads=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        needed = ["Open", "High", "Low", "Close"]
        if not all(x in df.columns for x in needed): return None
        return df[needed].dropna().loc[~df.index.duplicated(keep="last")]
    except Exception:
        return None

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)

def analyze(df):
    if len(df) < 150: return None
    d = df.copy()
    close, high, low, op = d["Close"], d["High"], d["Low"], d["Open"]

    d["EMA12"] = close.ewm(span=12, adjust=False).mean()
    d["EMA26"] = close.ewm(span=26, adjust=False).mean()
    d["EMA50"] = close.ewm(span=50, adjust=False).mean()
    d["SMA20"] = close.rolling(20).mean()
    d["RSI"] = calculate_rsi(close)
    d["MACD"] = d["EMA12"] - d["EMA26"]
    d["MACD_SIGNAL"] = d["MACD"].ewm(span=9, adjust=False).mean()
    d["MACD_HIST"] = d["MACD"] - d["MACD_SIGNAL"]

    std = close.rolling(20).std()
    d["BB_UPPER"] = d["SMA20"] + 2 * std
    d["BB_LOWER"] = d["SMA20"] - 2 * std

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    d["ATR14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    candle_range = (high - low).replace(0, np.nan)
    d["BODY"] = (close - op).abs() / candle_range
    d["LOCATION"] = (close - low) / candle_range

    d = d.dropna()
    if len(d) < 100: return None

    c = d.iloc[-2]
    p = d.iloc[-3]

    price = float(c["Close"])
    ema12, ema26, ema50 = float(c["EMA12"]), float(c["EMA26"]), float(c["EMA50"])
    sma20 = float(c["SMA20"])
    rsi, prev_rsi = float(c["RSI"]), float(p["RSI"])
    macd, macd_sig = float(c["MACD"]), float(c["MACD_SIGNAL"])
    hist, prev_hist = float(c["MACD_HIST"]), float(p["MACD_HIST"])
    bb_up = float(c["BB_UPPER"])
    bb_low = float(c["BB_LOWER"])
    atr = float(c["ATR14"])
    body, location = float(c["BODY"]), float(c["LOCATION"])

    gap = abs(ema12 - ema26)
    strength = gap / atr if atr > 0 else 0
    strong = strength >= 0.15

    if ema12 > ema26 and ema26 > ema50 and price > ema50 and strong:
        market = "UPTREND"
    elif ema12 < ema26 and ema26 < ema50 and price < ema50 and strong:
        market = "DOWNTREND"
    else:
        market = "SIDEWAYS"

    up = [
        market == "UPTREND",
        ema12 > ema26 and ema26 > ema50,
        45 <= rsi <= 68 and rsi > prev_rsi,
        macd > macd_sig and hist > prev_hist,
        price > ema12 and price > sma20,
        price > sma20 and price < bb_up,
        c["Close"] > c["Open"] and body >= 0.45 and location >= 0.65,
        atr > 0 and strength >= 0.15
    ]

    down = [
        market == "DOWNTREND",
        ema12 < ema26 and ema26 < ema50,
        32 <= rsi <= 55 and rsi < prev_rsi,
        macd < macd_sig and hist < prev_hist,
        price < ema12 and price < sma20,
        price < sma20 and price > bb_low,
        c["Close"] < c["Open"] and body >= 0.45 and location <= 0.35,
        atr > 0 and strength >= 0.15
    ]

    up_score = sum(up)
    down_score = sum(down)

    signal, reason = "NO TRADE", "Confirmation incomplete"
    if market == "UPTREND" and up_score >= 6 and up[2] and up[3] and up[4]:
        signal, reason = "UP", "Bullish confirmation"
    elif market == "DOWNTREND" and down_score >= 6 and down[2] and down[3] and down[4]:
        signal, reason = "DOWN", "Bearish confirmation"
    elif market == "SIDEWAYS":
        reason = "Sideways market"
    elif abs(up_score - down_score) <= 1:
        reason = "Signals balanced"

    if market == "DOWNTREND":
        side = "DOWN"
        selected = down
    elif market == "UPTREND":
        side = "UP"
        selected = up
    else:
        side = "UP" if up_score >= down_score else "DOWN"
        selected = up if up_score >= down_score else down
    
    names = ["Trend", "EMA", "RSI", "MACD", "Price", "BB", "Candle", "Vol"]
    indicator_cards = []
    for name, status in zip(names, selected):
        icon = "✅" if status else "❌"
        color = "#64ffda" if status else "#ff6b6b"
        indicator_cards.append(f'<div class="grid-card"><div class="grid-title">{name}</div><div class="grid-value" style="color: {color};">{icon}</div></div>')

    return {
        "signal": signal, "reason": reason, "market": market,
        "up": up_score, "down": down_score, "side": side, 
        "indicators": "".join(indicator_cards),
        "price": price, "rsi": rsi, "atr": atr, "ema12": ema12, "ema26": ema26, "ema50": ema50,
        "time": d.index[-2]
    }

# =========================================================
# RUN EXECUTION
# =========================================================

df = get_data(symbol, interval)
if df is None or len(df) < 150:
    st.error("⚠️ DATA UNAVAILABLE")
    st.stop()

r = analyze(df)
if r is None:
    st.error("⚠️ ANALYSIS ERROR")
    st.stop()

closed_time = r["time"]
try:
    if closed_time.tzinfo is None:
        closed_time = closed_time.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - closed_time).total_seconds() / 60
except Exception:
    age = 999999

max_age = 20 if timeframe == "5m" else (45 if timeframe == "15m" else (75 if timeframe == "30m" else 150))
stale = age > max_age

# Highly Highlighted Signal Box
if stale:
    st.markdown('<div class="signal wait">🕐 DATA STALE — NO SIGNAL</div>', unsafe_allow_html=True)
elif r["signal"] == "UP":
    st.markdown('<div class="signal up">🟢 UP SIGNAL (CALL)</div>', unsafe_allow_html=True)
elif r["signal"] == "DOWN":
    st.markdown('<div class="signal down">🔴 DOWN SIGNAL (PUT)</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal wait">🛡️ NO TRADE / WAIT</div>', unsafe_allow_html=True)

# Market Status
st.markdown(f'<div class="status"><b>{r["market"]}</b> | 🟢 {r["up"]}/8 • 🔴 {r["down"]}/8<div class="reason">{r["reason"]}</div></div>', unsafe_allow_html=True)

# Metrics Grid
st.markdown(f'''<div class="grid-container">
<div class="grid-card"><div class="grid-title">PRICE</div><div class="grid-value">{r["price"]:.5f}</div></div>
<div class="grid-card"><div class="grid-title">RSI</div><div class="grid-value">{r["rsi"]:.1f}</div></div>
<div class="grid-card"><div class="grid-title">ATR</div><div class="grid-value">{r["atr"]:.5f}</div></div>
<div class="grid-card"><div class="grid-title">EMA12</div><div class="grid-value">{r["ema12"]:.5f}</div></div>
<div class="grid-card"><div class="grid-title">EMA26</div><div class="grid-value">{r["ema26"]:.5f}</div></div>
<div class="grid-card"><div class="grid-title">EMA50</div><div class="grid-value">{r["ema50"]:.5f}</div></div>
</div>''', unsafe_allow_html=True)

# Detailed Indicators Grid Box
st.markdown(f'''<div class="indicators-wrapper">
<div class="ind-main-title">INDICATORS ({r["side"]})</div>
<div class="grid-container" style="margin: 0;">
{r["indicators"]}
</div>
</div>''', unsafe_allow_html=True)

# Refresh Button
if st.button("🔄 REFRESH DATA", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.markdown(f'<div class="footer">Age: {age:.1f}m | Closed: {closed_time}</div>', unsafe_allow_html=True)
