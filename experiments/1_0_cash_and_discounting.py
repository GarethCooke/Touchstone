"""Cash and discounting -- the arithmetic behind page 1.0.

Serves page 1.0 (docs/quant-learn-index-v1.md): time value, discount factors,
zero and forward curves, compounding conventions, and the page's check -- the
day-count bug, a 6-month deposit priced with the wrong convention.

Part 1 is arithmetic. Nothing here is random, so there is no seed; the same
inputs give the same file. Rates follow page 0.3: decimals, and continuously
compounded unless a row says otherwise. A discount factor is written DF.

Setup: the scripts that back Part 1 live here,
one per page, as Part 2's do; the day-count bug is a sterling deposit, right on
Actual/365 Fixed, priced by a system that defaults to Actual/360.

  C1  Compounding. 100 at 5 % for one year, compounded 1, 2, 4, 12 and 365
      times a year and continuously: the amount rises with the frequency and
      converges on 100 e^0.05. A rate is a number plus a convention: 5 %
      compounded annually is 4.879 % continuous, and 5 % continuous is 5.127 %
      annual. The conversions are exact and invert each other (1e-13).
  C2  Discount factors, zero rates and forward rates on one small curve: zero
      rates at 0.5, 1, 1.5 and 2 years, illustrative, not a market's. DF(T) =
      e^(-zT). The forward rate between two pillars is the rate that makes
      "invest to the far date" equal "invest to the near date, then roll":
      f = (z2 T2 - z1 T1) / (T2 - T1), and the forward discount factors
      multiply back to DF(2). On a rising curve every forward is above the
      zero rate at its end date.
  C3  The deposit and the day count -- the page's check. 10,000,000 placed on
      1 March 2027 for six months at 5 % simple, repaid on 1 September 2027:
      184 actual days. The year fraction is 184/365 on Actual/365 Fixed,
      184/360 on Actual/360 and 180/360 on 30/360. Interest is notional x
      rate x year fraction, so the wrong convention is a wrong payment: the
      Actual/360 figure is 365/360 of the right one, 1/72 too much, 3,500.76
      here -- the same as quoting the rate 6.94 basis points too high.
  C4  One deposit quote gives one discount factor: DF = 1 / (1 + R tau), and
      from it a continuously compounded zero rate, -ln(DF) / tau. This is how
      the short end of a curve is built from quotes.
  C5  Risk. The present value of one payment is N e^(-zT), and its
      sensitivity to the rate is -T x PV: a payment twice as far away moves
      twice as much, per pound of present value, for the same move in its
      rate. Per basis point this is the PV01. Analytic against a central bump
      (1e-6 relative).
  C6  The oracle (I4). QuantLib's day counters give the same year fractions on
      the deposit's dates and on every pair of month-starts and month-ends
      from 2026 to 2029; its InterestRate gives the same conversions,
      discount factors and forward rates (1e-12).

Run from the repository root:

    uv run experiments/1_0_cash_and_discounting.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_0_cash_and_discounting.json beside this file: parameters in, results
out, no timestamps. No plotting here; the site draws (see
experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from math import exp, log
from pathlib import Path

PAGE = "1.0"
BASIS_POINT = 1e-4


# --- day counts: the fraction of a year between two dates ---------------------
#
# A deposit pays notional x rate x (fraction of a year). The fraction is not a
# fact about the calendar. It is a convention, and each market has its own.


def days_actual(start: date, end: date) -> int:
    """The days actually elapsed."""
    return (end - start).days


def days_30_360(start: date, end: date) -> int:
    """30/360 (Bond Basis): every month counts as 30 days, every year as 360."""
    d1 = min(start.day, 30)
    d2 = 30 if (end.day == 31 and d1 == 30) else end.day
    return 360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)


DAY_COUNTS = {
    "ACT/365F": lambda start, end: days_actual(start, end) / 365,  # sterling money markets
    "ACT/360": lambda start, end: days_actual(start, end) / 360,   # dollar and euro money markets
    "30/360": lambda start, end: days_30_360(start, end) / 360,    # many fixed-rate bonds
}


def year_fraction(start: date, end: date, convention: str) -> float:
    return DAY_COUNTS[convention](start, end)


def deposit_interest(notional: float, rate: float, start: date, end: date, convention: str) -> float:
    """Simple interest, paid with the principal at maturity."""
    return notional * rate * year_fraction(start, end, convention)


# --- compounding: one rate, several conventions -------------------------------


def growth(rate: float, years: float, per_year: int | None) -> float:
    """What 1 grows to. per_year = None is continuous compounding."""
    if per_year is None:
        return exp(rate * years)
    return (1 + rate / per_year) ** (per_year * years)


def to_continuous(rate: float, per_year: int) -> float:
    """The continuous rate that grows 1 to the same amount."""
    return per_year * log(1 + rate / per_year)


def from_continuous(rate: float, per_year: int) -> float:
    """The rate compounded per_year times that grows 1 to the same amount."""
    return per_year * (exp(rate / per_year) - 1)


# --- discount factors, zero rates, forward rates ------------------------------


def discount_factor(zero_rate: float, years: float) -> float:
    """Today's value of 1 paid in `years`, at a continuously compounded rate."""
    return exp(-zero_rate * years)


