# Pre-registration

Both stages were written down before they were run. This file is the published version of those
two designs, edited only to remove references to work that is not in this repository. Nothing in
the decision rules has been softened after the fact; where a stage broke its own rules, the
`Deviations` section at the end says so.

---

## Stage 1 — conditional state enumeration

**Question.** Does the direction sequence of the first *n* five-minute candles carry information
about the excursion of the next *m* candles?

**Design, fixed before any result was seen.**

| element | choice |
|---|---|
| base | 5-minute bars built from M1, UTC |
| observation | `n_obs` candles, each classified bullish (close > open) or bearish |
| prediction | `n_pred` candles |
| windows | **anchored and non-overlapping** — consecutive windows share no candles, so observations are independent. Rolling windows would inflate every significance test, because neighbouring samples share bars |
| entry | the **open of the first prediction candle**. Everything used to form the state is closed before entry |
| barriers | ±1 × ATR14(5m) measured at the **last observation candle**, so the normaliser is causal. Scale-free and cross-instrument comparable; a fixed pip target is 44% cost on one of these instruments and 12% on another, and is not comparable at all |
| resolution | **M1 bars inside the prediction window** decide which barrier came first. If both are touched inside the same M1 bar the stop is taken (**adverse-first**, worst case). Those are counted and reported |
| null | symmetric barriers ⇒ P(up first) = 50% under a driftless walk. Reported against 50%, two-sided |
| configurations | (n_obs, n_pred) ∈ {(2,1), (3,1), (2,2), (3,2), (2,3)} |
| minimum cell | 200 decided entries, or the cell is not reported |

**Multiplicity, stated in advance.** Roughly 288 state-cells were possible; 112 cleared the
200-entry floor. The expected maximum |z| across 112 cells under the pure null is **2.61**. A cell
at |z| = 2 is the modal outcome of a search this size and means nothing on its own.

---

## Stage 2 — the barrier curve

**Question, and the decision rule, both written before the run.**

> Does the ordering edge persist at wider barriers, where cost becomes a small fraction of R? If
> BB/SS still separates by 2–4pp at ±3 or ±5 ATR, the cost problem solves itself. **If the
> separation decays toward zero as barriers widen — which is what a pure volatility-clustering
> effect would do — then it is a five-minute microstructure artefact that can never be captured.**

That second branch was named as fatal in advance. It is the branch that happened.

**Frozen design.**

| element | choice |
|---|---|
| entry | unchanged from Stage 1: the open of the candle after two closed observation candles, anchored non-overlapping windows, step 3 bars |
| states | the **full matrix** BB / BS / SB / SS carried through every barrier. BB and SS are the primary hypothesis but nothing is dropped |
| barriers | ±k × ATR14(5m), k ∈ {0.5, 1, 1.5, 2, 3, 4, 5}, ATR at the last observation candle |
| resolution | M1 bars decide which barrier came first, over a **fixed 24-hour window at every k**, so the curve isolates barrier size rather than confounding it with horizon. Undecided share reported per k. Adverse-first on same-bar ties |
| baseline | the **unconditional** up-first rate, computed per instrument per barrier. Every state is scored as excess over it, never against a bare 50% |
| primary statistic | BB−SS separation: P(up\|BB) − P(up\|SS) |
| inference | moving-block bootstrap over blocks of consecutive entries — non-overlap removes shared bars but not serial dependence in volatility regimes |
| null | **permutation**: state labels shuffled across entries, preserving both marginals and destroying only the state–outcome association |
| information | Brier score, log-loss and mutual information for the conditional model against the unconditional baseline |
| timing | median and IQR of time-to-barrier, to separate a persistent directional effect from a short-lived one |

**No strategy is built.** The output is a statistical map. The decision after Stage 2 is one of
*kill* / *investigate further* / *promote to Stage 3*.

---

## Deviations and errors, as they happened

These are reproduced from the run record. Each is a thing that went wrong, not a caveat written
afterwards to cover one.

1. **Five-minute resolution in the first Stage 2 run.** Deviated from Stage 1's M1 specification
   for speed. It inflated same-bar double-touches to 7.1% at k = 0.5, and because ties are forced
   adverse-first it manufactured a spurious "down-first after BB" effect whose size tracked the
   ambiguity rate exactly. Re-run at M1: ambiguity 0.1%, results unchanged to within 0.07pp. The
   voided run is kept as `results/stage2_results_5m_coarse.csv`.
2. **A tie-rule bug was diagnosed from a pattern match, before being tested.** The separation
   tracked the ambiguity column down the curve, so the adverse-first rule was asserted to have
   manufactured the result. It had not. **Assert after the control, not before.**
3. **Stage 1 was summarised as "genuine short-horizon continuation."** Wrong sign and wrong scope.
   Withdrawn — see the README.
4. **The block bootstrap used 64-entry blocks (16 h) against a 24-hour resolution window.** Blocks
   should be at least the overlap horizon, so the tight-barrier confidence intervals are narrower
   than they should be. It does not change the verdict: every interval at k ≥ 3 spans zero with
   room to spare.
5. **The Stage 2 report said "exactly one cell is net positive."** There are two, both USTEC BB at
   adjacent wide barriers. Corrected in the README and in the shipped copy of the report; the
   verdict is unchanged, because neither clears its own permutation null and both are dominated by
   drift.
