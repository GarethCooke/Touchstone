"""The Black-Scholes formula -- the experiment behind page 2.9.

Serves page 2.9 (docs/quant-learn-index-v1.md). Page 2.8 left the price as an
expectation,

    V = e^(-rT) E^Q[max(S_T - K, 0)],

under the measure Q in which the stock is page 2.6's Geometric Brownian motion
(GBM) with the risk-free rate r in the drift slot,

    dS = r S dt + sigma S dW~        (drift first),

so that S_T = S_0 exp((r - 1/2 sigma^2) T + sigma W~_T) is lognormal. For this
payoff the expectation is an ordinary integral against the lognormal density
and can be done by hand. Page 2.9 does it; the result is the Black-Scholes
formula

    C = S_0 N(d_1) - K e^(-rT) N(d_2),
    d_1 = (ln(S_0/K) + (r + 1/2 sigma^2) T) / (sigma sqrt T),   d_2 = d_1 - sigma sqrt T,

where N(.) is the cumulative normal -- written Phi on 2.6, N from this page on
(the S6 ruling). 2.8 borrowed this formula as its benchmark because 2.7 had
checked that it satisfies the PDE; here it is derived from the expectation, so
the Monte Carlo pricer, the integral and the closed form become three views of
one value.

Session S9's setup decisions (owner, 2026-11-05): (a) the page covers the call,
the put, put-call parity, a continuous dividend yield q and Black-76 -- one
integral done once, three substitutions; (b) N(d_1) is explained as the
probability of exercise under the measure that uses the stock as numeraire,
measured on the draws, and also as the delta 2.7 hedged with.

  C1  The integral. Numerical quadrature of e^(-rT) max(S - K, 0) against the
      lognormal density of S_T under Q -- as the page writes it, in S, and
      after the substitution S = S_0 exp((r - 1/2 sigma^2) T + sigma sqrt T z),
      in z against the standard normal density -- equals the closed form to
      1e-10 at the base case and on a grid of (S_0, K, r, q, sigma, T). The
      two pieces separately: e^(-rT) E^Q[S_T 1(S_T > K)] = S_0 N(d_1) and
      K e^(-rT) Q(S_T > K) = K e^(-rT) N(d_2), each by quadrature (1e-10) and
      by Monte Carlo on 2.8-style exact draws (within 5 s.e.). So "what
      N(d_1) and N(d_2) mean" is two measured numbers: N(d_2) = 0.470 is the
      Q-probability of exercise (2.8's 47.0 %), and N(d_1) = 0.627 is
      E^Q[S_T 1(S_T > K)] / E^Q[S_T] -- the share of the stock's value that
      comes from the paths that finish in the money, the probability of
      exercise under the measure that uses the stock as numeraire -- and also
      the delta 2.7 hedged with (dC/dS by a central bump agrees with N(d_1)).
      The conditional mean E^Q[S_T | S_T > K] = S_0 e^(rT) N(d_1)/N(d_2) is
      recorded beside it, because it is the number the phrase "the average
      stock price on the paths that finish above the strike" names, and it is
      not the one in the price.
  C2  Put-call parity. C - P = S_0 e^(-qT) - K e^(-rT) exactly on the closed
      form across the grid (1e-12); path by path on the Monte Carlo draws the
      two payoffs differ by S_T - K on every path (1e-9), so the difference of
      the two Monte Carlo prices on the SAME draws is the forward's
      no-arbitrage value within 5 s.e. The identity needs no model.
  C3  Limits, each as a convergence table. sigma -> 0: the call tends to
      max(S_0 - K e^(-rT), 0), the forward's value or zero (sigma = 0.4 down
      to 1e-6, at four spots including the kink F = K where the convergence is
      linear in sigma with slope K e^(-rT) sqrt T / sqrt(2 pi)). T -> 0: the
      call tends to its intrinsic value max(S_0 - K, 0) (T = 1 down to 1e-6);
      at the kink S_0 = K it falls like S_0 sigma sqrt(T / 2 pi) and N(d_1),
      N(d_2) -> 1/2. S_0 -> infinity: the call minus the forward S_0 - K
      e^(-rT) -> 0 and N(d_1), N(d_2) -> 1. S_0 -> 0: the call -> 0 and N(d_1),
      N(d_2) -> 0. Each gap decreases monotonically along its table.
  C4  Dividend yield and Black-76 -- three spellings of one formula. With a
      continuous yield q the stock's Q-drift is r - q and S_0 becomes S_0
      e^(-qT) in the price and in d_1; Black-76 writes the same price from the
      forward F = S_0 e^((r-q)T) as e^(-rT) [F N(d_1) - K N(d_2)] with d_1 =
      (ln(F/K) + 1/2 sigma^2 T) / (sigma sqrt T) -- r gone from d_1, surviving
      only in the discount (the two d_1's agree to 1e-14). At q = 0, 0.03 and
      0.08: the closed form with S_0 e^(-qT), Black-76 with F, and a Monte
      Carlo run with the drift r - q (2.8's simulator with one more
      parameter) give one number (1e-12 between the two formulas; the Monte
      Carlo within 5 s.e.); the forward's own value S_0 e^(-qT) - K e^(-rT) as
      the control; parity with dividends on the draws. Across the grid the
      call is decreasing in q and the put increasing (the stock leaks value to
      the holder of the stock, not of the option).
  C5  The oracle (I4) -- the first time QuantLib appears on an S page. The
      closed form of this page against (i) QuantLib-Python's BlackCalculator
      at the page's grid, price and delta (1e-10); (ii) QuantLib's
      AnalyticEuropeanEngine on a BlackScholesMertonProcess at the base case,
      the engine the golden generator uses; (iii) the committed golden file
      golden/bs_vanilla.json -- 7,200 grid cases and 34 edge cases generated
      by QuantLib 1.43 at T0 -- price and delta, to the file's own tolerances.
      The QuantLib version that ran is recorded in the JSON beside the golden
      file's. And the index's "MC agreement": a fresh 10^6-draw Q-run within
      5 s.e. of the closed form (2.8's C2 reproduced, new seed).
  D6  Fixtures for the Black-Scholes pricer demo (2.9-2.10): the call and the
      put against S on [40, 200] at tau = 1, 1/2, 1/4, 0.05 with the payoff
      and the forward line, N(d_1) and N(d_2) against S, and the parity line.
      Fixtures carry no claim beyond C1-C4; the site draws them (I15).

Run from the repository root:

    uv run experiments/2_9_black_scholes_formula.py [--seed 20261105] [--quick]

--quick runs a tenth of the draws for the learn site's build-time snippet check
(I3) and NO JSON is written -- the committed result is always the full run.
Under --quick the live QuantLib comparison and the golden-file comparison are
skipped with a notice if QuantLib or the file is not present; the full run
requires both (I4).

Writes 2_9_black_scholes_formula.json beside this file: parameters in, results
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
# against math.erf before anything else runs (copied from 2_8_risk_neutral_pricing.py).
# On the page this function is N(.); the code keeps 2.6's name Phi.


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


def normal_pdf(z):
    z = np.asarray(z, dtype=float)
    return np.exp(-0.5 * z * z) / sqrt(2.0 * pi)


# --- the closed form, as the page derives it ------------------------------------


def d1_d2(S, K, r, q, sigma, T):
    """d_1 = (ln(S/K) + (r - q + 1/2 sigma^2) T) / (sigma sqrt T), d_2 = d_1 - sigma sqrt T."""
    S = np.asarray(S, dtype=float)
    st = sigma * sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / st
    return d1, d1 - st


def bs_call(S, K, r, q, sigma, T):
    """C = S e^(-qT) N(d_1) - K e^(-rT) N(d_2)."""
    S = np.asarray(S, dtype=float)
    d1, d2 = d1_d2(S, K, r, q, sigma, T)
    return S * exp(-q * T) * Phi(d1) - K * exp(-r * T) * Phi(d2)


def bs_put(S, K, r, q, sigma, T):
    """P = K e^(-rT) N(-d_2) - S e^(-qT) N(-d_1)."""
    S = np.asarray(S, dtype=float)
    d1, d2 = d1_d2(S, K, r, q, sigma, T)
    return K * exp(-r * T) * Phi(-d2) - S * exp(-q * T) * Phi(-d1)


def bs_delta(S, K, r, q, sigma, T):
    """dC/dS = e^(-qT) N(d_1) -- the delta 2.7 hedged with (q = 0 there)."""
    d1, _ = d1_d2(S, K, r, q, sigma, T)
    return exp(-q * T) * Phi(d1)


def black76_call(F, K, r, sigma, T):
    """Black-76: C = e^(-rT) [F N(d_1) - K N(d_2)], d_1 = (ln(F/K) + 1/2 sigma^2 T) / (sigma sqrt T) -- no r in d_1."""
    st = sigma * sqrt(T)
    d1 = (log(F / K) + 0.5 * sigma * sigma * T) / st
    d2 = d1 - st
    return exp(-r * T) * (F * Phi(d1) - K * Phi(d2)), d1, d2


def forward_value(S0, K, r, q, T) -> float:
    """The forward's no-arbitrage value S_0 e^(-qT) - K e^(-rT): the parity line, no model."""
    return S0 * exp(-q * T) - K * exp(-r * T)


