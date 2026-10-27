"""The data seam. One MetaTrader 5 M1 export per instrument in `data/`, tab separated, exactly as
the terminal writes it:

    <DATE>	<TIME>	<OPEN>	<HIGH>	<LOW>	<CLOSE>	<TICKVOL>	<VOL>	<SPREAD>
    2018.01.02	16:15:00	6534.1	6535.8	6533.9	6535.2	412	0	14

No data is included in this repository; it is not ours to redistribute. `data/HOWTO.md` has the
export recipe and the two conventions that will otherwise break your reproduction.

Two things this loader does that matter to the result:

- **The timestamps are the broker SERVER's clock.** They are localised to Europe/Athens (the
  EET/EEST clock the export was taken on) and converted to UTC, so that a 5-minute bar means the
  same thing across daylight-saving boundaries. Resampling the naive server index instead smears
  two bars a year; it will not change this study's verdict, but it is not the same code.
- **`<SPREAD>` is in POINTS, not price**, and is multiplied by the instrument's point size. Nothing
  in this study is cost-sensitive at the bar level — costs enter only through `economics.py`, from
  a measured round-trip in basis points — but the column is carried so the loader is the same one
  the rest of the programme uses.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# <SPREAD> is in points; multiply by this to get price. 2-digit CFD feeds are 0.01.
POINT = {"XAUUSD": 0.01, "USTEC": 0.01, "US30": 0.01, "US500": 0.01}

# The programme's sealed out-of-sample period begins here and is never loaded. The exports this
# study was run on physically contain bars past it; the cap below is what keeps them out.
SEALED = "2026-05-21"

# instrument -> export filename. Change the right-hand side, not the code.
FILES = {"XAUUSD": "XAUUSD.csv", "USTEC": "USTEC.csv",
         "US30": "US30.csv", "US500": "US500.csv"}


def load_m1(symbol: str, cap: str = SEALED) -> pd.DataFrame:
    """Full M1 history for one instrument, UTC indexed, truncated at the sealed boundary.

    Columns: open, high, low, close, spread (in price units).
    """
    path = DATA / FILES.get(symbol, f"{symbol}.csv")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - see data/HOWTO.md")

    d = pd.read_csv(path, sep="\t")
    d.columns = [c.strip("<> ") for c in d.columns]
    d["dt"] = pd.to_datetime(d["DATE"] + " " + d["TIME"], format="%Y.%m.%d %H:%M:%S")
    d = d.set_index("dt").sort_index()
    d = d[~d.index.duplicated(keep="first")]

    # Server clock -> UTC. The hour that does not exist in spring and the one that happens twice
    # in autumn are dropped rather than guessed; that is ~1 bar-hour a year either way.
    i = d.index.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT")
    d = d[i.notna()]
    d.index = i[i.notna()].tz_convert("UTC")

    d = d.rename(columns={"OPEN": "open", "HIGH": "high", "LOW": "low",
                          "CLOSE": "close", "SPREAD": "spread"})
    d["spread"] = d["spread"] * POINT.get(symbol, 0.01)
    out = d[["open", "high", "low", "close", "spread"]].loc[:cap]
    assert out.index.max() <= pd.Timestamp(f"{cap} 23:59:59", tz="UTC"), "past the sealed boundary"
    return out


def to_m5(m1: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
    """5-minute bars with a CAUSAL ATR: the value on bar k is computed from bars strictly before
    k, so a bar is never normalised by its own range."""
    import numpy as np

    m5 = m1.resample("5min").agg({"open": "first", "high": "max", "low": "min",
                                  "close": "last"}).dropna()
    h, l, c = (m5[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    m5["atr"] = pd.Series(tr, index=m5.index).rolling(atr_period).mean().shift(1)
    return m5
