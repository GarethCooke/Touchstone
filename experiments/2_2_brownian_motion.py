"""Brownian motion — the experiment behind page 2.2.

Serves page 2.2 (docs/quant-learn-index-v1.md). W is the 2.1 walk with
sqrt(dt)-sized Gaussian steps, W_t = sum sqrt(dt) * Z_i, on a grid of step dt.
Four claims, each measured:

  C1  Independent Gaussian increments: W_t - W_s ~ N(0, t - s).
      Measured as: over lags of 1, 10, 100 and 250 steps, the increments have
      mean 0, variance equal to the lag in time (NOT sd equal to the lag, and
      NOT sd = sqrt(t) - sqrt(s)), zero skew, zero excess kurtosis, Gaussian
      tail fractions beyond 1, 2 and 3 sd, and consecutive non-overlapping
      increments are uncorrelated. A walk built from +-1 coin steps has the
      same mean, variance and independence at every lag, and its shape
      converges to the Gaussian at a measured rate: excess kurtosis exactly
      -2/k over k steps (-2 for one step, -0.008 over 250). The Gaussian is
      what the limit produces, whatever the coin (2.1's C4, one page on).
  C2  Continuous but nowhere differentiable. Over a window h the increment
      W_(t+h) - W_t shrinks like sqrt(h) (continuity: the path has no jumps)
      while the difference quotient (W_(t+h) - W_t) / h GROWS like 1/sqrt(h).
      Measured as: log-log slope of mean |dW| against h is +0.5; log-log slope
      of mean |dW/h| against h is -0.5; the secant slope at a fixed point of a
      single path is reported at each h so the reader can watch it not settle.
  C3  Self-similar: {sqrt(c) * W_(t/c)} is again a Brownian motion. Zooming
      into the first 1/c of a path and stretching time by c needs the vertical
      axis stretched by sqrt(c) -- not c, not 1.
      Measured as: variance of sqrt(c) * W_(1/c) is 1 for c = 4, 10, 100, with
      the same skew and kurtosis as W_1; the wrong stretches give c and 1/c.
  C4  Martingale and Markov. E[W_t | W_s] = W_s and Var(W_t | W_s) = t - s;
      given W_s, the earlier value W_r adds nothing.
      Measured as: regressing W_2 on W_1 gives slope 1, intercept 0, residual
      variance 1; among paths with W_1 in [1.4, 1.6], W_2 has mean 1.5 and
      sd 1 (not sqrt 2); adding W_0.5 as a regressor gets a coefficient of 0;
      paths that rose over [0, 1] show no momentum over [1, 2].

Run from the repository root:

    uv run experiments/2_2_brownian_motion.py [--seed 20260903]

Writes 2_2_brownian_motion.json beside this file: parameters in, results
out, no timestamps -- same seed, same file (I6). No plotting here; the site
draws (see experiments/README.md; the zoom is demo D1). Exits non-zero if
any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import erfc, sqrt
from pathlib import Path

import numpy as np

# Gaussian tail fractions P(|Z| > k) for k = 1, 2, 3 -- the shape C1 tests against.
GAUSSIAN_TAILS = {k: erfc(k / sqrt(2.0)) for k in (1, 2, 3)}


# --- step distributions (2.1's two coins) ----------------------------------


def gaussian_steps(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    return rng.standard_normal(size=shape)


def coin_steps(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    return (rng.integers(0, 2, size=shape, dtype=np.int8) * 2 - 1).astype(np.float64)


SAMPLERS = {"gaussian": gaussian_steps, "coin": coin_steps}


# --- running moments, accumulated chunk by chunk ---------------------------


class Moments:
    """Sums of x^1..x^4 and tail counts, so an ensemble too big to hold can
    still report mean, variance, skew, excess kurtosis and tail fractions."""

    def __init__(self) -> None:
        self.n = 0
        self.s = np.zeros(4)
        self.tails = {1: 0, 2: 0, 3: 0}

    def add(self, x: np.ndarray, sd_expected: float) -> None:
        x = x.ravel()
        self.n += x.size
        self.s += [x.sum(), (x**2).sum(), (x**3).sum(), (x**4).sum()]
        a = np.abs(x)
        for k in self.tails:
            self.tails[k] += int((a > k * sd_expected).sum())

    def summary(self) -> dict:
        n = self.n
        m1 = self.s[0] / n
        m2 = self.s[1] / n - m1**2
        m3 = self.s[2] / n - 3 * m1 * self.s[1] / n + 2 * m1**3
        m4 = (self.s[3] / n - 4 * m1 * self.s[2] / n
              + 6 * m1**2 * self.s[1] / n - 3 * m1**4)
        return {
            "n": n,
            "mean": float(m1),
            "var": float(m2),
            "skew": float(m3 / m2**1.5),
            "excess_kurtosis": float(m4 / m2**2 - 3.0),
            "tail_fraction_beyond_k_sd": {str(k): c / n for k, c in self.tails.items()},
        }


# --- the ensemble: W on [0, T], observed at a few times ----------------------


def run_ensemble(rng, sampler, n_paths, n_steps, dt, lags, times, chunk_paths):
    """Simulate paths in chunks; keep only the increment moments per lag, the
    lag-1 correlation of consecutive increments, and W at the named times."""
    sqrt_dt = sqrt(dt)
    inc = {lag: Moments() for lag in lags}
    corr_sums = {lag: np.zeros(3) for lag in lags}  # sum xy, sum x^2, sum y^2
    idx = {name: round(t / dt) for name, t in times.items()}
    at = {name: [] for name in times}

    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        w = np.empty((k, n_steps + 1))
        w[:, 0] = 0.0
        np.cumsum(sampler(rng, (k, n_steps)) * sqrt_dt, axis=1, out=w[:, 1:])
        for lag in lags:
            d = w[:, lag::lag] - w[:, :-lag:lag]       # non-overlapping increments
            inc[lag].add(d, sqrt(lag * dt))
            x, y = d[:, :-1].ravel(), d[:, 1:].ravel()  # consecutive pairs
            corr_sums[lag] += [(x * y).sum(), (x * x).sum(), (y * y).sum()]
        for name, i in idx.items():
            at[name].append(w[:, i].copy())
        done += k

    increments = {}
    for lag in lags:
        s = inc[lag].summary()
        s["lag_steps"] = lag
        s["lag_time"] = lag * dt
        s["var_expected"] = lag * dt
        xy, xx, yy = corr_sums[lag]
        s["consecutive_correlation"] = float(xy / sqrt(xx * yy))
        increments[str(lag)] = s
    return increments, {name: np.concatenate(v) for name, v in at.items()}


# --- C2: one fine path at a time -------------------------------------------


def roughness(rng, n_paths, fine_dt, hs, t_probe):
    """Paths on a grid of step fine_dt over [0, 1]. For each window h (a
    multiple of fine_dt): mean |dW| over all non-overlapping windows, the
    largest |dW| seen (continuity), and mean |dW/h|. Also the secant slope
    at t_probe for the FIRST path alone, at each h -- the demo's story."""
    n_steps = round(1.0 / fine_dt)
    sums = {h: np.zeros(2) for h in hs}      # sum |dW|, count
    maxabs = {h: 0.0 for h in hs}
    secant_first_path = {}
    for p in range(n_paths):
        w = np.concatenate([[0.0], np.cumsum(rng.standard_normal(n_steps) * sqrt(fine_dt))])
        for h in hs:
            m = round(h / fine_dt)
            d = np.abs(w[m::m] - w[:-m:m])
            sums[h] += [d.sum(), d.size]
            maxabs[h] = max(maxabs[h], float(d.max()))
            if p == 0:
                i = round(t_probe / fine_dt)
                secant_first_path[str(h)] = float((w[i + m] - w[i]) / h)
    rows = []
    for h in hs:
        mean_abs = sums[h][0] / sums[h][1]
        rows.append({
            "h": h,
            "mean_abs_increment": float(mean_abs),
            "mean_abs_increment_over_sqrt_h": float(mean_abs / sqrt(h)),
            "max_abs_increment": maxabs[h],
            "mean_abs_slope": float(mean_abs / h),
            "secant_slope_first_path_at_t": secant_first_path[str(h)],
        })
    return rows


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