def forward_rate(z1: float, t1: float, z2: float, t2: float) -> float:
    """The continuous rate from t1 to t2 implied by the zero rates at t1 and t2."""
    return (z2 * t2 - z1 * t1) / (t2 - t1)


def deposit_discount_factor(rate: float, tau: float) -> float:
    """The discount factor a simple deposit rate implies over its own period."""
    return 1 / (1 + rate * tau)


def pv01(notional: float, zero_rate: float, years: float) -> float:
    """Change in present value for a one-basis-point rise in the zero rate."""
    return -years * notional * discount_factor(zero_rate, years) * BASIS_POINT


# --- the oracle ---------------------------------------------------------------


def month_grid(first_year: int, last_year: int) -> list[date]:
    """Every month's first day, 30th (where it exists) and last day."""
    out = []
    for y in range(first_year, last_year + 1):
        for m in range(1, 13):
            nxt = date(y + (m == 12), m % 12 + 1, 1)
            last = nxt - timedelta(days=1)
            out.append(date(y, m, 1))
            if last.day >= 30:
                out.append(date(y, m, 30))
            out.append(last)
    return sorted(set(out))


def quantlib_oracle(params: dict, res: dict) -> dict | None:
    try:
        import QuantLib as ql
    except ImportError:
        return None
    counters = {"ACT/365F": ql.Actual365Fixed(), "ACT/360": ql.Actual360(), "30/360": ql.Thirty360(ql.Thirty360.BondBasis)}

    def qd(d: date):
        return ql.Date(d.day, d.month, d.year)

    start, end = date.fromisoformat(params["deposit"]["start"]), date.fromisoformat(params["deposit"]["end"])
    deposit = {name: abs(dc.yearFraction(qd(start), qd(end)) - year_fraction(start, end, name)) for name, dc in counters.items()}

    grid = month_grid(*params["oracle_grid_years"])
    worst = dict.fromkeys(counters, 0.0)
    pairs = 0
    for i, a in enumerate(grid):
        for b in grid[i + 1:]:
            pairs += 1
            for name, dc in counters.items():
                worst[name] = max(worst[name], abs(dc.yearFraction(qd(a), qd(b)) - year_fraction(a, b, name)))

    dc = ql.Actual365Fixed()
    R = params["compounding"]["rate"]
    freq = {1: ql.Annual, 2: ql.Semiannual, 4: ql.Quarterly, 12: ql.Monthly}
    conv = 0.0
    for m, f in freq.items():
        ours = to_continuous(R, m)
        theirs = ql.InterestRate(R, dc, ql.Compounded, f).equivalentRate(ql.Continuous, ql.Annual, 1.0).rate()
        back = ql.InterestRate(R, dc, ql.Continuous, ql.Annual).equivalentRate(ql.Compounded, f, 1.0).rate()
        conv = max(conv, abs(ours - theirs), abs(from_continuous(R, m) - back))

    curve = 0.0
    rows = res["curve"]["rows"]
    for i, row in enumerate(rows):
        T, z = row["T"], row["zero_rate"]
        curve = max(curve, abs(ql.InterestRate(z, dc, ql.Continuous, ql.Annual).discountFactor(T) - row["discount_factor"]))
        t0, df0 = (rows[i - 1]["T"], rows[i - 1]["discount_factor"]) if i else (0.0, 1.0)
        fwd = ql.InterestRate.impliedRate(df0 / row["discount_factor"], dc, ql.Continuous, ql.Annual, T - t0).rate()
        curve = max(curve, abs(fwd - row["forward_rate_from_previous"]))

    dep = res["deposit"]
    simple = ql.InterestRate(params["deposit"]["rate"], counters["ACT/365F"], ql.Simple, ql.Annual)
    dep_df = abs(simple.discountFactor(qd(start), qd(end)) - dep["discount_factor"])
    return {"version": ql.__version__, "deposit_year_fraction_max_abs_error": deposit,
            "grid": {"years": params["oracle_grid_years"], "dates": len(grid), "pairs": pairs, "max_abs_error": worst},
            "conversion_max_abs_error": conv, "curve_max_abs_error": curve, "deposit_discount_factor_abs_error": dep_df}


