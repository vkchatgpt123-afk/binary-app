```python
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V4.4 — ULTIMATE SINGLE-SCREEN LAYOUT
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V4.4",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS FOR FORCED SINGLE-SCREEN VIEW & NEON THEME
# =========================================================

st.markdown("""
<style>
/* Prevent scrolling and enforce a compact single screen layout */
html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #1a4b7c 0%, #0a192f 50%, #02060d 100%) !important;
    color: white !important;
    overflow: hidden !important;
    height: 100vh !important;
    max-height: 100vh !important;
}

.block-container {
    max-width: 400px !important;
    padding: 0.2rem 0.4rem !important;
    margin: 0 auto !important;
    height: 100vh !important;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* Force Streamlit columns to stay strictly 50-50 side-by-side */
div[data-testid="column"] {
    width: 50% !important;
    flex: 1 1 50% !important;
    min-width: 50% !important;
    padding: 0px 2px !important;
}

div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 4px;
    margin-bottom: 2px;
}

/* Compact Selectboxes */
div[data-baseweb="select"] > div {
    background-color: #112240 !important;
    color: white !important;
    border: 1px solid #64ffda !important;
    border-radius: 4px !important;
    min-height: 22px !important;
    height: 26px !important;
}
div[data-baseweb="select"] span {
    color: #64ffda !important;
    font-size: 8px !important;
    font-weight: bold;
}

/* Header Box */
.header-box {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 2px 4px;
    text-align: center;
    font-size: 8.5px;
    color: #64ffda;
    font-weight: bold;
    margin-bottom: 2px;
}

/* Highlighted Signal Box */
.signal {
    border-radius: 5px;
    padding: 4px;
    margin: 2px 0;
    text-align: center;
    font-size: 13px;
    font-weight: 900;
    box-shadow: 0 0 8px rgba(100,255,218,0.3);
    letter-spacing: 0.5px;
}

.up {
    background: #00b09b;
    border: 2px solid #64ffda;
    color: #ffffff;
}

.down {
    background: #ff416c;
    border: 2px solid #ff4b2b;
    color: #ffffff;
}

.wait {
    background: #f7b733;
    border: 2px solid #fc4a1a;
    color: #111111;
}

/* Status Bar */
.status {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 2px 4px;
    margin: 2px 0;
    text-align: center;
    font-size: 8.5px;
    font-weight: bold;
}

.reason {
    color: #a8b2d1;
    font-size: 7.5px;
    margin-top: 0px;
}

/* Metrics Grid (50-50 Pairs) */
.metrics-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin: 2px 0;
}

.metric-card {
    flex: 1 1 calc(50% - 3px);
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 2px 4px;
    text-align: center;
}

.metric-title {
    color: #8892b0;
    font-size: 7px;
    font-weight: bold;
}

.metric-value {
    color: #ffffff;
    font-size: 9.5px;
    font-weight: 900;
}

/* Detailed Indicators Grid Box (2x4 Grid layout) */
.indicators-container {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 4px;
    padding: 3px;
    margin: 2px 0;
}

.ind-title {
    color: #64ffda;
    font-size: 7.5px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2px;
}

.ind-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 2px;
}

.ind-item {
    background: #0a192f;
    border-radius: 3px;
    padding: 2px 1px;
    text-align: center;
    font-size: 7px;
    font-weight: bold;
    border: 1px solid rgba(100,255,218,0.15);
}

/* Compact Refresh Button */
.stButton > button {
    width: 100% !important;
    background-color: #112240 !important;
    color: #64ffda !important;
    border: 1px solid #64ffda !important;
    border-radius: 4px !important;
    padding: 2px !important;
    font-size: 8.5px !important;
    font-weight: bold !important;
    min-height: 24px !important;
    height: 26px !important;
    margin-top: 2px;
}

.footer {
    color: #8892b0;
    text-align: center;
    font-size: 6.5px;
    margin-top: 1px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# PAIRS & TIMEFRAME DEFINITIONS
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

col_pair, col_tf = st.columns(2)
with col_pair:
    pair = st.selectbox("PAIR", list(PAIRS.keys()))
with col_tf:
    timeframe = st.selectbox("TIMEFRAME", list(TIMEFRAMES.keys()))

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]

# =========================================================
# DATA FETCHING & TECHNICAL ANALYSIS ENGINE
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
    bb_up, bb_low = float(c["BB_UPPER"]), float(c["BB_LOWER"])
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

    selected = up if up_score >= down_score else down
    side = "UP" if up_score >= down_score else "DOWN"
    
    # Detailed Indicator Grid mapping
    names = ["Trend", "EMA", "RSI", "MACD", "Price", "Bollinger", "Candle", "Volume"]
    indicator_details = []
    for name, status in zip(names, selected):
        icon = "✅" if status else "❌"
        color = "#64ffda" if status else "#ff6b6b"
        indicator_details.append(f'<div class="ind-item" style="color: {color};">{name}<br>{icon}</div>')

    return {
        "signal": signal, "reason": reason, "market": market,
        "up": up_score, "down": down_score, "side": side, 
        "indicators": "".join(indicator_details),
        "price": price, "rsi": rsi, "atr": atr, "ema12": ema12, "ema26": ema26, "ema50": ema50,
        "time": d.index[-2]
    }

# =========================================================
# EXECUTION & SINGLE-SCREEN UI RENDERING
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

# Header Info
st.markdown(f'<div class="header-box">💱 {pair} • ⏱️ {timeframe} • 🔒 CLOSED</div>', unsafe_allow_html=True)

# Highlighted Signal Box
if stale:
    st.markdown('<div class="signal wait">🕐 DATA STALE — NO SIGNAL</div>', unsafe_allow_html=True)
elif r["signal"] == "UP":
    st.markdown('<div class="signal up">🟢 UP SIGNAL</div>', unsafe_allow_html=True)
elif r["signal"] == "DOWN":
    st.markdown('<div class="signal down">🔴 DOWN SIGNAL</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal wait">🛡️ NO TRADE</div>', unsafe_allow_html=True)

# Market Status
st.markdown(f"""
    <div class="status">
        <b>{r['market']}</b> | 🟢 {r['up']}/8 • 🔴 {r['down']}/8
        <div class="reason">{r['reason']}</div>
    </div>
""", unsafe_allow_html=True)

# Metrics Grid (50-50 format)
st.markdown(f"""
    <div class="metrics-grid">
        <div class="metric-card"><div class="metric-title">PRICE</div><div class="metric-value">{r['price']:.5f}</div></div>
        <div class="metric-card"><div class="metric-title">RSI</div><div class="metric-value">{r['rsi']:.1f}</div></div>
        <div class="metric-card"><div class="metric-title">ATR</div><div class="metric-value">{r['atr']:.5f}</div></div>
        <div class="metric-card"><div class="metric-title">EMA12</div><div class="metric-value">{r['ema12']:.5f}</div></div>
        <div class="metric-card"><div class="metric-title">EMA26</div><div class="metric-value">{r['ema26']:.5f}</div></div>
        <div class="metric-card"><div class="metric-title">EMA50</div><div class="metric-value">{r['ema50']:.5f}</div></div>
    </div>
""", unsafe_allow_html=True)

# Detailed Indicators Grid Box
st.markdown(f"""
    <div class="indicators-container">
        <div class="ind-title">INDICATOR DETAILS ({r['side']})</div>
        <div class="ind-grid">
            {r['indicators']}
        </div>
    </div>
""", unsafe_allow_html=True)

# Refresh Button
if st.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

st.markdown(f'<div class="footer">Age: {age:.1f}m | Closed: {closed_time}</div>', unsafe_allow_html=True)
```
