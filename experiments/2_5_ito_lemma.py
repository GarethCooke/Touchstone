"""Ito's lemma -- the experiment behind page 2.5.

Serves page 2.5 (docs/quant-learn-index-v1.md). One Brownian path W on
[0, T], chopped into n equal steps of length dt = T/n, grid times t_i = i dt,
increments dW_i = W(t_{i+1}) - W(t_i), and a smooth function g. Page 2.3's
Taylor expansion, one step at a time,

    g(W + dW) - g(W) = g'(W) dW + 1/2 g''(W) (dW)^2 + 1/6 g'''(W) (dW)^3 + ...,

summed over the grid, telescopes on the left to g(W_T) - g(0). Ito's lemma
is the statement that, as n -> infinity, only the first two terms survive:

    g(W_T) - g(0) = integral_0^T g'(W) dW + 1/2 integral_0^T g''(W) dt.

The script measures the lemma in its two forms on every grid -- the
(dW)^2-form, which keeps 1/2 Sum g''(W_i) (dW_i)^2 and is exact algebra for
g = x^2 (page 2.3's identity, which 2.4 rearranges), and the dt-form, which
replaces (dW_i)^2 by dt
(the rulebook) and is a limit -- for three functions: g = x^2 (the
expansion stops at second order), g = e^x (every order present) and g = x^3
(stops at third order, so the remainder is exactly Sum (dW)^3). Five
claims, each measured:

  C1  g = x^2. The (dW)^2-form is EXACT on every grid and every path:
      W_T^2 = Sum 2 W_i dW_i + Sum (dW_i)^2 (2.3's identity, g'' = 2; 2.4
      solves it for the left sum). The
      dt-form's residual is exactly Sum (dW)^2 - T -- page 2.3's number,
      mean 0, sd T sqrt(2/n), slope -1/2. The lemma's dt term is that
      identity's Sum (dW)^2 with 2.3's limit taken.
  C2  g = e^x and g = x^3. The (dW)^2-form now leaves a remainder from
      third order and beyond, 1/6 Sum g'''(W_i) (dW_i)^3 + ...; it vanishes
      like 1/n (slope -1): the signed cubes cancel (an odd moment, sd
      sqrt(15) T^(3/2)/n for Sum (dW)^3), and the fourth-order term is
      dt^2-sized. Page 2.3's bound Sum |dW|^3 ~ 1/sqrt n is the worst case;
      the actual remainder is an order smaller. For x^3 the remainder IS
      Sum (dW)^3 exactly and the fourth-order residual is 0 to rounding.
      The dt-form's residual is that remainder plus the (dW)^2-vs-dt noise
      1/2 Sum g''(W_i) ((dW_i)^2 - dt): mean 0, rms
      sqrt(dt/2 Sum g''(W_i)^2 dt) -- in the limit
      sqrt((e^(2T) - 1)/(4n)) for e^x and 3 T^(3/2)/sqrt n for x^3 -- slope
      -1/2. So on a grid the lemma is off by a 1/sqrt n noise that comes
      from (dW)^2 vs dt, not from the Taylor remainder. (The rms checks
      compare against the paths' own Sum g''^2 dt and Sum g'''^2 dt: for
      e^x these are integrals of e^(2W), heavy-tailed enough that their
      400-path means scatter by tens of percent around the closed forms,
      which the JSON reports as the limits.)
  C3  E[e^(W_t)] = e^(t/2), not constant and not e^(sqrt t): the growth is
      entirely the dt term. Split e^(W_t) - 1 = Sum e^(W_i) dW_i +
      1/2 Sum e^(W_i) dt + residual; the Ito sum has mean 0 at every
      checkpoint, the dt sum has mean e^(t/2) - 1. Hence the martingale:
      E[e^(W_t - t/2)] = 1 at t = 0.1, 0.25, 0.5, 0.75, 1, and its second
      half is uncorrelated with its first (as 2.4 C2). The candidates
      c = 1 (mean e^(-t/2)) and c t = sqrt t (mean e^(t/2 - sqrt t)) are
      reported beside it. Measured on 20,000 paths at n = 10^4, means
      within 5 s.e.
  C4  The smooth contrast, x(t) = t^2 on the same five grids, for the same
      three g: g(x_T) - g(0) - Sum g'(x_i) dx_i -> 0 like 1/n (the
      (dx)^2 term is dt^2-sized, 2.4 C3), so the chain rule holds and there
      is NO dt term: adding 1/2 Sum g''(x_i) dt makes the residual
      -1/2 integral_0^T g''(x(t)) dt, a constant that never shrinks.
  C5  The +-sqrt(dt) coin walk from 2.1 has (dW_i)^2 = dt on every step, so
      the two forms coincide EXACTLY, every n, every path: for x^2 both
      residuals are 0; for x^3 both are Sum (dW)^3 = dt W_T exactly, and
      the fourth-order residual is 0.

Paths are drawn once on a grid of 10^6 steps and coarsened, so the same
path is summed on n = 10^2 .. 10^6 (2.3's shape; no midpoints are needed
here, so the fine grid is 10^6, not 2.4's 2 x 10^6).

Run from the repository root:

    uv run experiments/2_5_ito_lemma.py [--seed 20260914] [--quick]

--quick runs a tenth of the paths for the learn site's build-time snippet
check (I3): the statistical tolerances widen by sqrt(400 / n_paths) so the
same claims are still asserted, and NO JSON is written -- the committed
result is always the full run.

Writes 2_5_ito_lemma.json beside this file: parameters in, results out, no
timestamps -- same seed, same file (I6). No plotting here; the site draws
(see experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import exp, sqrt
from pathlib import Path

import numpy as np


# --- the functions g, with g', g'', g''' ------------------------------------
#
# derivs(x) returns (g', g'', g''') evaluated at x; a constant derivative is
# returned as a scalar and broadcast where it is summed.


def _sq(x):
    return x * x


def _sq_derivs(x):
    return 2.0 * x, 2.0, 0.0


def _exp_derivs(x):
    e = np.exp(x)
    return e, e, e


def _cube(x):
    return x * x * x


def _cube_derivs(x):
    return 3.0 * x * x, 6.0 * x, 6.0


FUNCTIONS = {
    "x^2": (_sq, _sq_derivs),      # the expansion stops at second order: (dW)^2-form exact
    "exp": (np.exp, _exp_derivs),  # every order present: g = g' = g'' = g''' = e^x
    "x^3": (_cube, _cube_derivs),  # stops at third order: remainder is exactly Sum (dW)^3
}
FUNCTION_ORDER = ["x^2", "exp", "x^3"]


# --- the two forms of the lemma for one g on one grid ------------------------


def taylor_sums(w_grid: np.ndarray, dt: float, name: str) -> dict[str, np.ndarray]:
    """w_grid has shape (paths, n + 1): the path at the grid times. Returns,
    per path, the left side g(W_T) - g(W_0), the left-endpoint Ito sum
    Sum g'(W_i) dW_i, the second-order term in both forms, the third-order
    term, and the residuals of the two forms."""
    g, derivs = FUNCTIONS[name]
    d = np.diff(w_grid, axis=1)                    # dW_i, shape (paths, n)
    g1, g2, g3 = derivs(w_grid[:, :-1])            # read at the LEFT endpoint (2.4)
    d2 = d * d
    lhs = g(w_grid[:, -1]) - g(w_grid[:, 0])       # g(W_T) - g(0): the telescoped left side
    ito_sum = (g1 * d).sum(axis=1)                 # Sum g'(W_i) dW_i
    qv_term = 0.5 * (g2 * d2).sum(axis=1)          # 1/2 Sum g''(W_i) (dW_i)^2  -- the (dW)^2-form
    dt_term = 0.5 * dt * np.broadcast_to(g2, d.shape).sum(axis=1)   # 1/2 Sum g''(W_i) dt -- the dt-form
    cubic_term = (np.broadcast_to(g3, d.shape) * (d2 * d)).sum(axis=1) / 6.0   # 1/6 Sum g'''(W_i) (dW_i)^3
    r_qv = lhs - ito_sum - qv_term                 # third order and beyond
    r_dt = lhs - ito_sum - dt_term                 # r_qv + 1/2 Sum g''(W_i) ((dW_i)^2 - dt)
    # The paths' own predictions for the two noise terms' mean-squares (see
    # summarise_grid): the terms are martingale differences, so the
    # mean-square of the sum is the sum of the conditional mean-squares, and
    # E[(dW^2 - dt)^2] = 2 dt^2, E[(dW)^6] = 15 dt^3 given the past.
    g2b = np.broadcast_to(g2, d.shape)
    g3b = np.broadcast_to(g3, d.shape)
    noise = qv_term - dt_term                      # 1/2 Sum g''(W_i) ((dW_i)^2 - dt): (dW)^2 vs dt on a grid
    int_g2_sq = dt * (g2b * g2b).sum(axis=1)       # Sum g''(W_i)^2 dt  ~ integral_0^T g''(W)^2 dt
    int_g3_sq = dt * (g3b * g3b).sum(axis=1)       # Sum g'''(W_i)^2 dt
    return {
        "W_T": w_grid[:, -1].copy(),               # copy: a view would keep the whole chunk alive
        "lhs": lhs, "ito_sum": ito_sum, "qv_term": qv_term, "dt_term": dt_term,
        "cubic_term": cubic_term,
        "r_qv": r_qv, "r_dt": r_dt,
        "r_3": r_qv - cubic_term,                  # fourth order and beyond
        "noise": noise,
        "int_g2_sq": int_g2_sq, "int_g3_sq": int_g3_sq,
        # per path, squared term minus its conditional mean-square: mean 0 exactly
        "noise_sq_excess": noise * noise - 0.5 * dt * int_g2_sq,
        "cubic_sq_excess": cubic_term * cubic_term - (15.0 / 36.0) * dt * dt * int_g3_sq,
    }


def increment_sums(w_grid: np.ndarray) -> dict[str, np.ndarray]:
    """Per path: Sum (dW)^2 (2.3's number), the signed Sum (dW)^3 (an odd
    moment, cancels) and 2.3's bound Sum |dW|^3."""
    d = np.diff(w_grid, axis=1)
    d2 = d * d
    return {
        "sum_dW_sq": d2.sum(axis=1),
        "sum_dW_cubed": (d2 * d).sum(axis=1),
        "sum_abs_dW_cubed": (d2 * np.abs(d)).sum(axis=1),
    }


