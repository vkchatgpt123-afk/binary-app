import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V3.4
# BRIGHT COLORFUL • MOBILE • SINGLE SCREEN
# CLOSED CANDLE • MANUAL ONLY • NO AUTO TRADING
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.4",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# BRIGHT MOBILE CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        135deg,
        #06111f 0%,
        #102a43 45%,
        #071a2b 100%
    );
}

.block-container {
    max-width: 430px;
    padding: 0.18rem 0.30rem 0.20rem 0.30rem;
}

/* TITLE */

h1 {
    color: #ffffff !important;
    font-size: 21px !important;
    font-weight: 900 !important;
    text-align: center;
    margin: 0 !important;
    padding: 0 !important;
}

p {
    margin: 2px 0 !important;
}

/* CAPTION */

[data-testid="stCaptionContainer"] {
    color: #b9eaff !important;
    font-size: 9px !important;
}

/* SELECT BOX */

div[data-baseweb="select"] {
    background-color: #13263a !important;
    border-radius: 8px !important;
}

div[data-testid="stSelectbox"] label {
    color: #7de8ff !important;
    font-size: 9px !important;
    font-weight: 900 !important;
}

/* METRICS */

div[data-testid="stMetric"] {
    background: linear-gradient(
        135deg,
        #102a43,
        #173f5f
    );
    border: 1px solid #35d9ff;
    border-radius: 9px;
    padding: 4px !important;
    min-height: 47px !important;
    box-shadow: 0 0 7px rgba(0,220,255,0.18);
}

div[data-testid="stMetricLabel"] {
    color: #7de8ff !important;
    font-size: 8px !important;
    font-weight: 800 !important;
}

div[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 900 !important;
}

/* ALERT BOX */

div[data-testid="stAlert"] {
    border-radius: 10px !important;
    padding: 7px !important;
    margin: 4px 0 !important;
    font-weight: 900 !important;
}

/* BUTTON */

div.stButton > button {
    width: 100%;
    min-height: 32px;
    border-radius: 9px;
    background: linear-gradient(
        90deg,
        #00d4ff,
        #007bff
    );
    color: white;
    border: 0;
    font-weight: 900;
}

/* REMOVE EXTRA SPACE */

