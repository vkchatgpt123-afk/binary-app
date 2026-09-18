import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page configuration for compact view
st.set_page_config(page_title="Compact Pro Bot", page_icon="⚡", layout="centered")

# 60 Seconds Auto-Refresh Meta Tag
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

# Compact & Bright Cyber Styling (No Scrolling Needed)
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #050814 0%, #0b1329 100%); color: #ffffff; }
    
    .compact-header { 
        background: linear-gradient(90deg, #1f293d 0%, #111827 100%); 
        padding: 8px 12px; 
        border-radius: 10px; 
        border: 1px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center; 
        margin-bottom: 6px; 
    }
    
    .market-glow { 
        background: rgba(16, 185, 129, 0.15); 
        color: #34d399; 
        padding: 3px 8px; 
        border-radius: 20px; 
        font-weight: 700; 
        font-size: 11px; 
        border: 1px solid #10b981;
    }
    
    .signal-card-up { 
        background: linear-gradient(135deg, #059669 0%, #10b981 100%); 
        padding: 12px; 
        border-radius: 10px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.5);
        border: 1px solid #34d399;
        margin-bottom: 6px;
    }
    
    .signal-card-down { 
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); 
        padding: 12px; 
        border-radius: 10px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.5);
        border: 1px solid #f87171;
        margin-bottom: 6px;
    }
    
    .signal-card-wait { 
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%); 
        padding: 12px; 
        border-radius: 10px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.5);
        border: 1px solid #fbbf24;
        margin-bottom: 6px;
    }

    .indicator-row { 
        background: rgba(17, 24, 39, 0.8); 
        padding: 6px 10px; 
        border-radius: 6px; 
        margin-bottom: 4px; 
        border: 1px solid #374151; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="compact-header">
        <div>
            <h4 style="margin:0; color: #60a5fa;">⚡ PRO CYBER BOT</h4>
        </div>
        <div>
            <span class="market-glow">● LIVE</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Compact Timeframe Selector
timeframe = st.radio("Timeframe", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

# Currency Pairs List in Sidebar
selected_asset = st.sidebar.selectbox("Select Currency Pair", [
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X", 
    "USDCAD=X", "NZDUSD=X", "EURJPY=X", "GBPJPY=X"
])

@st.cache_data(ttl=15)
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

interval_map = {"1m": "1m", "2m": "2m", "5m": "5m"}
current_interval = interval_map.get(timeframe, "1m")

df = load_data(selected_asset, current_interval)

if df is None:
    st.error("⚠️ Data fetch karne me samasya.")
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

    std_20 = close.rolling(20).std().iloc[-1]
    upper_band = sma_20 + (std_20 * 2)
    lower_band = sma_20 - (std_20 * 2)
    bb_status = "Price above mid" if current_price > sma_20 else "Price below mid"

    if rsi_14 > 55 and macd_status == "Bullish":
        market_state, confidence, signal_type = "UPTREND", "HIGH 🔥", "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        market_state, confidence, signal_type = "DOWNTREND", "HIGH 🔥", "DOWN"
    else:
        market_state, confidence, signal_type = "SIDEWAYS", "LOW ⚠️", "HOLD"

    # Mini Price Info Box
    st.markdown(f"""
        <div style="background: rgba(17, 24, 39, 0.9); padding: 8px 12px; border-radius: 8px; border: 1px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 13px; color: #9ca3af; font-weight: bold;">{selected_asset.replace('=X', '')} ({timeframe})</span>
            <span style="font-size: 14px; font-weight: bold; color: #38bdf8;">{current_price:.5f} 
                <span style="font-size: 11px; color: {'#34d399' if price_change >= 0 else '#f87171'};">
                    ({'+' if price_change >= 0 else ''}{price_change_pct:.2f}%)
                </span>
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Signal Card Display
    if signal_type == "UP":
        st.markdown('<div class="signal-card-up"><h3 style="margin:0; font-size:18px;">🚀 CALL / BUY (UP)</h3><p style="margin:0; font-size:11px; color:#d1fae5;">Strong Bullish Momentum</p></div>', unsafe_allow_html=True)
    elif signal_type == "DOWN":
        st.markdown('<div class="signal-card-down"><h3 style="margin:0; font-size:18px;">🔻 PUT / SELL (DOWN)</h3><p style="margin:0; font-size:11px; color:#fee2e2;">Strong Bearish Momentum</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-card-wait"><h3 style="margin:0; font-size:18px;">⏳ NO TRADE / HOLD</h3><p style="margin:0; font-size:11px; color:#fef3c7;">Market sideways - Wait</p></div>', unsafe_allow_html=True)

    # Mini Stats Row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div style='background:rgba(17,24,39,0.8); padding:5px; border-radius:6px; text-align:center; border:1px solid #374151;'><p style='margin:0; font-size:9px; color:#9ca3af;'>STATE</p><p style='margin:0; font-size:11px; font-weight:bold; color:#38bdf8;'>{market_state}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='background:rgba(17,24,39,0.8); padding:5px; border-radius:6px; text-align:center; border:1px solid #374151;'><p style='margin:0; font-size:9px; color:#9ca3af;'>CONF</p><p style='margin:0; font-size:11px; font-weight:bold; color:#34d399;'>{confidence}</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='background:rgba(17,24,39,0.8); padding:5px; border-radius:6px; text-align:center; border:1px solid #374151;'><p style='margin:0; font-size:9px; color:#9ca3af;'>RSI</p><p style='margin:0; font-size:11px; font-weight:bold; color:#fbbf24;'>{rsi_14:.1f}</p></div>", unsafe_allow_html=True)

    st.write("")
    
    # Mini Indicators List
    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("MACD", macd_status, "🟢" if macd_status == "Bullish" else "🔴"),
        ("Bollinger", bb_status, "💎")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #9ca3af;">{name}</span>
                <span><b style="color: #ffffff; margin-right: 5px;">{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)