def coarsen(w: np.ndarray, factor: int) -> np.ndarray:
    """The same path on a grid factor times coarser. Coarse increments are
    sums of fine ones, so the coarse path is exactly Brownian."""
    return w[:, ::factor]


# --- C1, C2: the same paths on five grids -----------------------------------


def nested_grids(rng, n_paths, n_fine, T, factors, chunk_paths):
    """Simulate paths on the finest grid in chunks; for each coarsening factor
    and each g accumulate the per-path sums. Draws are consumed row by row,
    so the paths do not depend on chunk_paths.
    Returns {n: {"increments": {name: array}, name_of_g: {name: array}}}."""
    dt_fine = T / n_fine
    acc = {f: {"increments": {}, **{name: {} for name in FUNCTION_ORDER}} for f in factors}
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        w = np.empty((k, n_fine + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(k, n_fine)) * sqrt(dt_fine), axis=1, out=w[:, 1:])
        for f in factors:
            wg = coarsen(w, f)
            dt = dt_fine * f
            for name, arr in increment_sums(wg).items():
                acc[f]["increments"].setdefault(name, []).append(arr)
            for gname in FUNCTION_ORDER:
                for name, arr in taylor_sums(wg, dt, gname).items():
                    acc[f][gname].setdefault(name, []).append(arr)
        done += k
        print(f"[2.5] nested grids: {done:,}/{n_paths:,} paths", flush=True)
    per_n = {}
    for f in factors:
        per_n[n_fine // f] = {group: {name: np.concatenate(parts) for name, parts in d.items()}
                              for group, d in acc[f].items()}
    return per_n


