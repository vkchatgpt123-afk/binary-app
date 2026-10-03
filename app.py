import math
from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="EUR/USD Signal Pro",
    page_icon="📊",
    layout="centered",
)

PIP = 0.0001
SYMBOL = "EURUSD=X"
# interval -> (yahoo range, minutes per candle)
INTERVALS = {"1m": ("7d", 1), "5m": ("60d", 5), "15m": ("60d", 15)}
TIMEZONES = ["Asia/Kolkata", "UTC", "Asia/Dubai", "Europe/London", "America/New_York"]


# ============================================================
# STATISTICS
# ============================================================

def wilson(wins, n, z=1.96):
    """95% Wilson confidence interval for a win rate."""
    if n <= 0:
        return np.nan, np.nan
    p = wins / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0)) / den
    return center - half, center + half


def p_value_vs_breakeven(wins, n, breakeven):
    """One-sided p-value: is the win rate really above break-even?"""
    if n <= 0:
        return np.nan
    z = (wins / n - breakeven) / math.sqrt(breakeven * (1 - breakeven) / n)
    return 0.5 * math.erfc(z / math.sqrt(2))


def max_loss_streak(results):
    best = cur = 0
    for r in results:
        if r == "LOSS":
            cur += 1
            best = max(best, cur)
        elif r == "WIN":
            cur = 0
    return best


# ============================================================
# LIVE DATA (with retry + validation)
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def fetch_candles(interval):
    rng = INTERVALS[interval][0]
    last_err = None
    for host in ("query1", "query2"):
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{SYMBOL}"
        try:
            r = requests.get(
                url,
                params={"range": rng, "interval": interval, "includePrePost": "false"},
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            ts = res.get("timestamp") or []
            df = pd.DataFrame({
                "time": pd.to_datetime(ts, unit="s", utc=True),
                "open": q["open"], "high": q["high"],
                "low": q["low"], "close": q["close"],
            })
            df = (df.dropna().drop_duplicates("time")
                  .sort_values("time").reset_index(drop=True))
            if len(df) < 250:
                raise ValueError(f"Only {len(df)} candles received")
            return df
        except Exception as e:  # try next host
            last_err = e
    raise RuntimeError(f"Yahoo feed unavailable: {last_err}")


# ============================================================
# INDICATORS (Wilder smoothing = standard RSI / ATR / ADX)
# ============================================================

def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_indicators(df):
    x = df.copy()
    c, o, h, l = x["close"], x["open"], x["high"], x["low"]

    x["ema9"] = c.ewm(span=9, adjust=False).mean()
    x["ema21"] = c.ewm(span=21, adjust=False).mean()
    x["ema50"] = c.ewm(span=50, adjust=False).mean()

    delta = c.diff()
    gain = wilder(delta.clip(lower=0), 14)
    loss = wilder(-delta.clip(upper=0), 14)
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi[(loss == 0) & (gain > 0)] = 100.0
    x["rsi"] = rsi

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = wilder(tr, 14)
    x["atr_med"] = x["atr"].shift(1).rolling(100).median()

    # ADX: trend strength (separates trending from ranging markets)
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=x.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=x.index)
    plus_di = 100 * wilder(plus_dm, 14) / x["atr"]
    minus_di = 100 * wilder(minus_dm, 14) / x["atr"]
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    x["adx"] = wilder(dx, 14)

    mid = c.rolling(20).mean()
    sd = c.rolling(20).std(ddof=0)
    x["bb_mid"], x["bb_up"], x["bb_lo"] = mid, mid + 2 * sd, mid - 2 * sd

    rng = (h - l).replace(0, np.nan)
    x["body_atr"] = (c - o).abs() / x["atr"].replace(0, np.nan)
    x["close_loc"] = (c - l) / rng
    x["upper_wick"] = (h - np.maximum(o, c)) / rng
    x["lower_wick"] = (np.minimum(o, c) - l) / rng
    x["hour"] = x["time"].dt.hour
    return x


# ============================================================
# SIGNAL ENGINE (vectorised: identical logic for live + backtest)
#   A) Trend Pullback  - trade WITH the trend after a dip to EMA21
#   B) Range Reversal  - fade Bollinger extremes ONLY in ranging market
#   Transition zone (ADX between thresholds) = no trade.
# ============================================================