# --- C1: the integral by quadrature -------------------------------------------
#
# Composite Gauss-Legendre: `panels` equal panels, `nodes` points each. The
# integrands are smooth, so this reaches machine precision; no scipy needed.


def gauss_legendre(a: float, b: float, panels: int, nodes: int):
    x, w = np.polynomial.legendre.leggauss(nodes)
    edges = np.linspace(a, b, panels + 1)
    half = 0.5 * (edges[1:] - edges[:-1])
    mid = 0.5 * (edges[1:] + edges[:-1])
    X = (mid[:, None] + half[:, None] * x[None, :]).ravel()
    W = (half[:, None] * w[None, :]).ravel()
    return X, W


def lognormal_density(S, S0, r, q, sigma, T):
    """The Q-density of S_T: ln S_T ~ Normal(ln S_0 + (r - q - 1/2 sigma^2) T, sigma^2 T)."""
    S = np.asarray(S, dtype=float)
    m = log(S0) + (r - q - 0.5 * sigma * sigma) * T
    s = sigma * sqrt(T)
    return np.exp(-0.5 * ((np.log(S) - m) / s) ** 2) / (S * s * sqrt(2.0 * pi))


def integrate(S0, K, r, q, sigma, T, panels=64, nodes=32, z_max=40.0) -> dict:
    """The page's integral four ways, and the two pieces of the call.

    S-space -- as the page writes it: e^(-rT) Int_K^inf (S - K) f(S) dS with f the
    lognormal density, the panels placed uniformly in ln S so the tail is covered.
    z-space -- after the substitution S = S_0 exp((r - q - 1/2 sigma^2) T + sigma sqrt T z):
    e^(-rT) Int_{-d_2}^inf (S(z) - K) phi(z) dz. S(z) > K exactly when z > -d_2.
    """
    disc = exp(-r * T)
    m = log(S0) + (r - q - 0.5 * sigma * sigma) * T
    s = sigma * sqrt(T)
    d1, d2 = d1_d2(S0, K, r, q, sigma, T)
    d1, d2 = float(d1), float(d2)

    # S-space, the call: u = ln S from ln K to m + z_max s; dS = e^u du
    U, WU = gauss_legendre(log(K), m + z_max * s, panels, nodes)
    S = np.exp(U)
    f = lognormal_density(S, S0, r, q, sigma, T)
    call_S = disc * float(np.sum(WU * (S - K) * f * S))
    stock_piece_S = disc * float(np.sum(WU * S * f * S))          # e^(-rT) E^Q[S_T 1(S_T > K)]
    prob_S = float(np.sum(WU * f * S))                               # Q(S_T > K)
    strike_piece_S = K * disc * prob_S                               # K e^(-rT) Q(S_T > K)
    # S-space, the put: u from m - z_max s to ln K
    U2, WU2 = gauss_legendre(m - z_max * s, log(K), panels, nodes)
    S2 = np.exp(U2)
    f2 = lognormal_density(S2, S0, r, q, sigma, T)
    put_S = disc * float(np.sum(WU2 * (K - S2) * f2 * S2))
    mean_S = float(np.sum(WU * S * f * S) + np.sum(WU2 * S2 * f2 * S2))   # E^Q[S_T] over both halves

    # z-space, the call: z from -d_2 to -d_2 + z_max
    Z, WZ = gauss_legendre(-d2, -d2 + z_max, panels, nodes)
    SZ = S0 * np.exp((r - q - 0.5 * sigma * sigma) * T + s * Z)
    call_z = disc * float(np.sum(WZ * (SZ - K) * normal_pdf(Z)))
    stock_piece_z = disc * float(np.sum(WZ * SZ * normal_pdf(Z)))
    prob_z = float(np.sum(WZ * normal_pdf(Z)))

    return {"d1": d1, "d2": d2,
            "call_S_space": call_S, "call_z_space": call_z, "put_S_space": put_S,
            "stock_piece_S_space": stock_piece_S, "stock_piece_z_space": stock_piece_z,
            "strike_piece_S_space": strike_piece_S,
            "exercise_probability_S_space": prob_S, "exercise_probability_z_space": prob_z,
            "E_S_T_S_space": mean_S,
            "share_measure_probability_S_space": stock_piece_S / (disc * mean_S),
            "closed_form": {"call": float(bs_call(S0, K, r, q, sigma, T)), "put": float(bs_put(S0, K, r, q, sigma, T)),
                            "stock_piece": S0 * exp(-q * T) * float(Phi(d1)), "strike_piece": K * disc * float(Phi(d2)),
                            "N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)), "E_S_T": S0 * exp((r - q) * T)}}


# --- statistics ----------------------------------------------------------------


def stats(x: np.ndarray) -> dict[str, float]:
    sd = float(x.std(ddof=1))
    return {"mean": float(x.mean()), "sd": sd, "se_of_mean": sd / sqrt(x.size), "n": int(x.size)}


def histogram(x: np.ndarray, lo: float, hi: float, bins: int) -> dict:
    counts, edges = np.histogram(x, bins=bins, range=(lo, hi))
    return {"edges": edges.tolist(), "counts": counts.tolist(), "below_lo": int((x < lo).sum()), "above_hi": int((x > hi).sum())}


def ratio_stats(num: np.ndarray, den: np.ndarray) -> dict[str, float]:
    """R = mean(num)/mean(den) with its delta-method s.e.: sd of (num - R den)/mean(den) over sqrt n."""
    R = float(num.mean() / den.mean())
    g = (num - R * den) / den.mean()
    return {"ratio": R, "se": float(g.std(ddof=1) / sqrt(num.size)), "n": int(num.size)}


# --- C1, C2, C4, C5: the Monte Carlo run -- 2.8's exact draw, one more parameter ---


def mc_run(rng, n, S0, K, r, q, sigma, T, label) -> dict:
    """n exact draws of S_T under Q with the drift r - q; the call, the put, the two
    pieces, the exercise probability, the share-measure probability, parity on the
    same draws, the forward as the control."""
    Z = rng.standard_normal(n)
    S_T = S0 * np.exp((r - q - 0.5 * sigma * sigma) * T + sigma * sqrt(T) * Z)
    disc = exp(-r * T)
    itm = S_T > K
    call_pay = np.maximum(S_T - K, 0.0)
    put_pay = np.maximum(K - S_T, 0.0)
    d1, d2 = d1_d2(S0, K, r, q, sigma, T)
    C, P = float(bs_call(S0, K, r, q, sigma, T)), float(bs_put(S0, K, r, q, sigma, T))

    call = stats(disc * call_pay)
    put = stats(disc * put_pay)
    diff = stats(disc * (call_pay - put_pay))
    fwd = stats(disc * (S_T - K))
    prob = stats(itm.astype(float))
    stock_piece = stats(disc * S_T * itm)
    strike_piece = stats(K * disc * itm.astype(float))
    E_S_T = stats(S_T)
    share = ratio_stats(S_T * itm, S_T)
    cond = stats(S_T[itm])
    per_path = float(np.abs((call_pay - put_pay) - (S_T - K)).max())
    hist = histogram(S_T, 0.0, 400.0, 80)
    hist["share_of_paths_above_K"] = float(itm.mean())
    hist["share_of_S_T_mass_above_K"] = float((S_T * itm).sum() / S_T.sum())

    out = {"label": label, "n": int(n), "q": q, "drift": r - q,
           "d1": float(d1), "d2": float(d2), "N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)),
           "closed_form_call": C, "closed_form_put": P, "forward_no_arbitrage": forward_value(S0, K, r, q, T),
           "call": {**call, "error_in_se": (call["mean"] - C) / call["se_of_mean"]},
           "put": {**put, "error_in_se": (put["mean"] - P) / put["se_of_mean"]},
           "parity": {"per_path_identity_max_abs": per_path,
                      "mc_difference": {**diff, "error_in_se": (diff["mean"] - forward_value(S0, K, r, q, T)) / diff["se_of_mean"]},
                      "closed_form_difference": C - P},
           "forward_control": {**fwd, "error_in_se": (fwd["mean"] - forward_value(S0, K, r, q, T)) / fwd["se_of_mean"]},
           "exercise_probability": {**prob, "N_d2": float(Phi(d2)), "error_in_se": (prob["mean"] - float(Phi(d2))) / prob["se_of_mean"]},
           "stock_piece": {**stock_piece, "S0_e_qT_N_d1": S0 * exp(-q * T) * float(Phi(d1)),
                           "error_in_se": (stock_piece["mean"] - S0 * exp(-q * T) * float(Phi(d1))) / stock_piece["se_of_mean"]},
           "strike_piece": {**strike_piece, "K_e_rT_N_d2": K * disc * float(Phi(d2)),
                            "error_in_se": (strike_piece["mean"] - K * disc * float(Phi(d2))) / strike_piece["se_of_mean"]},
           "E_S_T": {**E_S_T, "expected": S0 * exp((r - q) * T), "error_in_se": (E_S_T["mean"] - S0 * exp((r - q) * T)) / E_S_T["se_of_mean"]},
           "share_measure_probability": {**share, "N_d1": float(Phi(d1)), "error_in_se": (share["ratio"] - float(Phi(d1))) / share["se"]},
           "conditional_mean_given_itm": {**cond, "expected": S0 * exp((r - q) * T) * float(Phi(d1)) / float(Phi(d2)),
                                          "error_in_se": (cond["mean"] - S0 * exp((r - q) * T) * float(Phi(d1)) / float(Phi(d2))) / cond["se_of_mean"]},
           "histogram_S_T": hist}
    return out


# --- C3: limits ------------------------------------------------------------------


def limit_table(xs, price_fn, limit_fn, extra_fn=None) -> list[dict]:
    rows = []
    prev = None
    for x in xs:
        C = float(price_fn(x))
        L = float(limit_fn(x))
        row = {"x": float(x), "call": C, "limit": L, "gap": C - L}
        if prev is not None and prev != 0.0:
            row["gap_over_previous_gap"] = (C - L) / prev
        if extra_fn is not None:
            row.update(extra_fn(x))
        rows.append(row)
        prev = C - L
    return rows


def limits(S0, K, r, sigma, T) -> dict:
    q = 0.0
    out = {}
    # sigma -> 0: the call -> max(S_0 - K e^(-rT), 0). At F = K the gap is linear in sigma.
    sigmas = [0.4, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6]
    kink = K * exp(-r * T)
    out["sigma_to_0"] = {"sigmas": sigmas, "limit": "max(S_0 - K e^(-rT), 0)", "rows": {}}
    for S in [90.0, kink, 100.0, 110.0]:
        key = f"S0_{S:.3f}" if S == kink else f"S0_{S:.0f}"
        rows = limit_table(sigmas, lambda s: bs_call(S, K, r, q, s, T), lambda s: max(S - K * exp(-r * T), 0.0),
                           lambda s: {"gap_over_sigma": (float(bs_call(S, K, r, q, s, T)) - max(S - K * exp(-r * T), 0.0)) / s})
        out["sigma_to_0"]["rows"][key] = {"S0": S, "at_kink": S == kink, "rows": rows}
    out["sigma_to_0"]["kink_slope_expected"] = K * exp(-r * T) * sqrt(T) / sqrt(2.0 * pi)
    out["sigma_to_0"]["kink_slope_measured"] = out["sigma_to_0"]["rows"][f"S0_{kink:.3f}"]["rows"][-1]["gap_over_sigma"]

    # T -> 0: the call -> max(S_0 - K, 0). At S_0 = K the gap is S_0 sigma sqrt(T/2pi) and N(d_1), N(d_2) -> 1/2.
    Ts = [1.0, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6]
    out["T_to_0"] = {"Ts": Ts, "limit": "max(S_0 - K, 0)", "rows": {}}
    for S in [90.0, 100.0, 110.0]:
        def extra(t, S=S):
            d1, d2 = d1_d2(S, K, r, q, sigma, t)
            return {"N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)),
                    "gap_over_sqrtT": (float(bs_call(S, K, r, q, sigma, t)) - max(S - K, 0.0)) / sqrt(t)}
        rows = limit_table(Ts, lambda t: bs_call(S, K, r, q, sigma, t), lambda t: max(S - K, 0.0), extra)
        out["T_to_0"]["rows"][f"S0_{S:.0f}"] = {"S0": S, "at_kink": S == K, "rows": rows}
    out["T_to_0"]["kink_slope_expected"] = S0 * sigma / sqrt(2.0 * pi)
    out["T_to_0"]["kink_slope_measured"] = out["T_to_0"]["rows"]["S0_100"]["rows"][-1]["gap_over_sqrtT"]

    # S_0 -> infinity: the call -> S_0 - K e^(-rT) (the forward); N(d_1), N(d_2) -> 1.
    Ss = [100.0 * 2 ** k for k in range(7)]
    def extra_inf(S):
        d1, d2 = d1_d2(S, K, r, q, sigma, T)
        return {"N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)), "put": float(bs_put(S, K, r, q, sigma, T))}
    out["S0_to_inf"] = {"S0s": Ss, "limit": "S_0 - K e^(-rT), the forward",
                        "rows": limit_table(Ss, lambda S: bs_call(S, K, r, q, sigma, T), lambda S: S - K * exp(-r * T), extra_inf)}
    # S_0 -> 0: the call -> 0; N(d_1), N(d_2) -> 0.
    Ss0 = [100.0 / 2 ** k for k in range(8)]
    out["S0_to_0"] = {"S0s": Ss0, "limit": "0",
                      "rows": limit_table(Ss0, lambda S: bs_call(S, K, r, q, sigma, T), lambda S: 0.0, extra_inf)}
    return out


# --- C5: the oracle ----------------------------------------------------------------


def quantlib_live(grid_points, S0, K, r, sigma, T) -> dict | None:
    try:
        import QuantLib as ql
    except ImportError:
        return None
    rows = []
    worst_call = worst_put = worst_delta = 0.0
    for (S, k, rr, qq, sg, t) in grid_points:
        F = S * exp((rr - qq) * t)
        disc = exp(-rr * t)
        bc_c = ql.BlackCalculator(ql.PlainVanillaPayoff(ql.Option.Call, k), F, sg * sqrt(t), disc)
        bc_p = ql.BlackCalculator(ql.PlainVanillaPayoff(ql.Option.Put, k), F, sg * sqrt(t), disc)
        c, p = float(bs_call(S, k, rr, qq, sg, t)), float(bs_put(S, k, rr, qq, sg, t))
        dl = float(bs_delta(S, k, rr, qq, sg, t))
        ec, ep, ed = abs(bc_c.value() - c), abs(bc_p.value() - p), abs(bc_c.delta(S) - dl)
        worst_call, worst_put, worst_delta = max(worst_call, ec), max(worst_put, ep), max(worst_delta, ed)
    # the golden generator's engine, at the base case, on dates: T = 365 days under Actual/365 Fixed
    today = ql.Date(1, 1, 2026)
    ql.Settings.instance().evaluationDate = today
    expiry = today + ql.Period(int(round(T * 365)), ql.Days)
    dc = ql.Actual365Fixed()
    spot = ql.QuoteHandle(ql.SimpleQuote(S0))
    rts = ql.YieldTermStructureHandle(ql.FlatForward(today, r, dc))
    qts = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.0, dc))
    vts = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), sigma, dc))
    process = ql.BlackScholesMertonProcess(spot, qts, rts, vts)
    opt = ql.VanillaOption(ql.PlainVanillaPayoff(ql.Option.Call, K), ql.EuropeanExercise(expiry))
    opt.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    engine_T = dc.yearFraction(today, expiry)
    return {"version": ql.__version__, "binding": "QuantLib-Python",
            "grid": {"n_points": len(grid_points), "engine": "BlackCalculator(forward, sigma sqrt T, discount)",
                     "max_abs_error_call": worst_call, "max_abs_error_put": worst_put, "max_abs_error_delta": worst_delta},
            "engine_base_case": {"engine": "AnalyticEuropeanEngine on BlackScholesMertonProcess, Actual/365 Fixed, NullCalendar, evaluation date 2026-01-01",
                                 "T_from_dates": engine_T, "price": opt.NPV(), "delta": opt.delta(),
                                 "closed_form_price": float(bs_call(S0, K, r, 0.0, sigma, engine_T)),
                                 "closed_form_delta": float(bs_delta(S0, K, r, 0.0, sigma, engine_T))}}


