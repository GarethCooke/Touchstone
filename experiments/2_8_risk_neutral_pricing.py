"""Risk-neutral pricing -- the experiment behind page 2.8.

Serves page 2.8 (docs/quant-learn-index-v1.md). The stock is page 2.6's
Geometric Brownian motion (GBM),

    dS = mu S dt + sigma S dW        (drift first),

sampled EXACTLY (2.6's decision 1): a European payoff looks only at T, so
S_T = S_0 exp((mu - 1/2 sigma^2) T + sigma W_T) is drawn directly, and where a
path is needed (C3, C4) it is stepped by 2.6's closed-form step, never Euler.

Page 2.7 ended with mu gone from the PDE and the question: if the price does
not depend on the stock's real-world drift, what drift should be used to value
the option? Page 2.8 answers from the opposite direction -- price as if the
stock drifted at r:

    V = e^(-rT) E^Q[payoff],

the expectation under a measure Q in which dS = r S dt + sigma S dW~. Session
S8's setup decision (owner, 2026-11-04, "a"): the "PDE price" the Monte Carlo
is compared against is the closed form, which 2.7 checked against the PDE at
1e-15 on a grid and 2e-13 at every point its hedges visited; 2.9 derives it.
Girsanov is measured, not quoted (decision "b"): the mu-paths reweighted by
the likelihood ratio reproduce the Q-price.

  C1  The index's check, both halves. The discounted average payoff over
      paths drawn at the REAL-WORLD drift mu in {-0.2, 0, 0.1, 0.3, 0.6} is
      NOT the price: it sits above the closed form for mu > r and below for
      mu < r, by e^(-rT) E^P[payoff] - V (the lognormal integral with mu, in
      closed form), more than 5 s.e. away, the gap growing with mu - r. At
      mu = r it lands on the closed form within 5 s.e. The forward likewise:
      e^(-rT) E^P[S_T - K] = S_0 e^((mu-r)T) - K e^(-rT) equals the
      no-arbitrage value S_0 - K e^(-rT) only at mu = r.
  C2  Monte Carlo under Q converges to the closed form like 1/sqrt n: the
      nested estimates at n = 10^3 ... 10^6 are each within 5 s.e. of V; the
      rms error of independent batches of size n falls with slope -1/2 and
      equals the reported standard error (I20: the s.e. is reported, and
      here it is also measured). The same for the forward, whose Q-price is
      S_0 - K e^(-rT) exactly, and for E^Q[S_T] = S_0 e^(rT).
  C3  The martingale. Under Q the discounted stock e^(-rt) S_t has mean S_0
      at every checkpoint t (2.5's exponential martingale e^(sigma W~ - 1/2
      sigma^2 t), rescaled), with a spread that grows with t -- a martingale
      is not a constant. Under mu > r its mean is S_0 e^((mu-r)t), above S_0
      by more than 5 s.e. (a submartingale); under mu < r below (a
      supermartingale). Path by path, e^(-rt) S_t = S_0 exp(sigma W~_t -
      1/2 sigma^2 t) to rounding (the bookkeeping behind the claim).
  C4  Girsanov as reweighting. The SAME mu-paths as C1, each given the weight
      L = exp(-lambda W_T - 1/2 lambda^2 T) with lambda = (mu - r)/sigma,
      average to the Q-price within 5 s.e.; mean L = 1. On the stepped
      mu-paths of C3, the weighted mean of log(S_T/S_0) is (r - 1/2 sigma^2) T
      -- the Q-drift -- while the weighted mean realised volatility is still
      sigma: reweighting moves the drift and leaves the volatility alone,
      and the weighted discounted stock has mean S_0 at every checkpoint (the
      martingale restored). The cost: mean L^2 = e^(lambda^2 T), so the
      effective sample size ESS = n e^(-lambda^2 T) and the weighted
      estimate's s.e. grows with |lambda| -- the practical reason to simulate
      under Q rather than reweight.
  C5  Feynman-Kac in numbers. V_MC(t, S) = e^(-r tau) E^Q[payoff | S_t = S]
      evaluated on a (t, S) grid with common random numbers agrees with the
      closed form at every grid point within 5 s.e., and, with its Greeks
      taken by central differences from V_MC alone (2.7's C5 (i) on a Monte
      Carlo surface), satisfies the Black-Scholes PDE with a residual bounded
      by the closed form's own finite-difference residual plus the Monte
      Carlo noise measured by an independent replication. The expectation IS
      the PDE's solution; the theorem is named on the page, not proved.

Run from the repository root:

    uv run experiments/2_8_risk_neutral_pricing.py [--seed 20261104] [--quick]

--quick runs a tenth of the paths for the learn site's build-time snippet
check (I3): the statistical tolerances widen by the square root of the
path-count ratio so the same claims are still asserted, and NO JSON is
written -- the committed result is always the full run.

Writes 2_8_risk_neutral_pricing.json beside this file: parameters in, results
out, no timestamps -- same seed, same file (I6). No plotting here; the site
draws (see experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import erf, exp, log, pi, sqrt
from pathlib import Path

import numpy as np


# --- the normal CDF, vectorised ----------------------------------------------
#
# numpy has no erf. This is Hart's 1968 rational approximation as given by
# West (2005), accurate to about 1e-14 in double precision; main() checks it
# against math.erf before anything else runs (copied from 2_7_delta_hedging.py).


def Phi(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    a = np.abs(x)
    e = np.exp(-0.5 * a * a)
    b = ((((((3.52624965998911e-02 * a + 0.700383064443688) * a + 6.37396220353165) * a
            + 33.912866078383) * a + 112.079291497871) * a + 221.213596169931) * a + 220.206867912376)
    c = (((((((8.83883476483184e-02 * a + 1.75566716318264) * a + 16.064177579207) * a
             + 86.7807322029461) * a + 296.564248779674) * a + 637.333633378831) * a
          + 793.826512519948) * a + 440.413735824752)
    tail_small = e * b / c
    with np.errstate(divide="ignore", invalid="ignore"):
        d = a + 0.65
        d = a + 4.0 / d
        d = a + 3.0 / d
        d = a + 2.0 / d
        d = a + 1.0 / d
        tail_large = e / (d * 2.506628274631)
    tail = np.where(a < 7.07106781186547, tail_small, tail_large)
    tail = np.where(a >= 37.0, 0.0, tail)
    return np.where(x > 0.0, 1.0 - tail, tail)


def phi_self_test() -> float:
    xs = np.linspace(-9.0, 9.0, 36001)
    ref = np.array([0.5 * (1.0 + erf(v / sqrt(2.0))) for v in xs])
    return float(np.abs(Phi(xs) - ref).max())


# --- the closed form: the PDE's solution, used as the target (setup "a") ------


def call_price(S, tau, K, r, sigma):
    """The closed-form call value at time-to-expiry tau > 0 -- 2.9 derives it; 2.7
    checked that it satisfies the Black-Scholes PDE, which is why 2.8 may use it as
    'the PDE price'."""
    S = np.asarray(S, dtype=float)
    st = sigma * sqrt(tau)
    d1 = (np.log(S / K) + (r + 0.5 * sigma * sigma) * tau) / st
    d2 = d1 - st
    return S * Phi(d1) - K * exp(-r * tau) * Phi(d2)


def call_greeks(S, tau, K, r, sigma):
    """Value, delta, gamma, theta of the call (2.7's function), for C5's PDE residual."""
    S = np.asarray(S, dtype=float)
    st = sigma * sqrt(tau)
    d1 = (np.log(S / K) + (r + 0.5 * sigma * sigma) * tau) / st
    d2 = d1 - st
    disc = exp(-r * tau)
    Nd1, Nd2 = Phi(d1), Phi(d2)
    nd1 = np.exp(-0.5 * d1 * d1) / sqrt(2.0 * pi)
    V = S * Nd1 - K * disc * Nd2
    return V, Nd1, nd1 / (S * st), -S * nd1 * sigma / (2.0 * sqrt(tau)) - r * K * disc * Nd2


def forward_price(S0, T, K, r) -> float:
    """The forward struck at K: S_0 - K e^(-rT) by no-arbitrage, no expectation needed."""
    return S0 - K * exp(-r * T)


def real_world_expectation(S0, K, T, mu, sigma) -> dict:
    """E^P[max(S_T - K, 0)] and E^P[S_T] under the real-world drift mu, in closed form:
    the lognormal integrated against the payoff (2.7's unhedged_closed_form; the same
    integral 2.9 does with r in place of mu)."""
    st = sigma * sqrt(T)
    d1 = (log(S0 / K) + (mu + 0.5 * sigma * sigma) * T) / st
    d2 = d1 - st
    E_pay = S0 * exp(mu * T) * float(Phi(d1)) - K * float(Phi(d2))
    E_pay2 = (S0 * S0 * exp((2.0 * mu + sigma * sigma) * T) * float(Phi(d1 + st))
              - 2.0 * K * S0 * exp(mu * T) * float(Phi(d1)) + K * K * float(Phi(d2)))
    return {"E_payoff": E_pay, "sd_payoff": sqrt(max(E_pay2 - E_pay * E_pay, 0.0)),
            "E_S_T": S0 * exp(mu * T)}


# --- statistics ----------------------------------------------------------------


def stats(x: np.ndarray) -> dict[str, float]:
    sd = float(x.std(ddof=1))
    return {"mean": float(x.mean()), "sd": sd, "se_of_mean": sd / sqrt(x.size), "n": int(x.size)}


def weighted(x: np.ndarray, w: np.ndarray) -> dict[str, float]:
    """The importance-sampling estimator (1/n) Sum w_i x_i and its standard error.
    Unnormalised on purpose: E^P[L X] = E^Q[X] exactly, so the estimate is unbiased
    and its s.e. is the plain sd of the products over sqrt n."""
    return stats(w * x)


def weighted_histogram(x: np.ndarray, w: np.ndarray, lo: float, hi: float, bins: int) -> dict:
    sums, _ = np.histogram(x, bins=bins, range=(lo, hi), weights=w)
    return {"lo": lo, "hi": hi, "bins": bins, "weight_sums": [float(c) for c in sums],
            "weight_below_lo": float(w[x < lo].sum()), "weight_above_hi": float(w[x >= hi].sum())}


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


def histogram(x: np.ndarray, lo: float, hi: float, bins: int) -> dict:
    counts, _ = np.histogram(x, bins=bins, range=(lo, hi))
    return {"lo": lo, "hi": hi, "bins": bins, "counts": [int(c) for c in counts],
            "below_lo": int((x < lo).sum()), "above_hi": int((x >= hi).sum())}


# --- C1 and C4 at expiry: one set of draws per drift, read two ways -------------


def terminal_run(rng, n, S0, K, T, r, mu, sigma, nested_ns, batch_ns, label) -> dict:
    """Draw S_T exactly under the drift mu, n paths. Report the discounted average
    payoff as it stands (C1) and reweighted by Girsanov's likelihood ratio (C4). When
    mu = r this is the Q-run, and the nested and batched estimates measure the
    1/sqrt n law (C2)."""
    Z = rng.standard_normal(n)
    W_T = sqrt(T) * Z
    S_T = S0 * np.exp((mu - 0.5 * sigma * sigma) * T + sigma * W_T)
    payoff = np.maximum(S_T - K, 0.0)
    disc = exp(-r * T)
    V = float(call_price(S0, T, K, r, sigma))
    F = forward_price(S0, T, K, r)
    lam = (mu - r) / sigma
    L = np.exp(-lam * W_T - 0.5 * lam * lam * T)
    cf = real_world_expectation(S0, K, T, mu, sigma)

    unw = stats(disc * payoff)
    fwd_unw = stats(disc * (S_T - K))
    itm = (S_T > K).astype(float)
    d2 = (log(S0 / K) + (r - 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))
    out = {
        "label": label, "mu": mu, "lambda": lam, "n_paths": n,
        "closed_form_price": V,
        "forward_no_arbitrage": F,
        "discounted_mean_payoff": unw,                                      # C1
        "closed_form_discounted_real_world_expectation": disc * cf["E_payoff"],
        "closed_form_bias": disc * cf["E_payoff"] - V,
        "measured_bias": unw["mean"] - V,
        "bias_in_se": (unw["mean"] - V) / unw["se_of_mean"],
        "E_payoff_real_world": {"measured": float(payoff.mean()), "closed_form": cf["E_payoff"]},
        "E_S_T": {"measured": float(S_T.mean()), "expected": cf["E_S_T"], "se": float(S_T.std(ddof=1) / sqrt(n))},
        "forward_discounted_mean": fwd_unw,
        "forward_closed_form_under_mu": S0 * exp((mu - r) * T) - K * disc,
        "itm_fraction_P": stats(itm),
        "itm_probability_Q": float(Phi(d2)),
        "girsanov": {                                                     # C4
            "weight": "L = exp(-lambda W_T - 1/2 lambda^2 T), lambda = (mu - r)/sigma, the same paths",
            "mean_L": stats(L),
            "mean_L2": stats(L * L),
            "expected_mean_L2": exp(lam * lam * T),
            "reweighted_discounted_mean_payoff": weighted(disc * payoff, L),
            "reweighted_forward": weighted(disc * (S_T - K), L),
            "reweighted_E_S_T": weighted(S_T, L),
            "ess": float(L.sum() ** 2 / (L * L).sum()),
            "ess_over_n": float(L.sum() ** 2 / (L * L).sum() / n),
            "expected_ess_over_n": exp(-lam * lam * T),
            "reweighted_itm_fraction": weighted(itm, L),
            "se_reweighted_price": weighted(disc * payoff, L)["se_of_mean"],
            "se_unweighted_price_under_mu": unw["se_of_mean"],
        },
        "histogram_S_T": histogram(S_T, 0.0, 400.0, 80),
        "histogram_S_T_reweighted": weighted_histogram(S_T, L, 0.0, 400.0, 80),
    }
    if abs(mu - r) < 1e-15:                                              # C2: the Q-run
        cum = np.cumsum(disc * payoff)
        nested = []
        for m in nested_ns:
            x = disc * payoff[:m]
            nested.append({"n": m, "estimate": float(cum[m - 1] / m), "se": float(x.std(ddof=1) / sqrt(m)),
                           "error": float(cum[m - 1] / m - V), "error_in_se": float((cum[m - 1] / m - V) / (x.std(ddof=1) / sqrt(m)))})
        batches = []
        for m in [m for m in batch_ns if n // m >= 100]:
            b = (disc * payoff[: (n // m) * m]).reshape(n // m, m).mean(axis=1)
            fb = (disc * (S_T[: (n // m) * m] - K)).reshape(n // m, m).mean(axis=1)
            batches.append({"n": m, "batches": int(n // m),
                            "rms_error": float(sqrt(((b - V) ** 2).mean())),
                            "predicted_se": float(unw["sd"] / sqrt(m)),
                            "forward_rms_error": float(sqrt(((fb - F) ** 2).mean())),
                            "forward_predicted_se": float(fwd_unw["sd"] / sqrt(m))})
        out["convergence"] = {
            "nested": nested, "batches": batches,
            "slope_rms_error_vs_n": loglog_slope([b["n"] for b in batches], [b["rms_error"] for b in batches]),
            "slope_forward_rms_error_vs_n": loglog_slope([b["n"] for b in batches], [b["forward_rms_error"] for b in batches]),
            "E_Q_S_T": {"measured": float(S_T.mean()), "expected": S0 * exp(r * T), "se": float(S_T.std(ddof=1) / sqrt(n))},
        }
    return out


# --- C3 and C4 along paths: the discounted stock at checkpoints ----------------


def path_run(rng, n_paths, n_steps, chunk, S0, T, r, mu, sigma, checkpoints, label) -> dict:
    """Step n_paths exact-GBM paths under mu on n_steps steps. At each checkpoint record
    e^(-rt) S_t, unweighted (C3) and weighted by L_T (C4); realised volatility and the
    terminal log-return, both ways; and the identity e^(-rt) S_t = S_0 exp(sigma W~_t
    - 1/2 sigma^2 t) with W~_t = W_t + lambda t, path by path."""
    dt = T / n_steps
    lam = (mu - r) / sigma
    idx = [int(round(c / dt)) for c in checkpoints]
    disc_S = {i: [] for i in idx}
    Ls, rv, lr = [], [], []
    identity_max = 0.0
    for start in range(0, n_paths, chunk):
        m = min(chunk, n_paths - start)
        Z = rng.standard_normal((m, n_steps))
        W = np.cumsum(sqrt(dt) * Z, axis=1)
        logS = log(S0) + (mu - 0.5 * sigma * sigma) * dt * np.arange(1, n_steps + 1) + sigma * W
        S = np.exp(logS)
        W_T = W[:, -1]
        L = np.exp(-lam * W_T - 0.5 * lam * lam * T)
        Ls.append(L)
        steps = np.diff(np.concatenate([np.full((m, 1), log(S0)), logS], axis=1), axis=1)
        rv.append(steps.var(axis=1, ddof=1) * (n_steps / T))      # realised variance, unbiased for sigma^2
        lr.append(logS[:, -1] - log(S0))
        for i in idx:
            t = i * dt
            d = exp(-r * t) * S[:, i - 1]
            disc_S[i].append(d)
            W_tilde = W[:, i - 1] + lam * t
            identity_max = max(identity_max, float(np.abs(d - S0 * np.exp(sigma * W_tilde - 0.5 * sigma * sigma * t)).max()))
    L = np.concatenate(Ls)
    rv = np.concatenate(rv)
    lr = np.concatenate(lr)
    cps = []
    for i in idx:
        t = i * dt
        d = np.concatenate(disc_S[i])
        cps.append({"t": t, "discounted_S": stats(d), "expected_under_mu": S0 * exp((mu - r) * t),
                    "expected_sd_under_mu": S0 * exp((mu - r) * t) * sqrt(exp(sigma * sigma * t) - 1.0),
                    "reweighted_discounted_S": weighted(d, L)})
    return {
        "label": label, "mu": mu, "lambda": lam, "n_paths": n_paths, "n_steps": n_steps,
        "checkpoints": cps,
        "identity_max_abs": identity_max,
        "realised_variance": {"unweighted": stats(rv), "reweighted": weighted(rv, L), "expected": sigma * sigma,
                              "realised_vol_unweighted": sqrt(float(rv.mean())), "realised_vol_reweighted": sqrt(float((L * rv).mean()))},
        "log_return_T": {"unweighted": stats(lr), "expected_under_mu": (mu - 0.5 * sigma * sigma) * T,
                         "reweighted": weighted(lr, L), "expected_under_Q": (r - 0.5 * sigma * sigma) * T},
        "mean_L": stats(L),
    }


# --- C5: Feynman-Kac on a (t, S) grid with common random numbers --------------


def mc_surface(Z, S_grid, tau, K, r, sigma):
    """V_MC(t, S) = e^(-r tau) mean payoff of S exp((r - 1/2 sigma^2) tau + sigma sqrt(tau) Z)
    for every S in S_grid, the SAME Z for every point (common random numbers), so that the
    surface is smooth enough to differentiate. Returns the estimate and its s.e."""
    growth = np.exp((r - 0.5 * sigma * sigma) * tau + sigma * sqrt(tau) * Z)
    V = np.empty(S_grid.size)
    se = np.empty(S_grid.size)
    for j, S in enumerate(S_grid):
        p = exp(-r * tau) * np.maximum(S * growth - K, 0.0)
        V[j] = p.mean()
        se[j] = p.std(ddof=1) / sqrt(p.size)
    return V, se


def feynman_kac(rng, n, S_lo, S_hi, n_S, taus, h_rel, K, r, sigma, replications) -> dict:
    S = np.linspace(S_lo, S_hi, n_S)
    rows = []
    for tau in taus:
        V_cf, delta, gamma, theta = call_greeks(S, tau, K, r, sigma)
        h, k = h_rel * S, h_rel * tau
        # the closed form's own finite-difference residual at this h (2.7's C5 (i))
        Vp, Vm = call_price(S + h, tau, K, r, sigma), call_price(S - h, tau, K, r, sigma)
        Vtp, Vtm = call_price(S, tau - k, K, r, sigma), call_price(S, tau + k, K, r, sigma)
        res_cf = (Vtp - Vtm) / (2 * k) + 0.5 * sigma ** 2 * S ** 2 * (Vp - 2 * V_cf + Vm) / (h * h) + r * S * (Vp - Vm) / (2 * h) - r * V_cf
        reps = []
        for _ in range(replications):
            Z = rng.standard_normal(n)
            V, se = mc_surface(Z, S, tau, K, r, sigma)
            Vp, _ = mc_surface(Z, S + h, tau, K, r, sigma)
            Vm, _ = mc_surface(Z, S - h, tau, K, r, sigma)
            Vtp, _ = mc_surface(Z, S, tau - k, K, r, sigma)
            Vtm, _ = mc_surface(Z, S, tau + k, K, r, sigma)
            res = (Vtp - Vtm) / (2 * k) + 0.5 * sigma ** 2 * S ** 2 * (Vp - 2 * V + Vm) / (h * h) + r * S * (Vp - Vm) / (2 * h) - r * V
            reps.append({"V": V, "se": se, "res": res})
        noise = sqrt(((reps[0]["res"] - reps[1]["res"]) ** 2).mean() / 2.0) if replications >= 2 else float("nan")
        V, se, res = reps[0]["V"], reps[0]["se"], reps[0]["res"]
        rows.append({
            "tau": tau, "h_rel": h_rel,
            "S": S.tolist(), "V_mc": V.tolist(), "se": se.tolist(), "V_closed_form": V_cf.tolist(),
            "max_abs_error_in_se": float(np.abs((V - V_cf) / se).max()),
            "pde_residual_rms": float(sqrt((res ** 2).mean())),
            "pde_residual_max_abs": float(np.abs(res).max()),
            "closed_form_fd_residual_rms": float(sqrt((res_cf ** 2).mean())),
            "mc_noise_rms_by_replication": noise,
            "analytic_residual_max_abs": float(np.abs(theta + 0.5 * sigma ** 2 * S ** 2 * gamma + r * S * delta - r * V_cf).max()),
            "largest_pde_term_rms": float(sqrt(((0.5 * sigma ** 2 * S ** 2 * gamma) ** 2).mean())),
        })
    return {"n_per_point": n, "grid": {"S": [S_lo, S_hi, n_S], "tau": list(taus)}, "h_rel": h_rel,
            "common_random_numbers": True, "replications": replications, "rows": rows}


# --- checks --------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []
    slack = sqrt(params["n_terminal_full"] / params["n_terminal"])   # --quick: a tenth of the paths

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    add("Phi: Hart/West normal CDF agrees with math.erf on [-9, 9] (max abs diff < 1e-13)", res["phi_max_abs_error"], 0.0, 1e-13)

    r = params["r"]
    runs = res["terminal"]
    q = next(v for v in runs.values() if abs(v["mu"] - r) < 1e-15)
    # C1
    for k, t in runs.items():
        mu, u = t["mu"], t["discounted_mean_payoff"]
        if abs(mu - r) < 1e-15:
            add(f"C1 mu={mu:+.2f} (= r): discounted MC average payoff is the closed form (within 5 s.e.)", u["mean"], t["closed_form_price"], 5 * u["se_of_mean"])
            add(f"C1 mu={mu:+.2f} (= r): discounted MC average of S_T - K is the forward's no-arbitrage value S_0 - K e^(-rT) (within 5 s.e.)", t["forward_discounted_mean"]["mean"], t["forward_no_arbitrage"], 5 * t["forward_discounted_mean"]["se_of_mean"])
        else:
            side = "above" if mu > r else "below"
            truth(f"C1 mu={mu:+.2f}: discounted MC average payoff is {side} the closed form by more than 5 s.e. -- the real-world expectation discounted at r is not the price", (u["mean"] - t["closed_form_price"]) * (1 if mu > r else -1) > 5 * u["se_of_mean"])
            add(f"C1 mu={mu:+.2f}: the gap equals e^(-rT) E^P[payoff] - V in closed form (within 5 s.e.)", u["mean"], t["closed_form_discounted_real_world_expectation"], 5 * u["se_of_mean"])
            truth(f"C1 mu={mu:+.2f}: the forward's discounted real-world mean S_0 e^((mu-r)T) - K e^(-rT) is more than 5 s.e. from its no-arbitrage value", abs(t["forward_discounted_mean"]["mean"] - t["forward_no_arbitrage"]) > 5 * t["forward_discounted_mean"]["se_of_mean"])
        add(f"C1 mu={mu:+.2f}: E[S_T] is S_0 e^(mu T) (within 5 s.e.; 2.6's check)", t["E_S_T"]["measured"], t["E_S_T"]["expected"], 5 * t["E_S_T"]["se"])
    ordered = sorted(runs.values(), key=lambda t: t["mu"])
    truth("C1: the measured gap to the closed form increases with mu - r across every drift run", all(a["measured_bias"] < b["measured_bias"] for a, b in zip(ordered, ordered[1:])))
    p1 = runs["mu_0.10"]
    add("C1 (P1): at mu = 0.1 the discounted real-world average sits above the closed form by the closed-form gap (within 5 s.e.)", p1["measured_bias"], p1["closed_form_bias"], 5 * p1["discounted_mean_payoff"]["se_of_mean"])
    # P3: two desks
    a, b = runs["mu_0.30"], runs["mu_-0.20"]
    truth("C1 (P3): the desks at mu = +0.3 and mu = -0.2 disagree on E^P[payoff] by more than 5 s.e.", abs(a["E_payoff_real_world"]["measured"] - b["E_payoff_real_world"]["measured"]) > 5 * sqrt(a["discounted_mean_payoff"]["se_of_mean"] ** 2 + b["discounted_mean_payoff"]["se_of_mean"] ** 2) * exp(r * params["T"]))

    # C2
    conv = q["convergence"]
    for row in conv["nested"]:
        add(f"C2 n={row['n']:,}: nested Q-estimate is within 5 s.e. of the closed form", row["estimate"], q["closed_form_price"], 5 * row["se"])
    for row in conv["batches"]:
        tol = 5.0 / sqrt(2.0 * row["batches"])      # 5 s.e. of an rms estimated from B batches
        add(f"C2 n={row['n']:,}: rms error of {row['batches']:,} independent batches equals the reported s.e. (within 5 s.e. of the rms, {tol:.0%})", row["rms_error"], row["predicted_se"], tol, "rel")
        add(f"C2 n={row['n']:,}: the forward's batch rms error equals its reported s.e. (within {tol:.0%})", row["forward_rms_error"], row["forward_predicted_se"], tol, "rel")
    add("C2: log-log slope of the batch rms error vs n is -1/2 -- the Monte Carlo error law, measured", conv["slope_rms_error_vs_n"], -0.5, 0.06)
    add("C2: the same slope for the forward", conv["slope_forward_rms_error_vs_n"], -0.5, 0.06)
    add("C2: E^Q[S_T] = S_0 e^(rT) (within 5 s.e.) -- the stock itself is priced by the r-drift", conv["E_Q_S_T"]["measured"], conv["E_Q_S_T"]["expected"], 5 * conv["E_Q_S_T"]["se"])

    # C3
    for k, p in res["paths"].items():
        mu = p["mu"]
        for c in p["checkpoints"]:
            d = c["discounted_S"]
            if abs(mu - r) < 1e-15:
                add(f"C3 Q t={c['t']}: E[e^(-rt) S_t] = S_0 (within 5 s.e.) -- the discounted stock is a martingale under Q", d["mean"], params["S0"], 5 * d["se_of_mean"])
                add(f"C3 Q t={c['t']}: sd of e^(-rt) S_t is S_0 sqrt(e^(sigma^2 t) - 1) (to 3 %) -- a martingale is not a constant", d["sd"], c["expected_sd_under_mu"], 0.03 * slack, "rel")
            else:
                word = "above (a submartingale)" if mu > r else "below (a supermartingale)"
                truth(f"C3 mu={mu:+.2f} t={c['t']}: E[e^(-rt) S_t] is {word} S_0 by more than 5 s.e.", (d["mean"] - params["S0"]) * (1 if mu > r else -1) > 5 * d["se_of_mean"])
                add(f"C3 mu={mu:+.2f} t={c['t']}: E[e^(-rt) S_t] = S_0 e^((mu-r)t) (within 5 s.e.)", d["mean"], c["expected_under_mu"], 5 * d["se_of_mean"])
        add(f"C3 mu={mu:+.2f}: e^(-rt) S_t = S_0 exp(sigma W~_t - 1/2 sigma^2 t) with W~_t = W_t + lambda t path by path (max abs < 1e-9; 2.5's exponential martingale rescaled)", p["identity_max_abs"], 0.0, 1e-9)
        add(f"C3 mu={mu:+.2f}: mean realised variance of the stepped paths is sigma^2 (within 5 s.e.; 2.6's check)", p["realised_variance"]["unweighted"]["mean"], p["realised_variance"]["expected"], 5 * p["realised_variance"]["unweighted"]["se_of_mean"])
        add(f"C3 mu={mu:+.2f}: mean log(S_T/S_0) is (mu - 1/2 sigma^2) T (within 5 s.e.)", p["log_return_T"]["unweighted"]["mean"], p["log_return_T"]["expected_under_mu"], 5 * p["log_return_T"]["unweighted"]["se_of_mean"])

    # C4
    for k, t in runs.items():
        mu, g = t["mu"], t["girsanov"]
        if abs(mu - r) < 1e-15:
            continue
        add(f"C4 mu={mu:+.2f}: the SAME paths reweighted by L = exp(-lambda W_T - 1/2 lambda^2 T) average to the closed form (within 5 s.e.)", g["reweighted_discounted_mean_payoff"]["mean"], t["closed_form_price"], 5 * g["reweighted_discounted_mean_payoff"]["se_of_mean"])
        add(f"C4 mu={mu:+.2f}: the reweighted forward is S_0 - K e^(-rT) (within 5 s.e.)", g["reweighted_forward"]["mean"], t["forward_no_arbitrage"], 5 * g["reweighted_forward"]["se_of_mean"])
        add(f"C4 mu={mu:+.2f}: mean weight is 1 (within 5 s.e.) -- L is a change of measure, not a rescaling", g["mean_L"]["mean"], 1.0, 5 * g["mean_L"]["se_of_mean"])
        add(f"C4 mu={mu:+.2f}: mean L^2 is e^(lambda^2 T) (within 5 s.e.) -- the variance the weights add", g["mean_L2"]["mean"], g["expected_mean_L2"], 5 * g["mean_L2"]["se_of_mean"])
        ess_tol = 5.0 * (2.0 * g["mean_L"]["se_of_mean"] + g["mean_L2"]["se_of_mean"] / g["expected_mean_L2"])
        add(f"C4 mu={mu:+.2f}: the effective sample size is n e^(-lambda^2 T) (within 5 s.e., {ess_tol:.1%}) -- what the weights cost in paths", g["ess_over_n"], g["expected_ess_over_n"], ess_tol, "rel")
        add(f"C4 mu={mu:+.2f}: the reweighted in-the-money fraction is Phi(d2), the Q-probability S_T > K (within 5 s.e.)", g["reweighted_itm_fraction"]["mean"], t["itm_probability_Q"], 5 * g["reweighted_itm_fraction"]["se_of_mean"])
        truth(f"C4 mu={mu:+.2f}: the unweighted in-the-money fraction is more than 5 s.e. from Phi(d2) -- under mu it is a different probability", abs(t["itm_fraction_P"]["mean"] - t["itm_probability_Q"]) > 5 * t["itm_fraction_P"]["se_of_mean"])
    up, down = runs["mu_0.30"]["girsanov"], runs["mu_-0.20"]["girsanov"]
    truth("C4: reweighting paths drawn at mu = +0.3 (towards the call's payoff) gives a SMALLER s.e. than the Q-run; at mu = -0.2 (away from it) a larger one -- the weights are importance sampling, and Q is the drift that needs none",
          up["se_reweighted_price"] < q["discounted_mean_payoff"]["se_of_mean"] < down["se_reweighted_price"])
    for k, p in res["paths"].items():
        mu = p["mu"]
        if abs(mu - r) < 1e-15:
            continue
        add(f"C4 mu={mu:+.2f} paths: the reweighted mean of log(S_T/S_0) is (r - 1/2 sigma^2) T, the Q-drift (within 5 s.e.)", p["log_return_T"]["reweighted"]["mean"], p["log_return_T"]["expected_under_Q"], 5 * p["log_return_T"]["reweighted"]["se_of_mean"])
        truth(f"C4 mu={mu:+.2f} paths: the unweighted and reweighted mean log-returns differ by more than 5 s.e. -- the drift moved", abs(p["log_return_T"]["reweighted"]["mean"] - p["log_return_T"]["unweighted"]["mean"]) > 5 * sqrt(p["log_return_T"]["reweighted"]["se_of_mean"] ** 2 + p["log_return_T"]["unweighted"]["se_of_mean"] ** 2))
        add(f"C4 mu={mu:+.2f} paths: the reweighted mean realised variance is still sigma^2 (within 5 s.e.) -- the volatility did not move", p["realised_variance"]["reweighted"]["mean"], p["realised_variance"]["expected"], 5 * p["realised_variance"]["reweighted"]["se_of_mean"])
        for c in p["checkpoints"]:
            w = c["reweighted_discounted_S"]
            add(f"C4 mu={mu:+.2f} paths t={c['t']}: the reweighted discounted stock has mean S_0 (within 5 s.e.) -- the martingale restored by the weights", w["mean"], params["S0"], 5 * w["se_of_mean"])

    # C5
    fk = res["feynman_kac"]
    for row in fk["rows"]:
        truth(f"C5 tau={row['tau']}: V_MC(t, S) agrees with the closed form at every grid point (within 5 s.e.) -- the Q-expectation is the PDE's solution", row["max_abs_error_in_se"] <= 5.0)
        add(f"C5 tau={row['tau']}: analytic Greeks satisfy the PDE on the grid (max abs < 1e-9; 2.7's check)", row["analytic_residual_max_abs"], 0.0, 1e-9)
        truth(f"C5 tau={row['tau']}: the MC surface's finite-difference PDE residual rms is bounded by the closed form's own FD residual plus 5 x the replication noise", row["pde_residual_rms"] <= row["closed_form_fd_residual_rms"] + 5.0 * row["mc_noise_rms_by_replication"])
        truth(f"C5 tau={row['tau']}: that residual is under {2 * slack:.0f} % of the PDE's largest term, 1/2 sigma^2 S^2 d2V/dS2, in rms", row["pde_residual_rms"] < 0.02 * slack * row["largest_pde_term_rms"])
    return checks


# --- main ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the paths, wider tolerances, no JSON written")
    args = parser.parse_args()

    q = args.quick
    n_term = 100_000 if q else 1_000_000
    params = {
        "seed": args.seed,
        "T": 1.0, "S0": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.40,
        "model": "dS = mu S dt + sigma S dW (drift first); S_T drawn exactly: S_T = S_0 exp((mu - 1/2 sigma^2) T + sigma W_T); paths stepped exactly where needed (C3, C4)",
        "price": "V = e^(-rT) E^Q[payoff], Q the measure with dS = r S dt + sigma S dW~; compared against the closed form, which 2.7 checked against the PDE (setup decision a)",
        "drifts": [-0.2, 0.0, 0.05, 0.1, 0.3, 0.6],
        "n_terminal": n_term, "n_terminal_full": 1_000_000,
        "nested_ns": [1_000, 10_000, 100_000, n_term], "batch_ns": [100, 1_000, 10_000],
        "paths": {"n_paths": 10_000 if q else 100_000, "n_steps": 256, "chunk": 10_000,
                  "checkpoints": [0.25, 0.5, 0.75, 1.0], "drifts": [0.05, 0.3, -0.2]},
        "feynman_kac": {"n_per_point": 100_000 if q else 1_000_000, "S": [50.0, 200.0, 16], "taus": [1.0, 0.5],
                        "h_rel": 0.02, "replications": 2},
    }
    T, S0, K, r, sigma = params["T"], params["S0"], params["K"], params["r"], params["sigma"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    phi_err = phi_self_test()
    print(f"[2.8] Phi self-test: max abs error {phi_err:.2e}", flush=True)
    V = float(call_price(S0, T, K, r, sigma))
    print(f"[2.8] closed form: r = {r}, sigma = {sigma}, S_0 = K = {S0:.0f}, T = {T}: V = {V:.4f}; forward S_0 - K e^(-rT) = {forward_price(S0, T, K, r):.4f}", flush=True)

    terminal = {}
    for mu in params["drifts"]:
        label = f"mu_{mu:.2f}"
        print(f"[2.8] terminal draws: drift mu = {mu:+.2f}{' (= r: the Q-run)' if abs(mu - r) < 1e-15 else ''}, sigma = {sigma}; {n_term:,} paths, lambda = {(mu - r) / sigma:+.3f}", flush=True)
        terminal[label] = terminal_run(rng, n_term, S0, K, T, r, mu, sigma, params["nested_ns"], params["batch_ns"], label)

    P = params["paths"]
    paths = {}
    for mu in P["drifts"]:
        label = f"mu_{mu:.2f}"
        print(f"[2.8] stepped paths: drift mu = {mu:+.2f}, sigma = {sigma}; {P['n_paths']:,} paths x {P['n_steps']} exact steps, checkpoints {P['checkpoints']}", flush=True)
        paths[label] = path_run(rng, P["n_paths"], P["n_steps"], P["chunk"], S0, T, r, mu, sigma, P["checkpoints"], label)

    F = params["feynman_kac"]
    print(f"[2.8] Feynman-Kac: V_MC(t, S) on S in {F['S']}, tau in {F['taus']}; {F['n_per_point']:,} common draws per point, h = {F['h_rel']:.0%}, {F['replications']} replications", flush=True)
    fk = feynman_kac(rng, F["n_per_point"], F["S"][0], F["S"][1], F["S"][2], F["taus"], F["h_rel"], K, r, sigma, F["replications"])

    results = {"phi_max_abs_error": phi_err, "closed_form_price": V, "forward_no_arbitrage": forward_price(S0, T, K, r),
               "terminal": terminal, "paths": paths, "feynman_kac": fk}
    checks = build_checks(results, params)

    out = {"page": "2.8", "script": Path(__file__).name, "params": params,
           "environment": {"numpy": np.__version__}, "results": results, "checks": checks}
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.8] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  ({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.8] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
