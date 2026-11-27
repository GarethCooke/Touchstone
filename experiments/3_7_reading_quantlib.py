"""Reading QuantLib -- the experiment behind page 3.7.

Serves page 3.7 (docs/quant-learn-index-v1.md): how the QuantLib-Python oracle
generates the golden values, and how to read the library those values come
from. The library's tests read QuantLib's answers from two committed files and
never link QuantLib, and the learn site cannot run it either, so the numbers
that page quotes from QuantLib are held here.

The option is Part 2's -- a share at 100 paying no dividend, strike 100, one
year, r = 0.05, sigma = 0.4 -- which is on neither golden grid.

This file builds one QuantLib pricing set-up of its own, and that one is wrong
on purpose (C5). Every right price is asked of the functions the two generators
in golden/ price a row with, `price_one` in each, so that what is measured is
the oracle as the golden files use it.

  C1  The oracle on the page's option. `price_one` returns a price and six
      Greeks for the call and for the put. The call's price is page 2.9's
      18.0230, and all fourteen numbers agree with the closed form written out
      in golden/verify_bs_vanilla.py to 1e-12 of each quantity's scale.
  C2  The engine's three numbers. QuantLib's AnalyticEuropeanEngine never sees
      r, q, sigma or T. It asks its curves for two discount factors and a
      variance to the expiry date, makes a forward price from them, and hands
      a forward, a standard deviation and a discount factor to a
      BlackCalculator: 105.13, 0.4 and 0.9512 here. `black_calculator` below
      restates that calculator's route for a call in plain Python. Given the
      same three numbers it returns the engine's price, and so does QuantLib's
      own BlackCalculator.
  C3  Theta by the equation. QuantLib's BlackCalculator has no formula for
      theta. It solves page 2.7's equation for it from the price, the delta
      and the gamma, and divides by the time to expiry. `black_calculator`
      does the same and gets the engine's theta; so does a difference of two
      prices a little apart in expiry.
  C4  Two dates. An option asks QuantLib's global evaluation date whether it
      has expired; a curve starts at the date it was built with. With the
      global date moved to 1 July 2026 and the generator's grid otherwise
      untouched, the 1,800 rows that expire in 91 days are zero in every
      column and the other 5,400 are what they were, to the last bit.
      On the day the page's one-year call expires, it is zero too.
  C5  The handles exchanged. A process built with the rate curve where the
      dividend curve belongs prices the page's call at 13.15, which is what
      the put is worth: with the share at the strike, exchanging the rate and
      the yield turns one into the other. `spot_the_bug` is the page's check,
      statement for statement. 800 of the golden grid's 7,200 rows have a rate
      equal to their yield and would not change.
  C6  The lattices. The American generator's `price_one` returns
      Leisen-Reimer's price at 2,001 steps and the most that
      Cox-Ross-Rubinstein and Tian differed from it. For the page's put that
      is 13.6676 and 0.0019. For the page's call, which is never exercised
      early and so is worth the closed form's 18.0230, Leisen-Reimer is
      within 2e-7 while the spread is again 0.0018: the spread measures the
      three trees against each other, and the primary one is far closer to
      the answer than to the other two.
  C7  The committed files, counted: rows, the QuantLib version that wrote
      them, the tolerances they carry, and the worst spread.

Run from the repository root:

    uv run experiments/3_7_reading_quantlib.py [--quick]

Nothing here is random, so there is no seed. --quick is for the learn site's
build-time snippet check (I3), where there is no QuantLib and no golden/: it
asserts the claims that are arithmetic (the engine's three numbers, theta by
the equation, and the exchange of rate and yield, all against page 1.4's
closed form) and writes NO JSON -- the committed result is the full run.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from math import exp, log, pi, sqrt
from pathlib import Path

PAGE = "3.7"
HERE = Path(__file__).resolve().parent

# Page 2.9's formula is restated once, in page 1.4's script, and imported from
# there. importlib, because a module whose name starts with a digit cannot be
# named in an import statement.
sys.path.insert(0, str(HERE))
_options = importlib.import_module("1_4_options")
black_scholes, cumulative_normal = _options.black_scholes, _options.cumulative_normal

EXPIRY_DAYS = 365          # one year under the generators' Actual/365 Fixed
GREEKS = ("price", "delta", "gamma", "vega", "theta", "rho", "dividend_rho")


# --- the engine's route, by hand ------------------------------------------------------


def engine_inputs(m: dict) -> dict:
    """What AnalyticEuropeanEngine::calculate hands its BlackCalculator.

    The engine asks the process for a variance and two discount factors to the
    expiry date. With flat curves and a constant volatility those are
    sigma^2 T, exp(-rT) and exp(-qT).
    """
    variance = m["sigma"] ** 2 * m["T"]
    discount = exp(-m["r"] * m["T"])
    dividend_discount = exp(-m["q"] * m["T"])
    return {"forward": m["S"] * dividend_discount / discount, "std_dev": sqrt(variance),
            "discount": discount, "variance": variance}


def black_calculator(forward: float, std_dev: float, discount: float, strike: float,
                     spot: float, maturity: float) -> dict:
    """QuantLib's BlackCalculator for a call, restated: value, delta, gamma and theta.

    d1 and the value are Black-76's, page 2.9's formula written in the forward.
    Theta is not a formula of its own. It is page 2.7's equation,
        theta + (r - q) S delta + (1/2) sigma^2 S^2 gamma - r V = 0,
    solved for theta, with r T read back as -ln(discount), (r - q) T as
    ln(forward / spot) and sigma^2 T as the variance, and the whole divided by T.
    """
    d1 = log(forward / strike) / std_dev + 0.5 * std_dev
    d2 = d1 - std_dev
    value = discount * (forward * cumulative_normal(d1) - strike * cumulative_normal(d2))
    forward_per_spot = forward / spot
    delta = discount * forward_per_spot * cumulative_normal(d1)
    density = exp(-0.5 * d1 * d1) / sqrt(2.0 * pi)
    gamma = discount * forward_per_spot * density / (spot * std_dev)
    theta = -(log(discount) * value + log(forward_per_spot) * spot * delta
              + 0.5 * std_dev ** 2 * spot * spot * gamma) / maturity
    return {"d1": d1, "d2": d2, "value": value, "delta": delta, "gamma": gamma, "theta": theta}


def by_hand(m: dict) -> dict:
    """C2, C3 and C5 as arithmetic: no QuantLib."""
    inputs = engine_inputs(m)
    calc = black_calculator(inputs["forward"], inputs["std_dev"], inputs["discount"], m["K"], m["S"], m["T"])
    closed = black_scholes(m["S"], m["K"], m["r"], m["sigma"], m["T"])
    h = 1e-4
    longer = black_scholes(m["S"], m["K"], m["r"], m["sigma"], m["T"] + h)["call"]
    shorter = black_scholes(m["S"], m["K"], m["r"], m["sigma"], m["T"] - h)["call"]

    exchanged = {**m, "r": m["q"], "q": m["r"]}
    swapped_inputs = engine_inputs(exchanged)
    swapped = black_calculator(swapped_inputs["forward"], swapped_inputs["std_dev"], swapped_inputs["discount"],
                               m["K"], m["S"], m["T"])
    return {
        "engine_inputs": inputs,
        "black_calculator": calc,
        "closed_form": {"call": closed["call"], "put": closed["put"], "call_delta": closed["call_delta"]},
        "theta_by_two_prices": -(longer - shorter) / (2.0 * h),
        "expiry_step_for_theta": h,
        "rate_and_yield_exchanged": {"engine_inputs": swapped_inputs, "call": swapped["value"],
                                     "call_delta": swapped["delta"]},
    }


# --- QuantLib, through the generators ---------------------------------------------------


def load_golden(name: str):
    """One of the scripts in golden/, as a module."""
    path = HERE.parent / "golden" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def spot_the_bug(ql, european) -> float:
    """The page's check, statement for statement: the fourth statement is wrong.

    BlackScholesMertonProcess takes the dividend curve before the rate curve.
    """
    today = european.EVALUATION_DATE
    dc, cal = european.DAY_COUNT, european.CALENDAR
    spot = ql.QuoteHandle(ql.SimpleQuote(100.0))
    expiry = today + ql.Period(EXPIRY_DAYS, ql.Days)

    rate_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(today, 0.05, dc))
    div_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(today, 0.0, dc))
    vol_ts = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            today, cal, 0.4, dc))
    process = ql.BlackScholesMertonProcess(
        spot, rate_ts, div_ts, vol_ts)
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(
            ql.Option.Call, 100.0),
        ql.EuropeanExercise(expiry))
    option.setPricingEngine(
        ql.AnalyticEuropeanEngine(process))
    return option.NPV()


def from_quantlib(m: dict, hand: dict) -> dict:
    """C1 to C7 on QuantLib itself."""
    import QuantLib as ql

    european = load_golden("generate_bs_vanilla")
    american = load_golden("generate_american_vanilla")
    verifier = load_golden("verify_bs_vanilla")
    settings = ql.Settings.instance()
    row = (m["S"], m["K"], m["sigma"], m["r"], m["q"], EXPIRY_DAYS)

    def european_row(kind, *, date=european.EVALUATION_DATE, inputs=row):
        # `price_one` reads the global date and does not set it; `build_document` does.
        settings.evaluationDate = date
        return european.price_one(kind, *inputs)

    call, put = european_row(ql.Option.Call), european_row(ql.Option.Put)
    case = {"spot": m["S"], "strike": m["K"], "expiry_years": m["T"]}
    reference = {kind: verifier.black_scholes_merton(kind == "call", m["S"], m["K"], m["sigma"], m["r"], m["q"], m["T"])
                 for kind in ("call", "put")}
    deviations = {kind: {field: verifier.deviation(priced[field], reference[kind][field], field, case)
                         for field in GREEKS}
                  for kind, priced in (("call", call), ("put", put))}

    # C2: QuantLib's own calculator on the three numbers.
    inputs = hand["engine_inputs"]
    calculator = ql.BlackCalculator(ql.PlainVanillaPayoff(ql.Option.Call, m["K"]),
                                    inputs["forward"], inputs["std_dev"], inputs["discount"])

    # C4: the page's call on three evaluation dates, and the whole grid on a fourth.
    expiry = european.EVALUATION_DATE + ql.Period(EXPIRY_DAYS, ql.Days)
    dated = {}
    for label, date in (("the_day_before_expiry", expiry - 1), ("the_expiry_date", expiry)):
        priced = european_row(ql.Option.Call, date=date)
        dated[label] = {"evaluation_date": date.ISO(), **priced,
                        "same_bits_as_on_the_generator_date": all(priced[f] == call[f] for f in GREEKS),
                        "every_number_zero": all(priced[f] == 0.0 for f in GREEKS)}
    settings.evaluationDate = european.EVALUATION_DATE
    as_generated = european.build_main_grid()
    moved = ql.Date(1, ql.July, 2026)
    settings.evaluationDate = moved
    regenerated = european.build_main_grid()
    settings.evaluationDate = european.EVALUATION_DATE
    committed = json.loads((HERE.parent / "golden" / "bs_vanilla.json").read_text(encoding="utf-8"))
    zero = unchanged = other = 0
    zero_days, unchanged_days = set(), set()
    for now, then in zip(regenerated, as_generated):
        if all(now[f] == 0.0 for f in GREEKS):
            zero += 1
            zero_days.add(now["expiry_days"])
        elif now == then:
            unchanged += 1
            unchanged_days.add(now["expiry_days"])
        else:
            other += 1
    grid_moved = {"evaluation_date": moved.ISO(), "rows": len(regenerated), "rows_zero_in_every_column": zero,
                  "rows_identical_to_the_generator_date": unchanged, "rows_neither": other,
                  "expiry_days_of_the_zero_rows": sorted(zero_days),
                  "expiry_days_of_the_identical_rows": sorted(unchanged_days),
                  # The committed file was written on Linux. On another platform the last bit of a
                  # row may differ, so this is recorded and held only to the file's own tolerance.
                  "rows_on_the_generator_date_identical_to_the_committed_file":
                      sum(1 for now, then in zip(as_generated, committed["cases"]) if now == then),
                  "largest_difference_from_the_committed_file":
                      max(abs(now[f] - then[f]) / max(abs(then[f]), 1.0)
                          for now, then in zip(as_generated, committed["cases"]) for f in GREEKS)}

    # C5: the check's own statements, and the same thing asked of the generator.
    settings.evaluationDate = european.EVALUATION_DATE
    bug = spot_the_bug(ql, european)
    exchanged = european_row(ql.Option.Call, inputs=(m["S"], m["K"], m["sigma"], m["q"], m["r"], EXPIRY_DAYS))
    percent_vol = european_row(ql.Option.Call, inputs=(m["S"], m["K"], 100.0 * m["sigma"], m["r"], m["q"], EXPIRY_DAYS))

    # C6: the three lattices.
    settings.evaluationDate = american.EVALUATION_DATE
    american_put = american.price_one(ql.Option.Put, *row)
    american_call = american.price_one(ql.Option.Call, *row)

    # C7: the committed files.
    american_file = json.loads((HERE.parent / "golden" / "american_vanilla.json").read_text(encoding="utf-8"))
    cases = committed["cases"]
    files = {
        "bs_vanilla": {
            "quantlib_version": committed["oracle"]["version"], "engine": committed["oracle"]["engine"],
            "evaluation_date": committed["oracle"]["evaluation_date"],
            "rows": committed["counts"]["cases"], "edge_rows": committed["counts"]["edge_cases"],
            "all_rows": committed["counts"]["total"], "matched_pairs": committed["counts"]["total"] // 2,
            "tolerance": committed["tolerances"]["cases"], "edge_tolerance": committed["tolerances"]["edge_cases"],
            "rows_with_rate_equal_to_yield": sum(1 for c in cases if c["rate"] == c["dividend_yield"]),
            "rows_expiring_in_91_days": sum(1 for c in cases if c["expiry_days"] == 91),
            "verifier_threshold": verifier.TOLERANCE,
        },
        "american_vanilla": {
            "quantlib_version": american_file["oracle"]["version"], "engine": american_file["oracle"]["engine"],
            "rows": american_file["counts"]["cases"], "steps": american.PRIMARY_STEPS,
            "lattices": [name for name, _tree, _steps in american.TREES],
            "worst_spread": american_file["tolerances"]["worst_spread"],
            "rows_with_no_spread": sum(1 for c in american_file["cases"] if c["spread"] == 0.0),
        },
    }

    return {
        "quantlib": ql.__version__,
        "results": {
            "oracle": {"call": call, "put": put, "closed_form": reference, "deviation_in_natural_scale": deviations},
            "quantlib_black_calculator": {"value": calculator.value(), "delta": calculator.delta(m["S"]),
                                          "gamma": calculator.gamma(m["S"]), "theta": calculator.theta(m["S"], m["T"])},
            "evaluation_date": {"generator_date": european.EVALUATION_DATE.ISO(), "expiry_date": expiry.ISO(),
                                "call": dated, "grid": grid_moved},
            "handles_exchanged": {"spot_the_bug_returns": bug, "generator_with_rate_and_yield_exchanged": exchanged,
                                  "same_bits": bug == exchanged["price"]},
            "volatility_as_a_percentage": percent_vol,
            "american": {"put": american_put, "call": american_call,
                         "call_less_the_closed_form": american_call["price"] - call["price"],
                         "premium_of_the_put": american_put["price"] - put["price"]},
            "golden_files": files,
        },
    }


# --- run ---------------------------------------------------------------------------------


def run(params: dict) -> tuple[dict, dict]:
    m = params["market"]
    res = {"by_hand": by_hand(m)}
    environment = {}
    if not params["quick"]:
        live = from_quantlib(m, res["by_hand"])
        environment["quantlib"] = live["quantlib"]
        res.update(live["results"])
        am, eu = res["american"], res["oracle"]
        res["quoted_in_checks"] = {
            "call": eu["call"]["price"],
            "put": eu["put"]["price"],
            "spot_the_bug_returns": res["handles_exchanged"]["spot_the_bug_returns"],
            "call_at_a_volatility_of_40": res["volatility_as_a_percentage"]["price"],
            "rows_that_go_to_zero": res["evaluation_date"]["grid"]["rows_zero_in_every_column"],
            "rows_that_do_not_change": res["evaluation_date"]["grid"]["rows_identical_to_the_generator_date"],
            "american_put": am["put"]["price"],
            "american_put_spread": am["put"]["spread"],
            "worst_spread_in_the_file": res["golden_files"]["american_vanilla"]["worst_spread"],
            "golden_tolerance": res["golden_files"]["bs_vanilla"]["tolerance"],
        }
    return res, environment


# --- checks --------------------------------------------------------------------------------


def build_checks(res: dict, params: dict) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        error = abs(measured - expected) / (abs(expected) if mode == "rel" else 1.0)
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(error <= tol)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0,
                       "mode": "abs", "pass": bool(ok)})

    hand = res["by_hand"]
    inputs, calc, closed = hand["engine_inputs"], hand["black_calculator"], hand["closed_form"]
    add("the closed form is page 2.9's 18.0230", closed["call"], 18.0230, 5e-5)
    add("C2 the forward is 105.13", inputs["forward"], 105.13, 5e-3)
    add("C2 the standard deviation is 0.4", inputs["std_dev"], 0.4, 1e-12)
    add("C2 the discount factor is 0.9512", inputs["discount"], 0.9512, 5e-5)
    add("C2 from those three numbers the calculator's route gives the closed form's price",
        calc["value"], closed["call"], 1e-12)
    add("C2 and its delta", calc["delta"], closed["call_delta"], 1e-12)
    add("C3 theta by the equation is the theta two prices a little apart in expiry give",
        calc["theta"], hand["theta_by_two_prices"], 1e-6)
    add("C3 and it is -9.80 a year", calc["theta"], -9.80, 5e-3)
    add("C5 with the rate and the yield exchanged the call is worth what the put is",
        hand["rate_and_yield_exchanged"]["call"], closed["put"], 1e-12)
    add("C5 which is 13.15", hand["rate_and_yield_exchanged"]["call"], 13.15, 5e-3)

    if "oracle" not in res:
        return checks

    oracle, files = res["oracle"], res["golden_files"]
    add("C1 QuantLib's call is the closed form's 18.0230", oracle["call"]["price"], closed["call"], 1e-12)
    add("C1 and its put is the closed form's", oracle["put"]["price"], closed["put"], 1e-12)
    worst = max(max(by_field.values()) for by_field in oracle["deviation_in_natural_scale"].values())
    truth("C1 all fourteen numbers are within 1e-12 of the verifier's closed form, in each quantity's scale",
          worst <= 1e-12)

    ql_calc = res["quantlib_black_calculator"]
    add("C2 QuantLib's own BlackCalculator on the three numbers gives the engine's price",
        ql_calc["value"], oracle["call"]["price"], 1e-12)
    add("C2 this file's restatement of it gives the same price", calc["value"], ql_calc["value"], 1e-12)
    add("C2 and the same gamma", calc["gamma"], ql_calc["gamma"], 1e-12)
    add("C3 QuantLib's calculator's theta is the engine's", ql_calc["theta"], oracle["call"]["theta"], 1e-12)
    add("C3 and this file's theta by the equation is the engine's", calc["theta"], oracle["call"]["theta"], 1e-12)
    add("C3 the engine's theta is the verifier's, which uses the textbook formula",
        oracle["call"]["theta"], oracle["closed_form"]["call"]["theta"], 1e-12)

    dates, grid = res["evaluation_date"]["call"], res["evaluation_date"]["grid"]
    truth("C4 the day before expiry the page's call is priced as on the generator's date, to the last bit",
          dates["the_day_before_expiry"]["same_bits_as_on_the_generator_date"])
    truth("C4 on the expiry date all seven numbers are zero", dates["the_expiry_date"]["every_number_zero"])
    add("C4 with the global date at 1 July 2026, 1,800 rows of the grid are zero in every column",
        grid["rows_zero_in_every_column"], 1800, 0)
    add("C4 the other 5,400 are what the generator's own date gives, to the last bit",
        grid["rows_identical_to_the_generator_date"], 5400, 0)
    truth("C4 and on its own date the generator's grid is the committed file's, within the file's tolerance",
          grid["largest_difference_from_the_committed_file"] <= files["bs_vanilla"]["tolerance"])
    truth("C4 no row is anything else, the zero rows are the 91-day ones and no 91-day row survives",
          grid["rows_neither"] == 0 and grid["expiry_days_of_the_zero_rows"] == [91]
          and 91 not in grid["expiry_days_of_the_identical_rows"])
    add("C4 and 1,800 is the number of 91-day rows in the committed file",
        files["bs_vanilla"]["rows_expiring_in_91_days"], grid["rows_zero_in_every_column"], 0)

    swap = res["handles_exchanged"]
    truth("C5 the check's statements return what the generator returns with the rate and the yield exchanged, "
          "to the last bit", swap["same_bits"])
    add("C5 which is the put's price", swap["spot_the_bug_returns"], oracle["put"]["price"], 1e-12)
    add("C5 800 rows of the grid have a rate equal to their yield", files["bs_vanilla"]["rows_with_rate_equal_to_yield"], 800, 0)
    add("a volatility written as 40 prices the call at the share price, 100.00",
        res["volatility_as_a_percentage"]["price"], 100.0, 5e-3)

    am = res["american"]
    add("C6 Leisen-Reimer prices the page's put at 13.6676", am["put"]["price"], 13.6676, 5e-5)
    add("C6 and the other two lattices are within 0.0019 of it", am["put"]["spread"], 0.0019, 5e-5)
    add("C6 early exercise is worth 0.52 on the put", am["premium_of_the_put"], 0.52, 5e-3)
    truth("C6 the call, never exercised early, is within 2e-7 of the closed form on Leisen-Reimer",
          abs(am["call_less_the_closed_form"]) < 2e-7)
    add("C6 while the other two lattices are 0.0018 from Leisen-Reimer", am["call"]["spread"], 0.0018, 5e-5)
    truth("C6 so the spread is more than a thousand times the primary lattice's own error there",
          am["call"]["spread"] > 1000.0 * abs(am["call_less_the_closed_form"]))

    eu, us = files["bs_vanilla"], files["american_vanilla"]
    truth("C7 both files were written by QuantLib 1.43, which is the QuantLib running now",
          eu["quantlib_version"] == us["quantlib_version"] == "1.43" == params["quantlib"])
    add("C7 the European file has 7,200 rows", eu["rows"], 7200, 0)
    add("C7 and 34 edge rows", eu["edge_rows"], 34, 0)
    add("C7 which is 3,617 pairs of a call and a put", eu["matched_pairs"], 3617, 0)
    add("C7 held to 1e-10", eu["tolerance"], 1e-10, 0)
    add("C7 and 1e-8", eu["edge_tolerance"], 1e-8, 0)
    add("C7 the verifier's threshold is 1e-13", eu["verifier_threshold"], 1e-13, 0)
    add("C7 the American file has 864 rows", us["rows"], 864, 0)
    add("C7 three lattices", len(us["lattices"]), 3, 0)
    add("C7 at 2,001 steps", us["steps"], 2001, 0)
    add("C7 the worst spread is 0.020", us["worst_spread"], 0.020, 5e-4)
    add("C7 on 72 rows the three lattices agree exactly", us["rows_with_no_spread"], 72, 0)
    q = res["quoted_in_checks"]
    add("the figures the checks quote are the results above", q["spot_the_bug_returns"], swap["spot_the_bug_returns"], 0)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true",
                        help="snippet check: the arithmetic only, without QuantLib or golden/, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "market": {"S": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.4, "T": 1.0, "q": 0.0,
                   "note": "Part 2's option (page 2.9): a share at 100 paying no dividend, strike 100, one year"},
        "expiry_days": EXPIRY_DAYS,
    }
    res, environment = run(params)
    checks = build_checks(res, {**params, **environment})

    out = {"page": PAGE, "script": Path(__file__).name, "params": params,
           "environment": environment, "results": res, "checks": checks}
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
    raise SystemExit(main())
