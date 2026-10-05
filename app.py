import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime as dt
import json
import os
import math

# ============================================================
# EUR/USD SIGNAL PRO V9
# Tabs layout (minimal scrolling) | One engine for live+backtest
# Manual only | Demo first | No guarantee of profit
# ============================================================

st.set_page_config(page_title="EUR/USD Signal PRO V9", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

SYMBOL = "EURUSD=X"
PIP = 0.0001
JOURNAL_FILE = "eurusd_v9_journal.json"

TF = {
    "1m": dict(interval="1m", range="7d", minutes=1, htf="5m"),
    "5m": dict(interval="5m", range="60d", minutes=5, htf="15m"),
    "15m": dict(interval="15m", range="60d", minutes=15, htf="60m"),
}
HTF = {"5m": ("5m", "60d", 5), "15m": ("15m", "60d", 15), "60m": ("60m", "1y", 60)}
HTF_NAME = {1: "UP", -1: "DOWN", 0: "NEUTRAL"}

# ============================================================
# STYLE
# ============================================================
st.markdown("""
<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.stApp {background:linear-gradient(180deg,#f4f9ff 0%,#fff 50%);}
.block-container {max-width:1100px; padding:.6rem .8rem 1rem;}
.hdr {display:flex; flex-wrap:wrap; align-items:center; gap:6px; justify-content:space-between;
      background:linear-gradient(135deg,#0057e7,#00a8ff); color:#fff; padding:10px 14px;
      border-radius:14px; margin-bottom:8px; box-shadow:0 6px 18px rgba(0,87,231,.18);}
.hdr .t {font-weight:850; font-size:18px; letter-spacing:.3px;}
.pill {display:inline-block; font-size:11px; font-weight:700; padding:3px 9px; border-radius:20px;
       margin-left:4px; background:rgba(255,255,255,.22); color:#fff;}
.pill.ok {background:#17b26a;} .pill.bad {background:#ef4444;} .pill.warn {background:#f2b705; color:#222;}
.stTabs [data-baseweb="tab-list"] {gap:2px;}
.stTabs [data-baseweb="tab"] {font-weight:750; padding:6px 10px;}
.sig {border-radius:16px; padding:14px 10px; text-align:center; border:2px solid; margin-bottom:8px;}
.sig.up {background:linear-gradient(135deg,#e6fff1,#fff); border-color:#17b26a;}
.sig.down {background:linear-gradient(135deg,#fff0f0,#fff); border-color:#ef4444;}
.sig.wait {background:linear-gradient(135deg,#fff9df,#fff); border-color:#f2b705;}
.sig .big {font-size:36px; font-weight:900; line-height:1.1;}
.sig.up .big {color:#0b8f4d;} .sig.down .big {color:#d62a2a;} .sig.wait .big {color:#9a7200;}
.sig .sub {font-size:12.5px; font-weight:650; color:#445; margin-top:4px;}
.kgrid {display:grid; gap:6px; margin-bottom:8px;}
.kpi {background:#fff; border:1px solid #dcecff; border-radius:12px; padding:6px 8px;
      box-shadow:0 3px 10px rgba(25,80,140,.06);}
.kl {font-size:10.5px; color:#6b7b90; font-weight:700; text-transform:uppercase;}
.kv {font-size:16px; font-weight:850; color:#0b3b78;}
.kv.g {color:#0b8f4d;} .kv.r {color:#d62a2a;} .kv.y {color:#9a7200;}
.clock {background:#fff; border:1px solid #dcecff; border-radius:12px; padding:8px 12px;
        display:flex; justify-content:space-between; font-weight:750; font-size:13px; margin-bottom:8px;}
.note {color:#6b7b90; font-size:11.5px;}
.stButton > button, .stDownloadButton > button {border-radius:10px; font-weight:800;}
@media (max-width:640px){.sig .big{font-size:30px}.kv{font-size:14px}}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def pill(text, kind=""):
    return f'<span class="pill {kind}">{text}</span>'


def kpis(items, cols=3):
    h = "".join(f'<div class="kpi"><div class="kl">{l}</div><div class="kv {c}">{v}</div></div>'
                for l, v, c in items)
    st.markdown(f'<div class="kgrid" style="grid-template-columns:repeat({cols},1fr)">{h}</div>',
                unsafe_allow_html=True)


def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_journal(data):
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, default=str)
        return True
    except Exception:
        return False


# ============================================================
# MARKET DATA
# ============================================================
@st.cache_data(ttl=10, show_spinner=False)
def fetch_yahoo(interval, period):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}"
           f"?interval={interval}&range={period}")
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        ts = res.get("timestamp", [])
        q = res["indicators"]["quote"][0]
        if not ts:
            return pd.DataFrame()
        df = pd.DataFrame({
            "time": pd.to_datetime(ts, unit="s", utc=True).astype("datetime64[ns, UTC]"),
            "open": q.get("open"), "high": q.get("high"),
            "low": q.get("low"), "close": q.get("close"),
        })
        df = df.dropna().sort_values("time").drop_duplicates("time")
        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def data_quality(df, tf):
    if df.empty:
        return False, "No market data (feed down or rate-limited).", None
    if len(df) < 300:
        return False, f"Only {len(df)} candles available (need 300+).", None
    exp = TF[tf]["minutes"]
    d = df["time"].diff().dropna().dt.total_seconds() / 60
    normal = d[d <= exp * 4]
    sp = float(normal.median()) if not normal.empty else None
    if sp is not None and abs(sp - exp) > max(1.0, exp * 0.35):
        return False, f"Timeframe mismatch: expected ~{exp}m, got ~{sp:.1f}m.", sp
    bad = ((df.high < df.low) | (df.open > df.high) | (df.open < df.low) |
           (df.close > df.high) | (df.close < df.low))
    if bad.any():
        return False, "Invalid OHLC candle detected.", sp
    return True, "OK", sp


def closed_index(df, tf):
    m = TF[tf]["minutes"]
    last_close = df["time"].iloc[-1].to_pydatetime() + dt.timedelta(minutes=m)
    if utc_now() >= last_close:
        return len(df) - 1
    return len(df) - 2 if len(df) >= 2 else None


# ============================================================
# INDICATORS (Wilder ADX / RSI / ATR)
# ============================================================
def add_indicators(df):
    x = df.copy()
    c, h, l, o = x.close, x.high, x.low, x.open
    a = 1 / 14
    for s in (9, 21, 50):
        x[f"ema{s}"] = c.ewm(span=s, adjust=False).mean()

    d = c.diff()
    g = d.clip(lower=0).ewm(alpha=a, adjust=False).mean()
    ls = (-d.clip(upper=0)).ewm(alpha=a, adjust=False).mean()
    x["rsi"] = 100 - 100 / (1 + g / ls.replace(0, np.nan))

    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=a, adjust=False).mean()
    x["atr_ratio"] = x.atr / x.atr.rolling(100).median().replace(0, np.nan)

    x["bb_mid"] = c.rolling(20).mean()
    sd = c.rolling(20).std()
    x["bb_upper"], x["bb_lower"] = x.bb_mid + 2 * sd, x.bb_mid - 2 * sd

    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    x["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()

    lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
    x["stoch"] = 100 * (c - lo14) / (hi14 - lo14).replace(0, np.nan)

    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=x.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=x.index)
    atr_w = x.atr.replace(0, np.nan)
    pdi = 100 * pdm.ewm(alpha=a, adjust=False).mean() / atr_w
    mdi = 100 * mdm.ewm(alpha=a, adjust=False).mean() / atr_w
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    x["adx"] = dx.ewm(alpha=a, adjust=False).mean()

    rng = (h - l).replace(0, np.nan)
    x["body"] = c - o
    x["cl"] = (c - l) / rng
    x["upper_wick"] = h - np.maximum(o, c)
    x["lower_wick"] = np.minimum(o, c) - l
    x["pb_low"] = l.rolling(4).min()
    x["pb_high"] = h.rolling(4).max()

    x["trend"] = np.where((x.ema21 > x.ema50) & (c > x.ema21), 1,
                          np.where((x.ema21 < x.ema50) & (c < x.ema21), -1, 0))
    return x.replace([np.inf, -np.inf], np.nan)


@st.cache_data(ttl=60, show_spinner=False)
def htf_table(htf):
    iv, rg, mins = HTF[htf]
    h = fetch_yahoo(iv, rg)
    if h.empty or len(h) < 100:
        return None
    hx = add_indicators(h)
    hx["avail"] = (hx.time + pd.Timedelta(minutes=mins)).astype("datetime64[ns, UTC]")
    return hx[["avail", "trend"]].rename(columns={"trend": "htf"}).sort_values("avail")


def attach_htf(x, htf_df):
    x = x.sort_values("close_time")
    if htf_df is None:
        x["htf"] = 0
        return x.reset_index(drop=True), False
    x = pd.merge_asof(x, htf_df, left_on="close_time", right_on="avail", direction="backward")
    x["htf"] = x["htf"].fillna(0).astype(int)
    return x.drop(columns=["avail"]).reset_index(drop=True), True


# ============================================================
# SINGLE SIGNAL ENGINE (used by LIVE and BACKTEST)
# ============================================================
def score_frame(x):
    adx, atrr, c = x.adx, x.atr_ratio, x.close
    vol_ok = (atrr <= 2.0) & (atrr >= 0.35)

    tu = (adx >= 23) & (x.ema21 > x.ema50)
    td = (adx >= 23) & (x.ema21 < x.ema50)
    rg = adx <= 17

    up_checks = [c > x.ema21, x.ema9 > x.ema21, x.rsi.between(48, 68), x.macd_hist > 0,
                 x.stoch > 45, x.cl >= 0.60, adx >= 25, x.body > 0,
                 x.pb_low <= x.ema21 + 0.3 * x.atr]
    dn_checks = [c < x.ema21, x.ema9 < x.ema21, x.rsi.between(32, 52), x.macd_hist < 0,
                 x.stoch < 55, x.cl <= 0.40, adx >= 25, x.body < 0,
                 x.pb_high >= x.ema21 - 0.3 * x.atr]
    t_up = sum(k.astype(int) for k in up_checks)
    t_dn = sum(k.astype(int) for k in dn_checks)

    r_up_core = (c <= x.bb_lower) & (x.rsi <= 35) & (x.stoch <= 25)
    r_dn_core = (c >= x.bb_upper) & (x.rsi >= 65) & (x.stoch >= 75)
    r_up = (r_up_core * (2 + (x.lower_wick > x.upper_wick).astype(int)
                         + (x.cl >= 0.5).astype(int) + 1)).astype(int)
    r_dn = (r_dn_core * (2 + (x.upper_wick > x.lower_wick).astype(int)
                         + (x.cl <= 0.5).astype(int) + 1)).astype(int)

    trend_mode = tu | td
    x["up_base"] = np.where(vol_ok, np.where(tu, t_up, np.where(rg, r_up, 0)), 0)
    x["dn_base"] = np.where(vol_ok, np.where(td, t_dn, np.where(rg, r_dn, 0)), 0)
    x["setup"] = np.where(trend_mode, "TREND PULLBACK", np.where(rg, "RANGE REVERSAL", "NONE"))
    x["max_score"] = np.where(trend_mode, 10, 6)
    min_s = np.where(trend_mode, 8, 5)

    up = x.up_base + (x.htf == 1).astype(int)
    dn = x.dn_base + (x.htf == -1).astype(int)
    up_ok = (x.up_base > 0) & (up >= min_s) & (up > dn) & (x.htf != -1)
    dn_ok = (x.dn_base > 0) & (dn >= min_s) & (dn > up) & (x.htf != 1)
    x["side"] = np.where(up_ok, "UP", np.where(dn_ok, "DOWN", "NONE"))
    x["score"] = np.where(up_ok, up, np.where(dn_ok, dn, np.maximum(up, dn)))

    x["regime"] = np.select(
        [adx.isna(), atrr > 2.2, tu & (c > x.ema21), td & (c < x.ema21), adx >= 23, adx <= 17],
        ["UNKNOWN", "VOL SPIKE", "UPTREND", "DOWNTREND", "TRANSITION", "RANGE"], "SIDEWAYS")

    hr, wd = x.close_time.dt.hour, x.close_time.dt.weekday
    x["session_ok"] = (hr >= 7) & (hr < 20) & (wd < 5)
    return x


def explain(r):
    items, u = [], None
    if r.setup == "TREND PULLBACK":
        u = r.ema21 > r.ema50
        items = [
            ("Price vs EMA21", r.close > r.ema21 if u else r.close < r.ema21),
            ("EMA9 vs EMA21", r.ema9 > r.ema21 if u else r.ema9 < r.ema21),
            ("RSI zone", 48 <= r.rsi <= 68 if u else 32 <= r.rsi <= 52),
            ("MACD", r.macd_hist > 0 if u else r.macd_hist < 0),
            ("Stochastic", r.stoch > 45 if u else r.stoch < 55),
            ("Candle close", r.cl >= .6 if u else r.cl <= .4),
            ("ADX≥25", r.adx >= 25),
            ("Body", r.body > 0 if u else r.body < 0),
            ("Pullback to EMA21", r.pb_low <= r.ema21 + .3 * r.atr if u
             else r.pb_high >= r.ema21 - .3 * r.atr),
        ]
    elif r.setup == "RANGE REVERSAL":
        u = r.close < r.bb_mid
        items = [
            ("BB extreme", r.close <= r.bb_lower if u else r.close >= r.bb_upper),
            ("RSI extreme", r.rsi <= 35 if u else r.rsi >= 65),
            ("Stoch extreme", r.stoch <= 25 if u else r.stoch >= 75),
            ("Rejection wick", r.lower_wick > r.upper_wick if u else r.upper_wick > r.lower_wick),
            ("Recovery close", r.cl >= .5 if u else r.cl <= .5),
        ]
    if u is not None:
        items.append(("HTF aligned", r.htf != 0 and ((r.htf == 1) == u)))
    return items


# ============================================================
# BACKTEST + VALIDATION (same signals as live, non-overlapping)
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def run_backtest(d, horizon, cost_pips, use_session, step_min):
    mask = (d.side != "NONE")
    if use_session:
        mask &= d.session_ok
    idxs = np.flatnonzero(mask.values)
    o, c = d.open.values, d.close.values
    t = d.time.values
    side, setup, score = d.side.values, d.setup.values, d.score.values
    trades, busy = [], -1
    for i in idxs:
        if i < 200 or i < busy or i + horizon >= len(d):
            continue
        e, xx = i + 1, i + horizon
        gap = (t[xx] - t[i]) / np.timedelta64(1, "m")
        if gap > (horizon + 1) * step_min * 1.5:      # skip weekend / data gaps
            continue
        pips = ((c[xx] - o[e]) if side[i] == "UP" else (o[e] - c[xx])) / PIP
        res = "TIE" if pips == 0 else ("WIN" if pips > cost_pips else "LOSS")
        trades.append((t[i], side[i], setup[i], int(score[i]), res, pips))
        busy = xx
    return pd.DataFrame(trades, columns=["time", "side", "setup", "score", "result", "pips"])


def wilson_lower(w, n, z=1.96):
    if n <= 0:
        return 0.0
    p = w / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def stats_for(tr, payout):
    be = 1 / (1 + payout)
    if tr.empty:
        return dict(n=0, wins=0, losses=0, acc=0.0, ev=0.0, lower=0.0, be=be)
    w = int((tr.result == "WIN").sum())
    l = int((tr.result == "LOSS").sum())
    n = w + l
    acc = w / n if n else 0.0
    return dict(n=n, wins=w, losses=l, acc=acc, ev=acc * payout - (1 - acc) if n else 0.0,
                lower=wilson_lower(w, n), be=be)


def validate(trades, split_time, payout):
    train, test = trades[trades.time < split_time], trades[trades.time >= split_time]
    a, b = stats_for(train, payout), stats_for(test, payout)
    active = b["n"] >= 40 and b["acc"] > b["be"] and b["ev"] > 0
    return a, b, active, train, test


# ============================================================
# JOURNAL (auto log + auto settle)
# ============================================================
def settle(journal, df, tf, now):
    changed = False
    m = TF[tf]["minutes"]
    for r in journal:
        if r.get("status") != "PENDING" or r.get("timeframe") != tf:
            continue
        try:
            et = pd.Timestamp(r["entry_time"])
            xt = et + pd.Timedelta(minutes=m * (int(r["horizon"]) - 1))
            if xt + pd.Timedelta(minutes=m) > now:
                continue
            e, xr = df[df.time == et], df[df.time == xt]
            if e.empty or xr.empty:
                if now - xt > pd.Timedelta(minutes=m * 6):
                    r["status"], r["result"], r["pnl"] = "VOID", "VOID", 0.0
                    changed = True
                continue
            entry, ex = float(e.open.iloc[0]), float(xr.close.iloc[0])
            diff = (ex - entry) if r["side"] == "UP" else (entry - ex)
            res = "TIE" if diff == 0 else ("WIN" if diff > 0 else "LOSS")
            stake, pay = float(r["stake"]), float(r["payout"])
            r.update(status="SETTLED", entry=entry, exit=ex, result=res,
                     pnl=round(stake * pay if res == "WIN" else (-stake if res == "LOSS" else 0.0), 2))
            changed = True
        except Exception:
            continue
    return changed


def risk_guard(journal, exclude_id, daily_limit, max_losses, max_trades):
    today = utc_now().date().isoformat()
    rec = [r for r in journal if str(r.get("date", "")).startswith(today) and r.get("id") != exclude_id]
    pnl = sum(float(r.get("pnl", 0) or 0) for r in rec)
    streak = 0
    for r in reversed([r for r in rec if r.get("status") == "SETTLED"]):
        if r.get("result") == "LOSS":
            streak += 1
        else:
            break
    if pnl <= -abs(daily_limit):
        return False, "Daily loss limit hit", pnl, streak, len(rec)
    if streak >= max_losses:
        return False, "Consecutive loss stop", pnl, streak, len(rec)
    if len(rec) >= max_trades:
        return False, "Max signals/day reached", pnl, streak, len(rec)
    return True, "Risk OK", pnl, streak, len(rec)


# ============================================================
# LIVE CLOCK (auto refresh on every new candle)
# ============================================================
def clock_body(step, sig_close_ts, window, active):
    ts = utc_now().timestamp()
    rem = int(step - ts % step)
    mm, ss = divmod(rem, 60)
    if active:
        left = int(window - (ts - sig_close_ts))
        entry = f"🟢 Entry window: <b>{max(left, 0)}s</b>" if left > 0 else "⌛ Entry window over"
    else:
        entry = "⏸ No active signal"
    st.markdown(f'<div class="clock"><span>⏱ Next candle: <b>{mm:02d}:{ss:02d}</b></span>'
                f'<span>{entry}</span></div>', unsafe_allow_html=True)
    cur_b = int(ts // step)
    if ts % step >= 5 and st.session_state.get("fresh_b", cur_b) < cur_b:
        fetch_yahoo.clear()
        htf_table.clear()
        st.rerun()
    if active and window - (ts - sig_close_ts) <= 0 and not st.session_state.get("win_rerun") == sig_close_ts:
        st.session_state["win_rerun"] = sig_close_ts
        st.rerun()


try:
    clock = st.fragment(run_every=1)(clock_body)
except Exception:
    clock = clock_body

# ============================================================
# LAYOUT SKELETON
# ============================================================
hdr = st.empty()
tabs = st.tabs(["🎯 Signal", "📊 Validation", "📈 Chart", "📒 Journal", "⚙️ Settings"])

# ---------------- SETTINGS ----------------
with tabs[4]:
    s1, s2, s3 = st.columns(3)
    with s1:
        tf = st.selectbox("Timeframe", ["1m", "5m", "15m"], index=1)
        horizon = st.number_input("Expiry (candles)", 1, 5, 1)
        payout = st.slider("Payout", 0.70, 0.95, 0.85, 0.01)
    with s2:
        balance = st.number_input("Demo balance", 0.0, value=1000.0, step=100.0)
        stake_pct = st.slider("Max stake %", 0.1, 2.0, 0.5, 0.1)
        cost_pips = st.slider("Backtest cost (pips)", 0.0, 2.0, 0.3, 0.1)
    with s3:
        daily_limit = st.number_input("Daily loss limit", 0.0, value=20.0, step=5.0)
        max_losses = st.number_input("Max consecutive losses", 1, 5, 2)
        max_trades = st.number_input("Max signals/day", 1, 20, 6)
    k1, k2, k3 = st.columns(3)
    with k1:
        require_oos = st.checkbox("Require OOS validation", True)
    with k2:
        use_session = st.checkbox("Session filter (07-20 UTC, Mon-Fri)", True)
    with k3:
        news_blackout = st.checkbox("News blackout (manual)", False)
    if st.button("🔄 Refresh data now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown('<div class="note">Manual only • No auto trading • No OTC • No martingale • '
                'No profit guarantee. Feed (Yahoo) can differ from your broker.</div>',
                unsafe_allow_html=True)

# ============================================================
# DATA + ENGINE
# ============================================================
cfg = TF[tf]
step = cfg["minutes"] * 60
now = utc_now()
ts_now = now.timestamp()
cur_b = int(ts_now // step)
st.session_state["fresh_b"] = cur_b if ts_now % step >= 5 else cur_b - 1

df = fetch_yahoo(cfg["interval"], cfg["range"])
ok, qmsg, spacing = data_quality(df, tf)
if not ok:
    hdr.markdown('<div class="hdr"><span class="t">📈 EUR/USD SIGNAL PRO V9</span></div>',
                 unsafe_allow_html=True)
    with tabs[0]:
        st.error(f"❌ {qmsg}")
        st.caption("Tip: wait a few seconds and press Refresh in Settings.")
    st.stop()

x = add_indicators(df)
x["close_time"] = (x.time + pd.Timedelta(minutes=cfg["minutes"])).astype("datetime64[ns, UTC]")
x, htf_ok = attach_htf(x, htf_table(cfg["htf"]))
x = score_frame(x)

idx = closed_index(x, tf)
if idx is None:
    with tabs[0]:
        st.error("❌ No closed candle yet.")
    st.stop()
row = x.iloc[idx]
htf_txt = HTF_NAME[int(row.htf)] if htf_ok else "UNKNOWN"

# feed + window
candle_open = row.time.to_pydatetime()
sig_close = candle_open + dt.timedelta(minutes=cfg["minutes"])
age_min = (now - candle_open).total_seconds() / 60
feed_ok = age_min <= max(15, cfg["minutes"] * 4)
sig_age = (now - sig_close).total_seconds()
window = max(15, 0.2 * step)
in_window = 0 <= sig_age <= window
sig_id = f"{tf}-{sig_close.isoformat()}"

# journal settle + risk
journal = load_journal()
if settle(journal, df, tf, pd.Timestamp(now)):
    save_journal(journal)
risk_ok, risk_msg, today_pnl, streak, n_today = risk_guard(journal, sig_id, daily_limit, max_losses, max_trades)

# validation
trades = run_backtest(x[["time", "open", "close", "side", "setup", "score", "session_ok"]],
                      int(horizon), float(cost_pips), bool(use_session), cfg["minutes"])
split_t = x.time.iloc[int(len(x) * 0.7)]
vtrain, vtest, v_active, tr_train, tr_test = validate(trades, split_t, payout)

# gates
gate = []
if not feed_ok:
    gate.append(f"Stale feed ({age_min:.0f}m old)")
if row.side != "NONE" and not in_window:
    gate.append(f"Entry window passed ({int(max(sig_age, 0))}s old)")
if news_blackout:
    gate.append("News blackout ON")
if use_session and not row.session_ok:
    gate.append("Outside trading session")
if not risk_ok:
    gate.append(risk_msg)
if require_oos and not v_active:
    gate.append("OOS validation not passed")
final_side = row.side if (row.side != "NONE" and not gate) else "NO TRADE"
stake = balance * stake_pct / 100 if final_side in ("UP", "DOWN") else 0.0

# auto-log signal
if final_side in ("UP", "DOWN") and not any(r.get("id") == sig_id for r in journal):
    journal.append(dict(id=sig_id, date=now.date().isoformat(), time=now.isoformat(),
                        entry_time=sig_close.isoformat(), timeframe=tf, side=final_side,
                        setup=row.setup, score=int(row.score), htf=htf_txt, horizon=int(horizon),
                        stake=round(stake, 2), payout=payout, status="PENDING",
                        result="", pnl=0.0, version="V9"))
    save_journal(journal)

# ---------------- HEADER ----------------
oos_p = pill("OOS ✓", "ok") if v_active else pill("OOS ✗", "warn")
hdr.markdown(
    f'<div class="hdr"><span class="t">📈 EUR/USD SIGNAL PRO V9</span><span>'
    f'{pill(f"Feed {age_min:.0f}m", "ok" if feed_ok else "bad")}'
    f'{pill("Session", "ok" if row.session_ok else "warn")}'
    f'{pill("Risk", "ok" if risk_ok else "bad")}{oos_p}{pill(tf)}</span></div>',
    unsafe_allow_html=True)

# ============================================================
# TAB 1 — SIGNAL
# ============================================================
with tabs[0]:
    cls = {"UP": "up", "DOWN": "down"}.get(final_side, "wait")
    label = {"UP": "▲ UP", "DOWN": "▼ DOWN"}.get(final_side, "■ NO TRADE")
    if final_side in ("UP", "DOWN"):
        sub = (f"{row.setup} • Score {int(row.score)}/{int(row.max_score)} • "
               f"Expiry {int(horizon) * cfg['minutes']}m • Stake cap {stake:.2f}")
    elif gate and row.side != "NONE":
        sub = f"{row.side} setup blocked: " + " • ".join(gate)
    elif gate:
        sub = " • ".join(gate)
    else:
        sub = f"Waiting for a clean setup • best score {int(row.score)}/{int(row.max_score)}"
    st.markdown(f'<div class="sig {cls}"><div class="big">{label}</div><div class="sub">{sub}</div></div>',
                unsafe_allow_html=True)

    clock(step, sig_close.timestamp(), window, final_side in ("UP", "DOWN"))

    rc = "g" if row.regime == "UPTREND" else "r" if row.regime == "DOWNTREND" else "y"
    hc = "g" if htf_txt == "UP" else "r" if htf_txt == "DOWN" else "y"
    kpis([("Price", f"{row.close:.5f}", ""), ("RSI", f"{row.rsi:.1f}", ""), ("ADX", f"{row.adx:.1f}", ""),
          ("Regime", row.regime, rc), ("HTF " + cfg["htf"], htf_txt, hc),
          ("Today P/L", f"{today_pnl:+.2f}", "g" if today_pnl > 0 else "r" if today_pnl < 0 else "")])

    with st.expander("🔎 Why this signal? (checklist)"):
        items = explain(row)
        if items:
            st.write("  ·  ".join(f"{'✅' if ok_ else '❌'} {n}" for n, ok_ in items))
        else:
            st.write("No setup: market is sideways/transition or volatility filter active.")
        st.caption(f"Closed candle: {row.time:%Y-%m-%d %H:%M} UTC • EMA9 {row.ema9:.5f} • "
                   f"EMA21 {row.ema21:.5f} • EMA50 {row.ema50:.5f} • ATR {row.atr:.6f}")

# ============================================================
# TAB 2 — VALIDATION
# ============================================================
with tabs[1]:
    st.caption(f"Same engine as live • older 70% vs newer 30% (out-of-sample) • "
               f"non-overlapping trades • cost {cost_pips} pip • {len(x)} candles")
    a, b = st.columns(2)
    for col, name, s in ((a, "TRAIN (older 70%)", vtrain), (b, "TEST / OOS (newer 30%)", vtest)):
        with col:
            st.markdown(f"**{name}**")
            kpis([("Trades", s["n"], ""), ("Win %", f"{s['acc'] * 100:.1f}", ""),
                  ("EV/trade", f"{s['ev']:+.3f}", "g" if s["ev"] > 0 else "r")])
    st.write(f"Break-even @ {payout * 100:.0f}% payout: **{vtest['be'] * 100:.1f}%** • "
             f"OOS 95% lower bound: **{vtest['lower'] * 100:.1f}%**")
    if v_active:
        st.success("✅ OOS passes: ≥40 trades, win% above break-even, positive EV.")
    else:
        st.warning("⚠️ OOS not proven (needs ≥40 trades, win% > break-even, EV > 0). "
                   + ("Signals are BLOCKED." if require_oos else "Gate is OFF in Settings."))
    if not trades.empty:
        bd = (trades.assign(win=(trades.result == "WIN"), dec=(trades.result != "TIE"))
              .groupby(["setup", "side"])
              .agg(trades=("result", "size"), win_pct=("win", lambda s: round(s.mean() * 100, 1)),
                   avg_pips=("pips", lambda s: round(s.mean(), 2))).reset_index())
        st.markdown("**Per-setup breakdown (all data)**")
        st.dataframe(bd, use_container_width=True, hide_index=True)
        eq = trades.result.map({"WIN": payout, "LOSS": -1.0, "TIE": 0.0}).cumsum()
        st.line_chart(pd.DataFrame({"Equity (units of stake)": eq.values}), height=180)

# ============================================================
# TAB 3 — CHART
# ============================================================
with tabs[2]:
    tail = x.tail(120)
    try:
        import plotly.graph_objects as go
        lab = tail.time.dt.strftime("%d %H:%M")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=lab, open=tail.open, high=tail.high, low=tail.low,
                                     close=tail.close, name="Price",
                                     increasing_line_color="#17b26a", decreasing_line_color="#ef4444"))
        for col, colr in (("ema9", "#0066ff"), ("ema21", "#f59e0b"), ("ema50", "#7c3aed")):
            fig.add_trace(go.Scatter(x=lab, y=tail[col], mode="lines", name=col.upper(),
                                     line=dict(width=1.2, color=colr)))
        for sd, sym, colr, ycol in (("UP", "triangle-up", "#0b8f4d", "low"),
                                    ("DOWN", "triangle-down", "#d62a2a", "high")):
            m = tail.side == sd
            if m.any():
                off = -1 if sd == "UP" else 1
                fig.add_trace(go.Scatter(x=lab[m], y=tail.loc[m, ycol] + off * 3 * PIP, mode="markers",
                                         name=f"{sd} signal", marker=dict(symbol=sym, size=10, color=colr)))
        fig.update_layout(height=430, margin=dict(l=4, r=4, t=4, b=4), xaxis_rangeslider_visible=False,
                          xaxis=dict(type="category", nticks=8), legend=dict(orientation="h", y=1.04),
                          paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    except Exception:
        st.line_chart(tail.set_index("time")[["close", "ema9", "ema21", "ema50"]], height=400)
        st.caption("Install plotly for candlesticks: pip install plotly")

# ============================================================
# TAB 4 — JOURNAL
# ============================================================
with tabs[3]:
    settled = [r for r in journal if r.get("status") == "SETTLED"]
    w = sum(1 for r in settled if r["result"] == "WIN")
    l_ = sum(1 for r in settled if r["result"] == "LOSS")
    wr = f"{w / (w + l_) * 100:.1f}%" if (w + l_) else "—"
    kpis([("Today P/L", f"{today_pnl:+.2f}", "g" if today_pnl > 0 else "r" if today_pnl < 0 else ""),
          ("Loss streak", streak, "r" if streak else ""), ("Signals today", n_today + (1 if final_side in ("UP", "DOWN") else 0), ""),
          ("Settled", len(settled), ""), ("Win rate (paper)", wr, ""),
          ("Total P/L", f"{sum(float(r.get('pnl', 0) or 0) for r in settled):+.2f}", "")])
    if journal:
        jdf = pd.DataFrame(journal)
        cols = [c for c in ["time", "timeframe", "side", "setup", "score", "htf", "status",
                            "result", "pnl"] if c in jdf.columns]
        st.dataframe(jdf[cols].tail(25).iloc[::-1], use_container_width=True, hide_index=True, height=300)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download CSV", jdf.to_csv(index=False), "journal_v9.csv",
                               use_container_width=True)
        with d2:
            if st.checkbox("Confirm clear journal"):
                if st.button("🗑 Clear journal", use_container_width=True):
                    save_journal([])
                    st.rerun()
    else:
        st.info("No signals yet. Signals are auto-logged and auto-settled as paper trades.")
    st.caption("Results are computed automatically from candle data (paper trades). "
               "On Streamlit Cloud the file resets on restart — download the CSV regularly.")

st.markdown('<div class="note" style="text-align:center;margin-top:6px">EUR/USD Signal PRO V9 • '
            'Rule-based analysis tool • Manual use only • Demo first • No profit guarantee</div>',
            unsafe_allow_html=True)
