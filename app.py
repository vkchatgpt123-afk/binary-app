import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V2 — CLEAN MOBILE
# Analysis only — NO auto trading
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V2",
    page_icon="📊",
    layout="centered"
)

# =========================================================
# MOBILE UI
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #080c14;
    color: white;
}

.block-container {
    max-width: 520px;
    padding: 0.45rem 0.55rem 0.5rem 0.55rem;
}

h1 {
    font-size: 1.15rem !important;
    margin: 0 !important;
    padding: 0 !important;
}

h2, h3 {
    margin: 0.25rem 0 !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.18rem;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.3rem;
}

/* TOP BAR */

.topbar {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 6px 8px;
    margin: 3px 0;
    text-align: center;
    font-size: 12px;
}

/* SIGNAL */

.signal {
    border-radius: 10px;
    padding: 12px 5px;
    margin: 5px 0;
    text-align: center;
    font-size: 28px;
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
    background: #29220b;
    border: 1px solid #f59e0b;
    color: #fbbf24;
}

/* STATUS */

.status {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 7px 8px;
    margin: 4px 0;
    text-align: center;
    font-size: 11px;
}

.reason {
    color: #9ca3af;
    font-size: 10px;
}

/* METRICS */

.metric {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 7px;
    padding: 5px 2px;
    text-align: center;
}

.metric-title {
    color: #9ca3af;
    font-size: 8px;
}

.metric-value {
    color: white;
    font-size: 12px;
    font-weight: bold;
}

/* CHECK */

.check {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 5px 7px;
    margin: 2px 0;
    font-size: 10px;
}

/* FOOTER */

.footer {
    color: #6b7280;
    text-align: center;
    font-size: 9px;
    margin-top: 4px;
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
    "GBP/JPY": "GBPJPY=X"
}


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "60m"
}


# =========================================================
# HEADER
# =========================================================

st.markdown(
    "<h1>📊 SIGNAL TERMINAL V2</h1>",
    unsafe_allow_html=True
)

st.markdown(
    '<div class="footer">Closed-candle analysis • Manual use only</div>',
    unsafe_allow_html=True
)


# =========================================================
# PAIR + TIMEFRAME
# =========================================================

c1, c2 = st.columns([1.5, 1])

with c1:
    selected_pair = st.selectbox(
        "Pair",
        list(PAIRS.keys()),
        index=0
    )

with c2:
    selected_tf = st.selectbox(
        "TF",
        list(TIMEFRAMES.keys()),
        index=0
    )

ticker = PAIRS[selected_pair]
interval = TIMEFRAMES[selected_tf]


# =========================================================
# DATA
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

        if not all(
            col in df.columns
            for col in required
        ):
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

    return data.dropna()


# =========================================================
# ANALYSIS
# =========================================================

def analyze_market(df):

    if len(df) < 100:
        return None

    data = calculate_indicators(df)

    if len(data) < 80:
        return None

    # CLOSED CANDLE ONLY

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

    # =====================================================
    # TREND
    # =====================================================

    ema_gap = abs(
        ema12 - ema26
    )

    strong_trend = (
        atr > 0
        and ema_gap >= (
            0.12 * atr
        )
    )

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


    # =====================================================
    # REVERSAL
    # =====================================================

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
    # UP
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
    # DOWN
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
    # SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = "Waiting for stronger setup."

    if (
        market_state == "UPTREND"
        and up_score >= 5
    ):

        signal = "UP"

        reason = (
            f"UP confirmation {up_score}/6"
        )

    elif (
        market_state == "DOWNTREND"
        and down_score >= 5
    ):

        signal = "DOWN"

        reason = (
            f"DOWN confirmation {down_score}/6"
        )

    elif market_state == "SIDEWAYS":

        reason = (
            "Sideways market filtered."
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

        "rsi":
            rsi,

        "ema12":
            ema12,

        "ema26":
            ema26,

        "ema50":
            ema50,

        "sma20":
            sma20,

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
# RUN
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
# PAIR / TF
# =========================================================

st.markdown(
    f"""
    <div class="topbar">
        <b>{selected_pair}</b>
        &nbsp; • &nbsp;
        <b>{selected_tf}</b>
        &nbsp; • &nbsp;
        🔒 CLOSED
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SIGNAL
# =========================================================

if result["signal"] == "UP":

    st.markdown(
        '<div class="signal up">🟢 UP</div>',
        unsafe_allow_html=True
    )

elif result["signal"] == "DOWN":

    st.markdown(
        '<div class="signal down">🔴 DOWN</div>',
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

if result["signal"] == "UP":

    score = (
        f'UP {result["up_score"]}/6'
    )

elif result["signal"] == "DOWN":

    score = (
        f'DOWN {result["down_score"]}/6'
    )

else:

    score = (
        f'UP {result["up_score"]}/6'
        f' • '
        f'DOWN {result["down_score"]}/6'
    )


st.markdown(
    f"""
    <div class="status">
        <b>Market:</b> {result["market_state"]}
        &nbsp; | &nbsp;
        <b>Score:</b> {score}
        <br>
        <span class="reason">
            {result["reason"]}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# KEY DATA
# =========================================================

a, b, c, d = st.columns(4)

with a:

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

with b:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">RSI</div>
            <div class="metric-value">
                {result["rsi"]:.1f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">EMA12</div>
            <div class="metric-value">
                {result["ema12"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with d:

    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-title">EMA26</div>
            <div class="metric-value">
                {result["ema26"]:.5f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# CHECKS
# =========================================================

with st.expander("🔎 Checks"):

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

        icon = "✅" if passed else "—"

        st.markdown(
            f"""
            <div class="check">
                {icon} {name}
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


# =========================================================
# TIME
# =========================================================

st.markdown(
    f"""
    <div class="footer">
        Closed candle: {result["closed_time"]}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SAFETY
# =========================================================

with st.expander("⚠️ Safety"):

    st.write(
        """
        Analysis only.

        • No automatic trading
        • No Martingale
        • No guaranteed profit
        • Closed-candle analysis
        • Sideways market filtered
        • Demo testing first

        Data source: Yahoo Finance.
        Yahoo data is not Quotex OTC feed data.
        """
    )
