# Getting data in

Four MetaTrader 5 M1 exports in this folder, tab separated, exactly as the terminal writes them:

```
<DATE>	<TIME>	<OPEN>	<HIGH>	<LOW>	<CLOSE>	<TICKVOL>	<VOL>	<SPREAD>
2018.01.02	16:15:00	6534.1	6535.8	6533.9	6535.2	412	0	14
```

| file | instrument |
|---|---|
| `XAUUSD.csv` | gold |
| `USTEC.csv` | Nasdaq 100 CFD |
| `US30.csv` | Dow CFD |
| `US500.csv` | S&P 500 CFD |

The names live in `FILES` at the top of `src/data.py`. Change that dict rather than renaming your
exports if you would rather not.

No data is included in this repository; it is not ours to redistribute.

## Exporting

1. Tools → Options → Charts → "Max bars in chart": set to Unlimited, then restart the terminal.
2. Open the symbol on M1 and hold Home until the history has downloaded back to 2018. The export
   contains only what the terminal actually has.
3. Tools → History Center (F2) → pick the symbol and M1 → Export.

Keep the header row and the tab separators. A full M1 history from 2018 runs to roughly 200 MB per
instrument, so budget about 800 MB of disk and a few minutes per load.

## The two things that will break your reproduction

**1. The timestamps are your broker server's clock, not UTC and not New York's.** `src/data.py`
localises them to `Europe/Athens` — the EET/EEST clock these exports were taken on — and converts
to UTC:

```python
i = d.index.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT")
d.index = i[i.notna()].tz_convert("UTC")
```

If your server is not on that clock, change the zone. If you skip the conversion entirely and
resample the naive index, you will smear two bars a year across the daylight-saving boundaries.
That will not change this study's verdict — nothing here turns on two bars — but it is then not
the same code, and you should not report it as a reproduction.

**2. `<SPREAD>` is in points, not price**, and is multiplied by the instrument's point size:

```python
POINT = {"XAUUSD": 0.01, "USTEC": 0.01, "US30": 0.01, "US500": 0.01}
```

Those are right for a 2-digit CFD feed. Nothing in *this* study is cost-sensitive at the bar level
— costs enter only through `economics.py`, from a measured round-trip in basis points — so a wrong
`POINT` will not quietly flatter the result here. It would elsewhere, which is why the loader is
the same one the rest of the programme uses.

A related warning from the same programme: on several feeds `<SPREAD>` is a **posted tariff**
rather than a measured one. It sits at a constant value for years and tells you nothing about real
liquidity. Check whether yours actually varies before reading anything into it.

## The costs in the economics table are not yours

`src/reconcile.py` carries a round-trip cost per instrument:

```python
INSTR = [("XAUUSD", 2.60), ("USTEC", 0.86), ("US30", 1.20), ("US500", 1.20)]
```

Basis points, measured on one broker's account. **Change them to yours before reading anything
into `stage2_economics.csv`.** The qualitative shape of the result does not depend on them — cost
falls as 1/k while the edge falls faster — but every number in that table does.

## Checking it loaded correctly

```python
import sys; sys.path.insert(0, "src")
from data import load_m1, to_m5
m1 = load_m1("USTEC")
print(len(m1), m1.index.min(), m1.index.max())
m5 = to_m5(m1)
print(len(m5), m5["atr"].median())
```

Expect roughly 2018-01-02 → 2026-05-21 in UTC, a few million M1 bars, and a median ATR14(5m) that
is a plausible price distance — on the Nasdaq CFD a handful of points, not thousands and not
0.0001.

The sanity check that matters most for this study is the **undecided rate**, because it is the
whole finding:

```python
# at +/-1 ATR with a one-candle window, 70-77% of entries should never resolve
```

If yours comes out near zero, your barriers or your ATR are wrong by an order of magnitude.

## What the study used

Four CFDs from one broker, 1-minute bars, 2018-01-02 → 2026-05-21, with the period after that
sealed and refused by an assertion in the loader.
