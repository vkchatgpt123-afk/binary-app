import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# 📊 SIGNAL TERMINAL V3.1
# Closed Candle • Manual Analysis • Mobile Professional UI
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3.1",
    page_icon="📊",
    layout="centered"
)

# =========================================================
# PROFESSIONAL MOBILE CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #070b12;
    color: #f8fafc;
}

.block-container {
    max-width: 500px;
    padding: 0.25rem 0.45rem 0.5rem 0.45rem !important;
}

/* Hide Streamlit header/footer */
header {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

/* Select boxes */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    color: white !important;
    border: 1px solid #263244 !important;
    border-radius: 6px !important;
    min-height: 32px !important;
}

div[data-baseweb="select"] span {
    color: white !important;
    font-size: 11px !important;
}

/* Main Header */
.top {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 7px;
    text-align: center;
    margin-bottom: 4px;
}

.title {
    color: white;
    font-size: 15px;
    font-weight: 900;
}

.subtitle {
    color: #94a3b8;
    font-size: 9px;
    margin-top: 2px;
}

/* Signal */
.signal {
    border-radius: 8px;
    padding: 9px;
    text-align: center;
    font-size: 20px;
    font-weight: 900;
    margin: 3px 0;
}

.signal-up {
    background: #052e24;
    border: 1px solid #10b981;
    color: #6ee7b7;
}

.signal-down {
    background: #3a1115;
    border: 1px solid #ef4444;
    color: #fca5a5;
}

.signal-wait {
    background: #2b2108;
    border: 1px solid #f59e0b;
    color: #fbbf24;
}

/* Status */
.status {
    background: #0f172a;
    border: 1px solid #263244;
    border-radius: 7px;
    padding: 6px;
    text-align: center;
    font-size: 10px;
    margin-bottom: 4px;
}

.reason {
    color: #94a3b8;
    font-size: 9px;
    margin-top: 3px;
}

/* Metric */
.metric {
    background: #0f172a;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 5px 2px;
    text-align: center;
    margin-bottom: 3px;
}

.metric-title {
    color: #64748b;
    font-size: 8px;
    font-weight: 800;
}

.metric-value {
    color: white;
    font-size: 11px;
    font-weight: 900;
}

/* Filter heading */
.filter-title {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 5px;
    padding: 5px;
    text-align: center;
    color: #cbd5e1;
    font-size: 9px;
    font-weight: 900;
    margin-top: 2px;
}

/* Filter rows */
.filter-row {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 4px 7px;
    margin-top: 2px;
    font-size: 9px;
    display: flex;
    justify-content: space-between;
}

.pass {
    color: #6ee7b7;
    font-weight: 900;
}

.fail {
    color: #fca5a5;
    font-weight: 900;
}

/* Footer */
.small-footer {
    color: #475569;
    text-align: center;
    font-size: 8px;
    margin-top: 4px;
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
# SELECTORS
# =========================================================

col1, col2 = st.columns(2)

with col1:
    pair = st.selectbox(
        "PAIR",
        list(PAIRS.keys()),
        index=0
    )

with col2:
    timeframe = st.selectbox(
        "TIMEFRAME",
        list(TIMEFRAMES.keys()),
        index=0
    )

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]


# =========================================================
# DATA DOWNLOAD
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

        # Fix MultiIndex returned by some yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        if not all(x in df.columns for x in required):
            return None

        df = df[required].copy()

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

