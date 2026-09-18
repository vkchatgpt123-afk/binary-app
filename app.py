import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Quotex Signal Bot", page_icon="📈", layout="centered")

# 60 Seconds Auto-Refresh Meta Tag
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .top-header { display: flex; justify-content: space-between; align-items: center; background: #161b22; padding: 10px 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 10px; }
    .market-badge { background: #21262d; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; border: 1px solid #30363d; }
    .signal-card-up { background: linear-gradient(135deg, #238636, #2ea043); padding: 20px; border-radius: 12px; text-align: center; color: white; font-weight: bold; box-shadow: 0 0 15px rgba(46,160,67,0.4); }
    .signal-card-down { background: linear-gradient(135deg, #da3633, #f85149); padding: 20px; border-radius: 12px; text-align: center; color: white; font-weight: bold; box-shadow: 0 0 15px rgba(218,54,51,0.4); }
    .signal-card-wait { background: linear-gradient(135deg, #9e6a03, #bb8009); padding: 20px; border-radius: 12px; text-align: center; color: white; font-weight: bold; box-shadow: 0 0 15px rgba(187,128,9,0.4); }
    .indicator-row { background: #161b22; padding: 10px 15px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="top-header">
        <div>
            <h3 style="margin:0; color: #58a6ff;">📈 Quotex Signal Bot</h3>
            <p style="margin:0; font-size:12px; color: #8b949e;">Auto-Refresh: 60s Active</p>
        </div>
        <div>
            <span class="market-badge" style="color: #3fb950;">● LIVE</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Expanded Currency Pairs List
selected_asset = st.sidebar.selectbox("Select Currency Pair", [
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X", 
    "USDCAD=X", "NZDUSD=X", "EURJPY=X", "GBPJPY=X"
])

@st.cache_data(ttl=15)
def load_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 20:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

df = load_data(selected_asset)

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
        market_state, confidence, signal_type = "UPTREND", "HIGH", "UP"
    elif rsi_14 < 45 and macd_status == "Bearish":
        market_state, confidence, signal_type = "DOWNTREND", "HIGH", "DOWN"
    else:
        market_state, confidence, signal_type = "SIDEWAYS", "LOW", "HOLD"

    st.markdown(f"""
        <div style="background: #161b22; padding: 12px; border-radius: 10px; border: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div><h4 style="margin:0; color: #8b949e;">{selected_asset.replace('=X', '')} (Live)</h4></div>
            <div style="text-align: right;">
                <h3 style="margin:0; color: #ffffff;">{current_price:.5f}</h3>
                <span style="color: {'#3fb950' if price_change >= 0 else '#f85149'}; font-size: 13px; font-weight: bold;">
                    {'+' if price_change >= 0 else ''}{price_change:.5f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div style="background: #161b22; padding: 10px; border-radius: 8px; border: 1px solid #30363d; text-align: center;">
                <p style="margin:0; font-size:11px; color:#8b949e;">Market State</p>
                <h4 style="margin:0; color: {'#3fb950' if market_state=='UPTREND' else '#f85149' if market_state=='DOWNTREND' else '#d29922'};">{market_state}</h4>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background: #161b22; padding: 10px; border-radius: 8px; border: 1px solid #30363d; text-align: center;">
                <p style="margin:0; font-size:11px; color:#8b949e;">Confidence</p>
                <h4 style="margin:0; color: {'#3fb950' if confidence=='HIGH' else '#d29922'};">{confidence}</h4>
            </div>
        """, unsafe_allow_html=True)

    st.write("")

    if signal_type == "UP":
        st.markdown('<div class="signal-card-up"><h2>🚀 UP (CALL / BUY)</h2><p style="margin:0; font-size:13px;">Strong Bullish Momentum Detected</p></div>', unsafe_allow_html=True)
    elif signal_type == "DOWN":
        st.markdown('<div class="signal-card-down"><h2>🔻 DOWN (PUT / SELL)</h2><p style="margin:0; font-size:13px;">Strong Bearish Momentum Detected</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-card-wait"><h2>⏳ NO TRADE / HOLD</h2><p style="margin:0; font-size:13px;">Market clear nahi hai, Wait karo</p></div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("### 📊 Indicator Breakdown")

    indicators = [
        ("SMA 20", f"{sma_20:.5f}", "🟢" if current_price > sma_20 else "🔴"),
        ("EMA 12", f"{ema_12:.5f}", "🟢" if current_price > ema_12 else "🔴"),
        ("RSI 14", f"{rsi_14:.1f}", "🟢" if rsi_14 > 50 else "🔴"),
        ("MACD", macd_status, "🟢" if macd_status == "Bullish" else "🔴"),
        ("Bollinger Bands", bb_status, "⚪")
    ]

    for name, val, status in indicators:
        st.markdown(f"""
            <div class="indicator-row">
                <span style="color: #8b949e;">{name}</span>
                <span><b>{val}</b> {status}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
        <div style="background: #161b22; padding: 12px; border-radius: 8px; border: 1px solid #30363d;">
            <p style="margin:0; font-weight:bold; color: #58a6ff; font-size: 13px;">💡 Rules:</p>
            <ul style="margin:5px 0 0 0; padding-left: 15px; font-size: 12px; color: #8b949e;">
                <li>Page automatically har 60 seconds me refresh hoga.</li>
                <li>Strictly NO Martingale, 1-2% risk per trade.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
