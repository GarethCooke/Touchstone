"""Forwards -- the arithmetic behind page 1.1.

Serves page 1.1 (docs/quant-learn-index-v1.md): cash-and-carry gives
F = S e^((r - q) T) with no stochastics at all; the value of a forward after
inception; delta of one; and the page's check -- replicate a forward with spot
plus borrowing and show the payoffs match.

Part 1 is arithmetic. Nothing here is random, so there is no seed. Symbols are
the notation ledger's: S the spot price of the underlying, r the risk-free
rate in the currency the price is quoted in, q the yield the underlying pays
its holder, T the delivery date in years, K the delivery price, F the forward
price. Rates are continuously compounded decimals (page 0.3).

Session decision (owner, 2026-11-16): the worked forward is an FX forward.
The underlying is one pound; its price S is in dollars per pound; r is the
dollar rate; q is the sterling rate, the yield a pound earns while it is
held. A share with a dividend yield is the same formula and is the aside. All
market levels here are illustrative, not a market's.

  C1  Cash-and-carry. To have one pound at T: buy e^(-qT) pounds now, with
      borrowed dollars, and deposit them. At T the deposit is one pound and
      the loan is S e^((r - q) T) dollars. That is a forward at delivery price
      F = S e^((r - q) T), built with no money down, so it is the only
      delivery price at which a forward costs nothing. At every final spot
      S_T on a grid, the forward's payoff S_T - F and the replication's --
      one pound worth S_T, less the loan -- are equal (1e-12).
  C2  The arbitrage. A forward quoted at any other price is free money: sell
      it and build the replication if it is dear, the reverse if it is cheap.
      The profit is the same at every S_T: the quoted price less F.
  C3  Value after inception. A forward to buy at K is worth
      V = S e^(-q tau) - K e^(-r tau) = (F_now - K) e^(-r tau), tau the time
      left: zero at inception, and after six months a function of spot that
      is a straight line. Values on one million pounds at three spots.
  C4  Delta. dV/dS = e^(-q tau): one when q = 0, a little under one with a
      yield (0.970 here), and the same at every spot -- the value is linear,
      so a bump of any size gives the same number and gamma is zero (1e-10).
      It tends to one as delivery approaches.
  C5  Rate risk. dV/dr = tau K e^(-r tau) and dV/dq = -tau S e^(-q tau). At
      inception the two are equal and opposite, because S e^(-qT) = K e^(-rT)
      is what makes the forward worth zero. Analytic against a central bump.
  C6  Settlement. Physical delivery -- pay K dollars, receive one pound, sell
      it at S_T -- and cash settlement of S_T - K leave the same dollars at
      every S_T (1e-12).
  C7  The desk's spelling, and page 1.0's bug again. With simple rates and
      each currency's own day count, F = S (1 + R_usd d/360) / (1 + R_gbp
      d/365) is the same F when the simple rates are the continuous ones
      restated (1e-12). Give sterling the dollar's Actual/360 by mistake and
      the forward moves by 5.2 points on 252.5.
  C8  The share. S = 100, r = 0.05, q = 0.03, T = 1: F = 102.02, the figure on
      page 2.9 and in the notation ledger; read from 2.9's committed JSON
      where it is present.
  C9  The oracle (I4). QuantLib discount factors on flat curves give the same
      forward price and the same contract value (1e-12).

Run from the repository root:

    uv run experiments/1_1_forwards.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_1_forwards.json beside this file: parameters in, results out, no
timestamps. No plotting here; the site draws. Exits non-zero if any check
fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import exp, log
from pathlib import Path

PAGE = "1.1"
BASIS_POINT = 1e-4
POINT = 1e-4  # one forward point on a rate quoted to four decimal places


# --- the forward price and the contract's value -------------------------------


def forward_price(S: float, r: float, q: float, T: float) -> float:
    """The delivery price at which a forward costs nothing to enter."""
    return S * exp((r - q) * T)


def forward_value(S: float, K: float, r: float, q: float, tau: float) -> float:
    """Value today of a contract to buy one unit at K, with tau years to delivery."""
    return S * exp(-q * tau) - K * exp(-r * tau)


def forward_delta(q: float, tau: float) -> float:
    """dV/dS: how much the contract's value moves per unit move in spot."""
    return exp(-q * tau)


