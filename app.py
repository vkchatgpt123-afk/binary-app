from datetime import datetime
import json
import math
import os

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="EUR/USD Signal Pro Advanced",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

PIP = 0.0001
SYMBOL = "EURUSD=X"
INTERVALS = {"1m": ("7d", 1), "5m": ("60d", 5), "15m": ("60d", 15)}
HTF_MINUTES = {1: 5, 5: 15, 15: 60}
TIMEZONES = ["Asia/Kolkata", "UTC", "Asia/Dubai", "Europe/London", "America/New_York"]
JOURNAL_FILE = "trading_journal.json"


# ============================================================
# PERSISTENT JOURNAL STORAGE
# ============================================================
def load_journal_data():
  if os.path.exists(JOURNAL_FILE):
    try:
      with open(JOURNAL_FILE, "r") as f:
        return json.load(f)
    except:
      pass
  return []


def save_journal_data(data):
  try:
    with open(JOURNAL_FILE, "w") as f:
      json.dump(data, f)
  except:
    pass


# ============================================================
# STATISTICS & KELLY CRITERION
# ============================================================
def wilson(wins, n, z=1.96):
  if n <= 0:
    return np.nan, np.nan
  p = wins / n
  den = 1 + z * z / n
  center = (p + z * z / (2 * n)) / den
  half = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0)) / den
  return center - half, center + half


def p_value_vs_breakeven(wins, n, breakeven):
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


def kelly_fraction(wr, payout):
  if payout <= 0 or wr <= 0:
    return 0.0
  f = (wr * (payout + 1) - 1) / payout
  return max(0.0, f)


# ============================================================
# LIVE DATA FETCHING
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
          "open": q["open"],
          "high": q["high"],
          "low": q["low"],
          "close": q["close"],
      })
      df = (
          df.dropna()
          .drop_duplicates("time")
          .sort_values("time")
          .reset_index(drop=True)
      )
      if len(df) < 250:
        raise ValueError(f"Only {len(df)} candles received")
      return df
    except Exception as e:
      last_err = e
  raise RuntimeError(f"Yahoo feed unavailable: {last_err}")


# ============================================================
# UI HELPER FUNCTIONS (MISSING EARLIER)
# ============================================================
def grid(tiles):
  return f"<div class='grid'>{''.join(tiles)}</div>"


def tile(title, val, sub="", tone=""):
  return (
      f"<div class='tile {tone}'><div class='tl'>{title}</div><div"
      f" class='tv'>{val}</div><div class='ts'>{sub}</div></div>"
  )


def chips(items):
  res = []
  for label, ok in items:
    c = "ok" if ok is True else ("bad" if ok is False else "idle")
    res.append(f"<span class='chip {c}'>{label}</span>")
  return f"<div class='chips'>{''.join(res)}</div>"


