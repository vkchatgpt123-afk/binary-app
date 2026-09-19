import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V3
# Professional • Mobile • Closed Candle • Manual Analysis
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V3",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
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

header {visibility: hidden;}

h1, h2, h3, p {
    margin: 0 !important;
}

/* Selectboxes */
div[data-baseweb="select"] > div {
    background: #111827 !important;
    color: #ffffff !important;
    border: 1px solid #263244 !important;
    border-radius: 6px !important;
    min-height: 32px !important;
}

div[data-baseweb="select"] span {
    color: #ffffff !important;
    font-size: 11px !important;
}

/* Top Header */
.topbar {
    background: linear-gradient(135deg,#111827,#0b1220);
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 7px 8px;
    text-align: center;
    margin-bottom: 4px;
}

.brand {
    font-size: 15px;
    font-weight: 900;
    letter-spacing: .5px;
}

.subbrand {
    color: #94a3b8;
    font-size: 9px;
    margin-top: 2px;
}

/* Signal */
.signal {
    border-radius: 8px;
    padding: 9px 5px;
    text-align: center;
    font-size: 20px;
    font-weight: 900;
    letter-spacing: .5px;
    margin: 3px 0;
}

.up {
    background: #052e24;
    border: 1px solid #10b981;
    color: #6ee7b7;
}

.down {
    background: #3a1115;
    border: 1px solid #ef4444;
    color: #fca5a5;
}

.wait {
    background: #2b2108;
    border: 1px solid #f59e0b;
    color: #fbbf24;
}

/* Market status */
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
    margin-top: 2px;
}

/* Metrics */
.metric {
    background: #0f172a;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 5px 3px;
    text-align: center;
    margin-bottom: 3px;
}

.metric-title {
    color: #64748b;
    font-size: 8px;
    font-weight: 800;
}

.metric-value {
    color: #f8fafc;
    font-size: 11px;
    font-weight: 900;
}

/* Filter table */
.filter-head {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 5px;
    padding: 4px 6px;
    font-size: 9px;
    color: #94a3b8;
    text-align: center;
    margin-top: 2px;
}

