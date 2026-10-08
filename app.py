import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime as dt
import json
import os
import math

# ============================================================
# EUR/USD SIGNAL PRO V13.1
# 5m / 10m / 15m | Real EUR/USD source only | NO OTC
# Manual analysis only | Paper first | No martingale
# Closed candle + closed HTF | Gate modes | Shadow forward-test
# NOTE: No tool can guarantee profit or 100% accuracy.
# ============================================================

st.set_page_config(page_title="EUR/USD Signal PRO V13.1", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

SYMBOL = "EURUSD=X"
PIP = 0.0001
JOURNAL_FILE = "eurusd_v131_journal.json"
FORWARD_TARGET = 100

TF = {
    "5m": dict(minutes=5, htf=15),
    "10m": dict(minutes=10, htf=30),
    "15m": dict(minutes=15, htf=60),
}
BASE_INTERVAL, BASE_RANGE = "5m", "60d"
HTF_NAME = {1: "UP", -1: "DOWN", 0: "NEUTRAL"}


# ============================================================
# HELPERS
# ============================================================
def html(s):
    """Collapse whitespace so Markdown never turns HTML into a code block."""
    st.markdown(" ".join(s.split()), unsafe_allow_html=True)


html("""
<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.stApp {background:linear-gradient(180deg,#f3f8ff 0%,#fff 48%,#f7fbff 100%);}
.block-container {max-width:1180px; padding:.55rem .7rem 1rem;}
.hdr {display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:7px;
 background:linear-gradient(135deg,#034fc7,#087df5 55%,#00a7e8); color:#fff; padding:12px 15px;
 border-radius:16px; margin-bottom:9px; box-shadow:0 8px 25px rgba(0,91,190,.18);}
.hdr .t {font-weight:900; font-size:18px;}
.pill {display:inline-block; font-size:10.5px; font-weight:800; padding:4px 9px; border-radius:20px;
 margin-left:3px; background:rgba(255,255,255,.2); color:#fff;}
.pill.ok {background:#18b66c;} .pill.bad {background:#e93434;} .pill.warn {background:#ffd24a; color:#222;}
.sig {border-radius:18px; padding:17px 12px; text-align:center; border:2px solid; margin-bottom:9px;
 box-shadow:0 5px 18px rgba(0,0,0,.06);}
.sig.up {background:linear-gradient(135deg,#e5fff1,#fff); border-color:#16a765;}
.sig.down {background:linear-gradient(135deg,#fff0f0,#fff); border-color:#e23a3a;}
.sig.wait {background:linear-gradient(135deg,#fff9dd,#fff); border-color:#e3ad00;}
.sig .big {font-size:38px; font-weight:950; line-height:1.1;}
.sig.up .big {color:#07874a;} .sig.down .big {color:#cf2929;} .sig.wait .big {color:#956f00;}
.sig .sub {font-size:12px; font-weight:700; color:#425466; margin-top:5px; line-height:1.45;}
.kgrid {display:grid; gap:7px; margin-bottom:8px;}
.kpi {background:#fff; border:1px solid #dbeaff; border-radius:13px; padding:8px 9px;
 box-shadow:0 3px 12px rgba(30,90,150,.055);}
.kl {font-size:10px; color:#718096; font-weight:800; text-transform:uppercase;}
.kv {font-size:16px; font-weight:900; color:#0b3d78; margin-top:2px;}
.kv.g {color:#07874a;} .kv.r {color:#d32929;} .kv.y {color:#987000;}
.clock {background:#fff; border:1px solid #dcecff; border-radius:13px; padding:9px 12px; display:flex;
 flex-wrap:wrap; justify-content:space-between; gap:6px; font-weight:800; font-size:12.5px; margin-bottom:9px;}
.statusbox {background:#fff; border:1px solid #dcecff; border-radius:14px; padding:10px 12px; margin-bottom:8px;}
.status-title {font-size:11px; font-weight:900; color:#52708e; text-transform:uppercase; margin-bottom:4px;}
.status-main {font-size:14px; font-weight:850; color:#0b3b78;}
.note {color:#6b7b90; font-size:11px; line-height:1.45;}
.stButton > button, .stDownloadButton > button {border-radius:10px; font-weight:850;}
.stTabs [data-baseweb="tab-list"] {gap:3px;}
.stTabs [data-baseweb="tab"] {font-weight:800; padding:7px 10px;}
@media (max-width:640px){.block-container{padding:.4rem .45rem .8rem}.hdr .t{font-size:15px}
.sig .big{font-size:30px}.kv{font-size:14px}.pill{font-size:9px;padding:3px 7px}}
</style>
""")


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def pill(text, kind=""):
    return f'<span class="pill {kind}">{text}</span>'


def kpis(items, cols=3):
    cells = "".join(f'<div class="kpi"><div class="kl">{l}</div><div class="kv {c}">{v}</div></div>'
                    for l, v, c in items)
    html(f'<div class="kgrid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>')


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
            json.dump(data[-800:], f, indent=1, default=str)
        return True
    except Exception:
        return False


def market_open(t):
    """Real forex hours (UTC): Sun 21:00 -> Fri 21:00. Weekend = closed. No OTC."""
    wd, h = t.weekday(), t.hour
    if wd == 5 or (wd == 4 and h >= 21) or (wd == 6 and h < 21):
        return False
    return True


# ============================================================
# DATA (5m base; 10m/15m/HTF aggregated, only COMPLETE bins)
# ============================================================
@st.cache_data(ttl=10, show_spinner=False)
def fetch_base_yahoo():
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}"
           f"?interval={BASE_INTERVAL}&range={BASE_RANGE}")
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        ts = res.get("timestamp", [])
        if not ts:
            return pd.DataFrame()
        q = res["indicators"]["quote"][0]
        df = pd.DataFrame({
            "time": pd.to_datetime(ts, unit="s", utc=True).astype("datetime64[ns, UTC]"),
            "open": q.get("open"), "high": q.get("high"),
            "low": q.get("low"), "close": q.get("close"),
        })
        return df.dropna().sort_values("time").drop_duplicates("time").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def aggregate_ohlc(df, minutes):
    if df.empty:
        return pd.DataFrame()
    if minutes == 5:
        return df.copy().reset_index(drop=True)
    need = minutes // 5
    g = (df.set_index("time")
         .resample(f"{minutes}min", label="left", closed="left")
         .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
              close=("close", "last"), n=("close", "count")))
    g = g[g.n >= need].drop(columns="n").reset_index()      # drop incomplete bins
    g["time"] = g["time"].astype("datetime64[ns, UTC]")
    return g


