import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Pro Binary Signal Panel", page_icon="📈", layout="centered")

st.title("🚀 Pro Binary Options Signal Panel")
st.markdown("### EMA + RSI + MACD + Bollinger Bands (No Martingale)")

# Sidebar for settings
st.sidebar.header("⚙️ Settings")
selected_asset = st.sidebar.selectbox(
    "Select Currency Pair",
    ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "USDJPY=X", "BTC-USD"]
)

auto_refresh = st.sidebar.checkbox("Auto-Refresh Every 60s", value=False)

@st.cache_data(ttl=30)
def load_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception:
        return None

# Main Panel
df = load_data(selected_asset)

if df is None:
    st.error("❌ Data fetch karne me dikkat ya market band hai. Kripya baad me koshish karein.")
else:
    close = df['Close']
    
    # Indicators
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    upper_band = sma_20 + (std_20 * 2)
    lower_band = sma_20 - (std_20 * 2)
    
    ema_9 = close.ewm(span=9, adjust=False).mean()
    ema_21 = close.ewm(span=21, adjust=False).mean()
    
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    sig_line = macd.ewm(span=9, adjust=False).mean()
    
    res = pd.DataFrame({
        'Close': close, 'RSI': rsi, 'MACD': macd, 
        'Sig_Line': sig_line, 'EMA_9': ema_9, 
        'EMA_21': ema_21, 'SMA_20': sma_20,
        'Upper': upper_band, 'Lower': lower_band
    }).dropna()
    
    signal = '⏳ HOLD (WAIT - No Clear Setup)'
    
    call_cond = (res['EMA_9'].iloc[-1] > res['EMA_21'].iloc[-1]) & (res['RSI'].iloc[-1] > 45) & (res['RSI'].iloc[-1] < 65) & (res['MACD'].iloc[-1] > res['Sig_Line'].iloc[-1]) & (res['Close'].iloc[-1] > res['SMA_20'].iloc[-1]) & (res['Close'].iloc[-1] < res['Upper'].iloc[-1])
    
    put_cond = (res['EMA_9'].iloc[-1] < res['EMA_21'].iloc[-1]) & (res['RSI'].iloc[-1] > 35) & (res['RSI'].iloc[-1] < 55) & (res['MACD'].iloc[-1] < res['Sig_Line'].iloc[-1]) & (res['Close'].iloc[-1] < res['SMA_20'].iloc[-1]) & (res['Close'].iloc[-1] > res['Lower'].iloc[-1])
    
    if call_cond:
        signal = '🟢 STRONG CALL (UP)'
    elif put_cond:
        signal = '🔴 STRONG PUT (DOWN)'
        
    latest_close = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_macd = macd.iloc[-1]
    latest_sig = sig_line.iloc[-1]
    
    # UI Display Cards
    st.markdown("---")
    col1, col2 = st.columns(2)
    col1.metric("💰 Current Price", f"{latest_close:.5f}")
    col2.metric("📈 RSI Value", f"{latest_rsi:.2f}")
    
    macd_status = "Bullish 🚀" if latest_macd > latest_sig else "Bearish 🔻"
    st.info(f"⚡ **MACD Status:** {macd_status}")
    
    st.markdown("### 🎯 Final Signal Status:")
    if "STRONG CALL" in signal:
        st.success(f"### {signal}")
    elif "STRONG PUT" in signal:
        st.error(f"### {signal}")
    else:
        st.warning(f"### {signal}")
        
    st.markdown("---")
    st.caption("💡 **Rule Reminder:** 2-3 minute expiry, Mon-Fri peak volume only, strictly NO Martingale, 1-2% risk per trade.")
