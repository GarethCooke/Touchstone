"""Check the committed golden file against an independent implementation.

The generator drives QuantLib. If it drives it *wrongly* -- dividend handle where the rate
handle belongs, a sign convention misread, a Greek accessor that means something other than
what SCHEMA.md claims -- the output is still a perfectly self-consistent file full of wrong
numbers, and nothing in the generator would notice. This script is what notices.

It re-derives every value from the closed form, in plain Python, using ``math.erfc`` -- the
same route ``std::erfc`` gives the C++ at T1 (tech-decision B3), so a disagreement here is a
disagreement the library would also have had.

Four checks:

1. **Closed form.** Price and all six Greeks, every row, against the formulas in SCHEMA.md.
2. **Put-call parity.** C - P = S.exp(-qT) - K.exp(-rT) for every matched pair. The one
   identity that holds whatever the model, so it tests the file rather than the formula.
3. **Schema conformance.** Fields, counts, axes, finiteness, expiry_years == days/365.
4. **Convention sanity.** The claims SCHEMA.md makes about signs and units, asserted rather
   than trusted.

Deviations are reported in units of each quantity's natural scale, not as bare relative
error: a deep out-of-the-money price of 1e-19 has no meaningful relative error, because both
implementations are returning arithmetic noise there. See SCHEMA.md, "Precision".

This is not the C++ test. It is the check that the file the C++ test will trust is worth
trusting. Exit status 0 if every check passes, 1 otherwise.

Usage::

    uv run golden/verify_bs_vanilla.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Agreement threshold for this cross-check, in units of the natural scale defined below.
# Not the golden file's own tolerance -- that is for the C++ and lives in the file's
# "tolerances" block. This says how closely two independent double-precision evaluations of
# the same closed form should agree. Observed worst case is ~4e-16, a couple of ulps; the
# threshold leaves two and a half orders of magnitude of headroom so that a real regression
# trips it and floating-point weather does not.
TOLERANCE = 1e-13

SQRT_2 = math.sqrt(2.0)
SQRT_2PI = math.sqrt(2.0 * math.pi)
EPSILON = sys.float_info.epsilon

GREEKS = ("price", "delta", "gamma", "vega", "theta", "rho", "dividend_rho")


def norm_cdf(x: float) -> float:
    """N(x) via erfc, as std::erfc will give the C++ (B3). Keeps the left tail."""
    return 0.5 * math.erfc(-x / SQRT_2)


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def black_scholes_merton(
    is_call: bool, s: float, k: float, sigma: float, r: float, q: float, t: float
) -> dict[str, float]:
    """Price and raw partial-derivative Greeks. Units exactly as SCHEMA.md states."""
    sqrt_t = math.sqrt(t)
    std = sigma * sqrt_t
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / std
    d2 = d1 - std

    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    pdf_d1 = norm_pdf(d1)

    # w = +1 for a call, -1 for a put: every formula below is sign-symmetric in it.
    w = 1.0 if is_call else -1.0
    n_w_d1 = norm_cdf(w * d1)
    n_w_d2 = norm_cdf(w * d2)

    return {
        "price": w * (s * df_q * n_w_d1 - k * df_r * n_w_d2),
        "delta": w * df_q * n_w_d1,
        "gamma": df_q * pdf_d1 / (s * std),
        "vega": s * df_q * pdf_d1 * sqrt_t,
        "theta": (
            -s * df_q * pdf_d1 * sigma / (2.0 * sqrt_t)
            - w * r * k * df_r * n_w_d2
            + w * q * s * df_q * n_w_d1
        ),
        "rho": w * k * t * df_r * n_w_d2,
        "dividend_rho": -w * t * s * df_q * n_w_d1,
    }


def natural_scale(field: str, case: dict) -> float:
    """The magnitude below which a value carries no information, only rounding.

    Comparing a 1e-19 price relatively is meaningless: at that size both implementations are
    reporting the residue of subtracting two numbers of order S. Each Greek gets the scale
    its formula actually carries.

    ``theta`` is the interesting one. QuantLib derives it by a route that divides by the year
    fraction, so its absolute error grows as 1/T -- measured at a constant one to two ulps of
    S once multiplied back by T, across every expiry in the file. Folding 1/T into the scale
    is what makes a one-day theta and a five-year theta comparable statements.
    """
    spot, strike, t = case["spot"], case["strike"], case["expiry_years"]
    if field == "price":
        return spot
    if field == "delta":
        return 1.0
    if field == "gamma":
        return 1.0 / spot
    if field == "vega":
        return spot
    if field == "theta":
        return spot / t
    if field == "rho":
        return strike * t
    if field == "dividend_rho":
        return spot * t
    raise KeyError(field)


def deviation(actual: float, expected: float, field: str, case: dict) -> float:
    return abs(actual - expected) / max(abs(expected), natural_scale(field, case))


def price_noise_floor(case: dict) -> float:
    """How negative a price may legitimately be: a few ulps of spot.

    A deep out-of-the-money price is the residue of a cancellation between two numbers of
    order S, so it can land on either side of zero. See SCHEMA.md, "Precision".
    """
    return 64.0 * case["spot"] * EPSILON


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.worst: dict[str, tuple[float, str]] = {}

    def record(self, field: str, dev: float, where: str) -> None:
        if dev > self.worst.get(field, (0.0, ""))[0]:
            self.worst[field] = (dev, where)
        if dev > TOLERANCE:
            self.failures.append(f"{field} deviates by {dev:.3e} at {where}")

    def fail(self, message: str) -> None:
        self.failures.append(message)


def describe(case: dict) -> str:
    label = f"{case['label']}/" if "label" in case else ""
    return (
        f"{label}{case['type']} S={case['spot']:g} K={case['strike']:g} "
        f"vol={case['vol']:g} r={case['rate']:g} q={case['dividend_yield']:g} "
        f"T={case['expiry_days']}d"
    )


def check_closed_form(cases: list[dict], report: Report) -> None:
    for case in cases:
        reference = black_scholes_merton(
            case["type"] == "call", case["spot"], case["strike"], case["vol"],
            case["rate"], case["dividend_yield"], case["expiry_years"],
        )
        where = describe(case)
        for field in GREEKS:
            report.record(field, deviation(case[field], reference[field], field, case), where)


def check_parity(cases: list[dict], report: Report) -> int:
    """C - P = S.exp(-qT) - K.exp(-rT): true whatever the model, so it tests the file."""
    by_parameters: dict[tuple, dict[str, dict]] = {}
    for case in cases:
        key = (
            case.get("label"), case["spot"], case["strike"], case["vol"],
            case["rate"], case["dividend_yield"], case["expiry_days"],
        )
        by_parameters.setdefault(key, {})[case["type"]] = case

    pairs = 0
    for key, sides in by_parameters.items():
        if "call" not in sides or "put" not in sides:
            report.fail(f"unmatched call/put at {key}")
            continue
        call, put = sides["call"], sides["put"]
        t = call["expiry_years"]
        expected = (
            call["spot"] * math.exp(-call["dividend_yield"] * t)
            - call["strike"] * math.exp(-call["rate"] * t)
        )
        actual = call["price"] - put["price"]
        report.record(
            "put-call parity",
            abs(actual - expected) / max(abs(expected), call["spot"]),
            describe(call),
        )
        pairs += 1
    return pairs


def check_conventions(cases: list[dict], report: Report) -> None:
    """Assert the signs SCHEMA.md claims, at the file's own noise floor."""
    for case in cases:
        where = describe(case)
        floor = price_noise_floor(case)
        unit = 64.0 * EPSILON

        if case["price"] < -floor:
            report.fail(f"price below the noise floor at {where}: {case['price']:.3e}")
        if case["gamma"] < -floor:
            report.fail(f"negative gamma at {where}: {case['gamma']:.3e}")
        if case["vega"] < -floor:
            report.fail(f"negative vega at {where}: {case['vega']:.3e}")

        if case["type"] == "call":
            if not -unit <= case["delta"] <= 1.0 + unit:
                report.fail(f"call delta outside [0,1] at {where}: {case['delta']:.3e}")
            if case["rho"] < -floor:
                report.fail(f"call rho negative at {where}: {case['rho']:.3e}")
            if case["dividend_rho"] > floor:
                report.fail(f"call dividend_rho positive at {where}")
        else:
            if not -1.0 - unit <= case["delta"] <= unit:
                report.fail(f"put delta outside [-1,0] at {where}: {case['delta']:.3e}")
            if case["rho"] > floor:
                report.fail(f"put rho positive at {where}: {case['rho']:.3e}")
            if case["dividend_rho"] < -floor:
                report.fail(f"put dividend_rho negative at {where}")


