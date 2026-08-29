"""Generate the Black-Scholes-Merton golden file from QuantLib.

QuantLib is Touchstone's oracle and never its dependency (CONSTITUTION.md I4). This script
is the only place QuantLib runs: it prices European calls and puts over a grid, writes the
prices and Greeks to ``golden/bs_vanilla.json``, and records the QuantLib version that
produced them. The C++ tests read that file; they never link QuantLib.

Two properties matter more than anything else here.

**Determinism.** Same QuantLib version, same bytes. The evaluation date is fixed in source,
never taken from the clock; the grid is fixed in source; no timestamp is written into the
output. If the regenerated file differs from the committed one, something real changed, and
``git diff`` says what. This is the exit criterion "the generator reruns reproducibly".

**No arithmetic of our own.** Every number in the output is what QuantLib returned, written
at full precision. The script applies no scaling, no rounding and no convention conversion
-- see ``SCHEMA.md`` on why the Greeks are raw partial derivatives rather than the scaled
quantities a desk quotes. Every transformation applied here would be a place the oracle's
authority leaks into our code.

Usage::

    uv run golden/generate_bs_vanilla.py            # write golden/bs_vanilla.json
    uv run golden/generate_bs_vanilla.py --stdout   # write to stdout instead
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import QuantLib as ql

# --------------------------------------------------------------------------------------
# Fixed conventions
# --------------------------------------------------------------------------------------
# The evaluation date is fixed in source so that the file does not change when the clock
# does. Its absolute value is arbitrary and carries no meaning: every quantity below is a
# function of the year fraction to expiry, not of the calendar.
EVALUATION_DATE = ql.Date(1, ql.January, 2026)

# Actual/365 Fixed with a null calendar. Expiries are whole numbers of days, so the year
# fraction QuantLib computes is exactly days / 365 -- no rounding sits between the grid
# definition and the number the C++ will be handed.
DAY_COUNT = ql.Actual365Fixed()
CALENDAR = ql.NullCalendar()

SCHEMA_ID = "touchstone/golden/bs_vanilla@1"

# --------------------------------------------------------------------------------------
# The main grid
# --------------------------------------------------------------------------------------
# A full cartesian product. Spot and strike are separate axes rather than a moneyness axis
# so that the file also exercises absolute-scale behaviour; the product therefore contains
# deep in- and out-of-the-money combinations as well as the near-the-money bulk.
#
# 5 spots x 5 strikes x 4 vols x 3 rates x 3 yields x 4 expiries x 2 types = 7200 rows.
SPOTS = [60.0, 80.0, 100.0, 120.0, 150.0]
STRIKES = [80.0, 90.0, 100.0, 110.0, 120.0]
VOLS = [0.05, 0.15, 0.30, 0.60]
RATES = [-0.005, 0.01, 0.05]  # a negative rate is a normal market state, not an edge case
YIELDS = [0.0, 0.02, 0.05]
EXPIRY_DAYS = [91, 365, 730, 1826]  # ~3m, 1y, 2y, ~5y
OPTION_TYPES = [("call", ql.Option.Call), ("put", ql.Option.Put)]

# --------------------------------------------------------------------------------------
# The edge block
# --------------------------------------------------------------------------------------
# Near-degenerate corners, kept out of the main grid and labelled individually. These are
# where a correct closed form and a correct oracle can still disagree in the last few
# digits: gamma and vega collapse toward zero, d1 and d2 grow without bound, and the
# difference of two nearly equal numbers loses precision. They are here so that T1 and T3
# have something to test limiting behaviour against -- at their own tolerance, never at the
# main grid's 1e-10. See SCHEMA.md.
#
# (label, spot, strike, vol, rate, yield, expiry_days)
EDGE_CASES = [
    ("one-day-atm",            100.0, 100.0, 0.20,  0.03, 0.01,    1),
    ("one-day-deep-itm-call",  200.0,  50.0, 0.20,  0.03, 0.01,    1),
    ("one-day-deep-otm-call",   50.0, 200.0, 0.20,  0.03, 0.01,    1),
    ("near-zero-vol-atm",      100.0, 100.0, 0.01,  0.03, 0.01,  365),
    ("near-zero-vol-itm-call", 120.0, 100.0, 0.01,  0.03, 0.01,  365),
    ("near-zero-vol-otm-call",  80.0, 100.0, 0.01,  0.03, 0.01,  365),
    ("very-high-vol-atm",      100.0, 100.0, 1.50,  0.03, 0.01,  365),
    ("very-high-vol-long",     100.0, 100.0, 1.50,  0.03, 0.01, 3652),
    ("deep-itm-call-1y",       200.0,  50.0, 0.20,  0.03, 0.01,  365),
    ("deep-otm-call-1y",        50.0, 200.0, 0.20,  0.03, 0.01,  365),
    ("zero-rate-zero-yield",   100.0, 100.0, 0.20,  0.00, 0.00,  365),
    ("rate-equals-yield",      100.0, 100.0, 0.20,  0.03, 0.03,  365),
    ("negative-rate-long",     100.0, 100.0, 0.20, -0.01, 0.00, 3652),
    ("high-yield-over-rate",   100.0, 100.0, 0.20,  0.01, 0.08,  365),
    ("ten-year-atm",           100.0, 100.0, 0.20,  0.03, 0.01, 3652),
    ("tiny-spot",                1.0,   1.0, 0.20,  0.03, 0.01,  365),
    ("large-spot",            5000.0, 5000.0, 0.20, 0.03, 0.01,  365),
]

FIELDS = [
    "type", "spot", "strike", "vol", "rate", "dividend_yield",
    "expiry_days", "expiry_years",
    "price", "delta", "gamma", "vega", "theta", "rho", "dividend_rho",
]

CONVENTIONS = {
    "price": "present value in the same currency units as spot and strike",
    "delta": "dV/dS, per 1.00 of spot",
    "gamma": "d2V/dS2, per 1.00 of spot squared",
    "vega": "dV/dsigma, per 1.00 of volatility (NOT per volatility point)",
    "theta": "dV/dt, per year (negative for a long position that decays)",
    "rho": "dV/dr, per 1.00 of the continuously compounded rate (NOT per basis point)",
    "dividend_rho": "dV/dq, per 1.00 of the continuously compounded dividend yield",
    "expiry_years": "year fraction under Actual/365 Fixed; exactly expiry_days / 365",
    "note": (
        "Raw partial derivatives as QuantLib returns them. No market scaling is applied: "
        "a per-day theta or a per-point vega would put a convention factor inside the "
        "oracle, where an arithmetic identity belongs. Scale at the point of display."
    ),
}


def price_one(
    option_type: int,
    spot: float,
    strike: float,
    vol: float,
    rate: float,
    dividend_yield: float,
    expiry_days: int,
) -> dict[str, float]:
    """Price one European vanilla and return its value and Greeks, unmodified."""
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
        ql.PlainVanillaPayoff(option_type, strike), ql.EuropeanExercise(expiry)
    )
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))

    return {
        "price": option.NPV(),
        "delta": option.delta(),
        "gamma": option.gamma(),
        "vega": option.vega(),
        "theta": option.theta(),
        "rho": option.rho(),
        "dividend_rho": option.dividendRho(),
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


def build_main_grid() -> list[dict]:
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


def build_edge_block() -> list[dict]:
    cases = []
    for label, spot, strike, vol, rate, dividend_yield, expiry_days in EDGE_CASES:
        for type_name, option_type in OPTION_TYPES:
            case = make_case(
                type_name, option_type, spot, strike, vol, rate, dividend_yield, expiry_days
            )
            cases.append({"label": label, **case})
    return cases


def build_document() -> dict:
    ql.Settings.instance().evaluationDate = EVALUATION_DATE
    return {
        "schema": SCHEMA_ID,
        "generator": "golden/generate_bs_vanilla.py",
        "documentation": "golden/SCHEMA.md",
        "model": (
            "Black-Scholes-Merton: one underlying, constant continuously compounded rate, "
            "constant continuous dividend yield, constant volatility, European exercise"
        ),
        "oracle": {
            "library": "QuantLib",
            "version": ql.__version__,
            "binding": "QuantLib-Python",
            "engine": "AnalyticEuropeanEngine on BlackScholesMertonProcess",
            "day_count": "Actual/365 Fixed",
            "calendar": "NullCalendar",
            "evaluation_date": EVALUATION_DATE.ISO(),
        },
        "conventions": CONVENTIONS,
        "tolerances": {
            "cases": 1e-10,
            "edge_cases": 1e-08,
            "note": (
                "Relative where the reference exceeds 1.0, absolute otherwise. The edge "
                "block is looser by construction, not by concession: see SCHEMA.md."
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
        "counts": {},   # filled below, once the cases exist
        "cases": build_main_grid(),
        "edge_cases": build_edge_block(),
    }


def serialise(doc: dict) -> str:
    """Serialise with one case per line.

    ``json.dump`` with an indent would quadruple the file for no gain; without one it would
    put 7200 cases on a single line, and every regeneration would show as one changed line.
    One case per line means git diffs name the rows that moved.
    """
    head = {k: v for k, v in doc.items() if k not in ("cases", "edge_cases")}
    out = [json.dumps(head, indent=2)[:-2].rstrip()]  # drop the closing brace, keep the rest
    for key in ("cases", "edge_cases"):
        out.append(',\n  "%s": [' % key)
        rows = [
            "    " + json.dumps(case, separators=(",", ":")) for case in doc[key]
        ]
        out.append("\n" + ",\n".join(rows) + "\n  ]")
    out.append("\n}\n")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout", action="store_true", help="write to stdout instead of the JSON file"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="write somewhere other than golden/bs_vanilla.json"
    )
    args = parser.parse_args()

    doc = build_document()
    doc["counts"] = {
        "cases": len(doc["cases"]),
        "edge_cases": len(doc["edge_cases"]),
        "total": len(doc["cases"]) + len(doc["edge_cases"]),
    }
    text = serialise(doc)

    if args.stdout:
        sys.stdout.write(text)
        return 0

    destination = args.out or Path(__file__).with_name("bs_vanilla.json")
    destination.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"wrote {destination} — QuantLib {doc['oracle']['version']}, "
        f"{doc['counts']['cases']} cases + {doc['counts']['edge_cases']} edge cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