@st.cache_data(ttl=10, show_spinner=False)
def get_timeframe_data(tf):
    return aggregate_ohlc(fetch_base_yahoo(), TF[tf]["minutes"])


def data_quality(df, tf):
    if df.empty:
        return False, "No market data (feed down or rate-limited)."
    if len(df) < 300:
        return False, f"Only {len(df)} candles available (need 300+)."
    exp = TF[tf]["minutes"]
    sp = df["time"].diff().dropna().dt.total_seconds() / 60
    normal = sp[sp <= exp * 4]
    if not normal.empty and abs(float(normal.median()) - exp) > max(1.0, exp * 0.35):
        return False, f"Timeframe mismatch: expected ~{exp}m, got ~{normal.median():.1f}m."
    bad = ((df.high < df.low) | (df.open > df.high) | (df.open < df.low) |
           (df.close > df.high) | (df.close < df.low))
    if bad.any():
        return False, "Invalid OHLC candle detected."
    return True, "OK"


def closed_index(df, tf):
    m = TF[tf]["minutes"]
    last_close = df["time"].iloc[-1].to_pydatetime() + dt.timedelta(minutes=m)
    if utc_now() >= last_close:
        return len(df) - 1
    return len(df) - 2 if len(df) >= 2 else None


# ============================================================
# INDICATORS (Wilder RSI / ATR / ADX)
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


@st.cache_data(ttl=30, show_spinner=False)
def htf_table(tf):
    mins = TF[tf]["htf"]
    h = aggregate_ohlc(fetch_base_yahoo(), mins)
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
    m = pd.merge_asof(x, htf_df, left_on="close_time", right_on="avail", direction="backward")
    m["htf"] = m["htf"].fillna(0).astype(int)
    return m.drop(columns=["avail"]).reset_index(drop=True), True