def check_schema(document: dict, report: Report) -> None:
    fields = document["fields"]
    expected_counts = {
        "cases": len(document["cases"]),
        "edge_cases": len(document["edge_cases"]),
        "total": len(document["cases"]) + len(document["edge_cases"]),
    }
    if document["counts"] != expected_counts:
        report.fail(f"counts {document['counts']} do not match {expected_counts}")

    axes = document["axes"]
    implied = 1
    for axis in ("spot", "strike", "vol", "rate", "dividend_yield", "expiry_days", "type"):
        implied *= len(axes[axis])
    if len(document["cases"]) != implied:
        report.fail(f"main grid has {len(document['cases'])} rows, axes imply {implied}")

    for name, cases, extra in (
        ("cases", document["cases"], set()),
        ("edge_cases", document["edge_cases"], {"label"}),
    ):
        for case in cases:
            if set(case) != set(fields) | extra:
                report.fail(f"{name}: field set mismatch at {describe(case)}")
                break
            for key, value in case.items():
                if isinstance(value, float) and not math.isfinite(value):
                    report.fail(f"{name}: non-finite {key} at {describe(case)}")
            if case["expiry_years"] != case["expiry_days"] / 365.0:
                report.fail(f"{name}: expiry_years is not days/365 at {describe(case)}")

    for axis in ("spot", "strike", "vol", "rate", "dividend_yield", "expiry_days", "type"):
        seen = {case[axis] for case in document["cases"]}
        if seen != set(axes[axis]):
            report.fail(f"axis {axis}: cases cover {sorted(seen)}, axes declare {sorted(axes[axis])}")


