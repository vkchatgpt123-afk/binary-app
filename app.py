import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime as dt
import json
import os
import math

# ============================================================
# EUR/USD SIGNAL PRO V7
# Rule-Based | Manual Only | No Auto Trade | No OTC
# ============================================================

st.set_page_config(
    page_title="EUR/USD Signal Pro V7",
    page_icon="📊",
    layout="centered"
)

# ============================================================
# CONFIG
# ============================================================

SYMBOL = "EURUSD=X"
PIP = 0.0001

INTERVALS = {
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

HTF_CONFIG = {
    "5m": {"interval": "5m", "range": "60d"},
    "15m": {"interval": "15m", "range": "60d"},
    "60m": {"interval": "60m", "range": "1y"}
}

JOURNAL_FILE = "eurusd_v7_journal.json"

# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 30px;
    font-weight: 800;
    text-align: center;
}

.subtitle {
    text-align: center;
    color: #777;
}

.signal-box {
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    border: 2px solid #444;
    margin: 12px 0;
}

.no-trade {
    background: rgba(120,120,120,0.10);
}

.up-box {
    background: rgba(0,180,80,0.12);
    border-color: #00a85a;
}

.down-box {
    background: rgba(220,40,40,0.12);
    border-color: #d62828;
}

.warning-box {
    padding: 15px;
    border-radius: 12px;
    background: rgba(255,180,0,0.12);
    border: 1px solid #d99a00;
}

.danger-box {
    padding: 15px;
    border-radius: 12px;
    background: rgba(220,40,40,0.12);
    border: 1px solid #d62828;
}

.small {
    font-size: 13px;
    color: #777;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# TITLE
# ============================================================

st.markdown(
    '<div class="main-title">📊 EUR/USD SIGNAL PRO V7</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Closed Candle • Manual Analysis • Capital Protection</div>',
    unsafe_allow_html=True
)

st.warning(
    "⚠️ IMPORTANT: External market feed is used for analysis. "
    "Feed price/candles may differ from Quotex. This tool does NOT place trades "
    "and does NOT guarantee profit."
)

# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []

    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_journal(data):
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def timeframe_minutes(tf):
    return INTERVALS[tf]["minutes"]


def safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default


# ============================================================
# YAHOO DATA
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def fetch_yahoo(interval, period):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{SYMBOL}?interval={interval}&range={period}"
    )

    try:
        r = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        r.raise_for_status()
        raw = r.json()

        result = raw["chart"]["result"][0]

        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]

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
            "volume": quote.get("volume")
        })

        df = df.dropna(
            subset=["open", "high", "low", "close"]
        ).copy()

        df = df.sort_values("time")
        df = df.drop_duplicates("time")
        df = df.reset_index(drop=True)

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# DATA QUALITY
# ============================================================

def check_data_quality(df, tf):
    result = {
        "ok": True,
        "reason": "",
        "bars": len(df),
        "gap": False,
        "spacing": None
    }

    if df is None or df.empty:
        result["ok"] = False
        result["reason"] = "No market data."
        return result

    if len(df) < 150:
        result["ok"] = False
        result["reason"] = f"Too little data: {len(df)} candles."
        return result

    minutes = timeframe_minutes(tf)

    times = df["time"].sort_values()

    diffs = times.diff().dropna().dt.total_seconds() / 60

    if len(diffs) > 10:
        median_spacing = float(diffs.median())
        result["spacing"] = median_spacing

        # FX can have session/weekend gaps, therefore
        # only abnormal small gaps are treated as a problem.
        normal_diffs = diffs[
            diffs <= minutes * 4
        ]

        if not normal_diffs.empty:
            spacing_error = abs(
                float(normal_diffs.median()) - minutes
            )

            if spacing_error > max(1.0, minutes * 0.35):
                result["ok"] = False
                result["reason"] = (
                    f"Timeframe spacing mismatch. "
                    f"Expected ~{minutes}m, got ~"
                    f"{normal_diffs.median():.1f}m."
                )
                return result

    # OHLC sanity
    bad = (
        (df["high"] < df["low"]) |
        (df["open"] > df["high"]) |
        (df["open"] < df["low"]) |
        (df["close"] > df["high"]) |
        (df["close"] < df["low"])
    )

    if bad.any():
        result["ok"] = False
        result["reason"] = "Invalid OHLC candle detected."
        return result

    return result