# ============================================================
# SINGLE SIGNAL ENGINE (LIVE + BACKTEST)
# ============================================================
def score_frame(x):
    adx, atrr, c = x.adx, x.atr_ratio, x.close
    vol_ok = (atrr >= 0.35) & (atrr <= 2.0)
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
    r_up = (r_up_core * (3 + (x.lower_wick > x.upper_wick).astype(int)
                         + (x.cl >= 0.5).astype(int))).astype(int)
    r_dn = (r_dn_core * (3 + (x.upper_wick > x.lower_wick).astype(int)
                         + (x.cl <= 0.5).astype(int))).astype(int)

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
            ("ADX>=25", r.adx >= 25),
            ("Body", r.body > 0 if u else r.body < 0),
            ("Pullback EMA21", r.pb_low <= r.ema21 + .3 * r.atr if u
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
# BACKTEST + VALIDATION
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def run_backtest(d, horizon, cost_pips, use_session, step_min):
    mask = d.side != "NONE"
    if use_session:
        mask &= d.session_ok
    idxs = np.flatnonzero(mask.values)
    o, c, t = d.open.values, d.close.values, d.time.values
    side, setup, score = d.side.values, d.setup.values, d.score.values
    trades, busy = [], -1
    for i in idxs:
        if i < 200 or i < busy:
            continue
        e, xx = i + 1, i + horizon
        if xx >= len(d):
            continue
        gap = (t[xx] - t[i]) / np.timedelta64(1, "m")
        if gap > (horizon + 1) * step_min * 1.5:        # skip weekend / data gaps
            continue
        pips = ((c[xx] - o[e]) if side[i] == "UP" else (o[e] - c[xx])) / PIP
        res = "TIE" if pips == 0 else ("WIN" if pips > cost_pips else "LOSS")
        trades.append((t[i], side[i], setup[i], int(score[i]), res, float(pips)))
        busy = xx
    out = pd.DataFrame(trades, columns=["time", "side", "setup", "score", "result", "pips"])
    out["time"] = pd.to_datetime(out["time"], utc=True)
    return out


def wilson_lower(w, n, z=1.96):
    if n <= 0:
        return 0.0
    p = w / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def stats_from(w, l, payout):
    n = w + l
    acc = w / n if n else 0.0
    return dict(n=n, wins=w, losses=l, acc=acc, ev=(acc * payout - (1 - acc)) if n else 0.0,
                lower=wilson_lower(w, n), be=1 / (1 + payout))


def stats_for(tr, payout):
    if tr.empty:
        return stats_from(0, 0, payout)
    return stats_from(int((tr.result == "WIN").sum()), int((tr.result == "LOSS").sum()), payout)


def validate(trades, split_time, payout, min_oos, buffer, wilson_gate):
    train, test = trades[trades.time < split_time], trades[trades.time >= split_time]
    a, b = stats_for(train, payout), stats_for(test, payout)
    reasons = []
    if b["n"] < min_oos:
        reasons.append(f"OOS trades {b['n']} < {min_oos}")
    if b["acc"] < b["be"] + buffer:
        reasons.append("OOS win% below break-even + buffer")
    if b["ev"] <= 0:
        reasons.append("OOS EV <= 0")
    if wilson_gate and b["lower"] < b["be"]:
        reasons.append("Wilson lower bound < break-even")
    return a, b, len(reasons) == 0, reasons


# ============================================================
# JOURNAL: settle, risk guard, forward stats
# ============================================================
def settle(journal, df, tf, now):
    changed = False
    m = TF[tf]["minutes"]
    for r in journal:
        if r.get("status") != "PENDING" or r.get("timeframe") != tf:
            continue
        try:
            et = pd.Timestamp(r["entry_time"])
            expiry = et + pd.Timedelta(minutes=m * int(r["horizon"]))
            if expiry > now:
                continue
            e = df[df.time == et]
            xr = df[df.time == expiry - pd.Timedelta(minutes=m)]
            if e.empty or xr.empty:
                if now - expiry > pd.Timedelta(minutes=m * 6):
                    r.update(status="VOID", result="VOID", pnl=0.0)
                    changed = True
                continue
            entry, ex = float(e.open.iloc[0]), float(xr.close.iloc[0])
            diff = (ex - entry) if r["side"] == "UP" else (entry - ex)
            res = "TIE" if diff == 0 else ("WIN" if diff > 0 else "LOSS")
            stake, pay = float(r["stake"]), float(r["payout"])
            r.update(status="SETTLED", entry=entry, exit=ex, result=res,
                     pnl=round(stake * pay if res == "WIN" else (-stake if res == "LOSS" else 0.0), 2),
                     expiry_time=expiry.isoformat())
            changed = True
        except Exception:
            continue
    return changed


def risk_guard(journal, exclude_id, daily_limit, max_losses, max_trades, cooldown_min, lock_amount):
    today = utc_now().date().isoformat()
    rec = [r for r in journal if str(r.get("date", "")).startswith(today)
           and r.get("id") != exclude_id and r.get("mode", "ACTIVE") == "ACTIVE"]
    settled = [r for r in rec if r.get("status") == "SETTLED"]
    pnl = sum(float(r.get("pnl", 0) or 0) for r in rec)
    streak = 0
    for r in reversed(settled):
        if r.get("result") == "LOSS":
            streak += 1
        else:
            break
    if pnl <= -abs(daily_limit):
        return False, "Daily loss limit reached", pnl, streak, len(rec)
    if lock_amount > 0 and pnl >= lock_amount:
        return False, "Profit lock reached", pnl, streak, len(rec)
    if streak >= max_losses:
        return False, "Consecutive-loss protection", pnl, streak, len(rec)
    if len(rec) >= max_trades:
        return False, "Max signals/day reached", pnl, streak, len(rec)
    if settled and settled[-1].get("result") == "LOSS":
        try:
            until = pd.Timestamp(settled[-1]["expiry_time"]) + pd.Timedelta(minutes=cooldown_min)
            if pd.Timestamp(utc_now()) < until:
                return False, f"Loss cooldown until {until:%H:%M} UTC", pnl, streak, len(rec)
        except Exception:
            pass
    return True, "Risk OK", pnl, streak, len(rec)


def forward_stats(journal, mode, payout):
    rec = [r for r in journal if r.get("status") == "SETTLED"
           and r.get("mode", "ACTIVE") == mode and r.get("result") in ("WIN", "LOSS")]
    w = sum(1 for r in rec if r["result"] == "WIN")
    return stats_from(w, len(rec) - w, payout)


# ============================================================
# LIVE CLOCK (refresh on new candle + when entry window ends)
# ============================================================
def clock_body(step, sig_close_ts, window, active):
    ts = utc_now().timestamp()
    mm, ss = divmod(int(step - ts % step), 60)
    if active:
        left = int(window - (ts - sig_close_ts))
        entry = f"🟢 Entry window: <b>{max(left, 0)}s</b>" if left > 0 else "⌛ Entry window over"
    else:
        entry = "⏸ No active signal"
    html(f'<div class="clock"><span>⏱ Next candle: <b>{mm:02d}:{ss:02d}</b></span><span>{entry}</span></div>')
    cur_b = int(ts // step)
    if ts % step >= 5 and st.session_state.get("fresh_b", cur_b) < cur_b:
        fetch_base_yahoo.clear()
        get_timeframe_data.clear()
        htf_table.clear()
        st.rerun()
    if active and window - (ts - sig_close_ts) <= 0 and st.session_state.get("win_rerun") != sig_close_ts:
        st.session_state["win_rerun"] = sig_close_ts
        st.rerun()


try:
    clock = st.fragment(run_every=1)(clock_body)
except Exception:
    clock = clock_body

# ============================================================
# LAYOUT + SETTINGS
# ============================================================
hdr = st.empty()
tabs = st.tabs(["🎯 SIGNAL", "📊 VALIDATION", "📈 CHART", "📒 JOURNAL", "⚙️ SETTINGS"])

with tabs[4]:
    c1, c2, c3 = st.columns(3)
    with c1:
        tf = st.selectbox("Timeframe", list(TF.keys()), index=0)
        horizon = st.number_input("Expiry (candles)", 1, 5, 1)
        payout = st.slider("Payout", 0.70, 0.95, 0.80, 0.01)
        entry_window = st.slider("Entry window (sec)", 10, 60, 20, 5)
    with c2:
        balance = st.number_input("Paper balance", 0.0, value=1000.0, step=100.0)
        stake_pct = st.slider("Max stake %", 0.1, 2.0, 0.5, 0.1)
        cost_pips = st.slider("Backtest cost (pips)", 0.0, 2.0, 0.3, 0.1)
        gate_mode = st.selectbox("Validation gate", ["Standard", "Strict", "Off (paper-learning)"],
                                 help="Standard: OOS win%>break-even+buffer, EV>0. "
                                      "Strict: + Wilson bound & 100+ trades. Off: no OOS gate.")
    with c3:
        daily_limit = st.number_input("Daily loss limit", 0.0, value=20.0, step=5.0)
        max_losses = st.number_input("Max consecutive losses", 1, 5, 2)
        max_trades = st.number_input("Max signals/day", 1, 20, 5)
        cooldown_min = st.slider("Loss cooldown (min)", 0, 60, 15, 5)
    q1, q2, q3 = st.columns(3)
    with q1:
        min_oos = st.slider("Min OOS trades (Standard)", 20, 200, 40, 10)
    with q2:
        edge_buffer = st.slider("OOS edge buffer", 0.0, 0.05, 0.01, 0.005)
        lock_units = st.slider("Profit lock (x stake)", 0.0, 5.0, 2.0, 0.5)
    with q3:
        use_session = st.checkbox("Core session filter (07-20 UTC)", True)
        news_blackout = st.checkbox("Manual news blackout", False)
    if st.button("🔄 REFRESH MARKET DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    html('<div class="note">EUR/USD live source only • 5m base feed, 10m/15m aggregated from complete 5m bars • '
         'Yahoo candles can differ from broker/Quotex • No OTC • No auto trading • No martingale • '
         'No guaranteed profit. Signals are only logged/settled while this app is open.</div>')

# ============================================================
# ENGINE
# ============================================================
cfg = TF[tf]
minutes = cfg["minutes"]
step = minutes * 60
now = utc_now()
ts_now = now.timestamp()
cur_b = int(ts_now // step)
st.session_state["fresh_b"] = cur_b if ts_now % step >= 5 else cur_b - 1
mkt_open = market_open(now)

df = get_timeframe_data(tf)
ok, qmsg = data_quality(df, tf)
if not ok:
    hdr_pills = pill("LIVE SOURCE", "ok") + pill("MARKET OPEN" if mkt_open else "MARKET CLOSED",
                                                   "ok" if mkt_open else "bad") + pill(tf)
    hdr.markdown(f'<div class="hdr"><span class="t">📈 EUR/USD SIGNAL PRO V13.1</span><span>{hdr_pills}</span></div>',
                 unsafe_allow_html=True)
    with tabs[0]:
        st.error(f"❌ {qmsg}")
        st.info("Settings → Refresh Market Data")
    st.stop()

x = add_indicators(df)
x["close_time"] = (x.time + pd.Timedelta(minutes=minutes)).astype("datetime64[ns, UTC]")
x, htf_ok = attach_htf(x, htf_table(tf))
x = score_frame(x)

idx = closed_index(x, tf)
if idx is None:
    with tabs[0]:
        st.error("❌ No closed candle yet.")
    st.stop()
row = x.iloc[idx]
htf_text = HTF_NAME.get(int(row.htf), "UNKNOWN") if htf_ok else "UNKNOWN"

candle_open = row.time.to_pydatetime()
candle_close = candle_open + dt.timedelta(minutes=minutes)
feed_age = (now - candle_open).total_seconds() / 60
feed_ok = feed_age <= max(15, minutes * 3)
sig_age = (now - candle_close).total_seconds()
in_window = 0 <= sig_age <= entry_window
signal_id = f"{tf}-{candle_close.isoformat()}"
stake_base = balance * stake_pct / 100

journal = load_journal()
if settle(journal, df, tf, pd.Timestamp(now)):
    save_journal(journal)

risk_ok, risk_msg, today_pnl, streak, n_today = risk_guard(
    journal, signal_id, daily_limit, max_losses, max_trades, cooldown_min, lock_units * stake_base)

trades = run_backtest(x[["time", "open", "close", "side", "setup", "score", "session_ok"]],
                      int(horizon), float(cost_pips), bool(use_session), minutes)
split_t = pd.Timestamp(x.time.iloc[int(len(x) * 0.7)])
split_t = split_t.tz_localize("UTC") if split_t.tzinfo is None else split_t.tz_convert("UTC")

strict = gate_mode == "Strict"
v_train, v_test, v_pass, v_reasons = validate(
    trades, split_t, payout, max(int(min_oos), 100) if strict else int(min_oos),
    float(edge_buffer), strict)
gate_off = gate_mode.startswith("Off")

# HARD gates: signal is not even a valid candidate
hard = []
if not mkt_open:
    hard.append("Forex market closed")
if not feed_ok:
    hard.append(f"Feed stale ({feed_age:.0f}m)")
if row.side != "NONE" and not in_window:
    hard.append("Entry window passed")
if news_blackout:
    hard.append("News blackout ON")
if use_session and not row.session_ok:
    hard.append("Outside core session")

# SOFT gates: valid candidate, but not allowed as ACTIVE (logged as SHADOW)
soft = []
if not risk_ok:
    soft.append(risk_msg)
if not gate_off and not v_pass:
    soft.append("OOS validation not passed")

existing = next((r for r in journal if r.get("id") == signal_id), None)
mode = None
if row.side in ("UP", "DOWN") and not hard:
    mode = existing.get("mode", "ACTIVE") if existing else ("SHADOW" if soft else "ACTIVE")

final_side = row.side if mode == "ACTIVE" else "NO TRADE"
stake = stake_base if final_side in ("UP", "DOWN") else 0.0

if mode and not existing:
    journal.append(dict(
        id=signal_id, date=now.date().isoformat(), time=now.isoformat(),
        entry_time=candle_close.isoformat(),
        expiry_time=(candle_close + dt.timedelta(minutes=minutes * int(horizon))).isoformat(),
        timeframe=tf, side=row.side, setup=row.setup, score=int(row.score),
        max_score=int(row.max_score), htf=htf_text, horizon=int(horizon),
        stake=round(stake_base, 2), payout=payout, mode=mode, status="PENDING",
        result="", pnl=0.0, version="V13.1"))
    save_journal(journal)

fa = forward_stats(journal, "ACTIVE", payout)
fs = forward_stats(journal, "SHADOW", payout)

# ============================================================
# HEADER
# ============================================================
fwd_n = fa["n"] + fs["n"]
hdr_pills = (pill("LIVE SOURCE", "ok")
             + pill("MARKET OPEN" if mkt_open else "MARKET CLOSED", "ok" if mkt_open else "bad")
             + (pill(f"FEED {feed_age:.0f}m", "ok") if feed_ok else pill("STALE FEED", "bad"))
             + (pill("RISK OK", "ok") if risk_ok else pill("RISK STOP", "bad"))
             + (pill("OOS ✓", "ok") if v_pass else pill("OOS ✗", "warn"))
             + pill(f"FWD {fwd_n}/{FORWARD_TARGET}", "warn" if fwd_n < FORWARD_TARGET else "ok")
             + pill(tf))
hdr.markdown(f'<div class="hdr"><span class="t">📈 EUR/USD SIGNAL PRO V13.1</span><span>{hdr_pills}</span></div>',
             unsafe_allow_html=True)

# ============================================================
# TAB 1 - SIGNAL
# ============================================================
with tabs[0]:
    cls = {"UP": "up", "DOWN": "down"}.get(final_side, "wait")
    label = {"UP": "▲ UP", "DOWN": "▼ DOWN"}.get(final_side, "■ NO TRADE")
    if final_side in ("UP", "DOWN"):
        sub = (f"{row.setup} • Score {int(row.score)}/{int(row.max_score)} • "
               f"Expiry {int(horizon) * minutes}m • Paper stake {stake:.2f}")
    elif mode == "SHADOW":
        sub = f"{row.side} setup BLOCKED: " + " • ".join(soft) + " • logged as shadow paper signal"
    elif hard and row.side != "NONE":
        sub = f"{row.side} setup blocked: " + " • ".join(hard)
    elif hard:
        sub = " • ".join(hard)
    else:
        sub = f"Waiting for a clean setup • best score {int(row.score)}/{int(row.max_score)}"
    html(f'<div class="sig {cls}"><div class="big">{label}</div><div class="sub">{sub}</div></div>')

    clock(step, candle_close.timestamp(), entry_window, final_side in ("UP", "DOWN"))

    rc = "g" if row.regime == "UPTREND" else "r" if row.regime == "DOWNTREND" else "y"
    hc = "g" if htf_text == "UP" else "r" if htf_text == "DOWN" else "y"
    pc_ = "g" if today_pnl > 0 else "r" if today_pnl < 0 else ""
    kpis([("Price", f"{row.close:.5f}", ""), ("RSI", f"{row.rsi:.1f}", ""), ("ADX", f"{row.adx:.1f}", ""),
          ("Regime", row.regime, rc), (f"HTF {cfg['htf']}m", htf_text, hc),
          ("Today P/L", f"{today_pnl:+.2f}", pc_)])

    html(f'<div class="statusbox"><div class="status-title">Market condition</div><div class="status-main">'
         f'{row.regime} • HTF {htf_text} • Volatility {row.atr_ratio:.2f}x</div></div>')

    with st.expander("🔎 WHY THIS SIGNAL?"):
        items = explain(row)
        if items:
            st.write("  ·  ".join(f"{'✅' if p else '❌'} {n}" for n, p in items))
        else:
            st.write("No valid setup: sideways/transition market or volatility filter active.")
        st.caption(f"Closed candle {row.time:%Y-%m-%d %H:%M} UTC • EMA9 {row.ema9:.5f} • "
                   f"EMA21 {row.ema21:.5f} • EMA50 {row.ema50:.5f} • ATR {row.atr:.6f}")
    html('<div class="note">Signal only after the candle closes. UP/DOWN is not a profit guarantee; '
         'NO TRADE is a valid result.</div>')

# ============================================================
# TAB 2 - VALIDATION
# ============================================================
with tabs[1]:
    st.caption(f"Older 70% = TRAIN • newer 30% = OOS TEST • {len(x)} candles • "
               f"{len(trades)} eligible historical trades • gate: {gate_mode}")
    a, b = st.columns(2)
    for col, name, s in ((a, "TRAIN (older 70%)", v_train), (b, "OOS TEST (newer 30%)", v_test)):
        with col:
            st.markdown(f"**{name}**")
            kpis([("Trades", s["n"], ""), ("Win %", f"{s['acc'] * 100:.1f}%", ""),
                  ("EV", f"{s['ev']:+.3f}", "g" if s["ev"] > 0 else "r")])
    st.write(f"Break-even @ {payout * 100:.0f}% payout: **{v_test['be'] * 100:.1f}%** • "
             f"OOS Wilson lower bound: **{v_test['lower'] * 100:.1f}%**")
    if gate_off:
        st.info("Gate is OFF: signals are not blocked by validation. Use only for paper-learning.")
    elif v_pass:
        st.success("✅ OOS gate passed (no guarantee for future trades).")
    else:
        st.warning("⚠️ OOS not proven: " + " | ".join(v_reasons))
    if not trades.empty:
        t2 = trades.assign(win=(trades.result == "WIN"))
        st.markdown("#### Setup performance")
        st.dataframe(t2.groupby(["setup", "side"]).agg(
            trades=("result", "size"), win_pct=("win", lambda s: round(s.mean() * 100, 1)),
            avg_pips=("pips", lambda s: round(s.mean(), 2))).reset_index(),
            use_container_width=True, hide_index=True)
        st.markdown("#### Score breakdown")
        st.dataframe(t2.groupby(["score", "side"]).agg(
            trades=("result", "size"), win_pct=("win", lambda s: round(s.mean() * 100, 1))).reset_index(),
            use_container_width=True, hide_index=True)
        eq = trades.result.map({"WIN": payout, "LOSS": -1.0, "TIE": 0.0}).cumsum()
        st.line_chart(pd.DataFrame({"Paper equity (stake units)": eq.values}), height=200)

# ============================================================
# TAB 3 - CHART
# ============================================================
with tabs[2]:
    tail = x.tail(120)
    try:
        import plotly.graph_objects as go
        lab = tail.time.dt.strftime("%d %H:%M")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=lab, open=tail.open, high=tail.high, low=tail.low, close=tail.close,
                                     name="EUR/USD", increasing_line_color="#16a765",
                                     decreasing_line_color="#e23a3a"))
        for col, colr in (("ema9", "#086cff"), ("ema21", "#f59e0b"), ("ema50", "#7c3aed")):
            fig.add_trace(go.Scatter(x=lab, y=tail[col], mode="lines", name=col.upper(),
                                     line=dict(width=1.3, color=colr)))
        for sd_, sym, colr, ycol, off in (("UP", "triangle-up", "#07874a", "low", -3),
                                          ("DOWN", "triangle-down", "#cf2929", "high", 3)):
            m = tail.side == sd_
            if m.any():
                fig.add_trace(go.Scatter(x=lab[m], y=tail.loc[m, ycol] + off * PIP, mode="markers",
                                         name=sd_, marker=dict(symbol=sym, size=10, color=colr)))
        fig.update_layout(height=460, margin=dict(l=5, r=5, t=10, b=5), xaxis_rangeslider_visible=False,
                          xaxis=dict(type="category", nticks=9), legend=dict(orientation="h", y=1.04),
                          paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    except Exception:
        st.line_chart(tail.set_index("time")[["close", "ema9", "ema21", "ema50"]], height=400)
        st.caption("Install plotly: pip install plotly")

# ============================================================
# TAB 4 - JOURNAL + FORWARD TEST
# ============================================================
with tabs[3]:
    st.markdown("#### 🧪 Forward test (real, live, out-of-sample)")
    comb_w, comb_l = fa["wins"] + fs["wins"], fa["losses"] + fs["losses"]
    comb = stats_from(comb_w, comb_l, payout)
    kpis([("ACTIVE settled", fa["n"], ""), ("ACTIVE win %", f"{fa['acc'] * 100:.1f}%" if fa["n"] else "—", ""),
          ("SHADOW settled", fs["n"], ""), ("SHADOW win %", f"{fs['acc'] * 100:.1f}%" if fs["n"] else "—", ""),
          ("Combined n", f"{comb['n']}/{FORWARD_TARGET}", ""),
          ("Wilson LB", f"{comb['lower'] * 100:.1f}%" if comb["n"] else "—",
           "g" if comb["n"] and comb["lower"] >= comb["be"] else "")], cols=3)
    if comb["n"] < FORWARD_TARGET:
        st.info(f"Need {FORWARD_TARGET - comb['n']} more settled signals before judging "
                f"(break-even {comb['be'] * 100:.1f}%). SHADOW = signals blocked by gates but tracked as paper.")
    elif comb["lower"] >= comb["be"]:
        st.success("Forward test supports a positive edge so far (still no guarantee).")
    else:
        st.warning("Forward test does NOT show a proven edge. Do not trade real money.")

    settled = [r for r in journal if r.get("status") == "SETTLED" and r.get("mode", "ACTIVE") == "ACTIVE"]
    total_pnl = sum(float(r.get("pnl", 0) or 0) for r in settled)
    kpis([("Today P/L (active)", f"{today_pnl:+.2f}", "g" if today_pnl > 0 else "r" if today_pnl < 0 else ""),
          ("Loss streak", streak, "r" if streak else ""),
          ("Active today", n_today + (1 if final_side in ("UP", "DOWN") else 0), ""),
          ("Total P/L (active)", f"{total_pnl:+.2f}", "g" if total_pnl > 0 else "r" if total_pnl < 0 else "")],
         cols=4)
    if journal:
        jdf = pd.DataFrame(journal)
        cols = [c for c in ["time", "timeframe", "mode", "side", "setup", "score", "htf",
                            "status", "result", "pnl"] if c in jdf.columns]
        st.dataframe(jdf[cols].tail(40).iloc[::-1], use_container_width=True, hide_index=True, height=330)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ DOWNLOAD CSV", jdf.to_csv(index=False), "eurusd_v131_journal.csv",
                               use_container_width=True)
        with d2:
            if st.checkbox("Confirm clear journal"):
                if st.button("🗑 CLEAR JOURNAL", use_container_width=True):
                    save_journal([])
                    st.rerun()
    else:
        st.info("No paper signals yet.")
    html('<div class="note">On Streamlit Cloud the journal file resets on restart - download the CSV regularly. '
         'Judge the system by 100+ settled forward signals, EV and drawdown, not by backtest alone.</div>')

html('<div class="note" style="text-align:center;margin-top:8px">EUR/USD SIGNAL PRO V13.1 • 5m/10m/15m • '
     'Live-source analysis • Manual only • Paper first • No OTC • No auto trading • No martingale • '
     'No profit guarantee</div>')