# --- the replication: spot plus borrowing --------------------------------------


def replicate(S: float, r: float, q: float, T: float) -> dict:
    """Build 'one unit of the underlying at T' today, with borrowed money.

    Buy e^(-qT) units now -- they earn the yield q and grow to one unit -- and
    borrow what they cost. Nothing is paid today; at T the loan is repaid.
    """
    units_bought = exp(-q * T)
    borrowed = units_bought * S
    return {"units_bought": units_bought, "borrowed": borrowed, "net_cost_today": units_bought * S - borrowed,
            "units_at_T": units_bought * exp(q * T), "loan_repaid_at_T": borrowed * exp(r * T)}


def replication_payoff(rep: dict, S_T: float) -> float:
    """What the replication is worth at T: the unit, at the final spot, less the loan."""
    return rep["units_at_T"] * S_T - rep["loan_repaid_at_T"]


def forward_payoff(S_T: float, K: float) -> float:
    return S_T - K


# --- the oracle ---------------------------------------------------------------


def quantlib_oracle(params: dict, res: dict) -> dict | None:
    try:
        import QuantLib as ql
    except ImportError:
        return None
    X = params["fx"]
    dc = ql.Actual365Fixed()
    today = ql.Date(16, 11, 2026)
    ql.Settings.instance().evaluationDate = today
    usd = ql.FlatForward(today, X["r"], dc, ql.Continuous)
    gbp = ql.FlatForward(today, X["q"], dc, ql.Continuous)
    F = X["S"] * gbp.discount(X["T"]) / usd.discount(X["T"])
    worst = abs(F - res["fx"]["F"])
    for row in res["fx"]["value_after_inception"]["rows"]:
        tau = res["fx"]["value_after_inception"]["tau"]
        v = row["S"] * gbp.discount(tau) - res["fx"]["F"] * usd.discount(tau)
        worst = max(worst, abs(v - row["value_per_unit"]))
    return {"version": ql.__version__, "forward_price": F, "max_abs_error": worst}


def page_2_9_forward(script_dir: Path) -> float | None:
    """F at q = 0.03 from 2.9's committed result, if it is beside this script."""
    path = script_dir / "2_9_black_scholes_formula.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)["results"]["dividends"]["q_rows"]["q_0.03"]["F"]


# --- the experiment -----------------------------------------------------------