def compute_signals(x, p):
    c, o, h, l = x["close"], x["open"], x["high"], x["low"]
    ratio = x["atr"] / x["atr_med"]

    ok = (
        (x["hour"] >= p["h0"]) & (x["hour"] < p["h1"])
        & ratio.between(0.6, 2.0)
        & (x["body_atr"] <= 3.0)
        & x[["atr", "atr_med", "rsi", "adx", "bb_up", "ema50"]].notna().all(axis=1)
    )
    good_vol = ratio.between(0.8, 1.5)

    # --- A) trend pullback
    up_tr = (x["ema21"] > x["ema50"]) & (c > x["ema50"]) & (x["adx"] >= p["adx_trend"])
    dn_tr = (x["ema21"] < x["ema50"]) & (c < x["ema50"]) & (x["adx"] >= p["adx_trend"])
    a_up = (ok & up_tr & (l.rolling(3).min() <= x["ema21"]) & (c > x["ema21"])
            & (c > o) & (c > c.shift(1)) & (x["close_loc"] >= 0.6) & x["rsi"].between(40, 66))
    a_dn = (ok & dn_tr & (h.rolling(3).max() >= x["ema21"]) & (c < x["ema21"])
            & (c < o) & (c < c.shift(1)) & (x["close_loc"] <= 0.4) & x["rsi"].between(34, 60))
    conf_a_up = ((x["adx"] >= 30).astype(int) + (x["ema9"] > x["ema21"]).astype(int)
                 + x["rsi"].between(45, 60).astype(int) + good_vol.astype(int)
                 + (x["close_loc"] >= 0.75).astype(int))
    conf_a_dn = ((x["adx"] >= 30).astype(int) + (x["ema9"] < x["ema21"]).astype(int)
                 + x["rsi"].between(40, 55).astype(int) + good_vol.astype(int)
                 + (x["close_loc"] <= 0.25).astype(int))

    # --- B) range reversal (previous candle pierced band, current candle rejects it)
    ranging = x["adx"] < p["adx_range"]
    b_up = (ok & ranging & (c.shift(1) <= x["bb_lo"].shift(1)) & (x["rsi"].shift(1) <= 35)
            & (c > x["bb_lo"]) & (c > o) & (x["close_loc"] >= 0.55))
    b_dn = (ok & ranging & (c.shift(1) >= x["bb_up"].shift(1)) & (x["rsi"].shift(1) >= 65)
            & (c < x["bb_up"]) & (c < o) & (x["close_loc"] <= 0.45))
    conf_b_up = ((x["rsi"].shift(1) <= 30).astype(int) + (x["lower_wick"].shift(1) >= 0.4).astype(int)
                 + good_vol.astype(int) + (x["close_loc"] >= 0.75).astype(int)
                 + (x["adx"] < 15).astype(int))
    conf_b_dn = ((x["rsi"].shift(1) >= 70).astype(int) + (x["upper_wick"].shift(1) >= 0.4).astype(int)
                 + good_vol.astype(int) + (x["close_loc"] <= 0.25).astype(int)
                 + (x["adx"] < 15).astype(int))

    n = len(x)
    side = np.zeros(n, dtype=int)
    conf = np.zeros(n, dtype=int)
    setup = np.array([""] * n, dtype=object)
    for mask, s, name, cf in [
        (a_up, 1, "Trend Pullback", conf_a_up), (a_dn, -1, "Trend Pullback", conf_a_dn),
        (b_up, 1, "Range Reversal", conf_b_up), (b_dn, -1, "Range Reversal", conf_b_dn),
    ]:
        m = mask.fillna(False).to_numpy(dtype=bool) & (cf.to_numpy() >= p["min_conf"])
        side[m], conf[m], setup[m] = s, cf.to_numpy()[m], name
    return pd.DataFrame({"side": side, "conf": conf, "setup": setup}, index=x.index)


def regime_label(r, p):
    if pd.isna(r["adx"]):
        return "—"
    if r["adx"] >= p["adx_trend"]:
        return "UPTREND" if r["ema21"] > r["ema50"] else "DOWNTREND"
    if r["adx"] < p["adx_range"]:
        return "RANGING"
    return "TRANSITION"


