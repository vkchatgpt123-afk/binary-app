import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V5.0 — MOBILE CLEAN
# MANUAL SIGNAL ONLY
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V5",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top,#173f68 0%,#081a30 50%,#02060d 100%);
    color:white;
}

.block-container {
    max-width:430px !important;
    padding:0.25rem 0.35rem 0.35rem !important;
}

header[data-testid="stHeader"] {
    display:none !important;
}

[data-testid="stToolbar"] {
    display:none !important;
}

div[data-testid="stVerticalBlock"] {
    gap:0.25rem !important;
}

div[data-testid="stHorizontalBlock"] {
    gap:4px !important;
}

div[data-testid="column"] {
    padding:0 !important;
    min-width:0 !important;
}

/* CONTROL BOX */
.control-box {
    background:#102542;
    border:1px solid #64ffda;
    border-radius:9px;
    padding:7px;
    margin-bottom:5px;
}

.stSelectbox label {
    color:#64ffda !important;
    font-size:8px !important;
    font-weight:900 !important;
    margin-bottom:2px !important;
}

div[data-baseweb="select"] > div {
    background:#07182e !important;
    border:1px solid #64ffda !important;
    border-radius:6px !important;
    min-height:30px !important;
}

div[data-baseweb="select"] span {
    color:white !important;
    font-size:10px !important;
    font-weight:800 !important;
}

/* SIGNAL */
.signal-box {
    border-radius:10px;
    padding:10px 5px;
    text-align:center;
    font-size:20px;
    font-weight:950;
    letter-spacing:1px;
    margin:4px 0;
}

