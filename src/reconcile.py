"""
RECONCILING STAGE 1 WITH STAGE 2.

Stage 1 (5-minute prediction window, 70-77% undecided) said BB -> UP-first, +2.3pp.
Stage 2 (24-hour window, 0.6% undecided) says BB -> DOWN-first, -1.0pp.

Same entries, same states, same +/-1 ATR barriers, same M1 ordering. The ONLY
difference is how long the barrier is given to be touched. If Stage 1 was a
selection effect - a statement about the fast-resolving 26% and not about the
population - then bucketing Stage 2 by time-to-resolution must reproduce BOTH
signs: positive in the first bucket, negative in the rest.

This script is the one that decides the verdict, and it is three dozen lines. The
expensive part was being willing to run it.

It also measures median ATR14(5m) in basis points per instrument and writes it, with the
round-trip cost, to results/instrument_cost.csv - which is all `economics.py` needs, so the
economics table can be rebuilt by anyone without any market data at all.

Run:  python -I reconcile.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from data import load_m1, to_m5     # noqa: E402

RESULTS = HERE.parent / "results"

# Round-trip cost in basis points, per instrument. These are the programme's own measured
# figures for a 2-digit CFD feed, not a vendor's quoted spread. Change them to yours before
# reading anything into the economics table: see data/HOWTO.md.
INSTR = [("XAUUSD", 2.60), ("USTEC", 0.86), ("US30", 1.20), ("US500", 1.20)]

HORIZON, BIG = 288, 10 ** 9
BUCKETS = [("<= 5 min  (Stage 1's window)", 0, 5), ("5-30 min", 5, 30),
           ("30 min - 2 h", 30, 120), ("2 - 8 h", 120, 480), ("8 - 24 h", 480, 10 ** 9)]

out_lines: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    out_lines.append(s)


def main() -> None:
    say("=" * 104)
    say("  RECONCILIATION — is Stage 1's positive sign a selection effect?   "
        "(+/-1 ATR, M1 ordering)")
    say("=" * 104)
    costs = []
    for sym, rt_bp in INSTR:
        m1 = load_m1(sym)[["open", "high", "low", "close"]]
        m5 = to_m5(m1)
        o, atr = m5["open"].to_numpy(float), m5["atr"].to_numpy(float)
        n = len(m5)
        ent = np.arange(20, n - HORIZON - 2, 3)
        ent = ent[np.isfinite(atr[ent]) & (atr[ent] > 0)]
        ob, cb = m5["open"].to_numpy(float), m5["close"].to_numpy(float)
        b = np.where(cb > ob, "B", "S")
        st = np.char.add(b[ent - 2], b[ent - 1])
        mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
        a_all = m1.index.searchsorted(m5.index[ent])
        b_all = m1.index.searchsorted(m5.index[ent] + pd.Timedelta(minutes=5 * HORIZON))
        res = np.zeros(len(ent), np.int8)
        tim = np.full(len(ent), np.nan)
        for i in range(len(ent)):
            aa, bb = a_all[i], b_all[i]
            if bb - aa < 2:
                continue
            e, v = o[ent[i]], atr[ent[i]]
            sh = np.maximum.accumulate(mh[aa:bb])
            sl = np.minimum.accumulate(ml[aa:bb])
            ns = bb - aa
            iu = np.searchsorted(sh, e + v, "left")
            idn = np.searchsorted(-sl, -(e - v), "left")
            tu = iu if iu < ns else BIG
            td = idn if idn < ns else BIG
            if tu == BIG and td == BIG:
                continue
            res[i] = 1 if tu < td else -1
            tim[i] = min(tu, td)

        atr_bp = 1e4 * np.nanmedian(atr[ent] / o[ent])
        # 1 dp: this is a median basis-point figure and further digits are noise. It is
        # also what the study used, so the committed economics table is reproducible from it.
        costs.append({"sym": sym, "rt_bp": rt_bp, "atr_bp": round(float(atr_bp), 1)})
        say("")
        say(f"  {sym}   median ATR14(5m) = {atr_bp:.1f}bp   round trip {rt_bp:.2f}bp")
        say(f"    cost as % of R:  0.5 ATR stop -> {100*rt_bp/(0.5*atr_bp):.1f}%R "
            f"|  1 ATR -> {100*rt_bp/atr_bp:.1f}%R  |  3 ATR -> {100*rt_bp/(3*atr_bp):.1f}%R")
        say(f"    {'time to resolution':<30}{'n':>9}{'share':>8}{'uncond':>9}"
            f"{'BB exc':>9}{'SS exc':>9}{'BB-SS':>9}")
        for lab, lo, hi in BUCKETS:
            m = (res != 0) & (tim >= lo) & (tim < hi)
            if m.sum() < 500:
                continue
            y = (res[m] == 1).astype(float)
            s = st[m]
            pu = y.mean()
            bbx = (y[s == "BB"].mean() - pu) * 100
            ssx = (y[s == "SS"].mean() - pu) * 100
            say(f"    {lab:<30}{int(m.sum()):>9,}{100*m.mean():>7.1f}%{100*pu:>8.2f}%"
                f"{bbx:>+9.2f}{ssx:>+9.2f}{bbx-ssx:>+9.2f}")

    pd.DataFrame(costs).to_csv(RESULTS / "instrument_cost.csv", index=False)
    say("")
    say("  The first bucket is Stage 1's window, and it carries Stage 1's sign. It is also not")
    say("  selectable at entry: membership in it IS the outcome. That is the whole finding.")
    (RESULTS / "reconciliation.txt").write_text("\n".join(out_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
