"""The explicit scheme -- the experiment behind page 3.3.

Serves page 3.3 (docs/quant-learn-index-v1.md): finite differences, and in
particular "explicit, implicit, Crank-Nicolson; stability". The library steps
its grid implicitly and by Crank-Nicolson and has no explicit scheme, so that
page's numbers for the implicit and Crank-Nicolson steps are the library's
own. This file holds the ones the library cannot produce:

  - what the explicit scheme returns on either side of its stability limit;
  - how many steps it needs on the library's own grid;
  - what an explicit step returns when it overwrites the array it is reading,
    which is the bug the page's check shows.

The option is Part 2's -- a share at 100, strike 100, one year, r = 0.05,
sigma = 0.4, no dividend -- and the equation is page 2.7's, written in the
log of the share price, x = ln S, and the time to expiry, tau = T - t, where
its coefficients are constants:

    du/dtau = (sigma^2 / 2) d2u/dx2 + (r - sigma^2 / 2) du/dx - r u.

With central differences on a uniform grid of step dx the right-hand side at
node i is a u[i-1] + b u[i] + c u[i+1], and one time step of size dtau is

    (I - theta dtau L) u_new = (I + (1 - theta) dtau L) u_old,

with theta = 0 the explicit scheme, theta = 1 the fully implicit one and
theta = 1/2 Crank-Nicolson. theta here is the scheme's weight, as the
library's code names it, and not the Greek of page 2.10.

The grid is sized as the library sizes its own: wide enough to hold the spot,
the strike and the forward with six total volatilities beyond the furthest,
and then anchored so that the spot is a node. The payoff is sampled at the
nodes. The two ends hold the option's value far out of and far in the money.

  C1  The grid. At 1,024 intervals asked for, the step is the library's own
      0.004716796875 and the spot is a node.
  C2  The stability limit. An explicit step multiplies the fastest-varying
      error the grid can hold by 1 - r dtau - 2 sigma^2 dtau / dx^2. Call
      sigma^2 dtau / dx^2 the mesh ratio. Above a mesh ratio of 1 that factor
      is below -1 and the error grows at every step; below it the scheme is
      stable. On a 128-interval grid the limit falls between 112 and 113
      steps a year, and the measured prices say so.
  C3  Past the limit there is no answer. At half the steps the limit allows
      the largest value on the grid is above 1e20, and at the library's own
      512 steps on the library's own grid the values overflow a double before
      the run ends.
  C4  The cost. The steps the limit demands grow as 1 / dx^2, so halving dx
      doubles the nodes and quadruples the steps. On the library's grid the
      explicit scheme needs 7,192 steps where the library takes 512.
  C5  When it is stable it is right. At twice the steps the limit demands,
      which holds the mesh ratio at one half, the explicit error falls by
      four each time dx is halved: second order, as the other two schemes
      are in dx.
  C6  The three schemes agree. On one grid, with steps enough for all three,
      explicit, implicit and Crank-Nicolson land within 0.03 of the closed
      form and of each other.
  C7  The bug in the page's check. An explicit step that writes each new value
      into the array it is still reading uses the new value of the node below
      and the old value of the node above. It does not blow up, which is what
      makes it hard to see: it returns a price, and the price is wrong by far
      more than the right loop's on the same grid, at every step count tried.

Run from the repository root:

    uv run experiments/3_3_explicit_scheme.py [--quick]

Nothing here is random, so there is no seed. --quick is for the learn site's
build-time snippet check (I3): it leaves out the two runs on the library's
1,024-interval grid, asserts every other claim, and writes NO JSON -- the
committed result is the full run.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from math import ceil, exp, log, sqrt
from pathlib import Path

import numpy as np

PAGE = "3.3"

# Page 2.9's formula is restated once, in page 1.4's script, and imported from
# there. importlib, because a module whose name starts with a digit cannot be
# named in an import statement.
sys.path.insert(0, str(Path(__file__).resolve().parent))
black_scholes = importlib.import_module("1_4_options").black_scholes

HALF_WIDTH_IN_TOTAL_VOLS = 6.0
# The library's log-spot step for this option at its default 1,024 intervals,
# as its browser build reports it (logSpotStep). C1 holds this file's grid to it.
LIBRARY_STEP_AT_1024 = 0.004716796875


# --- the grid ----------------------------------------------------------------------


def make_grid(m: dict, intervals: int) -> dict:
    """A uniform grid in x = ln S with the spot on a node, sized as the library's is."""
    x0, xk = log(m["S"]), log(m["K"])
    forward = x0 + (m["r"] - 0.5 * m["sigma"] ** 2) * m["T"]
    margin = HALF_WIDTH_IN_TOTAL_VOLS * m["sigma"] * sqrt(m["T"])
    lower, upper = min(x0, xk, forward) - margin, max(x0, xk, forward) + margin
    dx = (upper - lower) / intervals
    below, above = ceil((x0 - lower) / dx), ceil((upper - x0) / dx)
    x = x0 + (np.arange(below + above + 1) - below) * dx
    return {"x": x, "dx": dx, "spot_index": below, "intervals": below + above}


