import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# SIGNAL TERMINAL V2
# Analysis only — NO auto trading
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V2",
    page_icon="📊",
    layout="centered"
)

# ---------------------- UI ----------------------

st.markdown("""
<style>
.stApp {
    background: #0b0f19;
    color: white;
}

.block-container {
    max-width: 900px;
    padding-top: 1rem;
}

.card {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
    padding: 9px 12px;
    margin: 5px 0;
}

.signal-up,
.signal-down,
.signal-hold {
    padding: 14px;
    border-radius: 10px;
    text-align: center;
    font-weight: 900;
    font-size: 22px;
    margin: 8px 0;
}

.signal-up {
    background: #065f46;
    border: 1px solid #34d399;
}

.signal-down {
    background: #991b1b;
    border: 1px solid #f87171;
}

.signal-hold {
    background: #1f2937;
    border: 1px solid #fbbf24;
    color: #fbbf24;
}

.small {
    color: #9ca3af;
    font-size: 12px;
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
    "5 min": "5m",
    "15 min": "15m",
    "30 min": "30m",
    "1 hour": "60m",
}


# =========================================================
# HEADER
# =========================================================

st.title("📊 Signal Terminal V2")

st.caption(
    "Closed-candle analysis • No auto trading • "
    "No Martingale • No guaranteed profit"
)


# =========================================================
# PAIR + TIMEFRAME
# =========================================================

col1, col2 = st.columns(2)

with col1:
    selected_pair = st.selectbox(
        "Currency Pair",
        list(PAIRS.keys()),
        index=0
    )

with col2:
    selected_tf = st.selectbox(
        "Timeframe",
        list(TIMEFRAMES.keys()),
        index=0
    )


ticker = PAIRS[selected_pair]
interval = TIMEFRAMES[selected_tf]


# =========================================================
# REFRESH SETTINGS
# =========================================================

col3, col4 = st.columns(2)

with col3:
    auto_refresh = st.toggle(
        "Auto Refresh",
        value=True
    )

with col4:
    refresh_seconds = st.selectbox(
        "Refresh",
        [30, 60, 120, 300],
        index=1,
        format_func=lambda x: f"{x} seconds"
    )


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

        # New yfinance versions can return MultiIndex columns
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

    avg_loss = avg_loss.replace(0, np.nan)

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
    data["SMA20"] = close.rolling(20).mean()

    # RSI
    data["RSI"] = calculate_rsi(
        close,
        14
    )

    # MACD
    macd = (
        data["EMA12"]
        - data["EMA26"]
    )

    data["MACD"] = macd

    data["MACD_SIGNAL"] = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    # Bollinger Bands
    std = close.rolling(20).std()

    data["BB_UPPER"] = (
        data["SMA20"]
        + (2 * std)
    )

    data["BB_LOWER"] = (
        data["SMA20"]
        - (2 * std)
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

    # Candle structure
    candle_range = (
        high - low
    ).replace(0, np.nan)

    data["BODY_PCT"] = (
        (close - open_price).abs()
        / candle_range
    )

    # Where candle closed inside its range
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

    # -----------------------------------------------------
    # IMPORTANT:
    # Last row can still be forming.
    # We deliberately use the previous CLOSED candle.
    # -----------------------------------------------------

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

    bb_upper = float(
        candle["BB_UPPER"]
    )

    bb_lower = float(
        candle["BB_LOWER"]
    )

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
        and ema_gap >= (0.12 * atr)
    )

    # -----------------------------------------------------
    # MARKET REGIME
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

        market_state = "SIDEWAYS / UNCLEAR"


    # -----------------------------------------------------
    # REVERSAL CANDLE
    # -----------------------------------------------------

    bullish_reversal = (

        previous["Close"]
        < previous["Open"]

        and

        candle["Close"]
        > candle["Open"]

        and

        close_location >= 0.65

        and

        body_pct >= 0.35
    )


    bearish_reversal = (

        previous["Close"]
        > previous["Open"]

        and

        candle["Close"]
        < candle["Open"]

        and

        close_location <= 0.35

        and

        body_pct >= 0.35
    )


    # =====================================================
    # UP CHECKS
    # =====================================================

    up_checks = [

        (
            "Bullish reversal candle",
            bool(bullish_reversal)
        ),

        (
            "RSI recovering",
            bool(
                rsi > 35
                and rsi > float(previous["RSI"])
            )
        ),

        (
            "MACD improving",
            bool(
                macd > macd_signal
                and macd > float(previous["MACD"])
            )
        ),

        (
            "Price above SMA20",
            bool(
                close > sma20
            )
        ),

        (
            "Price above EMA12",
            bool(
                close > ema12
            )
        ),

        (
            "Usable volatility",
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
            "Bearish reversal candle",
            bool(bearish_reversal)
        ),

        (
            "RSI falling",
            bool(
                rsi < 65
                and rsi < float(previous["RSI"])
            )
        ),

        (
            "MACD weakening",
            bool(
                macd < macd_signal
                and macd < float(previous["MACD"])
            )
        ),

        (
            "Price below SMA20",
            bool(
                close < sma20
            )
        ),

        (
            "Price below EMA12",
            bool(
                close < ema12
            )
        ),

        (
            "Usable volatility",
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

    reason = (
        "Setup is not strong enough."
    )


    # Conservative rule:
    # Trend must agree AND minimum 5/6 checks.
    if (
        market_state == "UPTREND"
        and up_score >= 5
    ):

        signal = "UP"

        reason = (
            f"Trend + confirmation "
            f"({up_score}/6)"
        )


    elif (
        market_state == "DOWNTREND"
        and down_score >= 5
    ):

        signal = "DOWN"

        reason = (
            f"Trend + confirmation "
            f"({down_score}/6)"
        )


    elif market_state == "SIDEWAYS / UNCLEAR":

        reason = (
            "Sideways/unclear market "
            "— filtered."
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

        "bb_lower":
            bb_lower,

        "bb_upper":
            bb_upper,

        "closed_time":
            data.index[-2]
    }


# =========================================================
# LOAD DATA
# =========================================================

df = load_data(
    ticker,
    interval
)


if df is None:

    st.error(
        "⚠️ Market data unavailable. "
        "Try another timeframe or pair."
    )

    st.stop()


if len(df) < 100:

    st.error(
        "⚠️ Not enough candles "
        "for safe analysis."
    )

    st.stop()


result = analyze_market(df)


if result is None:

    st.error(
        "⚠️ Not enough clean data."
    )

    st.stop()


# =========================================================
# SIGNAL DISPLAY
# =========================================================

if result["signal"] == "UP":

    st.markdown(
        '<div class="signal-up">'
        '🟢 UP — CONFIRMED SETUP'
        '</div>',
        unsafe_allow_html=True
    )


elif result["signal"] == "DOWN":

    st.markdown(
        '<div class="signal-down">'
        '🔴 DOWN — CONFIRMED SETUP'
        '</div>',
        unsafe_allow_html=True
    )


else:

    st.markdown(
        '<div class="signal-hold">'
        '🛡️ NO TRADE — WAIT'
        '</div>',
        unsafe_allow_html=True
    )


# =========================================================
# MARKET STATUS
# =========================================================

st.markdown(
    f"""
    <div class="card">
        <b>Pair:</b> {selected_pair}<br>
        <b>Timeframe:</b> {selected_tf}<br>
        <b>Market:</b> {result["market_state"]}<br>
        <b>Reason:</b> {result["reason"]}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# INDICATORS
# =========================================================

st.markdown("### 📌 Indicators")


indicator_rows = [

    (
        "Current Price",
        f'{result["close"]:.5f}'
    ),

    (
        "SMA 20",
        f'{result["sma20"]:.5f}'
    ),

    (
        "EMA 12",
        f'{result["ema12"]:.5f}'
    ),

    (
        "EMA 26",
        f'{result["ema26"]:.5f}'
    ),

    (
        "EMA 50",
        f'{result["ema50"]:.5f}'
    ),

    (
        "RSI 14",
        f'{result["rsi"]:.1f}'
    ),

    (
        "MACD / Signal",
        f'{result["macd"]:.6f} / '
        f'{result["macd_signal"]:.6f}'
    ),

    (
        "ATR 14",
        f'{result["atr"]:.6f}'
    ),

    (
        "BB Lower / Upper",
        f'{result["bb_lower"]:.5f} / '
        f'{result["bb_upper"]:.5f}'
    )
]


for name, value in indicator_rows:

    st.markdown(
        f"""
        <div class="card">
            <span class="small">
                {name}
            </span>
            <br>
            <b>{value}</b>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# SIGNAL CHECKS
# =========================================================

st.markdown(
    "### 🔎 Signal Checks"
)


if result["signal"] == "UP":

    checks = result["up_checks"]


elif result["signal"] == "DOWN":

    checks = result["down_checks"]


else:

    # Show whichever direction currently has
    # stronger evidence, without issuing a signal.
    if (
        result["up_score"]
        >= result["down_score"]
    ):

        checks = result["up_checks"]

    else:

        checks = result["down_checks"]


for check_name, passed in checks:

    status = (
        "PASS ✅"
        if passed
        else
        "WAIT ❌"
    )

    st.markdown(
        f"""
        <div class="card">
            {check_name}
            <b style="float:right;">
                {status}
            </b>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# CLOSED CANDLE NOTICE
# =========================================================

st.markdown(
    f"""
    <div class="small">
        🔒 Signal calculated from CLOSED candle:
        {result["closed_time"]}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# MANUAL REFRESH
# =========================================================

if st.button(
    "🔄 Refresh Now",
    use_container_width=True
):

    st.cache_data.clear()

    st.rerun()


# =========================================================
# AUTO REFRESH
# =========================================================

if auto_refresh:

    st.markdown(
        f"""
        <meta
            http-equiv="refresh"
            content="{refresh_seconds}"
        >
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"🔄 Auto Refresh ON — "
        f"every {refresh_seconds} seconds"
    )

else:

    st.caption(
        "Auto Refresh OFF"
    )


# =========================================================
# SAFETY INFORMATION
# =========================================================

with st.expander(
    "⚠️ Important"
):

    st.write(
        """
        This terminal is an analysis/backtesting aid only.

        • No automatic trading
        • No Martingale
        • No guaranteed accuracy
        • No guaranteed profit
        • Weak/unclear markets are filtered
        • Signals use a closed candle
        • Demo testing should be done before any real-money use
        """
    )
