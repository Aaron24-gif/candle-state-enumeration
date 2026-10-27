# STATE ENUMERATION — STAGE 2 REPORT

*The internal report as written, reproduced here unedited except for the two notes marked
**PUBLISHED COPY** and the removal of one reference to work that is not in this repository. The
README is the readable version; this is the record.*

**Verdict: KILL.** No Stage 3.

## What was asked

Stage 1 enumerated short-horizon candle states and found conditional structure that
survived a 112-cell multiplicity bar and an unconditional control. It was economically
dead at 1-ATR barriers. Stage 2 was pre-registered to answer one question:

> Does the ordering edge persist at wider barriers, where cost becomes a small fraction
> of R? If BB/SS still separates by 2-4pp at +/-3 or +/-5 ATR, the cost problem solves
> itself. If the separation decays toward zero as barriers widen - which is what a pure
> volatility-clustering effect would do - then it is a 5-minute microstructure artifact
> that can never be captured.

Design frozen from Stage 1: anchored non-overlapping windows (step 3 bars), entry at the
open of the first prediction candle, ATR14(5m) at the last observation candle, M1 barrier
ordering with adverse-first ties. Only the barrier multiple varied. Fixed 24h resolution
window at every k so the curve isolates barrier size rather than horizon.
198,054 / 196,525 / 196,576 / 196,493 entries, 2018-01-02 -> 2026-05-20.

## The curve

BB-SS separation, percentage points. Brackets exclude ambiguous (same-M1-bar) entries.

    k(ATR)      XAUUSD        USTEC         US30        US500     mean  beats perm p95
       0.5  -2.38[-2.45] -2.60[-2.65] -2.75[-2.80] -3.81[-3.87]  -2.89        4 of 4
       1.0  -1.71        -0.67        -2.11        -2.11         -1.65        4 of 4
       1.5  -0.89        +0.37        -1.32        -1.18         -0.75        3 of 4
       2.0  -0.62        +0.37        -1.15        -0.65         -0.51        3 of 4
       3.0  -0.43        +0.59        -0.37        +0.03         -0.04        1 of 4
       4.0  -0.54        +0.49        -0.16        +0.19         -0.01        0 of 4
       5.0  -0.20        +0.43        -0.03        +0.26         +0.12        0 of 4

It decays. Sign coherence breaks from 1.5 ATR (USTEC positive while US30 stays negative).
Block-bootstrap CIs span zero for every instrument at every k >= 3. This is the branch
the pre-registration named as fatal.

## The sign is the opposite of Stage 1's, and Stage 1 was conditioned on the future

Stage 1 reported BB -> up-first, +2.3pp: continuation. Stage 2 reports BB -> down-first
at every barrier below 1.5 ATR. Same entries, same states, same barriers, same M1
ordering. The only difference is that Stage 1 gave each entry ONE 5-minute candle to
travel a full ATR, so 70-77% never resolved.

