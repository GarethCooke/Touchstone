"""The trade lifecycle and the risk system -- the arithmetic behind page 1.5.

Serves page 1.5 (docs/quant-learn-index-v1.md): capture, confirmation,
settlement, lifecycle events, end-of-day risk and P&L, reporting; pricing,
risk and P&L explain as system components; why the batch reruns everything
overnight; and the page's check -- order the events of a swap's life and name
the system that owns each.

The page is about systems, and most of it is the owner's account of them. This
file backs the numbers it carries. Part 1 is arithmetic. Nothing here is
random, so there is no seed.

Session decision (owner, 2026-11-16): the page follows one trade, page 1.3's
swap -- two years, 10,000,000 euros, both legs every six months, on page 1.0's
curve, at the par rate, seen from the side that pays fixed. The swap's
functions are page 1.3's and are imported from its script, so that each is
defined once. One function is new here: the swap's value once its first
fixing has been read and some time has passed, which page 1.3 left out.

  C1  The swap is page 1.3's: the par rate, the buckets and the first net
      payment, from that page's committed result.
  C2  The schedule. The events the contract fixes in advance, in order, with
      the amount each moves if every later fixing comes in at its forward.
  C3  A fixing changes the risk. Before the first fixing is read, the first
      floating payment moves with the curve; afterwards it is a known amount.
      The six-month bucket goes from +12.84 to -487.16 and the PV01 from
      1,924 to 1,424. Nothing in the market moved.
  C4  One day's P&L, explained. A day passes and the curve moves by 1, 2, 3
      and 4 basis points at its four points. The actual P&L is two full
      revaluations. The explained P&L is the passing of the day, plus last
      night's buckets times the moves. The rest is unexplained.
  C5  A fixing that differs from its forward. If the second fixing is read at
      5.10% where the curve had 5.2682%, the payment at one year changes by a
      known amount.
  C6  Linear risk changes slowly. A whole percentage point on every rate
      changes the swap's PV01 by 2.5%. Page 1.4's call changes its delta
      by a quarter when the share moves from 100 to 120.
  C7  The oracle (I4). QuantLib's swap, with the first fixing stored and the
      evaluation date moved on a day, gives the same values and buckets.

Run from the repository root:

    uv run experiments/1_5_trade_lifecycle.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_5_trade_lifecycle.json beside this file: parameters in, results out,
no timestamps. No plotting here; the site draws. Exits non-zero if any check
fails.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

PAGE = "1.5"
BASIS_POINT = 1e-4

# Page 1.3's swap, defined once, in that page's script. A module whose name
# starts with a digit cannot be named in an import statement.
swaps = importlib.import_module("1_3_swaps")


# --- the swap once its first fixing is read ------------------------------------


def payer_value_after_first_fixing(times: list[float], zero_rates: list[float], tau: float, notional: float, K: float,
                                   first_fixing: float, elapsed: float = 0.0) -> float:
    """Value to the payer of fixed when the first floating payment is a known amount.

    elapsed is the time since the swap was agreed, less than one period. Each
    zero rate belongs to its payment date and is applied to the time left to it.
    The known payment is discounted from the first date. The floating payments
    after it are worth D(T_1) - D(T_n), as on page 1.3.
    """
    D = swaps.discount_factors([t - elapsed for t in times], zero_rates)
    floating = notional * first_fixing * tau * D[0] + notional * (D[0] - D[-1])
    return floating - swaps.fixed_leg_pv(D, tau, notional, K)


def buckets(value, zero_rates: list[float], h: float) -> list[float]:
    """The change in value, per basis point, when one zero rate moves and the rest do not."""
    return [(value(swaps.bumped(zero_rates, h, i)) - value(swaps.bumped(zero_rates, -h, i))) / (2 * h) * BASIS_POINT
            for i in range(len(zero_rates))]


# --- the oracle ----------------------------------------------------------------


def quantlib_oracle(params: dict, res: dict) -> dict | None:
    """QuantLib's swap with the first fixing stored, on the day it is agreed and a day later.

    30/360 between dates six months apart gives year fractions of exactly one
    half, and one day is then 1/360 of a year, which is the page's day.
    """
    try:
        import QuantLib as ql
    except ImportError:
        return None
    C, S, D = params["curve"], params["swap"], params["day"]
    start = ql.Date(1, 3, 2027)
    dc = ql.Thirty360(ql.Thirty360.BondBasis)
    cal = ql.NullCalendar()
    months = [round(12 * t) for t in C["times"]]
    pay_dates = [cal.advance(start, ql.Period(m, ql.Months)) for m in months]
    period = ql.Period(round(12 * S["tau"]), ql.Months)
    schedule = ql.Schedule(start, pay_dates[-1], period, cal, ql.Unadjusted, ql.Unadjusted, ql.DateGeneration.Forward, False)
    K, fixing = res["swap"]["par_rate"], res["swap"]["first_fixing"]

    def value(today, zero_rates: list[float]) -> float:
        ql.Settings.instance().evaluationDate = today
        curve = ql.ZeroCurve([today] + pay_dates, [zero_rates[0]] + zero_rates, dc, cal, ql.Linear(), ql.Continuous)
        handle = ql.YieldTermStructureHandle(curve)
        index = ql.IborIndex("six-month-1-5", period, 0, ql.EURCurrency(), cal, ql.Unadjusted, False, dc, handle)
        index.clearFixings()
        index.addFixing(start, fixing)
        swap = ql.VanillaSwap(ql.VanillaSwap.Payer, S["notional"], schedule, K, dc, schedule, index, 0.0, dc)
        swap.setPricingEngine(ql.DiscountingSwapEngine(handle))
        return swap.NPV()

    z0, z1, h = C["zero_rates"], res["explain"]["zero_rates_after"], params["bump"]
    next_day = start + round(360 * D["elapsed"])
    ladder = buckets(lambda rates: value(start, rates), z0, h)
    out = {"version": ql.__version__, "value_when_agreed": value(start, z0), "value_next_day_same_rates": value(next_day, z0),
           "value_next_day_new_rates": value(next_day, z1), "buckets_after_first_fixing": ladder}
    out["errors"] = {
        "value_when_agreed": abs(out["value_when_agreed"]),
        "value_next_day_same_rates": abs(out["value_next_day_same_rates"] - res["explain"]["value_next_day_same_rates"]),
        "value_next_day_new_rates": abs(out["value_next_day_new_rates"] - res["explain"]["value_next_day_new_rates"]),
        "buckets": max(abs(a - b["after_first_fixing"]) for a, b in zip(ladder, res["fixing_changes_risk"]["buckets"])),
    }
    return out


def committed(script_dir: Path, name: str) -> dict | None:
    """Another page's committed result, if it is beside this script."""
    path = script_dir / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- the experiment ------------------------------------------------------------