def main() -> int:
    path = Path(__file__).with_name("bs_vanilla.json")
    document = json.loads(path.read_text(encoding="utf-8"))

    print(f"golden file : {path.name}")
    print(f"schema      : {document['schema']}")
    print(f"oracle      : QuantLib {document['oracle']['version']} "
          f"({document['oracle']['engine']})")
    print(f"cases       : {document['counts']['cases']} main + "
          f"{document['counts']['edge_cases']} edge")
    print(f"threshold   : {TOLERANCE:g} of each quantity's natural scale")
    print()

    report = Report()
    all_cases = document["cases"] + document["edge_cases"]

    print("schema conformance ...")
    check_schema(document, report)
    print("closed form against an independent erfc implementation ...")
    check_closed_form(all_cases, report)
    print("put-call parity ...")
    pairs = check_parity(document["cases"], report) + check_parity(document["edge_cases"], report)
    print(f"  {pairs} matched pairs")
    print("sign and unit conventions ...")
    check_conventions(all_cases, report)
    print()

    print("worst deviation by field, in units of the quantity's natural scale:")
    for field in (*GREEKS, "put-call parity"):
        if field in report.worst:
            dev, where = report.worst[field]
            print(f"  {field:16s} {dev:.3e}   {where}")
    print()

    if report.failures:
        print(f"FAIL — {len(report.failures)} problem(s):")
        for failure in report.failures[:40]:
            print(f"  {failure}")
        if len(report.failures) > 40:
            print(f"  ... and {len(report.failures) - 40} more")
        return 1

    print(f"PASS — {len(all_cases)} cases x 7 fields, plus parity on {pairs} pairs, "
          f"all within {TOLERANCE:g} of an independent implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
