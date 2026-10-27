# Candle-state enumeration — an edge that was chosen by the future

**Verdict: KILL.** No Stage 3.

Stage 1 enumerated short-horizon candle states on four instruments and found conditional
structure that survived a 112-cell multiplicity bar: after two bullish five-minute candles, gold
reached its upside barrier first **2.29 percentage points** more often than its own unconditional
rate. 112 cells, 198,000 entries each, non-overlapping windows, M1 barrier ordering, adverse-first
on ties. It looked like short-horizon continuation.

Stage 2 ran the same entries at wider barriers. **The sign flipped.**

Not weakened. Reversed, on the same entries, with the same code, against the same barriers.

The reason is the whole point of this repository:

> In Stage 1, each entry got **one five-minute candle** to travel a full ATR. **70–77% of entries
> never reached either barrier.** The result was computed on the 23–30% that did — and "resolves
> within five minutes" is not something you can know at entry. It is determined by what price does
> afterwards. Selecting on it is conditioning on future information.

No filter can place you in the favourable subset, because **membership in that subset is the
outcome**. Stage 1's headline was never a tradeable quantity.

We have recorded this as a named failure mode: **look-ahead by outcome-defined subsample.** The
warning sign is cheap to check and almost never looked at — **a high undecided rate**. If a large
share of your backtested trades never reach a target or a stop, the ones that did were selected by
the future.

---

## The curve that killed it

BB−SS separation in percentage points. Brackets exclude ambiguous (same-M1-bar) entries.

| k (ATR) | XAUUSD | USTEC | US30 | US500 | mean | beats permutation p95 |
|---:|---:|---:|---:|---:|---:|:---|
| 0.5 | −2.38 [−2.45] | −2.60 [−2.65] | −2.75 [−2.80] | −3.81 [−3.87] | **−2.89** | 4 of 4 |
| 1.0 | −1.71 | −0.67 | −2.11 | −2.11 | −1.65 | 4 of 4 |
| 1.5 | −0.89 | +0.37 | −1.32 | −1.18 | −0.75 | 3 of 4 |
| 2.0 | −0.62 | +0.37 | −1.15 | −0.65 | −0.51 | 3 of 4 |
| 3.0 | −0.43 | +0.59 | −0.37 | +0.03 | −0.04 | 1 of 4 |
| 4.0 | −0.54 | +0.49 | −0.16 | +0.19 | −0.01 | 0 of 4 |
| 5.0 | −0.20 | +0.43 | −0.03 | +0.26 | +0.12 | 0 of 4 |

It decays to nothing. **Sign coherence breaks from 1.5 ATR** — USTEC turns positive while US30
stays negative — which is what you see when four instruments are sampling noise rather than
sharing a mechanism. Block-bootstrap intervals span zero for every instrument at every k ≥ 3.

Stage 2's pre-registration named this branch as fatal before the run. That is the only reason the
curve is readable as an answer rather than as a menu.

## Both signs, from one table

Bucketing Stage 2 by time-to-resolution at ±1 ATR reproduces **both** results at once:

| time to resolution | share | XAUUSD | USTEC | US30 | US500 |
|---|---:|---:|---:|---:|---:|
| ≤ 5 min — *Stage 1's window* | ~26% | **+3.87** | **+4.83** | **+3.28** | **+0.78** |
| 5–30 min | ~61% | −4.37 | −3.42 | −4.29 | −3.85 |
| 30 min – 2 h | ~12% | −1.07 | −0.13 | −2.82 | −0.96 |
| 2 – 8 h | <1% | −5.40 | +2.09 | −4.93 | −4.27 |

Stage 1's effect is real **inside** the fast-resolving quarter, and it is reversed and outweighed
by the 61% that resolve slower. The disqualifying point is not that the average hides it. It is
that the fast-resolving quarter cannot be identified in advance.

`src/reconcile.py` is the script that settles this, and it is three dozen lines. The expensive
part was being willing to run it.

## Information content

Mutual information between state and outcome, against ~1 bit of outcome entropy:

| k (ATR) | Brier gain | log-loss gain | MI (bits) |
|---:|---:|---:|---:|
| 0.5 | 0.000126 | 0.000252 | 0.00036 |
| 1.0 | 0.000043 | 0.000087 | 0.00013 |
| 3.0 | 0.000006 | 0.000011 | 0.00002 |
| 5.0 | 0.000006 | 0.000013 | 0.00002 |

Statistically unmistakable across 198,000 non-overlapping entries; **informationally negligible**.
Those two things are not in tension, and a large enough sample will separate them for you every
time.

## Economics

Median ATR14(5m): XAUUSD 6.0bp, USTEC 7.1bp, US30 5.3bp, US500 5.4bp. Round-trip cost as a
fraction of R:

