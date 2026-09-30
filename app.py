import math
import numpy as np
import pandas as pd
import streamlit as st

PIP = 0.0001
TIME_COLS = ["datetime", "time", "timestamp", "date", "gmt time", "local time"]
TRADE_COLS = [
    "signal_idx", "entry_idx", "exit_idx", "time", "dir", "entry",
    "exit", "gross_pips", "net_pips", "outcome", "binary_profit",
]

st.set_page_config(page_title="EUR/USD Live Signal Bot", page_icon="📊", layout="centered")
st.title("📊 EUR/USD LIVE MARKET SIGNAL BOT")
st.caption("Strictly for Live Market Analysis | OTC Blocked")

st.markdown(
    """
<style>  
.signal {padding:20px;border-radius:12px;text-align:center;  
         font-size:28px;font-weight:bold;margin:12px 0;}  
.up {background:#d4edda;color:#155724;}  
.down {background:#f8d7da;color:#721c24;}  
.no {background:#fff3cd;color:#856404;}  
</style>  """,
    unsafe_allow_html=True,
)

# ---------------- SETTINGS ----------------

st.sidebar.header("⚙️ Strategy & Market Filter")
block_otc = st.sidebar.checkbox("🚫 Block OTC Markets Strictly", value=True)
only_weekday = st.sidebar.checkbox("📅 Trade Weekdays Only (Mon-Fri)", value=True)

n_candles = st.sidebar.slider("Same-colour candles in a row", 2, 8, 4)
body_mult = st.sidebar.slider("Body ≥ x ATR", 0.5, 3.0, 1.5, 0.1)
loc_min = st.sidebar.slider("Close location threshold (%)", 60, 99, 85) / 100
atr_mult = st.sidebar.slider("ATR > x × median ATR", 0.5, 3.0, 1.2, 0.1)
atr_period = int(st.sidebar.number_input("ATR period", 5, 50, 14))
lookback = int(st.sidebar.number_input("Median ATR lookback", 20, 300, 100))

st.sidebar.header("🧪 Backtest / Binary")
horizon = st.sidebar.slider("Exit after N candles", 1, 6, 1)
spread = st.sidebar.number_input("Estimated cost (pips per trade)", 0.0, 5.0, 0.8, 0.1)
payout_pct = st.sidebar.number_input("Binary payout (%)", 50, 100, 85)
stake = st.sidebar.number_input("Binary stake per signal", 1.0, 10000.0, 100.0, 1.0)
one_at_a_time = st.sidebar.checkbox("One trade at a time", value=True)
holdout_pct = st.sidebar.slider("Holdout (untouched test) %", 10, 50, 30)
drop_last = st.sidebar.checkbox("Ignore last candle (if still forming)", value=True)

uploaded = st.file_uploader("📂 Upload EUR/USD 5m candle CSV (Live Market Only)", type=["csv"])

# ---------------- HELPERS ----------------

def fmt(value, decimals=1):
    return "-" if pd.isna(value) else f"{value:.{decimals}f}"

def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center - margin) / d * 100, (center + margin) / d * 100

def p_value_above(k, n, p0):
    if n == 0:
        return np.nan
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return np.nan
    z = (k / n - p0) / se
    return 0.5 * math.erfc(z / math.sqrt(2))

def show_table(data):
    try:
        st.dataframe(data, width="stretch")
    except TypeError:
        st.dataframe(data, use_container_width=True)

# ---------------- DATA & MARKET CHECK ----------------