def run(params: dict) -> dict:
    C, S = params["curve"], params["swap"]
    times, z, tau, N, h = C["times"], C["zero_rates"], S["tau"], S["notional"], params["bump"]
    n = len(times)
    D = swaps.discount_factors(times, z)
    L = swaps.simple_forward_rates(D, tau)
    K = swaps.par_rate(D, tau)
    fixed_payment = N * K * tau

    # C1 the swap
    swap = {"par_rate": K, "fixed_payment": fixed_payment, "first_fixing": L[0], "forward_rates": L,
            "value_when_agreed": swaps.payer_swap_value(times, z, tau, N, K)}

    # C2 the schedule: what the contract fixes in advance, in order
    events = [{"at": 0.0, "event": "the swap is agreed", "amount": None},
              {"at": 0.0, "event": "reset 1: the fixing for the first period is read", "rate": L[0], "amount": None}]
    for i in range(n):
        floating = N * L[i] * tau
        events.append({"at": times[i], "event": f"payment {i + 1}: the two legs are netted and one amount is paid",
                       "fixed": fixed_payment, "floating_if_the_fixing_is_the_forward": floating,
                       "amount": fixed_payment - floating, "known_when_agreed": i == 0})
        if i < n - 1:
            events.append({"at": times[i], "event": f"reset {i + 2}: the fixing for the next period is read", "rate_if_the_forward": L[i + 1], "amount": None})
    events.append({"at": times[-1], "event": "the swap matures", "amount": None})
    schedule = {"events": events, "resets": sum(e["event"].startswith("reset") for e in events),
                "payments": sum(e["event"].startswith("payment") for e in events),
                "business_days": round(params["business_days_a_year"] * times[-1])}

    # C3 a fixing changes the risk
    def before(rates):
        return swaps.payer_swap_value(times, rates, tau, N, K)

    def after(rates):
        return payer_value_after_first_fixing(times, rates, tau, N, K, L[0])

    ladder_before, ladder_after = buckets(before, z, h), buckets(after, z, h)
    fixing = {"buckets": [{"T": t, "before_first_fixing": a, "after_first_fixing": b, "change": b - a}
                          for t, a, b in zip(times, ladder_before, ladder_after)],
              "pv01_before": sum(ladder_before), "pv01_after": sum(ladder_after),
              "value_before": before(z), "value_after": after(z),
              "a_deposit_of_the_notional_and_first_interest_to_six_months": -N * (1 + L[0] * tau) * times[0] * D[0] * BASIS_POINT}

    # C4 one day's P&L, explained from last night's risk
    day = params["day"]
    elapsed, moves_bp = day["elapsed"], day["moves_bp"]
    z_after = [zi + m * BASIS_POINT for zi, m in zip(z, moves_bp)]
    v0 = after(z)
    v_time = payer_value_after_first_fixing(times, z, tau, N, K, L[0], elapsed)
    v1 = payer_value_after_first_fixing(times, z_after, tau, N, K, L[0], elapsed)
    by_bucket = [{"T": t, "bucket": b, "move_bp": m, "explained": b * m} for t, b, m in zip(times, ladder_after, moves_bp)]
    rates_explained = sum(row["explained"] for row in by_bucket)
    explain = {"zero_rates_after": z_after, "value_last_night": v0, "value_next_day_same_rates": v_time, "value_next_day_new_rates": v1,
               "actual": v1 - v0, "time": v_time - v0, "rates_by_bucket": by_bucket, "rates": rates_explained,
               "explained": (v_time - v0) + rates_explained, "unexplained": (v1 - v0) - (v_time - v0) - rates_explained,
               "accrual_for_the_day": N * (L[0] - K) * elapsed}
    explain["unexplained_share_of_actual"] = explain["unexplained"] / explain["actual"]

    # C5 a fixing that differs from its forward
    alt = params["second_fixing_if_different"]
    surprise = {"forward": L[1], "fixing": alt, "floating_payment_projected": N * L[1] * tau, "floating_payment_fixed": N * alt * tau,
                "net_paid_by_fixed_payer_projected": fixed_payment - N * L[1] * tau, "net_paid_by_fixed_payer_fixed": fixed_payment - N * alt * tau,
                "change_in_the_payment": N * (L[1] - alt) * tau}

    # C6 linear risk changes slowly
    shift = params["large_shift_bp"]
    z_shifted = swaps.bumped(z, shift * BASIS_POINT)
    pv01_shifted = sum(buckets(after, z_shifted, h))
    slow = {"shift_bp": shift, "pv01": fixing["pv01_after"], "pv01_after_shift": pv01_shifted,
            "relative_change": pv01_shifted / fixing["pv01_after"] - 1}

    quoted = {
        "pv01_if_the_fixing_changed_nothing": fixing["pv01_before"],
        "rates_explained_if_last_night_s_risk_ignored_the_fixing": sum(a * m for a, m in zip(ladder_before, moves_bp)),
        "rates_explained_if_the_pv01_times_the_average_move": fixing["pv01_after"] * sum(moves_bp) / n,
        "second_payment_if_the_forward_were_paid": fixed_payment - N * L[1] * tau,
        "pv01_if_each_floating_payment_carried_a_quarter_of_it": fixing["pv01_before"] * (n - 1) / n,
        "actual_p_and_l": explain["actual"],
    }
    return {"swap": swap, "schedule": schedule, "fixing_changes_risk": fixing, "explain": explain,
            "second_fixing": surprise, "linear_risk_changes_slowly": slow, "quoted_in_checks": quoted}


