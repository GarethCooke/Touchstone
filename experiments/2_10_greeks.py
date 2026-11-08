"""Greeks -- the experiment behind page 2.10.

Serves page 2.10 (docs/quant-learn-index-v1.md). Page 2.9 derived the
Black-Scholes call price

    C = S_0 e^(-qT) N(d_1) - K e^(-rT) N(d_2),
    d_1 = (ln(S_0/K) + (r - q + 1/2 sigma^2) T) / (sigma sqrt T),   d_2 = d_1 - sigma sqrt T,

and met its first derivative, the delta Delta = dC/dS_0 = e^(-qT) N(d_1), as the
hedge ratio of page 2.7. This page differentiates the rest of the formula. The
Greeks are the partial derivatives of the price with respect to its inputs,
each with a name:

    Delta = dV/dS        delta        the hedge ratio (2.7, 2.9)
    Gamma = d^2V/dS^2    gamma        the delta's own sensitivity to spot (2.7)
    vega  = dV/dsigma    vega         the price's sensitivity to volatility
    Theta = dV/dt        theta        the price's sensitivity to the passage of time
    rho   = dV/dr        rho          the price's sensitivity to the risk-free rate

(and dV/dq, the dividend-rho, which the oracle carries). The closed forms, with
phi the standard normal density and w = +1 for a call, -1 for a put:

    Delta = w e^(-qT) N(w d_1)
    Gamma = e^(-qT) phi(d_1) / (S sigma sqrt T)
    vega  = S e^(-qT) phi(d_1) sqrt T
    Theta = -S e^(-qT) phi(d_1) sigma / (2 sqrt T) - w r K e^(-rT) N(w d_2) + w q S e^(-qT) N(w d_1)
    rho   = w K T e^(-rT) N(w d_2)
    dV/dq = -w T S e^(-qT) N(w d_1)

Units are raw partials, as the golden file and the T0 decision have them: vega
per 1.00 of volatility, Theta per year, rho per 1.00 of rate (the owner's
ruling Q2/a at S10; desk conventions -- per vol point, per day, per basis
point -- are a display scaling the page names once). The PDE of page 2.7,

    Theta + 1/2 sigma^2 S^2 Gamma + r S Delta - r V = 0,

is re-read on this page as a statement about a delta-hedged book's P&L: theta
pays for gamma. Session S10's setup decisions (owner, 2026-11-05): (Q1/a) the
gamma P&L -- hedged at sigma_i while the stock moves at sigma_r the mean P&L is
(sigma_r^2 - sigma_i^2) x E[Sum e^(-rt) 1/2 Gamma S^2 dt] -- is 2.7's measured
result (-3.76 +- 0.02, 0.00 +- 0.003, +3.74 +- 0.03 at sigma_r = 0.3, 0.4, 0.5),
cited and re-read, not re-measured; what is new here is the per-step attribution
of the option's change on the hedged book (C3). (Q2/a) raw units, above. (Q3/a)
the put's Greeks beside the call's, through parity (C5).

  C1  Analytic against bump-and-revalue. Delta, Gamma, vega, Theta, rho and the
      dividend-rho by central differences of 2.9's closed form, at the base case
      and across the 216-point grid of (S_0, K, r, q, sigma, T) 2.9 used, one bump
      size per Greek (5 x 10^-5 relative in S, sigma and T; 10^-5 absolute in r and
      q; 10^-4 relative for Gamma's second difference), against the closed forms
      above, to 10^-7. The bump-size study for Gamma alone -- the error against
      h from 10^-1 to 10^-6 relative, truncation falling as h^2 and round-off
      rising as 1/h^2, the best h in between -- is recorded to say why page 3.5
      exists; the systematic study of bump sizes and Monte Carlo Greeks is 3.5's. Also the two moves the predictions asked about: the stock from
      100 to 101 (the actual change against Delta x 1 and Delta x 1 + 1/2 Gamma x 1^2)
      and sigma from 0.40 to 0.41 (against vega x 0.01).
  C2  The oracle (I4). All seven columns of golden/bs_vanilla.json -- price,
      delta, gamma, vega, theta, rho, dividend_rho -- against the closed forms
      at 7,200 grid rows and 34 edge rows, to the file's own tolerances (raw
      partials as the file has them); QuantLib-Python's BlackCalculator live at
      the page's grid for the same seven. The first time the golden Greeks are
      read on an S page (2.9 read price and delta).
  C3  The PDE as a P&L statement, on paths. 2.7's hedged book re-simulated with
      2.7's hedge (the same code, chunked the same way) at sigma_r = sigma_i = 0.4,
      mu = 0, N = 256 and 4096 steps over 4,000 paths: on every step the option's
      change dV is attributed to Theta dt + Delta dS + 1/2 Gamma dS^2 (Taylor to
      second order, 2.5's lemma on a grid) with the remainder measured; the hedge
      removes the Delta dS term and the cash leg adds (r S Delta - r V) dt, so the
      hedged book's step is Theta dt + 1/2 Gamma dS^2 + (r S Delta - r V) dt plus
      the remainder. Summed along each path and discounted: the gamma gain
      Sum e^(-rt) 1/2 Gamma dS^2, the theta cost Sum e^(-rt) Theta dt, the carry
      Sum e^(-rt) (r S Delta - r V) dt. The identity measured: by the PDE the theta
      cost plus the carry equals -Sum e^(-rt) 1/2 sigma_i^2 S^2 Gamma dt on every
      path (10^-12), so the hedged P&L is Sum e^(-rt) 1/2 Gamma S^2 ((dS/S)^2 -
      sigma_i^2 dt) -- 2.7's gamma P&L row -- plus the remainder; its mean is
      zero within 5 s.e. (theta pays for gamma, on average, exactly), and the
      gamma gain's mean equals minus the theta cost's and the carry's. The same
      attribution at sigma_r = 0.3 and 0.5 shows the gamma gain growing with
      sigma_r^2 while the theta cost does not move with it: the mean hedged
      P&L is (sigma_r^2 - sigma_i^2) x mean(Sum e^(-rt) 1/2 Gamma S^2 dt) within
      5 s.e. on these paths -- the per-step view of 2.7's result, which is
      recorded beside it as the citation (cited, not re-measured: Q1/a).
  C4  Shapes, for D6. Each Greek against S on [40, 200] at tau = 1, 1/2, 1/4 and
      0.05: Delta from 0 to 1 (monotone); Gamma peaking at S = K e^(-(r + 3/2
      sigma^2) tau) -- 74.8 at tau = 1, below the strike -- and at the strike as
      tau -> 0; vega peaking at S = K e^((1/2 sigma^2 - r) tau) = 103.0 at tau = 1;
      Theta most negative near the strike and collapsing onto it. Against T at
      the money: Gamma sqrt T, vega / sqrt T and Theta sqrt T tend to phi(0)/(S
      sigma), S phi(0) and -S sigma phi(0)/2 as T -> 0 (Gamma and -Theta blow up
      like 1/sqrt T, vega vanishes like sqrt T).
  C5  Parity's Greeks. Differentiating C - P = S_0 e^(-qT) - K e^(-rT): Delta_P =
      Delta_C - e^(-qT), Gamma_P = Gamma_C, vega_P = vega_C, Theta_P - Theta_C =
      r K e^(-rT) - q S_0 e^(-qT), rho_P - rho_C = -K T e^(-rT), across the grid
      to 10^-12; the put's Greeks at the base case (Delta = -0.373, Theta = -5.05,
      rho = -50.4).
  D6  Fixtures for the Black-Scholes pricer demo (2.9-2.10): the five Greeks of
      the call and the put against S on 2.9's grid at the four tau; the Greeks
      at the base case for the demo's readout. Fixtures carry no claim beyond
      C1-C5; the site draws them (I15).

Run from the repository root:

    uv run experiments/2_10_greeks.py [--seed 20261105] [--quick]

--quick runs a tenth of the paths and N = 256 only, and NO JSON is written --
the committed result is always the full run (I3). Under --quick the live
QuantLib comparison and the golden-file comparison are skipped with a notice if
QuantLib or the file is not present; the full run requires both (I4).

Writes 2_10_greeks.json beside this file: parameters in, results out, no
timestamps -- same seed, same file (I6). No plotting here; the site draws (see
experiments/README.md). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import erf, exp, log, pi, sqrt
from pathlib import Path

import numpy as np


# --- the normal CDF and density, vectorised ----------------------------------------
#
# numpy has no erf. Hart's 1968 rational approximation as given by West (2005),
# accurate to about 1e-14 in double precision; main() checks it against math.erf
# before anything else runs (copied from 2_9_black_scholes_formula.py). On the
# page the function is N(.); the code keeps 2.6's name Phi.


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


def phi(x) -> np.ndarray:
    """The standard normal density phi(z) = e^(-z^2/2) / sqrt(2 pi)."""
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x * x) / sqrt(2.0 * pi)


def phi_self_test() -> float:
    xs = np.linspace(-9.0, 9.0, 36001)
    ref = np.array([0.5 * (1.0 + erf(v / sqrt(2.0))) for v in xs])
    return float(np.abs(Phi(xs) - ref).max())


# --- the closed form and its Greeks, as the page writes them ---------------------------


def d1_d2(S, K, r, q, sigma, T):
    S = np.asarray(S, dtype=float)
    st = sigma * sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / st
    return d1, d1 - st


def price(S, K, r, q, sigma, T, w=1):
    """w = +1 the call C = S e^(-qT) N(d_1) - K e^(-rT) N(d_2); w = -1 the put."""
    S = np.asarray(S, dtype=float)
    d1, d2 = d1_d2(S, K, r, q, sigma, T)
    return w * (S * exp(-q * T) * Phi(w * d1) - K * exp(-r * T) * Phi(w * d2))


def greeks(S, K, r, q, sigma, T, w=1) -> dict:
    """The five Greeks and the dividend-rho of a call (w = +1) or put (w = -1), raw partials."""
    S = np.asarray(S, dtype=float)
    d1, d2 = d1_d2(S, K, r, q, sigma, T)
    eq, er, st = exp(-q * T), exp(-r * T), sigma * sqrt(T)
    nd1 = phi(d1)
    V = w * (S * eq * Phi(w * d1) - K * er * Phi(w * d2))
    return {
        "price": V,
        "delta": w * eq * Phi(w * d1),
        "gamma": eq * nd1 / (S * st),
        "vega": S * eq * nd1 * sqrt(T),
        "theta": -S * eq * nd1 * sigma / (2.0 * sqrt(T)) - w * r * K * er * Phi(w * d2) + w * q * S * eq * Phi(w * d1),
        "rho": w * K * T * er * Phi(w * d2),
        "dividend_rho": -w * T * S * eq * Phi(w * d1),
    }


GREEK_NAMES = ["delta", "gamma", "vega", "theta", "rho", "dividend_rho"]


def theta_pieces(S, K, r, q, sigma, T) -> dict:
    """The call's theta split as the PDE splits it: -1/2 sigma^2 S^2 Gamma (the gamma term)
    and -(r S Delta - r V) (the carry), which sum to Theta exactly."""
    g = greeks(S, K, r, q, sigma, T)
    gamma_term = -0.5 * sigma * sigma * float(S) ** 2 * float(g["gamma"])
    carry_term = -(r * float(S) * float(g["delta"]) - r * float(g["price"]))
    return {"theta": float(g["theta"]), "gamma_term": gamma_term, "carry_term": carry_term,
            "sum_of_pieces": gamma_term + carry_term, "pde_residual": float(g["theta"]) - gamma_term - carry_term}


# --- C1: bump-and-revalue --------------------------------------------------------------


def bump_greeks(S, K, r, q, sigma, T, w, h_rel) -> dict:
    """Central differences of the closed form. First derivatives in S, sigma and T with the
    step h = h_rel["first"] x the input; in r and q with the absolute step h_rel["rate"] (the
    rates may be zero); Gamma by the second central difference in S with h_rel["gamma"] x S."""
    S = float(S)
    hS, hs, hT = h_rel["first"] * S, h_rel["first"] * sigma, h_rel["first"] * T
    hr, hq = h_rel["rate"], h_rel["rate"]                      # absolute: r and q may be zero
    hG = h_rel["gamma"] * S
    f = lambda **kw: float(price(kw.get("S", S), K, kw.get("r", r), kw.get("q", q), kw.get("sigma", sigma), kw.get("T", T), w))
    return {
        "delta": (f(S=S + hS) - f(S=S - hS)) / (2 * hS),
        "gamma": (f(S=S + hG) - 2 * f() + f(S=S - hG)) / (hG * hG),
        "vega": (f(sigma=sigma + hs) - f(sigma=sigma - hs)) / (2 * hs),
        "theta": -(f(T=T + hT) - f(T=T - hT)) / (2 * hT),      # d/dt = -d/dT
        "rho": (f(r=r + hr) - f(r=r - hr)) / (2 * hr),
        "dividend_rho": (f(q=q + hq) - f(q=q - hq)) / (2 * hq),
    }


def gamma_bump_study(S, K, r, q, sigma, T, h_rels) -> list[dict]:
    """Gamma by the second central difference against h (relative to S): the error
    against the closed form, truncation ~ h^2 and round-off ~ eps/h^2."""
    g = float(greeks(S, K, r, q, sigma, T)["gamma"])
    rows = []
    for h_rel in h_rels:
        h = h_rel * S
        est = (float(price(S + h, K, r, q, sigma, T)) - 2 * float(price(S, K, r, q, sigma, T)) + float(price(S - h, K, r, q, sigma, T))) / (h * h)
        rows.append({"h_rel": h_rel, "h": h, "gamma_bump": est, "error": est - g, "abs_error": abs(est - g)})
    return rows


# --- C3: 2.7's hedge, re-run with the per-step attribution ---------------------------------


def hedge_chunk_attributed(S, T, K, r, sigma_i) -> dict[str, np.ndarray]:
    """2.7's `hedge_chunk` for the call, with the option's change on every step attributed.

    S: m paths x (N+1) prices on an even grid. Per path, discounted to 0:
      dV_sum      Sum e^(-rt) (V_{i+1} - V_i)                       the option's actual change
      delta_term  Sum e^(-rt) Delta dS                              what the hedge removes
      gamma_gain  Sum e^(-rt) 1/2 Gamma dS^2
      theta_cost  Sum e^(-rt) Theta dt
      carry       Sum e^(-rt) (r S Delta - r V) dt                  the cash leg, to first order
      carry_exact Sum e^(-rt) (r S Delta - V) (e^(r dt) - 1)       2.7's cash leg exactly
      remainder   Sum e^(-rt) [(V_{i+1} - V_i) - (Theta dt + Delta dS + 1/2 Gamma dS^2)]
      gamma_dt    Sum e^(-rt) 1/2 Gamma S^2 sigma_i^2 dt            what the price assumed the gamma gain would be
      hedged      2.7's pnl_disc: Sum e^(-rt) [(V_{i+1} - V_i) - Delta dS - carry_exact step]
      pde_max     max |PDE residual| at the points visited
    On the last step V_{i+1} is the payoff, as in 2.7.
    """
    m, Np1 = S.shape
    N = Np1 - 1
    dt = T / N
    accr = exp(r * dt) - 1.0
    Si = S[:, 0]
    g = greeks(Si, K, r, 0.0, sigma_i, T)
    V, delta, gamma, theta = g["price"], g["delta"], g["gamma"], g["theta"]
    V0 = V.copy()
    acc = {k: np.zeros(m) for k in ("dV_sum", "delta_term", "gamma_gain", "theta_cost", "carry", "carry_exact", "remainder", "gamma_dt", "hedged")}
    pde_max = 0.0
    for i in range(N):
        tau_next = T - (i + 1) * dt
        S1 = S[:, i + 1]
        if i + 1 < N:
            g1 = greeks(S1, K, r, 0.0, sigma_i, tau_next)
            V1, d1, gm1, th1 = g1["price"], g1["delta"], g1["gamma"], g1["theta"]
        else:
            V1 = np.maximum(S1 - K, 0.0)
            d1 = gm1 = th1 = None
        dS = S1 - Si
        df = exp(-r * (i + 1) * dt)
        dV = V1 - V
        taylor = theta * dt + delta * dS + 0.5 * gamma * dS * dS
        carry_exact = (V - delta * Si) * accr
        acc["dV_sum"] += df * dV
        acc["delta_term"] += df * delta * dS
        acc["gamma_gain"] += df * 0.5 * gamma * dS * dS
        acc["theta_cost"] += df * theta * dt
        acc["carry"] += df * (r * Si * delta - r * V) * dt
        acc["carry_exact"] += df * (-carry_exact)
        acc["remainder"] += df * (dV - taylor)
        acc["gamma_dt"] += df * 0.5 * gamma * Si * Si * sigma_i * sigma_i * dt
        acc["hedged"] += df * (dV - delta * dS - carry_exact)
        pde = theta + 0.5 * sigma_i * sigma_i * Si * Si * gamma + r * Si * delta - r * V
        pde_max = max(pde_max, float(np.abs(pde).max()))
        Si, V, delta, gamma, theta = S1, V1, d1, gm1, th1
    acc["pde_max"] = np.array([pde_max])
    acc["V0"] = V0
    return acc


def stats(x: np.ndarray) -> dict[str, float]:
    sd = float(x.std(ddof=1))
    return {"mean": float(x.mean()), "sd": sd, "se_of_mean": sd / sqrt(x.size), "rms": float(sqrt((x * x).mean())),
            "max_abs": float(np.abs(x).max()), "n": int(x.size)}


def attribution_scenario(rng, n_paths, n_fine, Ns, chunk_paths, T, S0, K, r, mu, sigma_r, sigma_i, label, cited) -> dict:
    """Draw n_paths exact-GBM paths at n_fine steps (2.7's way), hedge each at every N, attribute."""
    dt_f = T / n_fine
    keys = ("dV_sum", "delta_term", "gamma_gain", "theta_cost", "carry", "carry_exact", "remainder", "gamma_dt", "hedged")
    acc = {N: {k: [] for k in keys} for N in Ns}
    pde_max = {N: 0.0 for N in Ns}
    realised = []
    for start in range(0, n_paths, chunk_paths):
        m = min(chunk_paths, n_paths - start)
        Z = rng.standard_normal((m, n_fine))
        logS = np.empty((m, n_fine + 1))
        logS[:, 0] = log(S0)
        np.cumsum((mu - 0.5 * sigma_r * sigma_r) * dt_f + sigma_r * sqrt(dt_f) * Z, axis=1, out=logS[:, 1:])
        logS[:, 1:] += log(S0)
        S_fine = np.exp(logS)
        realised.append(np.diff(logS, axis=1).std(axis=1, ddof=1) * sqrt(n_fine / T))
        for N in Ns:
            S = S_fine[:, :: n_fine // N].copy()
            h = hedge_chunk_attributed(S, T, K, r, sigma_i)
            for k in keys:
                acc[N][k].append(h[k])
            pde_max[N] = max(pde_max[N], float(h["pde_max"][0]))
    realised = np.concatenate(realised)
    per_N = []
    for N in Ns:
        c = {k: np.concatenate(v) for k, v in acc[N].items()}
        # the identities, per path
        pde_identity = c["theta_cost"] + c["carry"] + c["gamma_dt"]                      # = 0 by the PDE, to round-off
        attribution = c["dV_sum"] - (c["theta_cost"] + c["delta_term"] + c["gamma_gain"] + c["remainder"])   # = 0 exactly
        hedged_from_pieces = c["theta_cost"] + c["gamma_gain"] + c["carry"] + c["remainder"]                # ~ hedged (carry to first order)
        gamma_pnl = c["gamma_gain"] - c["gamma_dt"]                                      # 2.7's gamma P&L row
        per_N.append({
            "N": N, "dt": T / N,
            "option_change": stats(c["dV_sum"]),
            "delta_term": stats(c["delta_term"]),
            "gamma_gain": stats(c["gamma_gain"]),
            "theta_cost": stats(c["theta_cost"]),
            "carry": stats(c["carry"]),
            "carry_exact": stats(c["carry_exact"]),
            "remainder": stats(c["remainder"]),
            "gamma_dt": stats(c["gamma_dt"]),
            "hedged_pnl_discounted": stats(c["hedged"]),
            "gamma_pnl": stats(gamma_pnl),
            "attribution_identity_max_abs": float(np.abs(attribution).max()),
            "pde_identity_max_abs": float(np.abs(pde_identity).max()),
            "hedged_minus_pieces": stats(c["hedged"] - hedged_from_pieces),
            "hedged_minus_gamma_pnl": stats(c["hedged"] - gamma_pnl),
            "gamma_gain_plus_theta_plus_carry": stats(c["gamma_gain"] + c["theta_cost"] + c["carry"]),
            "mean_predicted_by_vol_gap": (sigma_r ** 2 - sigma_i ** 2) * float((c["gamma_dt"] / (sigma_i ** 2)).mean()),
            "gamma_integral_mean": float((c["gamma_dt"] / (sigma_i ** 2)).mean()),
            "pde_residual_max_abs_at_visited_points": pde_max[N],
        })
    return {"label": label, "mu": mu, "sigma_realised": sigma_r, "sigma_implied": sigma_i, "n_paths": n_paths, "n_fine": n_fine,
            "realised_vol": {"mean": float(realised.mean()), "sd": float(realised.std(ddof=1)), "expected": sigma_r},
            "per_N": per_N, "cited_from_2_7": cited}


# --- C4: shapes ---------------------------------------------------------------------------


def shapes_against_S(K, r, sigma, taus, S_lo, S_hi, n_S) -> dict:
    S = np.linspace(S_lo, S_hi, n_S)
    out = {"S": S.tolist(), "taus": taus, "curves": {}}
    for tau in taus:
        gc = greeks(S, K, r, 0.0, sigma, tau, +1)
        gp = greeks(S, K, r, 0.0, sigma, tau, -1)
        i_g, i_v, i_t = int(np.argmax(gc["gamma"])), int(np.argmax(gc["vega"])), int(np.argmin(gc["theta"]))
        out["curves"][f"tau_{tau:g}"] = {
            "tau": tau,
            "call": {k: gc[k].tolist() for k in ("price", "delta", "gamma", "vega", "theta", "rho")},
            "put": {k: gp[k].tolist() for k in ("price", "delta", "gamma", "vega", "theta", "rho")},
            "gamma_peak": {"S_on_grid": float(S[i_g]), "S_closed_form": K * exp(-(r + 1.5 * sigma * sigma) * tau),
                           "gamma_at_peak": float(gc["gamma"][i_g]), "gamma_at_strike": float(greeks(K, K, r, 0.0, sigma, tau)["gamma"])},
            "vega_peak": {"S_on_grid": float(S[i_v]), "S_closed_form": K * exp((0.5 * sigma * sigma - r) * tau),
                          "vega_at_peak": float(gc["vega"][i_v]), "vega_at_strike": float(greeks(K, K, r, 0.0, sigma, tau)["vega"])},
            "theta_trough": {"S_on_grid": float(S[i_t]), "theta_at_trough": float(gc["theta"][i_t]),
                             "theta_at_strike": float(greeks(K, K, r, 0.0, sigma, tau)["theta"])},
            "delta_monotone": bool(np.all(np.diff(gc["delta"]) > 0)),
            "delta_range": [float(gc["delta"][0]), float(gc["delta"][-1])],
        }
    return out


def shapes_against_T(S0, K, r, sigma, Ts) -> dict:
    rows = []
    for T in Ts:
        g = greeks(S0, K, r, 0.0, sigma, T)
        rows.append({"T": T, "gamma": float(g["gamma"]), "vega": float(g["vega"]), "theta": float(g["theta"]), "delta": float(g["delta"]), "rho": float(g["rho"]),
                     "gamma_sqrtT": float(g["gamma"]) * sqrt(T), "vega_over_sqrtT": float(g["vega"]) / sqrt(T), "theta_sqrtT": float(g["theta"]) * sqrt(T)})
    return {"Ts": Ts, "rows": rows,
            "limits": {"gamma_sqrtT": float(phi(0.0)) / (S0 * sigma), "vega_over_sqrtT": S0 * float(phi(0.0)), "theta_sqrtT": -S0 * sigma * float(phi(0.0)) / 2.0}}


# --- C2: the oracle -------------------------------------------------------------------------


def quantlib_live(grid_points) -> dict | None:
    try:
        import QuantLib as ql
    except ImportError:
        return None
    worst = {k: 0.0 for k in ("price", *GREEK_NAMES)}
    for (S, k, rr, qq, sg, t) in grid_points:
        F = S * exp((rr - qq) * t)
        disc = exp(-rr * t)
        for w, typ in ((+1, ql.Option.Call), (-1, ql.Option.Put)):
            bc = ql.BlackCalculator(ql.PlainVanillaPayoff(typ, k), F, sg * sqrt(t), disc)
            g = greeks(S, k, rr, qq, sg, t, w)
            ours = {"price": float(g["price"]), "delta": float(g["delta"]), "gamma": float(g["gamma"]), "vega": float(g["vega"]),
                    "theta": float(g["theta"]), "rho": float(g["rho"]), "dividend_rho": float(g["dividend_rho"])}
            theirs = {"price": bc.value(), "delta": bc.delta(S), "gamma": bc.gamma(S), "vega": bc.vega(t),
                      "theta": bc.theta(S, t), "rho": bc.rho(t), "dividend_rho": bc.dividendRho(t)}
            for key in worst:
                worst[key] = max(worst[key], abs(ours[key] - theirs[key]))
    return {"version": ql.__version__, "binding": "QuantLib-Python", "engine": "BlackCalculator(forward, sigma sqrt T, discount); delta(spot), gamma(spot), vega(T), theta(spot, T), rho(T), dividendRho(T)",
            "n_points": len(grid_points), "call_and_put": True, **{f"max_abs_error_{k}": v for k, v in worst.items()}}


def golden_file_check(script_dir: Path) -> dict | None:
    candidates = [script_dir.parent / "golden" / "bs_vanilla.json", script_dir.parent / "bs_vanilla.json"]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        g = json.load(f)
    tol = g["tolerances"]
    cols = ["price", *GREEK_NAMES]

    def block(rows, tolerance):
        worst = {k: 0.0 for k in cols}
        worst_row = {k: None for k in cols}
        for c in rows:
            S, k, sg, rr, qq, t = c["spot"], c["strike"], c["vol"], c["rate"], c["dividend_yield"], c["expiry_years"]
            w = 1 if c["type"] == "call" else -1
            ours = greeks(S, k, rr, qq, sg, t, w)
            label = c.get("label", f"{c['type']} S={S} K={k} vol={sg} r={rr} q={qq} T={t:.4f}")
            for key in cols:
                ref = c[key]
                e = abs(float(ours[key]) - ref) / (abs(ref) if abs(ref) > 1.0 else 1.0)    # the file's rule
                if e > worst[key]:
                    worst[key], worst_row[key] = e, label
        return {"n": len(rows), "tolerance": tolerance, **{f"worst_{k}_error": worst[k] for k in cols}, **{f"worst_{k}_row": worst_row[k] for k in cols}}

    return {"file": str(path.relative_to(script_dir.parent)), "schema": g["schema"], "oracle": g["oracle"],
            "units": {k: g["conventions"].get(k) for k in cols} if isinstance(g.get("conventions"), dict) else None,
            "cases": block(g["cases"], tol["cases"]), "edge_cases": block(g["edge_cases"], tol["edge_cases"]), "tolerance_rule": tol["note"]}


# --- checks ---------------------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected), "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    def within_se(claim, block, target, k=5.0):
        add(claim + " (within 5 s.e.)", block["mean"], target, k * block["se_of_mean"])

    add("Phi: Hart/West normal CDF agrees with math.erf on [-9, 9] (max abs diff < 1e-13)", res["phi_max_abs_error"], 0.0, 1e-13)

    # C1 -- bump-and-revalue
    B = res["bump"]
    tols = params["bump_tolerance"]
    for name in GREEK_NAMES:
        add(f"C1 base case: {name} by central bump = the closed form (tolerance {tols[name]:.0e})", B["base"]["bump"][name], B["base"]["analytic"][name], tols[name])
        add(f"C1 the put at the base case: {name} by central bump = the closed form", B["base_put"]["bump"][name], B["base_put"]["analytic"][name], tols[name])
        add(f"C1 across the {B['grid']['n_points']}-point grid, call and put: max |bump - closed form| for {name}", B["grid"][f"max_abs_error_{name}"], 0.0, tols[name])
    st = B["gamma_bump_study"]
    i_min = int(np.argmin([r_["abs_error"] for r_ in st]))
    truth("C1 the Gamma bump study: the error is smallest at an intermediate h (truncation on one side, round-off on the other)", 0 < i_min < len(st) - 1)
    truth("C1 the Gamma bump study: the error at h = 10^-6 relative exceeds the error at the chosen h by 100x (round-off)", st[-1]["abs_error"] > 100 * st[i_min]["abs_error"])
    truth("C1 the Gamma bump study: the error at h = 10^-1 relative exceeds the error at the chosen h by 100x (truncation)", st[0]["abs_error"] > 100 * st[i_min]["abs_error"])
    truth(f"C1 the Gamma bump study: the chosen h = {params['bump_h_rel']['gamma']:g} relative is the study's best", abs(st[i_min]["h_rel"] - params["bump_h_rel"]["gamma"]) < 1e-15)
    M = res["moves"]["spot_100_to_101"]
    add("C1 the stock 100 -> 101: the actual change in C against Delta x 1 (the first-order estimate, within 0.01)", M["actual_change"], M["first_order"], 0.01)
    truth("C1 the stock 100 -> 101: the actual change exceeds Delta x 1 (Gamma > 0)", M["actual_change"] > M["first_order"])
    add("C1 the stock 100 -> 101: the actual change against Delta x 1 + 1/2 Gamma x 1^2 (second order, within 1e-4)", M["actual_change"], M["second_order"], 1e-4)
    M = res["moves"]["spot_100_to_99"]
    truth("C1 the stock 100 -> 99: the fall in C is smaller than Delta x 1 (Gamma > 0 again)", abs(M["actual_change"]) < abs(M["first_order"]))
    M = res["moves"]["vol_0.40_to_0.41"]
    add("C1 sigma 0.40 -> 0.41: the actual change in C against vega x 0.01 (within 1e-3)", M["actual_change"], M["first_order"], 1e-3)
    add("C1 vega per vol point = vega per unit / 100 (the display scaling, exactly)", M["first_order"], res["base_case"]["call"]["vega"] / 100.0, 1e-15)

    # the base case
    bc = res["base_case"]
    add("base case: Delta = N(d_1) = 0.6274 (2.9's number)", bc["call"]["delta"], 0.6274, 5e-5)
    add("base case: Theta = -1/2 sigma^2 S^2 Gamma - r K e^(-rT) N(d_2), the two pieces summing exactly (1e-12)", bc["theta_pieces"]["pde_residual"], 0.0, 1e-12)
    add("base case: Gamma = phi(d_1) / (S sigma sqrt T) (1e-15)", bc["call"]["gamma"], float(phi(bc["d1"])) / (params["S0"] * params["sigma"] * sqrt(params["T"])), 1e-15)
    add("base case: vega = S phi(d_1) sqrt T (1e-12)", bc["call"]["vega"], params["S0"] * float(phi(bc["d1"])) * sqrt(params["T"]), 1e-12)
    add("base case: rho = K T e^(-rT) N(d_2), the strike piece's T-weight (1e-12)", bc["call"]["rho"], params["K"] * params["T"] * exp(-params["r"] * params["T"]) * float(Phi(bc["d2"])), 1e-12)
    add("base case: the dividend-rho = -T S_0 N(d_1), the stock piece's T-weight (1e-12)", bc["call"]["dividend_rho"], -params["T"] * params["S0"] * float(Phi(bc["d1"])), 1e-12)
    add("base case: the PDE Theta + 1/2 sigma^2 S^2 Gamma + r S Delta - r V = 0 on the closed form (1e-12)", bc["pde_residual"], 0.0, 1e-12)

    # C2 -- the oracle
    O = res["oracle"]
    if O["live"] is not None:
        for name in ["price", *GREEK_NAMES]:
            add(f"C2 QuantLib {O['live']['version']} BlackCalculator at the grid, call and put: max |{name} - closed form| (1e-10)", O["live"][f"max_abs_error_{name}"], 0.0, 1e-10)
    elif not params["quick"]:
        truth("C2 QuantLib-Python present for the live oracle comparison (I4) -- required for the full run", False)
    if O["golden"] is not None:
        g = O["golden"]
        for name in ["price", *GREEK_NAMES]:
            add(f"C2 golden/bs_vanilla.json (QuantLib {g['oracle']['version']}): {g['cases']['n']} grid cases, worst {name} error within the file's tolerance", g["cases"][f"worst_{name}_error"], 0.0, g["cases"]["tolerance"])
            add(f"C2 golden edge cases ({g['edge_cases']['n']}): worst {name} error within the file's tolerance", g["edge_cases"][f"worst_{name}_error"], 0.0, g["edge_cases"]["tolerance"])
        truth("C2 the golden file records its QuantLib version (I4)", bool(g["oracle"].get("version")))
    elif not params["quick"]:
        truth("C2 golden/bs_vanilla.json present for the committed-oracle comparison (I4) -- required for the full run", False)

    # C3 -- the PDE as a P&L statement on paths
    for key, sc in res["attribution"].items():
        lab = f"sigma_r = {sc['sigma_realised']}"
        add(f"C3 {lab}: the realised volatility of the paths is sigma_r (within 5 s.e.)", sc["realised_vol"]["mean"], sc["sigma_realised"], 5 * sc["realised_vol"]["sd"] / sqrt(sc["n_paths"]))
        for p in sc["per_N"]:
            N = p["N"]
            add(f"C3 {lab}, N = {N}: the attribution dV = Theta dt + Delta dS + 1/2 Gamma dS^2 + remainder is exact per path (1e-10)", p["attribution_identity_max_abs"], 0.0, 1e-10)
            add(f"C3 {lab}, N = {N}: theta cost + carry + Sum e^(-rt) 1/2 sigma_i^2 S^2 Gamma dt = 0 on every path (the PDE, 1e-9)", p["pde_identity_max_abs"], 0.0, 1e-9)
            add(f"C3 {lab}, N = {N}: the PDE residual at every visited point (1e-12)", p["pde_residual_max_abs_at_visited_points"], 0.0, 1e-12)
            add(f"C3 {lab}, N = {N}: the hedged P&L is theta cost + gamma gain + carry + remainder, per path (rms, the e^(r dt) - 1 vs r dt gap only, < 1e-2)", p["hedged_minus_pieces"]["rms"], 0.0, 1e-2)
            add(f"C3 {lab}, N = {N}: the hedged P&L is 2.7's gamma P&L Sum e^(-rt) 1/2 Gamma S^2 ((dS/S)^2 - sigma_i^2 dt) plus the remainder (rms of the gap vs the remainder's rms, within 1e-2)",
                p["hedged_minus_gamma_pnl"]["rms"], p["remainder"]["rms"], 1e-2)
            if sc["sigma_realised"] == sc["sigma_implied"]:
                within_se(f"C3 {lab}, N = {N}: gamma gain + theta cost + carry has mean zero -- theta pays for gamma", p["gamma_gain_plus_theta_plus_carry"], 0.0)
                within_se(f"C3 {lab}, N = {N}: the gamma gain's mean equals minus the theta cost's and the carry's", p["gamma_gain"], -(p["theta_cost"]["mean"] + p["carry"]["mean"]))
                within_se(f"C3 {lab}, N = {N}: the hedged P&L has mean zero", p["hedged_pnl_discounted"], 0.0)
            within_se(f"C3 {lab}, N = {N}: the mean hedged P&L is (sigma_r^2 - sigma_i^2) x mean(Sum e^(-rt) 1/2 Gamma S^2 dt)", p["hedged_pnl_discounted"], p["mean_predicted_by_vol_gap"])
            within_se(f"C3 {lab}, N = {N}: the gamma gain's mean is (sigma_r/sigma_i)^2 x the gamma_dt mean (the gain grows with sigma_r^2)", p["gamma_gain"], (sc["sigma_realised"] / sc["sigma_implied"]) ** 2 * p["gamma_dt"]["mean"])
        pN = {p["N"]: p for p in sc["per_N"]}
        if 256 in pN and 4096 in pN:
            truth(f"C3 {lab}: the remainder's rms falls from N = 256 to 4096 (Taylor's remainder vanishes with the step)", pN[4096]["remainder"]["rms"] < pN[256]["remainder"]["rms"] / 4)
            truth(f"C3 {lab}: the theta cost's spread does not fall with N (it is a path integral, not a step error)", pN[4096]["theta_cost"]["sd"] > 0.5 * pN[256]["theta_cost"]["sd"])
        c = sc["cited_from_2_7"]
        if c is not None and 4096 in pN:
            add(f"C3 {lab}: 2.7's measured mean (cited, {c['hedged_mean']:+.3f} +- {c['hedged_se']:.3f} at N = 4096, seed 20261101) agrees with this run's within 5 of the combined s.e.",
                pN[4096]["hedged_pnl_discounted"]["mean"], c["hedged_mean"], 5 * sqrt(c["hedged_se"] ** 2 + pN[4096]["hedged_pnl_discounted"]["se_of_mean"] ** 2))
    A = res["attribution"]
    g_low, g_base, g_high = [A[k]["per_N"][-1]["gamma_gain"]["mean"] for k in ("sigma_r_0.3", "sigma_r_0.4", "sigma_r_0.5")]
    t_low, t_base, t_high = [A[k]["per_N"][-1]["theta_cost"]["mean"] for k in ("sigma_r_0.3", "sigma_r_0.4", "sigma_r_0.5")]
    truth("C3 across sigma_r = 0.3, 0.4, 0.5 the gamma gain's mean rises with sigma_r", g_low < g_base < g_high)
    h_low, h_base, h_high = [A[k]["per_N"][-1]["hedged_pnl_discounted"]["mean"] for k in ("sigma_r_0.3", "sigma_r_0.4", "sigma_r_0.5")]
    truth("C3 across sigma_r the hedged P&L's mean rises with sigma_r: negative below sigma_i, positive above", h_low < h_base < h_high and h_low < 0 < h_high)
    truth("C3 across sigma_r the gamma gain's mean moves by more than the theta cost's (the gain is set by sigma_r; the cost by sigma_i and where the paths went)",
          abs(g_high - g_low) > abs(t_high - t_low))

    # C4 -- shapes
    Sh = res["shapes_against_S"]
    for key, c in Sh["curves"].items():
        tau = c["tau"]
        dS = Sh["S"][1] - Sh["S"][0]
        truth(f"C4 tau = {tau}: Delta is monotone increasing in S", c["delta_monotone"])
        add(f"C4 tau = {tau}: Delta runs from ~0 at S = 40 to ~1 at S = 200 (the ends within 0.05)", c["delta_range"][1] - c["delta_range"][0], 1.0, 0.05)
        add(f"C4 tau = {tau}: Gamma peaks at K e^(-(r + 3/2 sigma^2) tau) = {c['gamma_peak']['S_closed_form']:.1f} (within one grid step)", c["gamma_peak"]["S_on_grid"], c["gamma_peak"]["S_closed_form"], dS)
        add(f"C4 tau = {tau}: vega peaks at K e^((1/2 sigma^2 - r) tau) = {c['vega_peak']['S_closed_form']:.1f} (within one grid step)", c["vega_peak"]["S_on_grid"], c["vega_peak"]["S_closed_form"], dS)
        truth(f"C4 tau = {tau}: Theta is most negative within 15 of the strike", abs(c["theta_trough"]["S_on_grid"] - params["K"]) <= 15.0)
    c1, c005 = Sh["curves"]["tau_1"], Sh["curves"]["tau_0.05"]
    truth("C4 at tau = 1 Gamma's peak sits below the strike (74.8 against 100) and Gamma there exceeds Gamma at the strike", c1["gamma_peak"]["S_closed_form"] < params["K"] and c1["gamma_peak"]["gamma_at_peak"] > c1["gamma_peak"]["gamma_at_strike"])
    truth("C4 at tau = 0.05 Gamma's peak is within 2 of the strike", abs(c005["gamma_peak"]["S_closed_form"] - params["K"]) < 2.0)
    truth("C4 Gamma at the strike grows as tau falls: tau = 0.05 > 1/4 > 1/2 > 1", Sh["curves"]["tau_0.05"]["gamma_peak"]["gamma_at_strike"] > Sh["curves"]["tau_0.25"]["gamma_peak"]["gamma_at_strike"] > Sh["curves"]["tau_0.5"]["gamma_peak"]["gamma_at_strike"] > c1["gamma_peak"]["gamma_at_strike"])
    truth("C4 vega at the strike shrinks as tau falls: tau = 1 > 1/2 > 1/4 > 0.05", c1["vega_peak"]["vega_at_strike"] > Sh["curves"]["tau_0.5"]["vega_peak"]["vega_at_strike"] > Sh["curves"]["tau_0.25"]["vega_peak"]["vega_at_strike"] > c005["vega_peak"]["vega_at_strike"])
    truth("C4 Theta at the strike is more negative as tau falls: tau = 0.05 < 1/4 < 1/2 < 1", c005["theta_trough"]["theta_at_strike"] < Sh["curves"]["tau_0.25"]["theta_trough"]["theta_at_strike"] < Sh["curves"]["tau_0.5"]["theta_trough"]["theta_at_strike"] < c1["theta_trough"]["theta_at_strike"])
    ST = res["shapes_against_T"]
    last = ST["rows"][-1]
    add("C4 at the money as T -> 0: Gamma sqrt T -> phi(0)/(S sigma) (1e-3 relative at T = 1e-6)", last["gamma_sqrtT"], ST["limits"]["gamma_sqrtT"], 1e-3, "rel")
    add("C4 at the money as T -> 0: vega / sqrt T -> S phi(0) (1e-3 relative)", last["vega_over_sqrtT"], ST["limits"]["vega_over_sqrtT"], 1e-3, "rel")
    add("C4 at the money as T -> 0: Theta sqrt T -> -S sigma phi(0)/2 (1e-2 relative; the carry term is the gap)", last["theta_sqrtT"], ST["limits"]["theta_sqrtT"], 1e-2, "rel")
    gs = [r_["gamma"] for r_ in ST["rows"]]
    truth("C4 at the money Gamma increases monotonically as T falls", all(b > a for a, b in zip(gs, gs[1:])))
    vs = [r_["vega"] for r_ in ST["rows"]]
    truth("C4 at the money vega decreases monotonically as T falls", all(b < a for a, b in zip(vs, vs[1:])))

    # C5 -- parity's Greeks
    P = res["parity_greeks"]
    for name, tol in (("delta", 1e-12), ("gamma", 1e-12), ("vega", 1e-12), ("theta", 1e-10), ("rho", 1e-10), ("dividend_rho", 1e-10)):
        add(f"C5 across the grid: put {name} - call {name} = the forward's {name} ({tol:.0e})", P["grid"][f"max_abs_error_{name}"], 0.0, tol)
    bp = res["base_case"]["put"]
    add("C5 the put at the base case: Delta_P = Delta_C - 1 = -0.3726", bp["delta"], res["base_case"]["call"]["delta"] - 1.0, 1e-12)
    add("C5 the put at the base case: Gamma_P = Gamma_C", bp["gamma"], res["base_case"]["call"]["gamma"], 1e-15)
    add("C5 the put at the base case: vega_P = vega_C", bp["vega"], res["base_case"]["call"]["vega"], 1e-12)
    add("C5 the put at the base case: Theta_P - Theta_C = r K e^(-rT)", bp["theta"] - res["base_case"]["call"]["theta"], params["r"] * params["K"] * exp(-params["r"] * params["T"]), 1e-12)
    add("C5 the put at the base case: rho_P - rho_C = -K T e^(-rT)", bp["rho"] - res["base_case"]["call"]["rho"], -params["K"] * params["T"] * exp(-params["r"] * params["T"]), 1e-12)
    truth("C5 the put's rho is negative and the call's positive", bp["rho"] < 0 < res["base_case"]["call"]["rho"])

    # D6 -- fixtures consistent with C5
    D = res["d6"]
    add("D6 fixtures: call delta - put delta = e^(-q tau) = 1 at every S and tau (1e-12)", D["parity_check_max_abs_delta"], 0.0, 1e-12)
    add("D6 fixtures: call gamma = put gamma at every S and tau (1e-15)", D["parity_check_max_abs_gamma"], 0.0, 1e-15)
    return checks


# --- main -----------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--quick", action="store_true", help="a tenth of the paths and N = 256 only, no JSON written; the oracle comparisons skipped if unavailable")
    args = parser.parse_args()
    q = args.quick

    params = {
        "seed": args.seed, "quick": q,
        "T": 1.0, "S0": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.40, "q": 0.0,
        "formula": "C = S_0 e^(-qT) N(d_1) - K e^(-rT) N(d_2); P = K e^(-rT) N(-d_2) - S_0 e^(-qT) N(-d_1); d_1 = (ln(S_0/K) + (r - q + 1/2 sigma^2) T)/(sigma sqrt T); d_2 = d_1 - sigma sqrt T",
        "greeks": {"delta": "w e^(-qT) N(w d_1)", "gamma": "e^(-qT) phi(d_1) / (S sigma sqrt T)", "vega": "S e^(-qT) phi(d_1) sqrt T -- per 1.00 of volatility",
                   "theta": "-S e^(-qT) phi(d_1) sigma / (2 sqrt T) - w r K e^(-rT) N(w d_2) + w q S e^(-qT) N(w d_1) -- per year, d/dt at fixed S",
                   "rho": "w K T e^(-rT) N(w d_2) -- per 1.00 of rate", "dividend_rho": "-w T S e^(-qT) N(w d_1) -- per 1.00 of yield",
                   "units": "raw partials (the golden file's and T0's convention; owner's ruling Q2/a); desk scalings -- per vol point /100, per day /365, per basis point /10000 -- at display only"},
        "pde": "Theta + 1/2 sigma^2 S^2 Gamma + r S Delta - r V = 0 (2.7), re-read as: theta cost + carry = -(gamma gain the price assumes)",
        "grid": {"S0": [80.0, 100.0, 120.0], "K": [90.0, 100.0, 110.0], "r": [0.0, 0.05], "q": [0.0, 0.03], "sigma": [0.2, 0.4], "T": [0.25, 1.0, 2.0]},
        "bump_h_rel": {"first": 5e-5, "rate": 1e-5, "gamma": 1e-4,
                       "why": "central differences: truncation ~ h^2, round-off ~ eps/h (first) and eps/h^2 (second); the Gamma study below puts the second difference's best h near 1e-4 relative in double precision at these scales, not the 1e-2 a hand estimate suggests -- 3.5's subject"},
        "bump_tolerance": {"delta": 1e-7, "gamma": 1e-7, "vega": 1e-7, "theta": 1e-7, "rho": 1e-7, "dividend_rho": 1e-7},
        "gamma_bump_study_h_rel": [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 1e-4, 1e-5, 1e-6],
        "paths": {"n_fine": 4096, "Ns": [256] if q else [256, 4096], "n_paths": 400 if q else 4000, "chunk_paths": 400 if q else 500,
                  "n_paths_full": 4000, "as_in_2_7": "exact GBM at n_fine steps, read on N; 2.7's seed was 20261101, mu = 0"},
        "attribution_scenarios": {"sigma_r_0.3": {"mu": 0.0, "sigma_realised": 0.3}, "sigma_r_0.4": {"mu": 0.0, "sigma_realised": 0.4}, "sigma_r_0.5": {"mu": 0.0, "sigma_realised": 0.5}},
        "cited_from_2_7": {"source": "experiments/2_7_delta_hedging.json, scenarios vol_low / base / vol_high, per_N N = 4096, call.hedged_pnl_discounted and gamma_dt_mean (seed 20261101, 4000 paths)",
                           "sigma_r_0.3": {"hedged_mean": -3.759, "hedged_se": 0.0197, "gamma_dt_mean": 53.71, "predicted": -3.760},
                           "sigma_r_0.4": {"hedged_mean": -0.0022, "hedged_se": 0.0033, "gamma_dt_mean": 46.82, "predicted": 0.0},
                           "sigma_r_0.5": {"hedged_mean": 3.7404, "hedged_se": 0.0256, "gamma_dt_mean": 41.57, "predicted": 3.741}},
        "shapes": {"S": [40.0, 200.0, 161], "taus": [1.0, 0.5, 0.25, 0.05], "Ts": [2.0, 1.0, 0.5, 0.25, 0.1, 0.01, 1e-3, 1e-4, 1e-6]},
    }
    T, S0, K, r, sigma = params["T"], params["S0"], params["K"], params["r"], params["sigma"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    phi_err = phi_self_test()
    print(f"[2.10] Phi self-test: max abs error {phi_err:.2e}", flush=True)

    # the base case
    d1, d2 = (float(v) for v in d1_d2(S0, K, r, 0.0, sigma, T))
    gc = {k: float(v) for k, v in greeks(S0, K, r, 0.0, sigma, T, +1).items()}
    gp = {k: float(v) for k, v in greeks(S0, K, r, 0.0, sigma, T, -1).items()}
    tp = theta_pieces(S0, K, r, 0.0, sigma, T)
    pde_res = gc["theta"] + 0.5 * sigma * sigma * S0 * S0 * gc["gamma"] + r * S0 * gc["delta"] - r * gc["price"]
    base_case = {"d1": d1, "d2": d2, "N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)), "phi_d1": float(phi(d1)),
                 "call": gc, "put": gp, "theta_pieces": tp, "pde_residual": pde_res,
                 "desk_units": {"vega_per_vol_point": gc["vega"] / 100.0, "theta_per_day": gc["theta"] / 365.0, "rho_per_basis_point": gc["rho"] / 10000.0,
                                "note": "display scalings of the raw partials above; the oracle and the C++ carry the raw values"}}
    print(f"[2.10] base case S_0 = K = {S0:.0f}, r = {r}, sigma = {sigma}, T = {T}: C = {gc['price']:.4f}; Delta {gc['delta']:.4f}, Gamma {gc['gamma']:.6f}, "
          f"vega {gc['vega']:.3f}/unit, Theta {gc['theta']:.3f}/yr (= {tp['gamma_term']:.3f} gamma term + {tp['carry_term']:.3f} carry), rho {gc['rho']:.3f}/unit; "
          f"put: Delta {gp['delta']:.4f}, Theta {gp['theta']:.3f}, rho {gp['rho']:.3f}", flush=True)

    # C1: bump-and-revalue
    h = params["bump_h_rel"]
    g = params["grid"]
    grid_points = [(S, k, rr, qq, sg, t) for S in g["S0"] for k in g["K"] for rr in g["r"] for qq in g["q"] for sg in g["sigma"] for t in g["T"]]
    worst = {name: 0.0 for name in GREEK_NAMES}
    worst_row = {name: None for name in GREEK_NAMES}
    for (S, k, rr, qq, sg, t) in grid_points:
        for w in (+1, -1):
            an = greeks(S, k, rr, qq, sg, t, w)
            bu = bump_greeks(S, k, rr, qq, sg, t, w, h)
            for name in GREEK_NAMES:
                e = abs(bu[name] - float(an[name]))
                if e > worst[name]:
                    worst[name], worst_row[name] = e, f"{'call' if w > 0 else 'put'} S={S} K={k} r={rr} q={qq} sigma={sg} T={t}"
    bump = {"h_rel": h,
            "base": {"analytic": {k: gc[k] for k in GREEK_NAMES}, "bump": bump_greeks(S0, K, r, 0.0, sigma, T, +1, h)},
            "base_put": {"analytic": {k: gp[k] for k in GREEK_NAMES}, "bump": bump_greeks(S0, K, r, 0.0, sigma, T, -1, h)},
            "grid": {"n_points": len(grid_points), "call_and_put": True, **{f"max_abs_error_{k}": v for k, v in worst.items()}, **{f"worst_row_{k}": v for k, v in worst_row.items()}},
            "gamma_bump_study": gamma_bump_study(S0, K, r, 0.0, sigma, T, params["gamma_bump_study_h_rel"])}
    print(f"[2.10] C1 bump-and-revalue at the base case: " + ", ".join(f"{k} {bump['base']['bump'][k] - gc[k]:+.1e}" for k in GREEK_NAMES)
          + f"; grid worst " + ", ".join(f"{k} {worst[k]:.1e}" for k in GREEK_NAMES), flush=True)
    print("[2.10] C1 Gamma bump study: " + ", ".join(f"h={row['h_rel']:g}: {row['abs_error']:.1e}" for row in bump["gamma_bump_study"]), flush=True)

    # the two moves the predictions asked about
    C0 = gc["price"]
    moves = {
        "spot_100_to_101": {"actual_change": float(price(101.0, K, r, 0.0, sigma, T)) - C0, "first_order": gc["delta"] * 1.0,
                            "second_order": gc["delta"] * 1.0 + 0.5 * gc["gamma"] * 1.0, "half_gamma": 0.5 * gc["gamma"], "C_at_101": float(price(101.0, K, r, 0.0, sigma, T)), "delta_at_101": float(greeks(101.0, K, r, 0.0, sigma, T)["delta"])},
        "spot_100_to_99": {"actual_change": float(price(99.0, K, r, 0.0, sigma, T)) - C0, "first_order": -gc["delta"] * 1.0,
                           "second_order": -gc["delta"] * 1.0 + 0.5 * gc["gamma"] * 1.0, "C_at_99": float(price(99.0, K, r, 0.0, sigma, T))},
        "vol_0.40_to_0.41": {"actual_change": float(price(S0, K, r, 0.0, 0.41, T)) - C0, "first_order": gc["vega"] * 0.01, "C_at_0.41": float(price(S0, K, r, 0.0, 0.41, T))},
        "rate_0.05_to_0.06": {"actual_change": float(price(S0, K, 0.06, 0.0, sigma, T)) - C0, "first_order": gc["rho"] * 0.01, "C_at_0.06": float(price(S0, K, 0.06, 0.0, sigma, T))},
        "one_day_passes": {"actual_change": float(price(S0, K, r, 0.0, sigma, T - 1.0 / 365.0)) - C0, "first_order": gc["theta"] / 365.0, "C_at_364_days": float(price(S0, K, r, 0.0, sigma, T - 1.0 / 365.0))},
    }
    print(f"[2.10] C1 moves: S 100 -> 101: C {C0:.4f} -> {moves['spot_100_to_101']['C_at_101']:.4f}, change {moves['spot_100_to_101']['actual_change']:.4f} vs Delta {gc['delta']:.4f} (+ 1/2 Gamma {0.5 * gc['gamma']:.4f}); "
          f"sigma 0.40 -> 0.41: change {moves['vol_0.40_to_0.41']['actual_change']:.4f} vs vega x 0.01 = {gc['vega'] * 0.01:.4f}; one day: {moves['one_day_passes']['actual_change']:.4f} vs Theta/365 = {gc['theta'] / 365:.4f}", flush=True)

    # C2: the oracle
    print("[2.10] C2 oracle: QuantLib-Python BlackCalculator at the grid, seven columns; the golden file's seven columns", flush=True)
    live = quantlib_live(grid_points)
    golden = golden_file_check(Path(__file__).resolve().parent)
    if live is None:
        print("[2.10] C2: QuantLib-Python not importable -- live oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        print(f"[2.10] C2: QuantLib {live['version']} at {live['n_points']} points, call and put: worst " + ", ".join(f"{k} {live[f'max_abs_error_{k}']:.1e}" for k in ["price", *GREEK_NAMES]), flush=True)
    if golden is None:
        print("[2.10] C2: golden/bs_vanilla.json not found -- committed-oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        print(f"[2.10] C2: {golden['file']} (QuantLib {golden['oracle']['version']}): {golden['cases']['n']} cases worst " + ", ".join(f"{k} {golden['cases'][f'worst_{k}_error']:.1e}" for k in ["price", *GREEK_NAMES])
              + f"; {golden['edge_cases']['n']} edge cases worst " + ", ".join(f"{k} {golden['edge_cases'][f'worst_{k}_error']:.1e}" for k in ["price", *GREEK_NAMES]), flush=True)
    oracle = {"live": live, "golden": golden}

    # C3: the PDE as a P&L statement on paths
    P = params["paths"]
    attribution = {}
    for key, sc in params["attribution_scenarios"].items():
        print(f"[2.10] C3 attribution: mu = {sc['mu']}, sigma_r = {sc['sigma_realised']}, sigma_i = {sigma}; {P['n_paths']} paths x {P['n_fine']} fine steps, N in {P['Ns']}", flush=True)
        attribution[key] = attribution_scenario(rng, P["n_paths"], P["n_fine"], P["Ns"], P["chunk_paths"], T, S0, K, r, sc["mu"], sc["sigma_realised"], sigma, key,
                                                None if q else params["cited_from_2_7"][key])
        p = attribution[key]["per_N"][-1]
        print(f"[2.10] C3 {key}, N = {p['N']}: option change {p['option_change']['mean']:+.3f}; delta term {p['delta_term']['mean']:+.3f}; gamma gain {p['gamma_gain']['mean']:+.3f} +- {p['gamma_gain']['se_of_mean']:.3f}; "
              f"theta cost {p['theta_cost']['mean']:+.3f} +- {p['theta_cost']['se_of_mean']:.3f}; carry {p['carry']['mean']:+.3f}; remainder rms {p['remainder']['rms']:.4f}; "
              f"hedged {p['hedged_pnl_discounted']['mean']:+.4f} +- {p['hedged_pnl_discounted']['se_of_mean']:.4f} (sd {p['hedged_pnl_discounted']['sd']:.3f}) vs (sigma_r^2 - sigma_i^2) x {p['gamma_integral_mean']:.2f} = {p['mean_predicted_by_vol_gap']:+.3f}; "
              f"PDE identity {p['pde_identity_max_abs']:.1e}", flush=True)

    # C4: shapes
    Sh = params["shapes"]
    shapes_S = shapes_against_S(K, r, sigma, Sh["taus"], Sh["S"][0], Sh["S"][1], Sh["S"][2])
    shapes_T = shapes_against_T(S0, K, r, sigma, Sh["Ts"])
    c1 = shapes_S["curves"]["tau_1"]
    print(f"[2.10] C4 shapes at tau = 1: Gamma peaks at S = {c1['gamma_peak']['S_on_grid']:.0f} (closed form {c1['gamma_peak']['S_closed_form']:.1f}), {c1['gamma_peak']['gamma_at_peak']:.5f} vs {c1['gamma_peak']['gamma_at_strike']:.5f} at the strike; "
          f"vega peaks at {c1['vega_peak']['S_on_grid']:.0f} ({c1['vega_peak']['S_closed_form']:.1f}); Theta trough at {c1['theta_trough']['S_on_grid']:.0f}; "
          f"at the money T = 1e-6: Gamma sqrt T {shapes_T['rows'][-1]['gamma_sqrtT']:.6f} vs {shapes_T['limits']['gamma_sqrtT']:.6f}", flush=True)

    # C5: parity's Greeks across the grid
    worst_p = {name: 0.0 for name in GREEK_NAMES}
    for (S, k, rr, qq, sg, t) in grid_points:
        c_, p_ = greeks(S, k, rr, qq, sg, t, +1), greeks(S, k, rr, qq, sg, t, -1)
        fwd = {"delta": -exp(-qq * t), "gamma": 0.0, "vega": 0.0, "theta": rr * k * exp(-rr * t) - qq * S * exp(-qq * t), "rho": -k * t * exp(-rr * t), "dividend_rho": t * S * exp(-qq * t)}
        for name in GREEK_NAMES:
            worst_p[name] = max(worst_p[name], abs(float(p_[name]) - float(c_[name]) - fwd[name]))
    parity_greeks = {"identities": "P - C = K e^(-rT) - S_0 e^(-qT), so Delta_P = Delta_C - e^(-qT), Gamma and vega equal, Theta_P - Theta_C = r K e^(-rT) - q S_0 e^(-qT), rho_P - rho_C = -K T e^(-rT), dq: + T S_0 e^(-qT)",
                     "grid": {"n_points": len(grid_points), **{f"max_abs_error_{k}": v for k, v in worst_p.items()}},
                     "base_case": {"call": gc, "put": gp, "forward_theta": r * K * exp(-r * T), "forward_rho": -K * T * exp(-r * T)}}
    print(f"[2.10] C5 parity's Greeks across the grid: worst " + ", ".join(f"{k} {v:.1e}" for k, v in worst_p.items()), flush=True)

    # D6 fixtures: the Greeks against S at the four tau (2.9's S grid), call and put
    S_arr = np.array(shapes_S["S"])
    d6 = {"S": shapes_S["S"], "taus": Sh["taus"], "curves": {}, "base_case_readout": {"call": gc, "put": gp, "desk_units": base_case["desk_units"]},
          "units": "raw partials: vega per 1.00 of sigma, Theta per year, rho per 1.00 of r; scale at display"}
    pd_, pg_ = 0.0, 0.0
    for tau in Sh["taus"]:
        gC, gP = greeks(S_arr, K, r, 0.0, sigma, tau, +1), greeks(S_arr, K, r, 0.0, sigma, tau, -1)
        d6["curves"][f"tau_{tau:g}"] = {"tau": tau, "call": {k: gC[k].tolist() for k in ("delta", "gamma", "vega", "theta", "rho")}, "put": {k: gP[k].tolist() for k in ("delta", "gamma", "vega", "theta", "rho")}}
        pd_ = max(pd_, float(np.abs(gC["delta"] - gP["delta"] - 1.0).max()))
        pg_ = max(pg_, float(np.abs(gC["gamma"] - gP["gamma"]).max()))
    d6["parity_check_max_abs_delta"], d6["parity_check_max_abs_gamma"] = pd_, pg_

    results = {"phi_max_abs_error": phi_err, "base_case": base_case, "bump": bump, "moves": moves, "oracle": oracle,
               "attribution": attribution, "shapes_against_S": shapes_S, "shapes_against_T": shapes_T, "parity_greeks": parity_greeks, "d6": d6}
    checks = build_checks(results, params)

    out = {"page": "2.10", "script": Path(__file__).name, "params": params,
           "environment": {"numpy": np.__version__, "quantlib": live["version"] if live else None, "golden_oracle": golden["oracle"] if golden else None},
           "results": results, "checks": checks}
    out_path = Path(__file__).with_suffix(".json")
    if q:
        print(f"[2.10] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  ({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.10] {'checked (--quick)' if q else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s ({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
