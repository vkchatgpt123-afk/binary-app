import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# =========================================================
# SIGNAL TERMINAL V4.9.9 — ORIGINAL LAYOUT FIX
# MANUAL SIGNAL ONLY — NO AUTO TRADING
# =========================================================

st.set_page_config(
    page_title="Signal Terminal",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background: radial-gradient(
        circle at top,
        #1a4b7c 0%,
        #0a192f 50%,
        #02060d 100%
    );
    color: white;
}

.block-container {
    max-width: 410px !important;
    padding: 0.35rem 0.35rem 0.4rem !important;
}

[data-testid="stHorizontalBlock"] {
    gap: 4px !important;
}

[data-testid="column"] {
    padding: 0 !important;
    min-width: 0 !important;
}

/* ---------------- CONTROLS ---------------- */

.control-box {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 7px;
    padding: 5px;
    margin-bottom: 5px;
}

.stSelectbox label {
    color: #64ffda !important;
    font-size: 8px !important;
    font-weight: bold !important;
    margin-bottom: 1px !important;
}

div[data-baseweb="select"] > div {
    background: #0a192f !important;
    color: white !important;
    border: 1px solid #64ffda !important;
    border-radius: 5px !important;
    min-height: 29px !important;
}

div[data-baseweb="select"] span {
    color: white !important;
    font-size: 10px !important;
    font-weight: bold !important;
}

/* ---------------- SIGNAL ---------------- */

.signal-box {
    border-radius: 8px;
    padding: 9px 5px;
    margin: 5px 0;
    text-align: center;
    font-size: 18px;
    font-weight: 900;
    letter-spacing: 1px;
}