def why_no_trade(r, p):
    if not (p["h0"] <= r["hour"] < p["h1"]):
        return "Outside chosen trading session (low liquidity / spreads)."
    if pd.isna(r["atr_med"]) or pd.isna(r["adx"]):
        return "Indicators still warming up."
    ratio = r["atr"] / r["atr_med"]
    if ratio < 0.6:
        return "Market too quiet (volatility far below normal)."
    if ratio > 2.0:
        return "Volatility spike (news-like conditions) - skipped."
    if r["body_atr"] > 3.0:
        return "Abnormal oversized candle - skipped."
    reg = regime_label(r, p)
    if reg == "TRANSITION":
        return f"Transition zone (ADX {r['adx']:.0f}) - neither a clean trend nor a clean range."
    if reg == "RANGING":
        return "Ranging market, but price is not rejecting a Bollinger extreme."
    return f"{reg.title()}, but no pullback-and-resume trigger yet."


def explain(r, setup, side, p):
    d = "UP" if side == 1 else "DOWN"
    if setup == "Trend Pullback":
        trend = "uptrend" if side == 1 else "downtrend"
        return (f"{trend} (ADX {r['adx']:.0f}); price dipped to EMA21 and resumed {d}; "
                f"RSI {r['rsi']:.0f} (not exhausted).")
    band = "lower" if side == 1 else "upper"
    return (f"Ranging market (ADX {r['adx']:.0f}); price pierced the {band} Bollinger band "
            f"and was rejected; RSI extreme on prior candle.")


# ============================================================
# BINARY-OPTIONS BACKTEST (win = +payout, loss = -1, tie = 0)
# ============================================================

def run_backtest(x, sig, horizon, one_at_a_time):
    n = len(x)
    o, c = x["open"].to_numpy(), x["close"].to_numpy()
    rows, busy_until = [], -1
    for i in np.flatnonzero(sig["side"].to_numpy() != 0):
        e, ex = i + 1, i + horizon
        if ex >= n:
            break
        if one_at_a_time and e <= busy_until:
            continue
        s = int(sig["side"].iat[i])
        move = round((c[ex] - o[e]) * s / PIP, 1)
        res = "WIN" if move > 0 else ("LOSS" if move < 0 else "TIE")
        rows.append({
            "signal_time": x["time"].iat[i], "entry_time": x["time"].iat[e],
            "side": "UP" if s == 1 else "DOWN", "setup": sig["setup"].iat[i],
            "conf": int(sig["conf"].iat[i]), "entry": o[e], "exit": c[ex],
            "pips": move, "result": res,
        })
        busy_until = ex
    return pd.DataFrame(rows)


def score_trades(tr, payout):
    """Adds pnl (in stake units) and returns summary stats."""
    if tr.empty:
        return None
    tr = tr.copy()
    tr["pnl"] = tr["result"].map({"WIN": payout, "LOSS": -1.0, "TIE": 0.0})
    wins = int((tr["result"] == "WIN").sum())
    losses = int((tr["result"] == "LOSS").sum())
    decided = wins + losses
    be = 1 / (1 + payout)
    wr = wins / decided if decided else np.nan
    lo, hi = wilson(wins, decided)
    equity = np.r_[0.0, tr["pnl"].cumsum().to_numpy()]
    max_dd = float((equity - np.maximum.accumulate(equity)).min())
    return {
        "tr": tr, "n": len(tr), "wins": wins, "losses": losses, "ties": len(tr) - decided,
        "decided": decided, "wr": wr, "lo": lo, "hi": hi, "be": be,
        "ev": float(tr["pnl"].mean()), "net": float(tr["pnl"].sum()),
        "dd": max_dd, "streak": max_loss_streak(tr["result"]),
        "pval": p_value_vs_breakeven(wins, decided, be), "equity": equity,
    }


