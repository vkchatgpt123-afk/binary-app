import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V4.9.9
# MOBILE SINGLE-SCREEN VERSION
# MANUAL SIGNAL ONLY — NO AUTO TRADING
# =========================================================

st.set_page_config(
    page_title="Signal Terminal V4.9.9",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# MOBILE CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background:
    radial-gradient(circle at top,
    #183e68 0%,
    #08182d 48%,
    #02060d 100%);
    color: white;
}

.block-container {
    max-width: 430px !important;
    padding: 0.25rem 0.35rem 0.35rem !important;
}

header[data-testid="stHeader"] {
    height: 0 !important;
    visibility: hidden !important;
}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    display: none !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.22rem !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.28rem !important;
    align-items: stretch !important;
}

div[data-testid="column"] {
    padding: 0 !important;
    min-width: 0 !important;
}

/* =====================================================
   PAIR + TIMEFRAME REAL SINGLE BOX
   ===================================================== */

div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #64ffda !important;
    border-radius: 8px !important;
    background: rgba(17,34,64,.96) !important;
    padding: 0.30rem !important;
}

/* =====================================================
   SELECTBOX
   ===================================================== */

.stSelectbox label {
    color: #64ffda !important;
    font-size: 8px !important;
    font-weight: 800 !important;
    margin-bottom: 1px !important;
}

div[data-baseweb="select"] > div {
    background: #07182f !important;
    border: 1px solid #64ffda !important;
    border-radius: 5px !important;
    min-height: 31px !important;
}

div[data-baseweb="select"] span {
    color: white !important;
    font-size: 10px !important;
    font-weight: 800 !important;
}

/* =====================================================
   SIGNAL BOX
   ===================================================== */

.signal {
    width: 100%;
    box-sizing: border-box;
    border-radius: 10px;
    padding: 11px 6px;
    text-align: center;
    font-size: 20px;
    font-weight: 950;
    letter-spacing: 0.8px;
    margin: 0;
    box-shadow: 0 0 20px rgba(100,255,218,.25);
}

