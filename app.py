import streamlit as st
import pandas as pd
import numpy as np
import requests
import math

st.set_page_config(
    page_title="EUR/USD Signal Bot V7",
    page_icon="📊",
    layout="centered"
)

PIP = 0.0001
YF_SYMBOL = "EURUSD=X"


# ============================================================
# STATISTICS
# ============================================================

def wilson(wins, n, z=1.96):
    if n <= 0:
        return np.nan, np.nan

    p = wins / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(
        max(p * (1 - p) / n + z * z / (4 * n * n), 0)
    ) / den

    return center - half, center + half


def max_loss_streak(values):
    best = 0
    current = 0

    for value in values:
        if int(value) == 0:
            current += 1
            best = max(best, current)
        else:
            current = 0

    return best


# ============================================================
# LIVE EUR/USD 5-MIN DATA
# ============================================================

@st.cache_data(ttl=45, show_spinner=False)
def get_live_5m():

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{YF_SYMBOL}"
        "?range=5d&interval=5m&includePrePost=false"
    )

    response = requests.get(
        url,
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    result = response.json()["chart"]["result"][0]

    quote = result["indicators"]["quote"][0]
    timestamps = result.get("timestamp", [])

    df = pd.DataFrame({
        "time": pd.to_datetime(
            timestamps,
            unit="s",
            utc=True
        ),
        "open": quote.get("open", []),
        "high": quote.get("high", []),
        "low": quote.get("low", []),
        "close": quote.get("close", []),
        "volume": quote.get(
            "volume",
            [np.nan] * len(timestamps)
        )
    })

    df = df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    df = (
        df
        .drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# INDICATORS
# ============================================================

def indicators(df):

    x = df.copy()

    # EMA
    x["ema12"] = (
        x["close"]
        .ewm(span=12, adjust=False)
        .mean()
    )

    x["ema26"] = (
        x["close"]
        .ewm(span=26, adjust=False)
        .mean()
    )

    # SMA
    x["sma20"] = (
        x["close"]
        .rolling(20)
        .mean()
    )

    # RSI
    delta = x["close"].diff()

    gain = (
        delta
        .clip(lower=0)
        .rolling(14)
        .mean()
    )

    loss = (
        (-delta.clip(upper=0))
        .rolling(14)
        .mean()
    )

    rs = gain / loss.replace(0, np.nan)

    x["rsi14"] = (
        100 -
        100 / (1 + rs)
    )

    # ATR
    tr = pd.concat(
        [
            x["high"] - x["low"],
            (
                x["high"] -
                x["close"].shift()
            ).abs(),
            (
                x["low"] -
                x["close"].shift()
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    x["atr14"] = (
        tr
        .rolling(14)
        .mean()
    )

    # Previous ATR median
    x["atr_med100"] = (
        x["atr14"]
        .shift(1)
        .rolling(100)
        .median()
    )

    # Candle structure
    x["body"] = (
        x["close"] -
        x["open"]
    ).abs()

    x["range"] = (
        x["high"] -
        x["low"]
    ).replace(0, np.nan)

    x["body_atr"] = (
        x["body"] /
        x["atr14"].replace(0, np.nan)
    )

    # 0 = close at low
    # 1 = close at high
    x["close_loc"] = (
        x["close"] -
        x["low"]
    ) / x["range"]

    # MACD
    x["macd"] = (
        x["ema12"] -
        x["ema26"]
    )

    x["macd_signal"] = (
        x["macd"]
        .ewm(span=9, adjust=False)
        .mean()
    )

    x["macd_hist"] = (
        x["macd"] -
        x["macd_signal"]
    )

    # Bollinger Bands
    x["bb_mid"] = (
        x["close"]
        .rolling(20)
        .mean()
    )

    x["bb_std"] = (
        x["close"]
        .rolling(20)
        .std()
    )

    x["bb_upper"] = (
        x["bb_mid"] +
        2 * x["bb_std"]
    )

    x["bb_lower"] = (
        x["bb_mid"] -
        2 * x["bb_std"]
    )

    # Candle runs
    bullish = x["close"] > x["open"]
    bearish = x["close"] < x["open"]

    x["bull_run"] = (
        bullish
        .groupby((~bullish).cumsum())
        .cumsum()
    )

    x["bear_run"] = (
        bearish
        .groupby((~bearish).cumsum())
        .cumsum()
    )

    # Market regime
    x["trend_strength"] = (
        (x["ema12"] - x["ema26"]).abs() /
        x["atr14"].replace(0, np.nan)
    )

    x["regime"] = np.where(
        x["trend_strength"] >= 0.35,
        np.where(
            x["ema12"] > x["ema26"],
            "UPTREND",
            "DOWNTREND"
        ),
        "SIDEWAYS"
    )

    return x


# ============================================================
# SIGNAL ENGINE
# ============================================================

def signal_at(x, i, minimum=6):

    if i < 110:
        return (
            "NO TRADE",
            0,
            "Not enough historical data"
        )

    r = x.iloc[i]

    required = [
        "atr14",
        "atr_med100",
        "body_atr",
        "close_loc",
        "rsi14",
        "ema12",
        "ema26",
        "macd_hist",
        "bb_upper",
        "bb_lower"
    ]

    if any(
        pd.isna(r[k])
        for k in required
    ):
        return (
            "NO TRADE",
            0,
            "Indicators not ready"
        )

    # Sideways = no trade
    if r["regime"] == "SIDEWAYS":
        return (
            "NO TRADE",
            0,
            "SIDEWAYS market"
        )

    # Abnormal candle protection
    if r["body_atr"] > 3.5:
        return (
            "NO TRADE",
            0,
            "Abnormal candle"
        )

    up_score = 0
    down_score = 0

    up_reason = []
    down_reason = []

    # --------------------------------------------------------
    # Bullish exhaustion -> possible DOWN
    # --------------------------------------------------------

    if r["bull_run"] >= 4:
        down_score += 2
        down_reason.append(
            "4+ bullish candles"
        )

    # --------------------------------------------------------
    # Bearish exhaustion -> possible UP
    # --------------------------------------------------------

    if r["bear_run"] >= 4:
        up_score += 2
        up_reason.append(
            "4+ bearish candles"
        )

    # Strong body
    if r["body_atr"] >= 1.5:

        if r["close"] > r["open"]:
            down_score += 2
            down_reason.append(
                "strong bullish body"
            )

        elif r["close"] < r["open"]:
            up_score += 2
            up_reason.append(
                "strong bearish body"
            )

    # Close near high
    if (
        r["close_loc"] >= 0.85
        and r["close"] > r["open"]
    ):
        down_score += 2
        down_reason.append(
            "close near high"
        )

    # Close near low
    if (
        r["close_loc"] <= 0.15
        and r["close"] < r["open"]
    ):
        up_score += 2
        up_reason.append(
            "close near low"
        )

    # High volatility
    if (
        r["atr14"] >
        1.20 * r["atr_med100"]
    ):

        if r["close"] > r["open"]:
            down_score += 1
            down_reason.append(
                "high volatility"
            )

        elif r["close"] < r["open"]:
            up_score += 1
            up_reason.append(
                "high volatility"
            )

    # RSI
    if r["rsi14"] >= 68:
        down_score += 1
        down_reason.append(
            "RSI elevated"
        )

    if r["rsi14"] <= 32:
        up_score += 1
        up_reason.append(
            "RSI depressed"
        )

    # Bollinger
    if r["close"] >= r["bb_upper"]:
        down_score += 1
        down_reason.append(
            "upper Bollinger"
        )

    if r["close"] <= r["bb_lower"]:
        up_score += 1
        up_reason.append(
            "lower Bollinger"
        )

    # MACD
    if r["macd_hist"] < 0:
        down_score += 1
        down_reason.append(
            "MACD weakening"
        )

    if r["macd_hist"] > 0:
        up_score += 1
        up_reason.append(
            "MACD positive"
        )

    # --------------------------------------------------------
    # Trend protection
    # --------------------------------------------------------

    if r["regime"] == "UPTREND":

        if down_score >= minimum + 1:
            return (
                "DOWN",
                down_score,
                ", ".join(down_reason)
            )

        return (
            "NO TRADE",
            down_score,
            "UPTREND; reversal not strong enough"
        )

    if r["regime"] == "DOWNTREND":

        if up_score >= minimum + 1:
            return (
                "UP",
                up_score,
                ", ".join(up_reason)
            )

        return (
            "NO TRADE",
            up_score,
            "DOWNTREND; reversal not strong enough"
        )

    return (
        "NO TRADE",
        max(up_score, down_score),
        "No clean setup"
    )


# ============================================================
# BACKTEST
# ============================================================

def backtest(
    df,
    horizon=1,
    minimum=6,
    spread=1.2
):

    x = indicators(df)

    trades = []

    for i in range(
        110,
        len(x) - horizon - 1
    ):

        signal, score, reason = signal_at(
            x,
            i,
            minimum
        )

        if signal not in (
            "UP",
            "DOWN"
        ):
            continue

        entry_index = i + 1
        exit_index = i + horizon

        entry = float(
            x.iloc[entry_index]["open"]
        )

        exit_price = float(
            x.iloc[exit_index]["close"]
        )

        direction = (
            1
            if signal == "UP"
            else -1
        )

        gross_pips = (
            (exit_price - entry) /
            PIP *
            direction
        )

        net_pips = (
            gross_pips -
            spread
        )

        trades.append(
            {
                "signal_time":
                    x.iloc[i]["time"],

                "entry_time":
                    x.iloc[entry_index]["time"],

                "exit_time":
                    x.iloc[exit_index]["time"],

                "signal":
                    signal,

                "score":
                    score,

                "entry":
                    entry,

                "exit":
                    exit_price,

                "gross_pips":
                    gross_pips,

                "net_pips":
                    net_pips,

                "win":
                    int(gross_pips > 0)
            }
        )

    return pd.DataFrame(trades)


# ============================================================
# ONE TRADE AT A TIME
# ============================================================

def non_overlap(trades):

    if trades.empty:
        return trades

    keep = []
    last_exit = None

    for index, row in trades.iterrows():

        if (
            last_exit is None
            or row["entry_time"] > last_exit
        ):

            keep.append(index)

            last_exit = row["exit_time"]

    return (
        trades
        .loc[keep]
        .reset_index(drop=True)
    )


# ============================================================
# BACKTEST STATS
# ============================================================

def get_stats(trades):

    if trades.empty:
        return None

    n = len(trades)

    wins = int(
        trades["win"].sum()
    )

    winrate = wins / n

    low, high = wilson(
        wins,
        n
    )

    # Correct drawdown calculation
    equity = np.r_[
        0.0,
        trades["net_pips"]
        .astype(float)
        .cumsum()
        .to_numpy()
    ]

    peak = np.maximum.accumulate(
        equity
    )

    drawdown = (
        equity -
        peak
    )

    max_dd = float(
        drawdown.min()
    )

    positive = float(
        trades.loc[
            trades["net_pips"] > 0,
            "net_pips"
        ].sum()
    )

    negative = float(
        -trades.loc[
            trades["net_pips"] < 0,
            "net_pips"
        ].sum()
    )

    if negative > 0:
        profit_factor = (
            positive /
            negative
        )
    else:
        profit_factor = np.inf

    return {
        "trades": n,
        "wins": wins,
        "losses": n - wins,
        "winrate": winrate,
        "low": low,
        "high": high,
        "total_pips": float(
            trades["net_pips"].sum()
        ),
        "avg_pips": float(
            trades["net_pips"].mean()
        ),
        "profit_factor":
            profit_factor,
        "max_dd":
            max_dd,
        "max_streak":
            max_loss_streak(
                trades["win"]
            )
    }


# ============================================================
# USER INTERFACE
# ============================================================

st.title(
    "📊 EUR/USD SIGNAL BOT V7"
)

st.caption(
    "LIVE MARKET • 5-MIN CLOSED CANDLE • MANUAL SIGNAL ONLY"
)

with st.sidebar:

    st.header("⚙️ Settings")

    minimum = st.slider(
        "Minimum signal score",
        5,
        8,
        6
    )

    horizon = st.selectbox(
        "Backtest expiry candles",
        [1, 2, 3],
        index=0
    )

    spread = st.number_input(
        "Estimated spread / cost (pips)",
        min_value=0.0,
        max_value=5.0,
        value=1.2,
        step=0.1
    )

    one_trade = st.checkbox(
        "One trade at a time",
        value=True
    )

    st.divider()

    st.caption(
        "🔒 OTC DISABLED"
    )

    st.caption(
        "🔒 AUTO TRADING DISABLED"
    )


# ============================================================
# REFRESH
# ============================================================

if st.button(
    "🔄 REFRESH LIVE DATA",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


# ============================================================
# MAIN
# ============================================================

try:

    raw = get_live_5m()

    data = indicators(raw)

    if len(data) < 120:

        st.error(
            "Not enough live 5-minute data."
        )

        st.stop()

    now = pd.Timestamp.now(
        tz="UTC"
    )

    last = data.iloc[-1]

    candle_end = (
        last["time"].floor("5min")
        +
        pd.Timedelta(minutes=5)
    )

    # Never use a candle that is still forming
    if now < candle_end:
        signal_index = len(data) - 2
    else:
        signal_index = len(data) - 1

    row = data.iloc[
        signal_index
    ]

    age_minutes = (
        now -
        row["time"]
    ).total_seconds() / 60

    # Freshness protection
    stale = age_minutes > 20

    st.subheader(
        "🟢 LIVE EUR/USD"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "PRICE",
        f"{row['close']:.5f}"
    )

    col2.metric(
        "RSI",
        (
            f"{row['rsi14']:.1f}"
            if pd.notna(row["rsi14"])
            else "—"
        )
    )

    col3.metric(
        "ATR",
        (
            f"{row['atr14']/PIP:.1f} pips"
            if pd.notna(row["atr14"])
            else "—"
        )
    )

    st.write(
        "**Closed candle:** "
        +
        row["time"].strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    st.write(
        f"**Data age:** "
        f"{age_minutes:.1f} min"
    )

    if stale:

        st.error(
            "🔴 DATA STALE — NO SIGNAL"
        )

        st.warning(
            "Live data is too old. "
            "Do not trade."
        )

        st.stop()

    signal, score, reason = signal_at(
        data,
        signal_index,
        minimum
    )

    if signal == "UP":

        st.success(
            "🟢 UP"
        )

    elif signal == "DOWN":

        st.error(
            "🔴 DOWN"
        )

    else:

        st.warning(
            "🟡 NO TRADE"
        )

    st.write(
        f"**Market:** {row['regime']}"
    )

    st.write(
        f"**Score:** {score}"
    )

    st.write(
        f"**Reason:** {reason}"
    )


    # ========================================================
    # SAFETY CHECKS
    # ========================================================

    st.subheader(
        "🛡️ Safety Checks"
    )

    checks = [

        (
            "5m data available",
            True
        ),

        (
            "Closed candle",
            True
        ),

        (
            "Fresh data",
            not stale
        ),

        (
            "Indicators ready",
            all(
                pd.notna(
                    row[k]
                )
                for k in [
                    "atr14",
                    "rsi14",
                    "ema12",
                    "ema26",
                    "macd_hist"
                ]
            )
        ),

        (
            "Normal candle",
            (
                pd.notna(
                    row["body_atr"]
                )
                and
                row["body_atr"] <= 3.5
            )
        ),

        (
            "Not sideways",
            row["regime"] != "SIDEWAYS"
        )
    ]

    for name, okay in checks:

        if okay:

            st.write(
                "✅ " + name
            )

        else:

            st.write(
                "❌ " + name
            )


    # ========================================================
    # BACKTEST
    # ========================================================

    st.divider()

    st.subheader(
        "📈 Recent 5m Backtest"
    )

    trades = backtest(
        raw,
        horizon=horizon,
        minimum=minimum,
        spread=spread
    )

    if one_trade:

        trades = non_overlap(
            trades
        )

    trades = (
        trades
        .tail(300)
        .reset_index(drop=True)
    )

    if trades.empty:

        st.info(
            "No qualifying setups "
            "with current strict filter."
        )

    else:

        stats = get_stats(
            trades
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Trades",
            stats["trades"]
        )

        col2.metric(
            "Win rate",
            f"{stats['winrate']*100:.1f}%"
        )

        col3.metric(
            "Max loss streak",
            stats["max_streak"]
        )

        col4, col5, col6 = st.columns(3)

        col4.metric(
            "Net pips",
            f"{stats['total_pips']:.1f}"
        )

        col5.metric(
            "Profit factor",
            (
                f"{stats['profit_factor']:.2f}"
                if np.isfinite(
                    stats["profit_factor"]
                )
                else "∞"
            )
        )

        col6.metric(
            "Max drawdown",
            f"{stats['max_dd']:.1f} pips"
        )

        st.dataframe(
            trades.tail(25),
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "⚠️ Backtest results are historical "
            "observations and do not guarantee "
            "future performance."
        )


except Exception as error:

    st.error(
        "LIVE DATA ERROR"
    )

    st.code(
        str(error)
    )

    st.info(
        "Live feed unavailable or stale. "
        "Refresh later and do not trade "
        "while the feed is unavailable."
    )


st.divider()

st.caption(
    "EUR/USD • LIVE MARKET ONLY • "
    "OTC DISABLED • NO AUTO TRADE"
)
