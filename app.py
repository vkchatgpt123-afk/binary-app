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
.dot.g{background:var(--green);box-shadow:0 0 8px var(--green)}
.dot.r{background:var(--red);box-shadow:0 0 8px var(--red)}
.dot.a{background:var(--amber);box-shadow:0 0 8px var(--amber)}

/* signal card */
.sig{position:relative;border-radius:20px;padding:1.5rem 1rem 1.2rem;text-align:center;margin:.4rem 0 1rem;
     border:1px solid var(--line);background:linear-gradient(160deg,#111a2f,#0c1322)}
.sig .big{font-size:2.9rem;font-weight:800;line-height:1.05;letter-spacing:-.02em}
.sig .sub{color:#c3cbe0;font-size:.9rem;margin:.55rem auto 0;max-width:34rem;line-height:1.45}
.sig .meta{color:var(--mut);font-size:.76rem;margin-top:.8rem}
.sig .badge{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
            padding:.22rem .7rem;border-radius:999px;margin-bottom:.7rem;background:rgba(255,255,255,.07);color:#cdd5ea}
.sig.up{border-color:rgba(22,199,132,.55);background:linear-gradient(160deg,rgba(22,199,132,.20),#0c1322 70%);
        box-shadow:0 0 42px rgba(22,199,132,.18)}
.sig.up .big{color:var(--green)}
.sig.down{border-color:rgba(234,57,67,.55);background:linear-gradient(160deg,rgba(234,57,67,.20),#0c1322 70%);
          box-shadow:0 0 42px rgba(234,57,67,.18)}
.sig.down .big{color:var(--red)}
.sig.wait .big{color:var(--amber)}
.sig.stop .big{color:#aab3c9}
.meter{display:flex;gap:5px;justify-content:center;margin-top:.9rem}
.meter i{width:34px;height:6px;border-radius:4px;background:#26324f;display:inline-block}
.meter i.on{background:linear-gradient(90deg,#16c784,#7fe3b9)}
.down .meter i.on{background:linear-gradient(90deg,#ea3943,#ff8f96)}

/* tiles */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem;margin:.5rem 0 .9rem}
.tile{background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);
      border-radius:14px;padding:.7rem .85rem}
.tile .tl{color:var(--mut);font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.tile .tv{font-size:1.28rem;font-weight:700;margin-top:.15rem}
.tile .ts{color:var(--mut);font-size:.7rem;margin-top:.1rem}
.tile.g .tv{color:var(--green)} .tile.r .tv{color:var(--red)} .tile.a .tv{color:var(--amber)} .tile.b .tv{color:var(--blue)}

/* chips */
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.3rem 0 1rem}
.chip{font-size:.74rem;font-weight:600;padding:.3rem .7rem;border-radius:999px;border:1px solid var(--line);
      background:var(--panel2);color:#c3cbe0}
.chip.ok{border-color:rgba(22,199,132,.45);color:#7fe3b9;background:rgba(22,199,132,.09)}
.chip.bad{border-color:rgba(234,57,67,.45);color:#ff9aa1;background:rgba(234,57,67,.09)}
.chip.idle{color:var(--mut)}

/* verdict */
.vd{border-radius:14px;padding:.8rem 1rem;margin:.3rem 0 .8rem;border:1px solid var(--line)}
.vd b{font-size:1rem}.vd span{display:block;color:#c3cbe0;font-size:.82rem;margin-top:.15rem}
.vd.green{background:rgba(22,199,132,.12);border-color:rgba(22,199,132,.45)}
.vd.amber{background:rgba(245,166,35,.11);border-color:rgba(245,166,35,.45)}
.vd.red{background:rgba(234,57,67,.11);border-color:rgba(234,57,67,.45)}
.vd.gray{background:rgba(138,148,173,.10)}

.sec{font-size:.78rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.1em;margin:1rem 0 .3rem}

/* streamlit widgets */
.stTabs [data-baseweb="tab-list"]{gap:.2rem;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{font-weight:600;color:var(--mut);padding:.5rem .8rem}
.stTabs [aria-selected="true"]{color:#fff}
.stButton>button{border-radius:12px;border:1px solid var(--line);background:linear-gradient(160deg,var(--panel2),var(--panel));
                 color:var(--txt);font-weight:600}
.stButton>button:hover{border-color:var(--blue);color:#fff}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.session_state.setdefault("journal", [])
st.session_state["_full_run"] = True


def tile(label, value, sub="", tone=""):
    return (f"<div class='tile {tone}'><div class='tl'>{label}</div>"
            f"<div class='tv'>{value}</div><div class='ts'>{sub}</div></div>")


def grid(items):
    return "<div class='grid'>" + "".join(items) + "</div>"


def chips(items):
    cls = {True: "ok", False: "bad", None: "idle"}
    sym = {True: "✓", False: "✕", None: "–"}
    return "<div class='chips'>" + "".join(
        f"<span class='chip {cls[s]}'>{sym[s]} {name}</span>" for name, s in items) + "</div>"


def sec(title):
    st.markdown(f"<div class='sec'>{title}</div>", unsafe_allow_html=True)


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
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
    auto_refresh = st.checkbox("Auto-refresh every 30s", value=True)

    st.markdown("### 🎯 Filters")
    h0, h1 = st.slider("Trading session (UTC hours)", 0, 24, (7, 20),
                       help="07-20 UTC = London + New York. Asian night is low quality.")
    min_conf = st.slider("Minimum confluence (0-5)", 0, 5, 2)
    use_htf = st.checkbox("Higher-timeframe trend must agree", value=True,
                          help="Big accuracy filter for trend trades.")
    require_valid = st.checkbox("Only signal validated setups", value=True,
                                help="Blocks a setup unless it has been profitable in the backtest.")
    strict = st.checkbox("Strict validation (95% proof)", value=False,
                         help="Setup must beat break-even even in the pessimistic estimate. Very selective.")
    one_at_a_time = st.checkbox("One trade at a time", value=True)
    with st.expander("Advanced"):
        adx_trend = st.slider("ADX = trending above", 15, 35, 22)
        adx_range = st.slider("ADX = ranging below", 10, 25, 20)

    st.markdown("### 🛡️ Risk guard")
    balance = st.number_input("Balance", min_value=0.0, value=100.0, step=10.0)
    stake_pct = st.slider("Stake % of balance", 0.5, 5.0, 1.0, 0.5)
    max_consec = st.slider("Stop after N losses in a row", 1, 5, 2)
    max_loss_units = st.slider("Daily loss limit (stakes)", 1, 10, 3)
    st.caption(f"Suggested stake: **{balance * stake_pct / 100:.2f}**")

params = {"h0": h0, "h1": h1, "min_conf": min_conf, "adx_trend": adx_trend,
          "adx_range": adx_range, "use_htf": use_htf}

# ---------------- data ----------------
try:
    raw = fetch_candles(interval)
except Exception as err:
    st.markdown("<div class='hero'><div><div class='t'>EUR/USD Signal Pro</div></div></div>",
                unsafe_allow_html=True)
    st.markdown("<div class='sig stop'><div class='big'>⛔ NO DATA</div>"
                "<div class='sub'>Could not reach the live price feed. Do not trade without data.</div></div>",
                unsafe_allow_html=True)
    st.code(str(err))
    if st.button("🔄 Try again", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.stop()

x = add_indicators(raw, mins)
sig = compute_signals(x, params)
bt = run_backtest(x, sig, horizon, one_at_a_time)
overall = score_trades(bt, payout)

by_setup = {}
if overall is not None:
    for name, g in overall["tr"].groupby("setup"):
        by_setup[name] = score_trades(g.reset_index(drop=True), payout)
if strict:
    validated = {k: (v["decided"] >= 30 and v["lo"] > v["be"]) for k, v in by_setup.items()}
else:
    validated = {k: (v["decided"] >= 20 and v["ev"] > 0) for k, v in by_setup.items()}

now = pd.Timestamp.now(tz="UTC")
delta = pd.Timedelta(minutes=mins)
last_bar = x["time"].iloc[-1]
idx = len(x) - 1 if now >= last_bar + delta else len(x) - 2
row = x.iloc[idx]
entry_time = row["time"] + delta
age_s = (now - entry_time).total_seconds()
mkt_open, opens_at = market_state(now)
feed_stale = mkt_open and (now - last_bar) > max(pd.Timedelta(minutes=15), 3 * delta)
window_s = max(20, int(mins * 60 * 0.3))
regime = regime_label(row, params)
secs_left = max(0, int((now.floor(f"{mins}min") + delta - now).total_seconds()))


def fmt(t):
    return t.tz_convert(tz).strftime("%a %d %b, %H:%M")


# ---------------- header ----------------
if not mkt_open:
    status_html = "<span class='pill'><span class='dot a'></span>MARKET CLOSED</span>"
elif feed_stale:
    status_html = "<span class='pill'><span class='dot r'></span>FEED STALE</span>"
else:
    status_html = "<span class='pill'><span class='dot g'></span>LIVE</span>"
status_html += (f"<span class='pill'>EUR/USD • {interval}</span>"
                f"<span class='pill'>🕒 {now.tz_convert(tz).strftime('%H:%M')} {tz.split('/')[-1]}</span>")
if mkt_open and not feed_stale:
    status_html += f"<span class='pill'>⏱ next candle {secs_left // 60}:{secs_left % 60:02d}</span>"

st.markdown(
    "<div class='hero'><div><div class='t'>EUR/USD Signal Pro</div>"
    "<div class='s'>Manual signals • closed candles only</div></div></div>"
    f"<div class='status'>{status_html}</div>",
    unsafe_allow_html=True,
)
if st.button("🔄 Refresh live data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.caption("⚙️ Settings: tap the » icon at the top-left.")

tab_sig, tab_bt, tab_j, tab_guide = st.tabs(["📡 Signal", "📈 Backtest", "📒 Journal", "ℹ️ Guide"])

# ================= SIGNAL TAB =================
with tab_sig:
    htf_txt = {1.0: "UP", -1.0: "DOWN"}.get(row["htf"], "—")
    htf_tone = {"UP": "g", "DOWN": "r"}.get(htf_txt, "")
    reg_tone = {"UPTREND": "g", "DOWNTREND": "r", "RANGING": "b", "TRANSITION": "a"}.get(regime, "")
    st.markdown(grid([
        tile("Price", f"{row['close']:.5f}"),
        tile("Regime", regime.title(), "", reg_tone),
        tile("Higher TF", htf_txt, f"{HTF_MINUTES.get(mins, 15)}m trend", htf_tone),
        tile("ATR", f"{row['atr'] / PIP:.1f}" if pd.notna(row["atr"]) else "—", "pips"),
        tile("ADX", f"{row['adx']:.0f}" if pd.notna(row["adx"]) else "—", "trend strength"),
        tile("RSI", f"{row['rsi']:.0f}" if pd.notna(row["rsi"]) else "—", "14"),
    ]), unsafe_allow_html=True)

    today = now.tz_convert(tz).strftime("%Y-%m-%d")
    stopped, stop_msg, today_pnl = guard_status(st.session_state["journal"], today, max_consec, max_loss_units)

    side = int(sig["side"].iloc[idx])
    setup = sig["setup"].iloc[idx]
    conf = int(sig["conf"].iloc[idx])
    badge, meter = "", ""

    if not mkt_open:
        card, big = "stop", "🌙 MARKET CLOSED"
        sub = f"Forex reopens around <b>{fmt(opens_at)}</b>. No signals until then."
        meta = "Weekend break: Fri 21:00 → Sun 21:00 UTC. Use the Backtest tab meanwhile."
    elif feed_stale:
        card, big = "stop", "⛔ NO DATA"
        sub = "The live feed is delayed. Refresh in a minute. Do not trade without fresh data."
        meta = f"Last candle: {fmt(last_bar)}"
    elif stopped:
        card, big = "stop", "🛑 STOP TODAY"
        sub = f"Risk guard: {stop_msg}. Come back tomorrow."
        meta = "Protecting your balance is part of the strategy."
    elif side != 0 and age_s > window_s:
        card, big = "wait", "⌛ EXPIRED"
        sub = f"Signal is {int(age_s)}s old. Entering late ruins the edge - wait for the next one."
        meta = f"Setup was: {setup} ({'UP' if side == 1 else 'DOWN'})"
    elif side != 0 and require_valid and not validated.get(setup, False):
        card, big = "wait", "NO TRADE"
        sub = f"{setup} fired, but this setup has not proven profitable in the backtest, so it is skipped."
        meta = "Untick 'Only signal validated setups' to override (not recommended)."
    elif side != 0:
        card = "up" if side == 1 else "down"
        big = "▲ UP" if side == 1 else "▼ DOWN"
        badge = setup
        sub = explain(row, setup, side, params)
        meta = (f"Enter at {fmt(entry_time)} • expiry {horizon * mins} min • valid for {window_s}s")
        meter = "<div class='meter'>" + "".join(
            f"<i class='{'on' if k < conf else ''}'></i>" for k in range(5)) + "</div>"
    else:
        card, big = "wait", "NO TRADE"
        sub = why_no_trade(row, params)
        meta = f"Analysed candle closed {fmt(entry_time)}"
        if not (h0 <= row["hour"] < h1):
            meta += f" • next session starts {fmt(next_session(now, h0))}"

    badge_html = f"<div class='badge'>{badge}</div>" if badge else ""
    st.markdown(
        f"<div class='sig {card}'>{badge_html}<div class='big'>{big}</div>"
        f"<div class='sub'>{sub}</div>{meter}<div class='meta'>{meta}</div></div>",
        unsafe_allow_html=True,
    )

    if card in ("up", "down"):
        s = by_setup.get(setup)
        if s:
            st.caption(
                f"Track record of **{setup}**: {s['wr'] * 100:.1f}% wins over {s['decided']} trades "
                f"(break-even {s['be'] * 100:.1f}%).")

    sec("Safety checks")
    vol_ok = pd.notna(row["atr_med"]) and 0.6 <= row["atr"] / row["atr_med"] <= 2.0
    st.markdown(chips([
        ("Market open", mkt_open),
        ("Fresh data", (not feed_stale) if mkt_open else None),
        ("In session", h0 <= row["hour"] < h1),
        ("Normal volatility", bool(vol_ok)),
        ("Clear regime", regime in ("UPTREND", "DOWNTREND", "RANGING")),
        ("Risk guard", not stopped),
    ]), unsafe_allow_html=True)

    sec("Chart")
    st.altair_chart(candle_chart(x, tz), use_container_width=True, theme=None)
    st.caption(f"🟠 EMA21   🔵 EMA50   •   Today's journal P/L: {today_pnl:+.1f} stakes")

# ================= BACKTEST TAB =================
with tab_bt:
    st.caption(f"{len(x):,} candles • {fmt(x['time'].iloc[0])} → {fmt(x['time'].iloc[-1])} "
               f"• payout {payout_pct}%")
    if overall is None:
        st.info("No qualifying setups with the current filters. Loosen the confluence or session filter.")
    else:
        colr, title, note = verdict(overall)
        st.markdown(f"<div class='vd {colr}'><b>{title}</b><span>{note}</span></div>",
                    unsafe_allow_html=True)
        edge = (overall["wr"] - overall["be"]) * 100
        st.markdown(grid([
            tile("Trades", overall["n"], f"{overall['wins']}W / {overall['losses']}L / {overall['ties']}T"),
            tile("Win rate", f"{overall['wr'] * 100:.1f}%", f"{edge:+.1f} pts vs break-even",
                 "g" if edge > 0 else "r"),
            tile("EV / trade", f"{overall['ev']:+.3f}", "stake units", "g" if overall["ev"] > 0 else "r"),
            tile("Net result", f"{overall['net']:+.1f}", "stakes", "g" if overall["net"] > 0 else "r"),
            tile("Max drawdown", f"{overall['dd']:.1f}", "stakes", "a"),
            tile("Max loss streak", overall["streak"], "in a row", "a"),
        ]), unsafe_allow_html=True)
        st.caption(
            f"95% range for win rate: {overall['lo'] * 100:.1f}% – {overall['hi'] * 100:.1f}%  •  "
            f"p-value vs break-even: {overall['pval']:.3f}")

        sec("By setup")
        rows = [{
            "Setup": name, "Trades": s["decided"], "Win %": round(s["wr"] * 100, 1),
            "EV/trade": round(s["ev"], 3), "95% low": round(s["lo"] * 100, 1),
            "Validated": "✅" if validated[name] else "❌",
        } for name, s in by_setup.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        sec("Consistency check · older vs newer half")
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
            st.caption("If the halves disagree strongly, the edge is probably noise.")

        sec("Equity curve · stakes")
        st.altair_chart(equity_chart(overall["equity"]), use_container_width=True, theme=None)

        sec("Recent trades")
        show = overall["tr"].tail(25).iloc[::-1].copy()
        show["entry_time"] = show["entry_time"].dt.tz_convert(tz).dt.strftime("%d %b %H:%M")
        show = show[["entry_time", "side", "setup", "conf", "pips", "result", "pnl"]]
        st.dataframe(show, use_container_width=True, hide_index=True)

        csv = overall["tr"].to_csv(index=False).encode()
        st.download_button("⬇️ Download all backtest trades (CSV)", csv, "backtest_trades.csv",
                           "text/csv", use_container_width=True)

# ================= JOURNAL TAB =================
with tab_j:
    st.caption("Log every trade you take. The risk guard uses this to stop you after a bad streak.")
    jc1, jc2, jc3 = st.columns(3)
    j_side = jc1.selectbox("Side", ["UP", "DOWN"])
    j_res = jc2.selectbox("Result", ["WIN", "LOSS", "TIE"])
    jc3.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
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
        net = float(jdf["pnl"].sum())
        st.markdown(grid([
            tile("Logged trades", len(jdf)),
            tile("Win rate", f"{w / (w + l_) * 100:.0f}%" if (w + l_) else "—"),
            tile("Net", f"{net:+.1f}", "stakes", "g" if net > 0 else ("r" if net < 0 else "")),
        ]), unsafe_allow_html=True)
        st.dataframe(jdf.iloc[::-1], use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear journal"):
            st.session_state["journal"] = []
            st.rerun()
    else:
        st.info("No trades logged yet.")
    st.caption("Journal is kept only while this browser session is open.")

# ================= GUIDE TAB =================
with tab_guide:
    st.markdown(
        """
**How to use**
1. Read the signal card. Trade only when it says **▲ UP / ▼ DOWN** and is not expired.
2. Enter at the **next candle open** shown on the card, with the suggested expiry.
3. Log the result in *Journal*. When the risk guard says STOP, stop.

**The two setups**
- **Trend Pullback**: trade *with* a confirmed trend (ADX high, higher timeframe agrees) after a dip to EMA21.
- **Range Reversal**: fade a Bollinger-band rejection, *only* when the market is ranging (ADX low).
- Between the two (ADX in the middle) the bot stays out.

**Reality check**
- With ~85% payout you need **more than 54%** wins just to break even. In *Backtest*, trust a setup only when its **95% low** is above break-even.
- Yahoo prices can differ from Quotex's own feed by a few pips and arrive slightly late.
- No bot can guarantee wins. Keep stakes small and never risk money you cannot afford to lose.
"""
    )

st.markdown("<div style='text-align:center;color:#5d6882;font-size:.72rem;margin-top:1.5rem'>"
            "EUR/USD • live market only • OTC disabled • no auto-trading • not financial advice</div>",
            unsafe_allow_html=True)

# ---------------- auto refresh (only while market is open) ----------------
if auto_refresh and mkt_open and hasattr(st, "fragment"):
    @st.fragment(run_every=30)
    def _auto_tick():
        if st.session_state.pop("_full_run", False):
            return
        st.rerun()

    _auto_tick()
