"""Swaps -- the arithmetic behind page 1.3.

Serves page 1.3 (docs/quant-learn-index-v1.md): interest rate swaps;
PV(fixed) - PV(float), the par rate, why the floating leg is worth par at a
reset; PV01 and bucketed curve risk; fixings, resets, netting; and the page's
check -- price a two-year swap by hand from a curve, perturb one curve point,
predict which bucket moves.

Part 1 is arithmetic. Nothing here is random, so there is no seed. Symbols are
the notation ledger's and page 1.0's: z(T) the continuously compounded zero
rate, D(T) = e^(-z(T) T) the discount factor, tau the year fraction of a
period, K the fixed rate in the contract, N the notional. Rates are decimals.

Session decision (owner, 2026-11-16): the swap is the simplest that shows the
floating leg at par on a reset date. Two years; both legs paid every six
months; every period counted as exactly half a year; each floating payment set
at the start of its period at the six-month simple rate, and paid at the end.
The curve is page 1.0's: zero rates of 4.80%, 5.00%, 5.10% and 5.20% at 0.5, 1,
1.5 and 2 years, illustrative. One curve projects the floating rates and
discounts both legs; a desk discounts on a second curve, and the page says so
and does not.

  C1  The curve. The discount factors and the simple forward rate for each
      six months, L_i = (D(T_{i-1}) / D(T_i) - 1) / tau: page 1.0's, read from
      its committed result where it is present.
  C2  The floating leg. Each payment N L_i tau, projected at the forward rate
      and discounted, is worth N (D(T_{i-1}) - D(T_i)). The sum telescopes to
      N (1 - D(T_n)): it needs the last discount factor and no forecast.
  C3  Par at a reset. Add the notional at the end and the floating leg is
      worth exactly N: a floating-rate note prices at par on a reset date.
  C4  The fixed leg and the par rate. PV(fixed) = N K A, with the annuity
      A = tau * (sum of the discount factors). The par rate, at which the swap
      is worth nothing, is K* = (1 - D(T_n)) / A = 5.2608%: the forward rates
      averaged with the discount factors as weights.
  C5  A swap that is not at par. Paying a fixed 5.00% on the same dates is
      worth N (K* - K) A to the payer.
  C6  The first exchange. The first floating rate is known when the swap is
      agreed, so the first net payment is too.
  C7  PV01. Every zero rate up one basis point: the payer of fixed gains
      about 1,924 on ten million. Analytic against a bump.
  C8  Buckets. One zero rate up one basis point at a time. 96% of the par
      swap's risk is at the two-year point; the buckets sum to the PV01.
  C9  One point perturbed. The one-year zero rate up a basis point raises the
      second floating payment and lowers the third; their present values
      cancel, and the swap moves only by the fixed payment at one year being
      discounted a little more.
  C10 The oracle (I4). QuantLib's VanillaSwap on the same curve gives the same
      par rate, floating-leg value, swap value and bucketed risk.

Run from the repository root:

    uv run experiments/1_3_swaps.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_3_swaps.json beside this file: parameters in, results out, no
timestamps. No plotting here; the site draws. Exits non-zero if any check
fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import exp, log
from pathlib import Path

PAGE = "1.3"
BASIS_POINT = 1e-4


# --- the curve -----------------------------------------------------------------


def discount_factors(times: list[float], zero_rates: list[float]) -> list[float]:
    """D(T) = e^(-z(T) T) at each payment date."""
    return [exp(-z * t) for t, z in zip(times, zero_rates)]


def simple_forward_rates(discounts: list[float], tau: float) -> list[float]:
    """The simple rate for each period, fixed by the discount factors at its two ends."""
    starts = [1.0] + discounts[:-1]
    return [(d0 / d1 - 1) / tau for d0, d1 in zip(starts, discounts)]


# --- the swap ------------------------------------------------------------------


def annuity(discounts: list[float], tau: float) -> float:
    """Present value of 1 a year paid in instalments of tau on every payment date."""
    return tau * sum(discounts)


def floating_leg_pv(discounts: list[float], tau: float, notional: float) -> float:
    """Each payment projected at its forward rate and discounted, then summed."""
    forwards = simple_forward_rates(discounts, tau)
    return sum(notional * L * tau * d for L, d in zip(forwards, discounts))


def fixed_leg_pv(discounts: list[float], tau: float, notional: float, K: float) -> float:
    return notional * K * annuity(discounts, tau)


def par_rate(discounts: list[float], tau: float) -> float:
    """The fixed rate at which the two legs are worth the same."""
    return (1 - discounts[-1]) / annuity(discounts, tau)


def payer_swap_value(times: list[float], zero_rates: list[float], tau: float, notional: float, K: float) -> float:
    """Value to the side that pays fixed and receives floating: PV(float) - PV(fixed)."""
    d = discount_factors(times, zero_rates)
    return floating_leg_pv(d, tau, notional) - fixed_leg_pv(d, tau, notional, K)


def bumped(zero_rates: list[float], bump: float, only: int | None = None) -> list[float]:
    """The curve with every zero rate moved by bump, or with one of them moved."""
    return [z + bump if only is None or i == only else z for i, z in enumerate(zero_rates)]


# --- the oracle ----------------------------------------------------------------


def quantlib_oracle(params: dict, res: dict) -> dict | None:
    """QuantLib's swap on the same curve.

    30/360 between dates six months apart gives year fractions of exactly one
    half, which is the page's simplification, so the two can agree to rounding.
    """
    try:
        import QuantLib as ql
    except ImportError:
        return None
    C, S = params["curve"], params["swap"]
    today = ql.Date(1, 3, 2027)
    ql.Settings.instance().evaluationDate = today
    dc = ql.Thirty360(ql.Thirty360.BondBasis)
    cal = ql.NullCalendar()
    months = [round(12 * t) for t in C["times"]]
    dates = [today] + [cal.advance(today, ql.Period(m, ql.Months)) for m in months]
    schedule = ql.Schedule(today, dates[-1], ql.Period(round(12 * S["tau"]), ql.Months), cal, ql.Unadjusted, ql.Unadjusted,
                           ql.DateGeneration.Forward, False)

    def price(zero_rates: list[float], K: float):
        curve = ql.ZeroCurve(dates, [zero_rates[0]] + zero_rates, dc, cal, ql.Linear(), ql.Continuous)
        handle = ql.YieldTermStructureHandle(curve)
        index = ql.IborIndex("six-month", ql.Period(round(12 * S["tau"]), ql.Months), 0, ql.EURCurrency(), cal, ql.Unadjusted, False, dc, handle)
        swap = ql.VanillaSwap(ql.VanillaSwap.Payer, S["notional"], schedule, K, dc, schedule, index, 0.0, dc)
        swap.setPricingEngine(ql.DiscountingSwapEngine(handle))
        return swap

    z = C["zero_rates"]
    par = price(z, S["off_market_fixed_rate"])
    K_star = par.fairRate()
    h = params["bump"]
    buckets = [(price(bumped(z, h, i), K_star).NPV() - price(bumped(z, -h, i), K_star).NPV()) / (2 * h) * BASIS_POINT for i in range(len(z))]
    errors = {
        "par_rate": abs(K_star - res["par"]["par_rate"]),
        "floating_leg_pv": abs(par.floatingLegNPV() - res["floating_leg"]["pv"]),
        "off_market_value": abs(par.NPV() - res["off_market"]["value_to_payer"]),
        "par_swap_value": abs(price(z, K_star).NPV()),
        "buckets": max(abs(a - b["by_bump"]) for a, b in zip(buckets, res["risk"]["buckets"])),
    }
    return {"version": ql.__version__, "par_rate": K_star, "floating_leg_pv": par.floatingLegNPV(),
            "off_market_value": par.NPV(), "buckets": buckets, "errors": errors}


def page_1_0_curve(script_dir: Path) -> list[dict] | None:
    """The curve's rows from 1.0's committed result, if it is beside this script."""
    path = script_dir / "1_0_cash_and_discounting.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)["results"]["curve"]["rows"]


# --- the experiment ------------------------------------------------------------


def run(params: dict) -> dict:
    C, S = params["curve"], params["swap"]
    times, z, tau, N = C["times"], C["zero_rates"], S["tau"], S["notional"]
    n = len(times)
    D = discount_factors(times, z)
    L = simple_forward_rates(D, tau)
    A = annuity(D, tau)
    K_star = par_rate(D, tau)

    # C1 the curve, C2 the floating leg, C4 the fixed leg at the par rate: one row a period
    starts = [1.0] + D[:-1]
    periods = []
    for i in range(n):
        floating_payment = N * L[i] * tau
        fixed_payment = N * K_star * tau
        periods.append({"period": i + 1, "start": times[i] - tau, "end": times[i], "zero_rate": z[i], "discount_factor": D[i],
                        "forward_rate": L[i], "floating_payment": floating_payment, "floating_pv": floating_payment * D[i],
                        "floating_pv_as_difference_of_discount_factors": N * (starts[i] - D[i]),
                        "fixed_payment_at_par": fixed_payment, "fixed_pv_at_par": fixed_payment * D[i],
                        "net_paid_by_fixed_payer_if_fixings_are_the_forwards": fixed_payment - floating_payment})

    float_pv = floating_leg_pv(D, tau, N)
    floating = {"pv": float_pv, "pv_by_telescoping": N * (1 - D[-1]),
                "max_abs_period_error": max(abs(p["floating_pv"] - p["floating_pv_as_difference_of_discount_factors"]) for p in periods),
                "notional_at_maturity_pv": N * D[-1], "with_notional_pv": float_pv + N * D[-1],
                "sum_of_projected_payments_undiscounted": sum(p["floating_payment"] for p in periods)}

    # C4 the par rate
    par = {"annuity": A, "sum_of_discount_factors": sum(D), "par_rate": K_star,
           "par_rate_as_weighted_average_of_forwards": sum(l * d for l, d in zip(L, D)) / sum(D),
           "fixed_payment": N * K_star * tau, "fixed_leg_pv": fixed_leg_pv(D, tau, N, K_star),
           "value_to_payer": payer_swap_value(times, z, tau, N, K_star),
           "par_rate_continuously_compounded": (1 / tau) * log(1 + K_star * tau),
           "lowest_forward": min(L), "highest_forward": max(L)}

    # C5 a swap that is not at par
    K = S["off_market_fixed_rate"]
    off = {"fixed_rate": K, "fixed_payment": N * K * tau, "fixed_leg_pv": fixed_leg_pv(D, tau, N, K), "floating_leg_pv": float_pv,
           "value_to_payer": payer_swap_value(times, z, tau, N, K), "value_to_receiver": -payer_swap_value(times, z, tau, N, K),
           "value_via_par_rate": N * (K_star - K) * A}

    # C6 the first exchange is known at the start
    first = {"floating_rate_fixed_at_start": L[0], "fixed_payment": N * K_star * tau, "floating_payment": N * L[0] * tau,
             "net_paid_by_fixed_payer": N * (K_star - L[0]) * tau, "gross_payments_netted_into_one": 2}

    # C7 PV01, C8 buckets: the par swap, from the side that pays fixed
    h = params["bump"]

    def value(rates: list[float]) -> float:
        return payer_swap_value(times, rates, tau, N, K_star)

    pv01_bump = (value(bumped(z, h)) - value(bumped(z, -h))) / (2 * h) * BASIS_POINT
    buckets = []
    for i in range(n):
        last = i == n - 1
        # d/dz_i of N[(1 - D_n) - K tau sum D_j]: every date discounts its fixed payment;
        # the last date also carries the whole floating leg.
        analytic = N * times[i] * D[i] * (K_star * tau + (1.0 if last else 0.0)) * BASIS_POINT
        by_bump = (value(bumped(z, h, i)) - value(bumped(z, -h, i))) / (2 * h) * BASIS_POINT
        buckets.append({"T": times[i], "analytic": analytic, "by_bump": by_bump})
    total = sum(b["analytic"] for b in buckets)
    for b in buckets:
        b["share_of_total"] = b["analytic"] / total
    risk = {"pv01_payer_by_bump": pv01_bump, "pv01_payer_analytic": total, "pv01_receiver": -total, "buckets": buckets,
            "sum_of_buckets_by_bump": sum(b["by_bump"] for b in buckets),
            "annuity_times_notional_times_one_basis_point": N * A * BASIS_POINT,
            "one_payment_of_the_notional_at_maturity": N * times[-1] * D[-1] * BASIS_POINT}

    # C9 one curve point perturbed: the one-year zero rate up one basis point
    i = S["perturbed_pillar"]
    z_up = bumped(z, BASIS_POINT, i)
    D_up = discount_factors(times, z_up)
    L_up = simple_forward_rates(D_up, tau)
    rows = []
    for j in range(n):
        pay0, pay1 = N * L[j] * tau, N * L_up[j] * tau
        rows.append({"period": j + 1, "forward_rate_change_bp": (L_up[j] - L[j]) / BASIS_POINT, "floating_payment_change": pay1 - pay0,
                     "floating_pv_change": pay1 * D_up[j] - pay0 * D[j],
                     "fixed_pv_change": N * K_star * tau * (D_up[j] - D[j])})
    perturb = {"pillar_T": times[i], "bump_bp": 1.0, "rows": rows,
               "floating_leg_pv_change": sum(r["floating_pv_change"] for r in rows),
               "fixed_leg_pv_change": sum(r["fixed_pv_change"] for r in rows),
               "value_change_to_payer": value(z_up) - value(z)}

    # Figures the page's check questions quote, right answers and wrong ones alike (I5):
    # a wrong option's number is what its misconception computes, so it is computed here.
    quoted = {
        "two_year_zero_rate": z[-1],
        "two_year_zero_rate_compounded_twice_a_year": (exp(z[-1] * tau) - 1) / tau,
        "unweighted_mean_of_forward_rates": sum(L) / n,
        "mean_of_zero_rates": sum(z) / n,
        "floating_leg_if_every_payment_were_today_s_rate": N * L[0] * A,
        "floating_leg_undiscounted": sum(p["floating_payment"] for p in periods),
        "one_year_bucket_if_risk_were_spread_evenly": total / n,
        "second_floating_payment_pv_change_alone": rows[1]["floating_pv_change"],
        "pv01_if_notional_times_years_undiscounted": N * times[-1] * BASIS_POINT,
        "two_year_bucket_share": buckets[-1]["share_of_total"],
    }
    return {"periods": periods, "floating_leg": floating, "par": par, "off_market": off, "first_exchange": first,
            "risk": risk, "perturbation": perturb, "quoted_in_checks": quoted}


def build_checks(res: dict, params: dict, oracle: dict | None, curve_1_0: list[dict] | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    P, fl, par, off, risk, pt = res["periods"], res["floating_leg"], res["par"], res["off_market"], res["risk"], res["perturbation"]
    N = params["swap"]["notional"]

    if curve_1_0 is None:
        if not params["quick"]:
            truth("C1 1.0's committed JSON is beside this script for the full run", False)
    else:
        add("C1 the zero rates are page 1.0's, from that page's committed result", max(abs(p["zero_rate"] - c["zero_rate"]) for p, c in zip(P, curve_1_0)), 0.0, 0.0)
        add("C1 so are the discount factors (1e-12)", max(abs(p["discount_factor"] - c["discount_factor"]) for p, c in zip(P, curve_1_0)), 0.0, 1e-12)
        add("C1 and the simple forward rate for each six months (1e-12)", max(abs(p["forward_rate"] - c["simple_forward_rate"]) for p, c in zip(P, curve_1_0)), 0.0, 1e-12)
    truth("C1 the forward rates rise from period to period on this curve", all(a["forward_rate"] < b["forward_rate"] for a, b in zip(P, P[1:])))

    add("C2 each floating payment is worth N times the fall in the discount factor over its period (1e-9 on ten million)", fl["max_abs_period_error"], 0.0, 1e-9)
    add("C2 the floating leg is worth N (1 - D(2)) (1e-9 relative)", fl["pv"], fl["pv_by_telescoping"], 1e-9, "rel")
    add("C2 which is 987,747 on ten million", fl["pv"], 987_747.0, 0.5)
    add("C3 with the notional at the end it is worth exactly the notional: par (1e-9 relative)", fl["with_notional_pv"], N, 1e-9, "rel")

    add("C4 the annuity is 1.877547", par["annuity"], 1.877547, 5e-7)
    add("C4 the par rate is 5.2608%", par["par_rate"], 0.052608, 5e-7)
    add("C4 at the par rate the swap is worth nothing (1e-8 on ten million)", par["value_to_payer"], 0.0, 1e-8)
    add("C4 the par rate is the forward rates averaged with the discount factors as weights (1e-12)", par["par_rate_as_weighted_average_of_forwards"], par["par_rate"], 1e-12)
    truth("C4 so it lies between the lowest forward rate and the highest", par["lowest_forward"] < par["par_rate"] < par["highest_forward"])
    add("C4 the fixed payment at par is 263,042 every six months", par["fixed_payment"], 263_042.0, 0.5)

    add("C5 paying 5.00% instead is worth 48,974 to the payer", off["value_to_payer"], 48_974.0, 0.5)
    add("C5 which is N (K* - K) A (1e-9 relative)", off["value_to_payer"], off["value_via_par_rate"], 1e-9, "rel")
    add("C5 and the same amount, with the other sign, to the receiver", off["value_to_receiver"], -off["value_to_payer"], 0.0)

    fx = res["first_exchange"]
    add("C6 the first floating rate is 4.8581%, known at the start", fx["floating_rate_fixed_at_start"], 0.048581, 5e-7)
    add("C6 the payer of fixed pays 20,139 net at six months", fx["net_paid_by_fixed_payer"], 20_139.0, 0.5)
    add("C6 which is the fixed payment less the floating payment (1e-9)", fx["net_paid_by_fixed_payer"], fx["fixed_payment"] - fx["floating_payment"], 1e-9)

    add("C7 the PV01 formula agrees with a bump of every zero rate (1e-6 relative)", risk["pv01_payer_analytic"], risk["pv01_payer_by_bump"], 1e-6, "rel")
    add("C7 the payer of fixed gains about 1,924 a basis point on ten million", risk["pv01_payer_analytic"], 1_924.0, 0.5)
    truth("C7 the payer gains when rates rise and the receiver loses the same", risk["pv01_payer_analytic"] > 0 and risk["pv01_receiver"] == -risk["pv01_payer_analytic"])
    add("C8 each bucket's formula agrees with a bump of that zero rate alone (1e-6 relative)", max(abs(b["analytic"] / b["by_bump"] - 1) for b in risk["buckets"]), 0.0, 1e-6)
    add("C8 the buckets sum to the PV01 (1e-6 relative)", risk["sum_of_buckets_by_bump"], risk["pv01_payer_by_bump"], 1e-6, "rel")
    add("C8 the two-year bucket is 96% of the total", risk["buckets"][-1]["share_of_total"], 0.96, 0.005)
    truth("C8 every other bucket is under 2% of it", all(b["share_of_total"] < 0.02 for b in risk["buckets"][:-1]))
    add("C8 one payment of the notional at two years has a PV01 of 1,802, close to the swap's", risk["one_payment_of_the_notional_at_maturity"], 1_802.0, 0.5)

    rows = pt["rows"]
    truth("C9 the one-year zero rate up: the second forward rate rises and the third falls, and the others do not move",
          rows[1]["forward_rate_change_bp"] > 0 > rows[2]["forward_rate_change_bp"] and rows[0]["forward_rate_change_bp"] == 0 == rows[3]["forward_rate_change_bp"])
    add("C9 the floating leg's value does not change (1e-6 on ten million)", pt["floating_leg_pv_change"], 0.0, 1e-6)
    add("C9 the second and third floating payments' values move by the same amount, opposite ways (1e-6)", rows[1]["floating_pv_change"] + rows[2]["floating_pv_change"], 0.0, 1e-6)
    add("C9 the swap moves by the fall in the value of the fixed payment at one year (1e-6)", pt["value_change_to_payer"], -rows[1]["fixed_pv_change"], 1e-6)
    add("C9 which is 25 on ten million: the one-year bucket", pt["value_change_to_payer"], risk["buckets"][1]["analytic"], 0.01)

    qc = res["quoted_in_checks"]
    add("the page's checks: the two-year zero rate is 5.2682% compounded twice a year, above the par rate", qc["two_year_zero_rate_compounded_twice_a_year"], 0.052682, 5e-7)
    truth("the page's checks: the par rate is below it, and below the plain average of the forward rates", par["par_rate"] < qc["two_year_zero_rate_compounded_twice_a_year"] and par["par_rate"] < qc["unweighted_mean_of_forward_rates"])
    add("the page's checks: the plain average of the forward rates is 5.2684%", qc["unweighted_mean_of_forward_rates"], 0.052684, 5e-7)
    add("the page's checks: four payments at today's six-month rate would be worth 912,124", qc["floating_leg_if_every_payment_were_today_s_rate"], 912_124.0, 0.5)
    add("the page's checks: the four projected payments add up to 1,053,671 before discounting", qc["floating_leg_undiscounted"], 1_053_671.0, 0.5)

    if oracle is None:
        if not params["quick"]:
            truth("C10 QuantLib is importable for the full run (I4)", False)
    else:
        e = oracle["errors"]
        add("C10 QuantLib's VanillaSwap gives the same par rate (1e-12)", e["par_rate"], 0.0, 1e-12)
        add("C10 the same floating-leg value (1e-6 on ten million)", e["floating_leg_pv"], 0.0, 1e-6)
        add("C10 the same value for the 5.00% swap (1e-6)", e["off_market_value"], 0.0, 1e-6)
        add("C10 nothing for the par swap (1e-6)", e["par_swap_value"], 0.0, 1e-6)
        add("C10 and the same four buckets (1e-4)", e["buckets"], 0.0, 1e-4)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="snippet check: QuantLib optional, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "random": "none -- arithmetic only, so no seed (I6 has nothing to seed)",
        "curve": {"times": [0.5, 1.0, 1.5, 2.0], "zero_rates": [0.048, 0.05, 0.051, 0.052],
                  "note": "page 1.0's curve: continuously compounded zero rates, illustrative, not a market's"},
        "swap": {"notional": 10_000_000.0, "tau": 0.5, "off_market_fixed_rate": 0.05, "perturbed_pillar": 1,
                 "floating_rate_is": "the six-month simple rate, set at the start of each period and paid at its end",
                 "note": "both legs every six months, every period exactly half a year; one curve projects and discounts"},
        "bump": 1e-6,
    }
    res = run(params)
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C10: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    curve_1_0 = page_1_0_curve(Path(__file__).resolve().parent)
    res["oracle"] = oracle
    checks = build_checks(res, params, oracle, curve_1_0)

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