def operator(m: dict, dx: float) -> tuple[float, float, float]:
    """a, b, c: the weights of u[i-1], u[i] and u[i+1] in the right-hand side at node i."""
    diffusion = 0.5 * m["sigma"] ** 2 / dx**2
    convection = (m["r"] - 0.5 * m["sigma"] ** 2) / (2.0 * dx)
    return diffusion - convection, -2.0 * diffusion - m["r"], diffusion + convection


def call_far_in_the_money(x_top: float, tau: float, m: dict) -> float:
    """The call's value at the top of the grid: the share less the discounted strike."""
    return exp(x_top) - m["K"] * exp(-m["r"] * tau)


def mesh_ratio(m: dict, dx: float, steps: int) -> float:
    """sigma^2 dtau / dx^2: the number the explicit scheme's stability turns on."""
    return m["sigma"] ** 2 * (m["T"] / steps) / dx**2


def limit_steps(m: dict, dx: float) -> int:
    """The fewest steps a year at which the explicit scheme is stable on this grid: the
    fastest-varying error is multiplied by 1 - r dtau - 2 sigma^2 dtau / dx^2 at each step, and that must
    not be below -1, so dtau (sigma^2 / dx^2 + r / 2) <= 1."""
    return ceil(m["T"] * (m["sigma"] ** 2 / dx**2 + 0.5 * m["r"]))


# --- the three schemes ---------------------------------------------------------------


def explicit(m: dict, intervals: int, steps: int, in_place: bool = False) -> dict:
    """The call by the explicit scheme. With in_place the step overwrites the array it is
    reading, node by node from the bottom: the bug of the page's check."""
    g = make_grid(m, intervals)
    x, dx = g["x"], g["dx"]
    a, b, c = operator(m, dx)
    dtau = m["T"] / steps
    u = np.maximum(np.exp(x) - m["K"], 0.0)
    largest, overflowed_at = float(np.abs(u).max()), None
    with np.errstate(over="ignore", invalid="ignore"):
        for step in range(1, steps + 1):
            if in_place:
                for i in range(1, u.size - 1):
                    u[i] = u[i] + dtau * (a * u[i - 1] + b * u[i] + c * u[i + 1])
            else:
                u[1:-1] = u[1:-1] + dtau * (a * u[:-2] + b * u[1:-1] + c * u[2:])
            u[0], u[-1] = 0.0, call_far_in_the_money(x[-1], step * dtau, m)
            if not np.all(np.isfinite(u)):
                overflowed_at = step
                break
            largest = max(largest, float(np.abs(u).max()))
    price = float(u[g["spot_index"]]) if overflowed_at is None else None
    return {"intervals": int(g["intervals"]), "steps": steps, "dx": dx, "mesh_ratio": mesh_ratio(m, dx, steps),
            "price": price, "largest_value_on_the_grid": largest if overflowed_at is None else None,
            "overflowed_a_double_at_step": overflowed_at}