# --- C3 and C4 from the stored times ----------------------------------------


def self_similarity(at, zooms):
    w1 = at["1"]
    base = {"var": float(w1.var(ddof=1)),
            "skew": float(((w1 - w1.mean())**3).mean() / w1.std()**3),
            "excess_kurtosis": float(((w1 - w1.mean())**4).mean() / w1.std()**4 - 3)}
    rows = []
    for c in zooms:
        x = at[f"1/{c}"]
        rescaled = sqrt(c) * x
        rows.append({
            "zoom": c,
            "var_W_at_1_over_c": float(x.var(ddof=1)),
            "var_rescaled_sqrt_c": float(rescaled.var(ddof=1)),
            "var_if_stretched_by_c": float((c * x).var(ddof=1)),
            "var_if_not_stretched": float(x.var(ddof=1)),
            "skew_rescaled": float(((rescaled - rescaled.mean())**3).mean() / rescaled.std()**3),
            "excess_kurtosis_rescaled": float(((rescaled - rescaled.mean())**4).mean() / rescaled.std()**4 - 3),
        })
    return {"W_at_1": base, "zooms": rows}


def martingale_markov(at, cond_centre, cond_half_width):
    w_r, w_s, w_t = at["0.5"], at["1"], at["2"]
    # W_2 on W_1
    slope, intercept = np.polyfit(w_s, w_t, 1)
    resid = w_t - (slope * w_s + intercept)
    # W_2 on W_1 and W_0.5 -- Markov: the earlier point earns a zero coefficient
    X = np.column_stack([w_s, w_r, np.ones_like(w_s)])
    coef, *_ = np.linalg.lstsq(X, w_t, rcond=None)
    # the owner's question: paths at W_1 ~ 1.5
    sel = np.abs(w_s - cond_centre) <= cond_half_width
    cond = w_t[sel]
    # momentum: paths that rose over [0,1]
    up = w_s > 0
    return {
        "regress_W2_on_W1": {"slope": float(slope), "intercept": float(intercept),
                              "residual_var": float(resid.var(ddof=2)),
                              "residual_var_expected": 1.0},
        "regress_W2_on_W1_and_W05": {"coef_W1": float(coef[0]), "coef_W05": float(coef[1]),
                                     "intercept": float(coef[2])},
        "conditional_on_W1": {"window": [cond_centre - cond_half_width, cond_centre + cond_half_width],
                              "n_paths": int(sel.sum()),
                              "mean_W1_in_window": float(w_s[sel].mean()),
                              "mean_W2": float(cond.mean()),
                              "sd_W2": float(cond.std(ddof=1)),
                              "sd_W2_expected": 1.0,
                              "sd_W2_unconditional": float(w_t.std(ddof=1))},
        "momentum": {"n_paths_up_over_0_1": int(up.sum()),
                     "mean_increment_1_to_2_given_up": float((w_t - w_s)[up].mean()),
                     "mean_increment_1_to_2_given_down": float((w_t - w_s)[~up].mean())},
    }


