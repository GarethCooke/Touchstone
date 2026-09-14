"""The Ito integral -- the experiment behind page 2.4.

Serves page 2.4 (docs/quant-learn-index-v1.md). One Brownian path W on
[0, T], chopped into n equal steps of length dt = T/n, grid times t_i = i dt,
increments dW_i = W(t_{i+1}) - W(t_i). The object is the Riemann sum for
the integral of W with respect to W,

    Sum W(t_i*) dW_i,

with the integrand read at the LEFT endpoint t_i* = t_i (the Ito sum), at
the MIDPOINT (t_i + t_{i+1})/2 (the Stratonovich sum), or at the RIGHT
endpoint t_{i+1}. For a smooth curve the choice does not matter; for W it
does, and the difference is exactly page 2.3's number. Four claims, each
measured:

  C1  The three sums converge path by path to three DIFFERENT limits:
      left  -> 1/2 W_T^2 - 1/2 T      (the Ito integral),
      mid   -> 1/2 W_T^2              (Stratonovich: what the chain rule says),
      right -> 1/2 W_T^2 + 1/2 T.
      The mechanism is algebra, not a limit: on EVERY grid, for EVERY path,
        left  = 1/2 W_T^2 - 1/2 Sum (dW)^2          (from 2 W dW = (W+dW)^2 - W^2 - (dW)^2),
        right = 1/2 W_T^2 + 1/2 Sum (dW)^2,
        mid   = left + Sum d1^2 + Sum d1 d2          (d1, d2 the two half-step increments),
      so the left sum's error from its limit is -1/2 (Sum (dW)^2 - T) -- page
      2.3's quadratic-variation error halved -- with sd T/sqrt(2n), and the
      mid sum's error is 1/2 (Sum d1^2 - Sum d2^2), sd T/(2 sqrt n).
      Paths are drawn once on a grid of 2 x 10^6 steps and coarsened, so the
      same path is summed on five grids n = 10^2 .. 10^6 and every grid's
      midpoints are real path values, never interpolated. Measured as: the
      three identities hold to 1e-9 on every grid and path; mean error over
      paths within 5 s.e. of 0; sd of the error matches T/sqrt(2n) (left,
      right) and T/(2 sqrt n) (mid); log-log slopes -0.5; the gaps
      right - left = Sum (dW)^2 (mean T) and mid - left (mean T/2).
  C2  The Ito sum is a martingale with zero mean and the Ito isometry holds:
      E[left] = 0; E[left^2] = integral_0^T E[W_t^2] dt = T^2/2 (exactly
      T^2 (1 - 1/n)/2 on the grid); the running sum I(t) has mean 0 and
      variance t^2/2 at t = T/4, T/2, 3T/4, T; the second half of the sum is
      uncorrelated with the first (no forecastable drift). The anticipating
      sums are not martingales: E[mid] = T/2, E[right] = T, and the running
      right sum R(t) has mean t -- peeking at the next increment earns drift.
      Measured on a separate 20,000-path run at n = 10^4, means within 5 s.e.
  C3  The smooth contrast, x(t) = t^2 on the same five grids: the same
      identities hold, but Sum (dx)^2 = (4/3)/n -> 0, so all three sums
      agree with each other and with 1/2 x_T^2 = 1/2 -- the chain rule
      d(x^2) = 2x dx. Measured as: n (right - left) -> 4/3, slope -1; every
      sum within Sum (dx)^2 of 1/2.
  C4  The +-sqrt(dt) coin walk from 2.1 has Sum (dW)^2 = T exactly, so its
      left sum is 1/2 W_T^2 - 1/2 T EXACTLY and its right sum
      1/2 W_T^2 + 1/2 T EXACTLY, every n, every path. Ito's correction is
      not a Gaussian artefact; it is the price of sqrt(dt)-sized steps.

Run from the repository root:

    uv run experiments/2_4_ito_integral.py [--seed 20260908] [--quick]

--quick runs a tenth of the paths (about 5 s instead of 36) for the learn
site's build-time snippet check (I3): the statistical tolerances widen by
sqrt(400 / n_paths) so the same claims are still asserted, and NO JSON is
written -- the committed result is always the full run.

Writes 2_4_ito_integral.json beside this file: parameters in, results out,
no timestamps -- same seed, same file (I6). No plotting here; the site draws
(see experiments/README.md; the left-vs-midpoint demo is D3, which should
check itself against this file). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import sqrt
from pathlib import Path

import numpy as np


# --- the three sums for one path on one grid ---------------------------------


def riemann_sums(w_grid: np.ndarray, w_mid: np.ndarray) -> dict[str, np.ndarray]:
    """w_grid has shape (paths, n + 1): the path at the grid times.
    w_mid has shape (paths, n): the path at the midpoints of the n steps.
    Returns, per path, the left / mid / right sums and the pieces the
    identities are built from."""
    d = np.diff(w_grid, axis=1)                    # dW_i, shape (paths, n)
    left = (w_grid[:, :-1] * d).sum(axis=1)        # Sum W(t_i) dW_i
    mid = (w_mid * d).sum(axis=1)                  # Sum W(m_i) dW_i
    right = (w_grid[:, 1:] * d).sum(axis=1)        # Sum W(t_{i+1}) dW_i
    d1 = w_mid - w_grid[:, :-1]                    # first half-step increment
    d2 = w_grid[:, 1:] - w_mid                     # second half-step increment
    return {
        "left": left, "mid": mid, "right": right,
        "W_T": w_grid[:, -1].copy(),               # copy: a view would keep the whole chunk alive
        "sum_dW_sq": (d * d).sum(axis=1),          # Sum (dW)^2 -- page 2.3's number
        "sum_d1_sq": (d1 * d1).sum(axis=1),
        "sum_d2_sq": (d2 * d2).sum(axis=1),
        "sum_d1_d2": (d1 * d2).sum(axis=1),
    }


def grid_and_midpoints(w: np.ndarray, factor: int) -> tuple[np.ndarray, np.ndarray]:
    """w has shape (paths, n_fine + 1) with n_fine a multiple of factor, and
    factor even. Returns the same path on a grid factor times coarser, plus
    the path at the midpoints of the coarse steps (which are fine grid points
    because factor is even). Coarse increments are sums of fine ones, so the
    coarse path is exactly Brownian."""
    return w[:, ::factor], w[:, factor // 2::factor]


def identity_residuals(v: dict[str, np.ndarray], T: float) -> dict[str, np.ndarray]:
    """The exact algebra, per path: how far each sum is from its identity
    (rounding only) and from its LIMIT (the quadratic-variation error)."""
    half_WT2 = 0.5 * v["W_T"] ** 2
    return {
        # identities -- should be rounding error on every grid
        "left_identity": v["left"] - (half_WT2 - 0.5 * v["sum_dW_sq"]),
        "right_identity": v["right"] - (half_WT2 + 0.5 * v["sum_dW_sq"]),
        "mid_identity": v["mid"] - (v["left"] + v["sum_d1_sq"] + v["sum_d1_d2"]),
        # the same thing rearranged with Sum (dW)^2 = Sum d1^2 + 2 Sum d1 d2 + Sum d2^2:
        # the midpoint sum misses 1/2 W_T^2 by half the difference between the
        # quadratic variations of the first and second half-steps
        "mid_halves_identity": v["mid"] - (half_WT2 + 0.5 * (v["sum_d1_sq"] - v["sum_d2_sq"])),
        # errors from the limits -- these shrink like 1/sqrt n
        "left_error": v["left"] - (half_WT2 - 0.5 * T),
        "mid_error": v["mid"] - half_WT2,
        "right_error": v["right"] - (half_WT2 + 0.5 * T),
    }


# --- C1: the same paths on five grids ----------------------------------------


def nested_grids(rng, n_paths, n_fine, T, factors, chunk_paths):
    """Simulate paths on the finest grid in chunks; for each coarsening factor
    accumulate the per-path sums. Draws are consumed row by row, so the paths
    do not depend on chunk_paths. Returns {n: {name: array(n_paths)}}."""
    dt_fine = T / n_fine
    acc = {f: {} for f in factors}
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        w = np.empty((k, n_fine + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(k, n_fine)) * sqrt(dt_fine), axis=1, out=w[:, 1:])
        for f in factors:
            v = riemann_sums(*grid_and_midpoints(w, f))
            v.update(identity_residuals(v, T))
            for name, arr in v.items():
                acc[f].setdefault(name, []).append(arr)
        done += k
        print(f"[2.4] nested grids: {done:,}/{n_paths:,} paths", flush=True)
    per_n = {}
    for f in factors:
        per_n[n_fine // f] = {name: np.concatenate(parts) for name, parts in acc[f].items()}
    return per_n


def summarise_grid(n, T, v, keep_first):
    dt = T / n
    m = v["left"].size

    def stats(x):
        return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)),
                "se_of_mean": float(x.std(ddof=1) / sqrt(m)),
                "min": float(x.min()), "max": float(x.max())}

    first = lambda name: [float(x) for x in v[name][:keep_first]]  # noqa: E731
    return {
        "n": n, "dt": dt, "n_paths": int(m),
        "first_paths": {
            "W_T": first("W_T"),
            "left": first("left"), "mid": first("mid"), "right": first("right"),
            "half_WT_sq_minus_half_T": [float(0.5 * x * x - 0.5 * T) for x in v["W_T"][:keep_first]],
            "half_WT_sq": [float(0.5 * x * x) for x in v["W_T"][:keep_first]],
            "half_WT_sq_plus_half_T": [float(0.5 * x * x + 0.5 * T) for x in v["W_T"][:keep_first]],
            "sum_dW_sq": first("sum_dW_sq"),
        },
        "identities_max_abs_residual": {
            "left": float(np.abs(v["left_identity"]).max()),
            "mid": float(np.abs(v["mid_identity"]).max()),
            "mid_halves": float(np.abs(v["mid_halves_identity"]).max()),
            "right": float(np.abs(v["right_identity"]).max()),
        },
        "half_step_qv": {   # each half of the steps carries half the quadratic variation
            "sum_d1_sq_mean": float(v["sum_d1_sq"].mean()),
            "sum_d2_sq_mean": float(v["sum_d2_sq"].mean()),
            "sum_d1_d2_mean": float(v["sum_d1_d2"].mean()),
            "sum_d1_d2_rms": float(sqrt((v["sum_d1_d2"] ** 2).mean())),
            "sum_d1_d2_rms_expected": T / (2.0 * sqrt(n)),   # n terms, each of variance (dt/2)^2
            "expected_each_half": 0.5 * T,
        },
        "left_error": {**stats(v["left_error"]), "sd_expected": T / sqrt(2.0 * n)},
        "mid_error": {**stats(v["mid_error"]), "sd_expected": T / (2.0 * sqrt(n))},
        "right_error": {**stats(v["right_error"]), "sd_expected": T / sqrt(2.0 * n)},
        "gap_right_minus_left": {**stats(v["right"] - v["left"]), "expected": T,
                                 "note": "equals Sum (dW)^2 exactly"},
        "gap_mid_minus_left": {**stats(v["mid"] - v["left"]), "expected": 0.5 * T,
                               "note": "equals Sum d1^2 + Sum d1 d2 exactly"},
        "sum_dW_sq": stats(v["sum_dW_sq"]),
    }


# --- C2: expectations, isometry, martingale ----------------------------------


def expectations(rng, n, T, n_paths, chunk_paths, checkpoints):
    """Many paths on one grid. Per path: the three full sums, the running
    left sum I(t) and running right sum R(t) at the checkpoints (fractions
    of T), and the two halves of the left sum."""
    dt = T / n
    k_pts = [int(round(c * n)) for c in checkpoints]
    left, mid, right = [], [], []
    I_at, R_at = [], []
    first_half, second_half = [], []
    for _ in range(n_paths // chunk_paths):
        w = np.empty((chunk_paths, n + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(chunk_paths, n)) * sqrt(dt), axis=1, out=w[:, 1:])
        d = np.diff(w, axis=1)
        terms_left = w[:, :-1] * d
        terms_right = w[:, 1:] * d
        I = np.cumsum(terms_left, axis=1)          # I(t_k) = Sum_{i<k} W(t_i) dW_i
        R = np.cumsum(terms_right, axis=1)
        left.append(I[:, -1].copy()); right.append(R[:, -1].copy())   # copies: views would keep I, R alive
        # midpoint sum on this grid needs half-steps; use the coarse grid n/2
        # whose midpoints are this grid's odd points (n even).
        mid.append((w[:, 1::2][:, : n // 2] * np.diff(w[:, ::2], axis=1)).sum(axis=1))
        I_at.append(np.stack([I[:, k - 1] for k in k_pts], axis=1))
        R_at.append(np.stack([R[:, k - 1] for k in k_pts], axis=1))
        h = n // 2
        first_half.append(I[:, h - 1].copy()); second_half.append(I[:, -1] - I[:, h - 1])
    left, mid, right = map(np.concatenate, (left, mid, right))
    I_at, R_at = np.concatenate(I_at), np.concatenate(R_at)
    first_half, second_half = map(np.concatenate, (first_half, second_half))
    m = left.size

    def mean_se(x):
        return {"mean": float(x.mean()), "se": float(x.std(ddof=1) / sqrt(m))}

    def second_moment(x):
        x2 = x * x
        return {"mean": float(x2.mean()), "se": float(x2.std(ddof=1) / sqrt(m))}

    running = []
    for j, c in enumerate(checkpoints):
        t = c * T
        k = k_pts[j]
        running.append({
            "t": t, "k": k,
            "I": mean_se(I_at[:, j]),
            "I_sq": second_moment(I_at[:, j]),
            "I_sq_expected_limit": 0.5 * t * t,               # integral_0^t s ds
            "I_sq_expected_on_grid": 0.5 * dt * dt * k * (k - 1),  # Sum_{i<k} t_i dt
            "R": mean_se(R_at[:, j]),
            "R_expected": t,                                   # E[right] = E[left] + E[QV(t)]
        })
    return {
        "n": n, "dt": dt, "n_paths": int(m),
        "note_mid": f"midpoint sum evaluated on the n/2 = {n // 2} grid, whose midpoints are this grid's odd points",
        "left": {**mean_se(left), "expected": 0.0, "sd": float(left.std(ddof=1)),
                 "sd_expected_limit": T / sqrt(2.0)},
        "mid": {**mean_se(mid), "expected": 0.5 * T},
        "right": {**mean_se(right), "expected": T},
        "isometry": {**second_moment(left),
                     "expected_limit": 0.5 * T * T,
                     "expected_on_grid": 0.5 * T * T * (1.0 - 1.0 / n)},
        "running": running,
        "martingale": {
            "corr_first_half_second_half": float(np.corrcoef(first_half, second_half)[0, 1]),
            "mean_second_half_given_first_half_positive": float(second_half[first_half > 0].mean()),
            "mean_second_half_given_first_half_negative": float(second_half[first_half < 0].mean()),
            "se_second_half": float(second_half.std(ddof=1) / sqrt(m / 2)),
        },
    }


# --- C3: the smooth curve on the same grids ----------------------------------


def smooth_curve(n, T):
    t = np.linspace(0.0, T, n + 1)
    tm = 0.5 * (t[:-1] + t[1:])
    x = (t * t)[None, :]
    xm = (tm * tm)[None, :]
    v = riemann_sums(x, xm)
    target = 0.5 * float(x[0, -1]) ** 2
    return {
        "n": n,
        "left": float(v["left"][0]), "mid": float(v["mid"][0]), "right": float(v["right"][0]),
        "half_xT_sq": target,
        "sum_dx_sq": float(v["sum_dW_sq"][0]),
        "sum_dx_sq_times_n": float(v["sum_dW_sq"][0] * n),
        "sum_dx_sq_times_n_expected": 4.0 / 3.0,   # dt * integral_0^1 (2t)^2 dt
        "gap_right_minus_left": float(v["right"][0] - v["left"][0]),
        "max_abs_error_of_three": float(max(abs(v["left"][0] - target), abs(v["mid"][0] - target),
                                            abs(v["right"][0] - target))),
    }


# --- C4: the coin walk, built on each grid directly --------------------------


def coin_walk(rng, n, T, n_paths):
    dt = T / n
    steps = (rng.integers(0, 2, size=(n_paths, n), dtype=np.int8) * 2 - 1).astype(np.float64)
    w = np.empty((n_paths, n + 1))
    w[:, 0] = 0.0
    np.cumsum(steps * sqrt(dt), axis=1, out=w[:, 1:])
    d = np.diff(w, axis=1)
    left = (w[:, :-1] * d).sum(axis=1)
    right = (w[:, 1:] * d).sum(axis=1)
    WT = w[:, -1]
    return {
        "n": n, "n_paths": n_paths,
        "W_T": [float(x) for x in WT],
        "left": [float(x) for x in left],
        "right": [float(x) for x in right],
        "left_max_abs_deviation_from_half_WT_sq_minus_half_T": float(np.abs(left - (0.5 * WT**2 - 0.5 * T)).max()),
        "right_max_abs_deviation_from_half_WT_sq_plus_half_T": float(np.abs(right - (0.5 * WT**2 + 0.5 * T)).max()),
        "sum_dW_sq_max_abs_deviation_from_T": float(np.abs((d * d).sum(axis=1) - T).max()),
    }


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


# --- checks ------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []
    T = params["T"]
    # Statistical tolerances are set for the full run; a smaller run widens them
    # by the square root of the path-count ratio (1.0 for the full run). Checks
    # phrased as "within 5 s.e." scale themselves and need no slack.
    slack = sqrt(400 / params["nested_grids"]["n_paths"])
    slack_exp = sqrt(20_000 / params["expectations"]["n_paths"])

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    for g in res["grids"]:
        n = g["n"]
        r = g["identities_max_abs_residual"]
        add(f"C1 n={n:.0e}: left = 1/2 W_T^2 - 1/2 Sum (dW)^2 on every path (algebra)", r["left"], 0.0, 1e-9)
        add(f"C1 n={n:.0e}: right = 1/2 W_T^2 + 1/2 Sum (dW)^2 on every path (algebra)", r["right"], 0.0, 1e-9)
        add(f"C1 n={n:.0e}: mid = left + Sum d1^2 + Sum d1 d2 on every path (algebra)", r["mid"], 0.0, 1e-9)
        add(f"C1 n={n:.0e}: mid = 1/2 W_T^2 + 1/2 (Sum d1^2 - Sum d2^2) on every path (algebra)",
            r["mid_halves"], 0.0, 1e-9)
        hq = g["half_step_qv"]
        add(f"C1 n={n:.0e}: rms of Sum d1 d2 is T/(2 sqrt n)", hq["sum_d1_d2_rms"], hq["sum_d1_d2_rms_expected"],
            0.15 * slack, "rel")
        for name, label in (("left_error", "left - (1/2 W_T^2 - 1/2 T)"),
                            ("mid_error", "mid - 1/2 W_T^2"),
                            ("right_error", "right - (1/2 W_T^2 + 1/2 T)")):
            e = g[name]
            add(f"C1 n={n:.0e}: mean of {label} within 5 s.e. of 0", e["mean"], 0.0, 5 * e["se_of_mean"])
            add(f"C1 n={n:.0e}: sd of {label} is {'T/(2 sqrt n)' if name == 'mid_error' else 'T/sqrt(2n)'}",
                e["sd"], e["sd_expected"], 0.15 * slack, "rel")
        add(f"C1 n={n:.0e}: right - left (= Sum (dW)^2) has mean T",
            g["gap_right_minus_left"]["mean"], T, 5 * g["gap_right_minus_left"]["se_of_mean"])
        add(f"C1 n={n:.0e}: mid - left has mean T/2",
            g["gap_mid_minus_left"]["mean"], 0.5 * T, 5 * g["gap_mid_minus_left"]["se_of_mean"])

    for name in ("left_error", "mid_error", "right_error"):
        add(f"C1: log-log slope of sd({name}) vs n is -0.5", res["slopes"][f"sd_{name}"], -0.5, 0.03 * slack)

    e = res["expectations"]
    add(f"C2 (n={e['n']:.0e}, {e['n_paths']:,} paths): E[left] = 0", e["left"]["mean"], 0.0, 5 * e["left"]["se"])
    add("C2: E[mid] = T/2 (Stratonovich is not a martingale)", e["mid"]["mean"], 0.5 * T, 5 * e["mid"]["se"])
    add("C2: E[right] = T (peeking earns drift)", e["right"]["mean"], T, 5 * e["right"]["se"])
    add("C2 isometry: E[left^2] = T^2 (1 - 1/n) / 2  (limit T^2/2)",
        e["isometry"]["mean"], e["isometry"]["expected_on_grid"], 5 * e["isometry"]["se"])
    for r in e["running"]:
        add(f"C2 running t={r['t']:.2f}: E[I(t)] = 0", r["I"]["mean"], 0.0, 5 * r["I"]["se"])
        add(f"C2 running t={r['t']:.2f}: E[I(t)^2] = t^2/2 (on the grid)",
            r["I_sq"]["mean"], r["I_sq_expected_on_grid"], 5 * r["I_sq"]["se"])
        add(f"C2 running t={r['t']:.2f}: E[R(t)] = t for the right-endpoint sum",
            r["R"]["mean"], r["R_expected"], 5 * r["R"]["se"])
    mg = e["martingale"]
    add("C2 martingale: corr(first half of the sum, second half) is 0", mg["corr_first_half_second_half"], 0.0,
        0.03 * slack_exp)
    add("C2 martingale: E[second half | first half > 0] is 0",
        mg["mean_second_half_given_first_half_positive"], 0.0, 5 * mg["se_second_half"])
    add("C2 martingale: E[second half | first half < 0] is 0",
        mg["mean_second_half_given_first_half_negative"], 0.0, 5 * mg["se_second_half"])

    for s in res["smooth"]:
        n = s["n"]
        add(f"C3 n={n:.0e}: n * Sum (dx)^2 is 4/3 (so Sum (dx)^2 -> 0 like 1/n)",
            s["sum_dx_sq_times_n"], 4.0 / 3.0, 0.01, "rel")
        add(f"C3 n={n:.0e}: left, mid and right all within Sum (dx)^2 of 1/2 x_T^2",
            s["max_abs_error_of_three"], 0.0, s["sum_dx_sq"])
    add("C3: log-log slope of (right - left) vs n is -1", res["slopes"]["smooth_gap"], -1.0, 1e-3)

    for c in res["coin"]:
        add(f"C4 coin n={c['n']:.0e}: left = 1/2 W_T^2 - 1/2 T exactly, every path",
            c["left_max_abs_deviation_from_half_WT_sq_minus_half_T"], 0.0, 1e-9)
        add(f"C4 coin n={c['n']:.0e}: right = 1/2 W_T^2 + 1/2 T exactly, every path",
            c["right_max_abs_deviation_from_half_WT_sq_plus_half_T"], 0.0, 1e-9)
    return checks


# --- main --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the paths, wider tolerances, no JSON written")
    args = parser.parse_args()

    params = {
        "seed": args.seed,
        "T": 1.0,
        "nested_grids": {
            "n_fine": 2_000_000,     # twice the finest grid, so every grid's midpoints are path values
            "coarsen_by": [20_000, 2_000, 200, 20, 2],   # n = 10^2, 10^3, 10^4, 10^5, 10^6
            "n_paths": 40 if args.quick else 400,
            "chunk_paths": 5,        # memory only: draws are consumed row by row, so the paths do not depend on it
            "keep_first_paths": 5,
        },
        "expectations": {"n": 10_000, "n_paths": 2_000 if args.quick else 20_000, "chunk_paths": 1_000,
                         "checkpoints": [0.25, 0.5, 0.75, 1.0]},
        "smooth": {"x": "t^2", "ns": [100, 1_000, 10_000, 100_000, 1_000_000]},
        "coin": {"ns": [100, 1_000, 10_000, 100_000, 1_000_000], "n_paths": 5},
    }
    T = params["T"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    g = params["nested_grids"]
    per_n = nested_grids(rng, g["n_paths"], g["n_fine"], T, g["coarsen_by"], g["chunk_paths"])
    grids = [summarise_grid(n, T, per_n[n], g["keep_first_paths"]) for n in sorted(per_n)]
    ns = [x["n"] for x in grids]

    e = params["expectations"]
    print(f"[2.4] expectations: {e['n_paths']:,} paths at n={e['n']:,}", flush=True)
    exp = expectations(rng, e["n"], T, e["n_paths"], e["chunk_paths"], e["checkpoints"])

    print("[2.4] smooth curve and coin walk", flush=True)
    smooth = [smooth_curve(n, T) for n in params["smooth"]["ns"]]
    coin = [coin_walk(rng, n, T, params["coin"]["n_paths"]) for n in params["coin"]["ns"]]

    slopes = {
        "sd_left_error": loglog_slope(ns, [x["left_error"]["sd"] for x in grids]),
        "sd_mid_error": loglog_slope(ns, [x["mid_error"]["sd"] for x in grids]),
        "sd_right_error": loglog_slope(ns, [x["right_error"]["sd"] for x in grids]),
        "smooth_gap": loglog_slope([s["n"] for s in smooth], [s["gap_right_minus_left"] for s in smooth]),
    }

    results = {"grids": grids, "expectations": exp, "smooth": smooth, "coin": coin, "slopes": slopes}
    checks = build_checks(results, params)

    out = {
        "page": "2.4",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": results,
        "checks": checks,
    }
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.4] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  "
              f"({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.4] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
