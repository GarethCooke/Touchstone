"""Generate the American-exercise golden file from QuantLib.

The companion to ``generate_bs_vanilla.py``, and the same discipline: QuantLib is the
oracle and never a dependency (CONSTITUTION.md I4), the evaluation date is fixed in source,
nothing is rounded or rescaled on the way out, and the QuantLib version is recorded beside
the numbers.

What is different is that there is no closed form to be the oracle. An American vanilla's
value is the solution of a free-boundary problem, and every reference for it is itself a
numerical method. So this file does not claim a value to fifteen digits; it claims a value
and **how far three independent lattices disagreed about it**, per row, in a ``spread``
field. A test that reads this file compares against ``price`` with ``spread`` as the
oracle's own uncertainty, which is the only honest thing to compare against.

The three lattices are QuantLib's own: Leisen-Reimer, Cox-Ross-Rubinstein and Tian. They
differ in how the up and down factors and the risk-neutral probability are chosen, so they
converge along different paths and their spread is a genuine measurement rather than the
same error computed twice. Leisen-Reimer is the value written out, because its European
limit converges fastest.

Usage::

    uv run golden/generate_american_vanilla.py            # write golden/american_vanilla.json
    uv run golden/generate_american_vanilla.py --stdout   # write to stdout instead
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import QuantLib as ql

# --------------------------------------------------------------------------------------
# Fixed conventions — identical to generate_bs_vanilla.py, so that a row of this file and a
# row of that one with the same inputs describe the same contract under the same calendar.
# --------------------------------------------------------------------------------------
EVALUATION_DATE = ql.Date(1, ql.January, 2026)
DAY_COUNT = ql.Actual365Fixed()
CALENDAR = ql.NullCalendar()

SCHEMA_ID = "touchstone/golden/american_vanilla@1"

# Odd, because Leisen-Reimer is defined for an odd number of steps: it places a node exactly
# at the strike at expiry, which is where its accuracy comes from.
PRIMARY_STEPS = 2001
CROSS_STEPS = 2001

# --------------------------------------------------------------------------------------
# The grid
# --------------------------------------------------------------------------------------
# Smaller than the European grid, because a lattice at two thousand steps is five orders of
# magnitude slower than a closed form, and because what is being measured here is narrower:
# the early-exercise premium, which is a function of moneyness, carry and time, and not of
# absolute scale.
#
# Every axis earns its place against a specific claim the C++ tests make.
#
#   rate      -0.005 is there because an American put with a non-positive rate is worth
#             exactly its European counterpart — there is no interest on the strike to be
#             earned by exercising early — and that is an exact identity to test against.
#   yield     0.0 is there because an American call on an underlying with no dividend yield
#             is worth exactly its European counterpart. That identity is the strongest
#             check in the American suite: it holds the numerical method against the golden
#             file's fifteen digits rather than against another lattice's four.
#   vol       0.05 is there because a five-year at-the-money put at 5% volatility is worth
#             twenty times its European value. Low volatility is where the early-exercise
#             premium is largest relative to the option, not smallest.
#
# 3 spots x 3 strikes x 4 vols x 2 rates x 2 yields x 3 expiries x 2 types = 864 rows.
SPOTS = [80.0, 100.0, 120.0]
STRIKES = [90.0, 100.0, 110.0]
VOLS = [0.05, 0.15, 0.30, 0.60]
RATES = [-0.005, 0.05]
YIELDS = [0.0, 0.04]
EXPIRY_DAYS = [91, 365, 1826]  # ~3m, 1y, ~5y
OPTION_TYPES = [("call", ql.Option.Call), ("put", ql.Option.Put)]

FIELDS = [
    "type", "spot", "strike", "vol", "rate", "dividend_yield",
    "expiry_days", "expiry_years",
    "price", "delta", "gamma", "spread", "delta_spread", "gamma_spread",
]

CONVENTIONS = {
    "price": "present value in the same currency units as spot and strike",
    "delta": "dV/dS, per 1.00 of spot",
    "gamma": "d2V/dS2, per 1.00 of spot squared",
    "spread": (
        "max |price - price| over the three lattices, at this row's inputs. The oracle's "
        "own uncertainty about this number, measured rather than assumed."
    ),
    "delta_spread": "the same, for delta",
    "gamma_spread": "the same, for gamma",
    "expiry_years": "year fraction under Actual/365 Fixed; exactly expiry_days / 365",
    "note": (
        "American exercise: the holder may exercise at any time up to and including "
        "expiry. There is no closed form, so every value here is a lattice value and the "
        "spread beside it is what three lattices disagreed by."
    ),
}

TREES = [
    ("leisen_reimer", "LeisenReimer", PRIMARY_STEPS),
    ("cox_ross_rubinstein", "CoxRossRubinstein", CROSS_STEPS),
    ("tian", "Tian", CROSS_STEPS),
]


def price_one(
    option_type: int,
    spot: float,
    strike: float,
    vol: float,
    rate: float,
    dividend_yield: float,
    expiry_days: int,
) -> dict[str, float]:
    """Price one American vanilla on all three lattices; return the primary and the spread."""
    today = EVALUATION_DATE
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
    rate_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, rate, DAY_COUNT))
    dividend_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(today, dividend_yield, DAY_COUNT)
    )
    vol_ts = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, CALENDAR, vol, DAY_COUNT)
    )
    process = ql.BlackScholesMertonProcess(spot_handle, dividend_ts, rate_ts, vol_ts)

    expiry = today + ql.Period(expiry_days, ql.Days)
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(option_type, strike), ql.AmericanExercise(today, expiry)
    )

    values: list[tuple[float, float, float]] = []
    for _name, tree, steps in TREES:
        option.setPricingEngine(ql.BinomialVanillaEngine(process, tree, steps))
        values.append((option.NPV(), option.delta(), option.gamma()))

    primary = values[0]
    spreads = [
        max(abs(v[i] - primary[i]) for v in values[1:]) for i in range(3)
    ]
    return {
        "price": primary[0],
        "delta": primary[1],
        "gamma": primary[2],
        "spread": spreads[0],
        "delta_spread": spreads[1],
        "gamma_spread": spreads[2],
    }


def make_case(
    type_name: str,
    option_type: int,
    spot: float,
    strike: float,
    vol: float,
    rate: float,
    dividend_yield: float,
    expiry_days: int,
) -> dict:
    case = {
        "type": type_name,
        "spot": spot,
        "strike": strike,
        "vol": vol,
        "rate": rate,
        "dividend_yield": dividend_yield,
        "expiry_days": expiry_days,
        "expiry_years": expiry_days / 365.0,
    }
    case.update(
        price_one(option_type, spot, strike, vol, rate, dividend_yield, expiry_days)
    )
    return case


def build_grid() -> list[dict]:
    cases = []
    for type_name, option_type in OPTION_TYPES:
        for spot in SPOTS:
            for strike in STRIKES:
                for vol in VOLS:
                    for rate in RATES:
                        for dividend_yield in YIELDS:
                            for expiry_days in EXPIRY_DAYS:
                                cases.append(
                                    make_case(
                                        type_name, option_type, spot, strike,
                                        vol, rate, dividend_yield, expiry_days,
                                    )
                                )
    return cases


def build_document() -> dict:
    ql.Settings.instance().evaluationDate = EVALUATION_DATE
    cases = build_grid()
    worst = max(case["spread"] for case in cases)
    return {
        "schema": SCHEMA_ID,
        "generator": "golden/generate_american_vanilla.py",
        "documentation": "golden/AMERICAN-SCHEMA.md",
        "model": (
            "Black-Scholes-Merton with American exercise: one underlying, constant "
            "continuously compounded rate, constant continuous dividend yield, constant "
            "volatility, exercise at any time up to expiry"
        ),
        "oracle": {
            "library": "QuantLib",
            "version": ql.__version__,
            "binding": "QuantLib-Python",
            "engine": (
                f"BinomialVanillaEngine, LeisenReimer at {PRIMARY_STEPS} steps, on "
                "BlackScholesMertonProcess"
            ),
            "cross_checks": [
                f"BinomialVanillaEngine CoxRossRubinstein at {CROSS_STEPS} steps",
                f"BinomialVanillaEngine Tian at {CROSS_STEPS} steps",
            ],
            "day_count": "Actual/365 Fixed",
            "calendar": "NullCalendar",
            "evaluation_date": EVALUATION_DATE.ISO(),
        },
        "conventions": CONVENTIONS,
        "tolerances": {
            "worst_spread": worst,
            "note": (
                "There is no fixed tolerance for this file. Compare against price with the "
                "row's own spread as the oracle's uncertainty; worst_spread is the largest "
                "of those over the grid, recorded so that a change in the oracle's quality "
                "shows up in the diff."
            ),
        },
        "axes": {
            "spot": SPOTS,
            "strike": STRIKES,
            "vol": VOLS,
            "rate": RATES,
            "dividend_yield": YIELDS,
            "expiry_days": EXPIRY_DAYS,
            "type": [name for name, _ in OPTION_TYPES],
        },
        "fields": FIELDS,
        "counts": {"cases": len(cases)},
        "cases": cases,
    }


def serialise(doc: dict) -> str:
    """One case per line, as in generate_bs_vanilla.py, so diffs name the rows that moved."""
    head = {k: v for k, v in doc.items() if k != "cases"}
    out = [json.dumps(head, indent=2)[:-2].rstrip()]
    out.append(',\n  "cases": [')
    rows = ["    " + json.dumps(case, separators=(",", ":")) for case in doc["cases"]]
    out.append("\n" + ",\n".join(rows) + "\n  ]")
    out.append("\n}\n")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true", help="write to stdout instead")
    parser.add_argument("--out", type=Path, default=None, help="write somewhere else")
    args = parser.parse_args()

    doc = build_document()
    text = serialise(doc)

    if args.stdout:
        sys.stdout.write(text)
        return 0

    destination = args.out or Path(__file__).with_name("american_vanilla.json")
    destination.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"wrote {destination} — QuantLib {doc['oracle']['version']}, "
        f"{doc['counts']['cases']} cases, worst spread "
        f"{doc['tolerances']['worst_spread']:.3e}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
