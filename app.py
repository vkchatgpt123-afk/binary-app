import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V3.2
# Native Streamlit UI - No HTML
# Closed Candle • Manual Analysis
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.2",
    page_icon="📊",
    layout="centered"
)

# =========================================================
# PAGE STYLE
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #070b12;
}

.block-container {
    max-width: 520px;
    padding: 0.4rem 0.5rem 0.6rem 0.5rem;
}

[data-testid="stMetric"] {
    background-color: #111827;
    border: 1px solid #263244;
    border-radius: 7px;
    padding: 5px;
}

[data-testid="stMetricLabel"] {
    font-size: 9px !important;
}

[data-testid="stMetricValue"] {
    font-size: 14px !important;
}

div.stButton > button {
    width: 100%;
    border-radius: 7px;
    font-weight: 800;
}

div[data-testid="stSelectbox"] {
    margin-bottom: -5px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# TITLE
# =========================================================

st.title("📊 SIGNAL TERMINAL V3.2")

st.caption(
    "Manual Analysis • Closed Candle • No Auto Trading"
)


# =========================================================
# PAIRS / TIMEFRAMES
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
        "TIMEFRAME",
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

        if not all(x in df.columns for x in needed):
            return None

        df = df[needed].copy()
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
        data["MACD"].ewm(
            span=9,
            adjust=False
        ).mean()
    )

    data["MACD_HIST"] = (
        data["MACD"]
        - data["MACD_SIGNAL"]
    )

    # Bollinger
    std = close.rolling(20).std()

    data["BB_UPPER"] = (
        data["SMA20"] + 2 * std
    )

    data["BB_LOWER"] = (
        data["SMA20"] - 2 * std
    )

    # ATR
    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    data["ATR14"] = tr.ewm(
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

    data["BODY_PCT"] = (
        (close - open_price).abs()
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
    # CLOSED CANDLE
    # =====================================================

    candle = data.iloc[-2]
    previous = data.iloc[-3]

    price = float(candle["Close"])

    ema12 = float(candle["EMA12"])
    ema26 = float(candle["EMA26"])
    ema50 = float(candle["EMA50"])

    sma20 = float(candle["SMA20"])

    rsi = float(candle["RSI"])
    prev_rsi = float(previous["RSI"])

    macd = float(candle["MACD"])
    signal_line = float(
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
    # MARKET STATE
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
    # UP CONDITIONS
    # =====================================================

    up_trend = (
        market == "UPTREND"
    )

    up_ema = (
        ema12 > ema26
        and ema26 > ema50
    )

    up_rsi = (
        45 <= rsi <= 68
        and rsi > prev_rsi
    )

    up_macd = (
        macd > signal_line
        and macd_hist > prev_hist
    )

    up_price = (
        price > ema12
        and price > sma20
    )

    up_bb = (
        price > sma20
        and price < bb_upper
    )

    up_candle = (
        candle["Close"]
        > candle["Open"]
        and body_pct >= 0.45
        and close_location >= 0.65
    )

    up_volatility = (
        atr > 0
        and trend_strength >= 0.15
    )

    # =====================================================
    # DOWN CONDITIONS
    # =====================================================

    down_trend = (
        market == "DOWNTREND"
    )

    down_ema = (
        ema12 < ema26
        and ema26 < ema50
    )

    down_rsi = (
        32 <= rsi <= 55
        and rsi < prev_rsi
    )

    down_macd = (
        macd < signal_line
        and macd_hist < prev_hist
    )

    down_price = (
        price < ema12
        and price < sma20
    )

    down_bb = (
        price < sma20
        and price > bb_lower
    )

    down_candle = (
        candle["Close"]
        < candle["Open"]
        and body_pct >= 0.45
        and close_location <= 0.35
    )

    down_volatility = (
        atr > 0
        and trend_strength >= 0.15
    )

    # =====================================================
    # FILTER LIST
    # =====================================================

    up_filters = [
        ("Trend", up_trend),
        ("EMA Structure", up_ema),
        ("RSI Momentum", up_rsi),
        ("MACD Momentum", up_macd),
        ("Price Structure", up_price),
        ("Bollinger Position", up_bb),
        ("Candle Strength", up_candle),
        ("Volatility", up_volatility)
    ]

    down_filters = [
        ("Trend", down_trend),
        ("EMA Structure", down_ema),
        ("RSI Momentum", down_rsi),
        ("MACD Momentum", down_macd),
        ("Price Structure", down_price),
        ("Bollinger Position", down_bb),
        ("Candle Strength", down_candle),
        ("Volatility", down_volatility)
    ]

    # Scores
    up_score = sum(
        value for _, value in up_filters
    )

    down_score = sum(
        value for _, value in down_filters
    )

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = (
        "Waiting for stronger confirmation."
    )

    if (
        market == "UPTREND"
        and up_score >= 6
        and up_rsi
        and up_macd
        and up_price
    ):

        signal = "UP"

        reason = (
            f"Strong bullish setup "
            f"{up_score}/8"
        )

    elif (
        market == "DOWNTREND"
        and down_score >= 6
        and down_rsi
        and down_macd
        and down_price
    ):

        signal = "DOWN"

        reason = (
            f"Strong bearish setup "
            f"{down_score}/8"
        )

    elif market == "SIDEWAYS":

        reason = (
            "Sideways market filtered."
        )

    elif abs(
        up_score - down_score
    ) <= 1:

        reason = (
            "Signals too balanced."
        )

    # =====================================================
    # RETURN
    # =====================================================

    return {
        "signal": signal,
        "reason": reason,
        "market": market,

        "up_score": up_score,
        "down_score": down_score,

        "up_filters": up_filters,
        "down_filters": down_filters,

        "price": price,
        "ema12": ema12,
        "ema26": ema26,
        "ema50": ema50,
        "sma20": sma20,

        "rsi": rsi,
        "atr": atr,

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
        "⚠️ Market data unavailable."
    )

    st.stop()

if len(df) < 150:

    st.error(
        "⚠️ Not enough candle data."
    )

    st.stop()

result = analyze(df)

if result is None:

    st.error(
        "⚠️ Analysis error."
    )

    st.stop()


# =========================================================
# MARKET HEADER
# =========================================================

st.info(
    f"**{pair}**  •  **{timeframe}**  •  🔒 CLOSED CANDLE"
)


# =========================================================
# SIGNAL
# =========================================================

if result["signal"] == "UP":

    st.success(
        "🟢 UP SIGNAL"
    )

elif result["signal"] == "DOWN":

    st.error(
        "🔴 DOWN SIGNAL"
    )

else:

    st.warning(
        "🛡️ NO TRADE"
    )


# =========================================================
# STATUS
# =========================================================

st.write(
    f"**MARKET:** {result['market']}   |   "
    f"**UP:** {result['up_score']}/8   |   "
    f"**DOWN:** {result['down_score']}/8"
)

st.caption(
    result["reason"]
)


# =========================================================
# METRICS
# =========================================================

m1, m2, m3 = st.columns(3)

with m1:
    st.metric(
        "PRICE",
        f"{result['price']:.5f}"
    )

with m2:
    st.metric(
        "RSI 14",
        f"{result['rsi']:.1f}"
    )

with m3:
    st.metric(
        "ATR 14",
        f"{result['atr']:.5f}"
    )


m4, m5, m6 = st.columns(3)

with m4:
    st.metric(
        "EMA 12",
        f"{result['ema12']:.5f}"
    )

with m5:
    st.metric(
        "EMA 26",
        f"{result['ema26']:.5f}"
    )

with m6:
    st.metric(
        "EMA 50",
        f"{result['ema50']:.5f}"
    )


# =========================================================
# FILTERS
# =========================================================

st.subheader(
    "🔎 Confirmation Filters"
)

if result["signal"] == "UP":

    filters = result["up_filters"]

elif result["signal"] == "DOWN":

    filters = result["down_filters"]

else:

    if (
        result["up_score"]
        >= result["down_score"]
    ):
        filters = result["up_filters"]
        direction = "UP"
    else:
        filters = result["down_filters"]
        direction = "DOWN"

    st.caption(
        f"Showing stronger side: {direction}"
    )


for name, passed in filters:

    if passed:

        st.write(
            f"✅ {name}"
        )

    else:

        st.write(
            f"❌ {name}"
        )


# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH MARKET"
):

    st.cache_data.clear()

    st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.caption(
    f"Closed candle: {result['closed_time']}"
)

st.caption(
    "Manual analysis only • No auto trading"
)
