import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="PRO Quotex Cyber Bot", page_icon="⚡", layout="centered")

# 60 Seconds Auto-Refresh Meta Tag
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

# Pro Bright & Colorful Cyber Styling
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #050814 0%, #0b1329 100%); color: #ffffff; }
    
    .pro-header { 
        background: linear-gradient(90deg, #1f293d 0%, #111827 100%); 
        padding: 15px 20px; 
        border-radius: 16px; 
        border: 1px solid #3b82f6; 
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
        display: flex; justify-content: space-between; align-items: center; 
        margin-bottom: 15px; 
    }
    
    .market-glow { 
        background: rgba(16, 185, 129, 0.15); 
        color: #34d399; 
        padding: 6px 14px; 
        border-radius: 30px; 
        font-weight: 800; 
        font-size: 13px; 
        border: 1px solid #10b981;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
    }
    
    .signal-card-up { 
        background: linear-gradient(135deg, #059669 0%, #10b981 100%); 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.6);
        border: 2px solid #34d399;
        animation: pulse 2s infinite;
    }
    
    .signal-card-down { 
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 30px rgba(239, 68, 68, 0.6);
        border: 2px solid #f87171;
        animation: pulse 2s infinite;
    }
    
    .signal-card-wait { 
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%); 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center; 
        color: white; 
        font-weight: bold; 
        box-shadow: 0 0 30px rgba(245, 158, 11, 0.6);
        border: 2px solid #fbbf24;
    }
    
    .stat-card {
        background: rgba(17, 24, 39, 0.8);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #374151;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .indicator-row { 
        background: rgba(17, 24, 39, 0.9); 
        padding: 12px 18px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        border: 1px solid #374151; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        box-shadow: inset 0 1px 3px rgba(255,255,255,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="pro-header">
        <div>
            <h2 style="margin:0; color: #60a5fa; text-shadow: 0 0 10px rgba(96,165,250,0.5);">⚡ PRO CYBER BOT</h2>
            <p style="margin:0; font-size:12px; color: #9ca3af;">AI Trading Terminal & Live Scanner</p>
        </div>
        <div>
            <span class="market-glow">● ONLINE</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Timeframe Selector
timeframe = st.radio("Select Timeframe", ["1 Min", "2 Min", "5 Min"], horizontal=True)

# Currency Pairs List
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

interval_map = {"1 Min": "1m", "2 Min": "2m", "5 Min": "5m"}
current_interval = interval_map.get(timeframe, "1m")

df = load_data(selected_asset, current_interval)

if df is None:
    st.error("⚠️ Data fetch karne me samasya aa rahi hai.")
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
    bb_status = "Price above middle" if current_price > sma_20 else "Price below middle"

    if rsi_14 > 55 and macd_status == "Bullish":
        market_state, confidence, signal_type = "UPTREND", "HIGH 🔥", "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        market_state, confidence, signal_type = "DOWNTREND", "HIGH 🔥", "DOWN"
    else:
        market_state, confidence, signal_type = "SIDEWAYS", "LOW ⚠️", "HOLD"

    st.markdown(f"""
        <div style="background: rgba(17, 24, 39, 0.9); padding: 15px; border-radius: 14px; border: 1px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; box-shadow: 0 0 15px rgba(59,130,246,0.2);">
            <div>
                <span style="background: #3b82f6; color: white; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">PAIR</span>
                <h3 style="margin:5px 0 0 0; color: #ffffff;">{selected_asset.replace('=X', '')} <span style="font-size:13px; color:#9ca3af;">({timeframe})</span></h3>
            </div>
            <div style="text-align: right;">
                <h2 style="margin:0; color: #38bdf8; text-shadow: 0 0 10px rgba(56,189,248,0.4);">{current_price:.5f}</h2>
                <span style="color: {'#34d399' if price_change >= 0 else '#f87171'}; font-size: 14px; font-weight: bold;">
                    {'+' if price_change >= 0 else ''}{price_change:.5f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <p style="margin:0; font-size:12px; color:#9ca3af; font-weight:600;">MARKET STATE</p>
                <h3 style="margin:5px 0 0 0; color: {'#34d399' if market_state=='UPTREND' else '#f87171' if market_state=='DOWNTREND' else '#fbbf24'};">{market_state}</h3>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <p style="margin:0; font-size:12px; color:#9ca3af; font-weight:600;">CONFIDENCE</p>
                <h3 style="margin:5px 0 0 0; color: {'#34d399' if 'HIGH' in confidence else '#fbbf24'};">{confidence}</h3>
            </div>
        """, unsafe_allow_html=True)

    st.write("")

    if signal_type == "UP":
        st.markdown('<div class="signal-card-up"><h1 style="margin:0; font-size:28px; text-shadow: 0 0 10px white;">🚀 CALL / BUY (UP)</h1><p style="margin:5px 0 0 0; font-size:14px; color:#d1fae5;">Strong Bullish Momentum Detected</p></div>', unsafe_allow_html=True)
    elif signal_type == "DOWN":
        st.markdown('<div class="signal-card-down"><h1 style="margin:0; font-size:28px; text-shadow: 0 0 10px white;">🔻 PUT / SELL (DOWN)</h1><p style="margin:5px 0 0 0; font-size:14px; color:#fee2e2;">Strong Bearish Momentum Detected</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-card-wait"><h1 style="margin:0; font-size:26px;">⏳ NO TRADE / HOLD</h1><p style="margin:5px 0 0 0; font-size:14px; color:#fef3c7;">Market sideways hai, safe raho!</p></div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("### 📊 Advanced Indicators")

    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("RSI 14", f"{rsi_14:.1f}", "🟢" if rsi_14 > 50 else "🔴"),
        ("MACD Signal", macd_status, "🟢" if macd_status == "Bullish" else "🔴"),
        ("Bollinger Bands", bb_status, "💎")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #9ca3af; font-weight: 500;">{name}</span>
                <span><b style="color: #ffffff; margin-right: 8px;">{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(30, 58, 138, 0.3); padding: 15px; border-radius: 12px; border: 1px solid #3b82f6;">
            <p style="margin:0; font-weight:bold; color: #60a5fa; font-size: 14px;">🛡️ Pro Trading Rules:</p>
            <ul style="margin:5px 0 0 0; padding-left: 15px; font-size: 13px; color: #93c5fd;">
                <li>Auto-refresh active (60 seconds).</li>
                <li>Strictly avoid Martingale and trade with 1-2% risk.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
