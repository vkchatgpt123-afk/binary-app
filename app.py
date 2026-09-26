import streamlit as st
import pandas as pd
import numpy as np

# ==============================
# PAGE SETTINGS
# ==============================

st.set_page_config(
    page_title="EUR/USD Signal Bot",
    page_icon="📊",
    layout="centered"
)

st.title("📊 EUR/USD SIGNAL BOT")
st.caption("Closed-Candle Analysis | Manual / Demo Use Only")

# ==============================
# STYLE
# ==============================

st.markdown("""
<style>
.signal {
    padding: 22px;
    border-radius: 12px;
    text-align: center;
    font-size: 30px;
    font-weight: bold;
    margin: 15px 0;
}

.up {
    background-color: #d4edda;
    color: #155724;
}

.down {
    background-color: #f8d7da;
    color: #721c24;
}

.no {
    background-color: #fff3cd;
    color: #856404;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# INPUT
# ==============================

pair = st.selectbox(
    "💱 Pair",
    ["EUR/USD"]
)

timeframe = st.selectbox(
    "⏱️ Timeframe",
    ["5m"]
)

uploaded_file = st.file_uploader(
    "📂 Upload EUR/USD candle CSV",
    type=["csv"]
)

# ==============================
# INDICATORS
# ==============================

def calculate_atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.rolling(period).mean()


def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(close):

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    return macd, signal


# ==============================
# ANALYSIS
# ==============================

def analyze(df):

    required = {
        "open",
        "high",
        "low",
        "close"
    }

    if not required.issubset(df.columns):

        return None, (
            "CSV में open, high, low, close "
            "columns होने चाहिए।"
        )

    df = df.copy()

    # Convert prices to numbers
    for col in [
        "open",
        "high",
        "low",
        "close"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # Remove invalid rows
    df = df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    df = df.reset_index(drop=True)

    # Minimum candles
    if len(df) < 120:

        return None, (
            "कम से कम 120 candles चाहिए।"
        )

    # Candle validation
    if (
        (df["high"] < df["low"]).any()
        or
        (
            df["high"]
            <
            df[["open", "close"]].max(axis=1)
        ).any()
        or
        (
            df["low"]
            >
            df[["open", "close"]].min(axis=1)
        ).any()
    ):

        return None, (
            "डेटा में गलत candle values हैं।"
        )

    # ==========================
    # INDICATORS
    # ==========================

    df["ema12"] = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    df["ema26"] = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["rsi"] = calculate_rsi(
        df["close"],
        14
    )

    df["macd"], df["macd_signal"] = calculate_macd(
        df["close"]
    )

    df["atr"] = calculate_atr(
        df,
        14
    )

    # Bollinger Bands

    df["bb_middle"] = df["close"].rolling(
        20
    ).mean()

    bb_std = df["close"].rolling(
        20
    ).std()

    df["bb_upper"] = (
        df["bb_middle"] +
        2 * bb_std
    )

    df["bb_lower"] = (
        df["bb_middle"] -
        2 * bb_std
    )

    # ==========================
    # USE LAST CLOSED CANDLE
    # ==========================

    i = len(df) - 1

    current = df.iloc[i]

    previous = df.iloc[i - 1]

    # Check indicator availability

    indicator_values = [
        current["ema12"],
        current["ema26"],
        current["rsi"],
        current["macd"],
        current["macd_signal"],
        current["atr"],
        current["bb_middle"],
        current["bb_upper"],
        current["bb_lower"]
    ]

    if any(
        pd.isna(x)
        for x in indicator_values
    ):

        return None, (
            "Indicator data पूरा नहीं है।"
        )

    # ==========================
    # MARKET DIRECTION
    # ==========================

    uptrend = (
        current["ema12"] > current["ema26"]
        and
        current["close"] > current["ema12"]
    )

    downtrend = (
        current["ema12"] < current["ema26"]
        and
        current["close"] < current["ema12"]
    )

    if uptrend:

        market = "UPTREND"

    elif downtrend:

        market = "DOWNTREND"

    else:

        market = "SIDEWAYS"

    # ==========================
    # SCORE
    # ==========================

    up_score = 0
    down_score = 0

    checks = {}

    # EMA

    if current["ema12"] > current["ema26"]:

        up_score += 1
        checks["EMA Trend"] = "UP"

    elif current["ema12"] < current["ema26"]:

        down_score += 1
        checks["EMA Trend"] = "DOWN"

    else:

        checks["EMA Trend"] = "NEUTRAL"

    # Price vs EMA12

    if current["close"] > current["ema12"]:

        up_score += 1
        checks["Price vs EMA12"] = "UP"

    elif current["close"] < current["ema12"]:

        down_score += 1
        checks["Price vs EMA12"] = "DOWN"

    else:

        checks["Price vs EMA12"] = "NEUTRAL"

    # RSI

    if 52 <= current["rsi"] <= 70:

        up_score += 1
        checks["RSI"] = "UP"

    elif 30 <= current["rsi"] <= 48:

        down_score += 1
        checks["RSI"] = "DOWN"

    else:

        checks["RSI"] = "NEUTRAL"

    # MACD

    if current["macd"] > current["macd_signal"]:

        up_score += 1
        checks["MACD"] = "UP"

    elif current["macd"] < current["macd_signal"]:

        down_score += 1
        checks["MACD"] = "DOWN"

    else:

        checks["MACD"] = "NEUTRAL"

    # Bollinger

    if current["close"] > current["bb_middle"]:

        up_score += 1
        checks["Bollinger"] = "UP"

    elif current["close"] < current["bb_middle"]:

        down_score += 1
        checks["Bollinger"] = "DOWN"

    else:

        checks["Bollinger"] = "NEUTRAL"

    # ==========================
    # ATR FILTER
    # ==========================

    previous_atr = (
        df["atr"]
        .iloc[max(0, i - 100):i]
        .dropna()
    )

    if len(previous_atr) < 20:

        return None, (
            "ATR history पर्याप्त नहीं है।"
        )

    median_atr = previous_atr.median()

    volatility_ok = (
        current["atr"]
        >=
        0.80 * median_atr
    )

    # ==========================
    # FINAL SIGNAL
    # ==========================

    signal = "NO TRADE"

    reason = "Setup पर्याप्त मजबूत नहीं है।"

    # Sideways = No Trade

    if market == "SIDEWAYS":

        signal = "NO TRADE"

        reason = (
            "Market sideways है। "
            "Clear trend का इंतजार करें।"
        )

    elif not volatility_ok:

        signal = "NO TRADE"

        reason = (
            "Market volatility कम है।"
        )

    elif up_score >= 4 and (
        up_score >= down_score + 2
    ):

        signal = "UP"

        reason = (
            "Multiple indicators bullish "
            "direction में हैं।"
        )

    elif down_score >= 4 and (
        down_score >= up_score + 2
    ):

        signal = "DOWN"

        reason = (
            "Multiple indicators bearish "
            "direction में हैं।"
        )

    else:

        signal = "NO TRADE"

        reason = (
            "Indicators में पर्याप्त agreement नहीं है।"
        )

    return {

        "signal": signal,

        "market": market,

        "up_score": up_score,

        "down_score": down_score,

        "price": current["close"],

        "rsi": current["rsi"],

        "ema12": current["ema12"],

        "ema26": current["ema26"],

        "macd": current["macd"],

        "macd_signal": current["macd_signal"],

        "atr": current["atr"],

        "median_atr": median_atr,

        "volatility_ok": volatility_ok,

        "checks": checks,

        "reason": reason,

        "time": current.get(
            "datetime",
            current.get(
                "time",
                "N/A"
            )
        )

    }, None


# ==============================
# RUN
# ==============================

if uploaded_file:

    try:

        df = pd.read_csv(
            uploaded_file
        )

        # Clean column names

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        result, error = analyze(df)

        if error:

            st.error(error)

        elif result:

            st.markdown(
                f"### 💱 {pair} | ⏱️ {timeframe}"
            )

            # ======================
            # MARKET
            # ======================

            st.info(
                f'🌐 Market State: '
                f'{result["market"]}'
            )

            signal = result["signal"]

            # ======================
            # SIGNAL DISPLAY
            # ======================

            if signal == "UP":

                st.markdown(
                    '<div class="signal up">'
                    '🟢 UP'
                    '</div>',
                    unsafe_allow_html=True
                )

            elif signal == "DOWN":

                st.markdown(
                    '<div class="signal down">'
                    '🔴 DOWN'
                    '</div>',
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    '<div class="signal no">'
                    '🛑 NO TRADE'
                    '</div>',
                    unsafe_allow_html=True
                )

            st.warning(
                result["reason"]
            )

            # ======================
            # SCORE
            # ======================

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "🟢 UP Score",
                    f'{result["up_score"]}/5'
                )

            with col2:

                st.metric(
                    "🔴 DOWN Score",
                    f'{result["down_score"]}/5'
                )

            # ======================
            # PRICE / RSI / ATR
            # ======================

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "💰 Price",
                    f'{result["price"]:.5f}'
                )

            with col2:

                st.metric(
                    "📈 RSI",
                    f'{result["rsi"]:.1f}'
                )

            with col3:

                st.metric(
                    "⚡ ATR",
                    f'{result["atr"]:.6f}'
                )

            st.caption(
                f'🕒 Candle: {result["time"]}'
            )

            # ======================
            # INDICATORS
            # ======================

            st.subheader(
                "📊 Indicators"
            )

            indicator_table = pd.DataFrame({

                "Indicator": [
                    "EMA 12",
                    "EMA 26",
                    "RSI 14",
                    "MACD",
                    "MACD Signal",
                    "ATR 14"
                ],

                "Value": [
                    f'{result["ema12"]:.5f}',
                    f'{result["ema26"]:.5f}',
                    f'{result["rsi"]:.2f}',
                    f'{result["macd"]:.6f}',
                    f'{result["macd_signal"]:.6f}',
                    f'{result["atr"]:.6f}'
                ]

            })

            st.dataframe(
                indicator_table,
                use_container_width=True,
                hide_index=True
            )

            # ======================
            # CHECKS
            # ======================

            st.subheader(
                "📋 Strategy Checks"
            )

            for name, value in result["checks"].items():

                if value == "UP":

                    st.write(
                        f"🟢 {name}: UP"
                    )

                elif value == "DOWN":

                    st.write(
                        f"🔴 {name}: DOWN"
                    )

                else:

                    st.write(
                        f"⚪ {name}: NEUTRAL"
                    )

            # ======================
            # ATR FILTER
            # ======================

            if result["volatility_ok"]:

                st.write(
                    "🟢 Volatility Filter: OK"
                )

            else:

                st.write(
                    "🔴 Volatility Filter: LOW"
                )

            # ======================
            # RECENT DATA
            # ======================

            st.subheader(
                "📊 Recent Candle Data"
            )

            st.dataframe(
                df.tail(10),
                use_container_width=True
            )

            st.caption(
                "⚠️ यह bot केवल uploaded "
                "historical/candle data का "
                "analysis करता है।"
            )

            st.caption(
                "⚠️ यह auto-trading नहीं करता "
                "और profit की guarantee नहीं देता।"
            )

    except Exception as e:

        st.error(
            f"डेटा पढ़ने में समस्या: {e}"
        )

else:

    st.info(
        "शुरू करने के लिए "
        "EUR/USD की 5 मिनट वाली "
        "CSV फ़ाइल upload करें।"
    )