def verdict(s):
    if s is None or s["decided"] < 30:
        return "gray", "Not enough trades", "Fewer than 30 decided trades - results are not reliable yet."
    if s["lo"] > s["be"]:
        return "green", "Statistically proven edge", "Even the pessimistic (95%) win-rate estimate beats break-even."
    if s["ev"] > 0:
        return "amber", "Positive, but unproven", "Profitable in the sample, but could still be luck."
    return "red", "No edge", "Win rate is below break-even - this setup loses money historically."


# ============================================================
# JOURNAL / RISK GUARD
# ============================================================

def guard_status(journal, today, max_consec, max_loss_units):
    t = [j for j in journal if j["date"] == today]
    pnl = sum(j["pnl"] for j in t)
    consec = 0
    for j in reversed(t):
        if j["result"] == "LOSS":
            consec += 1
        elif j["result"] == "WIN":
            break
    if consec >= max_consec:
        return True, f"{consec} losses in a row today", pnl
    if pnl <= -max_loss_units:
        return True, f"daily loss limit reached ({pnl:.1f} stakes)", pnl
    return False, "", pnl


# ============================================================
# CHART
# ============================================================

def candle_chart(x, tz, n=80):
    d = x.tail(n).copy()
    d["time"] = d["time"].dt.tz_convert(tz).dt.tz_localize(None)
    d["up"] = d["close"] >= d["open"]
    ysc = alt.Scale(zero=False)
    col = alt.condition("datum.up", alt.value("#16c784"), alt.value("#ea3943"))
    base = alt.Chart(d).encode(x=alt.X("time:T", title=None))
    wick = base.mark_rule().encode(y=alt.Y("low:Q", scale=ysc, title=None), y2="high:Q", color=col)
    body = base.mark_bar(size=5).encode(y=alt.Y("open:Q", scale=ysc), y2="close:Q", color=col)
    e21 = base.mark_line(color="#f5a623", strokeWidth=1.2).encode(y=alt.Y("ema21:Q", scale=ysc))
    e50 = base.mark_line(color="#4c8bf5", strokeWidth=1.2).encode(y=alt.Y("ema50:Q", scale=ysc))
    return (wick + body + e21 + e50).properties(height=280)


# ===== UI =====