def run(params: dict) -> dict:
    X = params["fx"]
    S, r, q, T, N = X["S"], X["r"], X["q"], X["T"], X["notional"]
    F = forward_price(S, r, q, T)

    # C1 the replication, at every final spot on the grid
    rep = replicate(S, r, q, T)
    rows = [{"S_T": s, "forward_payoff": forward_payoff(s, F), "unit_worth": rep["units_at_T"] * s,
             "loan_repaid": rep["loan_repaid_at_T"], "replication_payoff": replication_payoff(rep, s)} for s in X["S_T_grid"]]
    replication = {**rep, "rows": rows,
                   "max_abs_difference": max(abs(row["forward_payoff"] - row["replication_payoff"]) for row in rows)}

    # C2 the arbitrage at a quoted price that is not F
    arb = []
    for quoted in X["mispriced_quotes"]:
        side = 1 if quoted > F else -1  # +1: sell the forward, buy the replication
        profits = [side * (forward_payoff(s, F) - forward_payoff(s, quoted)) for s in X["S_T_grid"]]
        arb.append({"quoted": quoted, "action": "sell the forward, build the replication" if side > 0 else "buy the forward, sell the replication",
                    "profit_per_unit_at_T": profits[0], "profit_spread_across_S_T": max(profits) - min(profits),
                    "profit_on_notional": profits[0] * N})

    # C3 value after inception
    A = X["after"]
    tau = T - A["t"]
    after_rows = []
    for s in A["spots"]:
        F_now = forward_price(s, r, q, tau)
        v = forward_value(s, F, r, q, tau)
        after_rows.append({"S": s, "forward_price_now": F_now, "points_now": (F_now - s) / POINT, "value_per_unit": v, "value_via_forward": (F_now - F) * exp(-r * tau),
                           "value_on_notional": v * N})
    after = {"t": A["t"], "tau": tau, "rows": after_rows}

    # C4 delta
    delta0 = forward_delta(q, T)
    bumps = [{"h": h, "delta_by_bump": (forward_value(S + h, F, r, q, T) - forward_value(S, F, r, q, T)) / h} for h in X["delta_bumps"]]
    delta = {"at_inception": delta0, "at_tau": forward_delta(q, tau), "with_no_yield": forward_delta(0.0, T),
             "bumps": bumps, "max_abs_bump_error": max(abs(b["delta_by_bump"] - delta0) for b in bumps),
             "on_notional": delta0 * N, "toward_delivery": [{"tau": t, "delta": forward_delta(q, t)} for t in (1.0, 0.5, 0.25, 1 / 12, 0.0)]}

    # C5 rate risk at inception, per basis point on the notional
    h = X["rate_bump"]
    dV_dr = T * F * exp(-r * T)
    dV_dq = -T * S * exp(-q * T)
    rates = {"dV_dr_per_bp_on_notional": dV_dr * BASIS_POINT * N, "dV_dq_per_bp_on_notional": dV_dq * BASIS_POINT * N,
             "dV_dr_by_bump": (forward_value(S, F, r + h, q, T) - forward_value(S, F, r - h, q, T)) / (2 * h) * BASIS_POINT * N,
             "dV_dq_by_bump": (forward_value(S, F, r, q + h, T) - forward_value(S, F, r, q - h, T)) / (2 * h) * BASIS_POINT * N,
             "sum_at_inception": (dV_dr + dV_dq) * BASIS_POINT * N}

    # C6 settlement
    settle_rows = [{"S_T": s, "physical_pay_dollars": F * N, "physical_receive_pounds": N, "physical_net_dollars_if_sold_at_S_T": (s - F) * N,
                    "cash_settlement_dollars": forward_payoff(s, F) * N} for s in X["S_T_grid"]]
    settlement = {"rows": settle_rows,
                  "max_abs_difference": max(abs(row["physical_net_dollars_if_sold_at_S_T"] - row["cash_settlement_dollars"]) for row in settle_rows)}

    # C7 the desk's spelling: simple rates, each currency's own day count
    M = X["money_market"]
    d = M["days"]
    R_usd = (exp(r * d / 365) - 1) / (d / 360)   # simple, Actual/360, restating r over d days
    R_gbp = (exp(q * d / 365) - 1) / (d / 365)   # simple, Actual/365 Fixed, restating q over d days
    F_desk = S * (1 + R_usd * d / 360) / (1 + R_gbp * d / 365)
    F_bug = S * (1 + R_usd * d / 360) / (1 + R_gbp * d / 360)
    desk = {"days": d, "R_usd_simple_act_360": R_usd, "R_gbp_simple_act_365": R_gbp, "F": F_desk, "F_sterling_on_act_360": F_bug,
            "points": (F_desk - S) / POINT, "points_sterling_on_act_360": (F_bug - S) / POINT,
            "error_points": (F_bug - F_desk) / POINT, "error_on_notional": (F_bug - F_desk) * N}

    fx = {"F": F, "forward_points": (F - S) / POINT, "delivery_dollars_on_notional": F * N, "value_at_inception": forward_value(S, F, r, q, T),
          "replication": replication, "arbitrage": arb, "value_after_inception": after, "delta": delta, "rates": rates,
          "settlement": settlement, "desk_spelling": desk}

    # C8 the share
    E = params["share"]
    share = {"F": forward_price(E["S"], E["r"], E["q"], E["T"]), "F_no_yield": forward_price(E["S"], E["r"], 0.0, E["T"]),
             "delta": forward_delta(E["q"], E["T"]), "delta_no_yield": forward_delta(0.0, E["T"]),
             "implied_carry": log(forward_price(E["S"], E["r"], E["q"], E["T"]) / E["S"]) / E["T"]}
    # Figures the page's check questions quote, right answers and wrong ones alike (I5):
    # a wrong option's number is what its misconception computes, so it is computed here.
    cent = 0.01
    quoted = {
        "value_change_for_one_cent_on_notional": delta0 * cent * N,
        "one_cent_at_delta_one": cent * N,
        "one_cent_at_F_over_S": F / S * cent * N,
        "full_unit_bought_grows_to": exp(q * T),
        "full_unit_loan_repaid": S * exp(r * T),
        "undiscounted_spot_less_K_on_notional": (S - F) * N,
        "points_run_off_in_six_months": (F - forward_price(S, r, q, tau)) / POINT,
    }
    return {"fx": fx, "share": share, "quoted_in_checks": quoted}


