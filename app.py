import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V2 — COMPACT MOBILE
# Analysis only — NO auto trading
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V2",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# COMPACT PROFESSIONAL UI
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #080c14;
    color: #ffffff;
}

.block-container {
    max-width: 620px;
    padding-top: 0.45rem;
    padding-bottom: 0.5rem;
    padding-left: 0.65rem;
    padding-right: 0.65rem;
}

h1 {
    font-size: 1.35rem !important;
    margin-bottom: 0.15rem !important;
}

h2 {
    font-size: 1rem !important;
}

h3 {
    font-size: 0.9rem !important;
}

p {
    margin-bottom: 0.25rem !important;
}

.small {
    color: #9ca3af;
    font-size: 10px;
}

.topbar {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 9px;
    padding: 7px 9px;
    margin: 4px 0;
    font-size: 12px;
}

.signal {
    padding: 13px 8px;
    border-radius: 11px;
    text-align: center;
    font-weight: 900;
    font-size: 27px;
    margin: 6px 0;
}

.signal-up {
    background: #064e3b;
    border: 1px solid #10b981;
    color: #6ee7b7;
}

.signal-down {
    background: #7f1d1d;
    border: 1px solid #ef4444;
    color: #fca5a5;
}

.signal-hold {
    background: #27220d;
    border: 1px solid #f59e0b;
    color: #fbbf24;
}

.status-card {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 9px;
    padding: 7px 9px;
    margin: 4px 0;
    font-size: 11px;
}

.metric {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 6px 5px;
    text-align: center;
    margin: 2px 0;
}

.metric-label {
    color: #9ca3af;
    font-size: 9px;
}

.metric-value {
    font-size: 13px;
    font-weight: 800;
}

.check {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 7px;
    padding: 5px 7px;
    margin: 2px 0;
    font-size: 10px;
}

.footer {
    color: #6b7280;
    font-size: 9px;
    text-align: center;
    margin-top: 5px;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.15rem;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.35rem;
}

button {
    min-height: 34px !important;
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
    "GBP/JPY": "GBPJPY=X",
}


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "60m",
}


# =========================================================
# HEADER
# =========================================================

st.markdown(
    "### 📊 SIGNAL TERMINAL V2"
)

st.markdown(
    '<div class="small">Closed-candle analysis • Manual use only</div>',
    unsafe_allow_html=True
)


# =========================================================
# PAIR + TIMEFRAME
# =========================================================

col1, col2 = st.columns([1.5, 1])

with col1:
    selected_pair = st.selectbox(
        "Pair",
        list(PAIRS.keys()),
        index=0,
        label_visibility="collapsed"
    )

with col2:
    selected_tf = st.selectbox(
        "TF",
        list(TIMEFRAMES.keys()),
        index=0,
        label_visibility="collapsed"
    )

ticker = PAIRS[selected_pair]
interval = TIMEFRAMES[selected_tf]


# =========================================================
# DATA LOADER
# =========================================================

