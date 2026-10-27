"""
STAGE 1 — CONDITIONAL STATE ENUMERATION.

The question: does the direction sequence of the first N 5-minute candles carry
information about the excursion of the next M candles?

DESIGN, fixed before any result was seen:

  base            5m bars built from M1, UTC
  observation     n_obs candles, classified bullish (close>open) / bearish
  prediction      n_pred candles
  windows         ANCHORED and NON-OVERLAPPING - consecutive windows share no candles,
                  so observations are independent. Rolling windows would inflate every
                  significance test because neighbouring samples share bars.
  entry           OPEN of the first prediction candle (the user's Definition A).
                  Everything used to form the state is closed before entry.
  barriers        +/- 1 x ATR14(5m) measured at the LAST OBSERVATION CANDLE (causal).
                  Scale-free and cross-instrument comparable; ~10 pips on these
                  instruments, but a fixed pip target is 44% cost on US500 and is not
                  comparable across instruments.
  resolution      M1 inside the prediction window decides which barrier came FIRST.
                  If both are touched inside the same M1 bar the STOP is taken
                  (adverse-first, worst case). Those are counted and reported.
  null            symmetric barriers -> P(up first) = 50% under a driftless walk.
                  Reported against 50%, two-sided.

MULTIPLICITY: ~288 state-cells in Stage 1. The expected maximum |z| across 288 cells
under the pure null is ~3.2. A cell at |z| = 2 is the MODAL outcome of a search this
size and means nothing on its own.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from data import load_m1, to_m5     # noqa: E402

INSTR = ["XAUUSD", "USTEC", "US30", "US500"]
RESULTS = HERE.parent / "results"
CONFIGS = [(2, 1), (3, 1), (2, 2), (3, 2), (2, 3)]      # (n_obs, n_pred)
BAR = "=" * 112


def prep(sym):
    m1 = load_m1(sym)
    return m1, to_m5(m1)


def outcomes(m1, m5, n_pred):
    """For every 5m bar k as ENTRY: which barrier is hit first over n_pred candles.

    Returns arrays aligned to m5: res (+1 up-first, -1 down-first, 0 neither),
    mfe, mae in ATR units, and an ambiguity flag (both inside one M1 bar).
    """
    m1i = m1.index
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    o5 = m5["open"].to_numpy(float)
    atr = m5["atr"].to_numpy(float)
    idx5 = m5.index
    starts = m1i.searchsorted(idx5)
    ends = m1i.searchsorted(idx5 + pd.Timedelta(minutes=5 * n_pred))
    n = len(m5)
    res = np.zeros(n, dtype=np.int8)
    mfe = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    amb = np.zeros(n, dtype=bool)
    for k in range(n):
        a, b = starts[k], ends[k]
        if b <= a or not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        e = o5[k]
        up, dn = e + atr[k], e - atr[k]
        seg_h, seg_l = mh[a:b], ml[a:b]
        mfe[k] = (seg_h.max() - e) / atr[k]
        mae[k] = (e - seg_l.min()) / atr[k]
        hu = np.flatnonzero(seg_h >= up)
        hd = np.flatnonzero(seg_l <= dn)
        tu = hu[0] if len(hu) else 10 ** 9
        td = hd[0] if len(hd) else 10 ** 9
        if tu == 10 ** 9 and td == 10 ** 9:
            res[k] = 0
        elif tu == td:                      # same M1 bar - order unknowable
            amb[k] = True
            res[k] = -1                     # adverse-first, worst case
        elif tu < td:
            res[k] = 1
        else:
            res[k] = -1
    return res, mfe, mae, amb


def run():
    rows = []
    for sym in INSTR:
        m1, m5 = prep(sym)
        o, c = m5["open"].to_numpy(float), m5["close"].to_numpy(float)
        bull = (c > o).astype(np.int8)
        n = len(m5)
        print(f"  {sym}: {n:,} 5m bars  {m5.index.min().date()} -> {m5.index.max().date()}",
              flush=True)
        cache = {}
        for n_obs, n_pred in CONFIGS:
            if n_pred not in cache:
                cache[n_pred] = outcomes(m1, m5, n_pred)
            res, mfe, mae, amb = cache[n_pred]
            step = n_obs + n_pred
            # ANCHORED, NON-OVERLAPPING: window starts every `step` bars
            starts = np.arange(0, n - step - 1, step)
            starts = starts[starts >= 20]
            ent = starts + n_obs                       # entry candle index
            ok = (ent < n) & np.isfinite(mfe[ent])
            starts, ent = starts[ok], ent[ok]
            # state string from the n_obs observation candles
            st = np.zeros(len(starts), dtype=object)
            for j in range(n_obs):
                bit = np.where(bull[starts + j] == 1, "B", "S")
                st = st + bit if j else bit
            r = res[ent]
            for state in sorted(set(st)):
                m = st == state
                dec = m & (r != 0)
                nd = int(dec.sum())
                if nd < 200:
                    continue
                w = int((r[dec] == 1).sum())
                p = sps.binomtest(w, nd, 0.5).pvalue
                z = (w - nd * 0.5) / np.sqrt(nd * 0.25)
                rows.append(dict(sym=sym, n_obs=n_obs, n_pred=n_pred, state=state,
                                 n_win=int(m.sum()), n_dec=nd, up_first=100 * w / nd,
                                 z=z, p=p, mfe=np.nanmedian(mfe[ent][m]),
                                 mae=np.nanmedian(mae[ent][m]),
                                 amb=100 * amb[ent][m].mean(),
                                 undec=100 * (1 - nd / max(int(m.sum()), 1))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(BAR)
    print("  STAGE 1 — anchored non-overlapping windows, +/-1 ATR barriers, M1 ordering")
    print(BAR)
    df = run()
    df.to_csv(RESULTS / "stage1_results.csv", index=False)
    print(f"\n  {len(df)} state-cells with n_dec >= 200. Expected max |z| under the null")
    print(f"  across {len(df)} cells is ~{sps.norm.ppf(1 - 0.5 / len(df)):.2f}.")
    print(f"\n{BAR}\n  THE FULL LANDSCAPE — every cell, sorted by |z|\n{BAR}")
    print(f"  {'sym':<8}{'obs':>4}{'pred':>5}{'state':>7}{'n_dec':>8}{'up first':>10}"
          f"{'z':>8}{'p':>9}{'MFE':>7}{'MAE':>7}{'MFE/MAE':>9}{'ambig%':>8}")
    d = df.reindex(df.z.abs().sort_values(ascending=False).index)
    for _, r in d.head(18).iterrows():
        print(f"  {r['sym']:<8}{r['n_obs']:>4}{r['n_pred']:>5}{r['state']:>7}"
              f"{r['n_dec']:>8}{r['up_first']:>9.2f}%{r['z']:>8.2f}{r['p']:>9.4f}"
              f"{r['mfe']:>7.2f}{r['mae']:>7.2f}{r['mfe']/max(r['mae'],1e-9):>9.2f}"
              f"{r['amb']:>7.1f}%")
    print(f"\n  |z| distribution: max {df.z.abs().max():.2f}  "
          f"p99 {df.z.abs().quantile(.99):.2f}  median {df.z.abs().median():.2f}")
    print(f"  cells with |z| > 3.2 (the multiplicity bar): "
          f"{int((df.z.abs() > 3.2).sum())} of {len(df)}")
    print(f"  cells with p < 0.05 uncorrected: {int((df.p < 0.05).sum())} "
          f"({100*(df.p < 0.05).mean():.1f}%) — expected by chance: 5.0%")
    print(f"\n  MFE/MAE across all cells: median "
          f"{(df.mfe/df.mae).median():.3f}  min {(df.mfe/df.mae).min():.3f}  "
          f"max {(df.mfe/df.mae).max():.3f}")
    print(f"  median ambiguous (both barriers in one M1 bar): {df.amb.median():.1f}%")
