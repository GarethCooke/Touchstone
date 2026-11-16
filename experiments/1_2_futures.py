"""Futures -- the arithmetic behind page 1.2.

Serves page 1.2 (docs/quant-learn-index-v1.md): exchange-traded forwards;
clearing, initial and variation margin, daily settlement, rolling; why they
exist; basis risk; and the page's check -- walk a margin account through a
week of prices.

Part 1 is arithmetic. Nothing here is random, so there is no seed. Symbols are
the notation ledger's: S the spot price, r the risk-free rate in the currency
the price is quoted in, q the yield the underlying pays its holder, T the
delivery date in years, F the forward price. Rates are continuously compounded
decimals (page 0.3).

Session decisions (owner, 2026-11-16): the contract is a pound future, the
contract of page 1.1 put on an exchange -- 62,500 pounds a contract, priced in
dollars per pound to four decimal places, 16 contracts for 1.1's one million
pounds, with 1.1's spot and rates, so its price starts at 1.1's forward price.
The margin walk is a customer's account: initial margin, a maintenance level,
and a call back up to the initial margin when the balance falls below it. The
contract size and tick are CME's British pound future's; the margin levels and
the week's prices are illustrative, not an exchange's.

  C1  The price. With constant rates the futures price is the forward price
      (Hull ch. 5; Cox, Ingersoll and Ross 1981): F = S e^((r - q) T) =
      1.275252, which trades at the nearest tick, 1.2753.
  C2  The contract. One tick is 6.25 dollars a contract; one point on 16
      contracts is 100 dollars; the initial margin is 400 points, 3.1% of the
      dollars the contract commits.
  C3  The margin walk. Long 16 contracts at 1.2753, five daily settlement
      prices. Each day's gain or loss is the change in the settlement price
      on the position, added to the account that day. The balance falls below
      the maintenance level once, on the third day, and the call restores the
      initial margin. Money paid in, plus the gains and losses, is the closing
      balance; the gains and losses sum to the position times the week's
      price change.
  C4  Against the forward. A forward at the same price over the same week has
      moved no cash; its value is the same price change, discounted from the
      delivery date.
  C5  The delta. The futures price moves e^((r - q) tau) for each unit of
      spot, a little over one, and the gain is cash that day. Discounted from
      the delivery date it is the forward's e^(-q tau) of page 1.1.
  C6  The basis. Futures less spot is 1.1's points, S (e^((r - q) tau) - 1):
      it runs to nothing at delivery, whatever spot does.
  C7  Basis risk. A hedge closed before delivery fixes the futures price paid
      less the basis on the day it is closed. That basis depends on the
      interest rates then, so the price is fixed to within tens of points
      where spot can move by a thousand.
  C8  The roll. The next contract costs more than the near one by the points
      between their two dates.
  C9  The oracle (I4). QuantLib discount factors on flat curves give the same
      futures prices at every delivery date used (1e-12).

Run from the repository root:

    uv run experiments/1_2_futures.py [--quick]

--quick is for the learn site's build-time snippet check (I3): it skips the
QuantLib comparison if QuantLib is not installed and writes NO JSON -- the
committed result is always the full run, which requires QuantLib (I4).

Writes 1_2_futures.json beside this file: parameters in, results out, no
timestamps. No plotting here; the site draws. Exits non-zero if any check
fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import exp
from pathlib import Path

PAGE = "1.2"
POINT = 1e-4  # one point, and one tick, on a price quoted to four decimal places


# --- the futures price ---------------------------------------------------------


def futures_price(S: float, r: float, q: float, T: float) -> float:
    """The forward price of page 1.1; the futures price too while rates are constant."""
    return S * exp((r - q) * T)


def to_tick(price: float, tick: float = POINT) -> float:
    """The nearest price the contract can trade at."""
    return round(round(price / tick) * tick, 10)


def points(difference: float) -> float:
    return difference / POINT


# --- the margin account --------------------------------------------------------


def margin_walk(trade_price: float, settlements: list[dict], contracts: int, size: float,
                initial_margin: float, maintenance_margin: float) -> list[dict]:
    """Walk a long position's margin account through daily settlement.

    The account opens with the initial margin. Each day the position is marked
    to that day's settlement price and the gain or loss since the previous mark
    is added to the balance. If the balance is then below the maintenance
    margin, the holder is called for enough to bring it back to the initial
    margin, not just to the maintenance level.
    """
    position = contracts * size
    balance = initial_margin
    previous = trade_price
    rows = []
    for day in settlements:
        price = day["price"]
        gain = round((price - previous) * position, 2)
        balance_before_call = round(balance + gain, 2)
        call = round(initial_margin - balance_before_call, 2) if balance_before_call < maintenance_margin else 0.0
        balance = round(balance_before_call + call, 2)
        rows.append({"day": day["day"], "settlement_price": price, "change_points": round(points(price - previous), 6),
                     "gain": gain, "balance_before_call": balance_before_call, "margin_call": call, "balance": balance})
        previous = price
    return rows


# --- the hedge closed before delivery ------------------------------------------


def hedged_price(F_bought: float, S_then: float, r_minus_q_then: float, tau_left: float) -> dict:
    """Buy the future at F_bought; later sell it and buy the pounds at spot.

    The pounds cost S_then and the future has gained F_then - F_bought, so the
    net price paid is S_then - (F_then - F_bought) = F_bought - basis_then.
    """
    F_then = S_then * exp(r_minus_q_then * tau_left)
    basis = F_then - S_then
    return {"S_then": S_then, "rate_difference_then": r_minus_q_then, "F_then": F_then, "basis_points_then": points(basis),
            "futures_gain_per_pound": F_then - F_bought, "net_price_paid": S_then - (F_then - F_bought),
            "net_price_via_basis": F_bought - basis}


# --- the oracle ----------------------------------------------------------------


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
    worst = abs(X["S"] * gbp.discount(X["T"]) / usd.discount(X["T"]) - res["price"]["F"])
    for row in res["basis"]["rows"]:
        tau = row["tau"]
        F = X["S"] * gbp.discount(tau) / usd.discount(tau) if tau > 0 else X["S"]
        worst = max(worst, abs(F - row["futures_price"]))
    return {"version": ql.__version__, "max_abs_error": worst}


def page_1_1_results(script_dir: Path) -> dict | None:
    """What this page takes from 1.1's committed result, if it is beside this script."""
    path = script_dir / "1_1_forwards.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        res = json.load(f)["results"]
    return {"F": res["fx"]["F"], "forward_value_change_for_one_cent": res["quoted_in_checks"]["value_change_for_one_cent_on_notional"]}


