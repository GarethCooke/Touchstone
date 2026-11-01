"""SDEs and geometric Brownian motion -- the experiment behind page 2.6.

Serves page 2.6 (docs/quant-learn-index-v1.md). The price model is the SDE

    dS = mu S dt + sigma S dW        (drift first: a = mu S, b = sigma S),

and page 2.5's general form of Ito's lemma, applied to f(S) = log S, turns it
into

    d(log S) = (mu - 1/2 sigma^2) dt + sigma dW,

whose right side no longer depends on S, so it integrates: the closed-form
sample is

    S_T = S_0 exp((mu - 1/2 sigma^2) T + sigma W_T).

The script measures five claims. Every path is a Brownian path W on [0, T]
chopped into n steps of dt = T/n, increments dW_i = sqrt(dt) Z_i; the Euler
(Euler-Maruyama) step is S_{i+1} = S_i (1 + mu dt + sigma dW_i), and "exact"
means the closed form above, built from the SAME normals.

  C1  Exact sampling at T (one normal per path, 10^6 paths): the log-return
      log(S_T / S_0) is Gaussian with mean (mu - 1/2 sigma^2) T and variance
      sigma^2 T (skewness 0, excess kurtosis 0); E[S_T] = S_0 e^(mu T); the
      median is S_0 e^((mu - 1/2 sigma^2) T); E[log S_T] - log E[S_T] =
      -1/2 sigma^2 T -- the volatility drag as a number; and the fraction of
      paths that end below the mean is Phi(1/2 sigma sqrt T) > 1/2. The
      same for the owner's P1 case mu = 0.
  C2  Euler against exact on the same normals, the same paths read on
      n = 10^2 .. 10^6 (2.5's nested grids): the pathwise gap in log S_T has
      rms 1/2 sigma^2 T sqrt(2/n) -- it shrinks like 1/sqrt n (slope -1/2),
      strong order 1/2 -- and the relative gap in S_T is the same number.
      Euler paths know nothing of -1/2 sigma^2, and their log S_T still has
      mean (mu - 1/2 sigma^2) T, not mu T: measured on 20,000 paths at
      n = 10^4, for mu = 0.1 and for mu = 0 (P1 on Euler paths), with the
      mean and the median of S_T.
  C3  The bug: sigma Z dt instead of sigma Z sqrt(dt) in the step. The
      realised volatility of the buggy path's log-returns is sigma sqrt(dt),
      not sigma: too SMALL by a factor 1/sqrt(dt) = sqrt n (100x at
      n = 10^4), and the spread of its S_T collapses the same way.
  C4  Where the Euler gap comes from -- 2.5's lemma on its first real
      process (a = mu S != 0, b = sigma S != 1). Along the Euler path,
      log S_T - log S_0 telescopes (the left side); Taylor's second-order
      sum Sum [x_i - 1/2 x_i^2] with x_i = mu dt + sigma dW_i is the
      (dS)^2-form and leaves a remainder of order 1/n (the signed cubes
      cancel, as on 2.5); the dt-form replaces Sum (dW)^2 by T and gives
      (mu - 1/2 sigma^2) T + sigma W_T, the exact solution. So the Euler gap
      in log S IS the dt-form residual, and its leading term is
      -1/2 sigma^2 (Sum (dW_i)^2 - T): page 2.5's (dW)^2-vs-dt noise with
      g'' b^2 = -sigma^2. The identity is checked per path: gap minus that
      term has rms of order 1/n (slope -1).
  C5  Mean reversion, dX = -theta X dt + sigma dW (Ornstein-Uhlenbeck) from
      a displaced start X_0: E[X_t] = X_0 e^(-theta t) and
      Var(X_t) = sigma^2 (1 - e^(-2 theta t)) / (2 theta), which STOPS at
      sigma^2 / (2 theta), while Var(W_t) = t keeps growing on the same
      normals. Euler steps against the exact OU step on the same normals.

Paths for C2-C4 are drawn once on a grid of 10^6 steps and coarsened, so
the same path is read on n = 10^2 .. 10^6 (2.5's shape).

Run from the repository root:

    uv run experiments/2_6_sdes_and_gbm.py [--seed 20261001] [--quick]

--quick runs a tenth of the paths for the learn site's build-time snippet
check (I3): the statistical tolerances widen by the square root of the
path-count ratio so the same claims are still asserted, and NO JSON is
written -- the committed result is always the full run.

Writes 2_6_sdes_and_gbm.json beside this file: parameters in, results out,
no timestamps -- same seed, same file (I6). No plotting here; the site draws
(see experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import erf, exp, log, pi, sqrt
from pathlib import Path

import numpy as np


def Phi(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def stats(x: np.ndarray) -> dict[str, float]:
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)),
            "se_of_mean": float(x.std(ddof=1) / sqrt(x.size)),
            "rms": float(sqrt((x * x).mean())),
            "max_abs": float(np.abs(x).max())}


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


def histogram(x: np.ndarray, lo: float, hi: float, bins: int) -> dict:
    counts, edges = np.histogram(x, bins=bins, range=(lo, hi))
    return {"lo": lo, "hi": hi, "bins": bins, "counts": [int(c) for c in counts],
            "below_lo": int((x < lo).sum()), "above_hi": int((x >= hi).sum())}


# --- C1: exact sampling at T --------------------------------------------------


def exact_at_T(rng, n_paths, S0, mu, sigma, T) -> dict:
    """One normal per path: W_T = sqrt(T) Z, S_T from the closed form."""
    Z = rng.standard_normal(n_paths)
    r = (mu - 0.5 * sigma * sigma) * T + sigma * sqrt(T) * Z   # log(S_T / S_0)
    S = S0 * np.exp(r)
    m = n_paths
    r_c = r - r.mean()
    var = float(r_c.var(ddof=1))
    skew = float((r_c ** 3).mean() / var ** 1.5)
    kurt = float((r_c ** 4).mean() / var ** 2 - 3.0)
    mean_S = float(S.mean())
    med_S = float(np.median(S))
    return {
        "n_paths": m, "S0": S0, "mu": mu, "sigma": sigma, "T": T,
        "log_return": {
            "mean": float(r.mean()), "se": float(r.std(ddof=1) / sqrt(m)),
            "mean_expected": (mu - 0.5 * sigma * sigma) * T,
            "mean_if_no_drag": mu * T,
            "variance": var, "variance_se": var * sqrt(2.0 / (m - 1)),
            "variance_expected": sigma * sigma * T,
            "skewness": skew, "skewness_se": sqrt(6.0 / m), "skewness_expected": 0.0,
            "excess_kurtosis": kurt, "excess_kurtosis_se": sqrt(24.0 / m), "excess_kurtosis_expected": 0.0,
            "histogram": histogram(r, -2.0, 2.0, 80),
        },
        "S_T": {
            "mean": mean_S, "mean_se": float(S.std(ddof=1) / sqrt(m)),
            "mean_expected": S0 * exp(mu * T),
            "median": med_S,
            # the sample median of a lognormal: se = median * sigma sqrt(T) * sqrt(pi / 2) / sqrt(m)
            "median_se": S0 * exp((mu - 0.5 * sigma * sigma) * T) * sigma * sqrt(T) * sqrt(pi / 2.0) / sqrt(m),
            "median_expected": S0 * exp((mu - 0.5 * sigma * sigma) * T),
            "median_if_no_drag": S0 * exp(mu * T),
            "sd": float(S.std(ddof=1)),
            "sd_expected": S0 * exp(mu * T) * sqrt(exp(sigma * sigma * T) - 1.0),
            "fraction_below_mean": float((S < S0 * exp(mu * T)).mean()),
            "fraction_below_mean_se": sqrt(0.25 / m),
            "fraction_below_mean_expected": Phi(0.5 * sigma * sqrt(T)),
            "quantiles": {str(q): float(np.quantile(S, q)) for q in (0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)},
            "histogram": histogram(S, 0.0, 4.0 * S0, 80),
        },
        "drag": {
            "E_log_S_minus_log_E_S": float(np.log(S).mean() - log(mean_S)),
            "se": float(np.log(S).std(ddof=1) / sqrt(m)),   # the log E[S] term's noise is smaller still
            "expected": -0.5 * sigma * sigma * T,
            "note": "log of the mean minus the mean of the log: the lognormal's mean-vs-median gap, -1/2 sigma^2 T",
        },
    }


# --- C2, C3, C4: Euler against exact on nested grids --------------------------


def grid_sums(w_grid: np.ndarray, dt: float, mu: float, sigma: float, T: float) -> dict[str, np.ndarray]:
    """w_grid has shape (paths, n + 1). Per path: the Euler log S_T, the exact
    log S_T, their gap, the leading term of the gap, the Taylor sums of
    log S along the Euler path, and the buggy step's numbers."""
    d = np.diff(w_grid, axis=1)                     # dW_i = sqrt(dt) Z_i
    W_T = w_grid[:, -1].copy()                      # copy: a view would keep the whole chunk alive
    sum_dW_sq = (d * d).sum(axis=1)
    x = mu * dt + sigma * d                         # the Euler step's relative change
    step_log = np.log1p(x)                          # log(1 + x): the Euler path's log-return per step
    log_euler = step_log.sum(axis=1)                # log(S^Euler_T / S_0), telescoped
    log_exact = (mu - 0.5 * sigma * sigma) * T + sigma * W_T
    gap_log = log_euler - log_exact                 # = the dt-form residual of the lemma on the Euler path (C4)
    gap_rel = np.expm1(gap_log)                     # S^Euler_T / S^exact_T - 1
    lead = -0.5 * sigma * sigma * (sum_dW_sq - T)   # 2.5's (dW)^2-vs-dt noise, g'' b^2 = -sigma^2
    x2 = x * x
    taylor2 = (x - 0.5 * x2).sum(axis=1)            # the (dS)^2-form: Taylor of log to second order, exact sums
    cubic = (x2 * x).sum(axis=1) / 3.0              # the third-order term 1/3 Sum x^3
    r_qv = log_euler - taylor2                      # third order and beyond: 1/n
    # the bug: sigma Z dt = sigma sqrt(dt) dW_i in place of sigma dW_i
    xb = mu * dt + sigma * sqrt(dt) * d
    step_log_bug = np.log1p(xb)
    log_bug = step_log_bug.sum(axis=1)
    n = d.shape[1]
    realised_vol = np.sqrt((step_log * step_log).sum(axis=1) / T)          # of the correct path: sqrt(Sum r_i^2 / T)
    realised_vol_bug = np.sqrt((step_log_bug * step_log_bug).sum(axis=1) / T)
    # the same with the per-step mean removed: on the buggy path the drift mu dt is no longer small
    # against the noise sigma dt Z (both are dt-sized), so Sum r_i^2 picks up mu^2 too
    realised_vol_demeaned = step_log.std(axis=1, ddof=1) * sqrt(n / T)
    realised_vol_bug_demeaned = step_log_bug.std(axis=1, ddof=1) * sqrt(n / T)
    return {
        "W_T": W_T, "sum_dW_sq": sum_dW_sq,
        "log_euler": log_euler, "log_exact": log_exact,
        "gap_log": gap_log, "gap_rel": gap_rel,
        "lead": lead, "resid_lead": gap_log - lead,
        "taylor2": taylor2, "cubic": cubic, "r_qv": r_qv, "r_3": r_qv - cubic,
        "log_bug": log_bug,
        "realised_vol": realised_vol, "realised_vol_bug": realised_vol_bug,
        "realised_vol_demeaned": realised_vol_demeaned, "realised_vol_bug_demeaned": realised_vol_bug_demeaned,
    }