# --- checks ----------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": tol, "mode": mode, "pass": bool(ok)})

    for walk in ("gaussian", "coin"):
        inc = res["increments"][walk]
        for lag, s in inc.items():
            tag = f"C1 {walk} lag {s['lag_time']:g}"
            add(f"{tag}: variance = lag in time", s["var"], s["var_expected"], 0.02, "rel")
            add(f"{tag}: |mean| within 5 s.e. of 0", abs(s["mean"]),
                0.0, 5 * sqrt(s["var_expected"] / s["n"]))
            add(f"{tag}: skew 0", s["skew"], 0.0, 0.03)
            add(f"{tag}: consecutive increments uncorrelated",
                s["consecutive_correlation"], 0.0, 0.01)
            if walk == "gaussian":
                add(f"{tag}: excess kurtosis 0", s["excess_kurtosis"], 0.0, 0.05)
                for k in ("1", "2", "3"):
                    add(f"{tag}: tail fraction beyond {k} sd is Gaussian",
                        s["tail_fraction_beyond_k_sd"][k], GAUSSIAN_TAILS[int(k)], 0.05, "rel")
            else:
                # A k-step coin increment is a scaled binomial: excess kurtosis
                # exactly -2/k, so the Gaussian shape arrives at rate 1/k. Tail
                # fractions are not checked for the coin: its increments sit on
                # a lattice and "beyond exactly 1 sd" falls between lattice
                # points (the JSON still reports them).
                add(f"{tag}: excess kurtosis is -2/k (CLT at rate 1/k)",
                    s["excess_kurtosis"], -2.0 / int(lag), 0.02)

    r = res["roughness"]
    hs = [row["h"] for row in r["rows"]]
    add("C2: log-log slope of mean |dW| vs h is +0.5 (continuity)",
        r["loglog_slope_mean_abs_increment"], 0.5, 0.01)
    add("C2: log-log slope of mean |dW/h| vs h is -0.5 (no derivative)",
        r["loglog_slope_mean_abs_slope"], -0.5, 0.01)
    add(f"C2: largest single increment at h={hs[-1]:g} is small (continuity, no jumps)",
        r["rows"][-1]["max_abs_increment"], 0.0, 10 * sqrt(hs[-1]))

    for row in res["self_similarity"]["zooms"]:
        c = row["zoom"]
        add(f"C3 zoom {c}: var of sqrt(c)*W(1/c) is 1", row["var_rescaled_sqrt_c"], 1.0, 0.03)
        add(f"C3 zoom {c}: excess kurtosis of rescaled is 0", row["excess_kurtosis_rescaled"], 0.0, 0.1)

    m = res["martingale_markov"]
    add("C4: slope of W2 on W1 is 1", m["regress_W2_on_W1"]["slope"], 1.0, 0.02)
    add("C4: intercept of W2 on W1 is 0", m["regress_W2_on_W1"]["intercept"], 0.0, 0.02)
    add("C4: residual variance of W2 given W1 is 1 (= 2 - 1)",
        m["regress_W2_on_W1"]["residual_var"], 1.0, 0.03)
    add("C4 Markov: coefficient on W0.5 given W1 is 0",
        m["regress_W2_on_W1_and_W05"]["coef_W05"], 0.0, 0.02)
    c = m["conditional_on_W1"]
    n = c["n_paths"]
    add("C4: mean W2 given W1 ~ 1.5 is 1.5 (within 4 s.e.)",
        c["mean_W2"], c["mean_W1_in_window"], 4 / sqrt(n))
    add("C4: sd of W2 given W1 ~ 1.5 is 1, not sqrt 2", c["sd_W2"], 1.0, 4 / sqrt(2 * n))
    add("C4: no momentum -- mean increment over [1,2] given a rise over [0,1] is 0",
        m["momentum"]["mean_increment_1_to_2_given_up"], 0.0,
        5 / sqrt(m["momentum"]["n_paths_up_over_0_1"]))
    return checks