# --- the experiment ------------------------------------------------------------


def run(params: dict) -> dict:
    X, C, W = params["fx"], params["contract"], params["walk"]
    S, r, q, T = X["S"], X["r"], X["q"], X["T"]
    size, n = C["size"], C["contracts"]
    position = n * size
    initial, maintenance = n * C["initial_margin_per_contract"], n * C["maintenance_margin_per_contract"]

    # C1 the price
    F = futures_price(S, r, q, T)
    F_tick = to_tick(F)
    price = {"F": F, "F_at_nearest_tick": F_tick, "points_over_spot": points(F - S)}

    # C2 the contract
    contract = {"position_pounds": position, "tick_value_per_contract": POINT * size, "point_value_on_position": POINT * position,
                "dollars_committed_per_contract": F_tick * size, "dollars_committed_on_position": F_tick * position,
                "initial_margin": initial, "maintenance_margin": maintenance,
                "initial_margin_in_points": C["initial_margin_per_contract"] / (POINT * size),
                "initial_margin_as_fraction_of_dollars_committed": initial / (F_tick * position),
                "contracts_for_an_amount_that_is_not_a_multiple": C["awkward_amount"] / size}

    # C3 the margin walk
    rows = margin_walk(W["trade_price"], W["settlements"], n, size, initial, maintenance)
    calls = [row for row in rows if row["margin_call"] > 0]
    total_gain = round(sum(row["gain"] for row in rows), 2)
    paid_in = round(initial + sum(row["margin_call"] for row in rows), 2)
    walk = {"rows": rows, "total_gain": total_gain, "paid_in": paid_in, "closing_balance": rows[-1]["balance"],
            "days_with_a_call": [row["day"] for row in calls], "calls": [row["margin_call"] for row in calls],
            "price_change_points": round(points(rows[-1]["settlement_price"] - W["trade_price"]), 6),
            "position_times_price_change": round((rows[-1]["settlement_price"] - W["trade_price"]) * position, 2),
            "lowest_balance": min(row["balance_before_call"] for row in rows),
            "excess_over_initial_at_close": round(rows[-1]["balance"] - initial, 2)}

    # C4 the same week on a forward at the same price: no cash, a discounted value
    tau_left = T - W["days_elapsed"] / 365
    F_close = rows[-1]["settlement_price"]
    forward = {"delivery_price": W["trade_price"], "forward_price_at_close": F_close, "tau_left": tau_left,
               "discount_factor": exp(-r * tau_left), "value": (F_close - W["trade_price"]) * exp(-r * tau_left) * position,
               "cash_moved": 0.0, "futures_cash_moved": total_gain}

    # C5 the delta: per unit of spot, and for one cent on the position
    cent = 0.01
    futures_delta = exp((r - q) * T)
    delta = {"futures_price_per_unit_of_spot": futures_delta, "one_cent_on_position": futures_delta * cent * position,
             "one_cent_discounted_from_delivery": futures_delta * cent * position * exp(-r * T),
             "forward_delta_of_page_1_1": exp(-q * T)}

    # C6 the basis runs off to nothing at delivery
    basis_rows = [{"months_to_delivery": m, "tau": m / 12, "futures_price": futures_price(S, r, q, m / 12),
                   "basis_points": points(futures_price(S, r, q, m / 12) - S)} for m in params["basis"]["months_to_delivery"]]
    basis = {"spot_held_at": S, "rows": basis_rows}

    # C7 a hedge closed two months before delivery
    H = params["hedge"]
    tau_h = H["months_left_when_closed"] / 12
    grid = [hedged_price(F_tick, s, d, tau_h) for d in H["rate_differences_then"] for s in H["spots_then"]]
    nets = [g["net_price_paid"] for g in grid]
    unchanged = hedged_price(F_tick, S, r - q, tau_h)
    hedge = {"F_bought": F_tick, "tau_left_when_closed": tau_h, "grid": grid,
             "unchanged_rates_and_spot": unchanged,
             "net_price_lowest": min(nets), "net_price_highest": max(nets),
             "net_price_range_points": points(max(nets) - min(nets)),
             "unhedged_price_range_points": points(max(H["spots_then"]) - min(H["spots_then"])),
             "max_abs_identity_error": max(abs(g["net_price_paid"] - g["net_price_via_basis"]) for g in grid),
             "basis_points_per_one_percent_of_rate_difference": points(S * (exp((r - q + 0.01) * tau_h) - exp((r - q) * tau_h)))}

    # C8 the roll: the near contract and the next
    R = params["roll"]
    near, nxt = futures_price(S, r, q, R["near_months"] / 12), futures_price(S, r, q, R["next_months"] / 12)
    roll = {"near_price": near, "next_price": nxt, "spread_points": points(nxt - near),
            "points_between_the_two_dates": points(S * (exp((r - q) * R["next_months"] / 12) - exp((r - q) * R["near_months"] / 12)))}

    # Figures the page's check questions quote, right answers and wrong ones alike (I5):
    # a wrong option's number is what its misconception computes, so it is computed here.
    third = rows[2]
    quoted = {
        "call_if_topped_up_only_to_maintenance": round(maintenance - third["balance_before_call"], 2),
        "call_if_it_were_the_day_s_loss": round(-third["gain"], 2),
        "points_below_trade_price_on_the_third_day": round(points(W["trade_price"] - third["settlement_price"]), 6),
        "loss_if_margin_paid_in_were_the_cost": paid_in,
        "loss_if_the_call_were_the_loss": calls[0]["margin_call"] if calls else 0.0,
        "net_price_if_the_hedge_were_exact": F_tick,
        "net_price_with_unchanged_rates": unchanged["net_price_paid"],
    }
    return {"price": price, "contract": contract, "walk": walk, "forward_comparison": forward, "delta": delta, "basis": basis,
            "hedge": hedge, "roll": roll, "quoted_in_checks": quoted}