def stats(x: np.ndarray) -> dict[str, float]:
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)),
            "se_of_mean": float(x.std(ddof=1) / sqrt(x.size)),
            "rms": float(sqrt((x * x).mean())),
            "max_abs": float(np.abs(x).max())}


def summarise_grid(n, T, per_grid, keep_first):
    dt = T / n
    inc = per_grid["increments"]
    out = {
        "n": n, "dt": dt, "n_paths": int(inc["sum_dW_sq"].size),
        "sum_dW_sq": {**stats(inc["sum_dW_sq"]), "expected": T, "sd_expected": T * sqrt(2.0 / n)},
        "sum_dW_cubed": {**stats(inc["sum_dW_cubed"]), "expected": 0.0,
                         "sd_expected": sqrt(15.0) * T ** 1.5 / n,   # n terms of variance E[(dW)^6] = 15 dt^3
                         "note": "an odd moment: the signed cubes cancel, so this is 1/n, not 2.3's 1/sqrt n bound"},
        "sum_abs_dW_cubed": {**stats(inc["sum_abs_dW_cubed"]),
                             "mean_expected": 2.0 * sqrt(2.0 / np.pi) * T ** 1.5 / sqrt(n),   # n E|dW|^3, E|Z|^3 = 2 sqrt(2/pi)
                             "note": "2.3 C4's bound: Sum |dW|^3 -> 0 like 1/sqrt n"},
        "functions": {},
    }
    for gname in FUNCTION_ORDER:
        v = per_grid[gname]
        first = lambda name: [float(x) for x in v[name][:keep_first]]  # noqa: E731
        entry = {
            "first_paths": {name: first(name) for name in
                            ("W_T", "lhs", "ito_sum", "qv_term", "dt_term", "r_qv", "r_dt", "cubic_term", "r_3")},
            "r_qv": stats(v["r_qv"]),
            "r_dt": stats(v["r_dt"]),
            "noise": {**stats(v["noise"]), "expected_mean": 0.0,
                      # E[noise^2] = Sum (1/4) g''(W_i)^2 * 2 dt^2 = (dt/2) Sum g''(W_i)^2 dt, given the paths
                      "rms_expected_from_paths": float(sqrt(0.5 * dt * v["int_g2_sq"].mean())),
                      "sq_excess": {"mean": float(v["noise_sq_excess"].mean()),
                                    "se_of_mean": float(v["noise_sq_excess"].std(ddof=1) / sqrt(v["noise"].size)),
                                    "note": "noise^2 - (dt/2) Sum g''^2 dt per path; mean 0 exactly"},
                      "note": "qv_term - dt_term = 1/2 Sum g''(W_i) ((dW_i)^2 - dt): what replacing (dW)^2 by dt costs on a grid"},
            "cubic_term": {**stats(v["cubic_term"]), "expected_mean": 0.0,
                           # E[cubic^2] = Sum (1/36) g'''(W_i)^2 * 15 dt^3 = (15/36) dt^2 Sum g'''(W_i)^2 dt
                           "rms_expected_from_paths": float(sqrt(15.0 / 36.0 * dt * dt * v["int_g3_sq"].mean())),
                           "sq_excess": {"mean": float(v["cubic_sq_excess"].mean()),
                                         "se_of_mean": float(v["cubic_sq_excess"].std(ddof=1) / sqrt(v["cubic_term"].size)),
                                         "note": "cubic^2 - (15/36) dt^2 Sum g'''^2 dt per path; mean 0 exactly"}},
            "r_3": stats(v["r_3"]),
            "int_g2_sq_mean": float(v["int_g2_sq"].mean()),
            "int_g3_sq_mean": float(v["int_g3_sq"].mean()),
        }
        if gname == "x^2":
            entry["r_qv"]["expected"] = "0 exactly: the expansion stops at second order (2.3's identity, rearranged in 2.4)"
            entry["r_dt"]["expected_identity"] = "Sum (dW)^2 - T exactly (= noise: r_qv is 0)"
            entry["r_dt"]["identity_max_abs_residual"] = float(np.abs(v["r_dt"] - (inc["sum_dW_sq"] - T)).max())
            entry["noise"]["rms_expected_limit"] = T * sqrt(2.0 / n)          # int_g2_sq = 4T exactly
            entry["cubic_term"]["expected"] = "0 exactly: g''' = 0"
        elif gname == "exp":
            # int_g2_sq = Sum e^(2 W_i) dt, mean integral_0^T e^(2t) dt = (e^(2T) - 1)/2 -- but e^(2W) is
            # heavy-tailed, so the 400-path mean of it scatters by tens of percent; the checks use the
            # paths' own value and the closed form is reported for the limit.
            entry["noise"]["rms_expected_limit"] = sqrt((exp(2.0 * T) - 1.0) / (4.0 * n))
            entry["cubic_term"]["rms_expected_limit"] = sqrt(15.0 / 36.0 * (exp(2.0 * T) - 1.0) / 2.0) * T / n
            entry["int_g2_sq_expected_limit"] = (exp(2.0 * T) - 1.0) / 2.0
            entry["r_qv"]["note"] = "third order and beyond: the cubic term plus a dt^2-sized fourth-order part, rms ~ 1/n"
        elif gname == "x^3":
            entry["r_qv"]["expected_identity"] = "Sum (dW)^3 exactly: the expansion stops at third order"
            entry["r_qv"]["identity_max_abs_residual"] = float(np.abs(v["r_qv"] - inc["sum_dW_cubed"]).max())
            entry["r_qv"]["rms_expected"] = sqrt(15.0) * T ** 1.5 / n
            entry["cubic_term"]["rms_expected_limit"] = sqrt(15.0) * T ** 1.5 / n   # int_g3_sq = 36T exactly
            entry["noise"]["rms_expected_limit"] = 3.0 * T ** 1.5 / sqrt(n)         # int_g2_sq = 36 Sum W_i^2 dt, mean 18T^2
            entry["int_g2_sq_expected_limit"] = 18.0 * T * T
            entry["r_3"]["expected"] = "0 exactly: nothing beyond third order"
        out["functions"][gname] = entry
    return out