@st.cache_data(ttl=45)
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

        df = df[
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

    avg_loss = avg_loss.replace(
        0,
        np.nan
    )

    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi.fillna(50)


# =========================================================
# INDICATORS
# =========================================================

def calculate_indicators(df):

    data = df.copy()

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    open_price = data["Open"]

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

    data["SMA20"] = close.rolling(
        20
    ).mean()

    data["RSI"] = calculate_rsi(
        close,
        14
    )

    macd = (
        data["EMA12"]
        - data["EMA26"]
    )

    data["MACD"] = macd

    data["MACD_SIGNAL"] = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    std = close.rolling(
        20
    ).std()

    data["BB_UPPER"] = (
        data["SMA20"]
        + (2 * std)
    )

    data["BB_LOWER"] = (
        data["SMA20"]
        - (2 * std)
    )

    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    data["ATR14"] = true_range.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14
    ).mean()

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

    return data.dropna()


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze_market(df):

    if len(df) < 100:
        return None

    data = calculate_indicators(df)

    if len(data) < 80:
        return None

    # CLOSED CANDLE
    candle = data.iloc[-2]
    previous = data.iloc[-3]

    close = float(candle["Close"])

    ema12 = float(candle["EMA12"])
    ema26 = float(candle["EMA26"])
    ema50 = float(candle["EMA50"])

    sma20 = float(candle["SMA20"])

    rsi = float(candle["RSI"])

    macd = float(candle["MACD"])
    macd_signal = float(
        candle["MACD_SIGNAL"]
    )

    atr = float(candle["ATR14"])

    body_pct = float(
        candle["BODY_PCT"]
    )

    close_location = float(
        candle["CLOSE_LOCATION"]
    )

    # -----------------------------------------------------
    # TREND STRENGTH
    # -----------------------------------------------------

    ema_gap = abs(
        ema12 - ema26
    )

    strong_trend = (
        atr > 0
        and ema_gap >= (
            0.12 * atr
        )
    )

    # -----------------------------------------------------
    # MARKET STATE
    # -----------------------------------------------------

    if (
        ema12 > ema26
        and close > ema50
        and strong_trend
    ):

        market_state = "UPTREND"

    elif (
        ema12 < ema26
        and close < ema50
        and strong_trend
    ):

        market_state = "DOWNTREND"

    else:

        market_state = "SIDEWAYS"


    # -----------------------------------------------------
    # REVERSAL CANDLE
    # -----------------------------------------------------

    bullish_reversal = (

        previous["Close"]
        < previous["Open"]

        and candle["Close"]
        > candle["Open"]

        and close_location >= 0.65

        and body_pct >= 0.35
    )


    bearish_reversal = (

        previous["Close"]
        > previous["Open"]

        and candle["Close"]
        < candle["Open"]

        and close_location <= 0.35

        and body_pct >= 0.35
    )


    # =====================================================
    # UP CHECKS
    # =====================================================

    up_checks = [

        (
            "Reversal",
            bool(bullish_reversal)
        ),

        (
            "RSI",
            bool(
                rsi > 35
                and rsi >
                float(previous["RSI"])
            )
        ),

        (
            "MACD",
            bool(
                macd > macd_signal
                and macd >
                float(previous["MACD"])
            )
        ),

        (
            "SMA20",
            bool(
                close > sma20
            )
        ),

        (
            "EMA12",
            bool(
                close > ema12
            )
        ),

        (
            "Volatility",
            bool(
                atr > 0
            )
        )
    ]


    # =====================================================
    # DOWN CHECKS
    # =====================================================

    down_checks = [

        (
            "Reversal",
            bool(bearish_reversal)
        ),

        (
            "RSI",
            bool(
                rsi < 65
                and rsi <
                float(previous["RSI"])
            )
        ),

        (
            "MACD",
            bool(
                macd < macd_signal
                and macd <
                float(previous["MACD"])
            )
        ),

        (
            "SMA20",
            bool(
                close < sma20
            )
        ),

        (
            "EMA12",
            bool(
                close < ema12
            )
        ),

        (
            "Volatility",
            bool(
                atr > 0
            )
        )
    ]


    up_score = sum(
        passed
        for _, passed in up_checks
    )

    down_score = sum(
        passed
        for _, passed in down_checks
    )


    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = "Waiting for stronger setup."

    if (
        market_state == "UPTREND"
        and up_score >= 5
    ):

        signal = "UP"

        reason = (
            f"UP setup {up_score}/6"
        )

    elif (
        market_state == "DOWNTREND"
        and down_score >= 5
    ):

        signal = "DOWN"

        reason = (
            f"DOWN setup {down_score}/6"
        )

    elif market_state == "SIDEWAYS":

        reason = (
            "Sideways market filtered"
        )


    return {

        "signal": signal,

        "reason": reason,

        "market_state":
            market_state,

        "up_checks":
            up_checks,

        "down_checks":
            down_checks,

        "up_score":
            up_score,

        "down_score":
            down_score,

        "close":
            close,

        "sma20":
            sma20,

        "ema12":
            ema12,

        "ema26":
            ema26,

        "ema50":
            ema50,

        "rsi":
            rsi,

        "macd":
            macd,

        "macd_signal":
            macd_signal,

        "atr":
            atr,

        "closed_time":
            data.index[-2]
    }