.signal-up {
    background:linear-gradient(135deg,#00a884,#73c93d);
    border:2px solid #64ffda;
    color:#00130d;
}

.signal-down {
    background:linear-gradient(135deg,#ff315e,#ff512b);
    border:2px solid #ff806b;
    color:white;
}

.signal-wait {
    background:linear-gradient(135deg,#f0ae28,#ed4c20);
    border:2px solid #ffd166;
    color:#111;
}

.signal-closed {
    background:linear-gradient(135deg,#52647b,#28384d);
    border:2px solid #91a5bd;
    color:white;
}

.signal-sub {
    font-size:8px;
    font-weight:700;
    letter-spacing:0;
    margin-top:3px;
}

/* STATUS */
.status-box {
    background:#102542;
    border:1px solid #64ffda;
    border-radius:8px;
    padding:6px 3px;
    text-align:center;
    font-size:10px;
    font-weight:900;
}

.status-reason {
    color:#a8b2d1;
    font-size:8px;
    font-weight:600;
    margin-top:2px;
}

/* METRICS */
.metric-grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:4px;
    margin:3px 0;
}

.metric-card {
    background:#102542;
    border:1px solid #4ee8cf;
    border-radius:6px;
    padding:5px 2px;
    text-align:center;
}

.metric-title {
    color:#8892b0;
    font-size:7px;
    font-weight:800;
}

.metric-value {
    color:white;
    font-size:10px;
    font-weight:900;
}

/* INDICATORS */
.indicator-box {
    background:#102542;
    border:1px solid #64ffda;
    border-radius:8px;
    padding:5px;
    margin-top:3px;
}

.indicator-title {
    text-align:center;
    color:#64ffda;
    font-size:9px;
    font-weight:900;
    margin-bottom:4px;
}

.indicator-grid {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:3px;
}

.indicator {
    background:#0b1d38;
    border:1px solid #304d70;
    border-radius:5px;
    padding:4px 1px;
    text-align:center;
}

.indicator-name {
    color:#8892b0;
    font-size:6px;
    font-weight:800;
}

.indicator-icon {
    font-size:13px;
    line-height:14px;
}

/* BUTTON */
.stButton > button {
    min-height:32px !important;
    background:#0d203b !important;
    border:1px solid #64ffda !important;
    border-radius:7px !important;
    color:white !important;
    font-size:10px !important;
    font-weight:900 !important;
}

.footer {
    text-align:center;
    color:#7f8ca8;
    font-size:7px;
    margin-top:3px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# PAIRS
# =========================================================

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X"
}

TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "60m"
}


# =========================================================
# PAIR + TIMEFRAME
# =========================================================

st.markdown('<div class="control-box">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    pair = st.selectbox(
        "PAIR",
        list(PAIRS.keys()),
        index=0,
        key="pair_v500"
    )

with col2:
    timeframe = st.selectbox(
        "TIMEFRAME",
        list(TIMEFRAMES.keys()),
        index=0,
        key="tf_v500"
    )

st.markdown('</div>', unsafe_allow_html=True)

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=20, show_spinner=False)
def get_data(symbol, interval):
    try:
        df = yf.download(
            symbol,
            period="7d",
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = ["Open", "High", "Low", "Close"]

        if not all(x in df.columns for x in needed):
            return None

        df = df[needed].copy()

        df = df.apply(
            pd.to_numeric,
            errors="coerce"
        ).dropna()

        df = df.loc[
            ~df.index.duplicated(keep="last")
        ]

        return df

    except Exception:
        return None


# =========================================================
# RSI
# =========================================================

def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return (
        100 - 100 / (1 + rs)
    ).fillna(50)


# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if df is None or len(df) < 150:
        return None

    d = df.copy()

    close = d["Close"]
    high = d["High"]
    low = d["Low"]
    op = d["Open"]

    # EMA
    d["EMA12"] = close.ewm(
        span=12,
        adjust=False
    ).mean()

    d["EMA26"] = close.ewm(
        span=26,
        adjust=False
    ).mean()

    d["EMA50"] = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # SMA
    d["SMA20"] = close.rolling(20).mean()

    # RSI
    d["RSI"] = calculate_rsi(close)

    # MACD
    d["MACD"] = d["EMA12"] - d["EMA26"]

    d["MACD_SIGNAL"] = d["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    d["MACD_HIST"] = (
        d["MACD"] -
        d["MACD_SIGNAL"]
    )

    # Bollinger
    std = close.rolling(20).std()

    d["BB_UPPER"] = (
        d["SMA20"] + 2 * std
    )

    d["BB_LOWER"] = (
        d["SMA20"] - 2 * std
    )

    # ATR
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ],
        axis=1
    ).max(axis=1)

    d["ATR14"] = tr.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14
    ).mean()

    # Candle
    candle_range = (
        high - low
    ).replace(0, np.nan)

    d["BODY"] = (
        (close - op).abs() /
        candle_range
    )

    d["LOCATION"] = (
        (close - low) /
        candle_range
    )

    d = d.dropna()

    if len(d) < 100:
        return None

    # Last completed candle
    c = d.iloc[-2]
    p = d.iloc[-3]

    price = float(c["Close"])

    ema12 = float(c["EMA12"])
    ema26 = float(c["EMA26"])
    ema50 = float(c["EMA50"])

    sma20 = float(c["SMA20"])

    rsi = float(c["RSI"])
    prev_rsi = float(p["RSI"])

    macd = float(c["MACD"])
    macd_sig = float(c["MACD_SIGNAL"])

    hist = float(c["MACD_HIST"])
    prev_hist = float(p["MACD_HIST"])

    bb_up = float(c["BB_UPPER"])
    bb_low = float(c["BB_LOWER"])

    atr = float(c["ATR14"])

    body = float(c["BODY"])
    location = float(c["LOCATION"])

    # Trend strength
    gap = abs(ema12 - ema26)

    strength = (
        gap / atr
        if atr > 0
        else 0
    )

    # Market
    if (
        ema12 > ema26
        and ema26 > ema50
        and price > ema50
        and strength >= 0.15
    ):
        market = "UPTREND"

    elif (
        ema12 < ema26
        and ema26 < ema50
        and price < ema50
        and strength >= 0.15
    ):
        market = "DOWNTREND"

    else:
        market = "SIDEWAYS"

    # UP
    up = [
        market == "UPTREND",
        ema12 > ema26 and ema26 > ema50,
        45 <= rsi <= 68 and rsi > prev_rsi,
        macd > macd_sig and hist > prev_hist,
        price > ema12 and price > sma20,
        price > sma20 and price < bb_up,
        bool(c["Close"] > c["Open"]) and body >= 0.45 and location >= 0.65,
        atr > 0 and strength >= 0.15
    ]

    # DOWN
    down = [
        market == "DOWNTREND",
        ema12 < ema26 and ema26 < ema50,
        32 <= rsi <= 55 and rsi < prev_rsi,
        macd < macd_sig and hist < prev_hist,
        price < ema12 and price < sma20,
        price < sma20 and price > bb_low,
        bool(c["Close"] < c["Open"]) and body >= 0.45 and location <= 0.35,
        atr > 0 and strength >= 0.15
    ]

    up_score = sum(up)
    down_score = sum(down)

    signal = "NO TRADE"
    reason = "Confirmation incomplete"

    if (
        market == "UPTREND"
        and up_score >= 6
        and up[2]
        and up[3]
        and up[4]
    ):
        signal = "UP"
        reason = "Bullish confirmation"

    elif (
        market == "DOWNTREND"
        and down_score >= 6
        and down[2]
        and down[3]
        and down[4]
    ):
        signal = "DOWN"
        reason = "Bearish confirmation"

    elif market == "SIDEWAYS":
        reason = "Sideways market — WAIT"

    elif abs(up_score - down_score) <= 1:
        reason = "Signals balanced"

    if market == "UPTREND":
        side = "UP"
        selected = up

    elif market == "DOWNTREND":
        side = "DOWN"
        selected = down

    elif up_score >= down_score:
        side = "UP"
        selected = up

    else:
        side = "DOWN"
        selected = down

    names = [
        "Trend",
        "EMA",
        "RSI",
        "MACD",
        "Price",
        "BB",
        "Candle",
        "Strength"
    ]

    indicator_html = ""

    for name, status in zip(names, selected):

        icon = "✅" if status else "❌"

        indicator_html += (
            '<div class="indicator">'
            '<div class="indicator-name">'
            + name +
            '</div>'
            '<div class="indicator-icon">'
            + icon +
            '</div>'
            '</div>'
        )

    return {
        "signal": signal,
        "reason": reason,
        "market": market,
        "up": up_score,
        "down": down_score,
        "side": side,
        "indicators": indicator_html,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "ema12": ema12,
        "ema26": ema26,
        "ema50": ema50,
        "time": d.index[-2]
    }