# --- the experiment -----------------------------------------------------------


def run(params: dict) -> dict:
    # C1 compounding
    C = params["compounding"]
    R, principal, years = C["rate"], C["principal"], C["years"]
    table = [{"per_year": m, "label": lab, "amount": principal * growth(R, years, m)}
             for m, lab in ((1, "annual"), (2, "semi-annual"), (4, "quarterly"), (12, "monthly"), (365, "daily"), (None, "continuous"))]
    conversions = {
        "annual_to_continuous": to_continuous(R, 1), "continuous_to_annual": from_continuous(R, 1),
        "semiannual_to_continuous": to_continuous(R, 2), "continuous_to_semiannual": from_continuous(R, 2),
        "round_trip_max_abs_error": max(abs(from_continuous(to_continuous(R, m), m) - R) for m in (1, 2, 4, 12, 365)),
    }

    # C2 the curve
    K = params["curve"]
    rows, prev_T, prev_z, prev_df = [], 0.0, 0.0, 1.0
    for T, z in zip(K["T"], K["zero_rates"]):
        df = discount_factor(z, T)
        f = forward_rate(prev_z, prev_T, z, T)
        rows.append({"T": T, "zero_rate": z, "discount_factor": df, "forward_from": prev_T, "forward_rate_from_previous": f,
                     "forward_discount_factor": df / prev_df, "simple_forward_rate": (prev_df / df - 1) / (T - prev_T),
                     "roll_matches_direct_abs_error": abs(exp(prev_z * prev_T) * exp(f * (T - prev_T)) - exp(z * T))})
        prev_T, prev_z, prev_df = T, z, df
    product = 1.0
    for row in rows:
        product *= row["forward_discount_factor"]
    curve = {"rows": rows, "product_of_forward_discount_factors": product,
             "every_forward_above_its_zero_rate": all(r["forward_rate_from_previous"] >= r["zero_rate"] for r in rows)}

    # C3 the deposit and the day count
    D = params["deposit"]
    start, end = date.fromisoformat(D["start"]), date.fromisoformat(D["end"])
    N, rate, right, wrong = D["notional"], D["rate"], D["right_convention"], D["wrong_convention"]
    by_convention = {name: {"days": days_30_360(start, end) if name == "30/360" else days_actual(start, end),
                            "year_fraction": year_fraction(start, end, name),
                            "interest": deposit_interest(N, rate, start, end, name)} for name in DAY_COUNTS}
    i_right, i_wrong = by_convention[right]["interest"], by_convention[wrong]["interest"]
    tau = by_convention[right]["year_fraction"]
    df = deposit_discount_factor(rate, tau)
    deposit = {
        "start_weekday": start.strftime("%A"), "end_weekday": end.strftime("%A"), "actual_days": days_actual(start, end),
        "by_convention": by_convention,
        "error": i_wrong - i_right, "error_as_fraction_of_interest": i_wrong / i_right - 1,
        "error_as_rate_basis_points": rate * (by_convention[wrong]["year_fraction"] / tau - 1) / BASIS_POINT,
        "error_30_360": by_convention["30/360"]["interest"] - i_right,
        "repayment": N + i_right, "repayment_wrong": N + i_wrong,
        # C4 one quote, one discount factor
        "discount_factor": df, "continuous_zero_rate": -log(df) / tau,
        "discount_factor_wrong_convention": deposit_discount_factor(rate, by_convention[wrong]["year_fraction"]),
    }

    # C5 risk
    P = params["pv01"]
    h = P["bump"]
    risk_rows = []
    for T, z in zip(K["T"], K["zero_rates"]):
        pv = P["notional"] * discount_factor(z, T)
        bumped = (P["notional"] * discount_factor(z + h, T) - P["notional"] * discount_factor(z - h, T)) / (2 * h) * BASIS_POINT
        risk_rows.append({"T": T, "zero_rate": z, "present_value": pv, "pv01": pv01(P["notional"], z, T), "pv01_by_bump": bumped,
                          "pv01_per_unit_pv": pv01(P["notional"], z, T) / pv})
    # Figures the page's check questions quote, right answers and wrong ones alike (I5):
    # a wrong option's number is what its misconception computes, so it is computed here.
    quoted = {
        "error_on_a_book_100_times_the_deposit": 100 * (i_wrong - i_right),
        "five_days_of_interest": N * rate * 5 / 365,
        "wrong_rate_equivalent": rate * by_convention[wrong]["year_fraction"] / tau,
        "annual_read_as_continuous_basis_points": (from_continuous(R, 1) - R) / BASIS_POINT,
        "pv_100_in_a_year_continuous": principal * discount_factor(R, 1.0),
        "pv_100_in_a_year_annual": principal / (1 + R),
        "fv_100_in_a_year_continuous": principal * growth(R, 1.0, None),
        "average_of_last_two_zero_rates": (K["zero_rates"][-2] + K["zero_rates"][-1]) / 2,
        "pv01_ratio_2y_to_6m": risk_rows[-1]["pv01"] / risk_rows[0]["pv01"],
    }
    return {"compounding": {"table": table, "limit": principal * exp(R * years), "conversions": conversions},
            "curve": curve, "deposit": deposit, "pv01": {"rows": risk_rows}, "quoted_in_checks": quoted}


