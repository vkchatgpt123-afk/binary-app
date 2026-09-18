import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Reversal Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0b0f19; color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 0.3rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    .pairs-flex {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 6px;
        justify-content: space-between;
    }
    .pair-link {
        flex: 0 0 23.5%;
        background: #1f2937;
        color: #ffffff;
        border: 1px solid #374151;
        padding: 6px 2px;
        text-align: center;
        border-radius: 4px;
        font-size: 10px;
        font-weight: bold;
        text-decoration: none;
        box-sizing: border-box;
        margin-bottom: 4px;
    }
    .pair-link-active {
        background: #2563eb !important;
        border: 1px solid #60a5fa !important;
        color: #ffffff !important;
    }
    
    .signal-up { background: #059669; padding: 10px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 20px; margin: 4px 0; }
    .signal-down { background: #dc2626; padding: 10px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 20px; margin: 4px 0; }
    .signal-wait { background: #b7791f; padding: 10px; border-radius: 8px; text-align: center; color: white; font-weight: 800; font-size: 18px; margin: 4px 0; }
    
    .card { background: #1f2937; border: 1px solid #374151; border-radius: 6px; padding: 8px; margin: 4px 0; font-size: 11px; }
    .metric { background: #111827; border: 1px solid #1f2937; border-radius: 4px; padding: 5px; margin: 2px 0; display: flex; justify-content: space-between; font-size: 10px; }
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
        if df.empty or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# 1. 8 Pairs Grid Selection
pairs = [
    ("EURUSD", "EURUSD=X"), ("GBPUSD", "GBPUSD=X"), 
    ("AUDUSD", "AUDUSD=X"), ("USDJPY", "USDJPY=X"), 
    ("USDCAD", "USDCAD=X"), ("NZDUSD", "NZDUSD=X"), 
    ("EURJPY", "EURJPY=X"), ("GBPJPY", "GBPJPY=X")
]

html_code = '<div class="pairs-flex">'
for name, ticker in pairs:
    active_class = " pair-link-active" if selected_asset == ticker else ""
    html_code += f'<a href="?pair={ticker}" class="pair-link{active_class}">{name}</a>'
html_code += '</div>'
st.markdown(html_code, unsafe_allow_html=True)

# 2. Timeframe Selection
timeframe = st.selectbox("TF", ["5m", "1m", "2m"], index=0, label_visibility="collapsed")

df = load_data(selected_asset, timeframe)

if df is not None and not df.empty:
    needed = ["Open", "High", "Low", "Close"]
    df = df.dropna(subset=[x for x in needed if x in df.columns])
    
    if len(df) >= 50:
        data = df.iloc[:-1].copy() # Ignore forming candle
        o, h, l, c = [data[x].astype(float) for x in needed]
        
        tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        recent = data.iloc[-4:]
        atr_last = float(atr.iloc[-1])
        prior_median = float(atr.iloc[-50:-1].median())
        
        # Strict Reversal Logic Checks
        # DOWN Setup (After 4 bullish candles reversal)
        checks_down = {
            "4 consecutive bullish candles": bool((recent["Close"] > recent["Open"]).all()),
            "Last body >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.2 * atr_last),
            "Volatility ATR check": bool(atr_last > 0.9 * prior_median)
        }
        
        # UP Setup (After 4 bearish candles reversal)
        checks_up = {
            "4 consecutive bearish candles": bool((recent["Close"] < recent["Open"]).all()),
            "Last body >= 1.5 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.2 * atr_last),
            "Volatility ATR check": bool(atr_last > 0.9 * prior_median)
        }

        if all(checks_down.values()):
            signal = "DOWN ⬇️"
            checks = checks_down
        elif all(checks_up.values()):
            signal = "UP ⬆️"
            checks = checks_up
        else:
            signal = "NO TRADE ⏸"
            checks = checks_down
            
        price = float(c.iloc[-1])
        prev = float(c.iloc[-2])
        pct = (price - prev) / prev * 100 if prev else 0
    else:
        signal, price, pct, checks, atr_last = "NO TRADE ⏸", 0, 0, {}, 0
else:
    signal, price, pct, checks, atr_last = "NO TRADE ⏸", 0, 0, {}, 0

# 3. UI Display
st.markdown(f'''
    <div class="card">
        <b>{selected_asset.replace("=X", "")} • {timeframe}</b>
        <span style="float:right; color: {"#34d399" if pct >= 0 else "#f87171"};">{price:.5f} ({pct:+.2f}%)</span>
    </div>
''', unsafe_allow_html=True)

if "DOWN" in signal:
    st.markdown('<div class="signal-down">DOWN SIGNAL 📉</div>', unsafe_allow_html=True)
elif "UP" in signal:
    st.markdown('<div class="signal-up">UP SIGNAL 📈</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal-wait">NO TRADE / WAIT ⏸</div>', unsafe_allow_html=True)

# 4. Detailed Checks & Metrics
st.markdown("### Setup Filters")
if checks:
    for name, ok in checks.items():
        st.markdown(f'<div class="metric"><span>{name}</span><b>{"PASS ✅" if ok else "FAIL ❌"}</b></div>', unsafe_allow_html=True)

st.markdown(f'<div class="metric"><span>ATR(14) Volatility</span><b>{atr_last:.5f}</b></div>', unsafe_allow_html=True)

# 5. Reboot Terminal Button
if st.button("🔌 Reboot Terminal", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()