# =========================================================
# LOAD
# =========================================================

df = get_data(symbol, interval)

if df is None or len(df) < 150:

    st.markdown(
        '<div class="signal-box signal-wait">'
        '⚠️ DATA UNAVAILABLE'
        '<div class="signal-sub">NO SIGNAL</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.stop()


r = analyze(df)

if r is None:

    st.markdown(
        '<div class="signal-box signal-wait">'
        '⚠️ ANALYSIS ERROR'
        '<div class="signal-sub">NO SIGNAL</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# AGE
# =========================================================

closed_time = r["time"]

try:

    if closed_time.tzinfo is None:
        closed_time = closed_time.replace(
            tzinfo=timezone.utc
        )

    age = max(
        0,
        (
            datetime.now(timezone.utc)
            - closed_time
        ).total_seconds() / 60
    )

except Exception:

    age = 999999


# =========================================================
# WEEKEND / STALE
# =========================================================

weekend = (
    datetime.now(timezone.utc).weekday() >= 5
)

max_age = {
    "5m": 20,
    "15m": 45,
    "30m": 75,
    "1H": 150
}[timeframe]

stale = age > max_age


# =========================================================
# DISPLAY SIGNAL
# =========================================================

if weekend:

    display_signal = "🔒 MARKET CLOSED"
    signal_class = "signal-closed"
    signal_reason = "Weekend — NO SIGNAL"

elif stale:

    display_signal = "🕐 DATA STALE"
    signal_class = "signal-wait"
    signal_reason = "Fresh candle unavailable"

elif r["signal"] == "UP":

    display_signal = "🟢 UP SIGNAL"
    signal_class = "signal-up"
    signal_reason = r["reason"]

elif r["signal"] == "DOWN":

    display_signal = "🔴 DOWN SIGNAL"
    signal_class = "signal-down"
    signal_reason = r["reason"]

else:

    display_signal = "🛡️ NO TRADE"
    signal_class = "signal-wait"
    signal_reason = r["reason"]


# =========================================================
# SIGNAL BOX
# =========================================================

st.markdown(
    '<div class="signal-box '
    + signal_class
    + '">'
    + display_signal
    + '<div class="signal-sub">'
    + signal_reason
    + '</div>'
    + '</div>',
    unsafe_allow_html=True
)


# =========================================================
# STATUS
# =========================================================

st.markdown(
    '<div class="status-box">'
    + '<b>'
    + r["market"]
    + '</b>'
    + ' | 🟢 '
    + str(r["up"])
    + '/8'
    + ' • 🔴 '
    + str(r["down"])
    + '/8'
    + '<div class="status-reason">'
    + signal_reason
    + '</div>'
    + '</div>',
    unsafe_allow_html=True
)


# =========================================================
# METRICS
# =========================================================

metrics_html = (
    '<div class="metric-grid">'

    '<div class="metric-card">'
    '<div class="metric-title">PRICE</div>'
    '<div class="metric-value">'
    + f'{r["price"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">RSI</div>'
    '<div class="metric-value">'
    + f'{r["rsi"]:.1f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">ATR</div>'
    '<div class="metric-value">'
    + f'{r["atr"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA12</div>'
    '<div class="metric-value">'
    + f'{r["ema12"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA26</div>'
    '<div class="metric-value">'
    + f'{r["ema26"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA50</div>'
    '<div class="metric-value">'
    + f'{r["ema50"]:.5f}'
    + '</div></div>'

    '</div>'
)

st.markdown(
    metrics_html,
    unsafe_allow_html=True
)


# =========================================================
# INDICATORS
# =========================================================

indicator_html = (
    '<div class="indicator-box">'
    '<div class="indicator-title">'
    + 'INDICATORS ('
    + r["side"]
    + ')'
    + '</div>'
    '<div class="indicator-grid">'
    + r["indicators"]
    + '</div>'
    '</div>'
)

st.markdown(
    indicator_html,
    unsafe_allow_html=True
)


# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH DATA",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    '<div class="footer">'
    + 'Closed: '
    + str(closed_time)
    + ' | Age: '
    + f'{age:.1f}m'
    + '<br>Manual signal assistant • No automatic trading'
    + '</div>',
    unsafe_allow_html=True
)