def build_checks(res: dict, params: dict, oracle: dict | None, r13: dict | None, r14: dict | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    sw, sch, fx, ex, sf = res["swap"], res["schedule"], res["fixing_changes_risk"], res["explain"], res["second_fixing"]

    if r13 is None:
        if not params["quick"]:
            truth("C1 1.3's committed JSON is beside this script for the full run", False)
    else:
        R = r13["results"]
        truth("C1 the curve and the swap are page 1.3's", r13["params"]["curve"]["zero_rates"] == params["curve"]["zero_rates"]
              and r13["params"]["curve"]["times"] == params["curve"]["times"]
              and all(abs(r13["params"]["swap"][k] - params["swap"][k]) <= 1e-12 for k in ("notional", "tau")))
        add("C1 the par rate is 1.3's committed 5.2608% (1e-12)", sw["par_rate"], R["par"]["par_rate"], 1e-12)
        add("C1 the first net payment is 1.3's 20,139 (1e-6)", res["schedule"]["events"][2]["amount"], R["first_exchange"]["net_paid_by_fixed_payer"], 1e-6)
        add("C3 before the first fixing the buckets are 1.3's committed four (1e-6)",
            max(abs(b["before_first_fixing"] - c["by_bump"]) for b, c in zip(fx["buckets"], R["risk"]["buckets"])), 0.0, 1e-6)
    add("C1 the swap is worth nothing when it is agreed (1e-8 on ten million)", sw["value_when_agreed"], 0.0, 1e-8)

    events = sch["events"]
    truth("C2 the events are in date order", all(a["at"] <= b["at"] for a, b in zip(events, events[1:])))
    truth("C2 four resets and four payments", sch["resets"] == 4 and sch["payments"] == 4)
    truth("C2 every reset comes before the payment it sets, by one period",
          all(events[k]["event"].startswith("reset") for k in (1, 3, 5, 7)) and [events[k]["at"] for k in (1, 3, 5, 7)] == [0.0, 0.5, 1.0, 1.5])
    truth("C2 only the first payment is known when the swap is agreed", [e.get("known_when_agreed") for e in events if e["event"].startswith("payment")] == [True, False, False, False])
    add("C2 about five hundred business days in two years", sch["business_days"], 500, 10)

    add("C3 reading the fixing does not change the value (1e-8)", fx["value_after"], fx["value_before"], 1e-8)
    add("C3 before it, the six-month bucket is +12.84", fx["buckets"][0]["before_first_fixing"], 12.84, 5e-3)
    add("C3 after it, the six-month bucket is -487.16", fx["buckets"][0]["after_first_fixing"], -487.16, 5e-3)
    add("C3 the other three buckets do not change (1e-4)", max(abs(b["change"]) for b in fx["buckets"][1:]), 0.0, 1e-4)
    add("C3 the PV01 goes from 1,924", fx["pv01_before"], 1_924.0, 0.5)
    add("C3 to 1,424", fx["pv01_after"], 1_424.0, 0.5)
    add("C3 the change is the PV01 of the notional and the first interest paid at six months: -500", fx["buckets"][0]["change"],
        fx["a_deposit_of_the_notional_and_first_interest_to_six_months"], 1e-3)

    add("C4 the actual P&L for the day is 6,956", ex["actual"], 6_956.0, 0.5)
    add("C4 the passing of the day explains -106", ex["time"], -106.0, 0.5)
    add("C4 the rate moves explain 7,072, from last night's buckets", ex["rates"], 7_072.0, 0.5)
    add("C4 the two-year bucket alone explains 7,399", ex["rates_by_bucket"][-1]["explained"], 7_399.0, 0.5)
    add("C4 and the six-month bucket -487", ex["rates_by_bucket"][0]["explained"], -487.0, 0.5)
    add("C4 actual = time + rates + unexplained (1e-6)", ex["actual"], ex["time"] + ex["rates"] + ex["unexplained"], 1e-6)
    truth("C4 the unexplained is under two parts in a thousand of the actual", abs(ex["unexplained_share_of_actual"]) < 2e-3)
    add("C4 the unexplained is about -10", ex["unexplained"], -10.0, 0.5)
    add("C4 the day's accrual, floating at 4.8581% less fixed at 5.2608%, is -112", ex["accrual_for_the_day"], -112.0, 0.5)

    add("C5 a second fixing of 5.10% makes the floating payment 255,000", sf["floating_payment_fixed"], 255_000.0, 1e-6)
    add("C5 and the net payment at one year 8,042 from the payer of fixed", sf["net_paid_by_fixed_payer_fixed"], 8_042.0, 0.5)
    add("C5 where the forward had it receiving 368", sf["net_paid_by_fixed_payer_projected"], -368.0, 0.5)

    slow = res["linear_risk_changes_slowly"]
    truth("C6 a hundred basis points on every rate changes the swap's PV01 by under 3%", abs(slow["relative_change"]) < 0.03)
    add("C6 by -2.5%", slow["relative_change"], -0.025, 5e-4)
    if r14 is None:
        if not params["quick"]:
            truth("C6 1.4's committed JSON is beside this script for the full run", False)
    else:
        d = {row["S"]: row["call_delta"] for row in r14["results"]["risk"]["delta_by_spot"]}
        res["linear_risk_changes_slowly"]["call_delta_at_100"], res["linear_risk_changes_slowly"]["call_delta_at_120"] = d[100.0], d[120.0]
        add("C6 1.4's call changes its delta by 25% when the share goes from 100 to 120", d[120.0] / d[100.0] - 1, 0.25, 5e-3)

    qc = res["quoted_in_checks"]
    add("the page's checks: risk that ignored the fixing would explain 7,572", qc["rates_explained_if_last_night_s_risk_ignored_the_fixing"], 7_572.0, 0.5)
    add("the page's checks: the PV01 times the average move would explain 3,561", qc["rates_explained_if_the_pv01_times_the_average_move"], 3_561.0, 0.5)
    add("the page's checks: three quarters of 1,924 is 1,443", qc["pv01_if_each_floating_payment_carried_a_quarter_of_it"], 1_443.0, 0.5)

    if oracle is None:
        if not params["quick"]:
            truth("C7 QuantLib is importable for the full run (I4)", False)
    else:
        e = oracle["errors"]
        add("C7 QuantLib's swap with the fixing stored is worth nothing when agreed (1e-6)", e["value_when_agreed"], 0.0, 1e-6)
        add("C7 the same value a day later on the same rates (1e-6)", e["value_next_day_same_rates"], 0.0, 1e-6)
        add("C7 the same value a day later on the moved rates (1e-6)", e["value_next_day_new_rates"], 0.0, 1e-6)
        add("C7 and the same four buckets after the fixing (1e-4)", e["buckets"], 0.0, 1e-4)
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
        "swap": {"notional": 10_000_000.0, "tau": 0.5, "side": "the payer of fixed, at the par rate",
                 "note": "page 1.3's swap; its functions are imported from 1_3_swaps.py"},
        "day": {"elapsed": 1 / 360, "moves_bp": [1.0, 2.0, 3.0, 4.0],
                "note": "one day is 1/360 of a year, as every period is half a year; the moves are made up"},
        "second_fixing_if_different": 0.051,
        "large_shift_bp": 100.0,
        "business_days_a_year": 250,
        "bump": 1e-6,
    }
    res = run(params)
    script_dir = Path(__file__).resolve().parent
    r13 = committed(script_dir, "1_3_swaps.json")
    r14 = committed(script_dir, "1_4_options.json")
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C7: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    res["oracle"] = oracle
    checks = build_checks(res, params, oracle, r13, r14)

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
