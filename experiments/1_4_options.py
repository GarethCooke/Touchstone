"""Options -- the arithmetic behind page 1.4.

Serves page 1.4 (docs/quant-learn-index-v1.md): calls, puts, payoffs,
moneyness, intrinsic and time value; why they exist; European and American;
the price as the cost of hedging; and the page's check -- the payoff-diagram
builder, combining legs into a straddle and a collar.

Part 1 is arithmetic. Nothing here is random, so there is no seed. Symbols are
the notation ledger's: S the share price, K the strike, T the expiry in years,
r the continuously compounded rate, sigma the volatility, C and P the prices
of the call and the put, N(.) the cumulative normal. S_T is the share price at
expiry.

Session decisions (owner, 2026-11-16): the option is Part 2's -- a share at
100, strike 100, one year, r = 0.05, sigma = 0.4, no dividend -- so the
premiums on the page are the numbers page 2.9 derives. A leg's premium is a
stated number: the page shows payoffs at expiry and prices nothing itself.
Every value before expiry in this file comes from page 2.9's formula, which
this file restates and holds against QuantLib and against 2.9's committed
result.

  C1  Payoffs at expiry. A call pays max(S_T - K, 0) and a put max(K - S_T, 0).
      Profit is the payoff less the premium for the holder, and the reverse
      for the writer. The premium is not compounded: a payoff diagram ignores
      the interest on it.
  C2  A call less a put at the same strike is a forward: S_T - K at every
      S_T. So C - P = S - K e^(-rT) today, which is put-call parity, and it
      is page 1.1's forward value. No model is needed for the difference.
  C3  Moneyness, intrinsic value and time value, with a year to run.
  C4  Bounds, and early exercise. A European call on a share that pays no
      dividend is worth more than S - K at every spot, so an American call
      is never exercised early. A European put deep in the money is worth
      less than K - S, so an American put can be.
  C5  Leverage and the protective put: the two reasons the page gives numbers
      for.
  C6  One fixed holding cannot hedge it. Sell the call, hold delta shares
      bought with borrowed money, and never trade again: the result at expiry
      depends on where the share finishes.
  C7  The hedge has to change: delta at three spots. And the price depends on
      volatility, which no linear product's does.
  C8  The straddle: a call and a put at the same strike.
  C9  The collar: a share held, a put bought below it, a call sold above it.
  C10 What page 2.7 measured, read from its committed result: the spread of
      the hedged result falls as the hedge is rebalanced more often, around
      a mean of nothing.
  C11 The oracle (I4). QuantLib's analytic European engine gives the same
      prices and deltas; its American engines give the American put.

Run from the repository root:

    uv run experiments/1_4_options.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_4_options.json beside this file: parameters in, results out, no
timestamps. No plotting here; the site draws. Exits non-zero if any check
fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import erf, exp, log, sqrt
from pathlib import Path

PAGE = "1.4"


# --- payoffs at expiry ---------------------------------------------------------


def call_payoff(S_T: float, K: float) -> float:
    """What a call pays its holder at expiry."""
    return max(S_T - K, 0.0)


def put_payoff(S_T: float, K: float) -> float:
    """What a put pays its holder at expiry."""
    return max(K - S_T, 0.0)


PAYOFFS = {"call": call_payoff, "put": put_payoff, "share": lambda S_T, K: S_T}


def strategy_payoff(legs: list[dict], S_T: float) -> float:
    """The payoff at expiry of several legs held together.

    A leg is {"kind": "call" | "put" | "share", "strike": K, "quantity": n,
    "premium": p}. The quantity is positive for a leg bought and negative for
    one sold. A share has no strike.
    """
    return sum(leg["quantity"] * PAYOFFS[leg["kind"]](S_T, leg.get("strike", 0.0)) for leg in legs)


def strategy_cost(legs: list[dict]) -> float:
    """What the legs cost to put on: premiums paid less premiums received."""
    return sum(leg["quantity"] * leg["premium"] for leg in legs)


def strategy_profit(legs: list[dict], S_T: float) -> float:
    """Payoff at expiry less what the legs cost. The cost is not compounded."""
    return strategy_payoff(legs, S_T) - strategy_cost(legs)


# --- page 2.9's formula, restated ----------------------------------------------


def cumulative_normal(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def black_scholes(S: float, K: float, r: float, sigma: float, T: float) -> dict:
    """Price and delta of a European call and put on a share paying no dividend."""
    d1 = (log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    call = S * cumulative_normal(d1) - K * exp(-r * T) * cumulative_normal(d2)
    put = K * exp(-r * T) * cumulative_normal(-d2) - S * cumulative_normal(-d1)
    return {"call": call, "put": put, "call_delta": cumulative_normal(d1), "put_delta": cumulative_normal(d1) - 1.0}


def moneyness(kind: str, S: float, K: float) -> str:
    if S == K:
        return "at the money"
    in_the_money = S > K if kind == "call" else S < K
    return "in the money" if in_the_money else "out of the money"


# --- the oracle ----------------------------------------------------------------


def quantlib_oracle(params: dict, res: dict) -> dict | None:
    """QuantLib's European prices and deltas on the page's grid, and the American put."""
    try:
        import QuantLib as ql
    except ImportError:
        return None
    M = params["market"]
    today = ql.Date(1, 1, 2026)
    ql.Settings.instance().evaluationDate = today
    dc = ql.Actual365Fixed()
    expiry = today + round(365 * M["T"])
    spot = ql.SimpleQuote(M["S"])
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(spot),
        ql.YieldTermStructureHandle(ql.FlatForward(today, 0.0, dc)),
        ql.YieldTermStructureHandle(ql.FlatForward(today, M["r"], dc)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), M["sigma"], dc)))

    def european(kind: str, K: float):
        option = ql.VanillaOption(ql.PlainVanillaPayoff(ql.Option.Call if kind == "call" else ql.Option.Put, K), ql.EuropeanExercise(expiry))
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        return option

    def american_put(K: float, engine) -> float:
        option = ql.VanillaOption(ql.PlainVanillaPayoff(ql.Option.Put, K), ql.AmericanExercise(today, expiry))
        option.setPricingEngine(engine)
        return option.NPV()

    price_error = delta_error = 0.0
    american = []
    for row in res["before_expiry"]["rows"]:
        spot.setValue(row["S"])
        for kind in ("call", "put"):
            option = european(kind, M["K"])
            price_error = max(price_error, abs(option.NPV() - row[kind]))
            delta_error = max(delta_error, abs(option.delta() - row[f"{kind}_delta"]))
        by_tree = american_put(M["K"], ql.BinomialVanillaEngine(process, "crr", 4000))
        by_grid = american_put(M["K"], ql.FdBlackScholesVanillaEngine(process, 400, 800))
        american.append({"S": row["S"], "american_put_by_tree": by_tree, "american_put_by_finite_differences": by_grid,
                         "european_put": row["put"], "intrinsic": row["put_intrinsic"]})
    spot.setValue(M["S"])
    strike_error = 0.0
    for leg in res["premiums"]["rows"]:
        strike_error = max(strike_error, abs(european(leg["kind"], leg["strike"]).NPV() - leg["price"]))
    return {"version": ql.__version__, "american_put": american,
            "errors": {"price": price_error, "delta": delta_error, "premiums": strike_error}}


def committed(script_dir: Path, name: str) -> dict | None:
    """Another page's committed result, if it is beside this script."""
    path = script_dir / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- the experiment ------------------------------------------------------------