def build_checks(res: dict, params: dict, oracle: dict | None, F_2_9: float | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    fx, share, X = res["fx"], res["share"], params["fx"]
    rep = fx["replication"]
    add("C1 the forward price is 1.2753 dollars per pound", fx["F"], 1.2753, 5e-5)
    add("C1 which is 252.5 points over spot", fx["forward_points"], 252.5, 0.05)
    add("C1 the replication costs nothing today", rep["net_cost_today"], 0.0, 0.0)
    add("C1 it holds exactly one pound at T (1e-12)", rep["units_at_T"], 1.0, 1e-12)
    add("C1 and owes exactly F dollars at T (1e-12)", rep["loan_repaid_at_T"], fx["F"], 1e-12)
    add("C1 forward and replication pay the same at every final spot on the grid (1e-12)", rep["max_abs_difference"], 0.0, 1e-12)
    add("C1 a forward struck at F is worth nothing at inception (1e-12)", fx["value_at_inception"], 0.0, 1e-12)

    for a in fx["arbitrage"]:
        add(f"C2 quoted at {a['quoted']}: the profit is the quote less F in size", abs(a["profit_per_unit_at_T"]), abs(a["quoted"] - fx["F"]), 1e-12)
        add(f"C2 quoted at {a['quoted']}: the profit is the same at every final spot (1e-12)", a["profit_spread_across_S_T"], 0.0, 1e-12)

    after = fx["value_after_inception"]["rows"]
    add("C3 the two spellings of the value agree at every spot (1e-12)", max(abs(r["value_per_unit"] - r["value_via_forward"]) for r in after), 0.0, 1e-12)
    truth("C3 the value rises with spot", all(a["value_per_unit"] < b["value_per_unit"] for a, b in zip(after, after[1:])))
    steps = [(b["value_per_unit"] - a["value_per_unit"]) / (b["S"] - a["S"]) for a, b in zip(after, after[1:])]
    add("C3 by the same amount per unit of spot between each pair of spots: a straight line (1e-12)", max(steps) - min(steps), 0.0, 1e-12)
    add("C3 that slope is the delta with six months left, e^(-q tau)", steps[0], fx["delta"]["at_tau"], 1e-12)

    d = fx["delta"]
    add("C4 delta at inception is e^(-qT) = 0.970", d["at_inception"], 0.970, 5e-4)
    add("C4 with no yield it is exactly one", d["with_no_yield"], 1.0, 0.0)
    add("C4 a bump of any size gives the same delta: no gamma (1e-10)", d["max_abs_bump_error"], 0.0, 1e-10)
    td = [row["delta"] for row in d["toward_delivery"]]
    truth("C4 delta rises to exactly one as delivery approaches", all(a < b for a, b in zip(td, td[1:])) and td[-1] == 1.0)

    rt = fx["rates"]
    add("C5 dV/dr agrees with a central bump (1e-6 relative)", rt["dV_dr_by_bump"], rt["dV_dr_per_bp_on_notional"], 1e-6, "rel")
    add("C5 dV/dq agrees with a central bump (1e-6 relative)", rt["dV_dq_by_bump"], rt["dV_dq_per_bp_on_notional"], 1e-6, "rel")
    add("C5 at inception the two rate sensitivities are equal and opposite (1e-9)", rt["sum_at_inception"], 0.0, 1e-9)
    add("C5 each is 121.31 dollars a basis point on one million pounds", rt["dV_dr_per_bp_on_notional"], 121.31, 0.005)

    add("C6 physical delivery and cash settlement leave the same dollars at every final spot (1e-9 on a million)", fx["settlement"]["max_abs_difference"], 0.0, 1e-9)

    desk = fx["desk_spelling"]
    add("C7 simple rates on each currency's own day count give the same F (1e-12)", desk["F"], fx["F"], 1e-12)
    add("C7 sterling counted on Actual/360 by mistake moves the forward by 5.2 points", abs(desk["error_points"]), 5.2, 0.05)
    truth("C7 and lowers it: more sterling interest assumed, so fewer dollars per pound forward", desk["error_points"] < 0)

    qc = res["quoted_in_checks"]
    add("the page's checks: one cent on spot moves the value by 9,704 dollars on a million pounds, not 10,000", qc["value_change_for_one_cent_on_notional"], 9704.46, 0.005)
    add("the page's checks: buying a whole pound today leaves 1.0305 pounds at T, more than the forward delivers", qc["full_unit_bought_grows_to"], 1.0305, 5e-5)

    add("C8 the share's forward is 102.02", share["F"], 102.02, 0.005)
    add("C8 with no dividend it is 105.13", share["F_no_yield"], 105.13, 0.005)
    add("C8 the carry implied by the share's forward is r - q = 0.02", share["implied_carry"], params["share"]["r"] - params["share"]["q"], 1e-12)
    add("C8 the share's carry is the pound's: F / S is the same in both examples", share["F"] / params["share"]["S"], fx["F"] / X["S"], 1e-12)
    if F_2_9 is None:
        if not params["quick"]:
            truth("C8 2.9's committed JSON is beside this script for the full run", False)
    else:
        add("C8 it is the forward on page 2.9, from that page's committed result (1e-12)", share["F"], F_2_9, 1e-12)

    if oracle is None:
        if not params["quick"]:
            truth("C9 QuantLib is importable for the full run (I4)", False)
    else:
        add("C9 QuantLib's discount factors give the same forward price and contract values (1e-12)", oracle["max_abs_error"], 0.0, 1e-12)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="snippet check: QuantLib optional, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "random": "none -- arithmetic only, so no seed (I6 has nothing to seed)",
        "fx": {"pair": "GBP/USD", "underlying": "one pound", "price_unit": "dollars per pound",
               "S": 1.25, "r": 0.05, "q": 0.03, "T": 1.0, "notional": 1_000_000.0,
               "r_is": "the dollar rate, continuously compounded", "q_is": "the sterling rate, continuously compounded",
               "S_T_grid": [1.00, 1.10, 1.20, 1.25, 1.30, 1.40, 1.50],
               "mispriced_quotes": [1.30, 1.26],
               "after": {"t": 0.5, "spots": [1.20, 1.25, 1.30]},
               "delta_bumps": [0.0001, 0.01, 0.10, 0.50], "rate_bump": 1e-6,
               "money_market": {"days": 365},
               "note": "illustrative levels, not a market's"},
        "share": {"S": 100.0, "r": 0.05, "q": 0.03, "T": 1.0, "note": "page 2.9's dividend case"},
    }
    res = run(params)
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C9: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    F_2_9 = page_2_9_forward(Path(__file__).resolve().parent)
    res["oracle"] = oracle
    res["page_2_9_forward"] = F_2_9
    checks = build_checks(res, params, oracle, F_2_9)

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