def golden_file_check(script_dir: Path) -> dict | None:
    candidates = [script_dir.parent / "golden" / "bs_vanilla.json",   # touchstone/experiments -> touchstone/golden
                  script_dir.parent / "bs_vanilla.json"]              # the learn site's vendor/touchstone layout
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        g = json.load(f)
    tol = g["tolerances"]

    def block(rows, tolerance):
        worst_price = worst_delta = 0.0
        worst_price_row = worst_delta_row = None
        for c in rows:
            S, k, sg, rr, qq, t = c["spot"], c["strike"], c["vol"], c["rate"], c["dividend_yield"], c["expiry_years"]
            if c["type"] == "call":
                price, delta = float(bs_call(S, k, rr, qq, sg, t)), float(bs_delta(S, k, rr, qq, sg, t))
            else:
                price, delta = float(bs_put(S, k, rr, qq, sg, t)), float(bs_delta(S, k, rr, qq, sg, t)) - exp(-qq * t)
            # the file's rule: relative where the reference exceeds 1, absolute otherwise
            ep = abs(price - c["price"]) / (abs(c["price"]) if abs(c["price"]) > 1.0 else 1.0)
            ed = abs(delta - c["delta"]) / (abs(c["delta"]) if abs(c["delta"]) > 1.0 else 1.0)
            if ep > worst_price:
                worst_price, worst_price_row = ep, c.get("label", f"{c['type']} S={S} K={k} vol={sg} r={rr} q={qq} T={t:.4f}")
            if ed > worst_delta:
                worst_delta, worst_delta_row = ed, c.get("label", f"{c['type']} S={S} K={k} vol={sg} r={rr} q={qq} T={t:.4f}")
        return {"n": len(rows), "tolerance": tolerance, "worst_price_error": worst_price, "worst_price_row": worst_price_row,
                "worst_delta_error": worst_delta, "worst_delta_row": worst_delta_row}

    return {"file": str(path.relative_to(script_dir.parent)), "schema": g["schema"], "oracle": g["oracle"],
            "cases": block(g["cases"], tol["cases"]), "edge_cases": block(g["edge_cases"], tol["edge_cases"]),
            "tolerance_rule": tol["note"]}