hr {
    margin: 3px 0 !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📊 SIGNAL TERMINAL V3.4")
st.caption("⚡ BRIGHT MODE  •  🔒 CLOSED CANDLE  •  MANUAL ONLY")

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

        required = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        if not all(
            x in df.columns
            for x in required
        ):
            return None

        df = df[required].copy()

        df = df.dropna()

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

def calculate_rsi(
    close,
    period=14
):

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

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
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi.fillna(50)

# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if len(df) < 150:
        return None

    data = df.copy()

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    open_price = data["Open"]

    # EMA

    data["EMA12"] = close.ewm(
        span=12,
        adjust=False
    ).mean()

    data["EMA26"] = close.ewm(
        span=26,
        adjust=False
    ).mean()

    data["EMA50"] = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # SMA

    data["SMA20"] = close.rolling(
        20
    ).mean()

    # RSI

    data["RSI"] = calculate_rsi(
        close,
        14
    )

    # MACD

    data["MACD"] = (
        data["EMA12"]
        - data["EMA26"]
    )

    data["MACD_SIGNAL"] = (
        data["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    data["MACD_HIST"] = (
        data["MACD"]
        - data["MACD_SIGNAL"]
    )

    # Bollinger

    std = close.rolling(
        20
    ).std()

    data["BB_UPPER"] = (
        data["SMA20"]
        + 2 * std
    )

    data["BB_LOWER"] = (
        data["SMA20"]
        - 2 * std
    )

    # ATR

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (
                high - previous_close
            ).abs(),
            (
                low - previous_close
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    data["ATR14"] = tr.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14
    ).mean()

    # Candle strength

    candle_range = (
        high - low
    ).replace(
        0,
        np.nan
    )

    data["BODY_PCT"] = (
        (
            close - open_price
        ).abs()
        / candle_range
    )

    data["CLOSE_LOCATION"] = (
        (close - low)
        / candle_range
    )

    data = data.dropna()

    if len(data) < 100:
        return None

    # =====================================================
    # LAST CLOSED CANDLE
    # =====================================================

    candle = data.iloc[-2]
    previous = data.iloc[-3]

    price = float(
        candle["Close"]
    )

    ema12 = float(
        candle["EMA12"]
    )

    ema26 = float(
        candle["EMA26"]
    )

    ema50 = float(
        candle["EMA50"]
    )

    sma20 = float(
        candle["SMA20"]
    )

    rsi = float(
        candle["RSI"]
    )

    prev_rsi = float(
        previous["RSI"]
    )

    macd = float(
        candle["MACD"]
    )

    macd_signal = float(
        candle["MACD_SIGNAL"]
    )

    macd_hist = float(
        candle["MACD_HIST"]
    )

    prev_hist = float(
        previous["MACD_HIST"]
    )

    bb_upper = float(
        candle["BB_UPPER"]
    )

    bb_lower = float(
        candle["BB_LOWER"]
    )

    atr = float(
        candle["ATR14"]
    )

    body_pct = float(
        candle["BODY_PCT"]
    )

    close_location = float(
        candle["CLOSE_LOCATION"]
    )

    # =====================================================
    # TREND STRENGTH
    # =====================================================

    ema_gap = abs(
        ema12 - ema26
    )

    trend_strength = (
        ema_gap / atr
        if atr > 0
        else 0
    )

    strong_trend = (
        trend_strength >= 0.15
    )

    # =====================================================
    # MARKET
    # =====================================================

    if (
        ema12 > ema26
        and ema26 > ema50
        and price > ema50
        and strong_trend
    ):

        market = "UPTREND"

    elif (
        ema12 < ema26
        and ema26 < ema50
        and price < ema50
        and strong_trend
    ):

        market = "DOWNTREND"

    else:

        market = "SIDEWAYS"

    # =====================================================
    # UP
    # =====================================================

    up_filters = [

        (
            "T",
            market == "UPTREND"
        ),

        (
            "EMA",
            ema12 > ema26
            and ema26 > ema50
        ),

        (
            "RSI",
            45 <= rsi <= 68
            and rsi > prev_rsi
        ),

        (
            "MACD",
            macd > macd_signal
            and macd_hist > prev_hist
        ),

        (
            "P",
            price > ema12
            and price > sma20
        ),

        (
            "BB",
            price > sma20
            and price < bb_upper
        ),

        (
            "C",
            candle["Close"]
            > candle["Open"]
            and body_pct >= 0.45
            and close_location >= 0.65
        ),

        (
            "V",
            atr > 0
            and trend_strength >= 0.15
        )
    ]

    # =====================================================
    # DOWN
    # =====================================================

    down_filters = [

        (
            "T",
            market == "DOWNTREND"
        ),

        (
            "EMA",
            ema12 < ema26
            and ema26 < ema50
        ),

        (
            "RSI",
            32 <= rsi <= 55
            and rsi < prev_rsi
        ),

        (
            "MACD",
            macd < macd_signal
            and macd_hist < prev_hist
        ),

        (
            "P",
            price < ema12
            and price < sma20
        ),

        (
            "BB",
            price < sma20
            and price > bb_lower
        ),

        (
            "C",
            candle["Close"]
            < candle["Open"]
            and body_pct >= 0.45
            and close_location <= 0.35
        ),

        (
            "V",
            atr > 0
            and trend_strength >= 0.15
        )
    ]

    up_score = sum(
        value
        for _, value
        in up_filters
    )

    down_score = sum(
        value
        for _, value
        in down_filters
    )

    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = "Waiting for confirmation."

    if (
        market == "UPTREND"
        and up_score >= 6
        and up_filters[2][1]
        and up_filters[3][1]
        and up_filters[4][1]
    ):

        signal = "UP"

        reason = (
            f"Bullish setup {up_score}/8"
        )

    elif (
        market == "DOWNTREND"
        and down_score >= 6
        and down_filters[2][1]
        and down_filters[3][1]
        and down_filters[4][1]
    ):

        signal = "DOWN"

        reason = (
            f"Bearish setup {down_score}/8"
        )

    elif market == "SIDEWAYS":

        reason = (
            "Sideways → NO TRADE"
        )

    elif abs(
        up_score - down_score
    ) <= 1:

        reason = (
            "Signals too balanced"
        )

    # =====================================================
    # COMPACT FILTERS
    # =====================================================

    if signal == "UP":

        selected = up_filters
        direction = "UP"

    elif signal == "DOWN":

        selected = down_filters
        direction = "DOWN"

    else:

        if up_score >= down_score:

            selected = up_filters
            direction = "UP"

        else:

            selected = down_filters
            direction = "DOWN"

    compact_filters = "  ".join(
        f"{name}{'✓' if value else '×'}"
        for name, value
        in selected
    )

    return {
        "signal": signal,
        "reason": reason,
        "market": market,
        "up_score": up_score,
        "down_score": down_score,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "ema12": ema12,
        "ema26": ema26,
        "ema50": ema50,
        "filters": compact_filters,
        "direction": direction,
        "closed_time": data.index[-2]
    }

# =========================================================
# GET DATA
# =========================================================

df = get_data(
    symbol,
    interval
)

if df is None:

    st.error(
        "⚠️ MARKET DATA UNAVAILABLE"
    )

    st.stop()

if len(df) < 150:

    st.error(
        "⚠️ NOT ENOUGH CANDLES"
    )

    st.stop()

result = analyze(df)

if result is None:

    st.error(
        "⚠️ ANALYSIS ERROR"
    )

    st.stop()

# =========================================================
# DATA FRESHNESS
# =========================================================

closed_time = result["closed_time"]

try:

    if closed_time.tzinfo is None:

        closed_time = closed_time.replace(
            tzinfo=timezone.utc
        )

    now_utc = datetime.now(
        timezone.utc
    )

    age_minutes = (
        now_utc - closed_time
    ).total_seconds() / 60

except Exception:

    age_minutes = 999999

# =========================================================
# STALE DATA PROTECTION
# =========================================================

# Approximate maximum age allowed.
# If data is too old, block UP/DOWN.

if timeframe == "5m":
    max_age = 20
elif timeframe == "15m":
    max_age = 45
elif timeframe == "30m":
    max_age = 75
else:
    max_age = 150

data_stale = age_minutes > max_age

if data_stale:

    result["signal"] = "DATA STALE"

    result["reason"] = (
        f"Data is {age_minutes:.0f} min old"
    )

# =========================================================
# HEADER
# =========================================================

st.info(
    f"💱 **{pair}**   •   ⏱️ **{timeframe}**   •   🔒 **CLOSED**"
)

# =========================================================
# SIGNAL DISPLAY
# =========================================================

if result["signal"] == "UP":

    st.success(
        "🟢  UP SIGNAL"
    )

elif result["signal"] == "DOWN":

    st.error(
        "🔴  DOWN SIGNAL"
    )

elif result["signal"] == "DATA STALE":

    st.warning(
        "🕐  DATA STALE — NO SIGNAL"
    )

else:

    st.warning(
        "🛡️  NO TRADE"
    )

# =========================================================
# MARKET + SCORE
# =========================================================

st.write(
    f"🌐 **{result['market']}**   |   "
    f"🟢 UP **{result['up_score']}/8**   |   "
    f"🔴 DOWN **{result['down_score']}/8**"
)

st.caption(
    f"💡 {result['reason']}"
)

# =========================================================
# PRICE / RSI / ATR
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "💰 PRICE",
        f"{result['price']:.5f}"
    )

with b:
    st.metric(
        "📈 RSI",
        f"{result['rsi']:.1f}"
    )

with c:
    st.metric(
        "⚡ ATR",
        f"{result['atr']:.5f}"
    )

# =========================================================
# EMA
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "EMA12",
        f"{result['ema12']:.5f}"
    )

with b:
    st.metric(
        "EMA26",
        f"{result['ema26']:.5f}"
    )

with c:
    st.metric(
        "EMA50",
        f"{result['ema50']:.5f}"
    )

# =========================================================
# FILTERS
# =========================================================

st.write(
    f"🔎 **FILTERS — {result['direction']}**"
)

st.write(
    result["filters"]
)

st.caption(
    "T Trend • EMA Structure • RSI • MACD • "
    "P Price • BB Bollinger • C Candle • V Volatility"
)

# =========================================================
# DATA AGE
# =========================================================

if data_stale:

    st.warning(
        f"🕐 DATA AGE: {age_minutes:.0f} min — "
        f"signal blocked"
    )

else:

    st.caption(
        f"🟢 Data age: {age_minutes:.1f} min"
    )

# =========================================================
# CLOSED TIME
# =========================================================

st.caption(
    f"🔒 Closed candle: {closed_time}"
)

# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH MARKET"
):

    st.cache_data.clear()

    st.rerun()

st.caption(
    "⚠️ Manual analysis only • No auto trading"
)
