"""Variance reduction -- the experiment behind page 3.2.

Serves page 3.2 (docs/quant-learn-index-v1.md): Monte Carlo, and in particular
"antithetics and control variates". Most of that page's numbers come from the
library's own Monte Carlo. This file holds the three the library cannot
produce:

  - a control variate, which the library does not have;
  - the standard error an antithetic run would report if it were computed
    from the paths and not from the pairs, which the library never computes;
  - antithetic sampling on a straddle, a payoff the library does not price in
    one sweep.

The option is Part 2's -- a share at 100, strike 100, one year, r = 0.05,
sigma = 0.4, no dividend -- priced under the risk-neutral measure by drawing
the terminal price exactly (page 2.6):

    S_T = S_0 exp((r - 1/2 sigma^2) T + sigma sqrt(T) Z),    Z standard normal.

The normals are numpy's (PCG64), seeded. They are not the library's generator,
so no estimate here equals one of the library's digit for digit; the standard
errors are the same quantity and agree to within their own noise (C1).

Symbols are the notation ledger's. X is one path's discounted payoff, n the
number of paths, s.e. the standard error of a mean. Y is the control: the
discounted terminal share price e^(-rT) S_T, whose mean is S_0 exactly (page
2.8's martingale).

  C1  The plain estimator. The mean of n = 32,768 discounted payoffs lands on
      the closed form within its standard error, and over 1,600 independent
      runs the spread of the estimates is the standard error each run
      reports.
  C2  Antithetic sampling on the call. Each normal is used twice, as Z and as
      -Z, and the sample is the pair. The two halves of a pair are negatively
      correlated, so the pair mean varies less than two independent paths
      would. The standard error computed from the pair means is the spread
      of the estimator. The one computed from the paths, as if they were
      independent, is not: it leaves the correlation out, and for the call it
      comes out too large -- it reports the plain estimator's error bar and
      hides the improvement.
  C3  Antithetic sampling on a straddle. The straddle's payoff is not
      monotone in S_T: it is large when Z is large and large when -Z is. The
      two halves of a pair are then positively correlated, the pair mean
      varies MORE than two independent paths would, and the standard error
      computed from the paths is too small. The technique makes this
      estimate worse at the same number of paths.
  C4  A control variate. X - beta (Y - S_0) has the same mean as X for any
      fixed beta, and the variance is least at beta = Cov(X, Y) / Var(Y),
      where it is (1 - rho^2) Var(X) with rho the correlation of X and Y.
      beta is estimated from the same paths. The controlled estimate lands
      on the closed form, its reported standard error is its spread over 1,600
      runs, and the error bar is the plain one times sqrt(1 - rho^2).
  C5  The numbers the page's check quotes, each computed here.

Run from the repository root:

    uv run experiments/3_2_variance_reduction.py [--seed 20261119] [--quick]

--quick is for the learn site's build-time snippet check (I3): a tenth of the
runs. A spread measured over 160 runs is too uncertain to tell a wrong standard
error from a right one, so the two checks that compare a wrong standard error
with the spread are the full run's alone; every other claim is asserted, with
the tolerance on a spread widened to match. NO JSON is written -- the
committed result is the full run.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from math import exp, sqrt
from pathlib import Path

import numpy as np

PAGE = "3.2"

# Page 2.9's formula is restated once, in page 1.4's script, and imported from
# there. importlib, because a module whose name starts with a digit cannot be
# named in an import statement.
sys.path.insert(0, str(Path(__file__).resolve().parent))
black_scholes = importlib.import_module("1_4_options").black_scholes


# --- the paths and the payoffs ---------------------------------------------------


def terminal_price(z: np.ndarray, m: dict) -> np.ndarray:
    """S_T for each standard normal in z: the exact draw of page 2.6, with drift r."""
    return m["S"] * np.exp((m["r"] - 0.5 * m["sigma"] ** 2) * m["T"] + m["sigma"] * sqrt(m["T"]) * z)


def discounted_call(S_T: np.ndarray, m: dict) -> np.ndarray:
    return exp(-m["r"] * m["T"]) * np.maximum(S_T - m["K"], 0.0)


def discounted_straddle(S_T: np.ndarray, m: dict) -> np.ndarray:
    """A call and a put at the same strike: it pays the distance from K."""
    return exp(-m["r"] * m["T"]) * np.abs(S_T - m["K"])


# --- the estimators --------------------------------------------------------------


def mean_and_se(x: np.ndarray) -> dict:
    """The mean of independent samples and its standard error, s / sqrt(n)."""
    return {"mean": float(x.mean()), "se": float(x.std(ddof=1) / sqrt(x.size)), "n": int(x.size)}


def antithetic(payoff, z_half: np.ndarray, m: dict) -> dict:
    """Each normal used as Z and as -Z. The sample is the pair."""
    up, down = payoff(terminal_price(z_half, m), m), payoff(terminal_price(-z_half, m), m)
    pairs = mean_and_se(0.5 * (up + down))
    paths = mean_and_se(np.concatenate([up, down]))
    return {"mean": pairs["mean"], "se_from_pairs": pairs["se"], "pairs": pairs["n"],
            "se_from_paths_as_if_independent": paths["se"], "paths": paths["n"],
            "correlation_within_a_pair": float(np.corrcoef(up, down)[0, 1])}


def control_variate(x: np.ndarray, y: np.ndarray, y_mean_known: float) -> dict:
    """X - beta (Y - E[Y]), with beta = Cov(X, Y) / Var(Y) estimated from the same paths."""
    covariance = np.cov(x, y, ddof=1)
    beta = float(covariance[0, 1] / covariance[1, 1])
    controlled = mean_and_se(x - beta * (y - y_mean_known))
    return {"mean": controlled["mean"], "se": controlled["se"], "n": controlled["n"], "beta": beta,
            "correlation": float(covariance[0, 1] / sqrt(covariance[0, 0] * covariance[1, 1])),
            "control_sample_mean": float(y.mean()), "control_known_mean": y_mean_known}


def one_run(rng: np.random.Generator, n: int, m: dict) -> dict:
    """Every estimator from one draw of n normals. The antithetic runs use the first n / 2
    of them twice, so each estimator costs the same n paths."""
    z = rng.standard_normal(n)
    S_T = terminal_price(z, m)
    call = discounted_call(S_T, m)
    return {
        "plain": mean_and_se(call),
        "control": control_variate(call, exp(-m["r"] * m["T"]) * S_T, m["S"]),
        "antithetic_call": antithetic(discounted_call, z[: n // 2], m),
        "plain_straddle": mean_and_se(discounted_straddle(S_T, m)),
        "antithetic_straddle": antithetic(discounted_straddle, z[: n // 2], m),
    }


def over_runs(runs: list[dict], estimator: str, se_key: str = "se") -> dict:
    """What the runs did against what each said it would do: the spread of the estimates
    beside the mean standard error the runs reported."""
    means = np.array([run[estimator]["mean"] for run in runs])
    return {"runs": len(runs), "mean_of_estimates": float(means.mean()),
            "spread_of_estimates": float(means.std(ddof=1)),
            "mean_reported_se": float(np.mean([run[estimator][se_key] for run in runs]))}


# --- the experiment ----------------------------------------------------------------


def run(params: dict) -> dict:
    m, n = params["market"], params["paths"]
    rng = np.random.default_rng(params["seed"])
    runs = [one_run(rng, n, m) for _ in range(params["runs"])]
    first = runs[0]

    closed = black_scholes(m["S"], m["K"], m["r"], m["sigma"], m["T"])
    straddle_closed = closed["call"] + closed["put"]

    summary = {
        "plain": over_runs(runs, "plain"),
        "control": over_runs(runs, "control"),
        "antithetic_call": over_runs(runs, "antithetic_call", "se_from_pairs"),
        "antithetic_call_from_paths": over_runs(runs, "antithetic_call", "se_from_paths_as_if_independent"),
        "plain_straddle": over_runs(runs, "plain_straddle"),
        "antithetic_straddle": over_runs(runs, "antithetic_straddle", "se_from_pairs"),
        "antithetic_straddle_from_paths": over_runs(runs, "antithetic_straddle", "se_from_paths_as_if_independent"),
    }
    averages = {
        "control_correlation": float(np.mean([r["control"]["correlation"] for r in runs])),
        "control_beta": float(np.mean([r["control"]["beta"] for r in runs])),
        "call_pair_correlation": float(np.mean([r["antithetic_call"]["correlation_within_a_pair"] for r in runs])),
        "straddle_pair_correlation": float(np.mean([r["antithetic_straddle"]["correlation_within_a_pair"] for r in runs])),
    }

    rho = first["control"]["correlation"]
    control = first["control"]
    quoted = {
        "plain_estimate": first["plain"]["mean"],
        "plain_se": first["plain"]["se"],
        "control_estimate": control["mean"],
        "control_se": control["se"],
        "control_beta": control["beta"],
        "control_sample_mean": control["control_sample_mean"],
        "control_adjustment": control["mean"] - first["plain"]["mean"],
        "control_if_the_adjustment_were_added": first["plain"]["mean"] + control["beta"] * (control["control_sample_mean"] - m["S"]),
        "control_if_beta_were_one": first["plain"]["mean"] - (control["control_sample_mean"] - m["S"]),
        "control_se_ratio": control["se"] / first["plain"]["se"],
        "control_se_ratio_predicted": sqrt(1.0 - rho * rho),
        "paths_for_the_plain_estimator_to_match_the_control": n / (1.0 - rho * rho),
        "antithetic_call_se_from_pairs": first["antithetic_call"]["se_from_pairs"],
        "antithetic_call_se_from_paths": first["antithetic_call"]["se_from_paths_as_if_independent"],
        "antithetic_call_se_from_pairs_divided_by_root_two": first["antithetic_call"]["se_from_pairs"] / sqrt(2.0),
        "antithetic_straddle_se_from_pairs": first["antithetic_straddle"]["se_from_pairs"],
        "antithetic_straddle_se_from_paths": first["antithetic_straddle"]["se_from_paths_as_if_independent"],
        "plain_straddle_se": first["plain_straddle"]["se"],
    }
    return {"closed_form": {"call": closed["call"], "put": closed["put"], "straddle": straddle_closed},
            "first_run": first, "over_runs": summary, "averages": averages, "quoted_in_checks": quoted}


# --- checks ------------------------------------------------------------------------


def build_checks(res: dict, params: dict) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        error = abs(measured - expected) / (abs(expected) if mode == "rel" else 1.0)
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(error <= tol)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0,
                       "mode": "abs", "pass": bool(ok)})

    runs = params["runs"]
    call, straddle = res["closed_form"]["call"], res["closed_form"]["straddle"]
    first, summary, averages = res["first_run"], res["over_runs"], res["averages"]
    # A standard deviation measured over `runs` runs is itself uncertain by 1 / sqrt(2 runs)
    # of its value; five of those is the bound on "the spread is the reported standard
    # error". It is 8.8% at 1,600 runs.
    spread_tol = 5.0 / sqrt(2.0 * runs)

    def lands(label, estimator, target, se_key="se"):
        s = summary[estimator]
        add(f"{label}: the mean of {runs} estimates is the closed form, within 5 standard errors of that mean",
            s["mean_of_estimates"], target, 5.0 * s["mean_reported_se"] / sqrt(runs))
        add(f"{label}: the first run is within 5 of its own standard errors of the closed form",
            first[estimator]["mean"], target, 5.0 * first[estimator][se_key])

    def honest(label, estimator):
        s = summary[estimator]
        add(f"{label}: the spread of the estimates is the standard error the runs report",
            s["spread_of_estimates"] / s["mean_reported_se"], 1.0, spread_tol)

    add("the closed form is page 2.9's 18.0230", call, 18.0230, 5e-5)

    lands("C1 plain", "plain", call)
    honest("C1 plain", "plain")

    lands("C2 antithetic call", "antithetic_call", call, "se_from_pairs")
    honest("C2 antithetic call, standard error from the pairs", "antithetic_call")
    truth("C2 the two halves of a pair are negatively correlated for the call", averages["call_pair_correlation"] < -0.2)
    add("C2 antithetic sampling narrows the call's error bar at the same number of paths, by sqrt(1 + correlation)",
        summary["antithetic_call"]["mean_reported_se"] / summary["plain"]["mean_reported_se"],
        sqrt(1.0 + averages["call_pair_correlation"]), 0.01)
    wrong = summary["antithetic_call_from_paths"]
    add("C2 computed from the paths as if independent, the call's standard error is the plain estimator's: "
        "the improvement is hidden", wrong["mean_reported_se"] / summary["plain"]["mean_reported_se"], 1.0, 0.01)
    truth("C2 so it is too LARGE: more than the pairs' by a tenth or more",
          wrong["mean_reported_se"] > 1.1 * summary["antithetic_call"]["mean_reported_se"])
    if not params["quick"]:
        truth("C2 and it is not the spread of the estimates: it exceeds the spread by more than the bound",
              wrong["mean_reported_se"] / wrong["spread_of_estimates"] - 1.0 > spread_tol)

    lands("C3 antithetic straddle", "antithetic_straddle", straddle, "se_from_pairs")
    honest("C3 antithetic straddle, standard error from the pairs", "antithetic_straddle")
    truth("C3 the two halves of a pair are positively correlated for the straddle", averages["straddle_pair_correlation"] > 0.2)
    add("C3 antithetic sampling WIDENS the straddle's error bar at the same number of paths, by sqrt(1 + correlation)",
        summary["antithetic_straddle"]["mean_reported_se"] / summary["plain_straddle"]["mean_reported_se"],
        sqrt(1.0 + averages["straddle_pair_correlation"]), 0.01)
    wrong = summary["antithetic_straddle_from_paths"]
    truth("C3 computed from the paths as if independent, the straddle's standard error is too SMALL: "
          "less than the pairs' by a tenth or more",
          wrong["mean_reported_se"] < 0.9 * summary["antithetic_straddle"]["mean_reported_se"])
    if not params["quick"]:
        truth("C3 and it is not the spread of the estimates: it falls short of the spread by more than the bound",
              1.0 - wrong["mean_reported_se"] / wrong["spread_of_estimates"] > spread_tol)

    lands("C4 control variate", "control", call)
    honest("C4 control variate", "control")
    add("C4 the controlled error bar is the plain one times sqrt(1 - rho^2)",
        summary["control"]["mean_reported_se"] / summary["plain"]["mean_reported_se"],
        sqrt(1.0 - averages["control_correlation"] ** 2), 0.01)
    truth("C4 the control is strongly correlated with the payoff", averages["control_correlation"] > 0.9)
    truth("C4 the control's sample mean is within 5 standard errors of S_0, its known mean",
          abs(first["control"]["control_sample_mean"] - params["market"]["S"])
          <= 5.0 * params["market"]["S"] * sqrt(exp(params["market"]["sigma"] ** 2 * params["market"]["T"]) - 1.0) / sqrt(params["paths"]))

    q = res["quoted_in_checks"]
    add("C5 the adjustment is minus beta times the control's miss", q["control_adjustment"],
        -q["control_beta"] * (q["control_sample_mean"] - params["market"]["S"]), 1e-9)
    truth("C5 at this seed the adjustment moves the first run's estimate towards the closed form",
          abs(q["control_estimate"] - call) < abs(q["plain_estimate"] - call))
    truth("C5 at this seed, added with the wrong sign, it moves the estimate away",
          abs(q["control_if_the_adjustment_were_added"] - call) > abs(q["plain_estimate"] - call))
    add("C5 the first run's error bars are in the measured ratio", q["control_se_ratio"], q["control_se_ratio_predicted"], 0.01)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261119)
    parser.add_argument("--quick", action="store_true", help="snippet check: a tenth of the runs, no JSON written")
    args = parser.parse_args()

    params = {
        "quick": args.quick,
        "seed": args.seed,
        "generator": "numpy default_rng (PCG64); not the library's generator",
        "market": {"S": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.4, "T": 1.0, "q": 0.0,
                   "note": "Part 2's option (page 2.9): a share at 100 paying no dividend, strike 100, one year"},
        "paths": 32768,
        "runs": 160 if args.quick else 1600,
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
