import streamlit as st
import pandas as pd
import numpy as np
import requests
import math

# ============================================================
# EUR/USD SIGNAL BOT V8
# QUALITY-FIRST • LIVE EUR/USD • 5M CLOSED CANDLE
# MANUAL SIGNAL ONLY • OTC DISABLED
# ============================================================

st.set_page_config(
    page_title="EUR/USD Signal Bot V8",
    page_icon="📊",
    layout="centered"
)

PIP = 0.0001
SYMBOL = "EURUSD=X"


# ============================================================
# BASIC HELPERS
# ============================================================

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


def wilson(wins, n, z=1.96):

    if n <= 0:
        return np.nan, np.nan

    p = wins / n

    den = 1 + (z * z / n)

    center = (
        p +
        (z * z / (2 * n))
    ) / den

    half = (
        z *
        math.sqrt(
            max(
                p * (1 - p) / n +
                z * z / (4 * n * n),
                0
            )
        )
    ) / den

    return center - half, center + half


# ============================================================
# LIVE DATA
# ============================================================

@st.cache_data(ttl=45, show_spinner=False)
def get_live_data():

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{SYMBOL}"
        "?range=5d&interval=5m&includePrePost=false"
    )

    response = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    result = response.json()[
        "chart"
    ]["result"][0]

    quote = result[
        "indicators"
    ]["quote"][0]

    timestamps = result.get(
        "timestamp",
        []
    )

    df = pd.DataFrame({
        "time": pd.to_datetime(
            timestamps,
            unit="s",
            utc=True
        ),
        "open": quote.get(
            "open",
            []
        ),
        "high": quote.get(
            "high",
            []
        ),
        "low": quote.get(
            "low",
            []
        ),
        "close": quote.get(
            "close",
            []
        ),
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

def add_indicators(df):

    x = df.copy()

    # ---------------- EMA ----------------

    x["ema12"] = (
        x["close"]
        .ewm(
            span=12,
            adjust=False
        )
        .mean()
    )

    x["ema26"] = (
        x["close"]
        .ewm(
            span=26,
            adjust=False
        )
        .mean()
    )

    x["ema50"] = (
        x["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    # ---------------- SMA ----------------

    x["sma20"] = (
        x["close"]
        .rolling(20)
        .mean()
    )

    # ---------------- RSI ----------------

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

    rs = (
        gain /
        loss.replace(0, np.nan)
    )

    x["rsi"] = (
        100 -
        (100 / (1 + rs))
    )

    # ---------------- ATR ----------------

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

    x["atr"] = (
        tr
        .rolling(14)
        .mean()
    )

    x["atr_median"] = (
        x["atr"]
        .shift(1)
        .rolling(100)
        .median()
    )

    # ---------------- Candle structure ----------------

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
        x["atr"].replace(0, np.nan)
    )

    x["close_location"] = (
        x["close"] -
        x["low"]
    ) / x["range"]

    # ---------------- MACD ----------------

    x["macd"] = (
        x["ema12"] -
        x["ema26"]
    )

    x["macd_signal"] = (
        x["macd"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    x["macd_hist"] = (
        x["macd"] -
        x["macd_signal"]
    )

    x["macd_hist_prev"] = (
        x["macd_hist"].shift(1)
    )

    # ---------------- Bollinger ----------------

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

    # ---------------- Candle runs ----------------

    bullish = (
        x["close"] >
        x["open"]
    )

    bearish = (
        x["close"] <
        x["open"]
    )

    x["bull_run"] = (
        bullish
        .groupby(
            (~bullish).cumsum()
        )
        .cumsum()
    )

    x["bear_run"] = (
        bearish
        .groupby(
            (~bearish).cumsum()
        )
        .cumsum()
    )

    # ---------------- Trend strength ----------------

    x["ema_gap"] = (
        x["ema12"] -
        x["ema26"]
    )

    x["ema_slope"] = (
        x["ema12"] -
        x["ema12"].shift(3)
    )

    x["trend_strength"] = (
        x["ema_gap"].abs() /
        x["atr"].replace(0, np.nan)
    )

    # ---------------- Market regime ----------------

    x["regime"] = np.where(

        x["trend_strength"] < 0.30,

        "SIDEWAYS",

        np.where(
            x["ema12"] >
            x["ema26"],

            "UPTREND",

            "DOWNTREND"
        )
    )

    return x


# ============================================================
# QUALITY SIGNAL ENGINE
# ============================================================

def get_signal(
    x,
    index,
    minimum_score=8
):

    if index < 120:

        return {
            "signal": "NO TRADE",
            "up": 0,
            "down": 0,
            "score": 0,
            "reason": "Not enough data"
        }

    r = x.iloc[index]

    required = [
        "atr",
        "atr_median",
        "body_atr",
        "close_location",
        "rsi",
        "ema12",
        "ema26",
        "ema50",
        "macd_hist",
        "bb_upper",
        "bb_lower"
    ]

    if any(
        pd.isna(r[k])
        for k in required
    ):

        return {
            "signal": "NO TRADE",
            "up": 0,
            "down": 0,
            "score": 0,
            "reason": "Indicators not ready"
        }

    # --------------------------------------------------------
    # Safety: abnormal candle
    # --------------------------------------------------------

    if r["body_atr"] > 3.0:

        return {
            "signal": "NO TRADE",
            "up": 0,
            "down": 0,
            "score": 0,
            "reason": "Abnormally large candle"
        }

    up = 0
    down = 0

    up_reason = []
    down_reason = []

    # ========================================================
    # UP SETUP
    # ========================================================

    # Strong bearish exhaustion
    if r["bear_run"] >= 4:

        up += 2

        up_reason.append(
            "4+ bearish candles"
        )

    # Strong bearish body
    if (
        r["body_atr"] >= 1.35
        and
        r["close"] < r["open"]
    ):

        up += 2

        up_reason.append(
            "strong bearish body"
        )

    # Close near low
    if (
        r["close_location"] <= 0.18
        and
        r["close"] < r["open"]
    ):

        up += 1

        up_reason.append(
            "close near low"
        )

    # Oversold
    if r["rsi"] <= 34:

        up += 2

        up_reason.append(
            "RSI oversold"
        )

    # Price below lower Bollinger
    if r["close"] <= r["bb_lower"]:

        up += 2

        up_reason.append(
            "below lower Bollinger"
        )

    # MACD improving
    if (
        r["macd_hist"] >
        r["macd_hist_prev"]
    ):

        up += 1

        up_reason.append(
            "MACD improving"
        )

    # ========================================================
    # DOWN SETUP
    # ========================================================

    # Strong bullish exhaustion
    if r["bull_run"] >= 4:

        down += 2

        down_reason.append(
            "4+ bullish candles"
        )

    # Strong bullish body
    if (
        r["body_atr"] >= 1.35
        and
        r["close"] > r["open"]
    ):

        down += 2

        down_reason.append(
            "strong bullish body"
        )

    # Close near high
    if (
        r["close_location"] >= 0.82
        and
        r["close"] > r["open"]
    ):

        down += 1

        down_reason.append(
            "close near high"
        )

    # Overbought
    if r["rsi"] >= 66:

        down += 2

        down_reason.append(
            "RSI overbought"
        )

    # Price above upper Bollinger
    if r["close"] >= r["bb_upper"]:

        down += 2

        down_reason.append(
            "above upper Bollinger"
        )

    # MACD weakening
    if (
        r["macd_hist"] <
        r["macd_hist_prev"]
    ):

        down += 1

        down_reason.append(
            "MACD weakening"
        )

    # ========================================================
    # MARKET REGIME PROTECTION
    # ========================================================

    # In strong trend, reversal needs extra confirmation.
    if r["regime"] == "UPTREND":

        down_required = minimum_score + 1

        if down >= down_required:

            return {
                "signal": "DOWN",
                "up": up,
                "down": down,
                "score": down,
                "reason": ", ".join(
                    down_reason
                )
            }

        return {
            "signal": "NO TRADE",
            "up": up,
            "down": down,
            "score": max(up, down),
            "reason":
                "UPTREND; reversal too weak"
        }

    if r["regime"] == "DOWNTREND":

        up_required = minimum_score + 1

        if up >= up_required:

            return {
                "signal": "UP",
                "up": up,
                "down": down,
                "score": up,
                "reason": ", ".join(
                    up_reason
                )
            }

        return {
            "signal": "NO TRADE",
            "up": up,
            "down": down,
            "score": max(up, down),
            "reason":
                "DOWNTREND; reversal too weak"
        }

    # SIDEWAYS
    return {
        "signal": "NO TRADE",
        "up": up,
        "down": down,
        "score": max(up, down),
        "reason": "SIDEWAYS market"
    }


# ============================================================
# BACKTEST
# ============================================================

def backtest(
    df,
    horizon=1,
    minimum_score=8,
    spread=1.2
):

    x = add_indicators(df)

    trades = []

    for i in range(
        120,
        len(x) -
        horizon -
        1
    ):

        result = get_signal(
            x,
            i,
            minimum_score
        )

        signal = result["signal"]

        if signal not in (
            "UP",
            "DOWN"
        ):
            continue

        entry_index = i + 1
        exit_index = i + horizon

        entry = float(
            x.iloc[
                entry_index
            ]["open"]
        )

        exit_price = float(
            x.iloc[
                exit_index
            ]["close"]
        )

        direction = (
            1
            if signal == "UP"
            else -1
        )

        gross_pips = (
            (
                exit_price -
                entry
            )
            /
            PIP
            *
            direction
        )

        net_pips = (
            gross_pips -
            spread
        )

        trades.append({

            "signal_time":
                x.iloc[i]["time"],

            "entry_time":
                x.iloc[
                    entry_index
                ]["time"],

            "exit_time":
                x.iloc[
                    exit_index
                ]["time"],

            "signal":
                signal,

            "score":
                result["score"],

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
        })

    return pd.DataFrame(
        trades
    )


# ============================================================
# REMOVE OVERLAPPING TRADES
# ============================================================

def non_overlap(trades):

    if trades.empty:
        return trades

    keep = []

    last_exit = None

    for index, row in trades.iterrows():

        if (
            last_exit is None
            or
            row["entry_time"] >
            last_exit
        ):

            keep.append(index)

            last_exit = (
                row["exit_time"]
            )

    return (
        trades
        .loc[keep]
        .reset_index(drop=True)
    )


# ============================================================
# STATISTICS
# ============================================================

def calculate_stats(trades):

    if trades.empty:
        return None

    n = len(trades)

    wins = int(
        trades["win"].sum()
    )

    losses = n - wins

    winrate = (
        wins / n
    )

    low, high = wilson(
        wins,
        n
    )

    # Equity starts at zero.
    equity = np.r_[
        0.0,
        trades[
            "net_pips"
        ]
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

    profit_factor = (
        positive / negative
        if negative > 0
        else np.inf
    )

    return {

        "trades":
            n,

        "wins":
            wins,

        "losses":
            losses,

        "winrate":
            winrate,

        "low":
            low,

        "high":
            high,

        "total_pips":
            float(
                trades[
                    "net_pips"
                ].sum()
            ),

        "avg_pips":
            float(
                trades[
                    "net_pips"
                ].mean()
            ),

        "profit_factor":
            profit_factor,

        "max_dd":
            max_dd,

        "max_streak":
            max_loss_streak(
                trades[
                    "win"
                ]
            )
    }


# ============================================================
# VALIDATION
# ============================================================

def validation_report(
    trades,
    holdout_percent=30
):

    if trades.empty:
        return None, None

    split = int(
        len(trades) *
        (1 -
         holdout_percent / 100)
    )

    if split < 10:
        return None, None

    train = (
        trades
        .iloc[:split]
        .copy()
    )

    holdout = (
        trades
        .iloc[split:]
        .copy()
    )

    return train, holdout


# ============================================================
# UI
# ============================================================

st.title(
    "📊 EUR/USD SIGNAL BOT V8"
)

st.caption(
    "QUALITY-FIRST • LIVE EUR/USD • 5M CLOSED CANDLE"
)

with st.sidebar:

    st.header(
        "⚙️ Bot Settings"
    )

    minimum_score = st.slider(
        "Minimum signal score",
        min_value=8,
        max_value=10,
        value=8,
        step=1
    )

    horizon = st.selectbox(
        "Backtest expiry",
        [1, 2, 3],
        index=0
    )

    spread = st.number_input(
        "Estimated cost (pips)",
        min_value=0.0,
        max_value=5.0,
        value=1.2,
        step=0.1
    )

    holdout_percent = st.slider(
        "Holdout %",
        min_value=20,
        max_value=40,
        value=30,
        step=5
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
        "🔒 AUTO TRADE DISABLED"
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
# LIVE ANALYSIS
# ============================================================

try:

    raw = get_live_data()

    data = add_indicators(
        raw
    )

    if len(data) < 150:

        st.error(
            "Not enough 5-minute data."
        )

        st.stop()

    now = pd.Timestamp.now(
        tz="UTC"
    )

    latest = data.iloc[-1]

    candle_end = (
        latest["time"].floor("5min")
        +
        pd.Timedelta(minutes=5)
    )

    # Use only CLOSED candle.
    if now < candle_end:

        signal_index = (
            len(data) - 2
        )

    else:

        signal_index = (
            len(data) - 1
        )

    row = data.iloc[
        signal_index
    ]

    age_minutes = (
        now -
        row["time"]
    ).total_seconds() / 60

    # --------------------------------------------------------
    # STALE DATA PROTECTION
    # --------------------------------------------------------

    stale = (
        age_minutes > 20
    )

    st.subheader(
        "🟢 LIVE EUR/USD"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "PRICE",
        f"{row['close']:.5f}"
    )

    c2.metric(
        "RSI",
        (
            f"{row['rsi']:.1f}"
            if pd.notna(row["rsi"])
            else "—"
        )
    )

    c3.metric(
        "ATR",
        (
            f"{row['atr']/PIP:.1f} pips"
            if pd.notna(row["atr"])
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
        f"{age_minutes:.1f} minutes"
    )

    if stale:

        st.error(
            "🔴 DATA STALE — NO SIGNAL"
        )

        st.stop()


    # --------------------------------------------------------
    # SIGNAL
    # --------------------------------------------------------

    result = get_signal(
        data,
        signal_index,
        minimum_score
    )

    signal = result[
        "signal"
    ]

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
        f"**Market:** "
        f"{row['regime']}"
    )

    st.write(
        f"**UP score:** "
        f"{result['up']}"
    )

    st.write(
        f"**DOWN score:** "
        f"{result['down']}"
    )

    st.write(
        f"**Final score:** "
        f"{result['score']}"
    )

    st.write(
        f"**Reason:** "
        f"{result['reason']}"
    )


    # ========================================================
    # SAFETY CHECKS
    # ========================================================

    st.subheader(
        "🛡️ Safety Checks"
    )

    checks = [

        (
            "5-minute data",
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
                    "atr",
                    "rsi",
                    "ema12",
                    "ema26",
                    "ema50",
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
                row["body_atr"] <= 3
            )
        ),

        (
            "Not sideways",
            row["regime"] != "SIDEWAYS"
        ),

        (
            "Score threshold",
            result["score"] >= minimum_score
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
        "📈 V8 BACKTEST"
    )

    trades = backtest(
        raw,
        horizon=horizon,
        minimum_score=minimum_score,
        spread=spread
    )

    if one_trade:

        trades = non_overlap(
            trades
        )

    if trades.empty:

        st.warning(
            "No qualifying setups."
        )

    else:

        train, holdout = (
            validation_report(
                trades,
                holdout_percent
            )
        )

        # ----------------------------------------------------
        # FULL
        # ----------------------------------------------------

        st.markdown(
            "### Overall"
        )

        overall_stats = (
            calculate_stats(
                trades
            )
        )

        a, b, c = st.columns(3)

        a.metric(
            "Trades",
            overall_stats["trades"]
        )

        b.metric(
            "Win rate",
            (
                f"{overall_stats['winrate']*100:.1f}%"
            )
        )

        c.metric(
            "Loss streak",
            overall_stats["max_streak"]
        )

        # ----------------------------------------------------
        # TRAIN
        # ----------------------------------------------------

        if train is not None:

            st.markdown(
                "### Training period"
            )

            train_stats = (
                calculate_stats(
                    train
                )
            )

            a, b, c = st.columns(3)

            a.metric(
                "Trades",
                train_stats["trades"]
            )

            b.metric(
                "Win rate",
                (
                    f"{train_stats['winrate']*100:.1f}%"
                )
            )

            c.metric(
                "Max DD",
                (
                    f"{train_stats['max_dd']:.1f}"
                )
            )

            # ------------------------------------------------
            # HOLDOUT
            # ------------------------------------------------

            st.markdown(
                "### 🔬 Out-of-sample holdout"
            )

            holdout_stats = (
                calculate_stats(
                    holdout
                )
            )

            a, b, c = st.columns(3)

            a.metric(
                "Trades",
                holdout_stats["trades"]
            )

            b.metric(
                "Win rate",
                (
                    f"{holdout_stats['winrate']*100:.1f}%"
                )
            )

            c.metric(
                "Max DD",
                (
                    f"{holdout_stats['max_dd']:.1f}"
                )
            )

            # ------------------------------------------------
            # VALIDATION STATUS
            # ------------------------------------------------

            if (
                holdout_stats["trades"] >= 20
                and
                holdout_stats["winrate"] >= 0.56
                and
                holdout_stats["total_pips"] > 0
            ):

                st.success(
                    "🟢 HOLDOUT PASSED — "
                    "historical evidence is acceptable"
                )

            else:

                st.warning(
                    "🟡 HOLDOUT NOT STRONG ENOUGH — "
                    "NO automatic confidence upgrade"
                )

        # ----------------------------------------------------
        # TRADE TABLE
        # ----------------------------------------------------

        st.markdown(
            "### Recent qualifying trades"
        )

        st.dataframe(
            trades.tail(30),
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "⚠️ Holdout results are historical evidence, "
            "not a guarantee of future wins."
        )


except Exception as error:

    st.error(
        "LIVE DATA ERROR"
    )

    st.code(
        str(error)
    )

    st.info(
        "Data feed unavailable/stale. "
        "Do not trade until fresh data returns."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "EUR/USD • LIVE MARKET ONLY • "
    "OTC DISABLED • MANUAL SIGNAL ONLY • "
    "NO AUTO TRADE"
)