# =========================================================
# LOAD
# =========================================================

df = load_data(
    ticker,
    interval
)

if df is None:

    st.error(
        "⚠️ Market data unavailable."
    )

    st.stop()

if len(df) < 100:

    st.error(
        "⚠️ Not enough candles."
    )

    st.stop()

result = analyze_market(df)

if result is None:

    st.error(
        "⚠️ Analysis unavailable."
    )

    st.stop()


# =========================================================
# TOP STATUS
# =========================================================

st.markdown(
    f"""
    <div class="topbar">
        <b>{selected_pair}</b>
        &nbsp; • &nbsp;
        <b>{selected_tf}</b>
        &nbsp; • &nbsp;
        CLOSED CANDLE
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# MAIN SIGNAL
# =========================================================

if result["signal"] == "UP":

    st.markdown(
        """
        <div class="signal signal-up">
            🟢 UP
        </div>
        """,
        unsafe_allow_html=True
    )

elif result["signal"] == "DOWN":

    st.markdown(
        """
        <div class="signal signal-down">
            🔴 DOWN
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="signal signal-hold">
            🛡️ NO TRADE
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# MARKET + SCORE
# =========================================================

if result["signal"] == "UP":

    score_text = (
        f'UP {result["up_score"]}/6'
    )

elif result["signal"] == "DOWN":

    score_text = (
        f'DOWN {result["down_score"]}/6'
    )

else:

    score_text = (
        f'UP {result["up_score"]}/6'
        f' • '
        f'DOWN {result["down_score"]}/6'
    )


st.markdown(
    f"""
    <div class="status-card">
        <b>Market:</b> {result["market_state"]}
        &nbsp;&nbsp; | &nbsp;&nbsp;
        <b>Score:</b> {score_text}
        <br>
        <span class="small">
            {result["reason"]}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# KEY NUMBERS ONLY
# =========================================================

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">PRICE</div>
            <div class="metric-value">
                {result["close"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">RSI</div>
            <div class="metric-value">
                {result["rsi"]:.1f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">EMA12</div>
            <div class="metric-value">
                {result["ema12"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m4:
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">EMA26</div>
            <div class="metric-value">
                {result["ema26"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# SIGNAL CHECKS — ONLY WHEN NEEDED
# =========================================================

with st.expander("🔎 Signal Checks"):

    if result["signal"] == "UP":
        checks = result["up_checks"]

    elif result["signal"] == "DOWN":
        checks = result["down_checks"]

    else:

        if (
            result["up_score"]
            >= result["down_score"]
        ):
            checks = result["up_checks"]
        else:
            checks = result["down_checks"]


    for name, passed in checks:

        status = (
            "✅"
            if passed
            else
            "—"
        )

        st.markdown(
            f"""
            <div class="check">
                {status} {name}
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# CLOSED CANDLE TIME
# =========================================================

st.markdown(
    f"""
    <div class="footer">
        🔒 Closed candle:
        {result["closed_time"]}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# REFRESH
# =========================================================

c1, c2 = st.columns(2)

with c1:

    if st.button(
        "🔄 Refresh",
        use_container_width=True
    ):

        st.cache_data.clear()
        st.rerun()

with c2:

    auto_refresh = st.toggle(
        "Auto",
        value=True
    )


# =========================================================
# AUTO REFRESH
# =========================================================

if auto_refresh:

    refresh_seconds = 60

    st.markdown(
        f"""
        <meta
            http-equiv="refresh"
            content="{refresh_seconds}"
        >
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="footer">🔄 Auto: 60s</div>',
        unsafe_allow_html=True
    )


# =========================================================
# SAFETY
# =========================================================

with st.expander("⚠️ Safety"):

    st.write(
        """
        Analysis only.

        • No auto trading
        • No Martingale
        • No guaranteed profit
        • Closed-candle signal
        • Sideways market filtered
        • Demo testing first

        Data source: Yahoo Finance.
        This is not Quotex OTC feed data.
        """
    )