# ============================================================
# TECHNICAL INDICATORS (Includes RSI, ATR, ADX, MACD, Stochastic)
# ============================================================
def wilder(s, n):
  return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_indicators(df, mins=5):
  x = df.copy()
  c, o, h, l = x["close"], x["open"], x["high"], x["low"]

  # Moving Averages
  x["ema9"] = c.ewm(span=9, adjust=False).mean()
  x["ema21"] = c.ewm(span=21, adjust=False).mean()
  x["ema50"] = c.ewm(span=50, adjust=False).mean()

  # RSI
  delta = c.diff()
  gain = wilder(delta.clip(lower=0), 14)
  loss = wilder(-delta.clip(upper=0), 14)
  rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
  rsi[(loss == 0) & (gain > 0)] = 100.0
  x["rsi"] = rsi

  # ATR & Volatility
  tr = pd.concat(
      [h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
  ).max(axis=1)
  x["atr"] = wilder(tr, 14)
  x["atr_med"] = x["atr"].shift(1).rolling(100).median()

  # ADX (Trend Strength)
  up, dn = h.diff(), -l.diff()
  plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=x.index)
  minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=x.index)
  plus_di = 100 * wilder(plus_dm, 14) / x["atr"]
  minus_di = 100 * wilder(minus_dm, 14) / x["atr"]
  dx = (
      100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
  )
  x["adx"] = wilder(dx, 14)

  # Bollinger Bands
  mid = c.rolling(20).mean()
  sd = c.rolling(20).std(ddof=0)
  x["bb_mid"], x["bb_up"], x["bb_lo"] = mid, mid + 2 * sd, mid - 2 * sd

  # MACD
  ema12 = c.ewm(span=12, adjust=False).mean()
  ema26 = c.ewm(span=26, adjust=False).mean()
  x["macd_line"] = ema12 - ema26
  x["macd_signal"] = x["macd_line"].ewm(span=9, adjust=False).mean()
  x["macd_hist"] = x["macd_line"] - x["macd_signal"]

  # Stochastic Oscillator (14, 3, 3)
  lowest_low = l.rolling(window=14).min()
  highest_high = h.rolling(window=14).max()
  x["stoch_k"] = (
      100 * (c - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
  )
  x["stoch_d"] = x["stoch_k"].rolling(window=3).mean()

  # Candle geometry properties
  rng = (h - l).replace(0, np.nan)
  x["body_atr"] = (c - o).abs() / x["atr"].replace(0, np.nan)
  x["close_loc"] = (c - l) / rng
  x["upper_wick"] = (h - np.maximum(o, c)) / rng
  x["lower_wick"] = (np.minimum(o, c) - l) / rng
  x["hour"] = x["time"].dt.hour
  x["htf"] = higher_tf_trend(x, mins)
  return x


def higher_tf_trend(x, mins):
  hm = HTF_MINUTES.get(mins, 15)
  s = x.set_index("time")["close"]
  h = s.resample(f"{hm}min").last().dropna()
  e21 = h.ewm(span=21, adjust=False).mean()
  e50 = h.ewm(span=50, adjust=False).mean()
  trend = ((e21 > e50).astype(int) - (e21 < e50).astype(int)).astype(float)
  trend.iloc[:50] = np.nan
  trend = trend.shift(1)
  pos = trend.index.get_indexer(x["time"].dt.floor(f"{hm}min"), method="pad")
  vals = trend.to_numpy()
  out = np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan)
  return pd.Series(out, index=x.index)


