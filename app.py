import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Reversal Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0b0f19; color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 2.2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    .pairs-container { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
    .pairs-row { display: flex; justify-content: space-between; gap: 4px; }
    .pair-btn {
        flex: 1;
        background: #1f2937;
        color: #ffffff;
        border: 1px solid #374151;
        padding: 6px 2px;
        text-align: center;
        border-radius: 6px;
        font-size: 10px;
        font-weight: bold;
        text-decoration: none;
        box-sizing: border-box;
    }
    .pair-btn-active {
        background: #2563eb !important;
        border: 1px solid #60a5fa !important;
    }
    
    .signal-up { 
        background: linear-gradient(135deg, #059669, #10b981); 
        padding: 10px; 
        border-radius: 6px; 
        text-align: center; 
        color: #ffffff; 
        font-weight: 900; 
        font-size: 20px; 
        margin: 4px 0; 
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.7);
        border: 1px solid #34d399;
    }
    .signal-down { 
        background: linear-gradient(135deg, #dc2626, #ef4444); 
        padding: 10px; 
        border-radius: 6px; 
        text-align: center; 
        color: #ffffff; 
        font-weight: 900; 
        font-size: 20px; 
        margin: 4px 0; 
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.7);
        border: 1px solid #f87171;
    }
    .signal-hold { 
        background: #1f2937; 
        border: 1px solid #374151; 
        padding: 10px; 
        border-radius: 6px; 
        text-align: center; 
        color: #fbbf24; 
        font-weight: 800; 
        font-size: 16px; 
        margin: 4px 0; 
    }
    
    .status-bar {
        background: #111827;
        padding: 6px 10px;
        border-radius: 5px;
        border: 1px solid #1f293d;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3px;
        font-size: 11px;
        font-weight: bold;
    }
    .indicator-row { 
        background: #111827; 
        padding: 6px 10px; 
        border-radius: 5px; 
        margin-bottom: 3px; 
        border: 1px solid #1f293d; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 11px;
    }
    .section-title {
        font-size: 14px;
        font-weight: bold;
        margin-top: 14px;
        margin-bottom: 6px;
        color: #e5e7eb;
        border-left: 3px solid #2563eb;
        padding-left: 6px;
    }
    </style>
""", unsafe_allow_html=True)

if 'selected_pair' not in st.session_state:
    st.session_state.selected_pair = "EURUSD=X"

query_params = st.query_params
if "pair" in query_params:
    st.session_state.selected_pair = query_params["pair"]

selected_asset = st.session_state.selected_pair

@st.cache_data(ttl=5)
def load_data(ticker, interval_val):
    try:
        df = yf.download(ticker, period="3d", interval=interval_val, progress=False, auto_adjust=False, threads=False)
        if df.empty or len(df) < 150:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

row1 = [("EURUSD", "EURUSD=X"), ("GBPUSD", "GBPUSD=X"), ("AUDUSD", "AUDUSD=X"), ("USDJPY", "USDJPY=X")]
row2 = [("USDCAD", "USDCAD=X"), ("NZDUSD", "NZDUSD=X"), ("EURJPY", "EURJPY=X"), ("GBPJPY", "GBPJPY=X")]

def render_row(pairs):
    html = '<div class="pairs-row">'
    for name, ticker in pairs:
        active = " pair-btn-active" if selected_asset == ticker else ""
        html += f'<a href="?pair={ticker}" class="pair-btn{active}">{name}</a>'
    html += '</div>'
    return html

st.markdown(f'''
    <div class="pairs-container">
        {render_row(row1)}
        {render_row(row2)}
    </div>
''', unsafe_allow_html=True)

# Kept only 2m and 5m as requested
timeframe = st.radio("TF", ["2m", "5m"], horizontal=True, label_visibility="collapsed")

df = load_data(selected_asset, timeframe)

checks_down = {}
checks_up = {}
total_candles = 0
atr_last = 0.0

if df is not None and not df.empty:
    needed = ["Open", "High", "Low", "Close"]
    df = df.dropna(subset=[x for x in needed if x in df.columns])
    df = df[~df.index.duplicated(keep="last")]
    total_candles = len(df)
    
    if total_candles >= 150:
        data = df.iloc[:-1].copy()
        o, h, l, c = [data[x].astype(float) for x in needed]
        
        tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        recent = data.iloc[-4:]
        atr_last = float(atr.iloc[-1])
        prior_median = float(atr.iloc[-120:-1].median())
        
        is_bullish_candles = bool((recent["Close"] > recent["Open"]).all())
        is_bearish_candles = bool((recent["Close"] < recent["Open"]).all())
        
        ema_50 = c.ewm(span=50, adjust=False).mean().iloc[-1]
        delta = c.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean().iloc[-1]
        avg_loss = loss.rolling(14).mean().iloc[-1]
        rsi_14 = float(100 - (100 / (1 + (avg_gain / (avg_loss + 1e-10)))))

        checks_down = {
            "4 consecutive bullish candles": is_bullish_candles,
            "Body size >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.5 * atr_last),
            "Close >= 85% of high-low range": bool((c.iloc[-1] - l.iloc[-1]) / (h.iloc[-1] - l.iloc[-1]) >= .85) if h.iloc[-1] > l.iloc[-1] else False,
            "Volatility ATR > 1.2 × Median": bool(atr_last > 1.2 * prior_median),
            "RSI Overbought Zone (>65)": bool(rsi_14 > 65),
            "Trend Filter (Price > EMA 50)": bool(c.iloc[-1] > ema_50)
        }
        
        checks_up = {
            "4 consecutive bearish candles": is_bearish_candles,
            "Body size >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.5 * atr_last),
            "Close <= 15% of high-low range": bool((c.iloc[-1] - l.iloc[-1]) / (h.iloc[-1] - l.iloc[-1]) <= .15) if h.iloc[-1] > l.iloc[-1] else False,
            "Volatility ATR > 1.2 × Median": bool(atr_last > 1.2 * prior_median),
            "RSI Oversold Zone (<35)": bool(rsi_14 < 35),
            "Trend Filter (Price < EMA 50)": bool(c.iloc[-1] < ema_50)
        }

        if all(checks_down.values()):
            signal_type = "DOWN"
            market_state = "STRONG REVERSAL DOWN 📉"
            confidence = "MAXIMUM 🛡️"
        elif all(checks_up.values()):
            signal_type = "UP"
            market_state = "STRONG REVERSAL UP 📈"
            confidence = "MAXIMUM 🛡️"
        else:
            signal_type = "HOLD"
            market_state = "FILTERING NOISE / WAIT ⏳"
            confidence = "ZERO RISK MODE"
            
        current_price = float(c.iloc[-1])
        prev_price = float(c.iloc[-2])
        price_change_pct = ((current_price - prev_price) / prev_price) * 100
        
        sma_20 = float(c.rolling(20).mean().iloc[-1])
        ema_12 = float(c.ewm(span=12, adjust=False).mean().iloc[-1])
        
        bb_std = float(c.rolling(20).std().iloc[-1])
        bb_upper = sma_20 + (bb_std * 2)
        bb_lower = sma_20 - (bb_std * 2)

        exp1 = c.ewm(span=12, adjust=False).mean()
        exp2 = c.ewm(span=26, adjust=False).mean()
        macd_val = (exp1 - exp2).iloc[-1]
        sig_val = (exp1 - exp2).ewm(span=9, adjust=False).mean().iloc[-1]
        macd_status = "Bullish" if macd_val > sig_val else "Bearish"
    else:
        current_price, price_change_pct, signal_type, market_state, confidence = 0.0, 0.0, "HOLD", "LOADING DATA...", "LOW"
        sma_20, ema_12, bb_lower, bb_upper, rsi_14 = 0, 0, 0, 0, 50
        macd_status = "Neutral"
else:
    current_price, price_change_pct, signal_type, market_state, confidence = 0.0, 0.0, "HOLD", "NO CONNECTION", "LOW"
    sma_20, ema_12, bb_lower, bb_upper, rsi_14 = 0, 0, 0, 0, 50
    macd_status = "Neutral"

if not checks_down:
    checks_down = {
        "4 consecutive bullish candles": False,
        "Body size >= 1.5 × ATR": False,
        "Close >= 85% of high-low range": False,
        "Volatility ATR > 1.2 × Median": False,
        "RSI Overbought Zone (>65)": False,
        "Trend Filter (Price > EMA 50)": False
    }

clean_name = selected_asset.replace('=X', '')
st.markdown(f"""
    <div style="background: #1f2937; padding: 6px 10px; border-radius: 6px; border: 1px solid #374151; display: flex; justify-content: space-between; align-items: center; margin-top: 4px; font-size: 12px;">
        <span><b>{clean_name}</b> ({timeframe})</span>
        <span style="color: {'#34d399' if price_change_pct >= 0 else '#f87171'}; font-weight:bold;">
            {current_price:.5f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
        </span>
    </div>
""", unsafe_allow_html=True)

if signal_type == "UP":
    st.markdown('<div class="signal-up">🚀 BUY / REVERSAL UP 🟢</div>', unsafe_allow_html=True)
elif signal_type == "DOWN":
    st.markdown('<div class="signal-down">🔻 SELL / REVERSAL DOWN 🔴</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal-hold">🛡️ NO TRADE - WAITING FOR SETUP</div>', unsafe_allow_html=True)

# Status and Filter matched to indicator row size style
st.markdown(f"""
    <div class="status-bar">
        <span style="color: #9ca3af;">Status: <span style="color: {'#34d399' if 'UP' in market_state else '#f87171' if 'DOWN' in market_state else '#fbbf24'};">{market_state}</span></span>
        <span>Filter: <b style="color: #60a5fa;">{confidence}</b></span>
    </div>
""", unsafe_allow_html=True)

indicators = [
    ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
    ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
    ("BB Lower/Upper", f"{bb_lower:.4f} / {bb_upper:.4f}", "🟢" if current_price >= bb_lower else "🔴"),
    ("RSI (14)", f"{rsi_14:.1f}", "🟢" if rsi_14 > 50 else "🔴"),
    ("MACD Trend", macd_status, "🟢" if macd_status == "Bullish" else "🔴")
]

for name, val, status in indicators:
    st.markdown(f"""
        <div class="indicator-row">
            <span style="color: #9ca3af;">{name}</span>
            <span><b style="color: #ffffff; margin-right: 6px;">{val}</b> {status}</span>
        </div>
    """, unsafe_allow_html=True)

# Setup checks section
st.markdown('<div class="section-title">Institutional Setup Checks (Zero-Risk Filter)</div>', unsafe_allow_html=True)
for check_name, passed in checks_down.items():
    badge = '<span style="color: #34d399; font-weight: bold;">PASS ✅</span>' if passed else '<span style="color: #f87171; font-weight: bold;">WAIT ❌</span>'
    st.markdown(f"""
        <div class="indicator-row">
            <span style="color: #d1d5db;">{check_name}</span>
            <span>{badge}</span>
        </div>
    """, unsafe_allow_html=True)

# Data section
st.markdown('<div class="section-title">Market Diagnostics</div>', unsafe_allow_html=True)
data_rows = [
    ("Analyzed Candles", str(total_candles)),
    ("ATR (14) Volatility", f"{atr_last:.5f}")
]
for name, val in data_rows:
    st.markdown(f"""
        <div class="indicator-row">
            <span style="color: #d1d5db;">{name}</span>
            <span><b style="color: #ffffff;">{val}</b></span>
        </div>
    """, unsafe_allow_html=True)

refresh_rate = st.selectbox("Refresh Rate", ["60s", "30s", "2m", "5m"], label_visibility="collapsed")

if st.button("🔌 Reboot Terminal", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()