| | 0.5 ATR | 1 ATR | 3 ATR |
|---|---:|---:|---:|
| XAUUSD | 87.1% | 43.6% | 14.5% |
| USTEC | 24.1% | 12.1% | 4.0% |
| US30 | 44.9% | 22.5% | 7.5% |
| US500 | 44.6% | 22.3% | 7.4% |

**Edge and cost move in opposite directions along the same axis.** The separation is largest where
the cost is largest and decays to zero exactly where the cost becomes bearable. That is the
structural reason this family cannot be rescued by widening the stop, and it is visible before any
of the statistics.

Scored at its most generous — every state traded on whichever side it leans — the best cell in the
map is US500 SS at 0.5 ATR: P(favourable) 52.50%, gross +0.050R against 0.444R of cost, net
**−0.394R**. Full grid in `results/stage2_economics.csv`.

### The two cells that survive costs

**Correction to the original report, which said "exactly one".** There are two, and they are the
same instrument and state at adjacent barriers:

| | gross | of which unconditional drift | the state's own contribution | cost | net |
|---|---:|---:|---:|---:|---:|
| USTEC, 4 ATR, BB | +0.0411R | +0.0352R (86%) | +0.0059R | 0.0303R | **+0.0108R** |
| USTEC, 5 ATR, BB | +0.0440R | +0.0386R (88%) | +0.0053R | 0.0242R | **+0.0197R** |

Most of each is 2018–2026 index drift — long exposure to a market that went up, which needs no
candle state to harvest. What is left is the state's own contribution, and at both barriers it
**fails its own permutation null**: +0.29pp against a p95 of 0.64pp at 4 ATR, +0.27pp against 0.65pp
at 5 ATR. They are also the best of 112 state-cell selections, so the honest bar is not 1.96 but
|z| > 2.6.

Finding two rather than one does not rescue anything — two adjacent barriers on one instrument is
one cell with a neighbour, not two independent confirmations.

---

## What is in here

```
PREREG.md                       both stages' designs, as frozen, plus the deviations
src/data.py                     the data seam — one MT5 export per instrument
src/stage1.py                   state enumeration, 112 cells
src/stage2.py                   the barrier curve, permutation null, bootstrap, information
src/reconcile.py                the time-to-resolution decomposition — the script with the answer
src/economics.py                net expectancy for all 28 cells, from committed artefacts only
results/stage1_results.csv      every Stage 1 cell
results/stage2_results.csv      the curve
results/stage2_results_5m_coarse.csv   the voided coarse run, kept rather than deleted
results/stage2_economics.csv    the economics grid
results/instrument_cost.csv     measured ATR in bp and round-trip cost, per instrument
results/reconciliation.txt      the reconciliation run, verbatim
results/STAGE2_REPORT.md        the original internal report
```

### Reproducing

`economics.py` needs **no market data at all** — it rebuilds the economics grid from
`stage2_results.csv` and `instrument_cost.csv`, both committed here:

```bash
pip install -r requirements.txt
python -I src/economics.py
```

Everything else needs four MetaTrader 5 M1 exports in `data/`. See `data/HOWTO.md`. No data is
included in this repository; it is not ours to redistribute.

```bash
python -I src/stage1.py      # ~200,000 entries x 4 instruments
python -I src/stage2.py      # the curve: 7 barriers, 600 permutations per cell
python -I src/reconcile.py   # the decomposition, and writes instrument_cost.csv
```

Data after **2026-05-21** is refused by an assertion in the loader. That period is sealed
out-of-sample work for the programme this came from, and the exports physically contain it.

## Things to be suspicious of

- **The costs are ours, not yours.** `INSTR` in `reconcile.py` carries a round-trip in basis
  points per instrument, measured on one broker's 2-digit CFD feed. On a different account every
  number in the economics table moves. The *shape* — cost falling as 1/k while the edge falls
  faster — does not.
- **The block bootstrap is too short.** 64-entry blocks against a 24-hour resolution window;
  the tight-barrier intervals are narrower than they should be. It happens not to matter here.
- **The sample is one broker's feed and four correlated instruments.** Three of the four are US
  equity indices. "4 of 4" is nothing like four independent confirmations, in either direction.
- **The adverse-first tie rule is a choice.** It is the worst case, applied uniformly; at M1
  resolution it touches 0.1% of entries and changes the separation by under 0.07pp. At 5-minute
  resolution it touched 7% and manufactured a result. The voided run is in `results/` so you can
  see what that looked like.

---

MIT licensed. Published by ANS Capital Group as part of an open research record: the failures get
published on the same terms as anything else, because a research programme that only publishes its
wins is not reporting a result, it is advertising.