# ============================================================
# SIGNAL ENGINE
# ============================================================
def compute_signals(x, p):
  c, o, h, l = x["close"], x["open"], x["high"], x["low"]
  ratio = x["atr"] / x["atr_med"]

  ok = (
      (x["hour"] >= p["h0"])
      & (x["hour"] < p["h1"])
      & ratio.between(0.6, 2.0)
      & (x["body_atr"] <= 3.0)
      & x[[
          "atr",
          "atr_med",
          "rsi",
          "adx",
          "bb_up",
          "ema50",
          "macd_hist",
          "stoch_k",
      ]]
      .notna()
      .all(axis=1)
  )
  good_vol = ratio.between(0.8, 1.5)

  up_tr = (
      (x["ema21"] > x["ema50"])
      & (c > x["ema50"])
      & (x["adx"] >= p["adx_trend"])
  )
  dn_tr = (
      (x["ema21"] < x["ema50"])
      & (c < x["ema50"])
      & (x["adx"] >= p["adx_trend"])
  )

  a_up = (
      ok
      & up_tr
      & (l.rolling(3).min() <= x["ema21"])
      & (c > x["ema21"])
      & (c > o)
      & (c > c.shift(1))
      & (x["close_loc"] >= 0.6)
      & x["rsi"].between(40, 66)
      & (x["macd_hist"] > 0)
      & (x["stoch_k"] > x["stoch_d"])
  )
  a_dn = (
      ok
      & dn_tr
      & (h.rolling(3).max() >= x["ema21"])
      & (c < x["ema21"])
      & (c < o)
      & (c < c.shift(1))
      & (x["close_loc"] <= 0.4)
      & x["rsi"].between(34, 60)
      & (x["macd_hist"] < 0)
      & (x["stoch_k"] < x["stoch_d"])
  )
  if p.get("use_htf", True):
    a_up = a_up & (x["htf"] == 1)
    a_dn = a_dn & (x["htf"] == -1)

  conf_a_up = (
      (x["adx"] >= 30).astype(int)
      + (x["ema9"] > x["ema21"]).astype(int)
      + x["rsi"].between(45, 60).astype(int)
      + good_vol.astype(int)
      + (x["close_loc"] >= 0.75).astype(int)
      + (x["macd_hist"] > x["macd_hist"].shift(1)).astype(int)
  )
  conf_a_dn = (
      (x["adx"] >= 30).astype(int)
      + (x["ema9"] < x["ema21"]).astype(int)
      + x["rsi"].between(40, 55).astype(int)
      + good_vol.astype(int)
      + (x["close_loc"] <= 0.25).astype(int)
      + (x["macd_hist"] < x["macd_hist"].shift(1)).astype(int)
  )

  ranging = x["adx"] < p["adx_range"]
  b_up = (
      ok
      & ranging
      & (c.shift(1) <= x["bb_lo"].shift(1))
      & (x["rsi"].shift(1) <= 35)
      & (x["stoch_k"].shift(1) <= 20)
      & (c > x["bb_lo"])
      & (c > o)
      & (x["close_loc"] >= 0.55)
  )
  b_dn = (
      ok
      & ranging
      & (c.shift(1) >= x["bb_up"].shift(1))
      & (x["rsi"].shift(1) >= 65)
      & (x["stoch_k"].shift(1) >= 80)
      & (c < x["bb_up"])
      & (c < o)
      & (x["close_loc"] <= 0.45)
  )
  conf_b_up = (
      (x["rsi"].shift(1) <= 30).astype(int)
      + (x["lower_wick"].shift(1) >= 0.4).astype(int)
      + good_vol.astype(int)
      + (x["stoch_k"].shift(1) <= 15).astype(int)
      + (x["adx"] < 15).astype(int)
  )
  conf_b_dn = (
      (x["rsi"].shift(1) >= 70).astype(int)
      + (x["upper_wick"].shift(1) >= 0.4).astype(int)
      + good_vol.astype(int)
      + (x["stoch_k"].shift(1) >= 85).astype(int)
      + (x["adx"] < 15).astype(int)
  )

  n = len(x)
  side = np.zeros(n, dtype=int)
  conf = np.zeros(n, dtype=int)
  setup = np.array([""] * n, dtype=object)
  for mask, s, name, cf in [
      (a_up, 1, "Trend Pullback", conf_a_up),
      (a_dn, -1, "Trend Pullback", conf_a_dn),
      (b_up, 1, "Range Reversal", conf_b_up),
      (b_dn, -1, "Range Reversal", conf_b_dn),
  ]:
    m = (
        mask.fillna(False).to_numpy(dtype=bool)
        & (cf.to_numpy() >= p["min_conf"])
    )
    side[m], conf[m], setup[m] = s, cf.to_numpy()[m], name
  return pd.DataFrame({"side": side, "conf": conf, "setup": setup}, index=x.index)


def market_state(now):
  wd, hr = now.weekday(), now.hour
  closed = (wd == 4 and hr >= 21) or wd == 5 or (wd == 6 and hr < 21)
  if not closed:
    return True, None
  opens = (now.normalize() + pd.Timedelta(days=(6 - wd) % 7)).replace(hour=21)
  return False, opens


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
    return "Outside chosen trading session."
  if pd.isna(r["atr_med"]) or pd.isna(r["adx"]):
    return "Indicators warming up."
  ratio = r["atr"] / r["atr_med"]
  if ratio < 0.6:
    return "Market too quiet."
  if ratio > 2.0:
    return "Volatility spike."
  reg = regime_label(r, p)
  if reg == "TRANSITION":
    return f"Transition zone (ADX {r['adx']:.0f})."
  if reg == "RANGING":
    return "Ranging market, waiting for Stochastic/Bollinger extremes."
  return f"{reg.title()}, waiting for MACD/Pullback trigger."


def explain(r, setup, side, p):
  d = "UP" if side == 1 else "DOWN"
  if setup == "Trend Pullback":
    trend = "uptrend" if side == 1 else "downtrend"
    return f"{trend} (ADX {r['adx']:.0f}); MACD hist confirmed; Stoch crossover {d}."
  band = "lower" if side == 1 else "upper"
  return f"Ranging (ADX {r['adx']:.0f}); Stoch & RSI extreme rejection at {band} band."


