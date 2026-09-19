import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V2 — FINAL STABLE MOBILE LAYOUT
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V2",
    page_icon="📊",
    layout="centered"
)

# =========================================================
# COMPACT CSS (NO HIDING, EVERYTHING VISIBLE)
# =========================================================

st.markdown("""
<style>
.stApp {
    background: #080c14;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {
    max-width: 480px;
    padding: 0.2rem 0.4rem 0.5rem 0.4rem !important;
}

/* Compact Selectboxes */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    color: white !important;
    border: 1px solid #263244 !important;
    border-radius: 4px !important;
    min-height: 32px !important;
}
div[data-baseweb="select"] span {
    color: white !important;
    font-size: 11px !important;
}

/* Header */
.header-box {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 3px 6px;
    text-align: center;
    font-size: 10px;
    color: #9ca3af;
    margin-bottom: 3px;
    margin-top: 2px;
}

/* Signal Box */
.signal {
    border-radius: 6px;
    padding: 6px 4px;
    margin: 2px 0;
    text-align: center;
    font-size: 18px;
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
    border: 1px solid #263244;
    border-radius: 5px;
    padding: 4px 6px;
    margin: 2px 0;
    text-align: center;
    font-size: 10px;
}

.reason {
    color: #9ca3af;
    font-size: 9px;
    margin-top: 1px;
}

/* Metrics Grid Boxes */
.metric-box {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 5px;
    padding: 4px 6px;
    margin: 2px 0;
    text-align: center;
}

.metric-title {
    color: #9ca3af;
    font-size: 9px;
    font-weight: bold;
}

.metric-value {
    color: white;
    font-size: 11px;
    font-weight: bold;
}

/* Check Rows */
.check {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 0;
    font-size: 10px;
    display: flex;
    justify-content: space-between;
}

.footer {
    color: #6b7280;
    text-align: center;
    font-size: 8px;
    margin-top: 3px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# PAIRS & TIMEFRAMES
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

# =========================================================
# VERTICAL SELECTORS (FIXED: NO HIDING)
# =========================================================

selected_pair = st.selectbox("Pair", list(PAIRS.keys()))
selected_tf = st.selectbox("Timeframe", list(TIMEFRAMES.keys()))

ticker = PAIRS[selected_pair]
interval = TIMEFRAMES[selected_tf]

# =========================================================
# DATA LOADING & ANALYSIS ENGINE
# =========================================================

@st.cache_data(ttl=30)
def load_data(symbol, interval_value):
    try:
        df = yf.download(symbol, period="7d", interval=interval_value, progress=False, auto_adjust=False, threads=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        required = ["Open", "High", "Low", "Close"]
        if not all(col in df.columns for col in required): return None
        return df[required].dropna().loc[~df.index.duplicated(keep="last")]
    except Exception:
        return None

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean().replace(0, np.nan)
    rs = avg_gain / avg_loss
    return (100 - (100 / (1 + rs))).fillna(50)

def analyze_market(df):
    if len(df) < 100: return None
    data = df.copy()
    close, high, low, open_price = data["Close"], data["High"], data["Low"], data["Open"]

    data["EMA12"] = close.ewm(span=12, adjust=False).mean()
    data["EMA26"] = close.ewm(span=26, adjust=False).mean()
    data["EMA50"] = close.ewm(span=50, adjust=False).mean()
    data["SMA20"] = close.rolling(20).mean()
    data["RSI"] = calculate_rsi(close, 14)
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()
    
    std = close.rolling(20).std()
    data["BB_UPPER"] = data["SMA20"] + 2 * std
    data["BB_LOWER"] = data["SMA20"] - 2 * std

    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    data["ATR14"] = true_range.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    candle_range = (high - low).replace(0, np.nan)
    data["BODY_PCT"] = (close - open_price).abs() / candle_range
    data["CLOSE_LOCATION"] = (close - low) / candle_range

    data = data.dropna()
    if len(data) < 80: return None

    candle = data.iloc[-2]
    previous = data.iloc[-3]

    close_val = float(candle["Close"])
    ema12, ema26, ema50 = float(candle["EMA12"]), float(candle["EMA26"]), float(candle["EMA50"])
    sma20, rsi, macd, macd_signal = float(candle["SMA20"]), float(candle["RSI"]), float(candle["MACD"]), float(candle["MACD_SIGNAL"])
    atr, body_pct, close_location = float(candle["ATR14"]), float(candle["BODY_PCT"]), float(candle["CLOSE_LOCATION"])

    strong_trend = atr > 0 and abs(ema12 - ema26) >= (0.12 * atr)
    if ema12 > ema26 and close_val > ema50 and strong_trend:
        market_state = "UPTREND"
    elif ema12 < ema26 and close_val < ema50 and strong_trend:
        market_state = "DOWNTREND"
    else:
        market_state = "SIDEWAYS"

    bullish_reversal = previous["Close"] < previous["Open"] and candle["Close"] > candle["Open"] and close_location >= 0.65 and body_pct >= 0.35
    bearish_reversal = previous["Close"] > previous["Open"] and candle["Close"] < candle["Open"] and close_location <= 0.35 and body_pct >= 0.35

    up_checks = [
        ("Reversal Pattern", bool(bullish_reversal)),
        ("RSI Momentum", bool(rsi > 35 and rsi > float(previous["RSI"]))),
        ("MACD Cross", bool(macd > macd_signal and macd > float(previous["MACD"]))),
        ("Above SMA20", bool(close_val > sma20)),
        ("Above EMA12", bool(close_val > ema12)),
        ("Volatility Active", bool(atr > 0))
    ]

    down_checks = [
        ("Reversal Pattern", bool(bearish_reversal)),
        ("RSI Momentum", bool(rsi < 65 and rsi < float(previous["RSI"]))),
        ("MACD Cross", bool(macd < macd_signal and macd < float(previous["MACD"]))),
        ("Below SMA20", bool(close_val < sma20)),
        ("Below EMA12", bool(close_val < ema12)),
        ("Volatility Active", bool(atr > 0))
    ]

    up_score = sum(p for _, p in up_checks)
    down_score = sum(p for _, p in down_checks)

    signal, reason = "NO TRADE", "Waiting for stronger setup."
    if market_state == "UPTREND" and up_score >= 5:
        signal, reason = "UP", f"UP confirmation {up_score}/6"
    elif market_state == "DOWNTREND" and down_score >= 5:
        signal, reason = "DOWN", f"DOWN confirmation {down_score}/6"
    elif market_state == "SIDEWAYS":
        reason = "Sideways market filtered."

    return {
        "signal": signal, "reason": reason, "market_state": market_state,
        "up_checks": up_checks, "down_checks": down_checks,
        "up_score": up_score, "down_score": down_score,
        "close": close_val, "rsi": rsi, "ema12": ema12, "ema26": ema26,
        "closed_time": data.index[-2]
    }

# =========================================================
# RENDER OUTPUT
# =========================================================

df = load_data(ticker, interval)
if df is None or len(df) < 100:
    st.error("⚠️ Market data unavailable.")
    st.stop()

result = analyze_market(df)
if result is None:
    st.error("⚠️ Analysis error.")
    st.stop()

# Header status bar
st.markdown(f"""
    <div class="header-box">
        <b>{selected_pair}</b> • <b>{selected_tf}</b> • 🔒 CLOSED CANDLE
    </div>
""", unsafe_allow_html=True)

# Signal Display Box
sig = result["signal"]
if sig == "UP":
    st.markdown('<div class="signal up">🟢 UP SIGNAL</div>', unsafe_allow_html=True)
elif sig == "DOWN":
    st.markdown('<div class="signal down">🔴 DOWN SIGNAL</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal wait">🛡️ NO TRADE</div>', unsafe_allow_html=True)

# Status info
score_txt = f'UP {result["up_score"]}/6' if sig == "UP" else (f'DOWN {result["down_score"]}/6' if sig == "DOWN" else f'UP {result["up_score"]}/6 • DOWN {result["down_score"]}/6')
st.markdown(f"""
    <div class="status">
        <b>Market:</b> {result["market_state"]} | <b>Score:</b> {score_txt}
        <div class="reason">{result["reason"]}</div>
    </div>
""", unsafe_allow_html=True)

# Metrics 2x2 Grid Columns
col1, col2 = st.columns(2)
with col1:
    st.markdown(f'<div class="metric-box"><div class="metric-title">PRICE</div><div class="metric-value">{result["close"]:.5f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">EMA12</div><div class="metric-value">{result["ema12"]:.5f}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-box"><div class="metric-title">RSI</div><div class="metric-value">{result["rsi"]:.1f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-box"><div class="metric-title">EMA26</div><div class="metric-value">{result["ema26"]:.5f}</div></div>', unsafe_allow_html=True)

# Checks Expander
with st.expander("🔎 Institutional Filters"):
    checks = result["up_checks"] if sig == "UP" else (result["down_checks"] if sig == "DOWN" else (result["up_checks"] if result["up_score"] >= result["down_score"] else result["down_checks"]))
    for name, passed in checks:
        icon = "✅" if passed else "❌"
        st.markdown(f'<div class="check"><span>{name}</span><span>{icon}</span></div>', unsafe_allow_html=True)

# Refresh button & timestamp
if st.button("🔄 REFRESH", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.markdown(f'<div class="footer">Closed: {result["closed_time"]}</div>', unsafe_allow_html=True)
