import math
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

PIP = 0.0001

# Single-Screen Compact Layout Configuration
st.set_page_config(
    page_title="EUR/USD 1-Screen Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- ULTRA-COMPACT SINGLE SCREEN CSS ----------------
st.markdown(
    """
<style>
    /* Remove excessive padding to prevent scrolling */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    
    /* Hide default streamlit footer/header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Compact Header */
    .header-title {
        font-size: 24px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 0px;
    }
    .header-subtitle {
        font-size: 12px;
        color: #8a99ad;
        margin-bottom: 10px;
    }

    /* Compact Glowing Signal Cards */
    .signal-box {
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-size: 28px;
        font-weight: 900;
        letter-spacing: 1px;
        margin: 5px 0 15px 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .signal-up {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: #ffffff;
        border: 2px solid #57ff9b;
    }
    .signal-down {
        background: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%);
        color: #ffffff;
        border: 2px solid #ff7b70;
    }
    .signal-no {
        background: linear-gradient(135deg, #f7b733 0%, #fc4a1a 100%);
        color: #ffffff;
        border: 2px solid #ffd276;
    }

    /* Compact Metrics */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 10px 15px;
        border-radius: 10px;
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-size: 13px !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f0f6fc !important;
        font-size: 20px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- COMPACT SIDEBAR CONTROLS ----------------
with st.sidebar:
    st.markdown("### ⚙️ Strategy Settings")
    n_candles = st.slider("Candles in a row", 2, 8, 4)
    body_mult = st.slider("Body ≥ x ATR", 0.5, 3.0, 1.5, 0.1)
    loc_min = st.slider("Close location (%)", 60, 99, 85) / 100
    atr_mult = st.slider("ATR > x median", 0.5, 3.0, 1.2, 0.1)
    atr_period = int(st.number_input("ATR period", 5, 50, 14))
    lookback = int(st.number_input("Lookback", 20, 300, 100))
    horizon = st.slider("Exit candles", 1, 6, 1)
    drop_last = st.checkbox("Ignore forming candle", value=True)

# ---------------- FETCH LIVE DATA ----------------
@st.cache_data(ttl=60)
def load_live_data():
    ticker = "EURUSD=X"
    df = yf.download(ticker, period="5d", interval="5m", progress=False)
    if df.empty:
        raise ValueError("Could not fetch live market data.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = df.columns.astype(str).str.strip().str.lower()
    df = df.rename(columns={"datetime": "time", "date": "time"})
    
    required = ["open", "high", "low", "close", "time"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing column: {c}")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close", "time"]).sort_values("time").reset_index(drop=True)
    return df

# ---------------- MAIN UI CONTAINER (SINGLE SCREEN) ----------------
col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.markdown('<p class="header-title">⚡ EUR/USD 1-SCREEN TERMINAL</p>', unsafe_allow_html=True)
    st.markdown('<p class="header-subtitle">Automated Live Feed & Signal Engine</p>', unsafe_allow_html=True)
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh", use_container_width=True)

try:
    df = load_live_data()
except Exception as exc:
    st.error(f"⚠️ Error: {exc}")
    st.stop()

if drop_last and len(df) > 1:
    df = df.iloc[:-1].reset_index(drop=True)

min_rows = lookback + atr_period + n_candles + horizon + 50
if len(df) < min_rows:
    st.warning(f"⏳ Gathering data... Need {min_rows}, have {len(df)}.")
    st.stop()

# ---------------- INDICATOR ENGINE ----------------
gaps = df["time"].diff().dropna()
step = gaps.median() if not gaps.empty else None

prev_close = df["close"].shift(1)
tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
df["atr"] = tr.rolling(atr_period, min_periods=atr_period).mean()
df["median_atr"] = df["atr"].shift(1).rolling(lookback, min_periods=lookback).median()

is_gap = df["time"].diff() > step * 1.5 if step is not None else pd.Series(False, index=df.index)
df["is_gap"] = is_gap.fillna(False)
win = max(atr_period, n_candles, 2)
df["recent_gap"] = df["is_gap"].astype(int).rolling(win, min_periods=1).max().astype(bool)

bull = df["close"] > df["open"]
bear = df["close"] < df["open"]
rng = (df["high"] - df["low"]).replace(0, np.nan)
close_loc = (df["close"] - df["low"]) / rng
body = (df["close"] - df["open"]).abs()

df["run_bull"] = bull.rolling(n_candles, min_periods=n_candles).sum() == n_candles
df["run_bear"] = bear.rolling(n_candles, min_periods=n_candles).sum() == n_candles
df["body_ok"] = body >= body_mult * df["atr"]
df["loc_top"] = close_loc >= loc_min
df["loc_bottom"] = close_loc <= (1 - loc_min)
df["vol_ok"] = df["atr"] > atr_mult * df["median_atr"]

clean = ~df["recent_gap"]
down = df["run_bull"] & df["body_ok"] & df["loc_top"] & df["vol_ok"] & clean
up = df["run_bear"] & df["body_ok"] & df["loc_bottom"] & df["vol_ok"] & clean

df["dir"] = np.select([down, up], [-1, 1], default=0).astype(int)
last = df.iloc[-1]

# ---------------- SIGNAL DISPLAY (PROMINENT) ----------------
if pd.isna(last["atr"]) or pd.isna(last["median_atr"]):
    st.markdown('<div class="signal-box signal-no">🛑 INITIALIZING... NO TRADE</div>', unsafe_allow_html=True)
elif last["dir"] == -1:
    st.markdown(f'<div class="signal-box signal-down">🔴 DOWN SIGNAL (PUT) &nbsp;|&nbsp; <span style="font-size:16px;">Time: {last["time"]}</span></div>', unsafe_allow_html=True)
elif last["dir"] == 1:
    st.markdown(f'<div class="signal-box signal-up">🟢 UP SIGNAL (CALL) &nbsp;|&nbsp; <span style="font-size:16px;">Time: {last["time"]}</span></div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="signal-box signal-no">🛑 NO TRADE SETUP &nbsp;|&nbsp; <span style="font-size:16px;">Time: {last["time"]}</span></div>', unsafe_allow_html=True)

# ---------------- METRICS & MINI CHART IN SINGLE ROW ----------------
col_metrics, col_chart = st.columns([2, 3])

with col_metrics:
    m1, m2 = st.columns(2)
    m1.metric("Price", f"{last['close']:.5f}")
    m2.metric("ATR Vol", f"{last['atr'] / PIP:.1f}p")
    
    m3, m4 = st.columns(2)
    m3.metric("Median ATR", f"{last['median_atr'] / PIP:.1f}p")
    m4.metric("Status", "🟢 LIVE")

with col_chart:
    st.markdown("<p style='font-size:13px; color:#8b949e; margin-bottom:0px;'><b>Recent Price Action (5m)</b></p>", unsafe_allow_html=True)
    st.line_chart(df.set_index("time")["close"].tail(50), height=130, use_container_width=True)
