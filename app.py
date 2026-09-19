import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V3.3
# TRUE SINGLE-SCREEN MOBILE
# Closed Candle • Manual Analysis • No Auto Trading
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.3",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# COMPACT MOBILE STYLE
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #070b12;
}

.block-container {
    max-width: 430px;
    padding: 0.20rem 0.30rem 0.20rem 0.30rem;
}

h1 {
    font-size: 20px !important;
    margin: 0 !important;
    padding: 0 !important;
}

h2, h3 {
    margin: 0 !important;
    padding: 0 !important;
}

p {
    margin: 2px 0 !important;
}

div[data-testid="stMetric"] {
    padding: 3px !important;
    min-height: 48px !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 8px !important;
}

div[data-testid="stMetricValue"] {
    font-size: 14px !important;
}

div.stButton > button {
    width: 100%;
    min-height: 32px;
    padding: 2px 5px;
    font-size: 12px;
    font-weight: 700;
}

div[data-testid="stSelectbox"] {
    margin-bottom: -10px;
}

.stAlert {
    padding: 7px !important;
    margin: 4px 0 !important;
}

hr {
    margin: 4px 0 !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📊 SIGNAL TERMINAL V3.3")
st.caption("Manual • Closed Candle • No Auto Trading")

# =========================================================
# PAIR / TIMEFRAME
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
        list(PAIRS.keys()),
        index=0
    )

with c2:
    timeframe = st.selectbox(
        "TIME",
        list(TIMEFRAMES.keys()),
        index=0
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

    # -------------------------
    # EMA
    # -------------------------

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

    # -------------------------
    # SMA
    # -------------------------

    data["SMA20"] = close.rolling(20).mean()

    # -------------------------
    # RSI
    # -------------------------

    data["RSI"] = calculate_rsi(
        close,
        14
    )

    # -------------------------
    # MACD
    # -------------------------

    data["MACD"] = (
        data["EMA12"] -
        data["EMA26"]
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
        data["MACD"] -
        data["MACD_SIGNAL"]
    )

    # -------------------------
    # Bollinger Bands
    # -------------------------

    std = close.rolling(20).std()

    data["BB_UPPER"] = (
        data["SMA20"] +
        2 * std
    )

    data["BB_LOWER"] = (
        data["SMA20"] -
        2 * std
    )

    # -------------------------
    # ATR
    # -------------------------

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

    # -------------------------
    # Candle
    # -------------------------

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

    # IMPORTANT:
    # -1 = currently forming candle
    # -2 = last CLOSED candle

    candle = data.iloc[-2]

    previous = data.iloc[-3]

    # =====================================================
    # VALUES
    # =====================================================

    price = float(candle["Close"])

    ema12 = float(candle["EMA12"])

    ema26 = float(candle["EMA26"])

    ema50 = float(candle["EMA50"])

    sma20 = float(candle["SMA20"])

    rsi = float(candle["RSI"])

    prev_rsi = float(previous["RSI"])

    macd = float(candle["MACD"])

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
    # MARKET REGIME
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
    # UP FILTERS
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
        macd > macd_signal
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
        candle["Close"] >
        candle["Open"]
        and body_pct >= 0.45
        and close_location >= 0.65
    )

    up_volatility = (
        atr > 0
        and trend_strength >= 0.15
    )

    # =====================================================
    # DOWN FILTERS
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
        macd < macd_signal
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
        candle["Close"] <
        candle["Open"]
        and body_pct >= 0.45
        and close_location <= 0.35
    )

    down_volatility = (
        atr > 0
        and trend_strength >= 0.15
    )

    # =====================================================
    # SCORE
    # =====================================================

    up_filters = [
        up_trend,
        up_ema,
        up_rsi,
        up_macd,
        up_price,
        up_bb,
        up_candle,
        up_volatility
    ]

    down_filters = [
        down_trend,
        down_ema,
        down_rsi,
        down_macd,
        down_price,
        down_bb,
        down_candle,
        down_volatility
    ]

    up_score = sum(up_filters)

    down_score = sum(down_filters)

    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = "Waiting for confirmation."

    if (
        market == "UPTREND"
        and up_score >= 6
        and up_rsi
        and up_macd
        and up_price
    ):

        signal = "UP"

        reason = (
            f"Bullish confirmation {up_score}/8"
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
            f"Bearish confirmation {down_score}/8"
        )

    elif market == "SIDEWAYS":

        reason = (
            "Sideways market — NO TRADE"
        )

    elif abs(
        up_score - down_score
    ) <= 1:

        reason = (
            "Signals too balanced"
        )

    # =====================================================
    # FILTER COMPACT SYMBOLS
    # =====================================================

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

    if signal == "UP":

        active_filters = up_filters
        direction = "UP"

    elif signal == "DOWN":

        active_filters = down_filters
        direction = "DOWN"

    else:

        if up_score >= down_score:

            active_filters = up_filters
            direction = "UP"

        else:

            active_filters = down_filters
            direction = "DOWN"

    compact_filters = " ".join(
        f"{name}{'✓' if value else '×'}"
        for name, value in zip(
            names,
            active_filters
        )
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
        "sma20": sma20,
        "closed_time": data.index[-2],
        "filters": compact_filters,
        "direction": direction
    }


# =========================================================
# LOAD DATA
# =========================================================

df = get_data(
    symbol,
    interval
)

if df is None:

    st.error(
        "⚠️ Market data unavailable"
    )

    st.stop()

if len(df) < 150:

    st.error(
        "⚠️ Not enough candle data"
    )

    st.stop()

result = analyze(df)

if result is None:

    st.error(
        "⚠️ Analysis error"
    )

    st.stop()


# =========================================================
# TERMINAL
# =========================================================

st.info(
    f"**{pair}**  •  **{timeframe}**  •  🔒 CLOSED"
)

# =========================================================
# SIGNAL
# =========================================================

if result["signal"] == "UP":

    st.success("🟢  UP SIGNAL")

elif result["signal"] == "DOWN":

    st.error("🔴  DOWN SIGNAL")

else:

    st.warning("🛡️  NO TRADE")


# =========================================================
# MARKET + SCORE
# =========================================================

st.write(
    f"**{result['market']}**   "
    f"| UP **{result['up_score']}/8** "
    f"| DOWN **{result['down_score']}/8**"
)

st.caption(
    result["reason"]
)

# =========================================================
# COMPACT METRICS
# =========================================================

a, b, c = st.columns(3)

with a:
    st.metric(
        "PRICE",
        f"{result['price']:.5f}"
    )

with b:
    st.metric(
        "RSI",
        f"{result['rsi']:.1f}"
    )

with c:
    st.metric(
        "ATR",
        f"{result['atr']:.5f}"
    )


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
# COMPACT FILTERS
# =========================================================

st.write(
    f"**FILTERS ({result['direction']})**"
)

st.caption(
    "T=Trend • EMA=Structure • RSI=Momentum • "
    "MACD=Momentum • P=Price • BB=Bollinger • "
    "C=Candle • V=Volatility"
)

st.write(
    result["filters"]
)

# =========================================================
# CLOSED CANDLE
# =========================================================

closed_time = result["closed_time"]

st.caption(
    f"🔒 Closed: {closed_time}"
)

# =========================================================
# REFRESH
# =========================================================

if st.button("🔄 REFRESH"):

    st.cache_data.clear()

    st.rerun()

st.caption(
    "Manual analysis only • No auto trading"
)