# ============================================================
# BACKTEST ENGINE
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
        "signal_time": x["time"].iat[i],
        "entry_time": x["time"].iat[e],
        "side": "UP" if s == 1 else "DOWN",
        "setup": sig["setup"].iat[i],
        "conf": int(sig["conf"].iat[i]),
        "entry": o[e],
        "exit": c[ex],
        "pips": move,
        "result": res,
    })
    busy_until = ex
  return pd.DataFrame(rows)


def score_trades(tr, payout):
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
      "tr": tr,
      "n": len(tr),
      "wins": wins,
      "losses": losses,
      "ties": len(tr) - decided,
      "decided": decided,
      "wr": wr,
      "lo": lo,
      "hi": hi,
      "be": be,
      "ev": float(tr["pnl"].mean()),
      "net": float(tr["pnl"].sum()),
      "dd": max_dd,
      "streak": max_loss_streak(tr["result"]),
      "pval": p_value_vs_breakeven(wins, decided, be),
      "equity": equity,
  }


def verdict(s):
  if s is None or s["decided"] < 30:
    return "gray", "Not enough trades", "Fewer than 30 decided trades."
  if s["lo"] > s["be"]:
    return "green", "Proven Edge", "Pessimistic 95% win-rate beats break-even."
  if s["ev"] > 0:
    return "amber", "Positive, Unproven", "Profitable in sample."
  return "red", "No Edge", "Win rate is below break-even."


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
# CHARTS
# ============================================================
GREEN, RED, AMBER, BLUE, MUTED = (
    "#16c784",
    "#ea3943",
    "#f5a623",
    "#4c8bf5",
    "#8a94ad",
)


def dark(chart):
  return (
      chart.configure(background="transparent")
      .configure_view(strokeWidth=0)
      .configure_axis(
          gridColor="#1b2540",
          domainColor="#1b2540",
          tickColor="#1b2540",
          labelColor=MUTED,
          labelFontSize=11,
          titleColor=MUTED,
      )
  )


def candle_chart(x, tz, n=80):
  d = x.tail(n).copy()
  d["time"] = d["time"].dt.tz_convert(tz).dt.tz_localize(None)
  d["up"] = d["close"] >= d["open"]
  ysc = alt.Scale(zero=False)
  col = alt.condition("datum.up", alt.value(GREEN), alt.value(RED))
  base = alt.Chart(d).encode(x=alt.X("time:T", title=None))
  wick = base.mark_rule().encode(
      y=alt.Y("low:Q", scale=ysc, title=None), y2="high:Q", color=col
  )
  body = base.mark_bar(size=5).encode(
      y=alt.Y("open:Q", scale=ysc), y2="close:Q", color=col
  )
  e21 = base.mark_line(color=AMBER, strokeWidth=1.3).encode(
      y=alt.Y("ema21:Q", scale=ysc)
  )
  e50 = base.mark_line(color=BLUE, strokeWidth=1.3).encode(
      y=alt.Y("ema50:Q", scale=ysc)
  )
  return dark((wick + body + e21 + e50).properties(height=280))


def equity_chart(eq):
  d = pd.DataFrame({"trade": range(len(eq)), "equity": eq})
  base = alt.Chart(d).encode(
      x=alt.X("trade:Q", title=None), y=alt.Y("equity:Q", title=None)
  )
  area = base.mark_area(opacity=0.22, color=BLUE)
  line = base.mark_line(color=BLUE, strokeWidth=2)
  zero = (
      alt.Chart(pd.DataFrame({"y": [0]}))
      .mark_rule(color=MUTED, strokeDash=[4, 4])
      .encode(y="y:Q")
  )
  return dark((area + line + zero).properties(height=200))


# ============================================================
# STYLES & UI
# ============================================================
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
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem;margin:.5rem 0 .9rem}
.tile{background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);
      border-radius:14px;padding:.7rem .85rem}
