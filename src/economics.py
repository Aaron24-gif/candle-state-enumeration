"""
THE ECONOMICS TABLE — what the best cell in the map is worth after costs.

Needs no market data. It reads two committed artefacts:

    results/stage2_results.csv     the barrier curve (from stage2.py)
    results/instrument_cost.csv    median ATR14(5m) in bp and round-trip cost (from reconcile.py)

so anyone can rebuild the table and check the arithmetic without reproducing the study.

METHOD, and the one place to be careful. For each instrument and barrier k we take the four
states, compute P(up first | state) = unconditional + the state's excess, and score each state
on the FAVOURABLE side of its own tilt: a state at 48.6% up-first is a 51.4% short. That is the
most generous reading available, chosen deliberately - the point of the table is that even the
best cell in the map does not pay, so it is scored at its best.

    gross = 2p - 1            R:R of 1, symmetric barriers
    cost  = round_trip_bp / (k * atr_bp)
    net   = gross - cost

Note what `cost` says: at a 0.5 ATR barrier on gold the round trip is 87% of R. Edge and cost
move in opposite directions along the same axis, which is the structural reason this family
cannot be rescued by widening the stop - the separation decays faster than the cost does.

Run:  python -I economics.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
STATES = ["BB", "BS", "SB", "SS"]


def build() -> pd.DataFrame:
    curve = pd.read_csv(RESULTS / "stage2_results.csv")
    cost = pd.read_csv(RESULTS / "instrument_cost.csv").set_index("sym")

    rows = []
    for _, r in curve.iterrows():
        best, best_p = None, 0.0
        for s in STATES:
            p_up = r["uncond"] + r[s.lower()]
            fav = max(p_up, 100 - p_up)      # trade whichever side the state leans
            if fav > best_p:
                best, best_p = s, fav
        c = cost.loc[r["sym"]]
        gross = 2 * best_p / 100 - 1
        rt = c["rt_bp"] / (r["k"] * c["atr_bp"])
        rows.append({"sym": r["sym"], "k": r["k"], "state": best, "p": best_p,
                     "gross": gross, "cost": rt, "net": gross - rt})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    e = build()
    e.to_csv(RESULTS / "stage2_economics.csv", index=False)
    print(f"  {'sym':<8}{'k':>5}{'state':>7}{'p(fav)':>9}{'gross R':>10}"
          f"{'cost R':>9}{'net R':>9}")
    for _, r in e.iterrows():
        print(f"  {r['sym']:<8}{r['k']:>5.1f}{r['state']:>7}{r['p']:>8.2f}%"
              f"{r['gross']:>+10.4f}{r['cost']:>9.4f}{r['net']:>+9.4f}")
    pos = e[e.net > 0]
    print(f"\n  cells net positive: {len(pos)} of {len(e)}")
    for _, r in pos.iterrows():
        print(f"    {r['sym']} {r['k']} ATR {r['state']}: {r['net']:+.4f}R")
    print("\n  Any positive cell is the best of 112 state-cell selections and has to clear its")
    print("  own permutation null before it means anything. See README, 'The one cell that")
    print("  survives costs'.")
