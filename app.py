import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V3.5
# COMPACT • BRIGHT • FULL INFORMATION
# CLOSED CANDLE • MANUAL ONLY
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.5",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# COMPACT BRIGHT DESIGN
# =========================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top, #12395a 0%, #07111d 55%, #03070c 100%);
}

.block-container {
    max-width: 420px;
    padding: 0.12rem 0.20rem 0.15rem 0.20rem;
}

h1 {
    font-size: 18px !important;
    text-align: center !important;
    margin: 0 !important;
    padding: 0 !important;
    color: #ffffff !important;
}

p {
    margin: 0 !important;
    line-height: 1.05 !important;
}

[data-testid="stCaptionContainer"] {
    font-size: 8px !important;
    line-height: 1 !important;
    color: #bdefff !important;
}

[data-testid="stSelectbox"] {
    margin-bottom: -13px !important;
}

[data-testid="stSelectbox"] label {
    font-size: 8px !important;
    font-weight: 900 !important;
    color: #4de7ff !important;
}

div[data-baseweb="select"] {
    min-height: 30px !important;
    border-radius: 7px !important;
    background: #10263a !important;
}

div[data-testid="stMetric"] {
    min-height: 42px !important;
    padding: 2px 3px !important;
    margin: 0 !important;
    border-radius: 7px !important;
    border: 1px solid #25d9ff !important;
    background: linear-gradient(135deg,#102b45,#123b59) !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 7px !important;
    line-height: 1 !important;
    color: #67eaff !important;
}

div[data-testid="stMetricValue"] {
    font-size: 12px !important;
    line-height: 1.1 !important;
    color: white !important;
}

div[data-testid="stAlert"] {
    min-height: 32px !important;
    padding: 5px 7px !important;
    margin: 3px 0 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 900 !important;
}

div.stButton > button {
    min-height: 28px !important;
    padding: 1px !important;
    border-radius: 7px !important;
    font-size: 10px !important;
    font-weight: 900 !important;
    background: linear-gradient(90deg,#00c6ff,#0072ff) !important;
    color: white !important;
}

hr {
    margin: 2px 0 !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📊 SIGNAL TERMINAL V3.5")

# =========================================================
# SETTINGS
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

        needed = ["Open", "High", "Low", "Close"]

        if not all(x in df.columns for x in needed):
            return None

        df = df[needed].dropna()

        df = df.loc[
            ~df.index.duplicated(keep="last")
        ]

        return df

    except Exception:
        return None

# =========================================================
# RSI
# =========================================================

def rsi_calc(close, period=14):

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

    rs = avg_gain / avg_loss.replace(
        0, np.nan
    )

    return (
        100 - 100 / (1 + rs)
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
    d["SMA20"] = close.rolling(20).mean()

    # RSI
    d["RSI"] = rsi_calc(close)

    # MACD
    d["MACD"] = (
        d["EMA12"] - d["EMA26"]
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
        d["MACD"] - d["MACD_SIGNAL"]
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

    # LAST CLOSED CANDLE
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

    gap = abs(ema12 - ema26)

    trend_strength = (
        gap / atr
        if atr > 0
        else 0
    )

    strong = trend_strength >= 0.15

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
    # FILTERS
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
        and trend_strength >= 0.15
    ]

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
        and trend_strength >= 0.15
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

    elif abs(up_score - down_score) <= 1:

        reason = "Signals balanced"

    # strongest side
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
        for n, x in zip(names, selected)
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
    st.error("⚠️ DATA UNAVAILABLE")
    st.stop()

if len(df) < 150:
    st.error("⚠️ NOT ENOUGH DATA")
    st.stop()

r = analyze(df)

if r is None:
    st.error("⚠️ ANALYSIS ERROR")
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
    f"💱 {pair}  •  ⏱️ {timeframe}  •  🔒 CLOSED"
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
        "🟢  UP SIGNAL"
    )

elif r["signal"] == "DOWN":

    st.error(
        "🔴  DOWN SIGNAL"
    )

else:

    st.warning(
        "🛡️  NO TRADE"
    )

# =========================================================
# MARKET / SCORE
# =========================================================

st.write(
    f"🌐 **{r['market']}**  |  "
    f"🟢 **{r['up']}/8**  |  "
    f"🔴 **{r['down']}/8**  |  "
    f"💡 {r['reason']}"
)

# =========================================================
# MAIN METRICS
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "💰 PRICE",
        f"{r['price']:.5f}"
    )

with b:
    st.metric(
        "📈 RSI",
        f"{r['rsi']:.1f}"
    )

with c:
    st.metric(
        "⚡ ATR",
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
    f"🔎 **{r['side']} FILTERS:** {r['filters']}"
)

# =========================================================
# DATA STATUS + TIME
# =========================================================

if stale:

    st.caption(
        f"🕐 AGE {age:.0f}m • "
        f"🔒 {closed_time}"
    )

else:

    st.caption(
        f"🟢 AGE {age:.1f}m • "
        f"🔒 {closed_time}"
    )

# =========================================================
# REFRESH
# =========================================================

if st.button("🔄 REFRESH MARKET"):

    st.cache_data.clear()
    st.rerun()

st.caption(
    "Manual analysis • No auto trading • "
    "Signal is not a profit guarantee"
)