.tile .tl{color:var(--mut);font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.tile .tv{font-size:1.28rem;font-weight:700;margin-top:.15rem}
.tile .ts{color:var(--mut);font-size:.7rem;margin-top:.1rem}
.tile.g .tv{color:var(--green)} .tile.r .tv{color:var(--red)} .tile.a .tv{color:var(--amber)} .tile.b .tv{color:var(--blue)}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.3rem 0 1rem}
.chip{font-size:.74rem;font-weight:600;padding:.3rem .7rem;border-radius:999px;border:1px solid var(--line);
      background:var(--panel2);color:#c3cbe0}
.chip.ok{border-color:rgba(22,199,132,.45);color:#7fe3b9;background:rgba(22,199,132,.09)}
.chip.bad{border-color:rgba(234,57,67,.45);color:#ff9aa1;background:rgba(234,57,67,.09)}
.chip.idle{color:var(--mut)}
.vd{border-radius:14px;padding:.8rem 1rem;margin:.3rem 0 .8rem;border:1px solid var(--line)}
.vd b{font-size:1rem}.vd span{display:block;color:#c3cbe0;font-size:.82rem;margin-top:.15rem}
.vd.green{background:rgba(22,199,132,.12);border-color:rgba(22,199,132,.45)}
.vd.amber{background:rgba(245,166,35,.11);border-color:rgba(245,166,35,.45)}
.vd.red{background:rgba(234,57,67,.11);border-color:rgba(234,57,67,.45)}
.vd.gray{background:rgba(138,148,173,.10)}
.sec{font-size:.78rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.1em;margin:1rem 0 .3rem}
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

if "journal" not in st.session_state:
  st.session_state["journal"] = load_journal_data()

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
with st.sidebar:
  st.markdown("### ⚙️ Settings")
  interval = st.selectbox("Candle size", list(INTERVALS), index=1)
  mins = INTERVALS[interval][1]
  horizon = st.selectbox("Expiry (candles)", [1, 2, 3], index=0)
  st.caption(f"Expiry on Quotex: **{horizon * mins} min**")

  payout_pct = st.slider("Broker payout %", 70, 95, 85)
  payout = payout_pct / 100
  be_rate = 1 / (1 + payout)
  st.caption(f"Break-even win rate: **{be_rate * 100:.1f}%**")

  tz = st.selectbox("Your timezone", TIMEZONES, index=0)
  auto_refresh = st.checkbox("Auto-refresh every 30s", value=True)
  enable_sound = st.checkbox("Enable signal audio alert", value=True)

  st.markdown("### 🎯 Filters")
  h0, h1 = st.slider("Trading session (UTC hours)", 0, 24, (7, 20))
  min_conf = st.slider("Minimum confluence (0-6)", 0, 6, 2)
  use_htf = st.checkbox("Higher-timeframe trend must agree", value=True)
  require_valid = st.checkbox("Only signal validated setups", value=True)
  strict = st.checkbox("Strict validation (95% proof)", value=False)
  one_at_a_time = st.checkbox("One trade at a time", value=True)

  with st.expander("Advanced"):
    adx_trend = st.slider("ADX = trending above", 15, 35, 22)
    adx_range = st.slider("ADX = ranging below", 10, 25, 20)

  st.markdown("### 🛡️ Risk Guard & Kelly")
  balance = st.number_input("Balance", min_value=0.0, value=100.0, step=10.0)
  stake_pct = st.slider("Stake % of balance", 0.5, 5.0, 1.0, 0.5)
  max_consec = st.slider("Stop after N losses in a row", 1, 5, 2)
  max_loss_units = st.slider("Daily loss limit (stakes)", 1, 10, 3)

params = {
    "h0": h0,
    "h1": h1,
    "min_conf": min_conf,
    "adx_trend": adx_trend,
    "adx_range": adx_range,
    "use_htf": use_htf,
}

# ============================================================
# DATA EXECUTION
# ============================================================
try:
  raw = fetch_candles(interval)
except Exception as err:
  st.markdown(
      "<div class='hero'><div><div class='t'>EUR/USD Signal Pro"
      " Advanced</div></div></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<div class='sig stop'><div class='big'>⛔ NO DATA</div><div"
      " class='sub'>Could not reach price feed.</div></div>",
      unsafe_allow_html=True,
  )
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
  validated = {
      k: (v["decided"] >= 30 and v["lo"] > v["be"]) for k, v in by_setup.items()
  }
else:
  validated = {
      k: (v["decided"] >= 20 and v["ev"] > 0) for k, v in by_setup.items()
  }

now = pd.Timestamp.now(tz="UTC")
delta = pd.Timedelta(minutes=mins)
last_bar = x["time"].iloc[-1]
idx = len(x) - 1 if now >= last_bar + delta else len(x) - 2
row = x.iloc[idx]
entry_time = row["time"] + delta
age_s = (now - entry_time).total_seconds()
mkt_open, opens_at = market_state(now)
feed_stale = mkt_open and (now - last_bar) > max(
    pd.Timedelta(minutes=15), 3 * delta
)
window_s = max(20, int(mins * 60 * 0.3))
regime = regime_label(row, params)
secs_left = max(
    0, int((now.floor(f"{mins}min") + delta - now).total_seconds())
)


def fmt(t):
  return t.tz_convert(tz).strftime("%a %d %b, %H:%M")


kelly_f = 0.0
if overall and overall["wr"] > 0:
  kelly_f = kelly_fraction(overall["wr"], payout)

# ============================================================
# STATUS BAR
# ============================================================
if not mkt_open:
  status_html = "<span class='pill'><span class='dot a'></span>MARKET CLOSED</span>"
elif feed_stale:
  status_html = "<span class='pill'><span class='dot r'></span>FEED STALE</span>"
else:
  status_html = "<span class='pill'><span class='dot g'></span>LIVE</span>"

status_html += (
    f"<span class='pill'>EUR/USD • {interval}</span><span class='pill'>🕒"
    f" {now.tz_convert(tz).strftime('%H:%M')} {tz.split('/')[-1]}</span>"
)
if mkt_open and not feed_stale:
  status_html += f"<span class='pill'>⏱ Next Candle {secs_left//60}:{secs_left%60:02d}</span>"

st.markdown(
    "<div class='hero'><div><div class='t'>EUR/USD Signal Pro"
    " Advanced</div><div class='s'>AI Binary Trading Terminal with MACD &"
    " Stoch</div></div></div>"
    f"<div class='status'>{status_html}</div>",
    unsafe_allow_html=True,
)

if st.button("🔄 Refresh live data", use_container_width=True):
  st.cache_data.clear()
  st.rerun()

tab_sig, tab_bt, tab_j, tab_guide = st.tabs(
    ["📡 Signal", "📈 Backtest", "📒 Journal", "ℹ️ Guide"]
)

# ================= SIGNAL TAB =================
with tab_sig:
  htf_txt = {1.0: "UP", -1.0: "DOWN"}.get(row["htf"], "—")
  htf_tone = {"UP": "g", "DOWN": "r"}.get(htf_txt, "")
  reg_tone = {
      "UPTREND": "g",
      "DOWNTREND": "r",
      "RANGING": "b",
      "TRANSITION": "a",
  }.get(regime, "")

  st.markdown(
      grid([
          tile("Price", f"{row['close']:.5f}"),
          tile("Regime", regime.title(), "", reg_tone),
          tile(
              "Higher TF",
              htf_txt,
              f"{HTF_MINUTES.get(mins, 15)}m trend",
              htf_tone,
          ),
          tile(
              "MACD Hist",
              f"{row['macd_hist']:.5f}" if pd.notna(row["macd_hist"]) else "—",
              "momentum",
          ),
          tile(
              "Stoch %K",
              f"{row['stoch_k']:.0f}" if pd.notna(row["stoch_k"]) else "—",
              "oscillator",
          ),
          tile(
              "RSI",
              f"{row['rsi']:.0f}" if pd.notna(row["rsi"]) else "—",
              "14",
          ),
      ]),
      unsafe_allow_html=True,
  )

  today = now.tz_convert(tz).strftime("%Y-%m-%d")
  stopped, stop_msg, today_pnl = guard_status(
      st.session_state["journal"], today, max_consec, max_loss_units
  )

  side = int(sig["side"].iloc[idx])
  setup = sig["setup"].iloc[idx]
  conf = int(sig["conf"].iloc[idx])
  badge, meter = "", ""

  if not mkt_open:
    card, big = "stop", "🌙 MARKET CLOSED"
    sub = f"Forex reopens around <b>{fmt(opens_at)}</b>."
    meta = "Weekend break."
  elif feed_stale:
    card, big = "stop", "⛔ NO DATA"
    sub = "Live feed delayed."
    meta = f"Last candle: {fmt(last_bar)}"
  elif stopped:
    card, big = "stop", "🛑 STOP TODAY"
    sub = f"Risk guard triggered: {stop_msg}."
    meta = "Protecting balance."
  elif side != 0 and age_s > window_s:
    card, big = "wait", "⌛ EXPIRED"
    sub = f"Signal expired ({int(age_s)}s old). Wait for next candle."
    meta = f"Setup was: {setup}"
  elif side != 0 and require_valid and not validated.get(setup, False):
    card, big = "wait", "NO TRADE"
    sub = f"{setup} fired, but setup is not backtest-validated."
    meta = "Skipped to avoid unproven risk."
  elif side != 0:
    card = "up" if side == 1 else "down"
    big = "▲ UP" if side == 1 else "▼ DOWN"
    badge = setup
    sub = explain(row, setup, side, params)
    meta = f"Enter at {fmt(entry_time)} • expiry {horizon * mins}m"
    meter = (
        "<div class='meter'>"
        + "".join(f"<i class='{'on' if k < conf else ''}'></i>" for k in range(6))
        + "</div>"
    )

    if enable_sound:
      st.markdown(
          "<audio autoplay><source"
          " src='https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3'"
          " type='audio/mpeg'></audio>",
          unsafe_allow_html=True,
      )
  else:
    card, big = "wait", "NO TRADE"
    sub = why_no_trade(row, params)
    meta = f"Analysed candle closed {fmt(entry_time)}"

  badge_html = f"<div class='badge'>{badge}</div>" if badge else ""
  st.markdown(
      f"<div class='sig {card}'>{badge_html}<div class='big'>{big}</div><div"
      f" class='sub'>{sub}</div>{meter}<div class='meta'>{meta}</div></div>",
      unsafe_allow_html=True,
  )

  if card in ("up", "down") and overall:
    rec_stake = balance * min(stake_pct / 100, kelly_f if kelly_f > 0 else 0.02)
    st.info(
        f"💡 **Smart Sizing Advice:** Suggested Stake based on Kelly Criterion:"
        f" **{rec_stake:.2f}** (Kelly Fraction: {kelly_f*100:.1f}%)"
    )

  st.markdown("### Safety & Technical Confluence Checks")
  vol_ok = pd.notna(row["atr_med"]) and 0.6 <= row["atr"] / row["atr_med"] <= 2.0
  st.markdown(
      chips([
          ("Market open", mkt_open),
          ("Fresh data", (not feed_stale) if mkt_open else None),
          ("In session", h0 <= row["hour"] < h1),
          ("Normal volatility", bool(vol_ok)),
          ("Clear regime", regime in ("UPTREND", "DOWNTREND", "RANGING")),
          ("Risk guard", not stopped),
      ]),
      unsafe_allow_html=True,
  )

  st.markdown("### Live Candle Chart")
  st.altair_chart(candle_chart(x, tz), use_container_width=True, theme=None)
  st.caption(
      f"🟠 EMA21 | 🔵 EMA50 | MACD Histogram & Stochastic %K Filters Active"
  )

# ================= BACKTEST TAB =================
with tab_bt:
  st.caption(
      f"{len(x):,} candles analyzed | Payout: {payout_pct}% | Break-even:"
      f" {be_rate*100:.1f}%"
  )
  if overall is None:
    st.info("No trades matched current filter criteria.")
  else:
    colr, title, note = verdict(overall)
    st.markdown(
        f"<div class='vd {colr}'><b>{title}</b><span>{note}</span></div>",
        unsafe_allow_html=True,
    )
    edge = (overall["wr"] - overall["be"]) * 100
    st.markdown(
        grid([
            tile(
                "Total Trades",
                overall["n"],
                f"{overall['wins']}W / {overall['losses']}L",
            ),
            tile(
                "Win Rate",
                f"{overall['wr']*100:.1f}%",
                f"{edge:+.1f}% vs BE",
                "g" if edge > 0 else "r",
            ),
            tile(
                "EV / Trade",
                f"{overall['ev']:+.3f}",
                "units",
                "g" if overall["ev"] > 0 else "r",
            ),
            tile(
                "Net P&L",
                f"{overall['net']:+.1f}",
                "stakes",
                "g" if overall["net"] > 0 else "r",
            ),
            tile("Max Drawdown", f"{overall['dd']:.1f}", "stakes", "a"),
            tile("Max Loss Streak", overall["streak"], "trades", "a"),
        ]),
        unsafe_allow_html=True,
    )

  st.markdown("### Setup Breakdown")
  rows = [
      {
          "Setup": name,
          "Trades": s["decided"],
          "Win %": round(s["wr"] * 100, 1),
          "EV/trade": round(s["ev"], 3),
          "95% Low": round(s["lo"] * 100, 1),
          "Validated": "✅" if validated[name] else "❌",
      }
      for name, s in by_setup.items()
  ]
  if rows:
    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True
    )

  st.markdown("### Equity Curve")
  if overall is not None:
    st.altair_chart(
        equity_chart(overall["equity"]), use_container_width=True, theme=None
    )
    csv = overall["tr"].to_csv(index=False).encode()
    st.download_button(
        "⬇ Download Backtest CSV",
        csv,
        "backtest_trades.csv",
        "text/csv",
        use_container_width=True,
    )

# ================= JOURNAL TAB =================
with tab_j:
  st.markdown(
      "**Persistent Journal:** Your logged trades are automatically saved locally"
      " (`trading_journal.json`)."
  )
  jc1, jc2, jc3 = st.columns(3)
  j_side = jc1.selectbox("Side", ["UP", "DOWN"])
  j_res = jc2.selectbox("Result", ["WIN", "LOSS", "TIE"])
  jc3.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)

  if jc3.button("➕ Add Entry", use_container_width=True):
    pnl = {"WIN": payout, "LOSS": -1.0, "TIE": 0.0}[j_res]
    st.session_state["journal"].append({
        "date": now.tz_convert(tz).strftime("%Y-%m-%d"),
        "time": now.tz_convert(tz).strftime("%H:%M"),
        "side": j_side,
        "result": j_res,
        "pnl": pnl,
    })
    save_journal_data(st.session_state["journal"])
    st.rerun()

  jr = st.session_state["journal"]
  if jr:
    jdf = pd.DataFrame(jr)
    w = int((jdf["result"] == "WIN").sum())
    l_ = int((jdf["result"] == "LOSS").sum())
    net = float(jdf["pnl"].sum())
    st.markdown(
        grid([
            tile("Logged Trades", len(jdf)),
            tile("Win Rate", f"{w/(w+l_)*100:.0f}%" if (w + l_) else "—"),
            tile(
                "Net P&L",
                f"{net:+.1f}",
                "stakes",
                "g" if net > 0 else ("r" if net < 0 else ""),
            ),
        ]),
        unsafe_allow_html=True,
    )
    st.dataframe(jdf.iloc[::-1], use_container_width=True, hide_index=True)
    if st.button("🗑️ Clear Journal Database"):
      st.session_state["journal"] = []
      if os.path.exists(JOURNAL_FILE):
        os.remove(JOURNAL_FILE)
      st.rerun()
  else:
    st.info("No trades logged yet.")

# ================= GUIDE TAB =================
with tab_guide:
  st.markdown("""
**New Technical Filters Added:**
- **MACD Filter:** Trend pullbacks now require MACD histogram agreement (positive for UP, negative for DOWN) to ensure proper momentum.
- **Stochastic Oscillator:** Range reversals now look for Stochastic %K crossing below 20 (for UP) or above 80 (for DOWN) at the Bollinger extremes.
- **Persistent Storage & Audio:** Fully configured for seamless GitHub deployment and live browser notifications.
""")

st.markdown(
    "<div"
    " style='text-align:center;color:#5d6882;font-size:.72rem;margin-top:1.5rem'>"
    "EUR/USD Signal Pro Advanced • GitHub Ready</div>",
    unsafe_allow_html=True,
)

if auto_refresh and mkt_open and hasattr(st, "fragment"):

  @st.fragment(run_every=30)
  def _auto_tick():
    st.rerun()

  _auto_tick()
