import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Reversal Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0b0f19; color: #ffffff; font-family: sans-serif; }
    .block-container { padding-top: 0.2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    .pairs-container {
        display: flex;
        flex-direction: column;
        gap: 3px;
        margin-bottom: 4px;
    }
    .pairs-row {
        display: flex;
        justify-content: space-between;
        gap: 3px;
    }
    .pair-link {
        flex: 1;
        background: #1f2937;
        color: #ffffff;
        border: 1px solid #374151;
        padding: 5px 2px;
        text-align: center;
        border-radius: 4px;
        font-size: 9px;
        font-weight: bold;
        text-decoration: none;
        box-sizing: border-box;
    }
    .pair-link-active {
        background: #2563eb !important;
        border: 1px solid #60a5fa !important;
        color: #ffffff !important;
    }
    
    .signal-up { background: #059669; padding: 8px; border-radius: 6px; text-align: center; color: white; font-weight: 800; font-size: 16px; margin: 3px 0; }
    .signal-down { background: #dc2626; padding: 8px; border-radius: 6px; text-align: center; color: white; font-weight: 800; font-size: 16px; margin: 3px 0; }
    .signal-wait { background: #b7791f; padding: 8px; border-radius: 6px; text-align: center; color: white; font-weight: 800; font-size: 15px; margin: 3px 0; }
    
    .card { background: #1f2937; border: 1px solid #374151; border-radius: 6px; padding: 6px 8px; margin: 3px 0; font-size: 11px; }
    .metric { background: #111827; border: 1px solid #1f2937; border-radius: 4px; padding: 4px 6px; margin: 2px 0; display: flex; justify-content: space-between; font-size: 10px; }
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

# 1. 8 Pairs Divided into Strict 2 Rows (4 pairs each) for Perfect Mobile Fit
row1_pairs = [
    ("EURUSD", "EURUSD=X"), ("GBPUSD", "GBPUSD=X"), 
    ("AUDUSD", "AUDUSD=X"), ("USDJPY", "USDJPY=X")
]
row2_pairs = [
    ("USDCAD", "USDCAD=X"), ("NZDUSD", "NZDUSD=X"), 
    ("EURJPY", "EURJPY=X"), ("GBPJPY", "GBPJPY=X")
]

def render_row(pair_list):
    html = '<div class="pairs-row">'
    for name, ticker in pair_list:
        active = " pair-link-active" if selected_asset == ticker else ""
        html += f'<a href="?pair={ticker}" class="pair-link{active}">{name}</a>'
    html += '</div>'
    return html

st.markdown(f'''
    <div class="pairs-container">
        {render_row(row1_pairs)}
        {render_row(row2_pairs)}
    </div>
''', unsafe_allow_html=True)

# 2. Timeframe Selection
timeframe = st.radio("TF", ["5m", "1m", "2m"], horizontal=True, label_visibility="collapsed")

df = load_data(selected_asset, timeframe)

if df is not None and not df.empty:
    needed = ["Open", "High", "Low", "Close"]
    df = df.dropna(subset=[x for x in needed if x in df.columns])
    
    if len(df) >= 50:
        data = df.iloc[:-1].copy() 
        o, h, l, c = [data[x].astype(float) for x in needed]
        
        tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        recent = data.iloc[-4:]
        atr_last = float(atr.iloc[-1])
        prior_median = float(atr.iloc[-50:-1].median())
        
        checks_down = {
            "4 consecutive bullish candles": bool((recent["Close"] > recent["Open"]).all()),
            "Last body >= 1.2 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.2 * atr_last),
            "Volatility ATR check": bool(atr_last > 0.8 * prior_median)
        }
        
        checks_up = {
            "4 consecutive bearish candles": bool((recent["Close"] < recent["Open"]).all()),
            "Last body >= 1.2 × ATR": bool(abs(o.iloc[-1] - c.iloc[-1]) >= 1.2 * atr_last),
            "Volatility ATR check": bool(atr_last > 0.8 * prior_median)
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

# 3. UI Display Cards
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
