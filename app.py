import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="EUR/USD Signal Terminal", page_icon="⚡", layout="centered")

st.markdown("""
<style>
.stApp{background:#0b0f19;color:#fff}
.block-container{padding-top:.7rem;max-width:760px}
.card{background:#1f2937;border:1px solid #374151;border-radius:8px;padding:10px;margin:6px 0}
.up{background:#059669;padding:12px;border-radius:8px;text-align:center;font-weight:800;font-size:24px}
.down{background:#dc2626;padding:12px;border-radius:8px;text-align:center;font-weight:800;font-size:24px}
.wait{background:#b7791f;padding:12px;border-radius:8px;text-align:center;font-weight:800;font-size:22px}
.metric{background:#111827;border:1px solid #1f2937;border-radius:6px;padding:7px;margin:3px 0;display:flex;justify-content:space-between;font-size:13px}
.small{color:#9ca3af;font-size:11px}
</style>
""", unsafe_allow_html=True)

st.title("⚡ EUR/USD Signal Terminal")
st.caption("Manual signal assistant • Research/Demo use only")

timeframe = st.selectbox("Timeframe", ["5m", "1m", "2m"], index=0)
refresh = st.selectbox("Refresh", ["Off", "30 sec", "60 sec", "120 sec"], index=2)

try:
    df = yf.download("EURUSD=X", period="5d", interval=timeframe,
                     progress=False, auto_adjust=False, threads=False)
except Exception:
    df = pd.DataFrame()

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

needed = ["Open","High","Low","Close"]
if not df.empty and all(x in df.columns for x in needed):
    df = df.dropna(subset=needed)
    df = df[~df.index.duplicated(keep="last")]

if len(df) < 116:
    st.markdown('<div class="wait">⏸ NO TRADE</div>', unsafe_allow_html=True)
    st.warning(f"Not enough candles. Need at least 116; received {len(df)}.")
    st.stop()

# Ignore the latest candle because it may still be forming.
data = df.iloc[:-1].copy()
o,h,l,c = [data[x].astype(float) for x in needed]

tr = pd.concat([(h-l),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
atr = tr.rolling(14).mean()

recent = data.iloc[-4:]
atr_last = float(atr.iloc[-1])
prior_median = float(atr.iloc[-101:-1].median())

checks = {
    "4 consecutive bullish 5M candles": bool((recent["Close"] > recent["Open"]).all()),
    "Last body >= 1.5 × ATR": bool(abs(o.iloc[-1]-c.iloc[-1]) >= 1.5*atr_last),
    "Close >= 85% of range": bool((c.iloc[-1]-l.iloc[-1])/(h.iloc[-1]-l.iloc[-1]) >= .85) if h.iloc[-1] > l.iloc[-1] else False,
    "ATR > 1.2 × prior 100 ATR median": bool(atr_last > 1.2*prior_median)
}
signal = "DOWN" if all(checks.values()) else "NO TRADE"

ema12 = c.ewm(span=12,adjust=False).mean().iloc[-1]
ema26 = c.ewm(span=26,adjust=False).mean().iloc[-1]
state = "UPTREND 📈" if c.iloc[-1] > ema12 > ema26 else ("DOWNTREND 📉" if c.iloc[-1] < ema12 < ema26 else "SIDEWAYS ↔️")

price=float(c.iloc[-1]); prev=float(c.iloc[-2])
pct=(price-prev)/prev*100 if prev else 0

st.markdown(f'<div class="card"><b>EUR/USD • {timeframe}</b><span style="float:right">{price:.5f} ({pct:+.2f}%)</span></div>', unsafe_allow_html=True)
st.markdown(f'<div class="{"down" if signal=="DOWN" else "wait"}">{"⬇ DOWN" if signal=="DOWN" else "⏸ NO TRADE"}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="card"><b>Market State:</b> {state}<br><span class="small">Strict 5M reversal research setup • 1 candle / 5 min expiry</span></div>', unsafe_allow_html=True)

st.markdown("### Setup checks")
for name,ok in checks.items():
    st.markdown(f'<div class="metric"><span>{name}</span><b>{"PASS ✅" if ok else "FAIL ❌"}</b></div>',unsafe_allow_html=True)

st.markdown("### Data")
st.markdown(f'<div class="metric"><span>Completed candles</span><b>{len(data)}</b></div>'
            f'<div class="metric"><span>ATR(14)</span><b>{atr_last:.6f}</b></div>',unsafe_allow_html=True)

st.info("No automatic trading. External EUR/USD data may differ from Quotex/broker server data. Research/demo only.")
