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
    initial_sidebar_state="collapsed",
)

PIP = 0.0001
SYMBOL = "EURUSD=X"
# interval -> (yahoo range, minutes per candle)
INTERVALS = {"1m": ("7d", 1), "5m": ("60d", 5), "15m": ("60d", 15)}
HTF_MINUTES = {1: 5, 5: 15, 15: 60}  # higher-timeframe used for trend confirmation
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


def add_indicators(df, mins=5):
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
    x["htf"] = higher_tf_trend(x, mins)
    return x


def higher_tf_trend(x, mins):
    """+1 / -1 trend of the higher timeframe using ONLY fully closed HTF candles."""
    hm = HTF_MINUTES.get(mins, 15)
    s = x.set_index("time")["close"]
    h = s.resample(f"{hm}min").last().dropna()
    e21 = h.ewm(span=21, adjust=False).mean()
    e50 = h.ewm(span=50, adjust=False).mean()
    trend = ((e21 > e50).astype(int) - (e21 < e50).astype(int)).astype(float)
    trend.iloc[:50] = np.nan
    trend = trend.shift(1)  # value known only after that HTF candle has closed
    pos = trend.index.get_indexer(x["time"].dt.floor(f"{hm}min"), method="pad")
    vals = trend.to_numpy()
    out = np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan)
    return pd.Series(out, index=x.index)


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
    if p.get("use_htf", True):
        a_up = a_up & (x["htf"] == 1)
        a_dn = a_dn & (x["htf"] == -1)
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


def market_state(now):
    """Forex trades Sun ~21:00 UTC -> Fri ~21:00 UTC."""
    wd, hr = now.weekday(), now.hour
    closed = (wd == 4 and hr >= 21) or wd == 5 or (wd == 6 and hr < 21)
    if not closed:
        return True, None
    opens = (now.normalize() + pd.Timedelta(days=(6 - wd) % 7)).replace(hour=21)
    return False, opens


def next_session(now, h0):
    c = now.normalize() + pd.Timedelta(hours=h0)
    if c <= now:
        c += pd.Timedelta(days=1)
    while c.weekday() >= 5:
        c += pd.Timedelta(days=1)
    return c


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
    if reg in ("UPTREND", "DOWNTREND") and p.get("use_htf", True):
        want = 1 if reg == "UPTREND" else -1
        if r["htf"] != want:
            return f"{reg.title()} here, but the higher timeframe does not agree - skipped."
    return f"{reg.title()}, but no pullback-and-resume trigger yet."


def explain(r, setup, side, p):
    d = "UP" if side == 1 else "DOWN"
    if setup == "Trend Pullback":
        trend = "uptrend" if side == 1 else "downtrend"
        return (f"{trend} (ADX {r['adx']:.0f}); price dipped to EMA21 and resumed {d}; "
                f"RSI {r['rsi']:.0f}; higher timeframe agrees.")
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
# CHARTS (dark theme)
# ============================================================

GREEN, RED, AMBER, BLUE, MUTED = "#16c784", "#ea3943", "#f5a623", "#4c8bf5", "#8a94ad"


def dark(chart):
    return (chart.configure(background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor="#1b2540", domainColor="#1b2540", tickColor="#1b2540",
                            labelColor=MUTED, labelFontSize=11, titleColor=MUTED))


def candle_chart(x, tz, n=80):
    d = x.tail(n).copy()
    d["time"] = d["time"].dt.tz_convert(tz).dt.tz_localize(None)
    d["up"] = d["close"] >= d["open"]
    ysc = alt.Scale(zero=False)
    col = alt.condition("datum.up", alt.value(GREEN), alt.value(RED))
    base = alt.Chart(d).encode(x=alt.X("time:T", title=None))
    wick = base.mark_rule().encode(y=alt.Y("low:Q", scale=ysc, title=None), y2="high:Q", color=col)
    body = base.mark_bar(size=5).encode(y=alt.Y("open:Q", scale=ysc), y2="close:Q", color=col)
    e21 = base.mark_line(color=AMBER, strokeWidth=1.3).encode(y=alt.Y("ema21:Q", scale=ysc))
    e50 = base.mark_line(color=BLUE, strokeWidth=1.3).encode(y=alt.Y("ema50:Q", scale=ysc))
    return dark((wick + body + e21 + e50).properties(height=280))


def equity_chart(eq):
    d = pd.DataFrame({"trade": range(len(eq)), "equity": eq})
    base = alt.Chart(d).encode(x=alt.X("trade:Q", title=None), y=alt.Y("equity:Q", title=None))
    area = base.mark_area(opacity=0.22, color=BLUE)
    line = base.mark_line(color=BLUE, strokeWidth=2)
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    return dark((area + line + zero).properties(height=200))


# ===== UI =====


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#090d16;--panel:#0f1626;--panel2:#141d33;--line:#1e2a47;--txt:#e7ebf6;--mut:#8a94ad;
      --green:#16c784;--red:#ea3943;--amber:#f5a623;--blue:#4c8bf5}
html,body,[class*="css"],.stApp{font-family:'Inter',sans-serif}
.stApp{background:radial-gradient(1100px 520px at 50% -8%,#142142 0%,#090d16 58%) fixed;color:var(--txt)}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:1.1rem;padding-bottom:3rem;max-width:760px}
[data-testid="stSidebar"]{background:#0b1120;border-right:1px solid var(--line)}
h1,h2,h3,h4{letter-spacing:-.01em}

/* header */
.hero{display:flex;justify-content:space-between;align-items:center;gap:.6rem;flex-wrap:wrap;margin:.2rem 0 .7rem}
.hero .t{font-size:1.45rem;font-weight:800;background:linear-gradient(90deg,#fff,#7fb0ff 60%,#16c784);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero .s{color:var(--mut);font-size:.72rem;font-weight:500;letter-spacing:.08em;text-transform:uppercase}
.status{display:flex;gap:.45rem;flex-wrap:wrap;margin-bottom:.7rem}
.pill{display:inline-flex;align-items:center;gap:.4rem;padding:.28rem .7rem;border-radius:999px;font-size:.72rem;
      font-weight:600;background:var(--panel2);border:1px solid var(--line);color:var(--txt)}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.dot.g{background:var(--green);box-shadow
