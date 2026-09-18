import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Reversal Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0b0f19; color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 2.2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* 2 Rows of 4 Pairs Layout with proper top spacing */
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
    
    .signal-up { background: #10b981; padding: 12px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 22px; margin: 4px 0; }
    .signal-down { background: #ef4444; padding: 12px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 22px; margin: 4px 0; }
    .signal-hold { background: #b7791f; padding: 12px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 20px; margin: 4px 0; }
    
    .status-bar {
        background: #1f2937;
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid #374151;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        font-size: 12px;
        font-weight: bold;
    }
    .indicator-row { 
        background: #111827; 
        padding: 5px 8px; 
        border-radius: 5px; 
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
        df = yf.download(ticker, period="3d", interval=interval_val, progress=False, auto_adjust=False, threads=False)
        if df.empty or len(df) < 120:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# 8 Pairs in 2 Rows
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

# Timeframe Selection
timeframe = st.radio("TF", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

df = load_data(selected_asset, timeframe)

if df is not None and not df.empty:
    needed = ["Open", "High", "Low", "Close"]
    df = df.dropna(subset=[x for x in needed if x in df.columns])
    df = df[~df.index.duplicated(keep="last")]
    
    if len(df) >= 116:
        data = df.iloc[:-1].copy()
        o, h, l, c = [data[x].astype(float) for x in needed]
        
        tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        recent = data.iloc[-4:]
        atr_last = float(atr.iloc[-1])
        prior_median = float(atr.iloc[-101:-1].median())
        
        checks_down = {
            "4 consecutive bullish candles": bool((recent["Close"] > recent["Open"]).all()),
            "Last body >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.5 * atr_last),
            "Close >= 85% of range": bool((c.iloc[-1] - l.iloc[-1]) / (h.iloc[-1] - l.iloc[-1]) >= .85) if h.iloc[-1] > l.iloc[-1] else False,
            "ATR > 1.2 × prior median": bool(atr_last > 1.2 * prior_median)
        }
        
        checks_up = {
            "4 consecutive bearish candles": bool((recent["Close"] < recent["Open"]).all()),
            "Last body >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.5 * atr_last),
            "Close <= 15% of range": bool((c.iloc[-1] - l.iloc[-1]) / (h.iloc[-1] - l.iloc[-1]) <= .15) if h.iloc[-1] > l.iloc[-1] else False,
            "ATR > 1.2 × prior median": bool(atr_last > 1.2 * prior_median)
        }

        if all(checks_down.values()):
            signal_type = "DOWN"
            market_state = "REVERSAL DOWN 📉"
            confidence = "HIGH 🔥"
        elif all(checks_up.values()):
            signal_type = "UP"
            market_state = "REVERSAL UP 📈"
            confidence = "HIGH 🔥"
        else:
            signal_type = "HOLD"
            market_state = "SIDEWAYS / WAIT ↔️"
            confidence = "LOW ⚠️"
            
        current_price = float(c.iloc[-1])
        prev_price = float(c.iloc[-2])
        price_change_pct = ((current_price - prev_price) / prev_price) * 100
        
        sma_20 = float(c.rolling(20).mean().iloc[-1])
        ema_12 = float(c.ewm(span=12, adjust=False).mean().iloc[-1])
        
        bb_std = float(c.rolling(20).std().iloc[-1])
        bb_upper = sma_20 + (bb_std * 2)
        bb_lower = sma_20 - (bb_std * 2)
        
        delta = c.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean().iloc[-1]
        avg_loss = loss.rolling(14).mean().iloc[-1]
        rs = avg_gain / (avg_loss + 1e-10)
        rsi_14 = float(100 - (100 / (1 + rs)))

        exp1 = c.ewm(span=12, adjust=False).mean()
        exp2 = c.ewm(span=26, adjust=False).mean()
        macd_val = (exp1 - exp2).iloc[-1]
        sig_val = (exp1 - exp2).ewm(span=9, adjust=False).mean().iloc[-1]
        macd_status = "Bullish" if macd_val > sig_val else "Bearish"
    else:
        current_price, price_change_pct, signal_type, market_state, confidence = 0.0, 0.0, "HOLD", "NOT ENOUGH DATA", "LOW"
        sma_20, ema_12, bb_lower, bb_upper, rsi_14 = 0, 0, 0, 0, 50
        macd_status = "Neutral"
else:
    current_price, price_change_pct, signal_type, market_state, confidence = 0.0, 0.0, "HOLD", "NO DATA", "LOW"
    sma_20, ema_12, bb_lower, bb_upper, rsi_14 = 0, 0, 0, 0, 50
    macd_status = "Neutral"

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
    st.markdown('<div class="signal-up">UP</div>', unsafe_allow_html=True)
elif signal_type == "DOWN":
    st.markdown('<div class="signal-down">DOWN</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal-hold">NO TRADE / HOLD</div>', unsafe_allow_html=True)

st.markdown(f"""
    <div class="status-bar">
        <span>State: <span style="color: {'#34d399' if 'UP' in market_state else '#f87171' if 'DOWN' in market_state else '#fbbf24'};">{market_state}</span></span>
        <span>Conf: <span style="color: #60a5fa;">{confidence}</span></span>
    </div>
""", unsafe_allow_html=True)

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
            <span><b style="color: #ffffff; margin-right: 6px;">{val}</b> {status}</span>
        </div>
    """, unsafe_allow_html=True)

refresh_rate = st.selectbox("Refresh Rate", ["60s", "30s", "2m", "5m"], label_visibility="collapsed")

if st.button("🔌 Reboot Terminal", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()