# --- main ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20260903)
    args = parser.parse_args()

    params = {
        "seed": args.seed,
        "ensemble": {
            "T": 2.0, "n_steps": 2000, "dt": 0.001, "n_paths": 40_000,
            "chunk_paths": 2_000,  # affects draw order, so it is part of the inputs
            "lags_steps": [1, 10, 100, 250],
            "times": {"0.5": 0.5, "1": 1.0, "2": 2.0, "1/4": 0.25, "1/10": 0.1, "1/100": 0.01},
            "step_distributions": ["gaussian", "coin"],
        },
        "roughness": {"n_paths": 100, "fine_dt": 1e-6, "T": 1.0,
                      "hs": [0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001],
                      "t_probe": 0.5},
        "self_similarity": {"zooms": [4, 10, 100]},
        "conditional": {"W1_centre": 1.5, "half_width": 0.1},
    }

    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()
    e = params["ensemble"]

    increments, at = {}, {}
    for name in e["step_distributions"]:
        print(f"[2.2] {name} ensemble: {e['n_paths']:,} paths x {e['n_steps']:,} steps ...", flush=True)
        increments[name], at[name] = run_ensemble(
            rng, SAMPLERS[name], e["n_paths"], e["n_steps"], e["dt"],
            e["lags_steps"], e["times"], e["chunk_paths"])

    r = params["roughness"]
    print(f"[2.2] roughness: {r['n_paths']} paths at dt={r['fine_dt']:g} ...", flush=True)
    rows = roughness(rng, r["n_paths"], r["fine_dt"], r["hs"], r["t_probe"])
    hs = [row["h"] for row in rows]
    rough = {
        "rows": rows,
        "loglog_slope_mean_abs_increment": loglog_slope(hs, [x["mean_abs_increment"] for x in rows]),
        "loglog_slope_mean_abs_slope": loglog_slope(hs, [x["mean_abs_slope"] for x in rows]),
    }

    results = {
        "increments": increments,
        "sd_if_it_subtracted_sqrt_0_5_minus_sqrt_0_25": sqrt(0.5) - sqrt(0.25),
        "gaussian_tail_fractions": {str(k): v for k, v in GAUSSIAN_TAILS.items()},
        "roughness": rough,
        "self_similarity": self_similarity(at["gaussian"], params["self_similarity"]["zooms"]),
        "martingale_markov": martingale_markov(
            at["gaussian"], params["conditional"]["W1_centre"], params["conditional"]["half_width"]),
    }
    checks = build_checks(results, params)

    out = {
        "page": "2.2",
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
    print(f"[2.2] wrote {out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