def build_checks(res: dict, params: dict, oracle: dict | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    comp, curve, dep = res["compounding"], res["curve"], res["deposit"]
    amounts = [row["amount"] for row in comp["table"]]
    truth("C1 the amount rises with the compounding frequency, annual to continuous", all(a < b for a, b in zip(amounts, amounts[1:])))
    add("C1 annual compounding at 5 % turns 100 into 105.00", amounts[0], 105.0, 1e-12)
    add("C1 continuous compounding at 5 % turns 100 into 105.13 (100 e^0.05)", amounts[-1], 105.12710963760242, 1e-12)
    add("C1 daily compounding is within half a penny of continuous on 100", amounts[-1] - amounts[-2], 0.0, 0.005)
    add("C1 5 % annual = 4.879 % continuous", comp["conversions"]["annual_to_continuous"], 0.04879, 5e-6)
    add("C1 5 % continuous = 5.127 % annual", comp["conversions"]["continuous_to_annual"], 0.05127, 5e-6)
    add("C1 the conversions invert each other (1e-13)", comp["conversions"]["round_trip_max_abs_error"], 0.0, 1e-13)

    rows = curve["rows"]
    add("C2 the forward discount factors multiply back to DF(2) (1e-12)", curve["product_of_forward_discount_factors"], rows[-1]["discount_factor"], 1e-12)
    add("C2 invest-then-roll equals invest-direct at every pillar (1e-12)", max(r["roll_matches_direct_abs_error"] for r in rows), 0.0, 1e-12)
    truth("C2 on a rising curve every forward rate is at or above the zero rate at its end date", curve["every_forward_above_its_zero_rate"])
    add("C2 the forward rate from 1.5 to 2 years is 5.50 %", rows[-1]["forward_rate_from_previous"], 0.055, 1e-12)

    truth("C3 the deposit starts and ends on a weekday", dep["start_weekday"] not in ("Saturday", "Sunday") and dep["end_weekday"] not in ("Saturday", "Sunday"))
    add("C3 the deposit runs 184 actual days", dep["actual_days"], 184, 0)
    add("C3 30/360 counts the same six months as 180 days", dep["by_convention"]["30/360"]["days"], 180, 0)
    add("C3 interest on Actual/365 Fixed is 252,054.79", dep["by_convention"]["ACT/365F"]["interest"], 252054.79, 0.005)
    add("C3 interest on Actual/360 is 255,555.56", dep["by_convention"]["ACT/360"]["interest"], 255555.56, 0.005)
    add("C3 interest on 30/360 is 250,000.00", dep["by_convention"]["30/360"]["interest"], 250000.00, 0.005)
    add("C3 the Actual/360 figure is too high by 3,500.76", dep["error"], 3500.76, 0.005)
    add("C3 the error is 1/72 of the interest, whatever the rate, the amount or the dates", dep["error_as_fraction_of_interest"], 1 / 72, 1e-12)
    add("C3 the error is the same as a rate 6.94 basis points too high", dep["error_as_rate_basis_points"], 6.94, 0.005)

    add("C4 the deposit implies a discount factor of 0.97541", dep["discount_factor"], 0.97541, 5e-6)
    add("C4 and a continuous zero rate of 4.938 %", dep["continuous_zero_rate"], 0.04938, 5e-6)
    add("C4 the discount factor repays to exactly 1: DF x (1 + R tau) = 1", dep["discount_factor"] * dep["repayment"] / params["deposit"]["notional"], 1.0, 1e-12)

    risk = res["pv01"]["rows"]
    add("C5 analytic PV01 agrees with a central bump at every pillar (1e-6 relative)",
        max(abs(r["pv01_by_bump"] / r["pv01"] - 1) for r in risk), 0.0, 1e-6)
    truth("C5 PV01 per unit of present value is -T basis points: proportional to the time to payment",
          all(abs(r["pv01_per_unit_pv"] + r["T"] * BASIS_POINT) < 1e-18 for r in risk))
    add("C5 1,000,000 due in two years is worth 901,225.30 and loses 180.25 for a basis point", risk[-1]["pv01"], -180.25, 0.005)

    qc = res["quoted_in_checks"]
    add("the page's checks: 100 at 5 % continuous for a year is worth 95.12 today", qc["pv_100_in_a_year_continuous"], 95.12, 0.005)
    add("the page's checks: two payments of 1,000,000, at 2 years and at 6 months: the PV01s are 3.69 to 1, not 4 to 1", qc["pv01_ratio_2y_to_6m"], 3.69, 0.005)
    add("the page's checks: reading 5 % annual as continuous overstates the rate by 12.7 basis points", qc["annual_read_as_continuous_basis_points"], 12.7, 0.05)

    if oracle is None:
        if not params["quick"]:
            truth("C6 QuantLib is importable for the full run (I4)", False)
    else:
        add("C6 QuantLib's day counters agree on the deposit's dates (1e-12)", max(oracle["deposit_year_fraction_max_abs_error"].values()), 0.0, 1e-12)
        add(f"C6 and on {oracle['grid']['pairs']} pairs of month-starts, 30ths and month-ends (1e-12)", max(oracle["grid"]["max_abs_error"].values()), 0.0, 1e-12)
        add("C6 QuantLib's InterestRate gives the same conversions (1e-12)", oracle["conversion_max_abs_error"], 0.0, 1e-12)
        add("C6 and the same discount factors and forward rates (1e-12)", oracle["curve_max_abs_error"], 0.0, 1e-12)
        add("C6 and the same discount factor for the deposit (1e-12)", oracle["deposit_discount_factor_abs_error"], 0.0, 1e-12)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="snippet check: QuantLib optional, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "random": "none -- arithmetic only, so no seed (I6 has nothing to seed)",
        "compounding": {"principal": 100.0, "rate": 0.05, "years": 1.0},
        "curve": {"T": [0.5, 1.0, 1.5, 2.0], "zero_rates": [0.048, 0.050, 0.051, 0.052],
                  "note": "continuously compounded zero rates; illustrative, not a market's"},
        "deposit": {"currency": "GBP", "notional": 10_000_000.0, "rate": 0.05, "start": "2027-03-01", "end": "2027-09-01",
                    "right_convention": "ACT/365F", "wrong_convention": "ACT/360",
                    "note": "simple interest paid at maturity; both dates are weekdays, so no date is adjusted"},
        "pv01": {"notional": 1_000_000.0, "bump": 1e-6},
        "oracle_grid_years": [2026, 2029],
    }
    res = run(params)
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C6: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    res["oracle"] = oracle
    checks = build_checks(res, params, oracle)

    out = {"page": PAGE, "script": Path(__file__).name, "params": params,
           "environment": {"quantlib": oracle["version"] if oracle else None}, "results": res, "checks": checks}
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[{PAGE}] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  ({c['measured']:.6g} vs {c['expected']:.6g})")
    print(f"[{PAGE}] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} ({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