CSS = """
<style>
.block-container{padding-top:1.4rem;max-width:760px}
.hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem}
.hdr h2{margin:0;font-size:1.35rem}
.pill{padding:.15rem .6rem;border-radius:999px;font-size:.72rem;font-weight:600;
      background:rgba(128,128,128,.18)}
.sig{border-radius:16px;padding:1.2rem 1rem;text-align:center;margin:.6rem 0 .8rem 0;
     border:1px solid rgba(128,128,128,.25)}
.sig .big{font-size:2.6rem;font-weight:800;line-height:1.1}
.sig .sub{opacity:.85;font-size:.9rem;margin-top:.3rem}
.sig .meta{opacity:.7;font-size:.78rem;margin-top:.6rem}
.up{background:rgba(22,199,132,.14);border-color:rgba(22,199,132,.5)}
.down{background:rgba(234,57,67,.14);border-color:rgba(234,57,67,.5)}
.wait{background:rgba(245,166,35,.12);border-color:rgba(245,166,35,.45)}
.stop{background:rgba(128,128,128,.14)}
.vd{border-radius:12px;padding:.7rem .9rem;margin:.3rem 0 .8rem 0;border:1px solid rgba(128,128,128,.25)}
.vd.green{background:rgba(22,199,132,.14)} .vd.amber{background:rgba(245,166,35,.14)}
.vd.red{background:rgba(234,57,67,.14)} .vd.gray{background:rgba(128,128,128,.12)}
.vd b{font-size:1rem}
[data-testid="stMetric"]{background:rgba(128,128,128,.08);border-radius:12px;padding:.5rem .7rem}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.session_state.setdefault("journal", [])

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")
    interval = st.selectbox("Candle size", list(INTERVALS), index=1)
    mins = INTERVALS[interval][1]
    horizon = st.selectbox("Expiry (candles)", [1, 2, 3], index=0,
                           help="Quotex expiry = candles x candle size")
    st.caption(f"Expiry on Quotex: **{horizon * mins} min**")
    payout_pct = st.slider("Broker payout %", 70, 95, 85,
                           help="Check the % shown next to EUR/USD in Quotex")
    payout = payout_pct / 100
    st.caption(f"Break-even win rate: **{100 / (1 + payout):.1f}%**")
    tz = st.selectbox("Your timezone", TIMEZONES, index=0)

    st.subheader("Filters")
    h0, h1 = st.slider("Trading session (UTC hours)", 0, 24, (7, 20),
                       help="07-20 UTC = London + New York. Asian night is low quality.")
    min_conf = st.slider("Minimum confluence (0-5)", 0, 5, 2)
    require_valid = st.checkbox("Only signal validated setups", value=True,
                                help="Blocks a setup unless it has been profitable in the backtest.")
    one_at_a_time = st.checkbox("One trade at a time", value=True)
    with st.expander("Advanced"):
        adx_trend = st.slider("ADX = trending above", 15, 35, 22)
        adx_range = st.slider("ADX = ranging below", 10, 25, 20)

    st.subheader("Risk guard")
    balance = st.number_input("Balance", min_value=0.0, value=100.0, step=10.0)
    stake_pct = st.slider("Stake % of balance", 0.5, 5.0, 1.0, 0.5)
    max_consec = st.slider("Stop after N losses in a row", 1, 5, 2)
    max_loss_units = st.slider("Daily loss limit (stakes)", 1, 10, 3)
    st.caption(f"Suggested stake: **{balance * stake_pct / 100:.2f}**")

params = {"h0": h0, "h1": h1, "min_conf": min_conf, "adx_trend": adx_trend, "adx_range": adx_range}

# ---------------- header ----------------
st.markdown(
    "<div class='hdr'><h2>📊 EUR/USD Signal Pro</h2>"
    "<span class='pill'>MANUAL • CLOSED CANDLES ONLY</span></div>",
    unsafe_allow_html=True,
)
if st.button("🔄 Refresh live data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ---------------- data ----------------
try:
    raw = fetch_candles(interval)
except Exception as err:
    st.error("Live data error")
    st.code(str(err))
    st.info("Feed unavailable. Do not trade without data. Refresh in a moment.")
    st.stop()

x = add_indicators(raw)
sig = compute_signals(x, params)
bt = run_backtest(x, sig, horizon, one_at_a_time)
overall = score_trades(bt, payout)

by_setup = {}
if overall is not None:
    for name, g in overall["tr"].groupby("setup"):
        by_setup[name] = score_trades(g.reset_index(drop=True), payout)
validated = {k: (v["decided"] >= 20 and v["ev"] > 0) for k, v in by_setup.items()}

now = pd.Timestamp.now(tz="UTC")
delta = pd.Timedelta(minutes=mins)
last_bar = x["time"].iloc[-1]
idx = len(x) - 1 if now >= last_bar + delta else len(x) - 2
row = x.iloc[idx]
entry_time = row["time"] + delta
age_s = (now - entry_time).total_seconds()
feed_stale = (now - last_bar) > max(pd.Timedelta(minutes=15), 3 * delta)
window_s = max(20, int(mins * 60 * 0.3))
regime = regime_label(row, params)
fmt = lambda t: t.tz_convert(tz).strftime("%d %b %H:%M")

tab_sig, tab_bt, tab_j, tab_guide = st.tabs(["📡 Signal", "📈 Backtest", "📒 Journal", "ℹ️ Guide"])

# ================= SIGNAL TAB =================
with tab_sig:
    c1, c2, c3 = st.columns(3)
    c1.metric("Price", f"{row['close']:.5f}")
    c2.metric("Regime", regime.title())
    c3.metric("ATR", f"{row['atr'] / PIP:.1f} pips" if pd.notna(row["atr"]) else "—")

    today = now.tz_convert(tz).strftime("%Y-%m-%d")
    stopped, stop_msg, today_pnl = guard_status(st.session_state["journal"], today, max_consec, max_loss_units)

    side = int(sig["side"].iloc[idx])
    setup = sig["setup"].iloc[idx]
    conf = int(sig["conf"].iloc[idx])

    if feed_stale:
        card, big, sub = "stop", "⛔ NO DATA", "Feed is stale or the market is closed. Do not trade."
        meta = f"Last candle: {fmt(last_bar)}"
    elif stopped:
        card, big, sub = "stop", "🛑 STOP TODAY", f"Risk guard: {stop_msg}. Come back tomorrow."
        meta = "Protecting your balance is part of the strategy."
    elif side != 0 and age_s > window_s:
        card, big = "wait", "⌛ EXPIRED"
        sub = f"Signal is {int(age_s)}s old. Entering late ruins the edge - wait for the next one."
        meta = f"Setup was: {setup} ({'UP' if side == 1 else 'DOWN'})"
    elif side != 0 and require_valid and not validated.get(setup, False):
        card, big = "wait", "🟡 NO TRADE"
        sub = f"{setup} fired, but this setup has not proven profitable in the backtest. Skipped."
        meta = "Untick 'Only signal validated setups' to override (not recommended)."
    elif side != 0:
        up = side == 1
        card, big = ("up", "🟢 UP") if up else ("down", "🔴 DOWN")
        sub = explain(row, setup, side, params)
        meta = (f"{setup} • confluence {conf}/5 • enter at {fmt(entry_time)} • "
                f"expiry {horizon * mins} min • valid for {window_s}s")
    else:
        card, big, sub = "wait", "🟡 NO TRADE", why_no_trade(row, params)
        meta = f"Analysed candle closed {fmt(entry_time)}"

    st.markdown(
        f"<div class='sig {card}'><div class='big'>{big}</div>"
        f"<div class='sub'>{sub}</div><div class='meta'>{meta}</div></div>",
        unsafe_allow_html=True,
    )

    if side != 0 and card in ("up", "down"):
        s = by_setup.get(setup)
        if s:
            st.caption(
                f"Historical record of **{setup}**: {s['wr'] * 100:.1f}% win rate over "
                f"{s['decided']} trades (break-even {s['be'] * 100:.1f}%)."
            )

    st.markdown("**Safety checks**")
    checks = [
        ("Fresh data", not feed_stale),
        ("Closed candle only", True),
        ("Inside trading session", h0 <= row["hour"] < h1),
        ("Normal volatility",
         pd.notna(row["atr_med"]) and 0.6 <= row["atr"] / row["atr_med"] <= 2.0),
        ("Clear regime (not transition)", regime in ("UPTREND", "DOWNTREND", "RANGING")),
        ("Risk guard clear", not stopped),
    ]
    st.write("  ".join(("✅ " if ok_ else "❌ ") + n_ for n_, ok_ in checks[:3]))
    st.write("  ".join(("✅ " if ok_ else "❌ ") + n_ for n_, ok_ in checks[3:]))

    st.altair_chart(candle_chart(x, tz), use_container_width=True)
    st.caption("🟠 EMA21  •  🔵 EMA50  •  Today's journal P/L: "
               f"{today_pnl:+.1f} stakes")

# ================= BACKTEST TAB =================
with tab_bt:
    st.caption(f"{len(x):,} candles • {fmt(x['time'].iloc[0])} → {fmt(x['time'].iloc[-1])} "
               f"• payout {payout_pct}%")
    if overall is None:
        st.info("No qualifying setups with the current filters. Loosen the confluence or session filter.")
    else:
        colr, title, note = verdict(overall)
        st.markdown(f"<div class='vd {colr}'><b>{title}</b><br>"
                    f"<span style='opacity:.8;font-size:.85rem'>{note}</span></div>",
                    unsafe_allow_html=True)
        a, b, c_ = st.columns(3)
        a.metric("Trades", overall["n"])
        b.metric("Win rate", f"{overall['wr'] * 100:.1f}%",
                 f"{(overall['wr'] - overall['be']) * 100:+.1f} vs break-even")
        c_.metric("EV / trade", f"{overall['ev']:+.3f} stake")
        d, e, f = st.columns(3)
        d.metric("Net result", f"{overall['net']:+.1f} stakes")
        e.metric("Max drawdown", f"{overall['dd']:.1f} stakes")
        f.metric("Max loss streak", overall["streak"])
        st.caption(
            f"95% confidence range for win rate: {overall['lo'] * 100:.1f}% – {overall['hi'] * 100:.1f}%  "
            f"• p-value vs break-even: {overall['pval']:.3f}  "
            f"• ties (refunded): {overall['ties']}"
        )

        st.markdown("**By setup**")
        rows = []
        for name, s in by_setup.items():
            rows.append({
                "Setup": name, "Trades": s["decided"], "Win %": round(s["wr"] * 100, 1),
                "EV/trade": round(s["ev"], 3), "95% low": round(s["lo"] * 100, 1),
                "Validated": "✅" if validated[name] else "❌",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("**Consistency check** (older half vs newer half)")
        tr = overall["tr"]
        half = len(tr) // 2
        cons = []
        for label, part in (("Older half", tr.iloc[:half]), ("Newer half", tr.iloc[half:])):
            s = score_trades(part.reset_index(drop=True), payout)
            if s:
                cons.append({"Period": label, "Trades": s["decided"],
                             "Win %": round(s["wr"] * 100, 1), "EV/trade": round(s["ev"], 3)})
        if cons:
            st.dataframe(pd.DataFrame(cons), use_container_width=True, hide_index=True)
            st.caption("If the two halves disagree strongly, the edge is probably noise.")

        st.markdown("**Equity curve (stakes)**")
        st.line_chart(pd.Series(overall["equity"], name="equity"))

        st.markdown("**Recent trades**")
        show = overall["tr"].tail(25).iloc[::-1].copy()
        show["entry_time"] = show["entry_time"].dt.tz_convert(tz).dt.strftime("%d %b %H:%M")
        show = show[["entry_time", "side", "setup", "conf", "pips", "result", "pnl"]]
        st.dataframe(show, use_container_width=True, hide_index=True)

# ================= JOURNAL TAB =================
with tab_j:
    st.caption("Log every trade you take. The risk guard uses this to stop you after a bad streak.")
    jc1, jc2, jc3 = st.columns(3)
    j_side = jc1.selectbox("Side", ["UP", "DOWN"])
    j_res = jc2.selectbox("Result", ["WIN", "LOSS", "TIE"])
    if jc3.button("➕ Add", use_container_width=True):
        pnl = {"WIN": payout, "LOSS": -1.0, "TIE": 0.0}[j_res]
        st.session_state["journal"].append({
            "date": now.tz_convert(tz).strftime("%Y-%m-%d"),
            "time": now.tz_convert(tz).strftime("%H:%M"),
            "side": j_side, "result": j_res, "pnl": pnl,
        })
        st.rerun()

    jr = st.session_state["journal"]
    if jr:
        jdf = pd.DataFrame(jr)
        w = int((jdf["result"] == "WIN").sum())
        l_ = int((jdf["result"] == "LOSS").sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Logged trades", len(jdf))
        m2.metric("Win rate", f"{w / (w + l_) * 100:.0f}%" if (w + l_) else "—")
        m3.metric("Net (stakes)", f"{jdf['pnl'].sum():+.1f}")
        st.dataframe(jdf.iloc[::-1], use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear journal"):
            st.session_state["journal"] = []
            st.rerun()
    else:
        st.info("No trades logged yet.")
    st.caption("Journal is kept only while this browser tab session is open.")

# ================= GUIDE TAB =================
with tab_guide:
    st.markdown(
        """
**How to use**
1. Press *Refresh*, read the signal card. Trade only when it says **UP / DOWN** and is not expired.
2. Enter at the **next candle open** shown on the card, with the suggested expiry.
3. Log the result in *Journal*. When the risk guard says STOP, stop.

**The two setups**
- **Trend Pullback** – trade *with* a confirmed trend (ADX high) after a dip to EMA21.
- **Range Reversal** – fade a Bollinger-band rejection, *only* when the market is ranging (ADX low).
- Between the two (ADX in the middle) the bot stays out.

**Reality check**
- With ~85% payout you need **> 54%** wins just to break even. Check the *Backtest* tab: a setup is only trustworthy when its **95% low** is above break-even.
- Yahoo prices can differ from Quotex's own feed by a few pips and arrive slightly late.
- No bot can guarantee wins. Never stake money you cannot afford to lose; keep stakes small.
"""
    )

st.divider()
st.caption("EUR/USD • live market only • OTC disabled • no auto-trading • not financial advice")
