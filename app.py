import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V3.6
# ULTRA COMPACT • BRIGHT • FULL INFORMATION
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.6",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# ULTRA COMPACT CSS
# =========================================================

st.markdown("""
<style>

/* ---------- APP ---------- */

.stApp {
    background:
        radial-gradient(
            circle at top,
            #123d63 0%,
            #071522 48%,
            #03070c 100%
        );
}

.block-container {
    max-width: 410px !important;
    padding: 0.05rem 0.12rem 0.08rem 0.12rem !important;
}

/* ---------- ALL TEXT ---------- */

p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* ---------- TITLE ---------- */

h1 {
    font-size: 17px !important;
    line-height: 18px !important;
    margin: 0 !important;
    padding: 0 !important;
    text-align: center !important;
    color: #ffffff !important;
}

/* ---------- CAPTION ---------- */

[data-testid="stCaptionContainer"] {
    font-size: 7px !important;
    line-height: 8px !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ---------- COLUMNS ---------- */

[data-testid="column"] {
    padding-left: 1px !important;
    padding-right: 1px !important;
}

/* ---------- SELECT ---------- */

[data-testid="stSelectbox"] {
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stSelectbox"] label {
    font-size: 7px !important;
    line-height: 8px !important;
    margin: 0 !important;
    color: #4de7ff !important;
    font-weight: 900 !important;
}

div[data-baseweb="select"] {
    min-height: 25px !important;
    height: 25px !important;
    border-radius: 5px !important;
}

div[data-baseweb="select"] > div {
    min-height: 25px !important;
    height: 25px !important;
    padding: 0 5px !important;
}

/* ---------- ALERT / SIGNAL ---------- */

div[data-testid="stAlert"] {
    min-height: 25px !important;
    padding: 3px 5px !important;
    margin: 2px 0 !important;
    border-radius: 6px !important;
    font-size: 10px !important;
    line-height: 11px !important;
    font-weight: 900 !important;
}

/* ---------- METRICS ---------- */

div[data-testid="stMetric"] {
    min-height: 34px !important;
    height: 34px !important;
    padding: 1px 2px !important;
    margin: 0 !important;
    border-radius: 5px !important;
    border: 1px solid #24dfff !important;
    background:
        linear-gradient(
            135deg,
            #102d47,
            #123a58
        ) !important;
    box-shadow: 0 0 4px rgba(0,220,255,.15);
}

div[data-testid="stMetricLabel"] {
    font-size: 6px !important;
    line-height: 7px !important;
    margin: 0 !important;
    padding: 0 !important;
    color: #64eaff !important;
}

div[data-testid="stMetricValue"] {
    font-size: 10px !important;
    line-height: 11px !important;
    margin: 0 !important;
    padding: 0 !important;
    color: #ffffff !important;
    font-weight: 900 !important;
}

/* ---------- BUTTON ---------- */

div.stButton {
    margin: 1px 0 !important;
}

div.stButton > button {
    min-height: 23px !important;
    height: 23px !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 5px !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    background:
        linear-gradient(
            90deg,
            #00c6ff,
            #0072ff
        ) !important;
}

/* ---------- HR ---------- */

hr {
    margin: 1px 0 !important;
    padding: 0 !important;
}

/* ---------- SPACE CONTROL ---------- */

div[data-testid="stVerticalBlock"] {
    gap: 0.12rem !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📊 SIGNAL TERMINAL V3.6")

# =========================================================
# PAIRS / TIME
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

c1, c2 = st.columns(2)

with c1:
    pair = st.selectbox(
        "PAIR",
        list(PAIRS.keys())
    )

with c2:
    timeframe = st.selectbox(
        "TIME",
        list(TIMEFRAMES.keys())
    )

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]

# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=20)
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

        needed = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        if not all(
            x in df.columns
            for x in needed
        ):
            return None

        df = df[needed].dropna()

        df = df.loc[
            ~df.index.duplicated(
                keep="last"
            )
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

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    return (
        100 -
        100 / (1 + rs)
    ).fillna(50)

# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if len(df) < 150:
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
    d["SMA20"] = close.rolling(
        20
    ).mean()

    # RSI
    d["RSI"] = calculate_rsi(
        close
    )

    # MACD
    d["MACD"] = (
        d["EMA12"] -
        d["EMA26"]
    )

    d["MACD_SIGNAL"] = (
        d["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    d["MACD_HIST"] = (
        d["MACD"] -
        d["MACD_SIGNAL"]
    )

    # Bollinger
    std = close.rolling(
        20
    ).std()

    d["BB_UPPER"] = (
        d["SMA20"] +
        2 * std
    )

    d["BB_LOWER"] = (
        d["SMA20"] -
        2 * std
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
    ).replace(
        0,
        np.nan
    )

    d["BODY"] = (
        (close - op).abs()
        / candle_range
    )

    d["LOCATION"] = (
        (close - low)
        / candle_range
    )

    d = d.dropna()

    if len(d) < 100:
        return None

    # CLOSED CANDLE
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

    # =====================================================
    # TREND
    # =====================================================

    gap = abs(
        ema12 - ema26
    )

    strength = (
        gap / atr
        if atr > 0
        else 0
    )

    strong = strength >= 0.15

    if (
        ema12 > ema26
        and ema26 > ema50
        and price > ema50
        and strong
    ):

        market = "UPTREND"

    elif (
        ema12 < ema26
        and ema26 < ema50
        and price < ema50
        and strong
    ):

        market = "DOWNTREND"

    else:

        market = "SIDEWAYS"

    # =====================================================
    # UP FILTERS
    # =====================================================

    up = [

        market == "UPTREND",

        ema12 > ema26
        and ema26 > ema50,

        45 <= rsi <= 68
        and rsi > prev_rsi,

        macd > macd_sig
        and hist > prev_hist,

        price > ema12
        and price > sma20,

        price > sma20
        and price < bb_up,

        c["Close"] > c["Open"]
        and body >= 0.45
        and location >= 0.65,

        atr > 0
        and strength >= 0.15
    ]

    # =====================================================
    # DOWN FILTERS
    # =====================================================

    down = [

        market == "DOWNTREND",

        ema12 < ema26
        and ema26 < ema50,

        32 <= rsi <= 55
        and rsi < prev_rsi,

        macd < macd_sig
        and hist < prev_hist,

        price < ema12
        and price < sma20,

        price < sma20
        and price > bb_low,

        c["Close"] < c["Open"]
        and body >= 0.45
        and location <= 0.35,

        atr > 0
        and strength >= 0.15
    ]

    up_score = sum(up)

    down_score = sum(down)

    # =====================================================
    # SIGNAL
    # =====================================================

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

        reason = "Sideways market"

    elif abs(
        up_score - down_score
    ) <= 1:

        reason = "Signals balanced"

    if up_score >= down_score:
        selected = up
        side = "UP"
    else:
        selected = down
        side = "DOWN"

    names = [
        "T",
        "EMA",
        "RSI",
        "MACD",
        "P",
        "BB",
        "C",
        "V"
    ]

    filters = " ".join(
        f"{n}{'✓' if x else '×'}"
        for n, x in zip(
            names,
            selected
        )
    )

    return {
        "signal": signal,
        "reason": reason,
        "market": market,
        "up": up_score,
        "down": down_score,
        "side": side,
        "filters": filters,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "ema12": ema12,
        "ema26": ema26,
        "ema50": ema50,
        "time": d.index[-2]
    }

# =========================================================
# RUN
# =========================================================

df = get_data(
    symbol,
    interval
)

if df is None:

    st.error(
        "⚠️ DATA UNAVAILABLE"
    )

    st.stop()

if len(df) < 150:

    st.error(
        "⚠️ NOT ENOUGH DATA"
    )

    st.stop()

r = analyze(df)

if r is None:

    st.error(
        "⚠️ ANALYSIS ERROR"
    )

    st.stop()

# =========================================================
# DATA AGE
# =========================================================

closed_time = r["time"]

try:

    if closed_time.tzinfo is None:
        closed_time = closed_time.replace(
            tzinfo=timezone.utc
        )

    age = (
        datetime.now(timezone.utc)
        - closed_time
    ).total_seconds() / 60

except Exception:

    age = 999999

if timeframe == "5m":
    max_age = 20
elif timeframe == "15m":
    max_age = 45
elif timeframe == "30m":
    max_age = 75
else:
    max_age = 150

stale = age > max_age

# =========================================================
# HEADER
# =========================================================

st.caption(
    f"💱 {pair} • ⏱️ {timeframe} • 🔒 CLOSED"
)

# =========================================================
# SIGNAL
# =========================================================

if stale:

    st.warning(
        "🕐 DATA STALE — NO SIGNAL"
    )

elif r["signal"] == "UP":

    st.success(
        "🟢 UP SIGNAL"
    )

elif r["signal"] == "DOWN":

    st.error(
        "🔴 DOWN SIGNAL"
    )

else:

    st.warning(
        "🛡️ NO TRADE"
    )

# =========================================================
# MARKET
# =========================================================

st.write(
    f"🌐 **{r['market']}** • "
    f"🟢 {r['up']}/8 • "
    f"🔴 {r['down']}/8 • "
    f"💡 {r['reason']}"
)

# =========================================================
# PRICE / RSI / ATR
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "PRICE",
        f"{r['price']:.5f}"
    )

with b:
    st.metric(
        "RSI",
        f"{r['rsi']:.1f}"
    )

with c:
    st.metric(
        "ATR",
        f"{r['atr']:.5f}"
    )

# =========================================================
# EMA
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "EMA12",
        f"{r['ema12']:.5f}"
    )

with b:
    st.metric(
        "EMA26",
        f"{r['ema26']:.5f}"
    )

with c:
    st.metric(
        "EMA50",
        f"{r['ema50']:.5f}"
    )

# =========================================================
# FILTERS
# =========================================================

st.write(
    f"🔎 {r['side']} • {r['filters']}"
)

# =========================================================
# AGE + CLOSED TIME
# =========================================================

if stale:

    st.caption(
        f"🕐 AGE {age:.0f}m • 🔒 {closed_time}"
    )

else:

    st.caption(
        f"🟢 AGE {age:.1f}m • 🔒 {closed_time}"
    )

# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH"
):

    st.cache_data.clear()
    st.rerun()

st.caption(
    "Manual • Closed Candle • No Auto Trading"
)