def run(params: dict) -> dict:
    M = params["market"]
    S, K, r, sigma, T = M["S"], M["K"], M["r"], M["sigma"], M["T"]
    base = black_scholes(S, K, r, sigma, T)

    # The premiums the page states: page 2.9's prices, to the penny.
    wanted = [("call", K), ("put", K), ("put", params["collar"]["put_strike"]), ("call", params["collar"]["call_strike"])]
    premium_rows = []
    for kind, strike in wanted:
        price = black_scholes(S, strike, r, sigma, T)[kind]
        premium_rows.append({"kind": kind, "strike": strike, "price": price, "stated_premium": round(price, 2)})
    premium = {(p["kind"], p["strike"]): p["stated_premium"] for p in premium_rows}
    call_premium, put_premium = premium[("call", K)], premium[("put", K)]

    # C1 payoffs at expiry, and profit for the holder and the writer
    expiry_rows = []
    for S_T in params["expiry_grid"]:
        c, p = call_payoff(S_T, K), put_payoff(S_T, K)
        expiry_rows.append({"S_T": S_T, "call_payoff": c, "put_payoff": p,
                            "call_holder_profit": c - call_premium, "call_writer_profit": call_premium - c,
                            "put_holder_profit": p - put_premium, "put_writer_profit": put_premium - p,
                            "call_less_put": c - p, "forward_payoff": S_T - K})
    at_expiry = {"rows": expiry_rows, "call_break_even": K + call_premium, "put_break_even": K - put_premium,
                 "call_holder_worst": -call_premium, "put_holder_worst": -put_premium,
                 "put_writer_worst_at_S_T_zero": put_premium - K}

    # C2 a call less a put is a forward
    discounted_strike = K * exp(-r * T)
    parity = {"call_less_put_today": base["call"] - base["put"], "S_less_discounted_strike": S - discounted_strike,
              "discounted_strike": discounted_strike, "forward_price": S * exp(r * T),
              "max_abs_payoff_difference": max(abs(row["call_less_put"] - row["forward_payoff"]) for row in expiry_rows)}

    # C3 moneyness, intrinsic value and time value with a year to run; C4 the bounds
    rows = []
    for spot in params["spot_grid"]:
        v = black_scholes(spot, K, r, sigma, T)
        ci, pi = call_payoff(spot, K), put_payoff(spot, K)
        rows.append({"S": spot, "call": v["call"], "put": v["put"], "call_delta": v["call_delta"], "put_delta": v["put_delta"],
                     "call_moneyness": moneyness("call", spot, K), "put_moneyness": moneyness("put", spot, K),
                     "call_intrinsic": ci, "put_intrinsic": pi, "call_time_value": v["call"] - ci, "put_time_value": v["put"] - pi,
                     "call_floor": max(spot - discounted_strike, 0.0), "put_floor": max(discounted_strike - spot, 0.0),
                     "call_alive_less_exercised": v["call"] - (spot - K), "put_alive_less_exercised": v["put"] - (K - spot)})
    before = {"rows": rows}

    # C5 leverage and the protective put
    up, flat, down = params["leverage_outcomes"]
    leverage = [{"S_T": S_T, "share_profit": S_T - S, "share_return": (S_T - S) / S,
                 "call_profit": call_payoff(S_T, K) - call_premium, "call_return": (call_payoff(S_T, K) - call_premium) / call_premium}
                for S_T in (up, flat, down)]
    protected = [{"kind": "share", "quantity": 1, "premium": S}, {"kind": "put", "strike": K, "quantity": 1, "premium": put_premium}]
    protective_put = {"cost": strategy_cost(protected), "rows": [{"S_T": S_T, "value": strategy_payoff(protected, S_T), "profit": strategy_profit(protected, S_T)}
                                                               for S_T in params["expiry_grid"]],
                      "worst_profit": min(strategy_profit(protected, S_T) for S_T in params["wide_grid"])}

    # C6 one fixed holding: sell the call, hold delta shares on borrowed money, never trade again
    delta = base["call_delta"]
    growth = exp(r * T)
    static_rows = [{"S_T": S_T, "premium_with_interest": base["call"] * growth, "paid_on_the_call": call_payoff(S_T, K),
                    "shares_less_loan": delta * (S_T - S * growth),
                    "result": base["call"] * growth - call_payoff(S_T, K) + delta * (S_T - S * growth)}
                   for S_T in params["static_grid"]]
    static = {"shares_held": delta, "rows": static_rows, "best": max(row["result"] for row in static_rows),
              "worst": min(row["result"] for row in static_rows)}

    # C7 the hedge has to change, and the price depends on volatility
    vol_rows = [{"sigma": s, "call": black_scholes(S, K, r, s, T)["call"], "put": black_scholes(S, K, r, s, T)["put"],
                 "call_less_put": black_scholes(S, K, r, s, T)["call"] - black_scholes(S, K, r, s, T)["put"]} for s in params["vol_grid"]]
    risk = {"delta_by_spot": [{"S": row["S"], "call_delta": row["call_delta"], "put_delta": row["put_delta"], "forward_delta": 1.0} for row in rows],
            "by_volatility": vol_rows}

    # C8 the straddle
    straddle_legs = [{"kind": "call", "strike": K, "quantity": 1, "premium": call_premium},
                     {"kind": "put", "strike": K, "quantity": 1, "premium": put_premium}]
    straddle_cost = strategy_cost(straddle_legs)
    straddle = {"legs": straddle_legs, "cost": straddle_cost, "break_even_low": K - straddle_cost, "break_even_high": K + straddle_cost,
                "worst_profit": min(strategy_profit(straddle_legs, S_T) for S_T in params["wide_grid"]), "worst_at": K,
                "rows": [{"S_T": S_T, "payoff": strategy_payoff(straddle_legs, S_T), "profit": strategy_profit(straddle_legs, S_T)} for S_T in params["expiry_grid"]]}

    # C9 the collar: the share, a put bought below, a call sold above
    Kp, Kc = params["collar"]["put_strike"], params["collar"]["call_strike"]
    collar_options = [{"kind": "put", "strike": Kp, "quantity": 1, "premium": premium[("put", Kp)]},
                      {"kind": "call", "strike": Kc, "quantity": -1, "premium": premium[("call", Kc)]}]
    collar_legs = [{"kind": "share", "quantity": 1, "premium": S}] + collar_options
    lo, hi = K, 2 * K
    for _ in range(200):  # the call strike whose premium pays for the put exactly
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if black_scholes(S, mid, r, sigma, T)["call"] > black_scholes(S, Kp, r, sigma, T)["put"] else (lo, mid)
    collar = {"legs": collar_legs, "options_cost": strategy_cost(collar_options), "floor": Kp, "cap": Kc,
              "worst_profit": min(strategy_profit(collar_legs, S_T) for S_T in params["wide_grid"]),
              "best_profit": max(strategy_profit(collar_legs, S_T) for S_T in params["wide_grid"]),
              "zero_cost_call_strike": 0.5 * (lo + hi),
              "rows": [{"S_T": S_T, "share_alone": S_T, "value": strategy_payoff(collar_legs, S_T),
                        "profit": strategy_profit(collar_legs, S_T), "share_alone_profit": S_T - S} for S_T in params["expiry_grid"]]}

    # Fixtures for the payoff-diagram builder (D11): each strategy's profit on a fine grid.
    lo_S, hi_S, n = params["d11"]["S_T"]
    grid = [lo_S + (hi_S - lo_S) * i / (n - 1) for i in range(n)]
    d11 = {"S_T": grid,
           "strategies": {name: {"legs": legs, "cost": strategy_cost(legs), "payoff": [strategy_payoff(legs, x) for x in grid],
                                 "profit": [strategy_profit(legs, x) for x in grid]}
                          for name, legs in (("long_call", straddle_legs[:1]), ("long_put", straddle_legs[1:]),
                                             ("straddle", straddle_legs), ("collar", collar_legs))}}

    # Figures the page's check questions quote, right answers and wrong ones alike (I5):
    # a wrong option's number is what its misconception computes, so it is computed here.
    q_S_T = params["check_S_T"]
    quoted = {
        "call_holder_profit_at_check_S_T": call_payoff(q_S_T, K) - call_premium,
        "call_payoff_at_check_S_T_premium_forgotten": call_payoff(q_S_T, K),
        "call_holder_if_the_loss_ran_on_like_a_forward": (q_S_T - K) - call_premium,
        "call_holder_profit_at_120": call_payoff(120.0, K) - call_premium,
        "straddle_break_even_if_only_the_call_s_premium_counted": K + call_premium,
        "straddle_profit_at_100": strategy_profit(straddle_legs, K),
        "straddle_profit_at_140": strategy_profit(straddle_legs, 140.0),
        "collar_value_at_60": strategy_payoff(collar_legs, 60.0), "collar_value_at_160": strategy_payoff(collar_legs, 160.0),
        "collar_if_the_sold_call_were_forgotten_at_160": strategy_payoff(collar_legs[:2], 160.0),
        "time_value_of_the_call_at_120": rows[3]["call_time_value"], "intrinsic_of_the_call_at_120": rows[3]["call_intrinsic"],
        "call_at_120": rows[3]["call"],
        "call_less_put_at_sigma_0_2": vol_rows[0]["call_less_put"], "call_less_put_at_sigma_0_5": vol_rows[-1]["call_less_put"],
        "call_at_sigma_0_2": vol_rows[0]["call"], "call_at_sigma_0_5": vol_rows[-1]["call"],
        "call_at_sigma_0_5_less_put_at_sigma_0_4": vol_rows[-1]["call"] - base["put"],
        "rise_in_the_call_from_sigma_0_4_to_0_5": vol_rows[-1]["call"] - base["call"],
        "static_hedge_result_at_100": base["call"] * growth - call_payoff(K, K) + delta * (K - S * growth),
        "collar_profit_at_160": strategy_profit(collar_legs, 160.0),
        "share_at_160_less_the_collar_s_cost": 160.0 - strategy_cost(collar_options),
        "share_at_160_plus_what_the_sold_call_is_in_the_money": 160.0 + call_payoff(160.0, Kc),
        "forward_bought_at_100_with_the_share_at_check_S_T": q_S_T - K,
        "interest_on_the_strike_for_the_year": K - discounted_strike,
        "put_at_120": rows[3]["put"],
        "call_less_put_if_it_grew_in_proportion_to_the_call": (base["call"] - base["put"]) * vol_rows[-1]["call"] / base["call"],
    }
    return {"base": base, "premiums": {"rows": premium_rows}, "at_expiry": at_expiry, "parity": parity, "before_expiry": before,
            "leverage": leverage, "protective_put": protective_put, "static_hedge": static, "risk": risk,
            "straddle": straddle, "collar": collar, "d11": d11, "quoted_in_checks": quoted}


