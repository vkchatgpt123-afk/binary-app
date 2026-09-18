import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Trading Terminal", page_icon="⚡", layout="centered")

# Custom Styling for Clean Trading Terminal
st.markdown("""
    <style>
    .stApp { background: #0b0e14; color: #ffffff; font-family: sans-serif; }
    
    .terminal-header { 
        background: #121824; 
        padding: 10px 15px; 
        border-radius: 10px; 
        border: 1px solid #1f293d; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 10px; 
    }
    
    .signal-card-up { 
        background: linear-gradient(135deg, #0e4429, #1b7a43); 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 2px solid #2ea043;
        box-shadow: 0 0 20px rgba(46, 160, 67, 0.4);
        margin-bottom: 10px;
    }
    
    .signal-card-down { 
        background: linear-gradient(135deg, #541212, #8c2020); 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 2px solid #da3633;
        box-shadow: 0 0 20px rgba(218, 54, 51, 0.4);
        margin-bottom: 10px;
    }
    
    .signal-card-wait { 
        background: linear-gradient(135deg, #593e02, #946903); 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        border: 2px solid #bb8009;
        box-shadow: 0 0 20px rgba(187, 128, 9, 0.4);
        margin-bottom: 10px;
    }

    .indicator-row { 
        background: #121824; 
        padding: 8px 12px; 
        border-radius: 8px; 
        margin-bottom: 6px; 
        border: 1px solid #1f293d; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 13px;
    }
    </style>
""", unsafe_allow_html=True)

# Session state for selected pair
if 'selected_pair' not in st.session_state:
    st.session_state.selected_pair = "EURUSD=X"

# Top Header with Refresh Button
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("<h4 style='margin:0; color:#58a6ff;'>⚡ PRO TRADING TERMINAL</h4>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Currency Pairs Grid Layout on Main Screen
st.markdown("<p style='font-size:11px; color:#8b949e; margin-bottom:4px;'>SELECT CURRENCY PAIR:</p>", unsafe_allow_html=True)
pairs = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X", "USDCAD=X", "NZDUSD=X", "EURJPY=X", "GBPJPY=X"]

cols = st.columns(4)
for idx, pair in enumerate(pairs):
    clean_name = pair.replace('=X', '')
    is_selected = (st.session_state.selected_pair == pair)
    with cols[idx % 4]:
        btn_type = "primary" if is_selected else "secondary"
        if st.button(clean_name, key=f"p_{pair}", use_container_width=True, type=btn_type):
            st.session_state.selected_pair = pair
            st.rerun()

selected_asset = st.session_state.selected_pair

# Timeframe Selector
timeframe = st.radio("Timeframe", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

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
    st.error("⚠️ Data load karne me samasya aa rahi hai.")
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
        market_state, confidence, signal_type = "UPTREND", "HIGH 🔥", "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        market_state, confidence, signal_type = "DOWNTREND", "HIGH 🔥", "DOWN"
    else:
        market_state, confidence, signal_type = "SIDEWAYS", "LOW ⚠️", "HOLD"

    # Price Banner
    st.markdown(f"""
        <div class="terminal-header" style="margin-top: 8px;">
            <span><b>{selected_asset.replace('=X', '')}</b> ({timeframe})</span>
            <span style="color: {'#3fb950' if price_change >= 0 else '#f85149'}; font-weight:bold;">
                {current_price:.5f} ({'+' if price_change >= 0 else ''}{price_change_pct:.2f}%)
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Signal Card Display (Sirf UP ya DOWN)
    if signal_type == "UP":
        st.markdown('<div class="signal-card-up"><h1 style="margin:0; font-size:32px; letter-spacing: 1px;">🟢 UP</h1><p style="margin:4px 0 0 0; font-size:12px; color:#d1fae5;">Strong Bullish Momentum</p></div>', unsafe_allow_html=True)
    elif signal_type == "DOWN":
        st.markdown('<div class="signal-card-down"><h1 style="margin:0; font-size:32px; letter-spacing: 1px;">🔴 DOWN</h1><p style="margin:4px 0 0 0; font-size:12px; color:#fee2e2;">Strong Bearish Momentum</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-card-wait"><h1 style="margin:0; font-size:26px;">⏳ HOLD</h1><p style="margin:4px 0 0 0; font-size:12px; color:#fef3c7;">Market Sideways - Wait</p></div>', unsafe_allow_html=True)

    # Mini Stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div style='background:#121824; padding:6px; border-radius:6px; text-align:center; border:1px solid #1f293d;'><p style='margin:0; font-size:9px; color:#8b949e;'>STATE</p><p style='margin:0; font-size:11px; font-weight:bold; color:#58a6ff;'>{market_state}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='background:#121824; padding:6px; border-radius:6px; text-align:center; border:1px solid #1f293d;'><p style='margin:0; font-size:9px; color:#8b949e;'>CONF</p><p style='margin:0; font-size:11px; font-weight:bold; color:#3fb950;'>{confidence}</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='background:#121824; padding:6px; border-radius:6px; text-align:center; border:1px solid #1f293d;'><p style='margin:0; font-size:9px; color:#8b949e;'>RSI</p><p style='margin:0; font-size:11px; font-weight:bold; color:#f0b429;'>{rsi_14:.1f}</p></div>", unsafe_allow_html=True)

    st.write("")

    # Indicators list
    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("MACD", macd_status, "🟢" if macd_status == "Bullish" else "🔴"),
        ("RSI Status", "Overbought" if rsi_14 > 70 else "Oversold" if rsi_14 < 30 else "Normal", "⚪")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #8b949e;">{name}</span>
                <span><b style="color: #ffffff; margin-right: 5px;">{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)