.filter-row {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 4px 6px;
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
.footer {
    text-align: center;
    color: #475569;
    font-size: 8px;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


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


# =========================================================
# TOP CONTROLS
# =========================================================

c1, c2 = st.columns(2)

with c1:
    selected_pair = st.selectbox(
        "PAIR",
        list(PAIRS.keys()),
        label_visibility="collapsed"
    )

with c2:
    selected_tf = st.selectbox(
        "TIMEFRAME",
        list(TIMEFRAMES.keys()),
        label_visibility="collapsed"
    )

ticker = PAIRS[selected_pair]
interval = TIMEFRAMES[selected_tf]


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=20)
def load_data(symbol, interval_value):

    try:

        df = yf.download(
            symbol,
            period="7d",
            interval=interval_value,
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close"]

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

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze_market(df):

    if len(df) < 150:
        return None

    data = df.copy()

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    open_price = data["Open"]

    # -------------------------
    # TREND
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

    data["SMA20"] = close.rolling(20).mean()

    # -------------------------
    # RSI
    # -------------------------

    data["RSI"] = calculate_rsi(close, 14)

    # -------------------------
    # MACD
    # -------------------------

    data["MACD"] = data["EMA12"] - data["EMA26"]

    data["MACD_SIGNAL"] = data["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    data["MACD_HIST"] = (
        data["MACD"] -
        data["MACD_SIGNAL"]
    )

    # -------------------------
    # BOLLINGER
    # -------------------------

    data["BB_MID"] = data["SMA20"]

    std = close.rolling(20).std()

    data["BB_UPPER"] = (
        data["BB_MID"] + 2 * std
    )

    data["BB_LOWER"] = (
        data["BB_MID"] - 2 * std
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
    # CANDLE STRUCTURE
    # -------------------------

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

    # ------------------------------------------------
    # CLOSED CANDLE
    # -2 = last fully completed candle
    # ------------------------------------------------

    candle = data.iloc[-2]
    previous = data.iloc[-3]

    close_val = float(candle["Close"])

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
    close_location = float(candle["CLOSE_LOCATION"])

    # =================================================
    # ATR / TREND STRENGTH
    # =================================================

    ema_gap = abs(ema12 - ema26)

    trend_strength = (
        ema_gap / atr
        if atr > 0
        else 0
    )

    strong_trend = trend_strength >= 0.15

    # =================================================
    # MARKET REGIME
    # =================================================

    if (
        ema12 > ema26
        and close_val > ema50
        and strong_trend
    ):

        market_state = "UPTREND"

    elif (
        ema12 < ema26
        and close_val < ema50
        and strong_trend
    ):

        market_state = "DOWNTREND"

    else:

        market_state = "SIDEWAYS"

    # =================================================
    # MACD MOMENTUM
    # =================================================

    macd_bull = (
        macd > macd_signal
        and macd_hist > prev_hist
    )

    macd_bear = (
        macd < macd_signal
        and macd_hist < prev_hist
    )

    # Genuine crossover
    bullish_cross = (
        prev_macd <= prev_signal
        and macd > macd_signal
    )

    bearish_cross = (
        prev_macd >= prev_signal
        and macd < macd_signal
    )

    # =================================================
    # RSI
    # =================================================

    rsi_rising = (
        rsi > float(previous["RSI"])
    )

    rsi_falling = (
        rsi < float(previous["RSI"])
    )

    bullish_rsi = (
        45 <= rsi <= 68
        and rsi_rising
    )

    bearish_rsi = (
        32 <= rsi <= 55
        and rsi_falling
    )

    # =================================================
    # PRICE STRUCTURE
    # =================================================

    bullish_price = (
        close_val > ema12
        and close_val > sma20
    )

    bearish_price = (
        close_val < ema12
        and close_val < sma20
    )

    # =================================================
    # BOLLINGER POSITION
    # =================================================

    bullish_bb = (
        close_val > float(candle["BB_MID"])
        and close_val < bb_upper
    )

    bearish_bb = (
        close_val < float(candle["BB_MID"])
        and close_val > bb_lower
    )

    # Avoid buying/selling extreme BB expansion
    not_upper_extreme = close_val < bb_upper
    not_lower_extreme = close_val > bb_lower

    # =================================================
    # CANDLE CONFIRMATION
    # =================================================

    bullish_candle = (
        candle["Close"] > candle["Open"]
        and body_pct >= 0.45
        and close_location >= 0.65
    )

    bearish_candle = (
        candle["Close"] < candle["Open"]
        and body_pct >= 0.45
        and close_location <= 0.35
    )

    # =================================================
    # SCORE
    # =================================================

    up_checks = [

        ("Trend", market_state == "UPTREND"),

        (
            "EMA Structure",
            ema12 > ema26 > ema50
        ),

        (
            "RSI Momentum",
            bullish_rsi
        ),

        (
            "MACD Momentum",
            macd_bull
        ),

        (
            "Price > SMA20",
            bullish_price
        ),

        (
            "Bollinger",
            bullish_bb and not_upper_extreme
        ),

        (
            "Candle Strength",
            bullish_candle
        ),

        (
            "Volatility",
            atr > 0 and trend_strength >= 0.15
        )
    ]

    down_checks = [

        ("Trend", market_state == "DOWNTREND"),

        (
            "EMA Structure",
            ema12 < ema26 < ema50
        ),

        (
            "RSI Momentum",
            bearish_rsi
        ),

        (
            "MACD Momentum",
            macd_bear
        ),

        (
            "Price < SMA20",
            bearish_price
        ),

        (
            "Bollinger",
            bearish_bb and not_lower_extreme
        ),

        (
            "Candle Strength",
            bearish_candle
        ),

        (
            "Volatility",
            atr > 0 and trend_strength >= 0.15
        )
    ]

    up_score = sum(
        bool(value)
        for _, value in up_checks
    )

    down_score = sum(
        bool(value)
        for _, value in down_checks
    )

    # =================================================
    # SIGNAL ENGINE
    # =================================================

    signal = "NO TRADE"

    reason = "Waiting for stronger confirmation."

    # Strong setup only
    if (
        market_state == "UPTREND"
        and up_score >= 6
        and bullish_price
        and macd_bull
        and bullish_rsi
    ):

        signal = "UP"
        reason = (
            f"Strong bullish confirmation "
            f"{up_score}/8"
        )

    elif (
        market_state == "DOWNTREND"
        and down_score >= 6
        and bearish_price
        and macd_bear
        and bearish_rsi
    ):

        signal = "DOWN"
        reason = (
            f"Strong bearish confirmation "
            f"{down_score}/8"
        )

    elif market_state == "SIDEWAYS":

        reason = "Sideways market filtered."

    elif abs(up_score - down_score) <= 1:

        reason = "Signals are too balanced."

    # =================================================
    # RETURN
    # =================================================

    return {

        "signal": signal,
        "reason": reason,

        "market_state": market_state,

        "up_checks": up_checks,
        "down_checks": down_checks,

        "up_score": up_score,
        "down_score": down_score,

        "close": close_val,

        "ema12": ema12,
        "ema26": ema26,
        "ema50": ema50,

        "sma20": sma20,

        "rsi": rsi,

        "macd": macd,
        "macd_signal": macd_signal,

        "atr": atr,

        "trend_strength": trend_strength,

        "closed_time": data.index[-2]
    }


# =========================================================
# LOAD
# =========================================================

df = load_data(
    ticker,
    interval
)

if df is None or len(df) < 150:

    st.error(
        "⚠️ Market data unavailable."
    )

    st.stop()


result = analyze_market(df)

if result is None:

    st.error(
        "⚠️ Analysis error."
    )

    st.stop()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    f"""
    <div class="topbar">
        <div class="brand">
            📊 SIGNAL TERMINAL V3
        </div>

        <div class="subbrand">
            {selected_pair} • {selected_tf}
            • 🔒 CLOSED CANDLE
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SIGNAL
# =========================================================

sig = result["signal"]

if sig == "UP":

    st.markdown(
        '<div class="signal up">🟢 UP SIGNAL</div>',
        unsafe_allow_html=True
    )

elif sig == "DOWN":

    st.markdown(
        '<div class="signal down">🔴 DOWN SIGNAL</div>',
        unsafe_allow_html=True
    )

else:

    st.markdown(
        '<div class="signal wait">🛡️ NO TRADE</div>',
        unsafe_allow_html=True
    )


# =========================================================
# STATUS
# =========================================================

st.markdown(
    f"""
    <div class="status">

        <b>MARKET</b> :
        {result["market_state"]}

        &nbsp; | &nbsp;

        <b>UP</b> :
        {result["up_score"]}/8

        &nbsp; | &nbsp;

        <b>DOWN</b> :
        {result["down_score"]}/8

        <div class="reason">
            {result["reason"]}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# METRICS — SINGLE SCREEN
# =========================================================

r1c1, r1c2, r1c3 = st.columns(3)

with r1c1:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">PRICE</div>
            <div class="metric-value">
                {result["close"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with r1c2:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">RSI 14</div>
            <div class="metric-value">
                {result["rsi"]:.1f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with r1c3:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">ATR 14</div>
            <div class="metric-value">
                {result["atr"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


r2c1, r2c2, r2c3 = st.columns(3)

with r2c1:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">EMA 12</div>
            <div class="metric-value">
                {result["ema12"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with r2c2:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">EMA 26</div>
            <div class="metric-value">
                {result["ema26"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with r2c3:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">EMA 50</div>
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
    '<div class="filter-head">🔎 CONFIRMATION FILTERS</div>',
    unsafe_allow_html=True
)

if sig == "UP":

    checks = result["up_checks"]

elif sig == "DOWN":

    checks = result["down_checks"]

else:

    if result["up_score"] >= result["down_score"]:
        checks = result["up_checks"]
    else:
        checks = result["down_checks"]


for name, passed in checks:

    icon = "✓" if passed else "×"

    css = "pass" if passed else "fail"

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
    <div class="footer">
        Closed Candle: {result["closed_time"]}<br>
        Manual analysis only • No auto trading
    </div>
    """,
    unsafe_allow_html=True
)
