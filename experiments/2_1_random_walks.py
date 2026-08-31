"""Random walks and scaling — the experiment behind page 2.1.

Serves page 2.1 (docs/quant-learn-index-v1.md). Four claims, each measured:

  C1  Variance adds across independent steps: Var(S_n) = n * Var(step).
      Measured as: log-log slope of Var(S_n) against n is 1.
  C2  Standard deviation does not add: sd(S_n) = sd(step) * sqrt(n), and the
      mean absolute distance E|S_n| grows like sqrt(n), not linearly.
      Measured as: log-log slope of E|S_n| against n is 0.5, E|S_n|/n falls
      as n grows, and at large n E|S_n| / (sd(step) * sqrt(n)) approaches
      sqrt(2/pi) = 0.7979...
  C3  Only sqrt(dt)-sized steps survive the continuous limit. A walk across
      [0, 1] in n = 1/dt steps of size dt^alpha has
      Var(S_1) = n * dt^(2*alpha) = dt^(2*alpha - 1):
      -> 0 for alpha > 1/2, exactly 1 at alpha = 1/2, -> infinity below.
  C4  None of it depends on the coin: Gaussian steps of the same variance
      give the same slopes. Independence and finite variance are all that
      is used.

Run from the repository root:

    uv run experiments/2_1_random_walks.py [--seed 20260830]

Writes 2_1_random_walks.json beside this file: parameters in, results out,
no timestamps — same seed, same file (I6). No plotting here; the site draws
(see experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

SQRT_2_OVER_PI = float(np.sqrt(2.0 / np.pi))


# --- step distributions ----------------------------------------------------


def coin_steps(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    """Fair coin: +1 or -1, equally likely. Mean 0, variance 1."""
    return rng.integers(0, 2, size=shape, dtype=np.int8) * 2 - 1


def gaussian_steps(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    """Standard normal steps. Same mean 0 and variance 1, no coin anywhere."""
    return rng.standard_normal(size=shape, dtype=np.float32)


SAMPLERS = {"coin": coin_steps, "gaussian": gaussian_steps}


# --- the walk, observed at checkpoints -------------------------------------


def positions_at_checkpoints(
    rng: np.random.Generator,
    sampler,
    n_paths: int,
    checkpoints: list[int],
    chunk_paths: int,
) -> dict[int, np.ndarray]:
    """S_m for every path, at each checkpoint m.

    A walk observed at step m is a length-m walk, so one ensemble serves all
    the checkpoints. Paths are simulated in chunks, each chunk in segments
    (checkpoint to checkpoint); only the running sum is kept, so no full path
    is ever stored.
    """
    assert checkpoints == sorted(checkpoints) and checkpoints[0] > 0
    collected: dict[int, list[np.ndarray]] = {m: [] for m in checkpoints}
    done = 0
    while done < n_paths:
        k = min(chunk_paths, n_paths - done)
        position = np.zeros(k, dtype=np.float64)
        previous = 0
        for m in checkpoints:
            segment = sampler(rng, (k, m - previous))
            position += segment.sum(axis=1, dtype=np.float64)
            collected[m].append(position.copy())
            previous = m
        done += k
    return {m: np.concatenate(parts) for m, parts in collected.items()}


def loglog_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of log10(y) against log10(x)."""
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


def moment_summary(positions: dict[int, np.ndarray], checkpoints: list[int]) -> dict:
    """Mean, variance and mean |S_n| at each checkpoint, plus the two slopes."""
    var = [float(positions[m].var(ddof=1)) for m in checkpoints]
    mean_abs = [float(np.abs(positions[m]).mean()) for m in checkpoints]
    mean = [float(positions[m].mean()) for m in checkpoints]
    return {
        "checkpoints": checkpoints,
        "mean": mean,
        "var": var,
        "mean_abs": mean_abs,
        # the same numbers, read against n — flat, flat, and falling:
        "var_over_n": [v / m for v, m in zip(var, checkpoints)],
        "mean_abs_over_sqrt_n": [a / np.sqrt(m) for a, m in zip(mean_abs, checkpoints)],
        "mean_abs_over_n": [a / m for a, m in zip(mean_abs, checkpoints)],
        "var_loglog_slope": loglog_slope(checkpoints, var),
        "mean_abs_loglog_slope": loglog_slope(checkpoints, mean_abs),
    }


# --- the scaling pincer ----------------------------------------------------