def coarsen(w: np.ndarray, factor: int) -> np.ndarray:
    return w[:, ::factor]


def nested_grids(rng, n_paths, n_fine, T, factors, chunk_paths, mu, sigma, keep_first):
    dt_fine = T / n_fine
    acc = {f: {} for f in factors}
    first_paths = None
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        w = np.empty((k, n_fine + 1))
        w[:, 0] = 0.0
        np.cumsum(rng.standard_normal(size=(k, n_fine)) * sqrt(dt_fine), axis=1, out=w[:, 1:])
        for f in factors:
            wg = coarsen(w, f)
            for name, arr in grid_sums(wg, dt_fine * f, mu, sigma, T).items():
                acc[f].setdefault(name, []).append(arr)
        if first_paths is None:
            # the first paths on the n = 100 grid, for the site's figure: exact, Euler and buggy S along the path
            f = max(factors)
            wg = coarsen(w, f)[:keep_first]
            dt = dt_fine * f
            t = np.arange(wg.shape[1]) * dt
            d = np.diff(wg, axis=1)
            first_paths = {
                "n": n_fine // f, "t": [float(v) for v in t],
                "paths": [{
                    "W": [float(v) for v in wg[j]],
                    "S_exact": [float(v) for v in np.exp((mu - 0.5 * sigma * sigma) * t + sigma * wg[j])],
                    "S_euler": [1.0] + [float(v) for v in np.cumprod(1.0 + mu * dt + sigma * d[j])],
                    "S_bug": [1.0] + [float(v) for v in np.cumprod(1.0 + mu * dt + sigma * sqrt(dt) * d[j])],
                } for j in range(wg.shape[0])],
                "note": "S_0 = 1 here; multiply by S0",
            }
        done += k
        print(f"[2.6] nested grids: {done:,}/{n_paths:,} paths", flush=True)
    per_n = {n_fine // f: {name: np.concatenate(parts) for name, parts in acc[f].items()} for f in factors}
    return per_n, first_paths


def summarise_grid(n, T, v, mu, sigma, keep_first) -> dict:
    dt = T / n
    first = lambda name: [float(x) for x in v[name][:keep_first]]  # noqa: E731
    return {
        "n": n, "dt": dt, "sqrt_dt": sqrt(dt), "n_paths": int(v["W_T"].size),
        "first_paths": {name: first(name) for name in
                        ("W_T", "sum_dW_sq", "log_exact", "log_euler", "gap_log", "gap_rel",
                         "lead", "resid_lead", "cubic", "r_qv", "log_bug", "realised_vol", "realised_vol_bug")},
        # C2
        "gap_log": {**stats(v["gap_log"]),
                    "rms_expected": 0.5 * sigma * sigma * T * sqrt(2.0 / n),
                    "note": "log S^Euler_T - log S^exact_T on the same normals; leading term -1/2 sigma^2 (Sum (dW)^2 - T), sd 1/2 sigma^2 T sqrt(2/n)"},
        "gap_rel": {**stats(v["gap_rel"]),
                    "rms_expected": 0.5 * sigma * sigma * T * sqrt(2.0 / n),
                    "note": "S^Euler_T / S^exact_T - 1 = e^gap_log - 1"},
        "log_euler": {"mean": float(v["log_euler"].mean()), "se_of_mean": float(v["log_euler"].std(ddof=1) / sqrt(v["log_euler"].size)),
                      "expected": (mu - 0.5 * sigma * sigma) * T, "if_no_drag": mu * T,
                      "sd": float(v["log_euler"].std(ddof=1)), "sd_expected": sigma * sqrt(T)},
        # C4
        "resid_lead": {**stats(v["resid_lead"]),
                       "note": "gap_log minus its leading term: 1/3 sigma^3 Sum (dW)^3 - mu sigma dt W_T - 1/2 mu^2 T dt - 1/4 sigma^4 Sum (dW)^4 + ...: order 1/n"},
        "r_qv": {**stats(v["r_qv"]),
                 "note": "log S^Euler_T - log S_0 - Sum [x_i - 1/2 x_i^2], x_i = mu dt + sigma dW_i: Taylor's third order and beyond along the Euler path, order 1/n"},
        "cubic": {**stats(v["cubic"]), "expected_mean_leading": mu * sigma * sigma * T * dt,
                  "sd_expected_leading": sigma ** 3 * sqrt(15.0) * T ** 1.5 / (3.0 * n),
                  "note": "1/3 Sum x_i^3: the signed cubes cancel, sd ~ sigma^3 sqrt(15) T^(3/2) / (3 n)"},
        "r_3": {**stats(v["r_3"]), "note": "fourth order and beyond: mean -3/4 sigma^4 T dt + ..., order 1/n"},
        "sum_dW_sq": {**stats(v["sum_dW_sq"]), "expected": T, "sd_expected": T * sqrt(2.0 / n)},
        # C3
        "realised_vol": {"mean": float(v["realised_vol"].mean()), "se_of_mean": float(v["realised_vol"].std(ddof=1) / sqrt(v["realised_vol"].size)),
                         "expected": sigma, "ratio_to_sigma": float(v["realised_vol"].mean() / sigma),
                         "demeaned_mean": float(v["realised_vol_demeaned"].mean()),
                         "note": "sqrt(Sum r_i^2 / T), r_i the Euler path's log-return per step; demeaned: sd(r_i) sqrt(n/T)"},
        "realised_vol_bug": {"mean": float(v["realised_vol_bug"].mean()),
                             "se_of_mean": float(v["realised_vol_bug"].std(ddof=1) / sqrt(v["realised_vol_bug"].size)),
                             "expected": sqrt(sigma * sigma + mu * mu) * sqrt(dt),
                             "demeaned_mean": float(v["realised_vol_bug_demeaned"].mean()),
                             "demeaned_se_of_mean": float(v["realised_vol_bug_demeaned"].std(ddof=1) / sqrt(v["realised_vol_bug_demeaned"].size)),
                             "demeaned_expected": sigma * sqrt(dt),
                             "ratio_to_sigma": float(v["realised_vol_bug_demeaned"].mean() / sigma),
                             "ratio_expected": sqrt(dt), "factor_too_small": float(sigma / v["realised_vol_bug_demeaned"].mean()),
                             "factor_expected": sqrt(n),
                             "note": "on the sigma Z dt path the noise per step is sigma dt Z and the drift mu dt is the same size, so "
                                     "sqrt(Sum r_i^2 / T) = sqrt(sigma^2 + mu^2) sqrt(dt) and the demeaned sd(r_i) sqrt(n/T) = sigma sqrt(dt): "
                                     "too small by 1/sqrt(dt) = sqrt n either way"},
        "log_bug": {"mean": float(v["log_bug"].mean()), "sd": float(v["log_bug"].std(ddof=1)),
                    "sd_expected": sigma * sqrt(T) * sqrt(dt), "sd_correct_expected": sigma * sqrt(T),
                    "note": "log(S^bug_T / S_0): its spread across paths collapses by the same sqrt(dt)"},
    }


# --- C2 (many paths): Euler paths know nothing of -1/2 sigma^2 ---------------


def euler_many(rng, n, T, n_paths, chunk_paths, S0, mu, sigma) -> dict:
    """20,000 Euler paths at one n: the mean and median of S_T and the mean of
    log S_T, without the closed form anywhere in the simulation."""
    dt = T / n
    log_T, W_T = [], []
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        d = rng.standard_normal(size=(k, n)) * sqrt(dt)
        log_T.append(np.log1p(mu * dt + sigma * d).sum(axis=1))
        W_T.append(d.sum(axis=1))
        done += k
    log_T = np.concatenate(log_T)
    W_T = np.concatenate(W_T)
    S = S0 * np.exp(log_T)
    m = S.size
    return {
        "n": n, "dt": dt, "n_paths": int(m), "S0": S0, "mu": mu, "sigma": sigma, "T": T,
        "log_S_T_minus_log_S0": {"mean": float(log_T.mean()), "se": float(log_T.std(ddof=1) / sqrt(m)),
                                 "expected": (mu - 0.5 * sigma * sigma) * T, "if_no_drag": mu * T,
                                 "sd": float(log_T.std(ddof=1)), "sd_expected": sigma * sqrt(T)},
        "S_T": {"mean": float(S.mean()), "mean_se": float(S.std(ddof=1) / sqrt(m)),
                "mean_expected": S0 * exp(mu * T),
                "mean_expected_on_grid": S0 * (1.0 + mu * dt) ** n,
                "median": float(np.median(S)),
                "median_se": S0 * exp((mu - 0.5 * sigma * sigma) * T) * sigma * sqrt(T) * sqrt(pi / 2.0) / sqrt(m),
                "median_expected": S0 * exp((mu - 0.5 * sigma * sigma) * T),
                "median_if_no_drag": S0 * exp(mu * T),
                "fraction_below_mean": float((S < S0 * exp(mu * T)).mean()),
                "fraction_below_mean_se": sqrt(0.25 / m),
                "fraction_below_mean_expected": Phi(0.5 * sigma * sqrt(T)),
                "histogram": histogram(S, 0.0, 4.0 * S0, 80)},
        "gap_to_exact_on_same_normals": {**stats(log_T - ((mu - 0.5 * sigma * sigma) * T + sigma * W_T)),
                                         "rms_expected": 0.5 * sigma * sigma * T * sqrt(2.0 / n)},
    }


# --- C5: Ornstein-Uhlenbeck ----------------------------------------------------


def ou(rng, n, T, n_paths, theta, sigma, X0, checkpoints) -> dict:
    """Euler and the exact OU step on the same normals, step by step over all
    paths at once; W on the same normals for the contrast."""
    dt = T / n
    k_pts = {int(round(c * n)): c * T for c in checkpoints}
    xe = np.full(n_paths, X0)                       # Euler
    xx = np.full(n_paths, X0)                       # exact step
    w = np.zeros(n_paths)
    a = exp(-theta * dt)
    s_exact = sigma * sqrt((1.0 - a * a) / (2.0 * theta))
    rows = []
    for i in range(1, n + 1):
        z = rng.standard_normal(n_paths)
        xe = xe + (-theta * xe) * dt + sigma * sqrt(dt) * z
        xx = a * xx + s_exact * z
        w = w + sqrt(dt) * z
        if i in k_pts:
            t = k_pts[i]
            var_lim = sigma * sigma / (2.0 * theta)
            rows.append({
                "t": t,
                "mean": {"euler": float(xe.mean()), "exact_step": float(xx.mean()),
                         "se": float(xe.std(ddof=1) / sqrt(n_paths)), "expected": X0 * exp(-theta * t)},
                "var": {"euler": float(xe.var(ddof=1)), "exact_step": float(xx.var(ddof=1)),
                        "se": float(xe.var(ddof=1) * sqrt(2.0 / (n_paths - 1))),
                        "expected": var_lim * (1.0 - exp(-2.0 * theta * t)),
                        "limit": var_lim,
                        "if_like_W": t},
                "var_W": {"measured": float(w.var(ddof=1)), "se": float(w.var(ddof=1) * sqrt(2.0 / (n_paths - 1))), "expected": t},
                "euler_minus_exact_step": stats(xe - xx),
            })
    return {
        "n": n, "dt": dt, "n_paths": n_paths, "theta": theta, "sigma": sigma, "X0": X0, "T": T,
        "var_limit": sigma * sigma / (2.0 * theta),
        "half_life": log(2.0) / theta,
        "checkpoints": rows,
        "note": "dX = -theta X dt + sigma dW; exact step X_{i+1} = e^(-theta dt) X_i + sigma sqrt((1 - e^(-2 theta dt)) / (2 theta)) Z_i",
    }


# --- checks -------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []
    T = params["T"]
    sigma = params["sigma"]
    mu = params["mu"]
    slack = sqrt(1000 / params["nested_grids"]["n_paths"])

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    for label, e in (("mu=0.1", res["exact"]), ("P1 case mu=0", res["exact_p1"])):
        lr, S, dr = e["log_return"], e["S_T"], e["drag"]
        m = e["n_paths"]
        add(f"C1 {label} ({m:,} paths): log-return mean is (mu - 1/2 sigma^2) T (within 5 s.e.)", lr["mean"], lr["mean_expected"], 5 * lr["se"])
        add(f"C1 {label}: log-return mean is NOT mu T (more than 5 s.e. away)", float(abs(lr["mean"] - lr["mean_if_no_drag"]) > 5 * lr["se"]), 1.0, 0.0)
        add(f"C1 {label}: log-return variance is sigma^2 T (within 5 s.e.)", lr["variance"], lr["variance_expected"], 5 * lr["variance_se"])
        add(f"C1 {label}: log-return skewness is 0 (within 5 s.e.)", lr["skewness"], 0.0, 5 * lr["skewness_se"])
        add(f"C1 {label}: log-return excess kurtosis is 0 (within 5 s.e.) -- Gaussian", lr["excess_kurtosis"], 0.0, 5 * lr["excess_kurtosis_se"])
        add(f"C1 {label}: E[S_T] = S0 e^(mu T) (within 5 s.e.)", S["mean"], S["mean_expected"], 5 * S["mean_se"])
        add(f"C1 {label}: median S_T = S0 e^((mu - 1/2 sigma^2) T) (within 5 s.e.)", S["median"], S["median_expected"], 5 * S["median_se"])
        add(f"C1 {label}: median S_T is NOT S0 e^(mu T) (more than 5 s.e. away)", float(abs(S["median"] - S["median_if_no_drag"]) > 5 * S["median_se"]), 1.0, 0.0)
        add(f"C1 {label}: sd of S_T is S0 e^(mu T) sqrt(e^(sigma^2 T) - 1) (to 3 %)", S["sd"], S["sd_expected"], 0.03 * sqrt(1_000_000 / m), "rel")
        add(f"C1 {label}: fraction of paths below the mean is Phi(1/2 sigma sqrt T) (within 5 s.e.)", S["fraction_below_mean"], S["fraction_below_mean_expected"], 5 * S["fraction_below_mean_se"])
        add(f"C1 {label}: E[log S_T] - log E[S_T] = -1/2 sigma^2 T, the drag (within 5 s.e.)", dr["E_log_S_minus_log_E_S"], dr["expected"], 5 * dr["se"])

    ns = [g["n"] for g in res["grids"]]
    for g in res["grids"]:
        n = g["n"]
        add(f"C2 n={n:.0e}: Euler-vs-exact gap in log S_T has rms 1/2 sigma^2 T sqrt(2/n) (to 15 %)", g["gap_log"]["rms"], g["gap_log"]["rms_expected"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: relative gap in S_T has the same rms (to 15 %)", g["gap_rel"]["rms"], g["gap_rel"]["rms_expected"], 0.15 * slack, "rel")
        add(f"C2 n={n:.0e}: the gap has mean 0 (within 5 s.e.; the true mean is O(dt))", g["gap_log"]["mean"], 0.0, 5 * g["gap_log"]["se_of_mean"])
        add(f"C2 n={n:.0e}: Euler log S_T has mean (mu - 1/2 sigma^2) T (within 5 s.e.)", g["log_euler"]["mean"], g["log_euler"]["expected"], 5 * g["log_euler"]["se_of_mean"])
        add(f"C3 n={n:.0e}: realised volatility of the correct path is sigma (to 2 %)", g["realised_vol"]["ratio_to_sigma"], 1.0, 0.02 * slack)
        add(f"C3 n={n:.0e}: realised volatility of the sigma Z dt path (demeaned) is sigma sqrt(dt) -- too small by sqrt n (to 2 %)", g["realised_vol_bug"]["ratio_to_sigma"], g["realised_vol_bug"]["ratio_expected"], 0.02 * slack, "rel")
        add(f"C3 n={n:.0e}: realised volatility of the sigma Z dt path (sum of squares) is sqrt(sigma^2 + mu^2) sqrt(dt): the drift is now noise-sized (to 2 %)", g["realised_vol_bug"]["mean"], g["realised_vol_bug"]["expected"], 0.02 * slack, "rel")
        add(f"C3 n={n:.0e}: sd of log S^bug_T across paths is sigma sqrt(T) sqrt(dt) (to 15 %)", g["log_bug"]["sd"], g["log_bug"]["sd_expected"], 0.15 * slack, "rel")
        add(f"C4 n={n:.0e}: gap minus its leading term -1/2 sigma^2 (Sum (dW)^2 - T) is smaller than the gap (ratio < 2/sqrt n)", g["resid_lead"]["rms"] / g["gap_log"]["rms"], 0.0, 2.0 / sqrt(n))
        add(f"C4 n={n:.0e}: the (dS)^2-form (Taylor to second order along the Euler path) leaves a remainder smaller than the gap (ratio < 2/sqrt n)", g["r_qv"]["rms"] / g["gap_log"]["rms"], 0.0, 2.0 / sqrt(n))
        add(f"C4 n={n:.0e}: the third-order term 1/3 Sum x^3 has sd sigma^3 sqrt(15) T^(3/2) / (3 n) (to 15 %)", g["cubic"]["sd"], g["cubic"]["sd_expected_leading"], 0.15 * slack, "rel")
        add(f"C4 n={n:.0e}: Sum (dW)^2 has sd T sqrt(2/n) (2.3's number, to 15 %)", g["sum_dW_sq"]["sd"], g["sum_dW_sq"]["sd_expected"], 0.15 * slack, "rel")
    s = res["slopes"]
    add("C2: log-log slope of rms(gap in log S_T) vs n is -1/2 -- strong order 1/2", s["rms_gap_log"], -0.5, 0.03 * slack)
    add("C2: log-log slope of rms(relative gap in S_T) vs n is -1/2", s["rms_gap_rel"], -0.5, 0.03 * slack)
    add("C4: log-log slope of rms(gap minus leading term) vs n is -1", s["rms_resid_lead"], -1.0, 0.05 * slack)
    add("C4: log-log slope of rms((dS)^2-form remainder) vs n is -1", s["rms_r_qv"], -1.0, 0.05 * slack)
    add("C3: log-log slope of the buggy path's realised volatility vs n is -1/2", s["realised_vol_bug"], -0.5, 0.01 * slack)

    for label, e in (("mu=0.1", res["euler_many"]), ("P1 case mu=0", res["euler_many_p1"])):
        lr, S = e["log_S_T_minus_log_S0"], e["S_T"]
        add(f"C2 Euler {label} ({e['n_paths']:,} paths, n={e['n']:.0e}): mean log S_T is (mu - 1/2 sigma^2) T (within 5 s.e.) -- the -1/2 sigma^2 emerges", lr["mean"], lr["expected"], 5 * lr["se"])
        add(f"C2 Euler {label}: mean log S_T is NOT mu T (more than 5 s.e. away)", float(abs(lr["mean"] - lr["if_no_drag"]) > 5 * lr["se"]), 1.0, 0.0)
        add(f"C2 Euler {label}: E[S_T] = S0 e^(mu T) (within 5 s.e.)", S["mean"], S["mean_expected"], 5 * S["mean_se"])
        add(f"C2 Euler {label}: median S_T = S0 e^((mu - 1/2 sigma^2) T) (within 5 s.e.)", S["median"], S["median_expected"], 5 * S["median_se"])
        add(f"C2 Euler {label}: fraction of paths below the mean is Phi(1/2 sigma sqrt T) (within 5 s.e.)", S["fraction_below_mean"], S["fraction_below_mean_expected"], 5 * S["fraction_below_mean_se"])
        add(f"C2 Euler {label}: gap to the exact solution on the same normals has rms 1/2 sigma^2 T sqrt(2/n) (to 15 %)",
            e["gap_to_exact_on_same_normals"]["rms"], e["gap_to_exact_on_same_normals"]["rms_expected"], 0.15 * sqrt(20_000 / e["n_paths"]), "rel")

    o = res["ou"]
    for r in o["checkpoints"]:
        t = r["t"]
        add(f"C5 OU t={t:.2f}: E[X_t] = X0 e^(-theta t) (within 5 s.e.)", r["mean"]["euler"], r["mean"]["expected"], 5 * r["mean"]["se"])
        add(f"C5 OU t={t:.2f}: Var(X_t) = sigma^2 (1 - e^(-2 theta t)) / (2 theta) (within 5 s.e.)", r["var"]["euler"], r["var"]["expected"], 5 * r["var"]["se"])
        add(f"C5 OU t={t:.2f}: Var(W_t) = t on the same normals (within 5 s.e.)", r["var_W"]["measured"], r["var_W"]["expected"], 5 * r["var_W"]["se"])
        add(f"C5 OU t={t:.2f}: Var(X_t) is NOT t (more than 5 s.e. away)", float(abs(r["var"]["euler"] - t) > 5 * r["var"]["se"]), 1.0, 0.0)
    last = o["checkpoints"][-1]
    add("C5 OU at T: Var(X_T) is within 5 s.e. of the limit sigma^2 / (2 theta) -- it has stopped", last["var"]["euler"], last["var"]["limit"], 5 * last["var"]["se"])
    add("C5 OU at T: Euler and the exact step agree to 1 % rms on the same normals", last["euler_minus_exact_step"]["rms"] / sqrt(last["var"]["limit"]), 0.0, 0.01)
    return checks


# --- main ---------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the paths, wider tolerances, no JSON written")
    args = parser.parse_args()

    q = args.quick
    params = {
        "seed": args.seed,
        "T": 1.0, "S0": 100.0, "mu": 0.10, "sigma": 0.40,
        "model": "dS = mu S dt + sigma S dW (drift first); Euler step S_{i+1} = S_i (1 + mu dt + sigma dW_i); exact S_T = S0 exp((mu - 1/2 sigma^2) T + sigma W_T)",
        "exact": {"n_paths": 100_000 if q else 1_000_000},
        "nested_grids": {
            "n_fine": 1_000_000,
            "coarsen_by": [10_000, 1_000, 100, 10, 1],   # n = 10^2, 10^3, 10^4, 10^5, 10^6
            "n_paths": 100 if q else 1000,
            "chunk_paths": 10,        # memory only: draws are consumed row by row, so the paths do not depend on it
            "keep_first_paths": 5,
        },
        "euler_many": {"n": 10_000, "n_paths": 2_000 if q else 20_000, "chunk_paths": 500},
        "ou": {"theta": 2.0, "sigma": 0.40, "X0": 1.0, "n": 10_000, "n_paths": 2_000 if q else 20_000,
               "checkpoints": [0.1, 0.25, 0.5, 0.75, 1.0]},
        "p1_case": {"mu": 0.0, "note": "the owner's P1 as posed: mu = 0, sigma = 0.4, T = 1"},
    }
    T, S0, mu, sigma = params["T"], params["S0"], params["mu"], params["sigma"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    print("[2.6] exact sampling at T", flush=True)
    exact = exact_at_T(rng, params["exact"]["n_paths"], S0, mu, sigma, T)
    exact_p1 = exact_at_T(rng, params["exact"]["n_paths"], S0, params["p1_case"]["mu"], sigma, T)

    g = params["nested_grids"]
    per_n, first_paths = nested_grids(rng, g["n_paths"], g["n_fine"], T, g["coarsen_by"], g["chunk_paths"], mu, sigma, g["keep_first_paths"])
    grids = [summarise_grid(n, T, per_n[n], mu, sigma, g["keep_first_paths"]) for n in sorted(per_n)]
    ns = [x["n"] for x in grids]

    e = params["euler_many"]
    print(f"[2.6] Euler, many paths: {e['n_paths']:,} at n={e['n']:,}, mu = {mu} and mu = 0", flush=True)
    em = euler_many(rng, e["n"], T, e["n_paths"], e["chunk_paths"], S0, mu, sigma)
    em_p1 = euler_many(rng, e["n"], T, e["n_paths"], e["chunk_paths"], S0, params["p1_case"]["mu"], sigma)

    o = params["ou"]
    print(f"[2.6] OU: {o['n_paths']:,} paths at n={o['n']:,}", flush=True)
    ou_res = ou(rng, o["n"], T, o["n_paths"], o["theta"], o["sigma"], o["X0"], o["checkpoints"])

    slopes = {
        "rms_gap_log": loglog_slope(ns, [x["gap_log"]["rms"] for x in grids]),
        "rms_gap_rel": loglog_slope(ns, [x["gap_rel"]["rms"] for x in grids]),
        "rms_resid_lead": loglog_slope(ns, [x["resid_lead"]["rms"] for x in grids]),
        "rms_r_qv": loglog_slope(ns, [x["r_qv"]["rms"] for x in grids]),
        "sd_cubic": loglog_slope(ns, [x["cubic"]["sd"] for x in grids]),
        "realised_vol_bug": loglog_slope(ns, [x["realised_vol_bug"]["mean"] for x in grids]),
        "sd_log_bug": loglog_slope(ns, [x["log_bug"]["sd"] for x in grids]),
    }

    results = {"exact": exact, "exact_p1": exact_p1, "grids": grids, "first_paths_n100": first_paths,
               "euler_many": em, "euler_many_p1": em_p1, "ou": ou_res, "slopes": slopes}
    checks = build_checks(results, params)

    out = {
        "page": "2.6",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": results,
        "checks": checks,
    }
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.6] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  "
              f"({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.6] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