def theta_scheme(m: dict, intervals: int, steps: int, theta: float) -> dict:
    """The call by the implicit scheme (theta = 1) or Crank-Nicolson (theta = 1/2). The
    matrix is the same at every step, so it is inverted once; the grids here are small."""
    g = make_grid(m, intervals)
    x, dx = g["x"], g["dx"]
    a, b, c = operator(m, dx)
    dtau = m["T"] / steps
    inner = x.size - 2
    L = (np.diag(np.full(inner, b)) + np.diag(np.full(inner - 1, a), -1) + np.diag(np.full(inner - 1, c), 1))
    solve = np.linalg.inv(np.eye(inner) - theta * dtau * L)
    carry = np.eye(inner) + (1.0 - theta) * dtau * L
    u = np.maximum(np.exp(x) - m["K"], 0.0)
    for step in range(1, steps + 1):
        top_old, top_new = u[-1], call_far_in_the_money(x[-1], step * dtau, m)
        rhs = carry @ u[1:-1]
        rhs[-1] += dtau * c * ((1.0 - theta) * top_old + theta * top_new)
        u[1:-1] = solve @ rhs
        u[0], u[-1] = 0.0, top_new
    return {"intervals": int(g["intervals"]), "steps": steps, "dx": dx, "theta": theta,
            "price": float(u[g["spot_index"]])}


# --- the experiment ------------------------------------------------------------------