.signal-up {
    background: linear-gradient(135deg,#00b09b,#96c93d);
    border: 2px solid #64ffda;
    color: #00150e;
}

.signal-down {
    background: linear-gradient(135deg,#ff416c,#ff4b2b);
    border: 2px solid #ff4b2b;
    color: white;
}

.signal-wait {
    background: linear-gradient(135deg,#f7b733,#fc4a1a);
    border: 2px solid #f7b733;
    color: #111;
}

.signal-closed {
    background: #151a22;
    border: 2px solid #64748b;
    color: white;
}

.signal-sub {
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0;
    margin-top: 3px;
}

/* ---------------- STATUS ---------------- */

.status-box {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 6px;
    padding: 5px;
    margin: 4px 0;
    text-align: center;
    font-size: 9px;
    font-weight: bold;
}

.status-reason {
    color: #a8b2d1;
    font-size: 8px;
    margin-top: 2px;
}

/* ---------------- METRICS ---------------- */

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin: 4px 0;
}

.metric-card {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 5px;
    padding: 6px 2px;
    text-align: center;
}

.metric-title {
    color: #8892b0;
    font-size: 7px;
    font-weight: bold;
}

.metric-value {
    color: white;
    font-size: 10px;
    font-weight: 900;
}

/* ---------------- INDICATORS ---------------- */

.indicator-box {
    background: #112240;
    border: 1px solid #64ffda;
    border-radius: 6px;
    padding: 5px;
    margin: 4px 0;
}

.indicator-title {
    color: #64ffda;
    font-size: 9px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 4px;
}

.indicator-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 3px;
}

.indicator-card {
    background: #0c1d38;
    border: 1px solid #304d70;
    border-radius: 5px;
    padding: 4px 1px;
    text-align: center;
}

.indicator-name {
    color: #8892b0;
    font-size: 6.5px;
    font-weight: bold;
}

.indicator-icon {
    font-size: 13px;
    line-height: 14px;
}

/* ---------------- BUTTON ---------------- */

.stButton > button {
    min-height: 31px !important;
    background: #0d203b !important;
    border: 1px solid #64ffda !important;
    border-radius: 6px !important;
    color: white !important;
    font-size: 10px !important;
    font-weight: 900 !important;
}

/* ---------------- FOOTER ---------------- */

.footer {
    color: #8892b0;
    text-align: center;
    font-size: 7px;
    margin-top: 3px;
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
# PAIR + TIMEFRAME
# =========================================================

st.markdown(
    '<div class="control-box">',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:
    pair = st.selectbox(
        "PAIR",
        list(PAIRS.keys()),
        index=0,
        key="pair_original"
    )

with col2:
    timeframe = st.selectbox(
        "TIMEFRAME",
        list(TIMEFRAMES.keys()),
        index=0,
        key="timeframe_original"
    )

st.markdown(
    '</div>',
    unsafe_allow_html=True
)

symbol = PAIRS[pair]
interval = TIMEFRAMES[timeframe]


# =========================================================
# DATA
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

    if df is None or len(df) < 150:
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
    d["RSI"] = calculate_rsi(close)

    # MACD
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

    # Bollinger
    std = close.rolling(20).std()

    d["BB_UPPER"] = (
        d["SMA20"] +
        2 * std
    )

    d["BB_LOWER"] = (
        d["SMA20"] -
        2 * std
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

    d["ATR14"] = tr.ewm(
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

    # Last completed candle
    c = d.iloc[-2]
    p = d.iloc[-3]

    price = float(c["Close"])

    ema12 = float(c["EMA12"])
    ema26 = float(c["EMA26"])
    ema50 = float(c["EMA50"])

    sma20 = float(c["SMA20"])

    rsi = float(c["RSI"])
    previous_rsi = float(p["RSI"])

    macd = float(c["MACD"])
    macd_signal = float(c["MACD_SIGNAL"])

    hist = float(c["MACD_HIST"])
    previous_hist = float(p["MACD_HIST"])

    bb_upper = float(c["BB_UPPER"])
    bb_lower = float(c["BB_LOWER"])

    atr = float(c["ATR14"])

    body = float(c["BODY"])
    location = float(c["LOCATION"])

    # Strength
    gap = abs(
        ema12 - ema26
    )

    strength = (
        gap / atr
        if atr > 0
        else 0
    )

    strong = strength >= 0.15

    # Market
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

    # UP conditions
    up = [

        market == "UPTREND",

        ema12 > ema26
        and ema26 > ema50,

        45 <= rsi <= 68
        and rsi > previous_rsi,

        macd > macd_signal
        and hist > previous_hist,

        price > ema12
        and price > sma20,

        price > sma20
        and price < bb_upper,

        bool(c["Close"] > c["Open"])
        and body >= 0.45
        and location >= 0.65,

        atr > 0
        and strength >= 0.15
    ]

    # DOWN conditions
    down = [

        market == "DOWNTREND",

        ema12 < ema26
        and ema26 < ema50,

        32 <= rsi <= 55
        and rsi < previous_rsi,

        macd < macd_signal
        and hist < previous_hist,

        price < ema12
        and price < sma20,

        price < sma20
        and price > bb_lower,

        bool(c["Close"] < c["Open"])
        and body >= 0.45
        and location <= 0.35,

        atr > 0
        and strength >= 0.15
    ]

    up_score = sum(up)
    down_score = sum(down)

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

    if market == "UPTREND":

        side = "UP"
        selected = up

    elif market == "DOWNTREND":

        side = "DOWN"
        selected = down

    else:

        side = (
            "UP"
            if up_score >= down_score
            else "DOWN"
        )

        selected = (
            up
            if up_score >= down_score
            else down
        )

    names = [
        "Trend",
        "EMA",
        "RSI",
        "MACD",
        "Price",
        "BB",
        "Candle",
        "Vol"
    ]

    indicator_html = ""

    for name, status in zip(
        names,
        selected
    ):

        icon = (
            "✅"
            if status
            else "❌"
        )

        indicator_html += (
            '<div class="indicator-card">'
            '<div class="indicator-name">'
            + name +
            '</div>'
            '<div class="indicator-icon">'
            + icon +
            '</div>'
            '</div>'
        )

    return {
        "signal": signal,
        "reason": reason,
        "market": market,
        "up": up_score,
        "down": down_score,
        "side": side,
        "indicators": indicator_html,
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

if df is None or len(df) < 150:

    st.markdown(
        '<div class="signal-box signal-wait">'
        '⚠️ DATA UNAVAILABLE'
        '<div class="signal-sub">'
        'NO SIGNAL'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.stop()

r = analyze(df)

if r is None:

    st.markdown(
        '<div class="signal-box signal-wait">'
        '⚠️ ANALYSIS ERROR'
        '<div class="signal-sub">'
        'NO SIGNAL'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

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

    age = max(
        0,
        (
            datetime.now(timezone.utc)
            - closed_time
        ).total_seconds() / 60
    )

except Exception:

    age = 999999


# =========================================================
# WEEKEND
# =========================================================

weekend = (
    datetime.now(timezone.utc).weekday()
    >= 5
)

max_age = {
    "5m": 20,
    "15m": 45,
    "30m": 75,
    "1H": 150
}[timeframe]

stale = age > max_age


# =========================================================
# SIGNAL DISPLAY
# =========================================================

if weekend:

    display_signal = "🔒 MARKET CLOSED"
    signal_class = "signal-closed"
    signal_reason = "Weekend — NO SIGNAL"

elif stale:

    display_signal = "🕐 DATA STALE"
    signal_class = "signal-wait"
    signal_reason = "Fresh data unavailable"

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
# SIGNAL BOX
# =========================================================

st.markdown(
    '<div class="signal-box '
    + signal_class
    + '">'
    + display_signal
    + '<div class="signal-sub">'
    + signal_reason
    + '</div>'
    + '</div>',
    unsafe_allow_html=True
)


# =========================================================
# STATUS
# =========================================================

st.markdown(
    '<div class="status-box">'
    '<b>'
    + r["market"]
    + '</b>'
    + ' | 🟢 '
    + str(r["up"])
    + '/8'
    + ' • 🔴 '
    + str(r["down"])
    + '/8'
    + '<div class="status-reason">'
    + signal_reason
    + '</div>'
    + '</div>',
    unsafe_allow_html=True
)


# =========================================================
# METRICS
# =========================================================

st.markdown(
    '<div class="metric-grid">'

    '<div class="metric-card">'
    '<div class="metric-title">PRICE</div>'
    '<div class="metric-value">'
    + f'{r["price"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">RSI</div>'
    '<div class="metric-value">'
    + f'{r["rsi"]:.1f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">ATR</div>'
    '<div class="metric-value">'
    + f'{r["atr"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA12</div>'
    '<div class="metric-value">'
    + f'{r["ema12"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA26</div>'
    '<div class="metric-value">'
    + f'{r["ema26"]:.5f}'
    + '</div></div>'

    '<div class="metric-card">'
    '<div class="metric-title">EMA50</div>'
    '<div class="metric-value">'
    + f'{r["ema50"]:.5f}'
    + '</div></div>'

    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# INDICATORS
# =========================================================

st.markdown(
    '<div class="indicator-box">'
    '<div class="indicator-title">'
    'INDICATORS ('
    + r["side"]
    + ')'
    '</div>'
    '<div class="indicator-grid">'
    + r["indicators"]
    + '</div>'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# REFRESH
# =========================================================

if st.button(
    "🔄 REFRESH DATA",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


# =========================================================
# FOOTER
# =========================================================

if weekend:

    footer_text = (
        "Market closed • Last available candle: "
        + str(closed_time)
    )

else:

    footer_text = (
        "Closed: "
        + str(closed_time)
        + " | Age: "
        + f"{age:.1f}m"
    )

st.markdown(
    '<div class="footer">'
    + footer_text
    + '<br>'
    'Manual signal assistant • No automatic trading'
    '</div>',
    unsafe_allow_html=True
)
