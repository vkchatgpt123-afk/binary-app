import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="EUR/USD Signal Bot",
    page_icon="📊",
    layout="centered"
)

st.title("📊 EUR/USD SIGNAL BOT")
st.caption("Manual Trading Analysis | No Auto Trade")

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

pair = st.selectbox("💱 Pair", ["EUR/USD"])
timeframe = st.selectbox("⏱️ Timeframe", ["5m"])

uploaded_file = st.file_uploader(
    "📂 Upload EUR/USD candle CSV",
    type=["csv"]
)


def calculate_atr(df, period=14):
    prev_close = df["close"].shift(1)

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(period).mean()


def analyze(df):
    required = {"open", "high", "low", "close"}

    if not required.issubset(df.columns):
        return None, "CSV में open, high, low, close कॉलम होने चाहिए।"

    df = df.copy()

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.reset_index(drop=True)

    if len(df) < 120:
        return None, "कम से कम 120 candles चाहिए।"

    if (
        (df["high"] < df["low"]).any()
        or (df["high"] < df[["open", "close"]].max(axis=1)).any()
        or (df["low"] > df[["open", "close"]].min(axis=1)).any()
    ):
        return None, "डेटा में गलत candle values हैं।"

    df["atr"] = calculate_atr(df)

    i = len(df) - 1
    current = df.iloc[i]

    previous_atrs = df["atr"].iloc[i - 100:i].dropna()

    if len(previous_atrs) < 100 or pd.isna(current["atr"]):
        return None, "ATR डेटा पूरा नहीं है।"

    median_atr = previous_atrs.median()

    last_four = df.iloc[i - 3:i + 1]

    four_bullish = (
        (last_four["close"] > last_four["open"]).all()
    )

    candle_range = current["high"] - current["low"]

    if candle_range <= 0:
        return None, "Candle range गलत है।"

    body = abs(current["close"] - current["open"])
    close_location = (
        (current["close"] - current["low"]) / candle_range
    )

    checks = {
        "4 Bullish Candles": bool(four_bullish),
        "Body ≥ 1.5 ATR": bool(body >= 1.5 * current["atr"]),
        "Close Location ≥ 85%": bool(close_location >= 0.85),
        "ATR > 1.2 × Median ATR": bool(
            current["atr"] > 1.2 * median_atr
        )
    }

    signal = "NO TRADE"

    if all(checks.values()):
        signal = "DOWN"

    return {
        "signal": signal,
        "price": current["close"],
        "atr": current["atr"],
        "median_atr": median_atr,
        "checks": checks,
        "time": current.get("datetime", current.get("time", "N/A"))
    }, None


if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()

        result, error = analyze(df)

        if error:
            st.error(error)

        elif result:
            st.markdown(f"### 💱 {pair} | ⏱️ {timeframe}")

            signal = result["signal"]

            if signal == "DOWN":
                st.markdown(
                    '<div class="signal down">🔴 DOWN</div>',
                    unsafe_allow_html=True
                )
                st.warning("यह केवल संभावित reversal setup है।")
            else:
                st.markdown(
                    '<div class="signal no">🛑 NO TRADE</div>',
                    unsafe_allow_html=True
                )
                st.info("सभी शर्तें पूरी नहीं हुईं।")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("💰 Price", f'{result["price"]:.5f}')

            with col2:
                st.metric("📈 ATR", f'{result["atr"]:.6f}')

            st.caption(f'🕒 Candle: {result["time"]}')

            st.subheader("📋 Strategy Checks")

            for name, passed in result["checks"].items():
                st.write(
                    f'{"✅" if passed else "❌"} {name}'
                )

            st.subheader("📊 Candle Data")
            st.dataframe(df.tail(10), use_container_width=True)

            st.caption(
                "⚠️ यह सिग्नल ऐतिहासिक/अपलोड किए गए डेटा पर आधारित है। "
                "यह लाइव डेटा नहीं लाता और मुनाफे की गारंटी नहीं देता।"
            )

    except Exception as e:
        st.error(f"डेटा पढ़ने में समस्या: {e}")

else:
    st.info("शुरू करने के लिए EUR/USD की 5 मिनट वाली CSV फ़ाइल अपलोड करें।")


Would you like the code adjusted to read a fixed CSV file from your GitHub repository instead of requiring a manual upload?