Bucketing Stage 2 by time-to-resolution at +/-1 ATR reproduces both signs:

    time to resolution              share   XAUUSD   USTEC    US30   US500
    <= 5 min (Stage 1's window)     ~26%     +3.87   +4.83   +3.28   +0.78
    5-30 min                        ~61%     -4.37   -3.42   -4.29   -3.85
    30 min - 2 h                    ~12%     -1.07   -0.13   -2.82   -0.96
    2 - 8 h                          <1%     -5.40   +2.09   -4.93   -4.27

Stage 1's effect is real inside the 26% that resolve fast, and is reversed and outweighed
by the 61% that resolve slower.

**The disqualifying point is not the averaging.** "Resolves within 5 minutes" is not
observable at entry - it is determined by what price does afterwards. Selecting on it is
conditioning on future information. No ex-ante filter can place you in the +3.87pp bucket,
because membership in that bucket IS the outcome. Stage 1's headline was never a
tradeable quantity. Recorded as a new failure mode: LOOK-AHEAD BY OUTCOME-DEFINED
SUBSAMPLE. A high undecided rate is the warning sign - the decided subset is selected on
the future.

## Information content

Mutual information between state and outcome, against ~1 bit of outcome entropy:

    k(ATR)   Brier gain  LogLoss gain    MI bits
       0.5     0.000126      0.000252    0.00036
       1.0     0.000043      0.000087    0.00013
       3.0     0.000006      0.000011    0.00002
       5.0     0.000006      0.000013    0.00002

Statistically unmistakable across 198,000 non-overlapping entries; informationally
negligible. Same finding as Stage 1's MFE/MAE of 1.02, in a second currency.

## Economics

Median ATR14(5m): XAUUSD 6.0bp, USTEC 7.1bp, US30 5.3bp, US500 5.4bp. Round-trip cost
as a fraction of R:

                 0.5 ATR   1 ATR   3 ATR
    XAUUSD         87.1%   43.6%   14.5%
    USTEC          24.1%   12.1%    4.0%
    US30           44.9%   22.5%    7.5%
    US500          44.6%   22.3%    7.4%

Edge and cost move in opposite directions along the same axis. Best case in the map is
US500 SS at 0.5 ATR: P(favourable) 52.50%, RR 1, gross +0.050R against 0.444R of cost,
net -0.394R.

Full grid in `stage2_economics.csv`. Exactly one cell is net positive:

    USTEC, 5 ATR, BB:  +0.020R net
      unconditional up-first 51.93%          -> +0.015R  (index drift, i.e. beta)
      conditional on BB      52.20%          -> +0.020R
      the STATE contributes                     +0.005R
      BB excess +0.27pp vs permutation p95 0.65pp -> FAILS its own null

Three-quarters of it is 2018-2026 index drift — long exposure to a market that went up,
which needs no candle state to harvest. The state's own contribution does not clear its
permutation null, and it is the best of 112 state-cell selections, so the honest bar is
|z| > 2.6.

> **PUBLISHED COPY — CORRECTION.** "Exactly one cell is net positive" is wrong. There are
> two: USTEC BB at 4 ATR (+0.0108R net) and at 5 ATR (+0.0197R net). Both are the same
> instrument and state at adjacent barriers, both are dominated by drift (86% and 88% of
> gross), and neither clears its own permutation null. The verdict is unchanged. See the
> README, "The two cells that survive costs".

## Errors made during Stage 2

1. **5-minute resolution in the first run.** Deviated from Stage 1's M1 spec for speed.
   Inflated same-bar double-touches to 7.1% at 0.5 ATR. Re-run at M1: ambiguity 0.1%,
   results unchanged to within 0.07pp. Kept as `stage2_results_5m_coarse.csv`.
2. **Diagnosed a tie-rule bug from a pattern match, before testing it.** The separation
   size tracked the ambiguity column down the curve, so I asserted the adverse-first tie
   rule had manufactured the result. It had not. Assert after the control, not before.
3. **Stage 1 was summarised as "genuine short-horizon continuation."** Wrong sign and
   wrong scope. Withdrawn.
4. **Block bootstrap used 64-entry blocks (16h) against a 24h resolution window.** Blocks
   should be >= the overlap horizon; the tight-barrier CIs are narrower than they should
   be. Does not change the verdict - k >= 3 intervals span zero with room to spare.

## Files

    stage1.py / stage1_results.csv          Stage 1
    stage2.py / stage2_results.csv          the barrier curve, M1 resolution
    stage2_results_5m_coarse.csv            the voided coarse run, kept for comparison
    reconcile.py                            time-to-resolution decomposition + cost table
    stage2_economics.csv                    net expectancy for all 28 cells

> **PUBLISHED COPY.** Paths have moved: code is under `src/`, outputs under `results/`. The
> economics grid had no generating script when this report was written; `src/economics.py`
> reconstructs it from `stage2_results.csv` and `instrument_cost.csv` and reproduces the
> committed table to floating-point precision.