def run(params: dict) -> dict:
    m = params["market"]
    closed = black_scholes(m["S"], m["K"], m["r"], m["sigma"], m["T"])["call"]

    def with_error(row: dict) -> dict:
        row["error"] = None if row["price"] is None else row["price"] - closed
        return row

    # C2, C3: one grid, the steps on either side of its limit.
    coarse = params["stability_grid"]
    coarse_grid = make_grid(m, coarse)
    limit = limit_steps(m, coarse_grid["dx"])
    stability = {
        "intervals_asked_for": coarse, "dx": coarse_grid["dx"],
        "fewest_stable_steps": limit,
        "rows": [with_error(explicit(m, coarse, steps)) for steps in params["stability_steps"]],
    }

    # C4, C5: the limit on finer and finer grids, and the explicit price at twice the
    # steps the limit demands, which holds the mesh ratio at one half.
    refinement = []
    for intervals in params["refinement_grids"]:
        g = make_grid(m, intervals)
        fewest = limit_steps(m, g["dx"])
        row = with_error(explicit(m, intervals, 2 * fewest))
        row["intervals_asked_for"] = intervals
        row["nodes"] = int(g["x"].size)
        row["fewest_stable_steps"] = fewest
        refinement.append(row)

    # C6: the three schemes on one grid.
    three = params["three_schemes"]
    schemes = {
        "explicit": with_error(explicit(m, three["intervals"], three["steps"])),
        "implicit": with_error(theta_scheme(m, three["intervals"], three["steps"], 1.0)),
        "crank_nicolson": with_error(theta_scheme(m, three["intervals"], three["steps"], 0.5)),
    }

    # C7: the step that overwrites what it is reading.
    bug = params["in_place"]
    in_place = [{"right": with_error(explicit(m, bug["intervals"], steps)),
                 "in_place": with_error(explicit(m, bug["intervals"], steps, in_place=True))}
                for steps in bug["steps"]]

    res = {"closed_form": {"call": closed}, "stability": stability, "refinement": refinement,
           "three_schemes": schemes, "in_place": in_place}

    # C1, C3, C4 on the library's own grid: left out of --quick.
    if not params["quick"]:
        fine = make_grid(m, 1024)
        fine_limit = limit_steps(m, fine["dx"])
        res["library_grid"] = {
            "intervals_asked_for": 1024, "intervals": int(fine["intervals"]), "nodes": int(fine["x"].size),
            "dx": fine["dx"], "spot_node_log_spot": float(fine["x"][fine["spot_index"]]),
            "library_steps": 512, "mesh_ratio_at_the_library_steps": mesh_ratio(m, fine["dx"], 512),
            "fewest_stable_steps": fine_limit,
            "explicit_at_the_library_steps": with_error(explicit(m, 1024, 512)),
            "explicit_at_the_fewest_stable_steps": with_error(explicit(m, 1024, fine_limit)),
        }

    first_bad = next(r for r in reversed(stability["rows"]) if r["steps"] < limit)
    half = next(r for r in stability["rows"] if r["steps"] == limit // 2)
    at_half_the_dx = refinement[params["refinement_grids"].index(2 * coarse)]["fewest_stable_steps"]
    res["quoted_in_checks"] = {
        "fewest_stable_steps_on_the_coarse_grid": limit,
        "fewest_stable_steps_at_half_the_dx": at_half_the_dx,
        "steps_ratio_when_dx_halves": at_half_the_dx / limit,
        "twice_the_steps_on_the_coarse_grid": 2 * limit,
        "price_one_step_short_of_the_limit": first_bad["price"],
        "half_the_limit_steps": half["steps"],
        "price_at_half_the_limit": half["price"],
        "largest_value_at_half_the_limit": half["largest_value_on_the_grid"],
        "in_place_steps": in_place[0]["in_place"]["steps"],
        "in_place_price": in_place[0]["in_place"]["price"],
        "in_place_error": in_place[0]["in_place"]["error"],
        "right_price_on_the_same_grid": in_place[0]["right"]["price"],
        "right_error_on_the_same_grid": in_place[0]["right"]["error"],
    }
    return res


# --- checks --------------------------------------------------------------------------


def build_checks(res: dict, params: dict) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        error = abs(measured - expected) / (abs(expected) if mode == "rel" else 1.0)
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(error <= tol)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0,
                       "mode": "abs", "pass": bool(ok)})

    m = params["market"]
    closed = res["closed_form"]["call"]
    add("the closed form is page 2.9's 18.0230", closed, 18.0230, 5e-5)

    stability, limit = res["stability"], res["stability"]["fewest_stable_steps"]
    rows = {row["steps"]: row for row in stability["rows"]}
    add("C2 on the 128-interval grid the limit is 113 steps a year", limit, 113, 0)
    truth("C2 the row one step short of the limit has a mesh ratio above 1, and the row at it below 1",
          rows[limit - 1]["mesh_ratio"] > 1.0 > rows[limit]["mesh_ratio"])
    stable = [row for row in stability["rows"] if row["steps"] >= limit]
    unstable = [row for row in stability["rows"] if row["steps"] < limit]
    truth("C2 at the limit and above it, every price is within 0.02 of the closed form",
          all(abs(row["error"]) < 0.02 for row in stable))
    truth("C2 at the limit and above it, nothing on the grid exceeds the value at its top node",
          all(row["largest_value_on_the_grid"] < exp(make_grid(m, params["stability_grid"])["x"][-1]) for row in stable))
    truth("C2 below the limit the error grows as the steps fall",
          all(abs(lo["error"]) > abs(hi["error"]) for lo, hi in zip(unstable, unstable[1:])))
    truth("C2 one step short of the limit the price is already further out than any stable row's",
          abs(rows[limit - 1]["error"]) > max(abs(row["error"]) for row in stable))
    half = rows[limit // 2]
    truth("C3 at half the steps the limit allows, the largest value on the grid is above 1e20",
          half["largest_value_on_the_grid"] > 1e20)
    truth("C3 and the price there is not within a million of the closed form", abs(half["error"]) > 1e6)

    refinement = res["refinement"]
    for coarse, fine in zip(refinement, refinement[1:]):
        add(f"C4 from {coarse['intervals_asked_for']} to {fine['intervals_asked_for']} intervals the steps needed "
            "quadruple", fine["fewest_stable_steps"] / coarse["fewest_stable_steps"], 4.0, 0.03, "rel")
        add(f"C5 and at twice those steps the explicit error falls by four, from {coarse['intervals_asked_for']} to "
            f"{fine['intervals_asked_for']} intervals", coarse["error"] / fine["error"], 4.0, 0.05, "rel")
    truth("C5 at twice the steps the limit demands, the mesh ratio is one half to within 0.02 on every grid",
          all(abs(row["mesh_ratio"] - 0.5) < 0.02 for row in refinement))

    schemes = res["three_schemes"]
    worst = max(abs(s["error"]) for s in schemes.values())
    truth("C6 on one grid the three schemes are each within 0.03 of the closed form", worst < 0.03)
    truth("C6 and within 0.03 of each other",
          max(s["price"] for s in schemes.values()) - min(s["price"] for s in schemes.values()) < 0.03)

    for pair in res["in_place"]:
        truth(f"C7 at {pair['right']['steps']} steps the in-place step does not blow up",
              pair["in_place"]["price"] is not None and pair["in_place"]["largest_value_on_the_grid"] < 1e4)
        truth(f"C7 at {pair['right']['steps']} steps the in-place price is more than five times as far from the "
              "closed form as the right loop's", abs(pair["in_place"]["error"]) > 5.0 * abs(pair["right"]["error"]))
    first = res["in_place"][0]
    truth("C7 at the fewest steps tried the in-place price is more than 2 too high",
          first["in_place"]["error"] > 2.0)
    q = res["quoted_in_checks"]
    add("C7 the quoted figures are the first pair's", q["in_place_price"], first["in_place"]["price"], 0)

    if "library_grid" in res:
        lib = res["library_grid"]
        add("C1 at 1,024 intervals asked for, the step is the library's 0.004716796875",
            lib["dx"], LIBRARY_STEP_AT_1024, 1e-15)
        add("C1 and the grid has the library's 1,026 nodes", lib["nodes"], 1026, 0)
        add("C1 the spot is a node", lib["spot_node_log_spot"], log(m["S"]), 1e-12)
        add("C4 on the library's grid the explicit scheme needs 7,192 steps", lib["fewest_stable_steps"], 7192, 0)
        truth("C3 at the library's 512 steps, the mesh ratio is 14 and the values overflow a double before the run ends",
              13.5 < lib["mesh_ratio_at_the_library_steps"] < 14.5
              and lib["explicit_at_the_library_steps"]["overflowed_a_double_at_step"] is not None)
        truth("C5 at 7,192 steps the explicit price is within 0.001 of the closed form",
              abs(lib["explicit_at_the_fewest_stable_steps"]["error"]) < 1e-3)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true",
                        help="snippet check: without the runs on the library's 1,024-interval grid, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "market": {"S": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.4, "T": 1.0, "q": 0.0,
                   "note": "Part 2's option (page 2.9): a share at 100 paying no dividend, strike 100, one year"},
        "half_width_in_total_vols": HALF_WIDTH_IN_TOTAL_VOLS,
        "stability_grid": 128,
        "stability_steps": [56, 96, 104, 108, 112, 113, 128, 256],
        "refinement_grids": [64, 128, 256, 512],
        "three_schemes": {"intervals": 128, "steps": 256},
        "in_place": {"intervals": 128, "steps": [256, 1024, 4096]},
    }
    res = run(params)
    checks = build_checks(res, params)

    out = {"page": PAGE, "script": Path(__file__).name, "params": params,
           "environment": {"numpy": np.__version__}, "results": res, "checks": checks}
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
