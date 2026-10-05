import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime as dt
import json
import os
import math

# ============================================================
# EUR/USD SIGNAL PRO V8
# Bright Professional Dashboard | Manual Only | Demo First
# ============================================================

st.set_page_config(
    page_title="EUR/USD Signal PRO V8",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)

SYMBOL = "EURUSD=X"
PIP = 0.0001
JOURNAL_FILE = "eurusd_v8_journal.json"

TIMEFRAMES = {
    "1m": {
        "interval": "1m",
        "range": "7d",
        "minutes": 1,
        "htf": "5m"
    },
    "5m": {
        "interval": "5m",
        "range": "60d",
        "minutes": 5,
        "htf": "15m"
    },
    "15m": {
        "interval": "15m",
        "range": "60d",
        "minutes": 15,
        "htf": "60m"
    }
}

HTF = {
    "5m": {
        "interval": "5m",
        "range": "60d"
    },
    "15m": {
        "interval": "15m",
        "range": "60d"
    },
    "60m": {
        "interval": "60m",
        "range": "1y"
    }
}

# ============================================================
# BRIGHT PROFESSIONAL UI
# ============================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        180deg,
        #f5fbff 0%,
        #ffffff 45%,
        #f7fbff 100%
    );
}

.block-container {
    max-width: 980px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}

.hero {
    background: linear-gradient(
        135deg,
        #0066ff,
        #00b8ff
    );
    color: white;
    padding: 22px 20px;
    border-radius: 22px;
    box-shadow: 0 10px 30px rgba(0,102,255,.20);
    margin-bottom: 14px;
}

.hero h1 {
    margin: 0;
    font-size: 30px;
    font-weight: 850;
}

.hero p {
    margin: 6px 0 0 0;
    font-size: 14px;
    opacity: .95;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 16px;
    border: 1px solid #dcecff;
    box-shadow: 0 6px 22px rgba(25,80,140,.08);
    margin: 10px 0;
}

.green-card {
    background: linear-gradient(
        135deg,
        #e9fff3,
        #ffffff
    );
    border: 2px solid #17b26a;
}

.red-card {
    background: linear-gradient(
        135deg,
        #fff0f0,
        #ffffff
    );
    border: 2px solid #ef4444;
}

.yellow-card {
    background: linear-gradient(
        135deg,
        #fff9df,
        #ffffff
    );
    border: 2px solid #f2b705;
}

.blue-card {
    background: linear-gradient(
        135deg,
        #eaf5ff,
        #ffffff
    );
    border: 2px solid #1683ff;
}

.big-signal {
    text-align: center;
    font-size: 38px;
    font-weight: 900;
    padding: 22px 10px 5px;
}

.signal-sub {
    text-align: center;
    font-size: 14px;
    font-weight: 700;
    padding-bottom: 18px;
}

.section-title {
    color: #075fc7;
    font-weight: 850;
    font-size: 21px;
    margin-top: 20px;
}

.small-note {
    color: #65758b;
    font-size: 12px;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #dcecff;
    padding: 10px;
    border-radius: 15px;
    box-shadow: 0 4px 15px rgba(25,80,140,.06);
}

.stButton > button {
    border-radius: 12px;
    font-weight: 800;
}

