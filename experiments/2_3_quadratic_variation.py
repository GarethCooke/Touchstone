"""Quadratic variation -- the experiment behind page 2.3.

Serves page 2.3 (docs/quant-learn-index-v1.md). One Brownian path W on
[0, T], chopped into n equal steps of length dt = T/n; dW is the change over
one step. The page's claim is the rulebook (dW)^2 = dt, dW.dt = 0, (dt)^2 = 0,
and that it fails for nothing smooth -- "the whole reason ordinary calculus
fails". Five claims, each measured:

  C1  Sum (dW)^2 -> T. Paths are simulated on the finest grid (n = 10^6) and
      coarsened by 10 at a time, so the SAME path is summed on five grids.
      Measured as: mean over paths within 5 s.e. of T at n = 10^2 .. 10^6;
      the spread across paths is T*sqrt(2/n) -- log-log slope of the sd
      against n is -0.5 -- so the limit holds path by path, not just on
      average (each single (dW)^2 has relative sd sqrt 2; the sum does not);
      every path is within 5 sd of T on every grid; and the sum does not know
      which path it is on: its correlation with W_T is 0 (an odd moment
      vanishes) and with max|W| is small (it is positive, of order 1/sqrt n,
      because bigger kicks make bigger excursions -- reported, bounded).
  C2  Sum |dW| -> infinity like sqrt n. E|dW| = sqrt(2 dt / pi), so
      Sum |dW| = sqrt(2/pi) * sqrt(nT) ~ 0.8, 8, 80 ... at n = 10^2, 10^4,
      10^6. Measured as: log-log slope +0.5; the constant sqrt(2/pi)
      recovered at every n.
  C3  The smooth contrast, f(t) = sin(2 pi t) on the same grids:
      Sum (df)^2 -> 0 like 1/n (it is 2 pi^2 / n: dt * integral of f'^2) while
      Sum |df| -> integral of |f'| = 4, finite. The opposite of W in both
      columns. Measured as: slope -1 and the constant 2 pi^2; Sum |df| = 4.
  C4  Everything beyond order dt vanishes. Sum dW.dt = dt * W_T, rms 1/n;
      Sum (dt)^2 = T dt = 1/n exactly; Sum |dW|^3 ~ 1/sqrt n. Measured as:
      log-log slopes -1, -1, -0.5. Hence dW.dt = 0 and (dt)^2 = 0.
  C5  The +-sqrt(dt) coin walk from 2.1 has Sum (dW)^2 = n dt = T EXACTLY,
      every n, every path, by construction (and Sum |dW| = sqrt(nT), constant
      1 rather than 0.798). The Gaussian walk converges to what the coin has
      for free; the spread in C1 is the whole difference between them.

Run from the repository root:

    uv run experiments/2_3_quadratic_variation.py [--seed 20260906]

Writes 2_3_quadratic_variation.json beside this file: parameters in, results
out, no timestamps -- same seed, same file (I6). No plotting here; the site
draws (see experiments/README.md; the counter is demo D2, which should check
itself against this file). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import pi, sqrt
from pathlib import Path

import numpy as np

SQRT_2_OVER_PI = sqrt(2.0 / pi)          # E|Z| for Z ~ N(0, 1)
E_ABS_Z_CUBED = 2.0 * sqrt(2.0 / pi)     # E|Z|^3


# --- variations of one path on one grid ------------------------------------


def variations(w: np.ndarray, dt: float) -> dict[str, np.ndarray]:
    """w has shape (paths, n + 1) on a grid of step dt. Returns, per path,
    every sum the page talks about."""
    d = np.diff(w, axis=1)
    a = np.abs(d)
    return {
        "sum_dW_sq": (d * d).sum(axis=1),          # Sum (dW)^2
        "sum_abs_dW": a.sum(axis=1),               # Sum |dW|
        "sum_dW_dt": d.sum(axis=1) * dt,           # Sum dW.dt  (= dt * W_T)
        "sum_abs_dW_cubed": (a**3).sum(axis=1),    # Sum |dW|^3
        "max_abs_W": np.abs(w).max(axis=1),
        "W_T": w[:, -1],
        "single_dW_sq_over_dt_sd": (d * d / dt).std(axis=1, ddof=1),  # sd of one term
    }


def coarsen(w: np.ndarray, factor: int) -> np.ndarray:
    """Keep every factor-th grid point: the same path on a grid factor times
    coarser. Coarse increments are sums of fine ones, so this is exactly a
    Brownian path on the coarse grid."""
    return w[:, ::factor]


# --- C1, C2, C4: the same paths on five grids --------------------------------


def nested_grids(rng, n_paths, n_fine, T, factors, chunk_paths):
    """Simulate paths on the finest grid in chunks; for each coarsening factor
    accumulate the per-path variations. Returns {n: {name: array(n_paths)}}
    (min/max, first paths, correlations are read off later)."""
    dt_fine = T / n_fine
    acc = {f: {} for f in factors}
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        w = np.empty((k, n_fine + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(k, n_fine)) * sqrt(dt_fine), axis=1, out=w[:, 1:])
        for f in factors:
            v = variations(coarsen(w, f), dt_fine * f)
            for name, arr in v.items():
                acc[f].setdefault(name, []).append(arr)
        done += k
        print(f"[2.3] nested grids: {done:,}/{n_paths:,} paths", flush=True)

    per_n = {}
    for f in factors:
        n = n_fine // f
        per_n[n] = {name: np.concatenate(parts) for name, parts in acc[f].items()}
    return per_n


def summarise_grid(n, T, v, keep_first):
    dt = T / n
    qv, av, cross, cubic = v["sum_dW_sq"], v["sum_abs_dW"], v["sum_dW_dt"], v["sum_abs_dW_cubed"]
    m = qv.size
    sd_expected = T * sqrt(2.0 / n)
    return {
        "n": n, "dt": dt, "n_paths": int(m),
        "sum_dW_sq": {
            "mean": float(qv.mean()),
            "sd": float(qv.std(ddof=1)),
            "sd_expected": sd_expected,
            "min": float(qv.min()), "max": float(qv.max()),
            "max_abs_deviation_from_T_in_sd": float(np.abs(qv - T).max() / sd_expected),
            "first_paths": [float(x) for x in qv[:keep_first]],
            "corr_with_W_T": float(np.corrcoef(qv, v["W_T"])[0, 1]),
            "corr_with_max_abs_W": float(np.corrcoef(qv, v["max_abs_W"])[0, 1]),
            "single_term_relative_sd_mean": float(v["single_dW_sq_over_dt_sd"].mean()),
            "single_term_relative_sd_expected": sqrt(2.0),
            "sum_relative_sd_expected": sqrt(2.0 / n),
        },
        "sum_abs_dW": {
            "mean": float(av.mean()),
            "expected": SQRT_2_OVER_PI * sqrt(n * T),
            "mean_over_sqrt_nT": float(av.mean() / sqrt(n * T)),
            "constant_expected": SQRT_2_OVER_PI,
            "first_paths": [float(x) for x in av[:keep_first]],
        },
        "sum_dW_dt": {
            "rms": float(sqrt((cross**2).mean())),
            "rms_expected": dt * sqrt(T),
            "first_paths": [float(x) for x in cross[:keep_first]],
        },
        "sum_dt_sq": {"value": n * dt * dt, "expected": T * dt},
        "sum_abs_dW_cubed": {
            "mean": float(cubic.mean()),
            "expected": E_ABS_Z_CUBED * T * sqrt(dt),
        },
    }


# --- C3: the smooth curve on the same grids ----------------------------------


def smooth_curve(n, T):
    t = np.linspace(0.0, T, n + 1)
    f = np.sin(2 * pi * t)
    d = np.diff(f)
    return {
        "n": n,
        "sum_df_sq": float((d * d).sum()),
        "sum_df_sq_times_n": float((d * d).sum() * n),
        "sum_df_sq_times_n_expected": 2 * pi**2,   # dt * integral_0^1 f'(t)^2 dt, f' = 2 pi cos
        "sum_abs_df": float(np.abs(d).sum()),
        "sum_abs_df_expected": 4.0,                # integral_0^1 |f'| = total rise and fall
        "max_abs_df": float(np.abs(d).max()),
    }


# --- C5: the coin walk, built on each grid directly --------------------------


def coin_walk(rng, n, T, n_paths):
    dt = T / n
    steps = (rng.integers(0, 2, size=(n_paths, n), dtype=np.int8) * 2 - 1).astype(np.float64)
    d = steps * sqrt(dt)
    qv = (d * d).sum(axis=1)
    av = np.abs(d).sum(axis=1)
    return {
        "n": n, "n_paths": n_paths,
        "sum_dW_sq_max_abs_deviation_from_T": float(np.abs(qv - T).max()),
        "sum_dW_sq_values": [float(x) for x in qv],
        "sum_abs_dW_over_sqrt_nT": [float(x / sqrt(n * T)) for x in av],
        "sum_abs_dW_constant_expected": 1.0,
    }


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


# --- checks ------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []
    T = params["T"]

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": tol, "mode": mode, "pass": bool(ok)})

    grids = res["grids"]
    for g in grids:
        n, q, m = g["n"], g["sum_dW_sq"], g["n_paths"]
        add(f"C1 n={n:.0e}: mean Sum (dW)^2 within 5 s.e. of T",
            q["mean"], T, 5 * q["sd_expected"] / sqrt(m))
        add(f"C1 n={n:.0e}: sd of Sum (dW)^2 across paths is T*sqrt(2/n)",
            q["sd"], q["sd_expected"], 0.15, "rel")
        add(f"C1 n={n:.0e}: every path within 5 sd of T",
            q["max_abs_deviation_from_T_in_sd"], 0.0, 5.0)
        add(f"C1 n={n:.0e}: a single (dW)^2/dt has relative sd sqrt 2 (the terms are wild)",
            q["single_term_relative_sd_mean"], sqrt(2.0), 0.02, "rel")
        a = g["sum_abs_dW"]
        add(f"C2 n={n:.0e}: Sum |dW| / sqrt(nT) is sqrt(2/pi)",
            a["mean_over_sqrt_nT"], SQRT_2_OVER_PI, 0.015, "rel")
        add(f"C4 n={n:.0e}: Sum (dt)^2 = T dt", g["sum_dt_sq"]["value"], T * g["dt"], 1e-9, "rel")

    add("C1: log-log slope of sd(Sum (dW)^2) vs n is -0.5",
        res["slopes"]["sd_sum_dW_sq"], -0.5, 0.03)
    add("C2: log-log slope of Sum |dW| vs n is +0.5",
        res["slopes"]["sum_abs_dW"], 0.5, 0.01)
    add("C4: log-log slope of rms Sum dW.dt vs n is -1",
        res["slopes"]["rms_sum_dW_dt"], -1.0, 0.03)
    add("C4: log-log slope of Sum (dt)^2 vs n is -1",
        res["slopes"]["sum_dt_sq"], -1.0, 1e-9)
    add("C4: log-log slope of Sum |dW|^3 vs n is -0.5",
        res["slopes"]["sum_abs_dW_cubed"], -0.5, 0.03)

    ind = res["independence"]
    add(f"C1 independence (n={ind['n']:.0e}, {ind['n_paths']:,} paths): "
        "corr(Sum (dW)^2, W_T) is 0", ind["corr_with_W_T"], 0.0, 0.03)
    add(f"C1 independence (n={ind['n']:.0e}): corr(Sum (dW)^2, max|W|) is small",
        ind["corr_with_max_abs_W"], 0.0, 0.05)
    add(f"C1 independence (n={ind['n']:.0e}): sd of Sum (dW)^2 is T*sqrt(2/n)",
        ind["sd"], ind["sd_expected"], 0.03, "rel")

    for s in res["smooth"]:
        n = s["n"]
        add(f"C3 n={n:.0e}: n * Sum (df)^2 is 2 pi^2 (so Sum (df)^2 -> 0 like 1/n)",
            s["sum_df_sq_times_n"], 2 * pi**2, 0.01, "rel")
        add(f"C3 n={n:.0e}: Sum |df| is 4", s["sum_abs_df"], 4.0, 1e-3, "rel")
    add("C3: log-log slope of Sum (df)^2 vs n is -1", res["slopes"]["smooth_sum_df_sq"], -1.0, 1e-3)

    for c in res["coin"]:
        add(f"C5 coin n={c['n']:.0e}: Sum (dW)^2 = T exactly, every path",
            c["sum_dW_sq_max_abs_deviation_from_T"], 0.0, 1e-9)
        add(f"C5 coin n={c['n']:.0e}: Sum |dW| / sqrt(nT) = 1, every path",
            max(c["sum_abs_dW_over_sqrt_nT"]), 1.0, 1e-9, "rel")
    return checks


# --- main --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()

    params = {
        "seed": args.seed,
        "T": 1.0,
        "nested_grids": {
            "n_fine": 1_000_000,
            "coarsen_by": [10_000, 1_000, 100, 10, 1],   # n = 10^2, 10^3, 10^4, 10^5, 10^6
            "n_paths": 400,
            "chunk_paths": 5,      # memory only: draws are consumed row by row, so the paths do not depend on it
            "keep_first_paths": 5,
        },
        "independence": {"n": 10_000, "n_paths": 20_000, "chunk_paths": 2_000},
        "smooth": {"f": "sin(2*pi*t)", "ns": [100, 1_000, 10_000, 100_000, 1_000_000]},
        "coin": {"ns": [100, 1_000, 10_000, 100_000, 1_000_000], "n_paths": 5},
    }
    T = params["T"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    g = params["nested_grids"]
    per_n = nested_grids(rng, g["n_paths"], g["n_fine"], T, g["coarsen_by"],
                         g["chunk_paths"])
    grids = [summarise_grid(n, T, per_n[n], g["keep_first_paths"]) for n in sorted(per_n)]
    ns = [x["n"] for x in grids]

    i = params["independence"]
    print(f"[2.3] independence: {i['n_paths']:,} paths at n={i['n']:,}", flush=True)
    dt = T / i["n"]
    qv, wt, mx = [], [], []
    for _ in range(i["n_paths"] // i["chunk_paths"]):
        w = np.empty((i["chunk_paths"], i["n"] + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(i["chunk_paths"], i["n"])) * sqrt(dt), axis=1, out=w[:, 1:])
        v = variations(w, dt)
        qv.append(v["sum_dW_sq"]); wt.append(v["W_T"]); mx.append(v["max_abs_W"])
    qv, wt, mx = map(np.concatenate, (qv, wt, mx))
    independence = {
        "n": i["n"], "n_paths": int(qv.size),
        "mean": float(qv.mean()), "sd": float(qv.std(ddof=1)), "sd_expected": T * sqrt(2.0 / i["n"]),
        "corr_with_W_T": float(np.corrcoef(qv, wt)[0, 1]),
        "corr_with_max_abs_W": float(np.corrcoef(qv, mx)[0, 1]),
        "mean_sum_dW_sq_given_W_T_above_1": float(qv[wt > 1].mean()),
        "mean_sum_dW_sq_given_W_T_below_minus_1": float(qv[wt < -1].mean()),
        "mean_sum_dW_sq_given_abs_W_T_below_0_5": float(qv[np.abs(wt) < 0.5].mean()),
    }

    print("[2.3] smooth curve and coin walk", flush=True)
    smooth = [smooth_curve(n, T) for n in params["smooth"]["ns"]]
    coin = [coin_walk(rng, n, T, params["coin"]["n_paths"]) for n in params["coin"]["ns"]]

    slopes = {
        "sd_sum_dW_sq": loglog_slope(ns, [x["sum_dW_sq"]["sd"] for x in grids]),
        "sum_abs_dW": loglog_slope(ns, [x["sum_abs_dW"]["mean"] for x in grids]),
        "rms_sum_dW_dt": loglog_slope(ns, [x["sum_dW_dt"]["rms"] for x in grids]),
        "sum_dt_sq": loglog_slope(ns, [x["sum_dt_sq"]["value"] for x in grids]),
        "sum_abs_dW_cubed": loglog_slope(ns, [x["sum_abs_dW_cubed"]["mean"] for x in grids]),
        "smooth_sum_df_sq": loglog_slope([s["n"] for s in smooth], [s["sum_df_sq"] for s in smooth]),
    }

    results = {
        "grids": grids,
        "independence": independence,
        "smooth": smooth,
        "coin": coin,
        "slopes": slopes,
        "constants": {"sqrt_2_over_pi": SQRT_2_OVER_PI, "two_pi_sq": 2 * pi**2,
                      "E_abs_Z_cubed": E_ABS_Z_CUBED},
    }
    checks = build_checks(results, params)

    out = {
        "page": "2.3",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": results,
        "checks": checks,
    }
    out_path = Path(__file__).with_suffix(".json")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  "
              f"({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.3] wrote {out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
