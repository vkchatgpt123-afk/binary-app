import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V3.8 — ULTRA COMPACT SINGLE SCREEN
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.8",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# ULTRA COMPACT CSS (SINGLE SCREEN FIT)
# =========================================================

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #123d63 0%, #071522 48%, #03070c 100%);
    color: white;
}

.block-container {
    max-width: 410px !important;
    padding: 0.1rem 0.3rem 0.3rem 0.3rem !important;
}

/* Compact Selectboxes */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    color: white !important;
    border: 1px solid #24dfff !important;
    border-radius: 4px !important;
    min-height: 26px !important;
}
div[data-baseweb="select"] span {
    color: white !important;
    font-size: 10px !important;
}

/* Header */
.header-box {
    background: #111827;
    border: 1px solid #24dfff;
    border-radius: 5px;
    padding: 3px 6px;
    text-align: center;
    font-size: 9px;
    color: #64eaff;
    margin-bottom: 2px;
    margin-top: 2px;
}

/* Signal Box */
.signal {
    border-radius: 5px;
    padding: 4px 2px;
    margin: 2px 0;
    text-align: center;
    font-size: 14px;
    font-weight: 900;
}

.up {
    background: #064e3b;
    border: 1px solid #10b981;
    color: #6ee7b7;
}

.down {
    background: #7f1d1d;
    border: 1px solid #ef4444;
    color: #fca5a5;
}

.wait {
    background: #1f1a0a;
    border: 1px solid #f59e0b;
    color: #fbbf24;
}

/* Status Bar */
.status {
    background: #111827;
    border: 1px solid #24dfff;
    border-radius: 4px;
    padding: 3px 5px;
    margin: 2px 0;
    text-align: center;
    font-size: 9px;
}

.reason {
    color: #9ca3af;
    font-size: 8px;
    margin-top: 1px;
}

/* Metrics Grid Boxes */
.metric-box {
    background: #111827;
    border: 1px solid #24dfff;
    border-radius: 4px;
    padding: 3px 5px;
    margin: 2px 0;
    text-align: center;
}

.metric-title {
    color: #64eaff;
    font-size: 8px;
    font-weight: bold;
}

.metric-value {
    color: white;
    font-size: 10px;
    font-weight: bold;
}

/* Filters Box */
.filters-box {
    background: #111827;
    border: 1px solid #24dfff;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 2px 0;
    text-align: center;
    font-size: 9px;
    color: #e2e8f0;
}

.footer {
    color: #6b7280;
    text-align: center;
    font-size: 7px;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# PAIRS & TIME
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

pair = st.selectbox("SELECT PAIR", list(PAIRS.keys()))
timeframe = st.selectbox("SELECT TIMEFRAME", list(TIMEFRAMES.keys()))

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
    names = ["T", "EMA", "RSI", "MACD", "P", "BB", "C", "V"]
    filters = " ".join(f"{n}{'✓' if x else '×'}" for n, x in zip(names, selected))

    return {
        "signal": signal, "reason": reason, "market": market,
        "up": up_score, "down": down_score, "side": side, "filters": filters,
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

# Header Info
st.markdown(f'<div class="header-box">💱 {pair} • ⏱️ {timeframe} • 🔒 CLOSED</div>', unsafe_allow_html=True)

# Signal Box
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

# Compact Metrics in 2x2 Grid Columns to Save Height
col1, col2 = st.columns(2)
with col1:
    st.markdown(f'<div class="metric-box"><div class="metric-title">PRICE</div><div class="metric-value">{r['price']:.5f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">ATR</div><div class="metric-value">{r['atr']:.5f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">EMA26</div><div class="metric-value">{r['ema26']:.5f}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-box"><div class="metric-title">RSI</div><div class="metric-value">{r['rsi']:.1f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">EMA12</div><div class="metric-value">{r['ema12']:.5f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">EMA50</div><div class="metric-value">{r['ema50']:.5f}</div></div>', unsafe_allow_html=True)

# Filters Box (Compact & Single Line)
st.markdown(f"""
    <div class="filters-box">
        <b>Filters ({r['side']}):</b> {r['filters']}
    </div>
""", unsafe_allow_html=True)

# Refresh Button
if st.button("🔄 REFRESH DATA", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.markdown(f'<div class="footer">Age: {age:.1f}m | Closed: {closed_time}</div>', unsafe_allow_html=True)