# --- C3: E[e^W] grows, and e^(W - t/2) is the martingale ---------------------


def expectations(rng, n, T, n_paths, chunk_paths, checkpoints):
    """Many paths on one grid. Per path, at each checkpoint t (a fraction of
    T): e^(W_t); the candidates e^(W_t - t/2), e^(W_t - t), e^(W_t - sqrt t);
    the running Ito sum S(t) = Sum_{i<k} e^(W_i) dW_i and the running dt sum
    D(t) = 1/2 Sum_{i<k} e^(W_i) dt, so that e^(W_t) - 1 = S(t) + D(t) +
    residual on every path."""
    dt = T / n
    k_pts = [int(round(c * n)) for c in checkpoints]
    ts = [c * T for c in checkpoints]
    expW_at, S_at, D_at = [], [], []
    M_half, M_T = [], []
    for _ in range(n_paths // chunk_paths):
        w = np.empty((chunk_paths, n + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(chunk_paths, n)) * sqrt(dt), axis=1, out=w[:, 1:])
        e = np.exp(w)
        d = np.diff(w, axis=1)
        S = np.cumsum(e[:, :-1] * d, axis=1)            # S(t_k) = Sum_{i<k} e^(W_i) dW_i
        D = np.cumsum(e[:, :-1], axis=1) * (0.5 * dt)   # D(t_k) = 1/2 Sum_{i<k} e^(W_i) dt
        expW_at.append(np.stack([e[:, k] for k in k_pts], axis=1))    # stack copies
        S_at.append(np.stack([S[:, k - 1] for k in k_pts], axis=1))
        D_at.append(np.stack([D[:, k - 1] for k in k_pts], axis=1))
        M_half.append(e[:, n // 2].copy() * exp(-0.25 * T))   # e^(W_{T/2} - T/4)
        M_T.append(e[:, -1].copy() * exp(-0.5 * T))           # e^(W_T - T/2)
    expW_at, S_at, D_at = map(np.concatenate, (expW_at, S_at, D_at))
    M_half, M_T = map(np.concatenate, (M_half, M_T))
    m = M_T.size

    def mean_se(x):
        return {"mean": float(x.mean()), "se": float(x.std(ddof=1) / sqrt(m))}

    running = []
    for j, t in enumerate(ts):
        k = k_pts[j]
        ew = expW_at[:, j]
        running.append({
            "t": t, "k": k,
            "exp_W": {**mean_se(ew), "expected": exp(0.5 * t),
                      "P1_candidate_exp_sqrt_t": exp(sqrt(t)),
                      "constant_candidate": 1.0},
            "exp_W_minus_half_t": {**mean_se(ew * exp(-0.5 * t)), "expected": 1.0},
            "exp_W_minus_t": {**mean_se(ew * exp(-t)), "expected": exp(-0.5 * t),
                              "note": "the c = 1 candidate: mean falls like e^(-t/2)"},
            "exp_W_minus_sqrt_t": {**mean_se(ew * exp(-sqrt(t))), "expected": exp(0.5 * t - sqrt(t)),
                                   "note": "the owner's P2, c t = sqrt t: not constant"},
            "growth_split": {
                "exp_W_minus_1": mean_se(ew - 1.0),
                "ito_sum_S": {**mean_se(S_at[:, j]), "expected": 0.0},
                "dt_sum_D": {**mean_se(D_at[:, j]),
                             "expected_on_grid": 0.5 * dt * (exp(0.5 * k * dt) - 1.0) / (exp(0.5 * dt) - 1.0),
                             "expected_limit": exp(0.5 * t) - 1.0},
                "residual": mean_se(ew - 1.0 - S_at[:, j] - D_at[:, j]),
            },
        })
    second_half = M_T - M_half
    return {
        "n": n, "dt": dt, "n_paths": int(m),
        "running": running,
        "martingale": {
            "process": "M(t) = e^(W_t - t/2)",
            "corr_first_half_second_half": float(np.corrcoef(M_half - 1.0, second_half)[0, 1]),
            "mean_second_half_given_M_half_above_1": float(second_half[M_half > 1.0].mean()),
            "mean_second_half_given_M_half_below_1": float(second_half[M_half < 1.0].mean()),
            "se_second_half": float(second_half.std(ddof=1) / sqrt(m / 2)),
            "sd_M_T": float(M_T.std(ddof=1)),
            "sd_M_T_expected": sqrt(exp(T) - 1.0),   # lognormal: Var e^(W_T - T/2) = e^T - 1
        },
    }


# --- C4: the smooth curve on the same grids ----------------------------------


def smooth_constants(T, name, n_quad=1_000_000):
    """L = lim n (g(x_T) - g(0) - Sum g'(x_i) dx_i) = 1/2 T integral_0^T g''(x(t)) x'(t)^2 dt
    and C = 1/2 integral_0^T g''(x(t)) dt, for x(t) = t^2, by the trapezoid rule
    on a fine grid (x^2: L = 4/3, C = 1; x^3: L = 12/5, C = 1;
    e^x: L = e - integral_0^1 e^(t^2) dt = 1.2556, C = 0.7313 at T = 1)."""
    t = np.linspace(0.0, T, n_quad + 1)
    _, g2, _ = FUNCTIONS[name][1](t * t)
    g2 = np.broadcast_to(g2, t.shape)
    return {"L": float(0.5 * T * np.trapezoid(g2 * (2.0 * t) ** 2, t)),
            "C": float(0.5 * np.trapezoid(g2, t))}


def smooth_curve(n, T, name, consts):
    t = np.linspace(0.0, T, n + 1)
    x = (t * t)[None, :]
    v = taylor_sums(x, T / n, name)
    r_chain = float(v["lhs"][0] - v["ito_sum"][0])     # the chain rule's residual: -> 0 like 1/n
    return {
        "n": n,
        "lhs": float(v["lhs"][0]), "chain_sum": float(v["ito_sum"][0]),
        "chain_residual": r_chain,
        "chain_residual_times_n": r_chain * n,
        "chain_residual_times_n_expected": consts["L"],
        "qv_term": float(v["qv_term"][0]),
        "dt_term": float(v["dt_term"][0]),
        "residual_with_dt_term": float(v["r_dt"][0]),   # r_chain - dt_term: -> -C, a constant that never shrinks
        "residual_with_dt_term_expected": -consts["C"],
    }


# --- C5: the coin walk, built on each grid directly --------------------------


def coin_walk(rng, n, T, n_paths):
    dt = T / n
    steps = (rng.integers(0, 2, size=(n_paths, n), dtype=np.int8) * 2 - 1).astype(np.float64)
    w = np.empty((n_paths, n + 1))
    w[:, 0] = 0.0
    np.cumsum(steps * sqrt(dt), axis=1, out=w[:, 1:])
    sq = taylor_sums(w, dt, "x^2")
    cu = taylor_sums(w, dt, "x^3")
    WT = w[:, -1]
    return {
        "n": n, "n_paths": n_paths,
        "W_T": [float(x) for x in WT],
        "x^2": {"r_qv_max_abs": float(np.abs(sq["r_qv"]).max()),
                "r_dt_max_abs": float(np.abs(sq["r_dt"]).max()),
                "note": "(dW)^2 = dt on every step, so the two forms coincide and both are exact"},
        "x^3": {"r_qv": [float(x) for x in cu["r_qv"]],
                "dt_times_W_T": [float(dt * x) for x in WT],
                "r_qv_minus_dt_W_T_max_abs": float(np.abs(cu["r_qv"] - dt * WT).max()),
                "r_dt_minus_dt_W_T_max_abs": float(np.abs(cu["r_dt"] - dt * WT).max()),
                "r_3_max_abs": float(np.abs(cu["r_3"]).max()),
                "note": "Sum (dW)^3 = dt^(3/2) Sum (+-1) = dt W_T exactly"},
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
        f = g["functions"]
        # C1: x^2
        add(f"C1 n={n:.0e}: x^2 (dW)^2-form exact on every path: W_T^2 = Sum 2W dW + Sum (dW)^2 (algebra)",
            f["x^2"]["r_qv"]["max_abs"], 0.0, 1e-9)
        add(f"C1 n={n:.0e}: x^2 dt-form residual = Sum (dW)^2 - T on every path (algebra)",
            f["x^2"]["r_dt"]["identity_max_abs_residual"], 0.0, 1e-9)
        add(f"C1 n={n:.0e}: x^2 dt-form residual has mean 0 (within 5 s.e.)",
            f["x^2"]["r_dt"]["mean"], 0.0, 5 * f["x^2"]["r_dt"]["se_of_mean"])
        add(f"C1 n={n:.0e}: x^2 dt-form residual has rms T sqrt(2/n) (2.3's number)",
            f["x^2"]["r_dt"]["rms"], f["x^2"]["noise"]["rms_expected_limit"], 0.15 * slack, "rel")
        # C2: e^x and x^3
        for gname, label in (("exp", "e^x"), ("x^3", "x^3")):
            e = f[gname]
            add(f"C2 n={n:.0e}: {label} third-order term 1/6 Sum g''' (dW)^3 has mean 0 (odd moment, within 5 s.e.)",
                e["cubic_term"]["mean"], 0.0, 5 * e["cubic_term"]["se_of_mean"])
            # e^x's weights e^(2W) are heavy-tailed: (dW)^6 has median 0.1 x its mean, and a few peak steps
            # of a few paths carry the mean-square, so the level is known to ~20 % at 400 paths -- the
            # slope check below carries the rate; x^3's level is checked to 15 % against its closed form
            add(f"C2 n={n:.0e}: {label} third-order term has rms sqrt(15/36 dt^2 Sum g'''^2 dt) -- 1/n"
                + (" (to 30 %: e^(2W) is heavy-tailed)" if gname == "exp" else ""),
                e["cubic_term"]["rms"], e["cubic_term"]["rms_expected_from_paths"],
                (0.30 if gname == "exp" else 0.15) * slack, "rel")
            add(f"C2 n={n:.0e}: {label} (dW)^2-vs-dt noise 1/2 Sum g'' ((dW)^2 - dt) has mean 0 (within 5 s.e.)",
                e["noise"]["mean"], 0.0, 5 * e["noise"]["se_of_mean"])
            add(f"C2 n={n:.0e}: {label} (dW)^2-vs-dt noise's mean-square is (dt/2) Sum g''^2 dt (within 5 s.e.) -- 1/sqrt n",
                e["noise"]["sq_excess"]["mean"], 0.0, 5 * e["noise"]["sq_excess"]["se_of_mean"])
            add(f"C2 n={n:.0e}: {label} dt-form residual has mean 0 (within 5 s.e.; the true mean is O(1/n))",
                e["r_dt"]["mean"], 0.0, 5 * e["r_dt"]["se_of_mean"])
        add(f"C2 n={n:.0e}: x^3 third-order term has rms sqrt(15) T^(3/2)/n (closed form)",
            f["x^3"]["cubic_term"]["rms"], f["x^3"]["cubic_term"]["rms_expected_limit"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: x^3 (dW)^2-vs-dt noise has rms sqrt(dt/2 Sum g''^2 dt) (limit 3 T^(3/2)/sqrt n)",
            f["x^3"]["noise"]["rms"], f["x^3"]["noise"]["rms_expected_from_paths"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: x^3 (dW)^2-form residual = Sum (dW)^3 on every path (algebra)",
            f["x^3"]["r_qv"]["identity_max_abs_residual"], 0.0, 1e-9)
        add(f"C2 n={n:.0e}: x^3 fourth-order residual is 0 on every path (the expansion stops at third order)",
            f["x^3"]["r_3"]["max_abs"], 0.0, 1e-9)
        add(f"C2 n={n:.0e}: x^3 (dW)^2-form residual has rms sqrt(15) T^(3/2)/n",
            f["x^3"]["r_qv"]["rms"], f["x^3"]["r_qv"]["rms_expected"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: e^x (dW)^2-form residual is smaller than its dt-form residual (remainder vs (dW)^2-noise)",
            float(f["exp"]["r_qv"]["rms"] < f["exp"]["r_dt"]["rms"]), 1.0, 0.0)
        # the increment sums behind C2
        add(f"C2 n={n:.0e}: Sum (dW)^3 has mean 0 (odd moment, within 5 s.e.)",
            g["sum_dW_cubed"]["mean"], 0.0, 5 * g["sum_dW_cubed"]["se_of_mean"])
        add(f"C2 n={n:.0e}: Sum (dW)^3 has sd sqrt(15) T^(3/2)/n",
            g["sum_dW_cubed"]["sd"], g["sum_dW_cubed"]["sd_expected"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: Sum |dW|^3 has mean 2 sqrt(2/pi) T^(3/2)/sqrt n (2.3 C4's bound)",
            g["sum_abs_dW_cubed"]["mean"], g["sum_abs_dW_cubed"]["mean_expected"], 0.05 * slack, "rel")

    s = res["slopes"]
    for gname, label in (("x^2", "x^2"), ("exp", "e^x"), ("x^3", "x^3")):
        add(f"C1/C2: log-log slope of sd({label} dt-form residual) vs n is -1/2", s[f"sd_r_dt_{gname}"], -0.5, 0.03 * slack)
    for gname, label in (("exp", "e^x"), ("x^3", "x^3")):
        add(f"C2: log-log slope of rms({label} (dW)^2-form residual) vs n is -1", s[f"rms_r_qv_{gname}"], -1.0, 0.05 * slack)
    add("C2: log-log slope of sd(Sum (dW)^3) vs n is -1", s["sd_sum_dW_cubed"], -1.0, 0.05 * slack)
    add("C2: log-log slope of mean(Sum |dW|^3) vs n is -1/2 (2.3's bound)", s["mean_sum_abs_dW_cubed"], -0.5, 0.01 * slack)

    e = res["expectations"]
    for r in e["running"]:
        t = r["t"]
        add(f"C3 t={t:.2f} ({e['n_paths']:,} paths, n={e['n']:.0e}): E[e^W_t] = e^(t/2)",
            r["exp_W"]["mean"], r["exp_W"]["expected"], 5 * r["exp_W"]["se"])
        add(f"C3 t={t:.2f}: E[e^(W_t - t/2)] = 1 (the martingale)",
            r["exp_W_minus_half_t"]["mean"], 1.0, 5 * r["exp_W_minus_half_t"]["se"])
        gs = r["growth_split"]
        add(f"C3 t={t:.2f}: E[Sum e^W dW] = 0 -- the Ito sum contributes nothing on average",
            gs["ito_sum_S"]["mean"], 0.0, 5 * gs["ito_sum_S"]["se"])
        add(f"C3 t={t:.2f}: E[1/2 Sum e^W dt] = e^(t/2) - 1 (on the grid) -- the dt term is the whole growth",
            gs["dt_sum_D"]["mean"], gs["dt_sum_D"]["expected_on_grid"], 5 * gs["dt_sum_D"]["se"])
    mg = e["martingale"]
    add("C3 martingale: corr(M(T/2) - 1, M(T) - M(T/2)) is 0", mg["corr_first_half_second_half"], 0.0,
        0.03 * slack_exp)
    add("C3 martingale: E[M(T) - M(T/2) | M(T/2) > 1] is 0",
        mg["mean_second_half_given_M_half_above_1"], 0.0, 5 * mg["se_second_half"])
    add("C3 martingale: E[M(T) - M(T/2) | M(T/2) < 1] is 0",
        mg["mean_second_half_given_M_half_below_1"], 0.0, 5 * mg["se_second_half"])

    for gname, label in (("x^2", "x^2"), ("exp", "e^x"), ("x^3", "x^3")):
        rows = res["smooth"][gname]
        for r in rows:
            n = r["n"]
            add(f"C4 n={n:.0e}: {label} on x = t^2: n * (chain-rule residual) is the constant L (residual -> 0 like 1/n)",
                r["chain_residual_times_n"], r["chain_residual_times_n_expected"], 0.02, "rel")
            add(f"C4 n={n:.0e}: {label} on x = t^2: adding the dt term leaves a residual of -C that does not shrink",
                r["residual_with_dt_term"], r["residual_with_dt_term_expected"], 0.05, "rel")
        add(f"C4: {label} on x = t^2: log-log slope of the chain-rule residual vs n is -1",
            s[f"smooth_chain_residual_{gname}"], -1.0, 0.01)
        add(f"C4: {label} on x = t^2: the wrongly added dt term's residual at n=1e6 is -C to 0.01%",
            rows[-1]["residual_with_dt_term"], rows[-1]["residual_with_dt_term_expected"], 1e-4, "rel")

    for c in res["coin"]:
        n = c["n"]
        add(f"C5 coin n={n:.0e}: x^2 -- both forms exact, every path", max(c["x^2"]["r_qv_max_abs"], c["x^2"]["r_dt_max_abs"]), 0.0, 1e-9)
        add(f"C5 coin n={n:.0e}: x^3 -- both residuals equal dt W_T exactly, every path",
            max(c["x^3"]["r_qv_minus_dt_W_T_max_abs"], c["x^3"]["r_dt_minus_dt_W_T_max_abs"]), 0.0, 1e-9)
        add(f"C5 coin n={n:.0e}: x^3 -- fourth-order residual 0, every path", c["x^3"]["r_3_max_abs"], 0.0, 1e-9)
    return checks


# --- main --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the paths, wider tolerances, no JSON written")
    args = parser.parse_args()

    params = {
        "seed": args.seed,
        "T": 1.0,
        "functions": {"x^2": "g' = 2x, g'' = 2, g''' = 0",
                      "exp": "g = g' = g'' = g''' = e^x",
                      "x^3": "g' = 3x^2, g'' = 6x, g''' = 6"},
        "nested_grids": {
            "n_fine": 1_000_000,
            "coarsen_by": [10_000, 1_000, 100, 10, 1],   # n = 10^2, 10^3, 10^4, 10^5, 10^6
            "n_paths": 40 if args.quick else 400,
            "chunk_paths": 5,        # memory only: draws are consumed row by row, so the paths do not depend on it
            "keep_first_paths": 5,
        },
        "expectations": {"n": 10_000, "n_paths": 2_000 if args.quick else 20_000, "chunk_paths": 1_000,
                         "checkpoints": [0.1, 0.25, 0.5, 0.75, 1.0]},
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
    print(f"[2.5] expectations: {e['n_paths']:,} paths at n={e['n']:,}", flush=True)
    exp_res = expectations(rng, e["n"], T, e["n_paths"], e["chunk_paths"], e["checkpoints"])

    print("[2.5] smooth curve and coin walk", flush=True)
    consts = {gname: smooth_constants(T, gname) for gname in FUNCTION_ORDER}
    smooth = {gname: [smooth_curve(n, T, gname, consts[gname]) for n in params["smooth"]["ns"]]
              for gname in FUNCTION_ORDER}
    coin = [coin_walk(rng, n, T, params["coin"]["n_paths"]) for n in params["coin"]["ns"]]

    slopes = {
        "sd_sum_dW_cubed": loglog_slope(ns, [x["sum_dW_cubed"]["sd"] for x in grids]),
        "mean_sum_abs_dW_cubed": loglog_slope(ns, [x["sum_abs_dW_cubed"]["mean"] for x in grids]),
    }
    for gname in FUNCTION_ORDER:
        slopes[f"sd_r_dt_{gname}"] = loglog_slope(ns, [x["functions"][gname]["r_dt"]["sd"] for x in grids])
        if gname != "x^2":
            slopes[f"rms_r_qv_{gname}"] = loglog_slope(ns, [x["functions"][gname]["r_qv"]["rms"] for x in grids])
        slopes[f"smooth_chain_residual_{gname}"] = loglog_slope(
            [r["n"] for r in smooth[gname]], [abs(r["chain_residual"]) for r in smooth[gname]])

    results = {"grids": grids, "expectations": exp_res, "smooth": smooth, "smooth_constants": consts,
               "coin": coin, "slopes": slopes}
    checks = build_checks(results, params)

    out = {
        "page": "2.5",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": results,
        "checks": checks,
    }
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.5] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  "
              f"({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.5] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