def get_closed_index(df, tf):
    """
    Yahoo timestamps are normally candle OPEN timestamps.
    We never analyse an unfinished candle.
    """

    if df.empty:
        return None

    minutes = timeframe_minutes(tf)

    now = utc_now()

    last_open = df["time"].iloc[-1].to_pydatetime()

    last_close_time = last_open + dt.timedelta(
        minutes=minutes
    )

    if now >= last_close_time:
        return len(df) - 1

    if len(df) >= 2:
        return len(df) - 2

    return None


def feed_status(df, tf):
    if df.empty:
        return False, "NO DATA"

    idx = get_closed_index(df, tf)

    if idx is None:
        return False, "NO CLOSED CANDLE"

    candle_time = df["time"].iloc[idx].to_pydatetime()

    age = (
        utc_now() - candle_time
    ).total_seconds()

    max_age = max(
        timeframe_minutes(tf) * 60 * 4,
        15 * 60
    )

    if age > max_age:
        return False, (
            f"STALE FEED ({age/60:.1f}m old)"
        )

    return True, "DATA OK"


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):

    x = df.copy()

    # EMA
    x["ema9"] = x["close"].ewm(
        span=9,
        adjust=False
    ).mean()

    x["ema21"] = x["close"].ewm(
        span=21,
        adjust=False
    ).mean()

    x["ema50"] = x["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI
    delta = x["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    x["rsi"] = 100 - (
        100 / (1 + rs)
    )

    # ATR
    prev_close = x["close"].shift(1)

    tr1 = x["high"] - x["low"]
    tr2 = (x["high"] - prev_close).abs()
    tr3 = (x["low"] - prev_close).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    x["atr"] = tr.ewm(
        span=14,
        adjust=False
    ).mean()

    # ATR baseline
    x["atr_med"] = x["atr"].rolling(
        100
    ).median()

    # Bollinger
    x["bb_mid"] = x["close"].rolling(
        20
    ).mean()

    x["bb_std"] = x["close"].rolling(
        20
    ).std()

    x["bb_upper"] = (
        x["bb_mid"] +
        2 * x["bb_std"]
    )

    x["bb_lower"] = (
        x["bb_mid"] -
        2 * x["bb_std"]
    )

    # MACD
    ema12 = x["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = x["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    x["macd"] = ema12 - ema26

    x["macd_signal"] = x["macd"].ewm(
        span=9,
        adjust=False
    ).mean()

    x["macd_hist"] = (
        x["macd"] -
        x["macd_signal"]
    )

    # Stochastic
    low14 = x["low"].rolling(
        14
    ).min()

    high14 = x["high"].rolling(
        14
    ).max()

    denom = (
        high14 - low14
    ).replace(0, np.nan)

    x["stoch"] = (
        100 *
        (x["close"] - low14) /
        denom
    )

    x["stoch_signal"] = x["stoch"].rolling(
        3
    ).mean()

    # ADX
    up_move = x["high"].diff()
    down_move = -x["low"].diff()

    plus_dm = np.where(
        (up_move > down_move) &
        (up_move > 0),
        up_move,
        0
    )

    minus_dm = np.where(
        (down_move > up_move) &
        (down_move > 0),
        down_move,
        0
    )

    atr14 = x["atr"].replace(
        0,
        np.nan
    )

    plus_di = (
        100 *
        pd.Series(
            plus_dm,
            index=x.index
        ).ewm(
            span=14,
            adjust=False
        ).mean() /
        atr14
    )

    minus_di = (
        100 *
        pd.Series(
            minus_dm,
            index=x.index
        ).ewm(
            span=14,
            adjust=False
        ).mean() /
        atr14
    )

    dx = (
        100 *
        (plus_di - minus_di).abs() /
        (plus_di + minus_di).replace(
            0,
            np.nan
        )
    )

    x["adx"] = dx.ewm(
        span=14,
        adjust=False
    ).mean()

    x["plus_di"] = plus_di
    x["minus_di"] = minus_di

    # Candle structure
    x["body"] = (
        x["close"] - x["open"]
    )

    x["body_abs"] = x["body"].abs()

    x["range"] = (
        x["high"] - x["low"]
    )

    x["body_atr"] = (
        x["body_abs"] /
        x["atr"].replace(
            0,
            np.nan
        )
    )

    x["close_location"] = (
        (x["close"] - x["low"]) /
        x["range"].replace(
            0,
            np.nan
        )
    )

    x["upper_wick"] = (
        x["high"] -
        x[["open", "close"]].max(axis=1)
    )

    x["lower_wick"] = (
        x[["open", "close"]].min(axis=1) -
        x["low"]
    )

    # Volatility ratio
    x["atr_ratio"] = (
        x["atr"] /
        x["atr_med"].replace(
            0,
            np.nan
        )
    )

    # Time
    x["hour"] = x["time"].dt.hour

    # Clean
    x = x.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return x


# ============================================================
# HTF TREND
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_htf_trend(htf):

    cfg = HTF_CONFIG[htf]

    df = fetch_yahoo(
        cfg["interval"],
        cfg["range"]
    )

    if df.empty:
        return "UNKNOWN"

    x = add_indicators(df)

    if len(x) < 80:
        return "UNKNOWN"

    row = x.iloc[-2].copy()

    if pd.isna(row["ema21"]) or pd.isna(row["ema50"]):
        return "UNKNOWN"

    if (
        row["ema21"] > row["ema50"] and
        row["close"] > row["ema21"]
    ):
        return "UP"

    if (
        row["ema21"] < row["ema50"] and
        row["close"] < row["ema21"]
    ):
        return "DOWN"

    return "NEUTRAL"


# ============================================================
# MARKET REGIME
# ============================================================

def detect_regime(row):

    adx = safe_float(row["adx"])
    atr_ratio = safe_float(row["atr_ratio"])

    if np.isnan(adx):
        return "UNKNOWN"

    if np.isnan(atr_ratio):
        atr_ratio = 1.0

    # Extreme volatility = transition/no trade
    if atr_ratio > 2.4:
        return "VOLATILITY_SPIKE"

    # Trend
    if adx >= 23:
        if (
            row["ema21"] > row["ema50"] and
            row["close"] > row["ema21"]
        ):
            return "UPTREND"

        if (
            row["ema21"] < row["ema50"] and
            row["close"] < row["ema21"]
        ):
            return "DOWNTREND"

        return "TREND_TRANSITION"

    # Range
    if adx <= 17:
        return "RANGE"

    return "SIDEWAYS"


# ============================================================
# SIGNAL ENGINE
# ============================================================

def generate_signal(x, idx, htf):

    if idx is None:
        return {
            "side": "NO TRADE",
            "score": 0,
            "max_score": 8,
            "setup": "NONE",
            "regime": "UNKNOWN",
            "reasons": ["No closed candle."]
        }

    row = x.iloc[idx]

    required = [
        "close",
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
        "close_location"
    ]

    if any(
        pd.isna(row[c])
        for c in required
    ):
        return {
            "side": "NO TRADE",
            "score": 0,
            "max_score": 8,
            "setup": "NONE",
            "regime": "UNKNOWN",
            "reasons": ["Indicator data incomplete."]
        }

    regime = detect_regime(row)

    close = row["close"]
    ema21 = row["ema21"]
    ema50 = row["ema50"]
    rsi = row["rsi"]
    adx = row["adx"]
    macd_hist = row["macd_hist"]
    stoch = row["stoch"]
    loc = row["close_location"]

    atr_ratio = safe_float(
        row["atr_ratio"],
        1.0
    )

    reasons = []

    up_score = 0
    down_score = 0

    setup = "NONE"

    # --------------------------------------------------------
    # VOLATILITY FILTER
    # --------------------------------------------------------

    if atr_ratio > 2.0:
        return {
            "side": "NO TRADE",
            "score": 0,
            "max_score": 8,
            "setup": "VOLATILITY FILTER",
            "regime": regime,
            "reasons": [
                "Volatility is abnormally high."
            ]
        }

    if atr_ratio < 0.35:
        return {
            "side": "NO TRADE",
            "score": 0,
            "max_score": 8,
            "setup": "LOW VOLATILITY",
            "regime": regime,
            "reasons": [
                "Market movement is too weak."
            ]
        }

    # --------------------------------------------------------
    # TREND PULLBACK
    # --------------------------------------------------------

    if regime in [
        "UPTREND",
        "DOWNTREND"
    ] and adx >= 23:

        setup = "TREND PULLBACK"

        # UP
        if ema21 > ema50:

            if close > ema21:
                up_score += 1
                reasons.append(
                    "Price above EMA21"
                )

            if row["ema9"] > ema21:
                up_score += 1
                reasons.append(
                    "EMA9 > EMA21"
                )

            if 48 <= rsi <= 68:
                up_score += 1
                reasons.append(
                    "Healthy bullish RSI"
                )

            if macd_hist > 0:
                up_score += 1
                reasons.append(
                    "Positive MACD momentum"
                )

            if stoch > 45:
                up_score += 1
                reasons.append(
                    "Bullish stochastic"
                )

            if loc >= 0.60:
                up_score += 1
                reasons.append(
                    "Strong candle close"
                )

            if adx >= 25:
                up_score += 1
                reasons.append(
                    "Strong ADX"
                )

            if row["body"] > 0:
                up_score += 1
                reasons.append(
                    "Bullish candle"
                )

        # DOWN
        elif ema21 < ema50:

            if close < ema21:
                down_score += 1
                reasons.append(
                    "Price below EMA21"
                )

            if row["ema9"] < ema21:
                down_score += 1
                reasons.append(
                    "EMA9 < EMA21"
                )

            if 32 <= rsi <= 52:
                down_score += 1
                reasons.append(
                    "Healthy bearish RSI"
                )

            if macd_hist < 0:
                down_score += 1
                reasons.append(
                    "Negative MACD momentum"
                )

            if stoch < 55:
                down_score += 1
                reasons.append(
                    "Bearish stochastic"
                )

            if loc <= 0.40:
                down_score += 1
                reasons.append(
                    "Weak candle close"
                )

            if adx >= 25:
                down_score += 1
                reasons.append(
                    "Strong ADX"
                )

            if row["body"] < 0:
                down_score += 1
                reasons.append(
                    "Bearish candle"
                )

    # --------------------------------------------------------
    # RANGE REVERSAL
    # --------------------------------------------------------

    elif regime == "RANGE":

        setup = "RANGE REVERSAL"

        # UP reversal
        if (
            close <= row["bb_lower"] and
            rsi <= 35 and
            stoch <= 25
        ):

            if close <= row["bb_lower"]:
                up_score += 1
                reasons.append(
                    "Lower Bollinger extreme"
                )

            if rsi <= 35:
                up_score += 1
                reasons.append(
                    "Oversold RSI"
                )

            if stoch <= 25:
                up_score += 1
                reasons.append(
                    "Oversold stochastic"
                )

            if row["lower_wick"] > row["upper_wick"]:
                up_score += 1
                reasons.append(
                    "Lower rejection wick"
                )

            if loc >= 0.50:
                up_score += 1
                reasons.append(
                    "Recovery close"
                )

        # DOWN reversal
        elif (
            close >= row["bb_upper"] and
            rsi >= 65 and
            stoch >= 75
        ):

            if close >= row["bb_upper"]:
                down_score += 1
                reasons.append(
                    "Upper Bollinger extreme"
                )

            if rsi >= 65:
                down_score += 1
                reasons.append(
                    "Overbought RSI"
                )

            if stoch >= 75:
                down_score += 1
                reasons.append(
                    "Overbought stochastic"
                )

            if row["upper_wick"] > row["lower_wick"]:
                down_score += 1
                reasons.append(
                    "Upper rejection wick"
                )

            if loc <= 0.50:
                down_score += 1
                reasons.append(
                    "Weak recovery close"
                )

    else:

        return {
            "side": "NO TRADE",
            "score": 0,
            "max_score": 8,
            "setup": "NO SETUP",
            "regime": regime,
            "reasons": [
                "Market is sideways/transition."
            ]
        }

    # --------------------------------------------------------
    # HTF CONFIRMATION
    # --------------------------------------------------------

    if htf == "UP":
        up_score += 1

    elif htf == "DOWN":
        down_score += 1

    # HTF neutral does NOT receive a point.

    # --------------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------------

    max_score = 8

    # Very strict
    if up_score >= 7 and up_score > down_score:

        return {
            "side": "UP",
            "score": up_score,
            "max_score": max_score,
            "setup": setup,
            "regime": regime,
            "reasons": reasons
        }

    if down_score >= 7 and down_score > up_score:

        return {
            "side": "DOWN",
            "score": down_score,
            "max_score": max_score,
            "setup": setup,
            "regime": regime,
            "reasons": reasons
        }

    return {
        "side": "NO TRADE",
        "score": max(
            up_score,
            down_score
        ),
        "max_score": max_score,
        "setup": setup,
        "regime": regime,
        "reasons": [
            f"UP {up_score}/8 • DOWN {down_score}/8",
            "Strong confirmation
