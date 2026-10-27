"""
STAGE 2 — THE BARRIER CURVE.  Pre-registered; nothing below was chosen after seeing a result.

QUESTION: does the Stage-1 conditional ordering effect persist as the barrier widens,
or is it a 5-minute microstructure artifact?

FROZEN DESIGN

  entry        unchanged from Stage 1: OPEN of the candle after 2 closed observation
               candles, anchored NON-OVERLAPPING windows (step = 3 bars).
  states       FULL matrix BB / BS / SB / SS carried through every barrier. BB and SS
               are the primary hypothesis but nothing is dropped.
  barriers     +/- k x ATR14(5m), k in {0.5, 1, 1.5, 2, 3, 4, 5}, ATR taken at the last
               observation candle (causal).
  resolution   M1 bars decide which barrier came FIRST (the Stage-1 spec), over a
               FIXED 24-hour window for every k, so the curve isolates barrier size
               rather than confounding it with horizon. Undecided % reported per k.
               Adverse-first when both barriers fall in the same M1 bar.

               NOTE: the first run of this script resolved at 5-minute granularity for
               speed. That inflated same-bar double-touches to 7% at k=0.5, and because
               ties are forced adverse-first it manufactured a spurious "down-first
               after BB" effect whose size tracked the ambiguity rate exactly. Kept as
               stage2_results_5m_coarse.csv. Ambiguity is now reported PER STATE, and
               the separation is recomputed with ambiguous entries dropped.
  baseline     the UNCONDITIONAL up-first rate is computed per instrument per barrier.
               Every state is scored as excess = P(up|state) - P(up|unconditional).
  primary stat BB-SS separation: P(up|BB) - P(up|SS), and excess(BB) - excess(SS).
  inference    MOVING-BLOCK BOOTSTRAP over blocks of consecutive entries (non-overlap
               removes shared bars but not serial dependence in volatility regimes).
  null         PERMUTATION: state labels shuffled across entries, preserving both
               marginals and destroying only the state-outcome association.
  information  Brier score, log-loss and mutual information for the conditional model
               against the unconditional baseline.
  timing       median and IQR of time-to-barrier, to separate a persistent directional
               effect from a short-lived one.

NO STRATEGY IS BUILT. Output is a statistical map. Decision after Stage 2 is one of:
kill / investigate further / promote to Stage 3.
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

INSTR = ["XAUUSD", "USTEC", "US30", "US500"]
RESULTS = HERE.parent / "results"

KS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
HORIZON = 288          # 5m bars = 24 hours, same for every barrier
STATES = ["BB", "BS", "SB", "SS"]
BAR = "=" * 116
RNG = np.random.default_rng(20260910)


def prep(sym):
    m1 = load_m1(sym)
    return m1, to_m5(m1)


def resolve(m1, m5):
    """First-crossing outcome, time and ambiguity for every entry, at M1 granularity."""
    m1i = m1.index
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    o = m5["open"].to_numpy(float)
    atr = m5["atr"].to_numpy(float)
    idx5 = m5.index
    n = len(m5)
    step = 3
    ent = np.arange(20, n - HORIZON - 2, step)
    ent = ent[np.isfinite(atr[ent]) & (atr[ent] > 0)]
    a_all = m1i.searchsorted(idx5[ent])
    b_all = m1i.searchsorted(idx5[ent] + pd.Timedelta(minutes=5 * HORIZON))
    nres = len(ent)
    res = np.zeros((nres, len(KS)), dtype=np.int8)
    tim = np.full((nres, len(KS)), np.nan)
    amb = np.zeros((nres, len(KS)), dtype=bool)
    BIG = 10 ** 9
    for i in range(nres):
        a, b = a_all[i], b_all[i]
        if b - a < 2:
            continue
        e, v = o[ent[i]], atr[ent[i]]
        sh = np.maximum.accumulate(mh[a:b])
        sl = np.minimum.accumulate(ml[a:b])
        nseg = b - a
        for j, k in enumerate(KS):
            iu = np.searchsorted(sh, e + k * v, side="left")
            idn = np.searchsorted(-sl, -(e - k * v), side="left")
            tu = iu if iu < nseg else BIG
            td = idn if idn < nseg else BIG
            if tu == BIG and td == BIG:
                continue
            if tu == td:                     # same M1 bar - order unknowable
                amb[i, j] = True
                res[i, j] = -1               # adverse-first, worst case
                tim[i, j] = tu
            elif tu < td:
                res[i, j] = 1
                tim[i, j] = tu
            else:
                res[i, j] = -1
                tim[i, j] = td
    return ent, res, tim, amb


def states_of(m5, ent):
    o, c = m5["open"].to_numpy(float), m5["close"].to_numpy(float)
    b = np.where(c > o, "B", "S")
    return np.char.add(b[ent - 2], b[ent - 1])


def block_boot(y, nb=2000, block=64):
    """Moving-block bootstrap mean of a 0/1 array."""
    n = len(y)
    if n < block * 3:
        return np.nan, np.nan
    nblk = int(np.ceil(n / block))
    out = np.empty(nb)
    starts_pool = n - block
    for b in range(nb):
        s = RNG.integers(0, starts_pool, nblk)
        idx = (s[:, None] + np.arange(block)[None, :]).ravel()[:n]
        out[b] = y[idx].mean()
    return np.percentile(out, 2.5), np.percentile(out, 97.5)


def info_metrics(st, y, states, p_uncond):
    """Brier, log-loss and mutual information: conditional vs unconditional."""
    p_state = {s: y[st == s].mean() for s in states if (st == s).sum() > 0}
    pc = np.array([p_state.get(s, p_uncond) for s in st])
    pu = np.full(len(y), p_uncond)
    eps = 1e-12
    brier_c = np.mean((pc - y) ** 2)
    brier_u = np.mean((pu - y) ** 2)
    ll_c = -np.mean(y * np.log(pc + eps) + (1 - y) * np.log(1 - pc + eps))
    ll_u = -np.mean(y * np.log(pu + eps) + (1 - y) * np.log(1 - pu + eps))
    # mutual information I(state; outcome) in bits
    mi = 0.0
    for s in states:
        m = st == s
        ps = m.mean()
        if ps <= 0:
            continue
        for v in (0, 1):
            pj = np.mean(m & (y == v))
            pv = np.mean(y == v)
            if pj > 0 and pv > 0:
                mi += pj * np.log2(pj / (ps * pv))
    return brier_c, brier_u, ll_c, ll_u, mi


def main():
    print(BAR)
    print("  STAGE 2 — BARRIER CURVE.  Full state matrix, unconditional baseline,")
    print("  block bootstrap, permutation null, information metrics, time-to-barrier.")
    print(BAR)
    allrows = []
    for sym in INSTR:
        m1, m5 = prep(sym)
        ent, res, tim, amb = resolve(m1, m5)
        st = states_of(m5, ent)
        print(f"\n  {sym}  entries {len(ent):,}  "
              f"{m5.index[ent[0]].date()} -> {m5.index[ent[-1]].date()}", flush=True)
        print(f"  {'k(ATR)':>7}{'undec%':>8}{'amb%':>6}{'uncond':>8}"
              f"{'BB exc':>9}{'BS exc':>9}{'SB exc':>9}{'SS exc':>9}"
              f"{'BB-SS':>8}{'95% CI':>18}{'perm p95':>9}{'ambBB':>7}{'ambSS':>7}{'noTie':>8}{'medT':>6}")
        for j, k in enumerate(KS):
            r = res[:, j]
            dec = r != 0
            nd = int(dec.sum())
            if nd < 500:
                print(f"  {k:>7.1f}   too few decided")
                continue
            y = (r[dec] == 1).astype(float)
            s = st[dec]
            pu = y.mean()
            exc = {q: (y[s == q].mean() - pu) * 100 if (s == q).sum() > 30 else np.nan
                   for q in STATES}
            sep = (y[s == "BB"].mean() - y[s == "SS"].mean()) * 100
            # block bootstrap CI on the BB-SS separation
            ybb, yss = y[s == "BB"], y[s == "SS"]
            lo1, hi1 = block_boot(ybb)
            lo2, hi2 = block_boot(yss)
            ci = (100 * (lo1 - hi2), 100 * (hi1 - lo2))
            # permutation null on the separation
            perm = np.empty(600)
            for b in range(600):
                sp = RNG.permutation(s)
                perm[b] = (y[sp == "BB"].mean() - y[sp == "SS"].mean()) * 100
            p95 = np.percentile(np.abs(perm), 95)
            ad = amb[dec, j]
            amb_bb = 100 * ad[s == "BB"].mean()
            amb_ss = 100 * ad[s == "SS"].mean()
            cl = ~ad
            sep_cl = (y[cl & (s == "BB")].mean() - y[cl & (s == "SS")].mean()) * 100
            bc, bu, lc, lu, mi = info_metrics(s, y, STATES, pu)
            medt = np.nanmedian(tim[dec, j])          # M1 bars = minutes
            print(f"  {k:>7.1f}{100*(1-nd/len(r)):>7.1f}%{100*amb[:,j].mean():>5.1f}%"
                  f"{100*pu:>7.2f}%{exc['BB']:>+9.2f}{exc['BS']:>+9.2f}"
                  f"{exc['SB']:>+9.2f}{exc['SS']:>+9.2f}{sep:>+8.2f}"
                  f"  [{ci[0]:+.2f},{ci[1]:+.2f}]{p95:>9.2f}{amb_bb:>6.1f}%"
                  f"{amb_ss:>6.1f}%{sep_cl:>+8.2f}{medt:>6.0f}")
            allrows.append(dict(sym=sym, k=k, n_dec=nd, undec=100*(1-nd/len(r)),
                                uncond=100*pu, bb=exc["BB"], bs=exc["BS"],
                                sb=exc["SB"], ss=exc["SS"], sep=sep,
                                ci_lo=ci[0], ci_hi=ci[1], perm_p95=p95,
                                amb_bb=amb_bb, amb_ss=amb_ss, sep_noties=sep_cl,
                                brier_c=bc, brier_u=bu, ll_c=lc, ll_u=lu, mi=mi,
                                med_min=medt))
    df = pd.DataFrame(allrows)
    df.to_csv(RESULTS / "stage2_results.csv", index=False)
    print(f"\n{BAR}\n  BB-SS SEPARATION vs BARRIER SIZE — the curve\n{BAR}")
    print("  columns: BB-SS separation in pp, ambiguous entries EXCLUDED in brackets")
    print(f"  {'k(ATR)':>7}" + "".join(f"{s:>18}" for s in INSTR) + f"{'mean':>10}"
          f"{'> perm p95?':>13}")
    for k in KS:
        row = df[df.k == k]
        vals = [row[row.sym == s].sep.values for s in INSTR]
        vals = [v[0] if len(v) else np.nan for v in vals]
        beats = sum(1 for s in INSTR
                    for _, rr in row[row.sym == s].iterrows()
                    if abs(rr.sep) > rr.perm_p95)
        nt = [row[row.sym == s].sep_noties.values for s in INSTR]
        nt = [v[0] if len(v) else np.nan for v in nt]
        print(f"  {k:>7.1f}" + "".join(f"{v:>+11.2f}[{w:+.2f}]" for v, w in zip(vals, nt))
              + f"{np.nanmean(vals):>+10.2f}{beats:>9} of 4")
    print(f"\n  INFORMATION GAIN vs the unconditional baseline (lower Brier/log-loss = better)")
    print(f"  {'k(ATR)':>7}{'Brier gain':>13}{'LogLoss gain':>14}{'MI bits':>11}")
    for k in KS:
        row = df[df.k == k]
        if not len(row):
            continue
        print(f"  {k:>7.1f}{(row.brier_u - row.brier_c).mean():>13.6f}"
              f"{(row.ll_u - row.ll_c).mean():>14.6f}{row.mi.mean():>11.5f}")


if __name__ == "__main__":
    main()