def rsi_calculation(close, period=14):

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

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze(df):

    if len(df) < 150:
        return None

    data = df.copy()

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    open_price = data["Open"]

    # -----------------------------------------------------
    # EMA
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SMA
    # -----------------------------------------------------

    data["SMA20"] = close.rolling(20).mean()

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    data["RSI"] = rsi_calculation(close, 14)

    # -----------------------------------------------------
    # MACD
    # -----------------------------------------------------

    data["MACD"] = (
        data["EMA12"] -
        data["EMA26"]
    )

    data["MACD_SIGNAL"] = data["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    data["MACD_HIST"] = (
        data["MACD"] -
        data["MACD_SIGNAL"]
    )

    # -----------------------------------------------------
    # BOLLINGER
    # -----------------------------------------------------

    std = close.rolling(20).std()

    data["BB_UPPER"] = (
        data["SMA20"] + 2 * std
    )

    data["BB_LOWER"] = (
        data["SMA20"] - 2 * std
    )

    # -----------------------------------------------------
    # ATR
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # CANDLE STRUCTURE
    # -----------------------------------------------------

    candle_range = (
        high - low
    ).replace(0, np.nan)

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

    # -----------------------------------------------------
    # LAST COMPLETED CANDLE
    # -----------------------------------------------------

    candle = data.iloc[-2]
    previous = data.iloc[-3]

    # -----------------------------------------------------
    # VALUES
    # -----------------------------------------------------

    price = float(candle["Close"])

    ema12 = float(candle["EMA12"])
    ema26 = float(candle["EMA26"])
    ema50 = float(candle["EMA50"])

    sma20 = float(candle["SMA20"])

    rsi = float(candle["RSI"])

    macd = float(candle["MACD"])
    macd_signal = float(candle["MACD_SIGNAL"])
    macd_hist = float(candle["MACD_HIST"])

    prev_macd = float(previous["MACD"])
    prev_signal = float(previous["MACD_SIGNAL"])
    prev_hist = float(previous["MACD_HIST"])

    bb_upper = float(candle["BB_UPPER"])
    bb_lower = float(candle["BB_LOWER"])

    atr = float(candle["ATR14"])

    body_pct = float(candle["BODY_PCT"])

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
    # RSI
    # =====================================================

    previous_rsi = float(
        previous["RSI"]
    )

    up_rsi = (
        rsi >= 45
        and rsi <= 68
        and rsi > previous_rsi
    )

    down_rsi = (
        rsi >= 32
        and rsi <= 55
        and rsi < previous_rsi
    )

    # =====================================================
    # MACD
    # =====================================================

    up_macd = (
        macd > macd_signal
        and macd_hist > prev_hist
    )

    down_macd = (
        macd < macd_signal
        and macd_hist < prev_hist
    )

    # Actual crossover
    bullish_cross = (
        prev_macd <= prev_signal
        and macd > macd_signal
    )

    bearish_cross = (
        prev_macd >= prev_signal
        and macd < macd_signal
    )

    # =====================================================
    # PRICE STRUCTURE
    # =====================================================

    up_price = (
        price > ema12
        and price > sma20
    )

    down_price = (
        price < ema12
        and price < sma20
    )

    # =====================================================
    # EMA STRUCTURE
    # =====================================================

    up_ema = (
        ema12 > ema26
        and ema26 > ema50
    )

    down_ema = (
        ema12 < ema26
        and ema26 < ema50
    )

    # =====================================================
    # BOLLINGER
    # =====================================================

    up_bb = (
        price > sma20
        and price < bb_upper
    )

    down_bb = (
        price < sma20
        and price > bb_lower
    )

    # =====================================================
    # CANDLE
    # =====================================================

    bullish_candle = (
        candle["Close"] >
        candle["Open"]
        and body_pct >= 0.45
        and close_location >= 0.65
    )

    bearish_candle = (
        candle["Close"] <
        candle["Open"]
        and body_pct >= 0.45
        and close_location <= 0.35
    )

    # =====================================================
    # VOLATILITY
    # =====================================================

    volatility = (
        atr > 0
        and trend_strength >= 0.15
    )

    # =====================================================
    # UP FILTERS
    # =====================================================

    up_filters = [

        ("Trend", market == "UPTREND"),

        ("EMA Structure", up_ema),

        ("RSI Momentum", up_rsi),

        ("MACD Momentum", up_macd),

        ("Price Structure", up_price),

        ("Bollinger Position", up_bb),

        ("Candle Strength", bullish_candle),

        ("Volatility", volatility)
    ]

    # =====================================================
    # DOWN FILTERS
    # =====================================================

    down_filters = [

        ("Trend", market == "DOWNTREND"),

        ("EMA Structure", down_ema),

        ("RSI Momentum", down_rsi),

        ("MACD Momentum", down_macd),

        ("Price Structure", down_price),

        ("Bollinger Position", down_bb),

        ("Candle Strength", bearish_candle),

        ("Volatility", volatility)
    ]

    # =====================================================
    # SCORE
    # =====================================================

    up_score = sum(
        1 for _, x in up_filters
        if x
    )

    down_score = sum(
        1 for _, x in down_filters
        if x
    )

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = (
        "Waiting for stronger confirmation."
    )

    # Strong UP
    if (
        market == "UPTREND"
        and up_score >= 6
        and up_rsi
        and up_macd
        and up_price
    ):

        signal = "UP"

        reason = (
            f"Bullish confirmation "
            f"{up_score}/8"
        )

    # Strong DOWN
    elif (
        market == "DOWNTREND"
        and down_score >= 6
        and down_rsi
        and down_macd
        and down_price
    ):

        signal = "DOWN"

        reason = (
            f"Bearish confirmation "
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

        "trend_strength": trend_strength,

        "bullish_cross": bullish_cross,

        "bearish_cross": bearish_cross,

        "closed_time": data.index[-2]
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
        "⚠️ Analysis failed."
    )

    st.stop()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    f"""
    <div class="top">

        <div class="title">
            📊 SIGNAL TERMINAL V3.1
        </div>

        <div class="subtitle">
            {pair} • {timeframe}
            • 🔒 CLOSED CANDLE
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SIGNAL BOX
# =========================================================

if result["signal"] == "UP":

    st.markdown(
        """
        <div class="signal signal-up">
            🟢 UP SIGNAL
        </div>
        """,
        unsafe_allow_html=True
    )

elif result["signal"] == "DOWN":

    st.markdown(
        """
        <div class="signal signal-down">
            🔴 DOWN SIGNAL
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="signal signal-wait">
            🛡️ NO TRADE
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# STATUS
# =========================================================

