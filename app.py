import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Trading Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #07090e 0%, #111827 100%); color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 0.4rem !important; padding-bottom: 0.4rem !important; max-width: 100% !important; }
    
    .pairs-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        margin-bottom: 8px;
        margin-top: 4px;
    }
    .pair-btn {
        background: #1f2937;
        color: #ffffff;
        border: 1px solid #374151;
        padding: 6px 2px;
        text-align: center;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        text-decoration: none;
        display: block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .pair-btn-active {
        background: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #60a5fa !important;
        box-shadow: 0 0 10px rgba(37,99,235,0.6);
    }
    
    .signal-card-up { 
        background: linear-gradient(135deg, #059669, #10b981); 
        padding: 8px; 
        border-radius: 8px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #34d399;
        margin-bottom: 6px;
        margin-top: 6px;
        box-shadow: 0 4px 12px rgba(16,185,129,0.3);
    }
    .signal-card-down { 
        background: linear-gradient(135deg, #dc2626, #ef4444); 
        padding: 8px; 
        border-radius: 8px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #f87171;
        margin-bottom: 6px;
        margin-top: 6px;
        box-shadow: 0 4px 12px rgba(239,68,68,0.3);
    }
    .signal-card-wait { 
        background: linear-gradient(135deg, #d97706, #f59e0b); 
        padding: 8px; 
        border-radius: 8px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #fbbf24;
        margin-bottom: 6px;
        margin-top: 6px;
        box-shadow: 0 4px 12px rgba(245,158,11,0.3);
    }
    .status-bar {
        background: #1f2937;
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid #374151;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        font-size: 11px;
        font-weight: bold;
    }
    .indicator-row { 
        background: #111827; 
        padding: 4px 8px; 
        border-radius: 6px; 
        margin-bottom: 3px; 
        border: 1px solid #1f293d; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 11px;
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
        df = yf.download(ticker, period="1d", interval=interval_val, progress=False)
        if df.empty or len(df) < 20:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# 1. All 8 Pairs Grid Box
pairs = [
    ("EURUSD", "EURUSD=X"), ("GBPUSD", "GBPUSD=X"), 
    ("AUDUSD", "AUDUSD=X"), ("USDJPY", "USDJPY=X"), 
    ("USDCAD", "USDCAD=X"), ("NZDUSD", "NZDUSD=X"), 
    ("EURJPY", "EURJPY=X"), ("GBPJPY", "GBPJPY=X")
]

grid_html = '<div class="pairs-grid">'
for name, ticker in pairs:
    is_active = (selected_asset == ticker)
    active_class = " pair-btn-active" if is_active else ""
    grid_html += f'<a href="?pair={ticker}" class="pair-btn{active_class}">{name}</a>'
grid_html += '</div>'

st.markdown(grid_html, unsafe_allow_html=True)

# 2. Timeframe Selection (1m, 2m, 5m with gap)
st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
timeframe = st.radio("TF", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

# Map timeframe string to yfinance interval
tf_map = {"1m": "1m", "2m": "2m", "5m": "5m"}
df = load_data(selected_asset, tf_map[timeframe])

if df is not None:
    close = df['Close']
    current_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100

    sma_20 = close.rolling(20).mean().iloc[-1]
    ema_12 = close.ewm(span=12).mean().iloc[-1]
    
    bb_std = close.rolling(20).std().iloc[-1]
    bb_upper = sma_20 + (bb_std * 2)
    bb_lower = sma_20 - (bb_std * 2)
    
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean().iloc[-1]
    avg_loss = loss.rolling(14).mean().iloc[-1]
    rs = avg_gain / (avg_loss + 1e-10)
    rsi_14 = 100 - (100 / (1 + rs))

    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd_val = (exp1 - exp2).iloc[-1]
    sig_val = (exp1 - exp2).ewm(span=9, adjust=False).mean().iloc[-1]
    macd_status = "Bullish" if macd_val > sig_val else "Bearish"

    if rsi_14 > 55 and macd_status == "Bullish":
        market_state = "UPTREND 📈"
        confidence = "HIGH 🔥"
        signal_type = "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        market_state = "DOWNTREND 📉"
        confidence = "HIGH 🔥"
        signal_type = "DOWN"
    else:
        market_state = "SIDEWAYS ↔️"
        confidence = "LOW ⚠️"
        signal_type = "HOLD"
else:
    current_price, price_change_pct, signal_type, market_state, confidence = 0, 0, "HOLD", "SIDEWAYS", "LOW"

# 3. Hold / Signal Card with Price Banner
st.markdown(f"""
    <div style="background: #1f2937; padding: 4px 8px; border-radius: 6px; border: 1px solid #374151; display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 11px;">
        <span><b>{selected_asset.replace('=X', '')}</b> ({timeframe})</span>
        <span style="color: {'#34d399' if price_change_pct >= 0 else '#f87171'}; font-weight:bold;">
            {current_price:.5f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
        </span>
    </div>
""", unsafe_allow_html=True)

if signal_type == "UP":
    st.markdown('<div class="signal-card-up"><h2 style="margin:0; font-size:20px;">UP</h2></div>', unsafe_allow_html=True)
elif signal_type == "DOWN":
    st.markdown('<div class="signal-card-down"><h2 style="margin:0; font-size:20px;">DOWN</h2></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal-card-wait"><h2 style="margin:0; font-size:18px;">HOLD</h2></div>', unsafe_allow_html=True)

# 4. Status Bar (Without Share option)
st.markdown(f"""
    <div class="status-bar">
        <span>State: <span style="color: {'#34d399' if 'UP' in market_state else '#f87171' if 'DOWN' in market_state else '#fbbf24'};">{market_state}</span></span>
        <span>Conf: <span style="color: #60a5fa;">{confidence}</span></span>
    </div>
""", unsafe_allow_html=True)

# 5. Indicators Section
if df is not None:
    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("BB Lower/Upper", f"{bb_lower:.4f} / {bb_upper:.4f}", "🟢" if current_price >= bb_lower else "🔴"),
        ("RSI (14)", f"{rsi_14:.1f}", "🟢" if rsi_14 > 50 else "🔴"),
        ("MACD", macd_status, "🟢" if macd_status == "Bullish" else "🔴")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #9ca3af;">{name}</span>
                <span><b style="color: #ffffff; margin-right: 4px;">{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)

# 6. Auto-Refresh Option (Including 60s)[span_2](start_span)[span_2](end_span)
auto_refresh = st.selectbox("Auto Refresh", ["60s", "1 min", "2 min", "5 min"], label_visibility="collapsed")

# 7. Reboot Terminal Option (Last)
if st.button("🔌 Reboot Terminal", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()
