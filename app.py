import streamlit as st

# Page Configuration
st.set_page_config(page_title="Quotex Signal Bot Pro", page_width="centered")

# Custom Quotex Styling & Layout
st.markdown("""
    <style>
        :root {
            --bg-color: #0b0e14;
            --card-bg: #131823;
            --border-color: #222b3d;
            --accent-green: #00ecb7;
            --accent-red: #ff3366;
            --text-main: #ffffff;
            --text-secondary: #8492a6;
            --gold: #f5a623;
        }

        .stApp {
            background-color: var(--bg-color);
        }

        .top-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .acc-balance {
            font-size: 16px;
            font-weight: bold;
            color: var(--gold);
        }

        .signal-btn-up {
            width: 100%;
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: #051310;
            padding: 16px;
            font-size: 22px;
            font-weight: 900;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 0 15px rgba(0, 236, 183, 0.4);
            margin-bottom: 10px;
        }

        .card-box {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            color: var(--text-main);
        }
    </style>
""", unsafe_allow_html=True)

# Quotex Header UI
st.markdown("""
    <div class="top-header">
        <div>
            <div style="font-size: 10px; color: #8492a6; font-weight: bold;">DEMO ACCOUNT</div>
            <div class="acc-balance">$9,871.99</div>
        </div>
        <button style="background: #00ecb7; color: #000; border: none; padding: 6px 14px; font-weight: bold; border-radius: 4px; cursor: pointer;">Deposit</button>
    </div>
""", unsafe_allow_html=True)

# Time Selector
col1, col2, col3 = st.columns(3)
with col1:
    st.radio("Timeframe", ["1m", "2m", "5m"], horizontal=True, label_visibility="collapsed")

# Signal Box Display
st.markdown("""
    <div class="card-box">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #8492a6; margin-bottom: 8px;">
            <span>EURUSD (1m)</span>
            <span style="color: #00ecb7;">1.14692 (+0.01%)</span>
        </div>
        <div class="signal-btn-up">UP</div>
    </div>
""", unsafe_allow_html=True)

# Market State
st.markdown("""
    <div class="card-box" style="display: flex; justify-content: space-between; font-size: 12px; font-weight: bold;">
        <div>State: <span style="color: #00ecb7;">UPTREND 📈</span></div>
        <div>Conf: <span style="color: #f5a623;">HIGH 🔥</span></div>
    </div>
""", unsafe_allow_html=True)

# Technical Indicators
st.markdown("""
    <div class="card-box">
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #222b3d; font-size: 12px;">
            <span style="color: #8492a6;">SMA 20</span>
            <span>1.14659 🟢</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #222b3d; font-size: 12px;">
            <span style="color: #8492a6;">EMA 12</span>
            <span>1.14683 🟢</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #222b3d; font-size: 12px;">
            <span style="color: #8492a6;">BB Lower/Upper</span>
            <span>1.1459 / 1.1473 🟢</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #222b3d; font-size: 12px;">
            <span style="color: #8492a6;">RSI (14)</span>
            <span>64.7 🟢</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 12px;">
            <span style="color: #8492a6;">MACD</span>
            <span>Bullish 🟢</span>
        </div>
    </div>
""", unsafe_allow_html=True)