st.markdown(
    f"""
    <div class="status">

        MARKET :
        <b>{result["market"]}</b>

        &nbsp; | &nbsp;

        UP :
        <b>{result["up_score"]}/8</b>

        &nbsp; | &nbsp;

        DOWN :
        <b>{result["down_score"]}/8</b>

        <div class="reason">
            {result["reason"]}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# METRICS
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                PRICE
            </div>

            <div class="metric-value">
                {result["price"]:.5f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

with c2:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                RSI 14
            </div>

            <div class="metric-value">
                {result["rsi"]:.1f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

with c3:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                ATR 14
            </div>

            <div class="metric-value">
                {result["atr"]:.5f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


c4, c5, c6 = st.columns(3)

with c4:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                EMA 12
            </div>

            <div class="metric-value">
                {result["ema12"]:.5f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

with c5:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                EMA 26
            </div>

            <div class="metric-value">
                {result["ema26"]:.5f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

with c6:

    st.markdown(
        f"""
        <div class="metric">

            <div class="metric-title">
                EMA 50
            </div>

            <div class="metric-value">
                {result["ema50"]:.5f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# FILTERS
# =========================================================

st.markdown(
    """
    <div class="filter-title">
        🔎 CONFIRMATION FILTERS
    </div>
    """,
    unsafe_allow_html=True
)


if result["signal"] == "DOWN":

    filters = result["down_filters"]

elif result["signal"] == "UP":

    filters = result["up_filters"]

else:

    # For NO TRADE choose the direction
    # with stronger score.
    if result["up_score"] >= result["down_score"]:

        filters = result["up_filters"]

    else:

        filters = result["down_filters"]


for name, passed in filters:

    if passed:

        icon = "✓"
        css = "pass"

    else:

        icon = "×"
        css = "fail"

    st.markdown(
        f"""
        <div class="filter-row">

            <span>{name}</span>

            <span class="{css}">
                {icon}
            </span>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH MARKET",
    use_container_width=True
):

    st.cache_data.clear()

    st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    f"""
    <div class="small-footer">

        Closed Candle:
        {result["closed_time"]}

        <br>

        Manual analysis • No auto trading

    </div>
    """,
    unsafe_allow_html=True
)
