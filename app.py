import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Trading Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0b0e14; color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 0.8rem !important; padding-bottom: 0.8rem !important; }
    
    .signal-card-up { 
        background: linear-gradient(135deg, #0e4429, #1b7a43); 
        padding: 8px; 
        border-radius: 6px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #2ea043;
        margin-bottom: 4px;
    }
    .signal-card-down { 
        background: linear-gradient(135deg, #541212, #8c2020); 
        padding: 8px; 
        border-radius: 6px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #da3633;
        margin-bottom: 4px;
    }
    .signal-card-wait { 
        background: linear-gradient(135deg, #593e02, #946903); 
        padding: 8px; 
        border-radius: 6px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 1px solid #bb8009;
        margin-bottom: 4px;
    }
    .indicator-row { 
        background: #121824; 
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

# Top row: Title and Refresh button compact
c_title, c_ref = st.columns([3, 1])
with c_title:
    st.markdown("<h5 style='margin:0; color:#58a6ff;'>⚡ PRO TERMINAL</h5>", unsafe_allow_html=True)
with c_ref:
    if st.button("🔄", use_container_width=True):
        st.rerun()

# Currency pairs in 4 columns grid (2 rows for 8 pairs) to save vertical space
pairs = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X", "USDCAD=X", "NZDUSD=X", "EURJPY=X", "GBPJPY=X"]

for i in range(0, len(pairs), 4):
    cols = st.columns(4)
    for j in range(4):
        if i + j < len(pairs):
            pair = pairs[i + j]
            clean_name = pair.replace('=X', '')
            is_selected = (st.session_state.selected_pair == pair)
            with cols[j]:
                btn_type = "primary" if is_selected else "secondary"
                if st.button(clean_name, key=f"btn_{pair}", use_container_width=True, type=btn_type):
                    st.session_state.selected_pair = pair
                    st.rerun()

selected_asset = st.session_state.selected_pair

# Timeframe compact selector
timeframe = st.radio("TF", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

@st.cache_data(ttl=10)
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

df = load_data(selected_asset, timeframe)

if df is None:
    st.error("Data error")
else:
    close = df['Close']
    current_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100

    sma_20 = close.rolling(20).mean().iloc[-1]
    ema_12 = close.ewm(span=12).mean().iloc[-1]
    
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
        signal_type = "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        signal_type = "DOWN"
    else:
        signal_type = "HOLD"

    # Price banner compact
    st.markdown(f"""
        <div style="background: #121824; padding: 5px 8px; border-radius: 6px; border: 1px solid #1f293d; display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 11px;">
            <span><b>{selected_asset.replace('=X', '')}</b> ({timeframe})</span>
            <span style="color: {'#3fb950' if price_change >= 0 else '#f85149'}; font-weight:bold;">
                {current_price:.5f} ({'+' if price_change >= 0 else ''}{price_change_pct:.2f}%)
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Signal Card (Only UP or DOWN)
    if signal_type == "UP":
        st.markdown('<div class="signal-card-up"><h2 style="margin:0; font-size:22px;">UP</h2></div>', unsafe_allow_html=True)
    elif signal_type == "DOWN":
        st.markdown('<div class="signal-card-down"><h2 style="margin:0; font-size:22px;">DOWN</h2></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-card-wait"><h2 style="margin:0; font-size:18px;">HOLD</h2></div>', unsafe_allow_html=True)

    # Indicators compact rows
    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("RSI", f"{rsi_14:.1f}", "🟢" if rsi_14 > 50 else "🔴"),
        ("MACD", macd_status, "🟢" if macd_status == "Bullish" else "🔴")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #8b949e;">{name}</span>
                <span><b style="color: #ffffff; margin-right: 4px;">{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)