hr {
    border: none;
    border-top: 1px solid #dbe8f5;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="hero">
    <h1>📈 EUR/USD SIGNAL PRO V8</h1>
    <p>
        Professional Manual Signal Terminal •
        Closed Candle • Capital Protection
    </p>
</div>
""", unsafe_allow_html=True)

st.info(
    "⚠️ DEMO-FIRST: This app is analysis software only. "
    "It does not place trades and does not guarantee profit. "
    "External feed prices may differ from your broker."
)

# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def safe_float(value, default=np.nan):
    try:
        return float(value)
    except Exception:
        return default


def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []

    try:
        with open(
            JOURNAL_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except Exception:
        return []


def save_journal(data):
    try:
        with open(
            JOURNAL_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                indent=2
            )

        return True

    except Exception:
        return False


def today_records(journal):
    today = utc_now().date().isoformat()

    return [
        r for r in journal
        if str(
            r.get("date", "")
        ).startswith(today)
    ]


def timeframe_minutes(tf):
    return TIMEFRAMES[tf]["minutes"]


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(
    ttl=30,
    show_spinner=False
)
def fetch_yahoo(
    interval,
    period
):

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{SYMBOL}?interval={interval}&range={period}"
    )

    try:

        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        payload = response.json()

        result = payload[
            "chart"
        ][
            "result"
        ][0]

        timestamps = result.get(
            "timestamp",
            []
        )

        quote = result[
            "indicators"
        ][
            "quote"
        ][0]

        if not timestamps:
            return pd.DataFrame()

        df = pd.DataFrame({
            "time": pd.to_datetime(
                timestamps,
                unit="s",
                utc=True
            ),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        })

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close"
            ]
        ).copy()

        df = df.sort_values(
            "time"
        )

        df = df.drop_duplicates(
            "time"
        )

        return df.reset_index(
            drop=True
        )

    except Exception:
        return pd.DataFrame()


# ============================================================
# DATA QUALITY
# ============================================================

def data_quality(
    df,
    tf
):

    if df.empty:
        return (
            False,
            "No market data.",
            None
        )

    if len(df) < 180:
        return (
            False,
            f"Only {len(df)} candles available.",
            None
        )

    expected = timeframe_minutes(tf)

    diffs = (
        df["time"]
        .diff()
        .dropna()
        .dt.total_seconds()
        / 60
    )

    normal = diffs[
        diffs <= expected * 4
    ]

    spacing = (
        float(normal.median())
        if not normal.empty
        else None
    )

    if spacing is not None:

        if abs(
            spacing - expected
        ) > max(
            1.0,
            expected * 0.35
        ):

            return (
                False,
                f"Timeframe mismatch: expected "
                f"~{expected}m, detected "
                f"~{spacing:.1f}m.",
                spacing
            )

    bad = (
        (df["high"] < df["low"]) |
        (df["open"] > df["high"]) |
        (df["open"] < df["low"]) |
        (df["close"] > df["high"]) |
        (df["close"] < df["low"])
    )

    if bad.any():

        return (
            False,
            "Invalid OHLC candle detected.",
            spacing
        )

    return (
        True,
        "Data quality OK.",
        spacing
    )


# ============================================================
# CLOSED CANDLE
# ============================================================

def closed_index(
    df,
    tf
):

    if df.empty:
        return None

    minutes = timeframe_minutes(tf)

    last_open = (
        df["time"]
        .iloc[-1]
        .to_pydatetime()
    )

    last_close = (
        last_open +
        dt.timedelta(
            minutes=minutes
        )
    )

    if utc_now() >= last_close:
        return len(df) - 1

    if len(df) >= 2:
        return len(df) - 2

    return None


def feed_status(
    df,
    tf
):

    idx = closed_index(
        df,
        tf
    )

    if idx is None:
        return (
            False,
            "NO CLOSED CANDLE"
        )

    candle_time = (
        df["time"]
        .iloc[idx]
        .to_pydatetime()
    )

    age_minutes = (
        utc_now() -
        candle_time
    ).total_seconds() / 60

    limit = max(
        15,
        timeframe_minutes(tf) * 4
    )

    if age_minutes > limit:

        return (
            False,
            f"STALE DATA • "
            f"{age_minutes:.1f}m old"
        )

    return (
        True,
        f"DATA OK • "
        f"{age_minutes:.1f}m"
    )


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):

    x = df.copy()

    # EMA
    x["ema9"] = (
        x["close"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    x["ema21"] = (
        x["close"]
        .ewm(
            span=21,
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

    # RSI
    delta = x["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    avg_loss = (
        loss
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    x["rsi"] = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    # ATR
    prev_close = x[
        "close"
    ].shift(1)

    tr = pd.concat(
        [
            x["high"] - x["low"],
            (
                x["high"] -
                prev_close
            ).abs(),
            (
                x["low"] -
                prev_close
            ).abs(),
        ],
        axis=1
    ).max(
        axis=1
    )

    x["atr"] = (
        tr
        .ewm(
            span=14,
            adjust=False
        )
        .mean()
    )

    x["atr_med"] = (
        x["atr"]
        .rolling(
            100
        )
        .median()
    )

    # Bollinger
    x["bb_mid"] = (
        x["close"]
        .rolling(
            20
        )
        .mean()
    )

    bb_std = (
        x["close"]
        .rolling(
            20
        )
        .std()
    )

    x["bb_upper"] = (
        x["bb_mid"] +
        2 * bb_std
    )

    x["bb_lower"] = (
        x["bb_mid"] -
        2 * bb_std
    )

    # MACD
    ema12 = (
        x["close"]
        .ewm(
            span=12,
            adjust=False
        )
        .mean()
    )

    ema26 = (
        x["close"]
        .ewm(
            span=26,
            adjust=False
        )
        .mean()
    )

    x["macd"] = (
        ema12 -
        ema26
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

    # Stochastic
    low14 = (
        x["low"]
        .rolling(
            14
        )
        .min()
    )

    high14 = (
        x["high"]
        .rolling(
            14
        )
        .max()
    )

    denom = (
        high14 -
        low14
    ).replace(
        0,
        np.nan
    )

    x["stoch"] = (
        100 *
        (
            x["close"] -
            low14
        ) /
        denom
    )

    # ADX
    up_move = (
        x["high"]
        .diff()
    )

    down_move = (
        -x["low"]
        .diff()
    )

    plus_dm = np.where(
        (
            up_move >
            down_move
        ) &
        (
            up_move > 0
        ),
        up_move,
        0
    )

    minus_dm = np.where(
        (
            down_move >
            up_move
        ) &
        (
            down_move > 0
        ),
        down_move,
        0
    )

    atr14 = (
        x["atr"]
        .replace(
            0,
            np.nan
        )
    )

    plus_di = (
        100 *
        pd.Series(
            plus_dm,
            index=x.index
        )
        .ewm(
            span=14,
            adjust=False
        )
        .mean()
        /
        atr14
    )

    minus_di = (
        100 *
        pd.Series(
            minus_dm,
            index=x.index
        )
        .ewm(
            span=14,
            adjust=False
        )
        .mean()
        /
        atr14
    )

    dx = (
        100 *
        (
            plus_di -
            minus_di
        ).abs()
        /
        (
            plus_di +
            minus_di
        ).replace(
            0,
            np.nan
        )
    )

    x["adx"] = (
        dx
        .ewm(
            span=14,
            adjust=False
        )
        .mean()
    )

    # Candle
    x["body"] = (
        x["close"] -
        x["open"]
    )

    x["range"] = (
        x["high"] -
        x["low"]
    )

    x["close_location"] = (
        (
            x["close"] -
            x["low"]
        )
        /
        x["range"].replace(
            0,
            np.nan
        )
    )

    x["upper_wick"] = (
        x["high"] -
        x[
            ["open", "close"]
        ].max(
            axis=1
        )
    )

    x["lower_wick"] = (
        x[
            ["open", "close"]
        ].min(
            axis=1
        ) -
        x["low"]
    )

    x["atr_ratio"] = (
        x["atr"] /
        x["atr_med"].replace(
            0,
            np.nan
        )
    )

    return x.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )


# ============================================================
# HIGHER TIMEFRAME
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)
def higher_timeframe_trend(
    htf
):

    cfg = HTF[htf]

    df = fetch_yahoo(
        cfg["interval"],
        cfg["range"]
    )

    if (
        df.empty or
        len(df) < 100
    ):
        return "UNKNOWN"

    x = add_indicators(
        df
    )

    row = x.iloc[-2]

    if (
        pd.isna(
            row["ema21"]
        ) or
        pd.isna(
            row["ema50"]
        )
    ):
        return "UNKNOWN"

    if (
        row["ema21"] >
        row["ema50"] and
        row["close"] >
        row["ema21"]
    ):
        return "UP"

    if (
        row["ema21"] <
        row["ema50"] and
        row["close"] <
        row["ema21"]
    ):
        return "DOWN"

    return "NEUTRAL"


# ============================================================
# MARKET REGIME
# ============================================================

def regime(row):

    adx = safe_float(
        row["adx"]
    )

    atr_ratio = safe_float(
        row["atr_ratio"],
        1.0
    )

    if np.isnan(adx):
        return "UNKNOWN"

    if atr_ratio > 2.2:
        return "VOLATILITY SPIKE"

    if adx >= 23:

        if (
            row["ema21"] >
            row["ema50"] and
            row["close"] >
            row["ema21"]
        ):
            return "UPTREND"

        if (
            row["ema21"] <
            row["ema50"] and
            row["close"] <
            row["ema21"]
        ):
            return "DOWNTREND"

        return "TRANSITION"

    if adx <= 17:
        return "RANGE"

    return "SIDEWAYS"


# ============================================================
# SIGNAL ENGINE
# ============================================================

def signal_engine(
    x,
    idx,
    htf
):

    if idx is None:

        return {
            "side": "NO TRADE",
            "score": 0,
            "setup": "NONE",
            "regime": "UNKNOWN",
            "reasons": [
                "No closed candle."
            ],
        }

    row = x.iloc[idx]

    needed = [
        "close",
        "ema9",
        "ema21",
        "ema50",
        "rsi",
        "atr",
        "atr_med",
        "adx",
        "bb_upper",
        "bb_lower",
        "macd_hist",
        "stoch",
        "close_location",
    ]

    if any(
        pd.isna(
            row[c]
        )
        for c in needed
    ):

        return {
            "side": "NO TRADE",
            "score": 0,
            "setup": "DATA INCOMPLETE",
            "regime": "UNKNOWN",
            "reasons": [
                "Indicators are not ready."
            ],
        }

    r = regime(
        row
    )

    reasons = []

    up = 0
    down = 0

    setup = "NONE"

    atr_ratio = safe_float(
        row["atr_ratio"],
        1.0
    )

    # Volatility filter
    if atr_ratio > 2.0:

        return {
            "side": "NO TRADE",
            "score": 0,
            "setup": "VOLATILITY FILTER",
            "regime": r,
            "reasons": [
                "Abnormally high volatility."
            ],
        }

    if atr_ratio < 0.35:

        return {
            "side": "NO TRADE",
            "score": 0,
            "setup": "LOW VOLATILITY",
            "regime": r,
            "reasons": [
                "Market movement is too weak."
            ],
        }

    # Trend
    if (
        r in (
            "UPTREND",
            "DOWNTREND"
        )
        and
        row["adx"] >= 23
    ):

        setup = "TREND PULLBACK"

        # UP
        if (
            row["ema21"] >
            row["ema50"]
        ):

            checks = [
                (
                    row["close"] >
                    row["ema21"],
                    "Price above EMA21"
                ),
                (
                    row["ema9"] >
                    row["ema21"],
                    "EMA9 above EMA21"
                ),
                (
                    48 <=
                    row["rsi"] <= 68,
                    "Bullish RSI zone"
                ),
                (
                    row["macd_hist"] > 0,
                    "Positive MACD"
                ),
                (
                    row["stoch"] > 45,
                    "Bullish stochastic"
                ),
                (
                    row["close_location"] >= 0.60,
                    "Strong candle close"
                ),
                (
                    row["adx"] >= 25,
                    "Strong ADX"
                ),
                (
                    row["body"] > 0,
                    "Bullish candle"
                ),
            ]

            for ok, text in checks:

                if ok:
                    up += 1
                    reasons.append(
                        text
                    )

        # DOWN
        elif (
            row["ema21"] <
            row["ema50"]
        ):

            checks = [
                (
                    row["close"] <
                    row["ema21"],
                    "Price below EMA21"
                ),
                (
                    row["ema9"] <
                    row["ema21"],
                    "EMA9 below EMA21"
                ),
                (
                    32 <=
                    row["rsi"] <= 52,
                    "Bearish RSI zone"
                ),
                (
                    row["macd_hist"] < 0,
                    "Negative MACD"
                ),
                (
                    row["stoch"] < 55,
                    "Bearish stochastic"
                ),
                (
                    row["close_location"] <= 0.40,
                    "Weak candle close"
                ),
                (
                    row["adx"] >= 25,
                    "Strong ADX"
                ),
                (
                    row["body"] < 0,
                    "Bearish candle"
                ),
            ]

            for ok, text in checks:

                if ok:
                    down += 1
                    reasons.append(
                        text
                    )

    # Range reversal
    elif r == "RANGE":

        setup = "RANGE REVERSAL"

        # UP
        if (
            row["close"] <=
            row["bb_lower"]
            and
            row["rsi"] <= 35
            and
            row["stoch"] <= 25
        ):

            checks = [
                (
                    row["close"] <=
                    row["bb_lower"],
                    "Lower BB extreme"
                ),
                (
                    row["rsi"] <= 35,
                    "Oversold RSI"
                ),
                (
                    row["stoch"] <= 25,
                    "Oversold stochastic"
                ),
                (
                    row["lower_wick"] >
                    row["upper_wick"],
                    "Lower rejection wick"
                ),
                (
                    row["close_location"] >= 0.50,
                    "Recovery close"
                ),
            ]

            for ok, text in checks:

                if ok:
                    up += 1
                    reasons.append(
                        text
                    )

        # DOWN
        elif (
            row["close"] >=
            row["bb_upper"]
            and
            row["rsi"] >= 65
            and
            row["stoch"] >= 75
        ):

            checks = [
                (
                    row["close"] >=
                    row["bb_upper"],
                    "Upper BB extreme"
                ),
                (
                    row["rsi"] >= 65,
                    "Overbought RSI"
                ),
                (
                    row["stoch"] >= 75,
                    "Overbought stochastic"
                ),
                (
                    row["upper_wick"] >
                    row["lower_wick"],
                    "Upper rejection wick"
                ),
                (
                    row["close_location"] <= 0.50,
                    "Weak recovery close"
                ),
            ]

            for ok, text in checks:

                if ok:
                    down += 1
                    reasons.append(
                        text
                    )

    else:

        return {
            "side": "NO TRADE",
            "score": 0,
            "setup": "NO SETUP",
            "regime": r,
            "reasons": [
                "Market is sideways or transitioning."
            ],
        }

    # HTF confirmation
    if htf == "UP":

        up += 1

        reasons.append(
            "Higher timeframe UP"
        )

    elif htf == "DOWN":

        down += 1

        reasons.append(
            "Higher timeframe DOWN"
        )

    score = max(
        up,
        down
    )

    if (
        up >= 7 and
        up > down
    ):

        return {
            "side": "UP",
            "score": up,
            "setup": setup,
            "regime": r,
            "reasons": reasons,
        }

    if (
        down >= 7 and
        down > up
    ):

        return {
            "side": "DOWN",
            "score": down,
            "setup": setup,
            "regime": r,
            "reasons": reasons,
        }

    return {
        "side": "NO TRADE",
        "score": score,
        "setup": setup,
        "regime": r,
        "reasons": [
            f"UP {up}/9 • DOWN {down}/9",
            "Strong confirmation not reached.",
        ],
    }


# ============================================================
# BACKTEST
# ============================================================

def backtest(
    df,
    min_score=7,
    horizon=1
):

    if len(df) < 300:
        return pd.DataFrame()

    x = add_indicators(
        df
    )

    trades = []

    for i in range(
        180,
        len(x) - horizon - 1
    ):

        row = x.iloc[i]

        if pd.isna(
            row["adx"]
        ):
            continue

        r = regime(
            row
        )

        up = 0
        down = 0

        if r == "UPTREND":

            checks = [
                row["close"] >
                row["ema21"],

                row["ema9"] >
                row["ema21"],

                48 <=
                row["rsi"] <= 68,

                row["macd_hist"] > 0,

                row["stoch"] > 45,

                row["close_location"] >= 0.60,

                row["adx"] >= 25,

                row["body"] > 0,
            ]

            up = sum(
                checks
            )

        elif r == "DOWNTREND":

            checks = [
                row["close"] <
                row["ema21"],

                row["ema9"] <
                row["ema21"],

                32 <=
                row["rsi"] <= 52,

                row["macd_hist"] < 0,

                row["stoch"] < 55,

                row["close_location"] <= 0.40,

                row["adx"] >= 25,

                row["body"] < 0,
            ]

            down = sum(
                checks
            )

        elif r == "RANGE":

            if (
                row["close"] <=
                row["bb_lower"]
                and
                row["rsi"] <= 35
                and
                row["stoch"] <= 25
            ):

                up = 5

            elif (
                row["close"] >=
                row["bb_upper"]
                and
                row["rsi"] >= 65
                and
                row["stoch"] >= 75
            ):

                down = 5

        if (
            up >= min_score
            and
            up > down
        ):

            side = "UP"
            score = up

        elif (
            down >= min_score
            and
            down > up
        ):

            side = "DOWN"
            score = down

        else:
            continue

        entry_i = i + 1
        exit_i = i + horizon

        entry = (
            x.iloc[entry_i]["open"]
        )

        exit_price = (
            x.iloc[exit_i]["close"]
        )

        if side == "UP":

            pnl = (
                exit_price -
                entry
            )

        else:

            pnl = (
                entry -
                exit_price
            )

        if pnl > 0:
            result = "WIN"

        elif pnl < 0:
            result = "LOSS"

        else:
            result = "TIE"

        trades.append({
            "time": x.iloc[i]["time"],
            "side": side,
            "score": score,
            "result": result,
            "pips": pnl / PIP,
        })

    return pd.DataFrame(
        trades
    )


# ============================================================
# STATISTICS
# ============================================================

def wilson_lower(
    wins,
    total,
    z=1.96
):

    if total <= 0:
        return 0.0

    p = (
        wins /
        total
    )

    denominator = (
        1 +
        z * z /
        total
    )

    centre = (
        p +
        z * z /
        (
            2 * total
        )
    )

    spread = (
        z *
        math.sqrt(
            p *
            (1 - p) /
            total
            +
            z * z /
            (
                4 *
                total *
                total
            )
        )
    )

    return (
        centre -
        spread
    ) / denominator


def stats_for(
    trades,
    payout
):

    if trades.empty:

        return {
            "n": 0,
            "wins": 0,
            "losses": 0,
            "accuracy": 0.0,
            "ev": 0.0,
            "lower": 0.0,
            "break_even":
                1 / (1 + payout),
        }

    wins = int(
        (
            trades["result"] ==
            "WIN"
        ).sum()
    )

    losses = int(
        (
            trades["result"] ==
            "LOSS"
        ).sum()
    )

    total = (
        wins +
        losses
    )

    if total == 0:

        accuracy = 0.0
        ev = 0.0
        lower = 0.0

    else:

        accuracy = (
            wins /
            total
        )

        ev = (
            accuracy *
            payout -
            (
                1 -
                accuracy
            )
        )

        lower = wilson_lower(
            wins,
            total
        )

    return {
        "n": total,
        "wins": wins,
        "losses": losses,
        "accuracy": accuracy,
        "ev": ev,
        "lower": lower,
        "break_even":
            1 / (1 + payout),
    }


# ============================================================
# OUT OF SAMPLE VALIDATION
# ============================================================

def validation(
    df,
    payout
):

    if len(df) < 500:
        return None

    split = int(
        len(df) * 0.70
    )

    train = df.iloc[
        :split
    ].copy()

    test = df.iloc[
        split:
    ].copy()

    train_trades = backtest(
        train
    )

    test_trades = backtest(
        test
    )

    train_stats = stats_for(
        train_trades,
        payout
    )

    test_stats = stats_for(
        test_trades,
        payout
    )

    active = (
        test_stats["n"] >= 100
        and
        test_stats["ev"] > 0
        and
        test_stats["accuracy"] >
        test_stats["break_even"]
    )

    return {
        "train": train_stats,
        "test": test_stats,
        "active": active,
        "test_trades": test_trades,
    }


# ============================================================
# RISK GUARD
# ============================================================

def risk_guard(
    journal,
    daily_limit,
    max_losses,
    max_trades
):

    records = today_records(
        journal
    )

    pnl = sum(
        safe_float(
            r.get(
                "pnl",
                0
            ),
            0
        )
        for r in records
    )

    streak = 0

    for r in reversed(
        records
    ):

        if (
            r.get("result") ==
            "LOSS"
        ):

            streak += 1

        else:

            break

    if (
        pnl <=
        -abs(
            daily_limit
        )
    ):

        return (
            False,
            "DAILY LOSS LIMIT HIT",
            pnl,
            streak
        )

    if (
        streak >=
        max_losses
    ):

        return (
            False,
            "CONSECUTIVE LOSS STOP",
            pnl,
            streak
        )

    if (
        len(records) >=
        max_trades
    ):

        return (
            False,
            "MAX TRADES REACHED",
            pnl,
            streak
        )

    return (
        True,
        "RISK GUARD ACTIVE",
        pnl,
        streak
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    "## ⚙️ TERMINAL SETTINGS"
)

tf = st.sidebar.selectbox(
    "📌 Timeframe",
    [
        "1m",
        "5m",
        "15m"
    ],
    index=1
)

payout = st.sidebar.slider(
    "💰 Assumed payout",
    0.70,
    0.95,
    0.85,
    0.01
)

balance = st.sidebar.number_input(
    "💵 Demo balance",
    min_value=0.0,
    value=1000.0,
    step=100.0
)

stake_pct = st.sidebar.slider(
    "🛡️ Max demo stake %",
    0.1,
    2.0,
    0.5,
    0.1
)

daily_limit = st.sidebar.number_input(
    "🛑 Daily loss limit",
    min_value=0.0,
    value=20.0,
    step=5.0
)

max_losses = st.sidebar.number_input(
    "🔴 Max consecutive losses",
    min_value=1,
    max_value=5,
    value=2,
    step=1
)

max_trades = st.sidebar.number_input(
    "📊 Max trades/day",
    min_value=1,
    max_value=20,
    value=6,
    step=1
)

news_blackout = st.sidebar.checkbox(
    "🚫 Manual news blackout",
    value=False
)

if st.sidebar.button(
    "🔄 REFRESH DATA",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(
    "---"
)

st.sidebar.markdown(
    "**Mode:** 🟢 Manual Only  \n"
    "**Market:** EUR/USD  \n"
    "**OTC:** 🔴 OFF  \n"
    "**Martingale:** 🔴 OFF"
)

# ============================================================
# LOAD DATA
# ============================================================

cfg = TIMEFRAMES[
    tf
]

with st.spinner(
    "📡 Loading market data..."
):

    df = fetch_yahoo(
        cfg["interval"],
        cfg["range"]
    )

ok, quality_message, spacing = data_quality(
    df,
    tf
)

if not ok:

    st.error(
        f"❌ {quality_message}"
    )

    st.stop()

feed_ok, feed_message = feed_status(
    df,
    tf
)

x = add_indicators(
    df
)

idx = closed_index(
    x,
    tf
)

if idx is None:

    st.error(
        "❌ No closed candle available."
    )

    st.stop()

row = x.iloc[
    idx
]

with st.spinner(
    "🔎 Checking higher timeframe..."
):

    htf = higher_timeframe_trend(
        cfg["htf"]
    )

signal = signal_engine(
    x,
    idx,
    htf
)

journal = load_journal()

risk_ok, risk_message, today_pnl, loss_streak = risk_guard(
    journal,
    daily_limit,
    max_losses,
    max_trades
)

validation_result = validation(
    df,
    payout
)

# ============================================================
# FINAL SAFETY GATE
# ============================================================

final_side = signal[
    "side"
]

gate = []

if not feed_ok:

    final_side = "NO TRADE"

    gate.append(
        feed_message
    )

if news_blackout:

    final_side = "NO TRADE"

    gate.append(
        "Manual news blackout is ON."
    )

if not risk_ok:

    final_side = "NO TRADE"

    gate.append(
        risk_message
    )

if signal["score"] < 7:

    final_side = "NO TRADE"

    gate.append(
        "Confluence below 7/9."
    )

if validation_result is None:

    gate.append(
        "Not enough history for OOS validation."
    )

# ============================================================
# MARKET STATUS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📡 MARKET STATUS'
    '</div>',
    unsafe_allow_html=True
)

m1, m2, m3 = st.columns(
    3
)

with m1:

    st.metric(
        "PRICE",
        f"{row['close']:.5f}"
    )

with m2:

    st.metric(
        "RSI",
        f"{row['rsi']:.1f}"
    )

with m3:

    st.metric(
        "ADX",
        f"{row['adx']:.1f}"
    )

m1, m2, m3 = st.columns(
    3
)

with m1:

    st.metric(
        "REGIME",
        signal["regime"]
    )

with m2:

    st.metric(
        "HTF",
        htf
    )

with m3:

    st.metric(
        "SCORE",
        f"{signal['score']}/9"
    )

# ============================================================
# SIGNAL CARD
# ============================================================

if final_side == "UP":

    st.markdown(
        """
        <div class="card green-card">
            <div class="big-signal">
                🟢 UP
            </div>
            <div class="signal-sub">
                STRONG MANUAL SIGNAL
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

elif final_side == "DOWN":

    st.markdown(
        """
        <div class="card red-card">
            <div class="big-signal">
                🔴 DOWN
            </div>
            <div class="signal-sub">
                STRONG MANUAL SIGNAL
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="card yellow-card">
            <div class="big-signal">
                🛑 NO TRADE
            </div>
            <div class="signal-sub">
                WAIT FOR A CLEANER SETUP
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# SIGNAL ANALYSIS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🔎 SIGNAL ANALYSIS'
    '</div>',
    unsafe_allow_html=True
)

c1, c2 = st.columns(
    2
)

with c1:

    st.write(
        f"**Setup:** "
        f"{signal['setup']}"
    )

    st.write(
        f"**Regime:** "
        f"{signal['regime']}"
    )

    st.write(
        f"**HTF trend:** "
        f"{htf}"
    )

with c2:

    st.write(
        f"**Signal score:** "
        f"{signal['score']}/9"
    )

    st.write(
        f"**Feed:** "
        f"{'OK' if feed_ok else 'STALE'}"
    )

    st.write(
        f"**Risk:** "
        f"{'OK' if risk_ok else risk_message}"
    )

for reason in signal[
    "reasons"
][
    :10
]:

    st.write(
        f"• {reason}"
    )

if gate:

    st.warning(
        "🛡️ Safety filters:\n\n"
        +
        "\n".join(
            f"• {g}"
            for g in gate
        )
    )

# ============================================================
# VALIDATION
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📊 OUT-OF-SAMPLE VALIDATION'
    '</div>',
    unsafe_allow_html=True
)

if validation_result is None:

    st.info(
        "At least 500 candles are needed "
        "before the V8 validation panel "
        "can calculate a train/test result."
    )

else:

    train = validation_result[
        "train"
    ]

    test = validation_result[
        "test"
    ]

    a, b = st.columns(
        2
    )

    with a:

        st.markdown(
            "### 🧪 TRAIN"
        )

        st.metric(
            "Trades",
            train["n"]
        )

        st.write(
            f"Wins: "
            f"**{train['wins']}**"
        )

        st.write(
            f"Losses: "
            f"**{train['losses']}**"
        )

        st.write(
            f"Accuracy: "
            f"**{train['accuracy']*100:.2f}%**"
        )

        st.write(
            f"EV: "
            f"**{train['ev']:.4f}**"
        )

    with b:

        st.markdown(
            "### 🎯 TEST / OOS"
        )

        st.metric(
            "Trades",
            test["n"]
        )

        st.write(
            f"Wins: "
            f"**{test['wins']}**"
        )

        st.write(
            f"Losses: "
            f"**{test['losses']}**"
        )

        st.write(
            f"Accuracy: "
            f"**{test['accuracy']*100:.2f}%**"
        )

        st.write(
            f"EV: "
            f"**{test['ev']:.4f}**"
        )

    st.write(
        f"Break-even at "
        f"{payout*100:.0f}% payout: "
        f"**{test['break_even']*100:.2f}%**"
    )

    if validation_result[
        "active"
    ]:

        st.success(
            "✅ OOS result currently "
            "passes the conservative "
            "activation test."
        )

    else:

        st.warning(
            "⚠️ OOS result is not strong "
            "enough to call a proven edge."
        )

# ============================================================
# CAPITAL PROTECTION
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🛡️ CAPITAL PROTECTION'
    '</div>',
    unsafe_allow_html=True
)

r1, r2, r3 = st.columns(
    3
)

with r1:

    st.metric(
        "TODAY P/L",
        f"{today_pnl:.2f}"
    )

with r2:

    st.metric(
        "LOSS STREAK",
        loss_streak
    )

with r3:

    st.metric(
        "TODAY TRADES",
        len(
            today_records(
                journal
            )
        )
    )

if risk_ok:

    st.success(
        "🟢 Risk Guard ACTIVE"
    )

else:

    st.error(
        f"🔴 Risk Guard: "
        f"{risk_message}"
    )

# ============================================================
# STAKE
# ============================================================

st.markdown(
    '<div class="section-title">'
    '💰 DEMO STAKE CONTROL'
    '</div>',
    unsafe_allow_html=True
)

if (
    final_side in (
        "UP",
        "DOWN"
    )
    and
    risk_ok
):

    stake = (
        balance *
        stake_pct /
        100
    )

    st.info(
        f"Demo stake cap: "
        f"**{stake:.2f}** "
        f"({stake_pct:.1f}% of balance)"
    )

else:

    st.warning(
        "Stake: **0 — NO TRADE**"
    )

# ============================================================
# INDICATORS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📈 INDICATORS'
    '</div>',
    unsafe_allow_html=True
)

a, b = st.columns(
    2
)

with a:

    st.write(
        f"EMA 9: "
        f"**{row['ema9']:.5f}**"
    )

    st.write(
        f"EMA 21: "
        f"**{row['ema21']:.5f}**"
    )

    st.write(
        f"EMA 50: "
        f"**{row['ema50']:.5f}**"
    )

    st.write(
        f"MACD Histogram: "
        f"**{row['macd_hist']:.6f}**"
    )

with b:

    st.write(
        f"RSI 14: "
        f"**{row['rsi']:.2f}**"
    )

    st.write(
        f"ADX 14: "
        f"**{row['adx']:.2f}**"
    )

    st.write(
        f"Stochastic: "
        f"**{row['stoch']:.2f}**"
    )

    st.write(
        f"ATR: "
        f"**{row['atr']:.6f}**"
    )

# ============================================================
# CHART
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📉 PRICE & TREND CHART'
    '</div>',
    unsafe_allow_html=True
)

chart = x.tail(
    150
)[
    [
        "time",
        "close",
        "ema9",
        "ema21",
        "ema50",
        "bb_upper",
        "bb_lower",
    ]
].copy()

chart = chart.set_index(
    "time"
)

st.line_chart(
    chart,
    height=400
)

# ============================================================
# JOURNAL
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📒 DEMO TRADE JOURNAL'
    '</div>',
    unsafe_allow_html=True
)

if journal:

    jdf = pd.DataFrame(
        journal
    )

    columns = [
        c
        for c in [
            "date",
            "timeframe",
            "side",
            "setup",
            "score",
            "result",
            "pnl",
        ]
        if c in jdf.columns
    ]

    st.dataframe(
        jdf[
            columns
        ].tail(20),
        use_container_width=True
    )

else:

    st.info(
        "No demo trades recorded yet."
    )

# ============================================================
# MANUAL RESULT ENTRY
# ============================================================

with st.expander(
    "➕ SAVE COMPLETED DEMO TRADE"
):

    side = st.selectbox(
        "Signal",
        [
            "UP",
            "DOWN"
        ]
    )

    result = st.selectbox(
        "Result",
        [
            "WIN",
            "LOSS",
            "TIE"
        ]
    )

    entry = st.number_input(
        "Entry price",
        value=float(
            row["close"]
        ),
        format="%.5f"
    )

    exit_price = st.number_input(
        "Exit price",
        value=float(
            row["close"]
        ),
        format="%.5f"
    )

    pnl = st.number_input(
        "Demo P/L",
        value=0.0,
        step=1.0
    )

    if st.button(
        "💾 SAVE RESULT",
        use_container_width=True
    ):

        now = utc_now()

        record = {
            "date":
                now.date().isoformat(),

            "time":
                now.isoformat(),

            "timeframe":
                tf,

            "side":
                side,

            "setup":
                signal["setup"],

            "regime":
                signal["regime"],

            "score":
                signal["score"],

            "htf":
                htf,

            "entry":
                entry,

            "exit":
                exit_price,

            "result":
                result,

            "pnl":
                pnl,

            "feed":
                "Yahoo external feed",

            "version":
                "V8",
        }

        journal.append(
            record
        )

        if save_journal(
            journal
        ):

            st.success(
                "✅ Demo result saved."
            )

            st.rerun()

        else:

            st.error(
                "Could not save journal file."
            )

# ============================================================
# DATA STATUS
# ============================================================

st.markdown(
    '<div class="section-title">'
    'ℹ️ DATA STATUS'
    '</div>',
    unsafe_allow_html=True
)

d1, d2 = st.columns(
    2
)

with d1:

    st.write(
        "Feed: "
        "**Yahoo external feed**"
    )

    st.write(
        f"Symbol: **{SYMBOL}**"
    )

    st.write(
        f"Timeframe: **{tf}**"
    )

    st.write(
        f"Bars: **{len(df)}**"
    )

with d2:

    if spacing:

        st.write(
            f"Spacing: "
            f"**{spacing:.1f} min**"
        )

    else:

        st.write(
            "Spacing: **N/A**"
        )

    st.write(
        f"Feed status: "
        f"**{feed_message}**"
    )

    st.write(
        f"HTF: "
        f"**{cfg['htf']} → {htf}**"
    )

    st.write(
        f"Closed candle: "
        f"**{x['time'].iloc[idx]} UTC**"
    )

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "---"
)

st.markdown(
    """
<div class="card blue-card">
<b>🛡️ V8 SAFETY RULES</b><br><br>
🟢 Closed candle only<br>
🟢 Strong confluence required<br>
🟢 Higher-timeframe confirmation<br>
🟢 Risk guard active<br>
🔴 No martingale<br>
🔴 No auto trading<br>
🔴 No OTC<br>
🔴 No profit guarantee<br>
🟡 Demo practice first
</div>
""",
    unsafe_allow_html=True
)

st.caption(
    "EUR/USD Signal PRO V8 • "
    "Rule-based analytical tool • "
    "Manual use only"
)