def page_2_7(result: dict | None) -> dict | None:
    """The three spreads page 1.4 cites from page 2.7's committed result."""
    if result is None:
        return None
    per_N = result["results"]["scenarios"]["base"]["per_N"]
    first, last = per_N[0], per_N[-1]
    return {"V0": result["results"]["scenarios"]["base"]["V0"], "unhedged_sd": first["call"]["unhedged_pnl_T"]["sd"],
            "static_N": first["N"], "static_sd": first["call"]["hedged_pnl_T"]["sd"],
            "most_N": last["N"], "most_sd": last["call"]["hedged_pnl_T"]["sd"], "most_mean": last["call"]["hedged_pnl_T"]["mean"],
            "most_se_of_mean": last["call"]["hedged_pnl_T"]["se_of_mean"]}


def build_checks(res: dict, params: dict, oracle: dict | None, r29: dict | None, r27: dict | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    M = params["market"]
    K = M["K"]
    base, ex, par, rows = res["base"], res["at_expiry"], res["parity"], res["before_expiry"]["rows"]
    by_S = {row["S"]: row for row in rows}
    stated = {(p["kind"], p["strike"]): p["stated_premium"] for p in res["premiums"]["rows"]}

    if r29 is None:
        if not params["quick"]:
            truth("2.9's committed JSON is beside this script for the full run", False)
    else:
        P = r29["params"]
        truth("the option is page 2.9's: the same S, K, r, sigma and T, and no dividend",
              all(abs(P[k] - M[m]) <= 1e-12 for k, m in (("S0", "S"), ("K", "K"), ("r", "r"), ("sigma", "sigma"), ("T", "T"))) and abs(P["q"]) <= 1e-12)
        add("the call is 2.9's committed price (1e-10)", base["call"], r29["results"]["base"]["call"], 1e-10)
        add("the put is 2.9's committed price (1e-10)", base["put"], r29["results"]["base"]["put"], 1e-10)
    add("the stated premium of the call is 18.02", stated[("call", K)], 18.02, 1e-9)
    add("the stated premium of the put is 13.15", stated[("put", K)], 13.15, 1e-9)
    add("the stated premium of the 90 put is 8.60", stated[("put", params["collar"]["put_strike"])], 8.60, 1e-9)
    add("the stated premium of the 130 call is 8.29", stated[("call", params["collar"]["call_strike"])], 8.29, 1e-9)

    truth("C1 a payoff is never negative", all(row["call_payoff"] >= 0 and row["put_payoff"] >= 0 for row in ex["rows"]))
    truth("C1 the holder's profit and the writer's add up to nothing at every S_T",
          all(abs(row["call_holder_profit"] + row["call_writer_profit"]) <= 1e-12 and abs(row["put_holder_profit"] + row["put_writer_profit"]) <= 1e-12 for row in ex["rows"]))
    add("C1 the call's holder breaks even at 118.02", ex["call_break_even"], 118.02, 1e-9)
    add("C1 the put's holder breaks even at 86.85", ex["put_break_even"], 86.85, 1e-9)
    add("C1 the most the call's holder can lose is the premium", ex["call_holder_worst"], -18.02, 1e-9)
    add("C1 the most the put's writer can lose is the strike less the premium", ex["put_writer_worst_at_S_T_zero"], -86.85, 1e-9)

    add("C2 a call less a put pays S_T - K at every S_T (1e-12)", par["max_abs_payoff_difference"], 0.0, 1e-12)
    add("C2 so C - P = S - K e^(-rT) today: put-call parity (1e-12)", par["call_less_put_today"], par["S_less_discounted_strike"], 1e-12)
    add("C2 which is 4.877", par["call_less_put_today"], 4.877, 5e-4)
    add("C2 the strike discounted is 95.12", par["discounted_strike"], 95.12, 5e-3)

    truth("C3 intrinsic value plus time value is the price, for every row",
          all(abs(row["call_intrinsic"] + row["call_time_value"] - row["call"]) <= 1e-12 and abs(row["put_intrinsic"] + row["put_time_value"] - row["put"]) <= 1e-12 for row in rows))
    truth("C3 the call's time value is positive at every spot on the grid", all(row["call_time_value"] > 0 for row in rows))
    add("C3 the call at 120 is worth 32.23: 20 intrinsic and 12.23 time value", by_S[120.0]["call"], 32.23, 5e-3)
    add("C3 the call at 80 is worth 7.58, all of it time value", by_S[80.0]["call"], 7.58, 5e-3)
    add("C3 the put at 80 is worth 22.70: 20 intrinsic and 2.70 time value", by_S[80.0]["put"], 22.70, 5e-3)
    add("C3 the put at 60 is worth 36.97, less than its intrinsic value of 40", by_S[60.0]["put"], 36.97, 5e-3)
    truth("C3 time value is largest at the money on this grid, for the call and the put",
          max(rows, key=lambda row: row["call_time_value"])["S"] == K and max(rows, key=lambda row: row["put_time_value"])["S"] == K)

    truth("C4 the call is worth at least S - K e^(-rT), and no more than S, at every spot", all(row["call_floor"] - 1e-12 <= row["call"] <= row["S"] for row in rows))
    truth("C4 so it is worth more alive than exercised at every spot: never exercise an American call early", all(row["call_alive_less_exercised"] > 0 for row in rows))
    truth("C4 the European put is worth less than K - S at 60 and more at 80", by_S[60.0]["put_alive_less_exercised"] < 0 < by_S[80.0]["put_alive_less_exercised"])

    lev = res["leverage"]
    add("C5 at 140 the share has made 40%", lev[0]["share_return"], 0.40, 1e-12)
    add("C5 and the call 122%", lev[0]["call_return"], 1.22, 5e-3)
    add("C5 at 100 the share has lost nothing and the call everything", lev[1]["call_return"], -1.0, 1e-12)
    add("C5 at 90 the share has lost 10% and the call everything", lev[2]["call_return"], -1.0, 1e-12)
    add("C5 the share with a put at 100 can lose no more than the put's premium", res["protective_put"]["worst_profit"], -13.15, 1e-9)

    st = res["static_hedge"]
    by_T = {row["S_T"]: row["result"] for row in st["rows"]}
    add("C6 the fixed hedge holds 0.627 of a share", st["shares_held"], 0.627, 5e-4)
    add("C6 its result is +15.73 if the share finishes at 100", by_T[100.0], 15.73, 5e-3)
    add("C6 -9.37 at 60", by_T[60.0], -9.37, 5e-3)
    add("C6 +0.83 at 140", by_T[140.0], 0.83, 5e-3)
    add("C6 and -14.08 at 180", by_T[180.0], -14.08, 5e-3)
    truth("C6 best at the strike and worse the further the share finishes from it, either way",
          max(st["rows"], key=lambda row: row["result"])["S_T"] == K and by_T[60.0] < by_T[80.0] < by_T[100.0] > by_T[120.0] > by_T[140.0] > by_T[180.0])

    d = {row["S"]: row["call_delta"] for row in res["risk"]["delta_by_spot"]}
    add("C7 the call's delta is 0.408 at 80", d[80.0], 0.408, 5e-4)
    add("C7 0.627 at 100", d[100.0], 0.627, 5e-4)
    add("C7 and 0.783 at 120", d[120.0], 0.783, 5e-4)
    vols = res["risk"]["by_volatility"]
    truth("C7 the call and the put are each worth more at a higher volatility", all(a["call"] < b["call"] and a["put"] < b["put"] for a, b in zip(vols, vols[1:])))
    add("C7 the call is 14.23 at a volatility of 0.3", vols[1]["call"], 14.23, 5e-3)
    add("C7 and 21.79 at 0.5", vols[3]["call"], 21.79, 5e-3)
    add("C7 the call less the put is the same at every volatility (1e-12)", max(abs(v["call_less_put"] - vols[0]["call_less_put"]) for v in vols), 0.0, 1e-12)

    sd = res["straddle"]
    add("C8 the straddle costs 31.17", sd["cost"], 31.17, 1e-9)
    add("C8 it breaks even at 68.83", sd["break_even_low"], 68.83, 1e-9)
    add("C8 and at 131.17", sd["break_even_high"], 131.17, 1e-9)
    add("C8 its worst result is the whole cost, at the strike", sd["worst_profit"], -31.17, 1e-9)
    truth("C8 its payoff is the distance of S_T from the strike", all(abs(row["payoff"] - abs(row["S_T"] - K)) <= 1e-12 for row in sd["rows"]))

    co = res["collar"]
    add("C9 the collar's two options cost 0.31 between them", co["options_cost"], 0.31, 1e-9)
    truth("C9 the collared share is worth S_T held between 90 and 130", all(abs(row["value"] - min(max(row["S_T"], co["floor"]), co["cap"])) <= 1e-12 for row in co["rows"]))
    add("C9 the worst result is -10.31", co["worst_profit"], -10.31, 1e-9)
    add("C9 and the best +29.69", co["best_profit"], 29.69, 1e-9)
    add("C9 a call struck at 128.66 would pay for the put exactly", co["zero_cost_call_strike"], 128.66, 5e-3)

    f = res["d11"]
    truth("D11's fixtures: profit is payoff less cost at every point of every strategy",
          all(abs(p - (y - s["cost"])) <= 1e-12 for s in f["strategies"].values() for p, y in zip(s["profit"], s["payoff"])))

    qc = res["quoted_in_checks"]
    add("the page's checks: the call's holder has lost 18.02 with the share at 90", qc["call_holder_profit_at_check_S_T"], -18.02, 1e-9)
    add("the page's checks: a forward bought at 100 for the same premium would have lost 28.02", qc["call_holder_if_the_loss_ran_on_like_a_forward"], -28.02, 1e-9)
    add("the page's checks: the straddle makes 8.83 at 140", qc["straddle_profit_at_140"], 8.83, 1e-9)
    add("the page's checks: the collared share is worth 90 at 60 and 130 at 160", qc["collar_value_at_60"] + qc["collar_value_at_160"], 220.0, 1e-9)
    add("the page's checks: the call at 120 has 12.23 of time value", qc["time_value_of_the_call_at_120"], 12.23, 5e-3)
    add("the page's checks: the call at a volatility of 0.5 less the put at 0.4 would be 8.65", qc["call_at_sigma_0_5_less_put_at_sigma_0_4"], 8.65, 5e-3)
    add("the page's checks: the call rises 3.77 when volatility goes from 0.4 to 0.5", qc["rise_in_the_call_from_sigma_0_4_to_0_5"], 3.77, 5e-3)
    add("the page's checks: the share at 160 less the 0.31 the collar cost would be 159.69", qc["share_at_160_less_the_collar_s_cost"], 159.69, 1e-9)
    add("the page's checks: the call's time value at 120 is the interest on the strike, 4.88, and the put, 7.36 (1e-12)",
        qc["interest_on_the_strike_for_the_year"] + qc["put_at_120"], qc["time_value_of_the_call_at_120"], 1e-12)
    add("the page's checks: 4.877 scaled up with the call would be 5.90", qc["call_less_put_if_it_grew_in_proportion_to_the_call"], 5.90, 5e-3)

    if r27 is None:
        if not params["quick"]:
            truth("C10 2.7's committed JSON is beside this script for the full run", False)
    else:
        h = res["page_2_7"]
        add("C10 2.7 hedged the same call: its V0 is this page's price (1e-10)", h["V0"], base["call"], 1e-10)
        add("C10 2.7's unhedged spread is 29.6", h["unhedged_sd"], 29.6, 0.05)
        truth("C10 its first hedge is set once and never changed", h["static_N"] == 1)
        add("C10 and leaves a spread of 11.8", h["static_sd"], 11.8, 0.05)
        truth("C10 its most frequent hedge rebalances 4,096 times", h["most_N"] == 4096)
        add("C10 and leaves a spread of 0.22", h["most_sd"], 0.22, 0.005)
        truth("C10 around a mean that is nothing within two standard errors", abs(h["most_mean"]) <= 2 * h["most_se_of_mean"])

    if oracle is None:
        if not params["quick"]:
            truth("C11 QuantLib is importable for the full run (I4)", False)
    else:
        e = oracle["errors"]
        add("C11 QuantLib's analytic engine gives the same prices on the spot grid (1e-10)", e["price"], 0.0, 1e-10)
        add("C11 the same deltas (1e-10)", e["delta"], 0.0, 1e-10)
        add("C11 and the same four premiums (1e-10)", e["premiums"], 0.0, 1e-10)
        am = {row["S"]: row for row in oracle["american_put"]}
        truth("C11 QuantLib's two American engines agree to a penny at every spot",
              all(abs(row["american_put_by_tree"] - row["american_put_by_finite_differences"]) <= 0.01 for row in oracle["american_put"]))
        truth("C11 the American put is worth at least the European and at least its intrinsic value at every spot",
              all(row["american_put_by_tree"] >= row["european_put"] - 1e-9 and row["american_put_by_tree"] >= row["intrinsic"] - 1e-9 for row in oracle["american_put"]))
        add("C11 at 100 the American put is 13.67 against the European 13.15", am[100.0]["american_put_by_tree"], 13.67, 0.01)
        add("C11 at 60 it is 40.02, above the 40 that exercising pays, where the European put is 36.97", am[60.0]["american_put_by_tree"], 40.02, 0.01)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="snippet check: QuantLib optional, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "random": "none -- arithmetic only, so no seed (I6 has nothing to seed)",
        "market": {"S": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.4, "T": 1.0, "q": 0.0,
                   "note": "Part 2's option (page 2.9): a share at 100 paying no dividend, strike 100, one year"},
        "expiry_grid": [60.0, 80.0, 100.0, 120.0, 140.0],
        "spot_grid": [60.0, 80.0, 100.0, 120.0, 140.0],
        "static_grid": [60.0, 80.0, 100.0, 120.0, 140.0, 180.0],
        "wide_grid": [float(x) for x in range(401)],
        "vol_grid": [0.2, 0.3, 0.4, 0.5],
        "leverage_outcomes": [140.0, 100.0, 90.0],
        "collar": {"put_strike": 90.0, "call_strike": 130.0},
        "check_S_T": 90.0,
        "d11": {"S_T": [40.0, 180.0, 141]},
    }
    res = run(params)
    script_dir = Path(__file__).resolve().parent
    r29 = committed(script_dir, "2_9_black_scholes_formula.json")
    r27 = committed(script_dir, "2_7_delta_hedging.json")
    res["page_2_7"] = page_2_7(r27)
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C11: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    res["oracle"] = oracle
    checks = build_checks(res, params, oracle, r29, r27)

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