def build_checks(res: dict, params: dict, oracle: dict | None, page_1_1: dict | None) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    p, c, w, W = res["price"], res["contract"], res["walk"], params["walk"]
    add("C1 the futures price is 1.2753 dollars per pound at the nearest tick", p["F_at_nearest_tick"], 1.2753, 1e-12)
    add("C1 which is the price the walk's position is bought at", W["trade_price"], p["F_at_nearest_tick"], 1e-12)
    if page_1_1 is None:
        if not params["quick"]:
            truth("C1 1.1's committed JSON is beside this script for the full run", False)
    else:
        add("C1 it is page 1.1's forward price, from that page's committed result (1e-12)", p["F"], page_1_1["F"], 1e-12)

    add("C2 one tick is 6.25 dollars a contract", c["tick_value_per_contract"], 6.25, 1e-9)
    add("C2 one point on 16 contracts is 100 dollars", c["point_value_on_position"], 100.0, 1e-9)
    add("C2 16 contracts are one million pounds", c["position_pounds"], 1_000_000.0, 0.0)
    add("C2 the initial margin is 400 points a contract", c["initial_margin_in_points"], 400.0, 1e-9)
    add("C2 and 3.1% of the dollars the position commits", c["initial_margin_as_fraction_of_dollars_committed"], 0.031, 5e-4)

    rows = w["rows"]
    add("C3 the week's gains and losses sum to the position times the price change (1e-6)", w["total_gain"], w["position_times_price_change"], 1e-6)
    add("C3 which is a loss of 1,300 dollars on a fall of 13 points", w["total_gain"], -1300.0, 1e-6)
    add("C3 money paid in plus gains and losses is the closing balance (1e-6)", w["paid_in"] + w["total_gain"], w["closing_balance"], 1e-6)
    truth("C3 there is exactly one margin call, on the third day", w["days_with_a_call"] == [rows[2]["day"]])
    add("C3 it is for 9,400 dollars", w["calls"][0], 9400.0, 1e-6)
    add("C3 and it restores the initial margin, not the maintenance level", rows[2]["balance"], c["initial_margin"], 1e-6)
    truth("C3 the balance is below the maintenance level only on that day", [r["balance_before_call"] < c["maintenance_margin"] for r in rows] == [False, False, True, False, False])
    add("C3 the closing balance is 48,100 dollars", w["closing_balance"], 48100.0, 1e-6)
    add("C3 each day's gain is 100 dollars a point (1e-6)", max(abs(r["gain"] - 100.0 * r["change_points"]) for r in rows), 0.0, 1e-6)

    f = res["forward_comparison"]
    add("C4 the forward over the same week is worth about -1,237 dollars, and has moved no cash", f["value"], -1237.0, 1.0)
    truth("C4 that is smaller in size than the future's 1,300, by the discount factor to delivery", abs(f["value"]) < abs(f["futures_cash_moved"]) and f["cash_moved"] == 0.0)
    add("C4 the two differ by exactly the discount factor (1e-12)", f["value"] / f["futures_cash_moved"], f["discount_factor"], 1e-12)

    dl = res["delta"]
    add("C5 the futures price moves 1.0202 for each unit of spot", dl["futures_price_per_unit_of_spot"], 1.0202, 5e-5)
    add("C5 one cent on spot is 10,202 dollars on 16 contracts, in cash that day", dl["one_cent_on_position"], 10_202.0, 0.5)
    add("C5 discounted from the delivery date that is the forward's delta times one cent (1e-9 relative)", dl["one_cent_discounted_from_delivery"], dl["forward_delta_of_page_1_1"] * 0.01 * c["position_pounds"], 1e-9, "rel")
    if page_1_1 is not None:
        add("C5 which is page 1.1's 9,704 dollars, from that page's committed result (1e-6)", dl["one_cent_discounted_from_delivery"], page_1_1["forward_value_change_for_one_cent"], 1e-6)
    add("C2 1,030,000 pounds would need 16.48 contracts, which cannot be bought", c["contracts_for_an_amount_that_is_not_a_multiple"], 16.48, 1e-9)

    b = res["basis"]["rows"]
    add("C6 the basis a year from delivery is 1.1's 252.5 points", b[0]["basis_points"], 252.5, 0.05)
    truth("C6 it falls as delivery approaches", all(x["basis_points"] > y["basis_points"] for x, y in zip(b, b[1:])))
    add("C6 and is nothing at delivery", b[-1]["basis_points"], 0.0, 0.0)

    h = res["hedge"]
    add("C7 the net price paid is the futures price bought less the basis when the hedge is closed (1e-12)", h["max_abs_identity_error"], 0.0, 1e-12)
    add("C7 with rates and spot unchanged that basis is 41.7 points, and the net price 1.2711", h["unchanged_rates_and_spot"]["net_price_paid"], 1.2711, 5e-5)
    add("C7 across the grid spot moves by 2,000 points", h["unhedged_price_range_points"], 2000.0, 1e-6)
    truth("C7 and the net price paid by fewer than 50", h["net_price_range_points"] < 50.0)
    add("C7 one percent on the rate difference is 21 points of basis with two months left", h["basis_points_per_one_percent_of_rate_difference"], 21.0, 0.5)

    ro = res["roll"]
    add("C8 the next contract is 63.0 points above the near one", ro["spread_points"], 63.0, 0.05)
    add("C8 which is the points between the two delivery dates (1e-9)", ro["spread_points"], ro["points_between_the_two_dates"], 1e-9)

    qc = res["quoted_in_checks"]
    add("the page's checks: topping up only to the maintenance level would be 1,400 dollars", qc["call_if_topped_up_only_to_maintenance"], 1400.0, 1e-6)
    add("the page's checks: the third day's loss alone is 2,900 dollars", qc["call_if_it_were_the_day_s_loss"], 2900.0, 1e-6)
    add("the page's checks: the price is then 94 points below the trade price", qc["points_below_trade_price_on_the_third_day"], 94.0, 1e-6)
    add("the page's checks: 49,400 dollars has been paid in over the week", qc["loss_if_margin_paid_in_were_the_cost"], 49400.0, 1e-6)

    if oracle is None:
        if not params["quick"]:
            truth("C9 QuantLib is importable for the full run (I4)", False)
    else:
        add("C9 QuantLib's discount factors give the same futures price at every delivery date used (1e-12)", oracle["max_abs_error"], 0.0, 1e-12)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="snippet check: QuantLib optional, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "random": "none -- arithmetic only, so no seed (I6 has nothing to seed)",
        "fx": {"pair": "GBP/USD", "underlying": "one pound", "price_unit": "dollars per pound",
               "S": 1.25, "r": 0.05, "q": 0.03, "T": 1.0,
               "r_is": "the dollar rate, continuously compounded", "q_is": "the sterling rate, continuously compounded",
               "note": "page 1.1's levels: illustrative, not a market's"},
        "contract": {"size": 62_500.0, "size_is": "pounds a contract, as CME's British pound future", "contracts": 16, "awkward_amount": 1_030_000.0,
                     "initial_margin_per_contract": 2_500.0, "maintenance_margin_per_contract": 2_000.0,
                     "note": "the margin levels are illustrative, not an exchange's"},
        "walk": {"side": "long", "trade_price": 1.2753, "days_elapsed": 4,
                 "settlements": [{"day": "Monday", "price": 1.2731}, {"day": "Tuesday", "price": 1.2688},
                                 {"day": "Wednesday", "price": 1.2659}, {"day": "Thursday", "price": 1.2702},
                                 {"day": "Friday", "price": 1.2740}],
                 "note": "bought on Monday before the close; the settlement prices are illustrative"},
        "basis": {"months_to_delivery": [12, 9, 6, 3, 0]},
        "hedge": {"months_left_when_closed": 2, "spots_then": [1.15, 1.25, 1.35], "rate_differences_then": [0.01, 0.02, 0.03],
                  "note": "pounds needed in ten months, hedged with the contract delivering in twelve"},
        "roll": {"near_months": 3, "next_months": 6},
    }
    res = run(params)
    oracle = quantlib_oracle(params, res)
    if oracle is None:
        print(f"[{PAGE}] C9: QuantLib-Python not importable -- oracle comparison "
              + ("skipped (--quick)" if args.quick else "MISSING (the full run requires it, I4)"), flush=True)
    page_1_1 = page_1_1_results(Path(__file__).resolve().parent)
    res["oracle"] = oracle
    res["page_1_1"] = page_1_1
    checks = build_checks(res, params, oracle, page_1_1)

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