# --- D6 fixtures -------------------------------------------------------------------


def d6_fixtures(K, r, sigma, taus, S_lo, S_hi, n_S) -> dict:
    S = np.linspace(S_lo, S_hi, n_S)
    curves = {}
    for tau in taus:
        d1, d2 = d1_d2(S, K, r, 0.0, sigma, tau)
        curves[f"tau_{tau:g}"] = {"tau": tau, "call": bs_call(S, K, r, 0.0, sigma, tau).tolist(),
                                  "put": bs_put(S, K, r, 0.0, sigma, tau).tolist(),
                                  "N_d1": Phi(d1).tolist(), "N_d2": Phi(d2).tolist(),
                                  "forward_line": (S - K * exp(-r * tau)).tolist()}
    return {"S": S.tolist(), "taus": taus, "payoff_call": np.maximum(S - K, 0.0).tolist(),
            "payoff_put": np.maximum(K - S, 0.0).tolist(), "curves": curves,
            "parity_line": "call - put = forward_line at every S and tau (C2)"}


# --- checks --------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    def within_se(claim, block, mean_key="mean", target_key=None, target=None, k=5.0):
        m = block[mean_key]
        t = block[target_key] if target_key else target
        add(claim + " (within 5 s.e.)", m, t, k * block["se_of_mean" if "se_of_mean" in block else "se"])

    add("Phi: Hart/West normal CDF agrees with math.erf on [-9, 9] (max abs diff < 1e-13)", res["phi_max_abs_error"], 0.0, 1e-13)

    # C1 -- the integral at the base case
    I, cf = res["integral"]["base"], res["integral"]["base"]["closed_form"]
    add("C1 the integral in S against the lognormal density = the closed form (1e-10)", I["call_S_space"], cf["call"], 1e-10)
    add("C1 the integral in z against the standard normal density = the closed form (1e-10)", I["call_z_space"], cf["call"], 1e-10)
    add("C1 the put's integral = the closed-form put (1e-10)", I["put_S_space"], cf["put"], 1e-10)
    add("C1 stock piece e^(-rT) E^Q[S_T 1(S_T>K)] by quadrature = S_0 N(d_1) (1e-10)", I["stock_piece_S_space"], cf["stock_piece"], 1e-10)
    add("C1 stock piece in z = S_0 N(d_1) (1e-10)", I["stock_piece_z_space"], cf["stock_piece"], 1e-10)
    add("C1 strike piece K e^(-rT) Q(S_T>K) by quadrature = K e^(-rT) N(d_2) (1e-10)", I["strike_piece_S_space"], cf["strike_piece"], 1e-10)
    add("C1 Q(S_T > K) by quadrature = N(d_2) (1e-12)", I["exercise_probability_z_space"], cf["N_d2"], 1e-12)
    add("C1 E^Q[S_T 1(S_T>K)] / E^Q[S_T] by quadrature = N(d_1) (1e-12)", I["share_measure_probability_S_space"], cf["N_d1"], 1e-12)
    add("C1 E^Q[S_T] by quadrature = S_0 e^(rT) (1e-10)", I["E_S_T_S_space"], cf["E_S_T"], 1e-10)
    G = res["integral"]["grid"]
    add(f"C1 grid of {G['n_points']} (S_0, K, r, q, sigma, T): max |quadrature - closed form|, call in S (1e-10)", G["max_abs_error_call_S_space"], 0.0, 1e-10)
    add("C1 grid: max |quadrature - closed form|, call in z (1e-10)", G["max_abs_error_call_z_space"], 0.0, 1e-10)
    add("C1 grid: max |quadrature - closed form|, put (1e-10)", G["max_abs_error_put"], 0.0, 1e-10)
    add("C1 grid: max |quadrature - closed form|, stock piece (1e-10)", G["max_abs_error_stock_piece"], 0.0, 1e-10)
    add("C1 grid: max |quadrature - closed form|, strike piece (1e-10)", G["max_abs_error_strike_piece"], 0.0, 1e-10)
    # C1 -- the Monte Carlo at the base case (and C5's MC agreement)
    M = res["mc"]["q_0"]
    within_se("C1/C5 MC agreement: the Q-run's discounted mean payoff is the closed-form call", M["call"], target_key=None, target=M["closed_form_call"])
    within_se("C1 the Q-run's discounted mean put payoff is the closed-form put", M["put"], target=M["closed_form_put"])
    within_se("C1 the measured probability of exercise under Q is N(d_2)", M["exercise_probability"], target_key="N_d2")
    within_se("C1 the measured stock piece e^(-rT) mean(S_T 1(S_T>K)) is S_0 N(d_1)", M["stock_piece"], target_key="S0_e_qT_N_d1")
    within_se("C1 the measured strike piece K e^(-rT) mean(1(S_T>K)) is K e^(-rT) N(d_2)", M["strike_piece"], target_key="K_e_rT_N_d2")
    within_se("C1 the share-measure probability mean(S_T 1(S_T>K)) / mean(S_T) is N(d_1)", M["share_measure_probability"], mean_key="ratio", target_key="N_d1")
    within_se("C1 E^Q[S_T] = S_0 e^(rT) on the draws", M["E_S_T"], target_key="expected")
    within_se("C1 the conditional mean E^Q[S_T | S_T>K] = S_0 e^(rT) N(d_1)/N(d_2) on the draws", M["conditional_mean_given_itm"], target_key="expected")
    truth("C1 N(d_1) > N(d_2): the share-measure probability exceeds the exercise probability", M["N_d1"] > M["N_d2"])
    D = res["delta"]
    add("C1 dC/dS by a central bump of the closed form = N(d_1), the delta 2.7 hedged with (1e-7)", D["bump_delta"], D["N_d1"], 1e-7)
    add("C1 N(d_1) at the base case is 2.7's delta 0.63 (to 0.005)", D["N_d1"], 0.627, 0.005)

    # C2 -- parity
    PR = res["parity"]
    add(f"C2 closed form across the grid: max |(C - P) - (S_0 e^(-qT) - K e^(-rT))| (1e-12)", PR["grid_max_abs_error"], 0.0, 1e-12)
    for key, run in res["mc"].items():
        add(f"C2 {run['label']}: per path, call payoff - put payoff = S_T - K (1e-9)", run["parity"]["per_path_identity_max_abs"], 0.0, 1e-9)
        within_se(f"C2 {run['label']}: the MC call minus the MC put on the same draws is the forward's value S_0 e^(-qT) - K e^(-rT)", run["parity"]["mc_difference"], target=run["forward_no_arbitrage"])
    add("C2 the MC difference carries the forward's noise, not the option's: its s.e. equals e^(-rT) sd(S_T)/sqrt n (1e-12)",
        M["parity"]["mc_difference"]["se_of_mean"], M["forward_control"]["se_of_mean"], 1e-12)

    # C3 -- limits
    L = res["limits"]
    for key, tab in L["sigma_to_0"]["rows"].items():
        gaps = [row["gap"] for row in tab["rows"]]
        truth(f"C3 sigma -> 0 at S_0 = {tab['S0']:.3f}: the gap to max(S_0 - K e^(-rT), 0) decreases monotonically", all(b <= a + 1e-15 for a, b in zip(gaps, gaps[1:])))
        if tab["at_kink"]:
            add("C3 sigma -> 0 at the kink F = K: gap / sigma -> K e^(-rT) sqrt T / sqrt(2 pi)", L["sigma_to_0"]["kink_slope_measured"], L["sigma_to_0"]["kink_slope_expected"], 1e-6, "rel")
        else:
            add(f"C3 sigma -> 0 at S_0 = {tab['S0']:.0f}: the gap at sigma = 1e-6 is below 1e-9", gaps[-1], 0.0, 1e-9)
    for key, tab in L["T_to_0"]["rows"].items():
        gaps = [row["gap"] for row in tab["rows"]]
        truth(f"C3 T -> 0 at S_0 = {tab['S0']:.0f}: the gap to max(S_0 - K, 0) decreases monotonically", all(b <= a + 1e-15 for a, b in zip(gaps, gaps[1:])))
        if not tab["at_kink"]:
            add(f"C3 T -> 0 at S_0 = {tab['S0']:.0f}: the gap at T = 1e-6 is below 1e-5 (r K T from the discounting, or nothing)", gaps[-1], 0.0, 1e-5)
        else:
            add("C3 T -> 0 at S_0 = K: gap / sqrt T -> S_0 sigma / sqrt(2 pi)", L["T_to_0"]["kink_slope_measured"], L["T_to_0"]["kink_slope_expected"], 1e-3, "rel")
            add("C3 T -> 0 at S_0 = K: N(d_1) -> 1/2", tab["rows"][-1]["N_d1"], 0.5, 1e-3)
            add("C3 T -> 0 at S_0 = K: N(d_2) -> 1/2", tab["rows"][-1]["N_d2"], 0.5, 1e-3)
    rows = L["S0_to_inf"]["rows"]
    truth("C3 S_0 -> infinity: the gap to the forward S_0 - K e^(-rT) decreases monotonically", all(b["gap"] <= a["gap"] + 1e-15 for a, b in zip(rows, rows[1:])))
    add("C3 S_0 -> infinity: the gap at S_0 = 6400 is below 1e-9 (it is the put's price)", rows[-1]["gap"], 0.0, 1e-9)
    add("C3 S_0 -> infinity: N(d_1) -> 1", rows[-1]["N_d1"], 1.0, 1e-12)
    add("C3 S_0 -> infinity: N(d_2) -> 1", rows[-1]["N_d2"], 1.0, 1e-12)
    rows = L["S0_to_0"]["rows"]
    truth("C3 S_0 -> 0: the call decreases monotonically to 0", all(b["gap"] <= a["gap"] + 1e-15 for a, b in zip(rows, rows[1:])))
    add("C3 S_0 -> 0: the call at S_0 = 0.78 is below 1e-9", rows[-1]["gap"], 0.0, 1e-9)
    add("C3 S_0 -> 0: N(d_1) -> 0", rows[-1]["N_d1"], 0.0, 1e-12)
    add("C3 S_0 -> 0: N(d_2) -> 0", rows[-1]["N_d2"], 0.0, 1e-12)

    # C4 -- dividends and Black-76
    for key, row in res["dividends"]["q_rows"].items():
        qv = row["q"]
        add(f"C4 q = {qv}: Black-76 with F = S_0 e^((r-q)T) = the closed form with S_0 e^(-qT) (1e-12)", row["black76_call"], row["closed_form_call"], 1e-12)
        add(f"C4 q = {qv}: Black-76's d_1 (no r) = the closed form's d_1 with r - q (1e-14)", row["black76_d1"], row["closed_form_d1"], 1e-14)
        add(f"C4 q = {qv}: the integral against the lognormal with mean F = the same price (1e-10)", row["quadrature_call"], row["closed_form_call"], 1e-10)
        run = res["mc"][key]
        within_se(f"C4 q = {qv}: the Monte Carlo run with the drift r - q lands on that price", run["call"], target=run["closed_form_call"])
        within_se(f"C4 q = {qv}: the forward's control S_0 e^(-qT) - K e^(-rT) on the same draws", run["forward_control"], target=run["forward_no_arbitrage"])
        within_se(f"C4 q = {qv}: E^Q[S_T] = S_0 e^((r-q)T) on the draws", run["E_S_T"], target_key="expected")
    truth("C4 across the grid the call is decreasing in q (q = 0.03 below q = 0 at every point)", res["dividends"]["call_decreasing_in_q_everywhere"])
    truth("C4 across the grid the put is increasing in q", res["dividends"]["put_increasing_in_q_everywhere"])
    truth("C4 at the base case the call with q = 0.03 is cheaper than with q = 0", res["dividends"]["q_rows"]["q_0.03"]["closed_form_call"] < res["dividends"]["q_rows"]["q_0"]["closed_form_call"])

    # C5 -- the oracle
    O = res["oracle"]
    if O["live"] is not None:
        add(f"C5 QuantLib {O['live']['version']} BlackCalculator at the grid: max |price - closed form|, call (1e-10)", O["live"]["grid"]["max_abs_error_call"], 0.0, 1e-10)
        add("C5 QuantLib BlackCalculator at the grid: max |price - closed form|, put (1e-10)", O["live"]["grid"]["max_abs_error_put"], 0.0, 1e-10)
        add("C5 QuantLib BlackCalculator at the grid: max |delta - e^(-qT) N(d_1)| (1e-10)", O["live"]["grid"]["max_abs_error_delta"], 0.0, 1e-10)
        E = O["live"]["engine_base_case"]
        add("C5 QuantLib AnalyticEuropeanEngine on BlackScholesMertonProcess (the golden generator's engine), base case: price (1e-10)", E["price"], E["closed_form_price"], 1e-10)
        add("C5 QuantLib AnalyticEuropeanEngine, base case: delta = N(d_1) (1e-10)", E["delta"], E["closed_form_delta"], 1e-10)
    elif not params["quick"]:
        truth("C5 QuantLib-Python present for the live oracle comparison (I4) -- required for the full run", False)
    if O["golden"] is not None:
        g = O["golden"]
        add(f"C5 golden/bs_vanilla.json (QuantLib {g['oracle']['version']}): {g['cases']['n']} grid cases, worst price error within the file's tolerance", g["cases"]["worst_price_error"], 0.0, g["cases"]["tolerance"])
        add(f"C5 golden grid cases: worst delta error within the file's tolerance", g["cases"]["worst_delta_error"], 0.0, g["cases"]["tolerance"])
        add(f"C5 golden edge cases ({g['edge_cases']['n']}): worst price error within the file's tolerance", g["edge_cases"]["worst_price_error"], 0.0, g["edge_cases"]["tolerance"])
        add("C5 golden edge cases: worst delta error within the file's tolerance", g["edge_cases"]["worst_delta_error"], 0.0, g["edge_cases"]["tolerance"])
        truth("C5 the golden file records its QuantLib version (I4)", bool(g["oracle"].get("version")))
    elif not params["quick"]:
        truth("C5 golden/bs_vanilla.json present for the committed-oracle comparison (I4) -- required for the full run", False)

    # D6 -- fixtures are consistent with C2 and the payoff
    F = res["d6"]
    S = np.array(F["S"])
    worst_parity = 0.0
    above_payoff = True
    for key, c in F["curves"].items():
        worst_parity = max(worst_parity, float(np.abs(np.array(c["call"]) - np.array(c["put"]) - np.array(c["forward_line"])).max()))
        above_payoff &= bool(np.all(np.array(c["call"]) >= np.array(F["payoff_call"]) - 1e-12))
    add("D6 fixtures: call - put = the forward line at every S and tau (1e-12)", worst_parity, 0.0, 1e-12)
    truth("D6 fixtures: the call curve lies on or above its payoff at every S and tau", above_payoff)
    return checks