def scaling_pincer(
    rng: np.random.Generator,
    n_paths: int,
    dts: list[float],
    alphas: list[float],
    chunk_paths: int,
) -> list[dict]:
    """Walks across [0, 1] in n = 1/dt coin steps of size dt^alpha.

    Every (dt, alpha) cell is simulated independently, no shortcuts, and
    reported beside the exact value n * dt^(2*alpha). Reading down a column
    as dt shrinks: alpha > 1/2 dies, alpha = 1/2 holds at 1, alpha < 1/2
    blows up.
    """
    table = []
    for dt in dts:
        n_steps = round(1.0 / dt)
        for alpha in alphas:
            step_size = dt**alpha
            sums = []
            done = 0
            while done < n_paths:
                k = min(chunk_paths, n_paths - done)
                sums.append(coin_steps(rng, (k, n_steps)).sum(axis=1, dtype=np.float64))
                done += k
            terminal = step_size * np.concatenate(sums)
            table.append(
                {
                    "dt": dt,
                    "alpha": alpha,
                    "n_steps": n_steps,
                    "step_size": step_size,
                    "var_measured": float(terminal.var(ddof=1)),
                    "var_exact": n_steps * step_size * step_size,
                }
            )
    return table


# --- checks ----------------------------------------------------------------


def build_checks(summaries: dict, pincer: list[dict], n_paths: int) -> list[dict]:
    checks = []

    def add(claim: str, measured: float, expected: float, tol: float, mode: str):
        if mode == "abs":
            ok = abs(measured - expected) <= tol
        else:  # relative
            ok = abs(measured / expected - 1.0) <= tol
        checks.append(
            {
                "claim": claim,
                "measured": measured,
                "expected": expected,
                "tolerance": tol,
                "mode": mode,
                "pass": bool(ok),
            }
        )

    for name in ("coin", "gaussian"):
        s = summaries[name]
        add(f"C1/C4 {name}: log-log slope of Var(S_n) vs n is 1",
            s["var_loglog_slope"], 1.0, 0.03, "abs")
        add(f"C2/C4 {name}: log-log slope of E|S_n| vs n is 0.5",
            s["mean_abs_loglog_slope"], 0.5, 0.03, "abs")
        largest = s["checkpoints"][-1]
        add(f"C2 {name}: E|S_n|/sqrt(n) at n={largest} is sqrt(2/pi)",
            s["mean_abs_over_sqrt_n"][-1], SQRT_2_OVER_PI, 0.03, "relative")
        # sanity: the walk is unbiased — mean within 5 standard errors of 0
        se = float(np.sqrt(s["var"][-1] / n_paths))
        add(f"sanity {name}: |mean S_n| at n={largest} within 5 s.e. of 0",
            abs(s["mean"][-1]), 0.0, 5.0 * se, "abs")

    worst = max(abs(c["var_measured"] / c["var_exact"] - 1.0) for c in pincer)
    add("C3: every pincer cell matches Var = n * dt^(2*alpha) (worst rel. error)",
        worst, 0.0, 0.05, "abs")
    return checks


# --- main ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20260830)
    args = parser.parse_args()

    params = {
        "seed": args.seed,
        "n_paths": 10_000,
        "checkpoints": [100, 1_000, 10_000, 100_000],
        "step_distributions": ["coin", "gaussian"],
        "chunk_paths": 250,  # affects draw order, so it is part of the inputs
        "pincer": {
            "T": 1.0,
            "n_paths": 10_000,
            "dts": [0.1, 0.01, 0.001, 0.0001],
            "alphas": [1.0, 0.75, 0.5, 0.25],
            "chunk_paths": 2_000,
        },
    }

    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    summaries = {}
    for name in params["step_distributions"]:
        print(f"[2.1] {name} walk: {params['n_paths']:,} paths "
              f"to n={params['checkpoints'][-1]:,} ...", flush=True)
        positions = positions_at_checkpoints(
            rng, SAMPLERS[name], params["n_paths"],
            params["checkpoints"], params["chunk_paths"],
        )
        summaries[name] = moment_summary(positions, params["checkpoints"])

    print("[2.1] scaling pincer: 16 (dt, alpha) cells ...", flush=True)
    p = params["pincer"]
    pincer = scaling_pincer(rng, p["n_paths"], p["dts"], p["alphas"], p["chunk_paths"])

    checks = build_checks(summaries, pincer, params["n_paths"])

    result = {
        "page": "2.1",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": {
            "walks": summaries,
            "mean_abs_asymptote_sqrt_2_over_pi": SQRT_2_OVER_PI,
            "scaling_pincer": pincer,
        },
        "checks": checks,
    }

    out_path = Path(__file__).with_suffix(".json")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    elapsed = time.perf_counter() - t0
    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}")
    print(f"[2.1] wrote {out_path.name} in {elapsed:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