def prepare(raw, file_name=""):
    df = raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    if block_otc:
        if "otc" in file_name.lower():
            raise ValueError("❌ OTC Market detected! This bot is configured for LIVE MARKET ONLY.")

    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)

    notes = []
    time_col = next((c for c in TIME_COLS if c in df.columns), None)

    if time_col:
        df["time"] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time")
        
        if only_weekday:
            is_weekend = df["time"].dt.dayofweek >= 5  # 5=Saturday, 6=Sunday
            if is_weekend.any():
                notes.append("⚠️ Weekend candles detected. Live forex market is closed on weekends.")
                if block_otc:
                    df = df.loc[~is_weekend].reset_index(drop=True)
                    notes.append("🔒 Weekend/OTC rows have been filtered out automatically.")

        before = len(df)
        df = df.drop_duplicates("time", keep="last")
        if len(df) < before:
            notes.append(f"Removed {before - len(df)} duplicate timestamps.")
    else:
        if block_otc:
            raise ValueError("❌ No timestamp column found. Cannot verify if data is Live or OTC.")
        df["time"] = np.arange(len(df))
        notes.append("⚠️ No time column. Assuming rows are oldest to newest.")

    bad = (
        (df["high"] < df["low"])
        | (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
    )
    if bad.any():
        notes.append(f"Removed {int(bad.sum())} invalid candles.")
    df = df.loc[~bad].reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid live candles remain after filtering.")
    return df, notes

def get_step(df):
    if pd.api.types.is_datetime64_any_dtype(df["time"]):
        gaps = df["time"].diff().dropna()
        if gaps.empty:
            return None
        step = gaps.median()
        if step <= pd.Timedelta(0):
            return None
        return step
    return None

# ---------------- INDICATORS ----------------

def add_indicators(data, step):
    df = data.copy()
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["atr"] = tr.rolling(atr_period, min_periods=atr_period).mean()
    df["median_atr"] = (
        df["atr"].shift(1).rolling(lookback, min_periods=lookback).median()
    )

    if step is not None:
        is_gap = df["time"].diff() > step * 1.5
    else:
        is_gap = pd.Series(False, index=df.index)
    df["is_gap"] = is_gap.fillna(False)

    win = max(atr_period, n_candles, 2)
    df["recent_gap"] = (
        df["is_gap"].astype(int).rolling(win, min_periods=1).max().astype(bool)
    )

    bull = df["close"] > df["open"]
    bear = df["close"] < df["open"]
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    close_loc = (df["close"] - df["low"]) / rng
    body = (df["close"] - df["open"]).abs()

    df["run_bull"] = bull.rolling(n_candles, min_periods=n_candles).sum() == n_candles
    df["run_bear"] = bear.rolling(n_candles, min_periods=n_candles).sum() == n_candles
    df["body_ok"] = body >= body_mult * df["atr"]
    df["loc_top"] = close_loc >= loc_min
    df["loc_bottom"] = close_loc <= (1 - loc_min)
    df["vol_ok"] = df["atr"] > atr_mult * df["median_atr"]

    clean = ~df["recent_gap"]
    down = df["run_bull"] & df["body_ok"] & df["loc_top"] & df["vol_ok"] & clean
    up = df["run_bear"] & df["body_ok"] & df["loc_bottom"] & df["vol_ok"] & clean

    df["dir"] = np.select([down, up], [-1, 1], default=0).astype(int)
    return df

# ---------------- TRADES ----------------

def interval_has_gap(df, start, end, step):
    if step is None:
        return False
    times = df["time"].iloc[start:end + 1]
    if len(times) <= 1:
        return False
    diffs = times.diff().dropna()
    return bool((diffs > step * 1.5).any() or (diffs <= pd.Timedelta(0)).any())

def build_all_trades(df, step):
    rows = []
    skipped_gap = 0
    for i in np.flatnonzero(df["dir"].to_numpy() != 0):
        i = int(i)
        direction = int(df.at[i, "dir"])
        entry_idx = i + 1
        exit_idx = i + horizon
        if exit_idx >= len(df):
            continue
        if interval_has_gap(df, i, exit_idx, step):
            skipped_gap += 1
            continue

        entry = float(df.at[entry_idx, "open"])
        exit_price = float(df.at[exit_idx, "close"])
        gross = direction * (exit_price - entry) / PIP

        if gross > 0:
            outcome, binary_profit = "WIN", stake * payout_pct / 100
        elif gross < 0:
            outcome, binary_profit = "LOSS", -stake
        else:
            outcome, binary_profit = "TIE", 0.0

        rows.append({
            "signal_idx": i,
            "entry_idx": entry_idx,
            "exit_idx": exit_idx,
            "time": df.at[i, "time"],
            "dir": direction,
            "entry": entry,
            "exit": exit_price,
            "gross_pips": gross,
            "net_pips": gross - spread,
            "outcome": outcome,
            "binary_profit": binary_profit,
        })
    return pd.DataFrame(rows, columns=TRADE_COLS), skipped_gap

def apply_non_overlap(trades):
    if trades.empty or not one_at_a_time:
        return trades.copy(), 0
    keep_idx, next_entry_allowed = [], -1
    for idx, entry_idx, exit_idx in zip(
        trades.index, trades["entry_idx"], trades["exit_idx"]
    ):
        if entry_idx >= next_entry_allowed:
            keep_idx.append(idx)
            next_entry_allowed = exit_idx + 1
    result = trades.loc[keep_idx].reset_index(drop=True)
    return result, len(trades) - len(result)

# ---------------- STATS ----------------

def compute_stats(trades):
    if trades.empty:
        return None
    t = trades
    wins = int((t["outcome"] == "WIN").sum())
    losses = int((t["outcome"] == "LOSS").sum())
    ties = int((t["outcome"] == "TIE").sum())
    settled = wins + losses

    breakeven = 100 / (1 + payout_pct / 100)
    low, high = wilson(wins, settled)
    p_value = p_value_above(wins, settled, breakeven / 100)

    cumulative = t["net_pips"].cumsum()
    drawdown = cumulative - cumulative.cummax()
    gains = t.loc[t["net_pips"] > 0, "net_pips"].sum()
    losses_pips = -t.loc[t["net_pips"] < 0, "net_pips"].sum()

    def directional_wr(direction):
        sub = t[t["dir"] == direction]
        w = int((sub["outcome"] == "WIN").sum())
        l = int((sub["outcome"] == "LOSS").sum())
        return w / (w + l) * 100 if w + l else np.nan

    return {
        "trades": len(t),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "settled": settled,
        "win_rate": wins / settled * 100 if settled else np.nan,
        "ci_low": low,
        "ci_high": high,
        "p_value": p_value,
        "breakeven": breakeven,
        "avg_gross": t["gross_pips"].mean(),
        "avg_net": t["net_pips"].mean(),
        "total_net": t["net_pips"].sum(),
        "pf": gains / losses_pips if losses_pips > 0 else np.inf,
        "max_dd": abs(drawdown.min()),
        "binary_total": t["binary_profit"].sum(),
        "binary_roi": t["binary_profit"].sum() / (stake * len(t)) * 100,
        "down_n": int((t["dir"] == -1).sum()),
        "up_n": int((t["dir"] == 1).sum()),
        "down_wr": directional_wr(-1),
        "up_wr": directional_wr(1),
    }

def show_stats(stats, trades):
    if stats is None:
        st.info("No completed signals in this section.")
        return
    a, b, c = st.columns(3)
    a.metric("Signals", stats["trades"])
    b.metric("Win Rate", f"{fmt(stats['win_rate'])}%")
    c.metric("Profit Factor", fmt(stats["pf"], 2))

    a, b, c = st.columns(3)
    a.metric("Avg Net Pips", fmt(stats["avg_net"], 2))
    b.metric("Total Net Pips", fmt(stats["total_net"], 1))
    c.metric("Max Drawdown", fmt(stats["max_dd"], 1))

    a, b, c = st.columns(3)
    a.metric("Binary P/L", fmt(stats["binary_total"], 2))
    b.metric("Binary ROI", f"{fmt(stats['binary_roi'], 2)}%")
    c.metric("Ties", stats["ties"])

    st.write(f"**95% confidence range of win rate:** {fmt(stats['ci_low'])}% – {fmt(stats['ci_high'])}%")
    st.write(f"**Binary break-even:** {stats['breakeven']:.2f}%")
    st.write(f"🔴 DOWN: {stats['down_n']} signals, {fmt(stats['down_wr'])}% win")
    st.write(f"🟢 UP: {stats['up_n']} signals, {fmt(stats['up_wr'])}% win")
    st.line_chart(trades["net_pips"].cumsum().reset_index(drop=True))

def verdict(stats):
    if stats is None:
        st.info("Holdout has no completed trades.")
        return
    if stats["settled"] < 100:
        st.warning(f"Holdout has only {stats['settled']} settled trades. Need more data.")
    elif stats["ci_low"] > stats["breakeven"]:
        st.success("Holdout: Win-rate range is above break-even (Live Market Verified).")
    else:
        st.error("Holdout does not establish a reliable edge.")

# ---------------- APP MAIN EXECUTION ----------------

if uploaded is None:
    st.info("Upload a Live EUR/USD 5-minute CSV file (Ensure it is NOT from OTC market).")
    st.stop()

try:
    df, notes = prepare(pd.read_csv(uploaded), uploaded.name)
except Exception as exc:
    st.error(f"{exc}")
    st.stop()

for note in notes:
    st.warning(note)

if drop_last:
    if len(df) > 1:
        df = df.iloc[:-1].reset_index(drop=True)
    else:
        st.error("Not enough rows.")
        st.stop()

min_rows = lookback + atr_period + n_candles + horizon + 50
if len(df) < min_rows:
    st.error(f"Need at least {min_rows} candles; found {len(df)}.")
    st.stop()

step = get_step(df)
df = add_indicators(df, step)
last = df.iloc[-1]

st.markdown(f"### 💱 EUR/USD Live Market | ⏱️️ 5m | 🕒 {last['time']}")

if pd.isna(last["atr"]) or pd.isna(last["median_atr"]):
    st.warning("Indicator data incomplete: NO TRADE.")
    st.stop()

if last["dir"] == -1:
    st.markdown('<div class="signal down">🔴 LIVE DOWN SETUP</div>', unsafe_allow_html=True)
elif last["dir"] == 1:
    st.markdown('<div class="signal up">🟢 LIVE UP SETUP</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="signal no">🛑 NO TRADE (Live Market Filter Active)</div>', unsafe_allow_html=True)

# ---------------- BACKTEST ----------------
st.subheader("🧪 Live Market Backtest Performance")
all_trades, skipped_gap = build_all_trades(df, step)
split_idx = int(len(df) * (1 - holdout_pct / 100))

train_raw = all_trades[(all_trades["signal_idx"] < split_idx) & (all_trades["exit_idx"] < split_idx)]
test_raw = all_trades[all_trades["signal_idx"] >= split_idx]

train, _ = apply_non_overlap(train_raw)
test, _ = apply_non_overlap(test_raw)

train_stats = compute_stats(train)
test_stats = compute_stats(test)

verdict(test_stats)

tab_test, tab_train = st.tabs(["🎯 Holdout Test", "🏋️ Tuning Data"])
with tab_test:
    show_stats(test_stats, test)
with tab_train:
    show_stats(train_stats, train)