.signal-up {
    background: linear-gradient(135deg,#00a884,#73c93d);
    border: 2px solid #64ffda;
    color: #00150e;
}

.signal-down {
    background: linear-gradient(135deg,#ff315e,#ff5a24);
    border: 2px solid #ff806b;
    color: white;
}

.signal-wait {
    background: linear-gradient(135deg,#f0ad25,#e94b20);
    border: 2px solid #ffd166;
    color: #111;
}

.signal-closed {
    background: linear-gradient(135deg,#53657d,#27364b);
    border: 2px solid #8fa5bf;
    color: white;
}

/* =====================================================
   MARKET STATUS
   ===================================================== */

.status {
    text-align: center;
    background: #102342;
    border: 1px solid #64ffda;
    border-radius: 7px;
    padding: 5px 3px;
    font-size: 10px;
    font-weight: 850;
    margin: 0;
}

.reason {
    color: #a8b2d1;
    font-size: 8px;
    font-weight: 600;
    margin-top: 2px;
}

/* =====================================================
   METRICS 3 x 2
   ===================================================== */

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 4px;
}

.metric {
    background: #102342;
    border: 1px solid #4ee8cf;
    border-radius: 6px;
    padding: 5px 2px;
    text-align: center;
}

.metric-title {
    color: #8892b0;
    font-size: 7px;
    font-weight: 800;
}

.metric-value {
    color: white;
    font-size: 10px;
    font-weight: 900;
    line-height: 1.2;
}

/* =====================================================
   INDICATORS 4 x 2
   ===================================================== */

.ind-title {
    text-align: center;
    color: #64ffda;
    font-size: 9px;
    font-weight: 900;
    margin-bottom: 3px;
}

.ind-grid {
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 3px;
}

.ind {
    background: #0c1d38;
    border: 1px solid #304d70;
    border-radius: 5px;
    padding: 4px 1px;
    text-align: center;
}

.ind-name {
    color: #8892b0;
    font-size: 6.5px;
    font-weight: 800;
}

.ind-icon {
    font-size: 13px;
    line-height: 14px;
}

/* =====================================================
   BUTTONS
   ===================================================== */

.stButton > button {
    min-height: 31px !important;
    border: 1px solid #64ffda !important;
    border-radius: 7px !important;
    background: #0d203b !important;
    color: white !important;
    font-size: 10px !important;
    font-weight: 900 !important;
    padding: 2px 5px !important;
}

.stButton > button:hover {
    border-color: white !important;
    color: #64ffda !important;
}

/* =====================================================
   FOOTER
   ===================================================== */

.footer {
    text-align: center;
    color: #7f8ca8;
    font-size: 7px;
    line-height: 1.15;
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
# PAIR + TIMEFRAME
# ONE REAL BOX
# =========================================================

with st.container(border=True):

    col1, col2 = st.columns(2)

    with col1:
        pair = st.selectbox(
            "PAIR",
            list(PAIRS.keys()),
            index=0,
            key="pair_v499"
        )

    with col2:
        timeframe = st.selectbox(
            "TIMEFRAME",
            list(TIMEFRAMES.keys()),
            index=0,
            key="tf_v499"
        )


symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]


# =========================================================
# DATA DOWNLOAD
# =========================================================

@st.cache_data(ttl=20, show_spinner=False)
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

        # Handle yfinance MultiIndex
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

        df = df.apply(
            pd.to_numeric,
            errors="coerce"
        ).dropna()

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

    return (
        100 - 100 / (1 + rs)
    ).fillna(50)


# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if df is None:
        return None

    if len(df) < 150:
        return None

    d = df.copy()

    close = d["Close"]
    high = d["High"]
    low = d["Low"]
    op = d["Open"]


    # =====================================================
    # EMA
    # =====================================================

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


    # =====================================================
    # SMA
    # =====================================================

    d["SMA20"] = close.rolling(20).mean()


    # =====================================================
    # RSI
    # =====================================================

    d["RSI"] = calculate_rsi(close)


    # =====================================================
    # MACD
    # =====================================================

    d["MACD"] = (
        d["EMA12"] -
        d["EMA26"]
    )

    d["MACD_SIGNAL"] = d["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    d["MACD_HIST"] = (
        d["MACD"] -
        d["MACD_SIGNAL"]
    )


    # =====================================================
    # BOLLINGER BANDS
    # =====================================================

    std = close.rolling(20).std()

    d["BB_UPPER"] = (
        d["SMA20"] +
        2 * std
    )

    d["BB_LOWER"] = (
        d["SMA20"] -
        2 * std
    )


    # =====================================================
    # ATR
    # =====================================================

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


    # =====================================================
    # CANDLE DATA
    # =====================================================

    candle_range = (
        high - low
    ).replace(
        0,
        np.nan
    )

    d["BODY"] = (
        (close - op).abs() /
        candle_range
    )

    d["LOCATION"] = (
        (close - low) /
        candle_range
    )


    d = d.dropna()


    if len(d) < 100:
        return None


    # =====================================================
    # IMPORTANT:
    # LAST ROW MAY BE FORMING.
    # USE PREVIOUS COMPLETED CANDLE.
    # =====================================================

    c = d.iloc[-2]

    p = d.iloc[-3]


    # =====================================================
    # VALUES
    # =====================================================

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
    # TREND STRENGTH
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


    # =====================================================
    # MARKET STATE
    # =====================================================

    if (
        ema12 > ema26
        and
        ema26 > ema50
        and
        price > ema50
        and
        strong
    ):

        market = "UPTREND"

    elif (
        ema12 < ema26
        and
        ema26 < ema50
        and
        price < ema50
        and
        strong
    ):

        market = "DOWNTREND"

    else:

        market = "SIDEWAYS"


    # =====================================================
    # UP CONDITIONS
    # =====================================================

    up = [

        market == "UPTREND",

        ema12 > ema26
        and
        ema26 > ema50,

        45 <= rsi <= 68
        and
        rsi > prev_rsi,

        macd > macd_sig
        and
        hist > prev_hist,

        price > ema12
        and
        price > sma20,

        price > sma20
        and
        price < bb_up,

        bool(c["Close"] > c["Open"])
        and
        body >= 0.45
        and
        location >= 0.65,

        atr > 0
        and
        strength >= 0.15
    ]


    # =====================================================
    # DOWN CONDITIONS
    # =====================================================

    down = [

        market == "DOWNTREND",

        ema12 < ema26
        and
        ema26 < ema50,

        32 <= rsi <= 55
        and
        rsi < prev_rsi,

        macd < macd_sig
        and
        hist < prev_hist,

        price < ema12
        and
        price < sma20,

        price < sma20
        and
        price > bb_low,

        bool(c["Close"] < c["Open"])
        and
        body >= 0.45
        and
        location <= 0.35,

        atr > 0
        and
        strength >= 0.15
    ]


    # =====================================================
    # SCORES
    # =====================================================

    up_score = sum(up)

    down_score = sum(down)


    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "NO TRADE"

    reason = "Confirmation incomplete"


    if (
        market == "UPTREND"
        and
        up_score >= 6
        and
        up[2]
        and
        up[3]
        and
        up[4]
    ):

        signal = "UP"

        reason = "Bullish confirmation"


    elif (
        market == "DOWNTREND"
        and
        down_score >= 6
        and
        down[2]
        and
        down[3]
        and
        down[4]
    ):

        signal = "DOWN"

        reason = "Bearish confirmation"


    elif market == "SIDEWAYS":

        reason = "Sideways market — WAIT"


    elif abs(
        up_score - down_score
    ) <= 1:

        reason = "Signals balanced"


    # =====================================================
    # SELECT INDICATOR SIDE
    # =====================================================

    if market == "DOWNTREND":

        side = "DOWN"

        selected = down

    elif market == "UPTREND":

        side = "UP"

        selected = up

    else:

        if up_score >= down_score:

            side = "UP"

            selected = up

        else:

            side = "DOWN"

            selected = down


    # =====================================================
    # INDICATORS
    # =====================================================

    names = [
        "Trend",
        "EMA",
        "RSI",
        "MACD",
        "Price",
        "BB",
        "Candle",
        "Strength"
    ]


    indicators = []


    for name, status in zip(
        names,
        selected
    ):

        icon = (
            "✅"
            if status
            else
            "❌"
        )

        indicators.append(
            f"""
            <div class="ind">
                <div class="ind-name">
                    {name}
                </div>

                <div class="ind-icon">
                    {icon}
                </div>
            </div>
            """
        )


    return {

        "signal": signal,

        "reason": reason,

        "market": market,

        "up": up_score,

        "down": down_score,

        "side": side,

        "indicators":
            "".join(indicators),

        "price": price,

        "rsi": rsi,

        "atr": atr,

        "ema12": ema12,

        "ema26": ema26,

        "ema50": ema50,

        "time": d.index[-2]
    }


# =========================================================
# GET DATA
# =========================================================

df = get_data(
    symbol,
    interval
)


# =========================================================
# DATA ERROR
# =========================================================

if (
    df is None
    or
    len(df) < 150
):

    st.markdown(
        """
        <div class="signal signal-wait">
            ⚠️ DATA UNAVAILABLE
            <div style="font-size:8px;margin-top:3px;">
                NO SIGNAL
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# ANALYZE
# =========================================================

r = analyze(df)


if r is None:

    st.markdown(
        """
        <div class="signal signal-wait">
            ⚠️ ANALYSIS ERROR
            <div style="font-size:8px;margin-top:3px;">
                NO SIGNAL
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# CANDLE AGE
# =========================================================

closed_time = r["time"]


try:

    if closed_time.tzinfo is None:

        closed_time = (
            closed_time.replace(
                tzinfo=timezone.utc
            )
        )

    now_utc = datetime.now(
        timezone.utc
    )

    age = max(
        0,
        (
            now_utc -
            closed_time
        ).total_seconds()
        / 60
    )

except Exception:

    age = 999999


# =========================================================
# MARKET STATUS
# =========================================================

weekend = (
    datetime.now(
        timezone.utc
    ).weekday() >= 5
)


max_age = {

    "5m": 20,

    "15m": 45,

    "30m": 75,

    "1H": 150

}[timeframe]


stale = age > max_age


# =========================================================
# FINAL DISPLAY SIGNAL
# =========================================================

if weekend:

    display_signal = "🔒 MARKET CLOSED"

    signal_class = "signal-closed"

    signal_reason = (
        "Weekend — NO SIGNAL"
    )


elif stale:

    display_signal = "🕐 DATA STALE"

    signal_class = "signal-wait"

    signal_reason = (
        "Fresh candle unavailable"
    )


elif r["signal"] == "UP":

    display_signal = "🟢 UP SIGNAL"

    signal_class = "signal-up"

    signal_reason = r["reason"]


elif r["signal"] == "DOWN":

    display_signal = "🔴 DOWN SIGNAL"

    signal_class = "signal-down"

    signal_reason = r["reason"]


else:

    display_signal = "🛡️ NO TRADE"

    signal_class = "signal-wait"

    signal_reason = r["reason"]


# =========================================================
# BIG SIGNAL BOX
# =========================================================

st.markdown(
    f"""
    <div class="signal {signal_class}">

        {display_signal}

        <div style="
            font-size:8px;
            font-weight:700;
            letter-spacing:0;
            margin-top:3px;
        ">

            {signal_reason}

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# MARKET STATUS
# =========================================================

st.markdown(
    f"""
    <div class="status">

        <b>{r["market"]}</b>

        &nbsp;|&nbsp;

        🟢 {r["up"]}/8

        &nbsp;•&nbsp;

        🔴 {r["down"]}/8

        <div class="reason">
            {signal_reason}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# METRICS 3 x 2
# =========================================================

st.markdown(
    f"""
    <div class="metric-grid">

        <div class="metric">
            <div class="metric-title">
                PRICE
            </div>
            <div class="metric-value">
                {r["price"]:.5f}
            </div>
        </div>


        <div class="metric">
            <div class="metric-title">
                RSI
            </div>
            <div class="metric-value">
                {r["rsi"]:.1f}
            </div>
        </div>


        <div class="metric">
            <div class="metric-title">
                ATR
            </div>
            <div class="metric-value">
                {r["atr"]:.5f}
            </div>
        </div>


        <div class="metric">
            <div class="metric-title">
                EMA12
            </div>
            <div class="metric-value">
                {r["ema12"]:.5f}
            </div>
        </div>


        <div class="metric">
            <div class="metric-title">
                EMA26
            </div>
            <div class="metric-value">
                {r["ema26"]:.5f}
            </div>
        </div>


        <div class="metric">
            <div class="metric-title">
                EMA50
            </div>
            <div class="metric-value">
                {r["ema50"]:.5f}
            </div>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# INDICATORS
# =========================================================

st.markdown(
    f"""
    <div class="ind-title">
        INDICATORS ({r["side"]})
    </div>

    <div class="ind-grid">
        {r["indicators"]}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# BUTTONS
# =========================================================

b1, b2 = st.columns(2)


with b1:

    if st.button(
        "🔄 REFRESH",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


with b2:

    if st.button(
        "🧹 CLEAR CACHE",
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

        Closed:
        {closed_time}

        &nbsp;|&nbsp;

        Age:
        {age:.1f}m

        <br>

        Manual signal assistant
        •
        No automatic trading

    </div>
    """,
    unsafe_allow_html=True
)