# --- main ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the draws, no JSON written; the oracle comparisons skipped if unavailable")
    args = parser.parse_args()

    q = args.quick
    n_mc = 100_000 if q else 1_000_000
    params = {
        "seed": args.seed, "quick": q,
        "T": 1.0, "S0": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.40, "q": 0.0,
        "model": "dS = r S dt + sigma S dW~ under Q (drift first), S_T = S_0 exp((r - q - 1/2 sigma^2) T + sigma sqrt T Z) drawn exactly (2.6's decision 1)",
        "formula": "C = S_0 e^(-qT) N(d_1) - K e^(-rT) N(d_2); d_1 = (ln(S_0/K) + (r - q + 1/2 sigma^2) T)/(sigma sqrt T); d_2 = d_1 - sigma sqrt T. P = K e^(-rT) N(-d_2) - S_0 e^(-qT) N(-d_1). Black-76: e^(-rT)[F N(d_1) - K N(d_2)], F = S_0 e^((r-q)T), d_1 = (ln(F/K) + 1/2 sigma^2 T)/(sigma sqrt T)",
        "quadrature": {"rule": "composite Gauss-Legendre", "panels": 64, "nodes": 32, "z_max": 40.0},
        "grid": {"S0": [80.0, 100.0, 120.0], "K": [90.0, 100.0, 110.0], "r": [0.0, 0.05], "q": [0.0, 0.03], "sigma": [0.2, 0.4], "T": [0.25, 1.0, 2.0]},
        "n_mc": n_mc, "n_mc_full": 1_000_000, "q_values": [0.0, 0.03, 0.08],
        "delta_bump_h": 0.01,
        "limits": {"sigmas": [0.4, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6], "Ts": [1.0, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6],
                   "S0_to_inf": [100.0 * 2 ** k for k in range(7)], "S0_to_0": [100.0 / 2 ** k for k in range(8)]},
        "d6": {"S": [40.0, 200.0, 161], "taus": [1.0, 0.5, 0.25, 0.05]},
    }
    T, S0, K, r, sigma = params["T"], params["S0"], params["K"], params["r"], params["sigma"]
    Q = params["quadrature"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    phi_err = phi_self_test()
    print(f"[2.9] Phi self-test: max abs error {phi_err:.2e}", flush=True)
    d1, d2 = (float(v) for v in d1_d2(S0, K, r, 0.0, sigma, T))
    C, P = float(bs_call(S0, K, r, 0.0, sigma, T)), float(bs_put(S0, K, r, 0.0, sigma, T))
    print(f"[2.9] closed form: r = {r}, sigma = {sigma}, S_0 = K = {S0:.0f}, T = {T}: d_1 = {d1:.4f}, d_2 = {d2:.4f}, "
          f"N(d_1) = {float(Phi(d1)):.4f}, N(d_2) = {float(Phi(d2)):.4f}; C = {C:.4f}, P = {P:.4f}, C - P = {C - P:.4f}, "
          f"forward S_0 - K e^(-rT) = {forward_value(S0, K, r, 0.0, T):.4f}", flush=True)

    # C1: the integral, base case and grid
    print(f"[2.9] C1 quadrature: {Q['rule']}, {Q['panels']} panels x {Q['nodes']} nodes, in S against the lognormal density and in z", flush=True)
    base_I = integrate(S0, K, r, 0.0, sigma, T, Q["panels"], Q["nodes"], Q["z_max"])
    g = params["grid"]
    grid_points = [(S, k, rr, qq, sg, t) for S in g["S0"] for k in g["K"] for rr in g["r"] for qq in g["q"] for sg in g["sigma"] for t in g["T"]]
    worst = {"call_S_space": 0.0, "call_z_space": 0.0, "put": 0.0, "stock_piece": 0.0, "strike_piece": 0.0}
    parity_worst = 0.0
    call_dec = put_inc = True
    for (S, k, rr, qq, sg, t) in grid_points:
        I = integrate(S, k, rr, qq, sg, t, Q["panels"], Q["nodes"], Q["z_max"])
        cf = I["closed_form"]
        worst["call_S_space"] = max(worst["call_S_space"], abs(I["call_S_space"] - cf["call"]))
        worst["call_z_space"] = max(worst["call_z_space"], abs(I["call_z_space"] - cf["call"]))
        worst["put"] = max(worst["put"], abs(I["put_S_space"] - cf["put"]))
        worst["stock_piece"] = max(worst["stock_piece"], abs(I["stock_piece_S_space"] - cf["stock_piece"]))
        worst["strike_piece"] = max(worst["strike_piece"], abs(I["strike_piece_S_space"] - cf["strike_piece"]))
        parity_worst = max(parity_worst, abs((cf["call"] - cf["put"]) - forward_value(S, k, rr, qq, t)))
        if qq == 0.0:
            c0, c3 = float(bs_call(S, k, rr, 0.0, sg, t)), float(bs_call(S, k, rr, 0.03, sg, t))
            p0, p3 = float(bs_put(S, k, rr, 0.0, sg, t)), float(bs_put(S, k, rr, 0.03, sg, t))
            call_dec &= c3 < c0
            put_inc &= p3 > p0
    integral = {"base": base_I, "grid": {"n_points": len(grid_points), **{f"max_abs_error_{k}": v for k, v in worst.items()}}}
    print(f"[2.9] C1 base: call in S {base_I['call_S_space']:.10f}, in z {base_I['call_z_space']:.10f}, closed form {C:.10f}; "
          f"pieces {base_I['stock_piece_S_space']:.6f} + {-base_I['strike_piece_S_space']:.6f}; grid worst {max(worst.values()):.2e}", flush=True)

    # the Monte Carlo runs: q = 0 (C1, C2, C5's MC agreement) and the dividend yields (C4)
    mc = {}
    for qv in params["q_values"]:
        label = f"q_{qv:g}"
        print(f"[2.9] Monte Carlo: drift r - q = {r - qv:+.2f}, sigma = {sigma}; {n_mc:,} exact draws of S_T (q = {qv})", flush=True)
        mc[label] = mc_run(rng, n_mc, S0, K, r, qv, sigma, T, label)
    M = mc["q_0"]
    print(f"[2.9] C1 MC at q = 0: call {M['call']['mean']:.4f} ± {M['call']['se_of_mean']:.4f} ({M['call']['error_in_se']:+.1f} s.e.); "
          f"Q(S_T > K) = {M['exercise_probability']['mean']:.4f} vs N(d_2) {M['N_d2']:.4f}; "
          f"share-measure {M['share_measure_probability']['ratio']:.4f} ± {M['share_measure_probability']['se']:.4f} vs N(d_1) {M['N_d1']:.4f}; "
          f"E[S_T | ITM] = {M['conditional_mean_given_itm']['mean']:.2f}", flush=True)
    print(f"[2.9] C2 parity on the draws: C - P = {M['parity']['mc_difference']['mean']:.4f} ± {M['parity']['mc_difference']['se_of_mean']:.4f} "
          f"vs S_0 - K e^(-rT) = {M['forward_no_arbitrage']:.4f}; per-path identity {M['parity']['per_path_identity_max_abs']:.1e}", flush=True)

    # the delta 2.7 hedged with
    h = params["delta_bump_h"]
    delta = {"N_d1": float(Phi(d1)), "analytic": float(bs_delta(S0, K, r, 0.0, sigma, T)),
             "bump_delta": float((bs_call(S0 + h, K, r, 0.0, sigma, T) - bs_call(S0 - h, K, r, 0.0, sigma, T)) / (2 * h)), "h": h,
             "note": "2.7 hedged with Delta = N(d_1) = 0.63 as a black box; here it is the derivative of the formula derived on this page"}

    # C3: limits
    print("[2.9] C3 limits: sigma -> 0, T -> 0, S_0 -> infinity, S_0 -> 0", flush=True)
    lim = limits(S0, K, r, sigma, T)

    # C4: dividends and Black-76 -- three spellings
    q_rows = {}
    for qv in params["q_values"]:
        F = S0 * exp((r - qv) * T)
        b76, b76_d1, b76_d2 = black76_call(F, K, r, sigma, T)
        cd1, cd2 = (float(v) for v in d1_d2(S0, K, r, qv, sigma, T))
        I = integrate(S0, K, r, qv, sigma, T, Q["panels"], Q["nodes"], Q["z_max"])
        q_rows[f"q_{qv:g}"] = {"q": qv, "F": F, "closed_form_call": float(bs_call(S0, K, r, qv, sigma, T)), "closed_form_put": float(bs_put(S0, K, r, qv, sigma, T)),
                               "closed_form_d1": cd1, "closed_form_d2": cd2, "black76_call": b76, "black76_d1": b76_d1, "black76_d2": b76_d2,
                               "quadrature_call": I["call_z_space"], "forward_no_arbitrage": forward_value(S0, K, r, qv, T),
                               "S0_e_qT": S0 * exp(-qv * T), "N_d1": float(Phi(cd1)), "N_d2": float(Phi(cd2))}
        print(f"[2.9] C4 q = {qv}: drift r - q = {r - qv:+.2f}; closed form {q_rows[f'q_{qv:g}']['closed_form_call']:.6f}, Black-76 (F = {F:.4f}) {b76:.6f}, "
              f"MC {mc[f'q_{qv:g}']['call']['mean']:.4f} ± {mc[f'q_{qv:g}']['call']['se_of_mean']:.4f}; forward {forward_value(S0, K, r, qv, T):.4f}", flush=True)
    dividends = {"q_rows": q_rows, "call_decreasing_in_q_everywhere": bool(call_dec), "put_increasing_in_q_everywhere": bool(put_inc),
                 "note": "three spellings of one formula: S_0 e^(-qT) in the price and in d_1; the forward F in Black-76 with r only in the discount; the simulator with the drift r - q"}

    # C5: the oracle
    print("[2.9] C5 oracle: QuantLib-Python at the grid and the golden generator's engine; the committed golden file", flush=True)
    live = quantlib_live(grid_points, S0, K, r, sigma, T)
    golden = golden_file_check(Path(__file__).resolve().parent)
    if live is None:
        print("[2.9] C5: QuantLib-Python not importable -- live oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        print(f"[2.9] C5: QuantLib {live['version']}: grid worst call {live['grid']['max_abs_error_call']:.1e}, put {live['grid']['max_abs_error_put']:.1e}, delta {live['grid']['max_abs_error_delta']:.1e}; "
              f"engine base case {live['engine_base_case']['price']:.10f} vs {live['engine_base_case']['closed_form_price']:.10f}", flush=True)
    if golden is None:
        print("[2.9] C5: golden/bs_vanilla.json not found -- committed-oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        print(f"[2.9] C5: {golden['file']} (QuantLib {golden['oracle']['version']}): {golden['cases']['n']} cases worst price {golden['cases']['worst_price_error']:.1e}, delta {golden['cases']['worst_delta_error']:.1e}; "
              f"{golden['edge_cases']['n']} edge cases worst price {golden['edge_cases']['worst_price_error']:.1e} ({golden['edge_cases']['worst_price_row']}), delta {golden['edge_cases']['worst_delta_error']:.1e}", flush=True)
    oracle = {"live": live, "golden": golden}

    # D6 fixtures
    D = params["d6"]
    d6 = d6_fixtures(K, r, sigma, D["taus"], D["S"][0], D["S"][1], D["S"][2])

    results = {"phi_max_abs_error": phi_err,
               "base": {"d1": d1, "d2": d2, "N_d1": float(Phi(d1)), "N_d2": float(Phi(d2)), "N_d1_minus_N_d2": float(Phi(d1) - Phi(d2)),
                        "call": C, "put": P, "call_minus_put": C - P, "forward_no_arbitrage": forward_value(S0, K, r, 0.0, T),
                        "E_Q_S_T": S0 * exp(r * T), "stock_piece_S0_N_d1": S0 * float(Phi(d1)), "strike_piece_K_e_rT_N_d2": K * exp(-r * T) * float(Phi(d2)),
                        "partial_expectation_E_Q_S_T_1_ITM": S0 * exp(r * T) * float(Phi(d1)),
                        "conditional_mean_E_Q_S_T_given_ITM": S0 * exp(r * T) * float(Phi(d1)) / float(Phi(d2))},
               "integral": integral, "mc": mc, "delta": delta, "parity": {"grid_max_abs_error": parity_worst, "identity": "C - P = S_0 e^(-qT) - K e^(-rT)"},
               "limits": lim, "dividends": dividends, "oracle": oracle, "d6": d6}
    checks = build_checks(results, params)

    out = {"page": "2.9", "script": Path(__file__).name, "params": params,
           "environment": {"numpy": np.__version__, "quantlib": live["version"] if live else None,
                           "golden_oracle": golden["oracle"] if golden else None},
           "results": results, "checks": checks}
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.9] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  ({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.9] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
