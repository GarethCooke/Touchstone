"""Where it breaks -- the experiment behind page 2.11.

Serves page 2.11 (docs/quant-learn-index-v1.md), the last page of Part 2. Pages
2.6-2.10 built the Black-Scholes model on three assumptions and used each one:
a single known volatility sigma (2.6, 2.7, 2.9), continuous frictionless
rebalancing (2.7, where N -> infinity was the limit and no cost was charged), and
lognormal returns (2.6, whose test battery checked the moments of log S_T). This
page breaks each one in turn, measures what breaks with it, and shows why the
formula survives anyway: as the quoting convention -- "vol is the unit of price".

Session S11's setup decisions (owner, 2026-11-08, all the recommendations):
(Q1/a) the synthetic market is a two-component lognormal mixture -- the stock
is GBM at sigma_low with probability p and at sigma_high with probability 1 - p,
the component forwards tied so the mixture's forward is F = S_0 e^(rT); every
price is p C(sigma_low, F_low) + (1 - p) C(sigma_high, F_high), closed form. A
second, asymmetric mixture (the high-vol component with the lower forward)
gives skew. (Q2/a) one hedging break measured -- 2.7's hedge with Black-Scholes
deltas at the implied vol on the mixture's paths, the spread against N -- and
the transaction-cost break in one table (cost ~ sqrt N); Leland is v2's.
(Q3/a) one expiry's smile on the page; the four-tau smiles are D9 fixtures only;
vanna and volga named, not computed. (Q4/a) the page ends Part 2 with a bridge.

  C1  The implied-vol solver. Newton on sigma with 2.10's vega, safeguarded by
      bisection on [1e-6, 5]: round-trips 2.9's formula on the 216-point grid
      (call and put) and every row of golden/bs_vanilla.json (7,200 + 34): recover
      the row's vol from its price to 1e-10 where vega is not vanishing, and
      record what happens where it is (the price is flat in sigma at double
      precision, so the vol is not identifiable from the price -- the solver
      returns a sigma that reproduces the price, not the row's sigma). The
      no-arbitrage bounds max(S_0 e^(-qT) - K e^(-rT), 0) < C < S_0 e^(-qT) and the
      solver's refusal outside them; the iteration trace from sigma_0 = 0.2 at
      the base case (Newton's quadratic tail); QuantLib's blackFormulaImpliedStdDev
      as the second oracle (I4). The first root finder on a study page -- 3.4
      owns the general theory; 2.11 states one working method and its guard.
  C2  The synthetic market. The symmetric mixture (p = 1/2, sigma = 0.2 / 0.6,
      equal forwards): prices at strikes 60-160, T = 1, closed form; the implied
      vol at each strike by C1; the smile measured -- its minimum (at the forward
      F, not the spot), its level against the mean vol 0.40 and the rms vol
      sqrt(1/2 0.2^2 + 1/2 0.6^2) = 0.447, the wings rising towards sigma_high,
      the symmetry sigma(K) = sigma(F^2/K) in log-moneyness; at the money the
      price is almost linear in sigma, so the mixture's price is the price at
      (nearly) the mean vol, below the price at the rms vol -- the Jensen gap,
      quantified. Put-call parity holds exactly across the smile (the mixture's
      forward is F), so the put's implied vol equals the call's. The asymmetric
      mixture (p = 3/4, sigma = 0.3 / 0.6, forwards 1.05 F / 0.85 F): skew. The
      terminal distribution's excess kurtosis on 10^6 draws against the closed
      form for a mixture of normals, and against the lognormal's 0.
  C3  Lognormal returns vs reality, on the mixture's paths: 2.6's test battery
      (log-return mean, variance, skewness, kurtosis; E[S_T]; the median; the sd
      of S_T) applied to the mixture's draws against two lognormals with the
      fitted vol: the one matching the mixture's first two log moments for the
      log-moment rows and the median, and the one with the forward F for E[S_T]
      and the sd -- which checks pass and which fail, and by how many s.e.; daily log-returns (252 steps, 20,000 paths): the pooled kurtosis
      and the fraction beyond 3 sd against the normal's 0.27 %, and the same
      within each vol state (Gaussian -- the fat tails are the mixing).
  C4  The hedge under the wrong model. 2.7's delta hedge written as a bank
      account (buy the option at P_0, short Delta shares, cash at r, rebalance N
      times, liquidate at T), checked against 2.7's telescoped formula per path.
      Three books: the control -- GBM at sigma = 0.4 hedged at 0.4 (2.7's base,
      the spread ~ 1/sqrt N, sd sqrt N ~ 13.5 cited); the mixture hedged with
      Black-Scholes deltas at the ATM implied vol, the option bought at the
      mixture's price -- the spread against N tends to a floor, not zero; the
      oracle hedge -- the same paths, the deltas at each path's true vol -- whose
      within-state spread does fall like 1/sqrt N, leaving exactly the between-
      state piece: the two-point distribution C(sigma_j) - C_mix, sd sqrt(p(1-p))
      |C(sigma_high) - C(sigma_low)| = 7.54. Paths are drawn under the pricing
      drift mu = r (Decision -- owner may overrule: under it the mean hedged P&L
      is zero for every N and every hedge, 2.8's argument, so the spread is the
      whole story; 2.7 showed the hedge is drift-blind in the limit, so the
      choice costs nothing); per-state means are C(sigma_j) - C_mix at every N.
  C5  Transaction costs. A proportional fee k = 10 basis points on every share
      traded, tracked in C4's books: the rebalancing cost's mean against N grows
      like sqrt N (each trade ~ 1/sqrt N, N of them); the ratio for N -> 4N tends
      to 2, the log-log slope to 1/2; the trade-off table -- spread falling as
      1/sqrt N, cost rising as sqrt N -- and the N on the grid at which their sum
      is smallest. Leland's adjusted sigma is named for v2, not derived.
  D9  Fixtures for the implied-vol solver and smile viewer (2.11, 3.4): the
      smile (strike, mixture price, implied vol) at tau = 1, 1/2, 1/4, 0.05 for
      both mixtures; the solver's trace at the base case; the kurtosis table; the
      P5 quote (the stock at 110: the price quote stale, the vol quote not).
      Fixtures carry no claim beyond C1-C5; the site draws them (I15).

Run from the repository root:

    uv run experiments/2_11_where_it_breaks.py [--seed 20261108] [--quick]

--quick runs a tenth of the paths and N up to 256 only, and NO JSON is written --
the committed result is always the full run (I3). Under --quick the live
QuantLib comparison and the golden-file comparison are skipped with a notice if
QuantLib or the file is not present; the full run requires both (I4).

Writes 2_11_where_it_breaks.json beside this file: parameters in, results out,
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


# --- the normal CDF and density, vectorised (2.9's Phi, 2.10's phi) -------------------------


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
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x * x) / sqrt(2.0 * pi)


def phi_self_test() -> float:
    xs = np.linspace(-9.0, 9.0, 36001)
    ref = np.array([0.5 * (1.0 + erf(v / sqrt(2.0))) for v in xs])
    return float(np.abs(Phi(xs) - ref).max())


# --- the closed form, its delta and vega (2.9, 2.10), sigma allowed to vary per path ---------


def price(S, K, r, q, sigma, T, w=1):
    """w = +1 the call C = S e^(-qT) N(d_1) - K e^(-rT) N(d_2); w = -1 the put. S and sigma may be arrays."""
    S = np.asarray(S, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    st = sigma * sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / st
    d2 = d1 - st
    return w * (S * exp(-q * T) * Phi(w * d1) - K * exp(-r * T) * Phi(w * d2))


def delta(S, K, r, q, sigma, T, w=1):
    S = np.asarray(S, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    st = sigma * sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / st
    return w * exp(-q * T) * Phi(w * d1)


def vega(S, K, r, q, sigma, T):
    """2.10's vega = S e^(-qT) phi(d_1) sqrt T, per 1.00 of sigma, the same for call and put."""
    S = np.asarray(S, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    st = sigma * sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / st
    return S * exp(-q * T) * phi(d1) * sqrt(T)


def no_arbitrage_bounds(S, K, r, q, T, w=1) -> tuple[float, float]:
    """The price's range as sigma runs from 0 to infinity: the forward intrinsic value to the
    stock (call) or the discounted strike (put). Only prices strictly inside have an implied vol."""
    fwd_intrinsic = max(w * (S * exp(-q * T) - K * exp(-r * T)), 0.0)
    upper = S * exp(-q * T) if w > 0 else K * exp(-r * T)
    return fwd_intrinsic, upper


# --- C1: the implied-vol solver ---------------------------------------------------------------


def implied_vol(target, S, K, r, q, T, w=1, sigma0=0.2, lo=1e-6, hi=5.0, price_tol=1e-12, sigma_tol=1e-14, max_iter=100, trace=False) -> dict:
    """Newton on sigma with the analytic vega, bisection-safeguarded on [lo, hi].

    Returns sigma, the iteration count, how many steps were bisections, the achieved price
    error, and a status: 'converged'; 'below_lower_bound' / 'above_upper_bound' (no sigma
    gives this price -- the no-arbitrage bounds); 'below_sigma_lo' / 'above_sigma_hi' (the
    price is inside the bounds but outside [price(lo), price(hi)], so the answer lies outside
    the search interval); 'max_iter'. The stopping rule: |price(sigma) - target| <= price_tol x
    max(1, |target|) -- relative above 1, absolute below, the golden file's rule -- or the
    bracket narrower than sigma_tol. Where vega is tiny the price is flat in sigma at double
    precision and the recovered sigma is one of many that reproduce the price (C1 records it).
    """
    f = lambda s: float(price(S, K, r, q, s, T, w))
    lower, upper = no_arbitrage_bounds(S, K, r, q, T, w)
    tol = price_tol * max(1.0, abs(target))
    out = {"sigma": float("nan"), "iterations": 0, "bisections": 0, "price_error": float("nan"), "status": None,
           "lower_bound": lower, "upper_bound": upper}
    if trace:
        out["trace"] = []
    if target < lower - tol:
        out["status"] = "below_lower_bound"
        return out
    if target > upper + tol:
        out["status"] = "above_upper_bound"
        return out
    f_lo, f_hi = f(lo), f(hi)
    if target < f_lo - tol:
        out.update(sigma=lo, price_error=f_lo - target, status="below_sigma_lo")
        return out
    if target > f_hi + tol:
        out.update(sigma=hi, price_error=f_hi - target, status="above_sigma_hi")
        return out
    a, b = lo, hi                      # the bracket: f(a) <= target <= f(b), f increasing in sigma
    s = min(max(sigma0, a), b)
    for it in range(1, max_iter + 1):
        p = f(s)
        diff = p - target
        if trace:
            out["trace"].append({"iteration": it, "sigma": s, "price": p, "price_error": diff})
        if abs(diff) <= tol:
            out.update(sigma=s, iterations=it, price_error=diff, status="converged")
            return out
        if diff > 0:
            b = s
        else:
            a = s
        v = float(vega(S, K, r, q, s, T))
        s_newton = s - diff / v if v > 0 else float("nan")
        if np.isfinite(s_newton) and a < s_newton < b:
            s = s_newton
        else:
            s = 0.5 * (a + b)
            out["bisections"] += 1
        if b - a < sigma_tol:
            p = f(s)
            out.update(sigma=s, iterations=it, price_error=p - target, status="converged")
            return out
    out.update(sigma=s, iterations=max_iter, price_error=f(s) - target, status="max_iter")
    return out


def solver_round_trip_grid(grid_points, solver) -> dict:
    worst = {"call": 0.0, "put": 0.0}
    worst_row = {"call": None, "put": None}
    iters = []
    statuses = {}
    for (S, k, rr, qq, sg, t) in grid_points:
        for w, name in ((+1, "call"), (-1, "put")):
            p = float(price(S, k, rr, qq, sg, t, w))
            res = implied_vol(p, S, k, rr, qq, t, w, **solver)
            statuses[res["status"]] = statuses.get(res["status"], 0) + 1
            iters.append(res["iterations"])
            e = abs(res["sigma"] - sg) if np.isfinite(res["sigma"]) else float("inf")
            if e > worst[name]:
                worst[name], worst_row[name] = e, f"{name} S={S} K={k} r={rr} q={qq} sigma={sg} T={t}: recovered {res['sigma']!r}, {res['iterations']} it, status {res['status']}"
    return {"n_points": len(grid_points), "call_and_put": True, "max_abs_sigma_error_call": worst["call"], "max_abs_sigma_error_put": worst["put"],
            "worst_row_call": worst_row["call"], "worst_row_put": worst_row["put"],
            "iterations": {"mean": float(np.mean(iters)), "max": int(max(iters)), "min": int(min(iters))}, "statuses": statuses}


def solver_golden_check(script_dir: Path, solver) -> dict | None:
    candidates = [script_dir.parent / "golden" / "bs_vanilla.json", script_dir.parent / "bs_vanilla.json"]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        g = json.load(f)

    def block(rows):
        """Three classes by the row's vega. vega >= 1 per unit: the vol is identifiable to 1e-10 from a 1e-12 price.
        1e-8 <= vega < 1: identifiable to price_tol x max(1, price) / vega -- the vol error is the price error divided
        by vega, so it is checked against that bound. vega < 1e-8: the price is flat in sigma at double precision;
        the solver reproduces the price but the row's vol is not recoverable from it."""
        n = len(rows)
        v_hi, v_lo = 1.0, 1e-8
        tol0 = solver["price_tol"]
        out = {"n": n, "statuses": {}, "n_inside_bounds": 0, "n_on_lower_bound": 0, "vega_thresholds": {"identifiable": v_hi, "price_only": v_lo},
               "identifiable": {"n": 0, "max_abs_sigma_error": 0.0, "worst_row": None, "max_abs_price_error_rel": 0.0, "iterations_max": 0},
               "vega_limited": {"n": 0, "max_abs_sigma_error": 0.0, "max_ratio_sigma_error_to_bound": 0.0, "worst_row": None, "max_abs_price_error_rel": 0.0, "iterations_max": 0,
                                "bound": "price_tol x max(1, price) / vega(sigma_row)"},
               "not_identifiable": {"n": 0, "max_abs_price_error_rel": 0.0, "max_abs_sigma_error": 0.0, "rows": []}}
        for c in rows:
            S, k, sg, rr, qq, t = c["spot"], c["strike"], c["vol"], c["rate"], c["dividend_yield"], c["expiry_years"]
            w = 1 if c["type"] == "call" else -1
            target = c["price"]
            res = implied_vol(target, S, k, rr, qq, t, w, **solver)
            out["statuses"][res["status"]] = out["statuses"].get(res["status"], 0) + 1
            lower, upper = res["lower_bound"], res["upper_bound"]
            tol = tol0 * max(1.0, abs(target))
            if lower - tol <= target <= upper + tol:
                out["n_inside_bounds"] += 1
            if abs(target - lower) <= tol:
                out["n_on_lower_bound"] += 1
            label = c.get("label", f"{c['type']} S={S} K={k} vol={sg} r={rr} q={qq} T={t:.4f}")
            v_true = float(vega(S, k, rr, qq, sg, t))
            s_err = abs(res["sigma"] - sg) if np.isfinite(res["sigma"]) else float("inf")
            p_err_rel = abs(res["price_error"]) / max(1.0, abs(target)) if np.isfinite(res["price_error"]) else float("inf")
            if v_true >= v_hi:
                blk = out["identifiable"]
                blk["n"] += 1
                blk["iterations_max"] = max(blk["iterations_max"], res["iterations"])
                blk["max_abs_price_error_rel"] = max(blk["max_abs_price_error_rel"], p_err_rel)
                if s_err > blk["max_abs_sigma_error"]:
                    blk["max_abs_sigma_error"], blk["worst_row"] = s_err, f"{label}: recovered {res['sigma']!r}, vega {v_true:.3g}, status {res['status']}"
            elif v_true >= v_lo:
                blk = out["vega_limited"]
                blk["n"] += 1
                blk["iterations_max"] = max(blk["iterations_max"], res["iterations"])
                blk["max_abs_price_error_rel"] = max(blk["max_abs_price_error_rel"], p_err_rel)
                blk["max_abs_sigma_error"] = max(blk["max_abs_sigma_error"], s_err)
                ratio = s_err / (tol / v_true)
                if ratio > blk["max_ratio_sigma_error_to_bound"]:
                    blk["max_ratio_sigma_error_to_bound"], blk["worst_row"] = ratio, f"{label}: recovered {res['sigma']!r}, vega {v_true:.3g}, sigma error {s_err:.2e} vs bound {tol / v_true:.2e}"
            else:
                blk = out["not_identifiable"]
                blk["n"] += 1
                blk["max_abs_price_error_rel"] = max(blk["max_abs_price_error_rel"], p_err_rel)
                blk["max_abs_sigma_error"] = max(blk["max_abs_sigma_error"], s_err)
                if len(blk["rows"]) < 40:
                    blk["rows"].append({"label": label, "vol": sg, "vega": v_true, "price": target, "recovered": res["sigma"], "price_error": res["price_error"], "status": res["status"]})
        return out

    return {"file": str(path.relative_to(script_dir.parent)), "schema": g["schema"], "oracle": g["oracle"],
            "cases": block(g["cases"]), "edge_cases": block(g["edge_cases"])}


def quantlib_implied_vol(grid_points, solver) -> dict | None:
    """QuantLib's blackFormulaImpliedStdDev (no dates: forward, discount, Black price) as the second oracle."""
    try:
        import QuantLib as ql
    except ImportError:
        return None
    worst, worst_row = 0.0, None
    for (S, k, rr, qq, sg, t) in grid_points:
        F, disc = S * exp((rr - qq) * t), exp(-rr * t)
        for w, typ in ((+1, ql.Option.Call), (-1, ql.Option.Put)):
            p = float(price(S, k, rr, qq, sg, t, w))
            ours = implied_vol(p, S, k, rr, qq, t, w, **solver)["sigma"]
            theirs = ql.blackFormulaImpliedStdDev(typ, k, F, p, disc, 0.0, 0.2 * sqrt(t), 1e-15, 200) / sqrt(t)
            e = abs(ours - theirs)
            if e > worst:
                worst, worst_row = e, f"{'call' if w > 0 else 'put'} S={S} K={k} r={rr} q={qq} sigma={sg} T={t}: ours {ours!r}, QuantLib {theirs!r}"
    return {"version": ql.__version__, "binding": "QuantLib-Python", "engine": "blackFormulaImpliedStdDev(type, strike, forward, price, discount, 0, guess 0.2 sqrt T, accuracy 1e-15) / sqrt T",
            "n_points": len(grid_points), "call_and_put": True, "max_abs_sigma_error": worst, "worst_row": worst_row}


# --- C2: the mixture market -------------------------------------------------------------------


def mixture_price(K, S0, r, T, mix, w=1):
    """p-weighted Black-Scholes prices, each component on its own forward F_j = f_j S_0 e^(rT),
    priced as the Black-Scholes price at spot f_j S_0 (same r, q = 0). Sum p_j f_j = 1 keeps the forward."""
    K = np.asarray(K, dtype=float)
    out = np.zeros_like(K, dtype=float)
    for p, sg, fwd in zip(mix["p"], mix["sigmas"], mix["forward_factors"]):
        out = out + p * price(fwd * S0, K, r, 0.0, sg, T, w)
    return out


def smile(mix, S0, r, T, strikes, solver) -> dict:
    """Mixture prices and implied vols across strikes, call and put, with the solver's statuses."""
    F = S0 * exp(r * T)
    calls = mixture_price(strikes, S0, r, T, mix, +1)
    puts = mixture_price(strikes, S0, r, T, mix, -1)
    iv_c, iv_p, st_c, st_p, it_c = [], [], [], [], []
    for K_, c_, p_ in zip(strikes, calls, puts):
        rc = implied_vol(float(c_), S0, float(K_), r, 0.0, T, +1, **solver)
        rp = implied_vol(float(p_), S0, float(K_), r, 0.0, T, -1, **solver)
        iv_c.append(rc["sigma"] if rc["status"] == "converged" else float("nan"))
        iv_p.append(rp["sigma"] if rp["status"] == "converged" else float("nan"))
        st_c.append(rc["status"])
        st_p.append(rp["status"])
        it_c.append(rc["iterations"])
    iv_c, iv_p = np.array(iv_c), np.array(iv_p)
    vega_c = np.array([float(vega(S0, float(K_), r, 0.0, s_, T)) if np.isfinite(s_) else 0.0 for K_, s_ in zip(strikes, iv_c)])
    vega_p = np.array([float(vega(S0, float(K_), r, 0.0, s_, T)) if np.isfinite(s_) else 0.0 for K_, s_ in zip(strikes, iv_p)])
    both = np.isfinite(iv_c) & np.isfinite(iv_p) & (vega_c >= 1e-3) & (vega_p >= 1e-3)
    parity_gap = calls - puts - (S0 - strikes * exp(-r * T))
    i_min = int(np.nanargmin(iv_c))
    return {"strikes": strikes.tolist(), "forward": F, "T": T,
            "call_price": calls.tolist(), "put_price": puts.tolist(),
            "implied_vol_call": [None if not np.isfinite(v) else float(v) for v in iv_c],
            "implied_vol_put": [None if not np.isfinite(v) else float(v) for v in iv_p],
            "solver_status_call": st_c, "solver_status_put": st_p, "solver_iterations_call_max": int(max(it_c)),
            "n_strikes_with_vol": int(np.isfinite(iv_c).sum()),
            "parity_gap_max_abs": float(np.abs(parity_gap).max()),
            "call_minus_put_implied_vol_max_abs_where_both_vega_ge_1e-3": float(np.abs(iv_c[both] - iv_p[both]).max()) if both.any() else None,
            "n_strikes_both_vega_ge_1e-3": int(both.sum()),
            "minimum": {"K_on_grid": float(strikes[i_min]), "implied_vol": float(iv_c[i_min])}}


def smile_features(mix, S0, r, T, solver, sigma_ref) -> dict:
    """Named points of the smile the page quotes: at the spot, at the forward, the wings, the symmetry
    sigma(K) = sigma(F^2/K), the slope at the forward in log-moneyness, the crossing of the rms vol."""
    F = S0 * exp(r * T)

    def iv(K_):
        res = implied_vol(float(mixture_price(K_, S0, r, T, mix, +1)), S0, float(K_), r, 0.0, T, +1, **solver)
        return res["sigma"] if res["status"] == "converged" else float("nan")

    pts = {f"K_{K_:g}": {"K": float(K_), "implied_vol": iv(K_), "mixture_price": float(mixture_price(K_, S0, r, T, mix, +1))} for K_ in (60.0, 80.0, 90.0, 100.0, 110.0, 120.0, 140.0, 160.0)}
    at_F = iv(F)
    # symmetry in log-moneyness about the forward
    sym = []
    for K_ in (70.0, 80.0, 90.0, 95.0):
        K_ref = F * F / K_
        sym.append({"K": K_, "K_reflected": K_ref, "implied_vol": iv(K_), "implied_vol_reflected": iv(K_ref), "gap": iv(K_) - iv(K_ref)})
    # slope at the forward in log-moneyness k = ln(K/F), central difference
    h = 0.01
    slope = (iv(F * exp(h)) - iv(F * exp(-h))) / (2 * h)
    # the minimum by a fine scan around the forward
    Ks = np.linspace(0.8 * F, 1.25 * F, 901)
    ivs = np.array([iv(K_) for K_ in Ks])
    i_min = int(np.nanargmin(ivs))
    # where the smile crosses the reference (rms) vol, on each side of the forward, by a fine scan 50-200
    Ks2 = np.linspace(50.0, 200.0, 1501)
    ivs2 = np.array([iv(K_) for K_ in Ks2])
    above = ivs2 > sigma_ref
    cross = []
    for i in range(1, len(Ks2)):
        if np.isfinite(ivs2[i - 1]) and np.isfinite(ivs2[i]) and above[i - 1] != above[i]:
            t_ = (sigma_ref - ivs2[i - 1]) / (ivs2[i] - ivs2[i - 1])
            cross.append(float(Ks2[i - 1] + t_ * (Ks2[i] - Ks2[i - 1])))
    return {"forward": F, "at_spot": pts["K_100"]["implied_vol"], "at_forward": at_F, "points": pts,
            "minimum_fine_scan": {"K": float(Ks[i_min]), "implied_vol": float(ivs[i_min]), "K_over_F": float(Ks[i_min] / F)},
            "symmetry_about_forward": sym, "slope_at_forward_per_unit_log_moneyness": slope,
            "crosses_reference_vol_at_K": cross, "reference_vol": sigma_ref}


def mixture_log_moments(mix, S0, r, T) -> dict:
    """Exact central moments of log S_T for a mixture of normals N(m_j, s_j^2), m_j = ln F_j - 1/2 sigma_j^2 T."""
    F = S0 * exp(r * T)
    ms = [log(F * f) - 0.5 * sg * sg * T for sg, f in zip(mix["sigmas"], mix["forward_factors"])]
    ss = [sg * sqrt(T) for sg in mix["sigmas"]]
    mean = sum(p * m for p, m in zip(mix["p"], ms))
    m2 = sum(p * ((m - mean) ** 2 + s * s) for p, m, s in zip(mix["p"], ms, ss))
    m3 = sum(p * ((m - mean) ** 3 + 3 * (m - mean) * s * s) for p, m, s in zip(mix["p"], ms, ss))
    m4 = sum(p * ((m - mean) ** 4 + 6 * (m - mean) ** 2 * s * s + 3 * s ** 4) for p, m, s in zip(mix["p"], ms, ss))
    var_S = sum(p * (F * f) ** 2 * exp(sg * sg * T) for p, sg, f in zip(mix["p"], mix["sigmas"], mix["forward_factors"])) - F * F
    return {"mean": mean, "variance": m2, "sd": sqrt(m2), "skewness": m3 / m2 ** 1.5, "excess_kurtosis": m4 / (m2 * m2) - 3.0,
            "sigma_fit": sqrt(m2 / T), "E_S_T": F, "sd_S_T": sqrt(var_S), "component_means": ms, "component_sds": ss}


def sample_moments(x: np.ndarray) -> dict:
    m = x.mean()
    c = x - m
    v = (c * c).mean()
    return {"mean": float(m), "variance": float(v), "sd": float(sqrt(v)), "skewness": float((c ** 3).mean() / v ** 1.5), "excess_kurtosis": float((c ** 4).mean() / (v * v) - 3.0), "n": int(x.size)}


def draw_mixture_terminal(rng, n, mix, S0, r, T) -> tuple[np.ndarray, np.ndarray]:
    """log S_T under the pricing measure: the state j with probability p_j, then N(m_j, sigma_j^2 T)."""
    F = S0 * exp(r * T)
    state = rng.choice(len(mix["p"]), size=n, p=mix["p"])
    sig = np.array(mix["sigmas"])[state]
    fwd = np.array(mix["forward_factors"])[state]
    Z = rng.standard_normal(n)
    logS = np.log(F * fwd) - 0.5 * sig * sig * T + sig * sqrt(T) * Z
    return logS, state


def kurtosis_study(rng, n_draws, n_batches, mix, S0, r, T, sigma_single) -> dict:
    """Excess kurtosis of log S_T: the mixture on n_draws draws (in batches, the batch sd giving the s.e.)
    against the exact mixture-of-normals value; a single lognormal at sigma_single as the control (0)."""
    exact = mixture_log_moments(mix, S0, r, T)
    per = max(1, n_draws // n_batches)
    k_mix, k_single, sk_mix, all_mix = [], [], [], []
    for _ in range(n_batches):
        logS, _ = draw_mixture_terminal(rng, per, mix, S0, r, T)
        mm = sample_moments(logS)
        k_mix.append(mm["excess_kurtosis"])
        sk_mix.append(mm["skewness"])
        all_mix.append(logS)
        Z = rng.standard_normal(per)
        k_single.append(sample_moments(log(S0) + (r - 0.5 * sigma_single ** 2) * T + sigma_single * sqrt(T) * Z)["excess_kurtosis"])
    all_mix = np.concatenate(all_mix)
    pooled = sample_moments(all_mix)
    sd3 = pooled["sd"]
    beyond3 = float((np.abs(all_mix - pooled["mean"]) > 3 * sd3).mean())
    beyond3_normal = 2.0 * (1.0 - float(Phi(3.0)))
    return {"n_draws": int(per * n_batches), "n_batches": n_batches,
            "mixture": {"excess_kurtosis_mean": float(np.mean(k_mix)), "excess_kurtosis_se": float(np.std(k_mix, ddof=1) / sqrt(n_batches)),
                        "skewness_mean": float(np.mean(sk_mix)), "skewness_se": float(np.std(sk_mix, ddof=1) / sqrt(n_batches)),
                        "exact_excess_kurtosis": exact["excess_kurtosis"], "exact_skewness": exact["skewness"], "pooled": pooled,
                        "fraction_beyond_3sd": beyond3},
            "lognormal": {"sigma": sigma_single, "excess_kurtosis_mean": float(np.mean(k_single)), "excess_kurtosis_se": float(np.std(k_single, ddof=1) / sqrt(n_batches)),
                          "exact_excess_kurtosis": 0.0, "fraction_beyond_3sd_exact": beyond3_normal},
            "exact_mixture_log_moments": exact}


# --- C3: 2.6's battery and daily returns on the mixture's paths -----------------------------------


def battery_2_6(logS, state, mix, S0, r, T) -> dict:
    """2.6's C1 checks, applied to the mixture's draws against two lognormals that share the vol sigma_fit.

    The log-moment rows and the median are tested against the lognormal fitted to the mixture's first two
    log moments. E[S_T] and the sd of S_T are tested against the lognormal with that vol and the forward F,
    which is what any model priced to no-arbitrage has. They are different lognormals: the log-moment fit's
    own E[S_T] is e^(mean + variance / 2), which is above F. Every row names its reference, and the two
    forward-matched rows also record what the log-moment fit itself would have given.
    """
    exact = mixture_log_moments(mix, S0, r, T)
    n = logS.size
    F = S0 * exp(r * T)
    sig_fit = exact["sigma_fit"]
    ret = logS - log(S0)
    mm = sample_moments(ret)
    S_T = np.exp(logS)
    se = {"mean": mm["sd"] / sqrt(n), "variance": mm["variance"] * sqrt(2.0 / n), "skewness": sqrt(6.0 / n), "kurtosis": sqrt(24.0 / n),
          "E_S_T": float(S_T.std(ddof=1)) / sqrt(n)}
    # median: s.e. by the asymptotic formula 1/(2 f(median) sqrt n) on the fitted lognormal's log density
    med = float(np.median(S_T))
    med_fit = S0 * exp((r - 0.5 * sig_fit ** 2) * T) * exp(exact["mean"] - (log(S0) + (r - 0.5 * sig_fit ** 2) * T))   # the fitted lognormal's median = e^(mean of log)
    med_fit = exp(exact["mean"])
    f_med = float(phi(0.0)) / (sqrt(exact["variance"]) * med_fit)
    se_med = 1.0 / (2.0 * f_med * sqrt(n))
    rows = []

    LOG_FIT, FORWARD_MATCHED, ANY_LOGNORMAL = "log-moment fit", "forward-matched lognormal, vol sigma_fit", "any lognormal"

    def row(name, measured, expected, se_, reference, tol_se=5.0):
        z = (measured - expected) / se_ if se_ > 0 else float("inf")
        rows.append({"check": name, "measured": float(measured), "expected": float(expected), "se": float(se_), "z": float(z), "pass_within_5se": bool(abs(z) <= tol_se),
                     "reference": reference})

    # what the log-moment fit itself has for the two rows that are tested against the forward-matched lognormal
    fit_E_S_T = exp(exact["mean"] + 0.5 * exact["variance"])
    fit_sd_S_T = fit_E_S_T * sqrt(exp(exact["variance"]) - 1.0)

    row("log-return mean is the mixture's exact log mean (the log-moment fit matches it by construction)", mm["mean"], exact["mean"] - log(S0), se["mean"], LOG_FIT)
    row("log-return variance is sigma_fit^2 T (matched by construction)", mm["variance"], sig_fit ** 2 * T, se["variance"], LOG_FIT)
    row("log-return skewness is 0 (the lognormal's)", mm["skewness"], 0.0, se["skewness"], ANY_LOGNORMAL)
    row("log-return excess kurtosis is 0 (the lognormal's) -- Gaussian", mm["excess_kurtosis"], 0.0, se["kurtosis"], ANY_LOGNORMAL)
    row("E[S_T] = S_0 e^(rT) = F (the forward -- the mixture's, and any lognormal's priced to the same forward)", float(S_T.mean()), F, se["E_S_T"], FORWARD_MATCHED)
    rows[-1].update({"log_moment_fit_expected": float(fit_E_S_T), "log_moment_fit_z": float((float(S_T.mean()) - fit_E_S_T) / se["E_S_T"])})
    row("median S_T = e^(E log S_T) (the lognormal's median)", med, med_fit, se_med, LOG_FIT)
    sd_fit = F * sqrt(exp(sig_fit ** 2 * T) - 1.0)
    sd_meas = float(S_T.std(ddof=1))
    rows.append({"check": "sd of S_T is F sqrt(e^(sigma_fit^2 T) - 1) (2.6's rule: to 3 %)", "measured": sd_meas, "expected": sd_fit, "relative_gap": sd_meas / sd_fit - 1.0,
                 "pass_to_3pct": bool(abs(sd_meas / sd_fit - 1.0) <= 0.03), "exact_mixture_sd_S_T": exact["sd_S_T"], "exact_relative_gap": exact["sd_S_T"] / sd_fit - 1.0,
                 "reference": FORWARD_MATCHED, "log_moment_fit_expected": float(fit_sd_S_T)})
    by_state = []
    for j, (sg, f) in enumerate(zip(mix["sigmas"], mix["forward_factors"])):
        sel = state == j
        mj = sample_moments(ret[sel])
        by_state.append({"state": j, "sigma": sg, "n": int(sel.sum()), "excess_kurtosis": mj["excess_kurtosis"], "se_kurtosis": sqrt(24.0 / sel.sum()),
                         "skewness": mj["skewness"], "sd_over_sqrtT": mj["sd"] / sqrt(T), "gaussian_within_5se": bool(abs(mj["excess_kurtosis"]) <= 5 * sqrt(24.0 / sel.sum()))})
    return {"n": int(n), "sigma_fit": sig_fit, "rows": rows, "n_pass": int(sum(1 for r_ in rows if r_.get("pass_within_5se", r_.get("pass_to_3pct")))),
            "n_fail": int(sum(1 for r_ in rows if not r_.get("pass_within_5se", r_.get("pass_to_3pct")))), "by_state": by_state}


def daily_returns_study(rng, n_paths, steps, mix, S0, r, T) -> dict:
    """Daily log-returns along mixture paths (the state fixed per path): pooled and within each state."""
    dt = T / steps
    state = rng.choice(len(mix["p"]), size=n_paths, p=mix["p"])
    sig = np.array(mix["sigmas"])[state][:, None]
    fwd = np.array(mix["forward_factors"])[state]
    drift = (r + np.log(fwd) / T)[:, None]                     # the component's forward: F_j = f_j F
    Z = rng.standard_normal((n_paths, steps))
    inc = (drift - 0.5 * sig * sig) * dt + sig * sqrt(dt) * Z
    pooled = inc.ravel()
    mm = sample_moments(pooled)
    beyond3 = float((np.abs(pooled - mm["mean"]) > 3 * mm["sd"]).mean())
    normal3 = 2.0 * (1.0 - float(Phi(3.0)))
    # exact pooled excess kurtosis of a scale mixture of normals with (nearly) equal means, 3 E[sigma^4]/E[sigma^2]^2 - 3:
    # at the nominal p, and conditional on the states actually drawn (the state is per path, so 20,000 paths is the
    # sample size for p-hat, not 5 million returns -- the conditional value is the fair comparison)
    sig2 = np.array(mix["sigmas"]) ** 2
    E2 = float(sum(p * s2 for p, s2 in zip(mix["p"], sig2)))
    E4 = float(sum(p * s2 * s2 for p, s2 in zip(mix["p"], sig2)))
    p_hat = np.array([(state == j).mean() for j in range(len(mix["p"]))])
    E2_hat, E4_hat = float((p_hat * sig2).sum()), float((p_hat * sig2 * sig2).sum())
    # s.e. of the pooled kurtosis from batches of paths, each compared with the exact value at its own p-hat
    n_batches = 10
    diffs = []
    for b in np.array_split(np.arange(n_paths), n_batches):
        xb = inc[b].ravel()
        kb = sample_moments(xb)["excess_kurtosis"]
        pb = np.array([(state[b] == j).mean() for j in range(len(mix["p"]))])
        diffs.append(kb - (3.0 * float((pb * sig2 * sig2).sum()) / float((pb * sig2).sum()) ** 2 - 3.0))
    by_state = []
    for j, sg in enumerate(mix["sigmas"]):
        x = inc[state == j].ravel()
        mj = sample_moments(x)
        by_state.append({"state": j, "sigma": sg, "n_returns": int(x.size), "annualised_sd": mj["sd"] / sqrt(dt), "excess_kurtosis": mj["excess_kurtosis"],
                         "se_kurtosis": sqrt(24.0 / x.size), "fraction_beyond_3sd": float((np.abs(x - mj["mean"]) > 3 * mj["sd"]).mean())})
    # per-path realised volatility (2.7's statistic): bimodal
    rv = inc.std(axis=1, ddof=1) / sqrt(dt)
    return {"n_paths": n_paths, "steps": steps, "state_counts": [int((state == j).sum()) for j in range(len(mix["p"]))], "p_hat": p_hat.tolist(),
            "pooled": {**mm, "annualised_sd": mm["sd"] / sqrt(dt), "fraction_beyond_3sd": beyond3, "fraction_beyond_3sd_normal": normal3,
                       "ratio_to_normal": beyond3 / normal3, "se_kurtosis_if_iid_normal": sqrt(24.0 / pooled.size),
                       "exact_excess_kurtosis_scale_mixture": 3.0 * E4 / (E2 * E2) - 3.0, "exact_excess_kurtosis_at_p_hat": 3.0 * E4_hat / (E2_hat * E2_hat) - 3.0,
                       "kurtosis_minus_exact_at_p_hat_batches": {"mean": float(np.mean(diffs)), "se": float(np.std(diffs, ddof=1) / sqrt(n_batches)), "n_batches": n_batches},
                       "rms_vol_at_p_hat": sqrt(E2_hat)},
            "by_state": by_state,
            "realised_vol_per_path": {"mean_by_state": [float(rv[state == j].mean()) for j in range(len(mix["p"]))], "sd_by_state": [float(rv[state == j].std(ddof=1)) for j in range(len(mix["p"]))],
                                      "overall_mean": float(rv.mean()), "overall_sd": float(rv.std(ddof=1)), "rms_vol": sqrt(E2),
                                      "histogram": {"edges": np.linspace(0.1, 0.8, 36).tolist(), "counts": np.histogram(rv, bins=np.linspace(0.1, 0.8, 36))[0].tolist()}}}


# --- C4 / C5: the hedge as a bank account, with costs ------------------------------------------


def hedge_book(S, T, K, r, sigma_h, P0, k) -> dict[str, np.ndarray]:
    """Buy the call at P0 (the first column of S is S_0), short Delta shares, cash at r, rebalance at
    every grid time with Black-Scholes deltas at sigma_h (scalar, or one per path), liquidate at T.

    Per path, discounted to 0: pnl_gross (no fee), cost_setup, cost_rebalance, cost_unwind (each
    the fee k x |shares traded| x price, discounted), pnl_net = pnl_gross - the three costs,
    turnover (Sum |dDelta| S, undiscounted), and telescoped -- 2.7's Sum e^(-rt)[dV - Delta dS -
    carry_exact] with V the Black-Scholes value at sigma_h and V_0 replaced by P0 -- which equals
    pnl_gross exactly (the bookkeeping identity).
    """
    m, Np1 = S.shape
    N = Np1 - 1
    dt = T / N
    growth = exp(r * dt)
    S0 = S[:, 0]
    sig = np.broadcast_to(np.asarray(sigma_h, dtype=float), (m,))
    d = delta(S0, K, r, 0.0, sig, T)
    V = price(S0, K, r, 0.0, sig, T)
    B = -P0 + d * S0                                   # cash after buying the option and shorting Delta shares
    cost_setup = k * np.abs(d) * S0
    cost_rebal = np.zeros(m)
    turnover = np.abs(d) * S0
    telescoped = np.zeros(m)
    Vprev, dprev, Sprev = V, d, S0
    for i in range(N):
        t_next = (i + 1) * dt
        tau_next = T - t_next
        S1 = S[:, i + 1]
        df = exp(-r * t_next)
        B = B * growth
        if i + 1 < N:
            d1 = delta(S1, K, r, 0.0, sig, tau_next)
            V1 = price(S1, K, r, 0.0, sig, tau_next)
            trade = (d1 - dprev) * S1
            B = B + trade
            cost_rebal += df * k * np.abs(trade)
            turnover += np.abs(trade)
        else:
            d1 = dprev
            V1 = np.maximum(S1 - K, 0.0)
        telescoped += df * ((V1 - Vprev) - dprev * (S1 - Sprev) - (Vprev - dprev * Sprev) * (growth - 1.0))
        Vprev, dprev, Sprev = V1, d1, S1
    S_T = S[:, N]
    wealth = np.maximum(S_T - K, 0.0) - dprev * S_T + B
    pnl_gross = exp(-r * T) * wealth
    cost_unwind = exp(-r * T) * k * np.abs(dprev) * S_T
    telescoped += (V - P0)                              # 2.7's V_0 is the model price; the book paid P0
    return {"pnl_gross": pnl_gross, "pnl_net": pnl_gross - cost_setup - cost_rebal - cost_unwind,
            "cost_setup": cost_setup, "cost_rebalance": cost_rebal, "cost_unwind": cost_unwind, "turnover": turnover,
            "telescoped_minus_bank": telescoped - pnl_gross, "V0_model": V}


def stats(x: np.ndarray) -> dict[str, float]:
    if x.size < 2:
        return {"mean": float(x.mean()) if x.size else float("nan"), "sd": float("nan"), "se_of_mean": float("nan"), "n": int(x.size)}
    sd = float(x.std(ddof=1))
    return {"mean": float(x.mean()), "sd": sd, "se_of_mean": sd / sqrt(x.size), "rms": float(sqrt((x * x).mean())), "max_abs": float(np.abs(x).max()), "n": int(x.size)}


def hedging_scenarios(rng, H, T, S0, K, r, mix, sigma_control, sigma_imp, P_mix, k) -> dict:
    """Three books on two path sets. Control: GBM at sigma_control (mu = r), hedged at sigma_control,
    bought at C(sigma_control). Mixture: the state per path, GBM at sigma_j with the component drift
    (mu = r + ln f_j / T, so the discounted stock is a martingale), hedged (a) at sigma_imp, bought
    at P_mix; (b) the oracle, at the path's own sigma_j, bought at P_mix. Every N read off one fine grid."""
    n_paths, n_fine, Ns, chunk = H["n_paths"], H["n_fine"], H["Ns"], H["chunk_paths"]
    dt_f = T / n_fine
    keys = ("pnl_gross", "pnl_net", "cost_setup", "cost_rebalance", "cost_unwind", "turnover", "telescoped_minus_bank")
    books = {"control": {N: {kk: [] for kk in keys} for N in Ns}, "mixture_bs_hedge": {N: {kk: [] for kk in keys} for N in Ns}, "mixture_oracle_hedge": {N: {kk: [] for kk in keys} for N in Ns}}
    states, realised_ctrl, realised_mix = [], [], []
    C_single = float(price(S0, K, r, 0.0, sigma_control, T))
    sig_arr, fwd_arr = np.array(mix["sigmas"]), np.array(mix["forward_factors"])
    for start in range(0, n_paths, chunk):
        m = min(chunk, n_paths - start)
        # control paths
        Z = rng.standard_normal((m, n_fine))
        logS = np.empty((m, n_fine + 1))
        logS[:, 0] = log(S0)
        np.cumsum((r - 0.5 * sigma_control ** 2) * dt_f + sigma_control * sqrt(dt_f) * Z, axis=1, out=logS[:, 1:])
        logS[:, 1:] += log(S0)
        realised_ctrl.append(np.diff(logS, axis=1).std(axis=1, ddof=1) * sqrt(n_fine / T))
        S_fine = np.exp(logS)
        for N in Ns:
            S = S_fine[:, :: n_fine // N].copy()
            h = hedge_book(S, T, K, r, sigma_control, C_single, k)
            for kk in keys:
                books["control"][N][kk].append(h[kk])
        # mixture paths: the state drawn per path, fixed along it
        state = rng.choice(len(mix["p"]), size=m, p=mix["p"])
        sg = sig_arr[state][:, None]
        drift = (r + np.log(fwd_arr[state]) / T)[:, None]
        Z = rng.standard_normal((m, n_fine))
        np.cumsum((drift - 0.5 * sg * sg) * dt_f + sg * sqrt(dt_f) * Z, axis=1, out=logS[:, 1:])
        logS[:, 1:] += log(S0)
        realised_mix.append(np.diff(logS, axis=1).std(axis=1, ddof=1) * sqrt(n_fine / T))
        states.append(state)
        S_fine = np.exp(logS)
        for N in Ns:
            S = S_fine[:, :: n_fine // N].copy()
            h = hedge_book(S, T, K, r, sigma_imp, P_mix, k)
            for kk in keys:
                books["mixture_bs_hedge"][N][kk].append(h[kk])
            h = hedge_book(S, T, K, r, sig_arr[state], P_mix, k)
            for kk in keys:
                books["mixture_oracle_hedge"][N][kk].append(h[kk])
    state = np.concatenate(states)
    realised_ctrl, realised_mix = np.concatenate(realised_ctrl), np.concatenate(realised_mix)
    C_j = [float(price(f * S0, K, r, 0.0, s_, T)) for s_, f in zip(mix["sigmas"], mix["forward_factors"])]
    between_state_sd = float(sqrt(sum(p * (c - P_mix) ** 2 for p, c in zip(mix["p"], C_j))))
    out = {"n_paths": n_paths, "n_fine": n_fine, "Ns": Ns, "fee_k": k, "mu": "r (the pricing drift; component drifts r + ln f_j / T)",
           "control": {"sigma": sigma_control, "price_paid": C_single, "realised_vol": {"mean": float(realised_ctrl.mean()), "sd": float(realised_ctrl.std(ddof=1))}, "per_N": []},
           "mixture_bs_hedge": {"sigma_hedge": sigma_imp, "price_paid": P_mix, "per_N": []},
           "mixture_oracle_hedge": {"sigma_hedge": "the path's own sigma_j", "price_paid": P_mix, "per_N": []},
           "mixture_paths": {"state_counts": [int((state == j).sum()) for j in range(len(mix["p"]))], "p": mix["p"],
                             "realised_vol_by_state": [{"state": j, "sigma": mix["sigmas"][j], "mean": float(realised_mix[state == j].mean()), "sd": float(realised_mix[state == j].std(ddof=1))} for j in range(len(mix["p"]))],
                             "component_prices_C_j": C_j, "price_paid_P_mix": P_mix, "expected_pnl_by_state_C_j_minus_P_mix": [c - P_mix for c in C_j],
                             "between_state_sd": between_state_sd}}
    for name in ("control", "mixture_bs_hedge", "mixture_oracle_hedge"):
        for N in Ns:
            c = {kk: np.concatenate(v) for kk, v in books[name][N].items()}
            cost_total = c["cost_setup"] + c["cost_rebalance"] + c["cost_unwind"]
            row = {"N": N, "dt": T / N,
                   "pnl_gross": stats(c["pnl_gross"]), "pnl_net": stats(c["pnl_net"]),
                   "sd_times_sqrtN": float(c["pnl_gross"].std(ddof=1)) * sqrt(N),
                   "cost_rebalance": stats(c["cost_rebalance"]), "cost_setup": stats(c["cost_setup"]), "cost_unwind": stats(c["cost_unwind"]), "cost_total": stats(cost_total),
                   "cost_rebalance_mean_over_sqrtN": float(c["cost_rebalance"].mean()) / sqrt(N),
                   "turnover": stats(c["turnover"]),
                   "spread_plus_cost": float(c["pnl_gross"].std(ddof=1)) + float(cost_total.mean()),
                   "bookkeeping_identity_max_abs": float(np.abs(c["telescoped_minus_bank"]).max())}
            if name != "control":
                row["by_state"] = [{"state": j, "sigma": mix["sigmas"][j], "pnl_gross": stats(c["pnl_gross"][state == j]), "pnl_net": stats(c["pnl_net"][state == j]),
                                    "expected_mean": C_j[j] - P_mix, "cost_rebalance": stats(c["cost_rebalance"][state == j])} for j in range(len(mix["p"]))]
                within = sum(mix["p"][j] * float(c["pnl_gross"][state == j].var(ddof=1)) for j in range(len(mix["p"])))
                row["within_state_sd"] = float(sqrt(within))
                row["between_state_sd_from_means"] = float(sqrt(sum(mix["p"][j] * (float(c["pnl_gross"][state == j].mean()) - float(c["pnl_gross"].mean())) ** 2 for j in range(len(mix["p"])))))
            out[name]["per_N"].append(row)
    # log-log slopes over N >= 64
    for name in ("control", "mixture_bs_hedge", "mixture_oracle_hedge"):
        rows = [r_ for r_ in out[name]["per_N"] if r_["N"] >= 64]
        lN = np.log([r_["N"] for r_ in rows])
        out[name]["slopes_over_N_ge_64"] = {"sd_gross": float(np.polyfit(lN, np.log([r_["pnl_gross"]["sd"] for r_ in rows]), 1)[0]),
                                            "cost_rebalance_mean": float(np.polyfit(lN, np.log([r_["cost_rebalance"]["mean"] for r_ in rows]), 1)[0])}
        if name != "control":
            out[name]["slopes_over_N_ge_64"]["within_state_sd"] = float(np.polyfit(lN, np.log([r_["within_state_sd"] for r_ in rows]), 1)[0])
    ctrl = out["control"]["per_N"]
    i_best = int(np.argmin([r_["spread_plus_cost"] for r_ in ctrl]))
    out["control"]["trade_off"] = {"N_minimising_spread_plus_cost_on_grid": ctrl[i_best]["N"], "rows": [{"N": r_["N"], "spread_sd": r_["pnl_gross"]["sd"], "cost_mean": r_["cost_total"]["mean"],
                                                                                                        "cost_rebalance_mean": r_["cost_rebalance"]["mean"], "sum": r_["spread_plus_cost"]} for r_ in ctrl],
                                   "cost_ratio_N_to_4N": [{"N": a["N"], "N4": b["N"], "ratio": b["cost_rebalance"]["mean"] / a["cost_rebalance"]["mean"]} for a, b in zip(ctrl, ctrl[1:])]}
    return out


# --- checks -----------------------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected), "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    def truth(claim, ok):
        checks.append({"claim": claim, "measured": float(bool(ok)), "expected": 1.0, "tolerance": 0.0, "mode": "abs", "pass": bool(ok)})

    def within_se(claim, block, target, k=5.0):
        add(claim + " (within 5 s.e.)", block["mean"], target, k * block["se_of_mean"])

    S0, K, r, T, sigma = params["S0"], params["K"], params["r"], params["T"], params["sigma"]
    add("Phi: Hart/West normal CDF agrees with math.erf on [-9, 9] (max abs diff < 1e-13)", res["phi_max_abs_error"], 0.0, 1e-13)

    # C1 -- the solver
    B = res["solver"]["base_case"]
    add("C1 base case: the implied vol of C = 18.0230 is sigma = 0.40 (1e-12)", B["sigma"], sigma, 1e-12)
    truth(f"C1 base case: converged from sigma_0 = 0.2 in at most 8 iterations ({B['iterations']})", B["status"] == "converged" and B["iterations"] <= 8)
    truth("C1 base case: no bisection step was needed (Newton alone)", B["bisections"] == 0)
    tr = [abs(t_["price_error"]) for t_ in B["trace"]]
    truth("C1 base case: Newton's quadratic tail -- each price error from the second iteration on is below the square of the previous relative error x 10",
          all(tr[i + 1] <= 10.0 * (tr[i] / 18.0) ** 2 * 18.0 for i in range(1, len(tr) - 1)) if len(tr) > 2 else True)
    bd = res["solver"]["bounds_base_case"]
    add("C1 the lower bound at the base case is S_0 - K e^(-rT) = 4.877 (sigma -> 0)", bd["lower_bound"], S0 - K * exp(-r * T), 1e-12)
    add("C1 the upper bound at the base case is S_0 = 100 (sigma -> infinity)", bd["upper_bound"], S0, 1e-12)
    add("C1 the price at sigma = 1e-6 sits on the lower bound (1e-6)", bd["price_at_sigma_lo"], bd["lower_bound"], 1e-6)
    truth("C1 the price at sigma = 5 is below the upper bound: the search interval does not reach the bound", bd["price_at_sigma_hi"] < bd["upper_bound"])
    truth("C1 a price below the lower bound (4.0) is refused: status below_lower_bound, sigma NaN", bd["refusals"]["price_4.0"]["status"] == "below_lower_bound" and not np.isfinite(bd["refusals"]["price_4.0"]["sigma"]))
    truth("C1 a price above the upper bound (101) is refused: status above_upper_bound, sigma NaN", bd["refusals"]["price_101.0"]["status"] == "above_upper_bound" and not np.isfinite(bd["refusals"]["price_101.0"]["sigma"]))
    truth("C1 a price inside the bounds but above the sigma = 5 cap (99.5) reports above_sigma_hi", bd["refusals"]["price_99.5"]["status"] == "above_sigma_hi")
    G = res["solver"]["grid_round_trip"]
    add(f"C1 round trip on the {G['n_points']}-point grid, calls: max |recovered - sigma| (1e-10)", G["max_abs_sigma_error_call"], 0.0, 1e-10)
    add(f"C1 round trip on the {G['n_points']}-point grid, puts: max |recovered - sigma| (1e-10)", G["max_abs_sigma_error_put"], 0.0, 1e-10)
    truth(f"C1 round trip on the grid: every solve converged (statuses {G['statuses']})", set(G["statuses"]) == {"converged"})
    truth(f"C1 round trip on the grid: at most 12 iterations on any point (max {G['iterations']['max']})", G["iterations"]["max"] <= 12)
    O = res["solver"]["oracle"]
    if O["live"] is not None:
        add(f"C1 QuantLib {O['live']['version']} blackFormulaImpliedStdDev at the grid, call and put: max |ours - theirs| (1e-9)", O["live"]["max_abs_sigma_error"], 0.0, 1e-9)
    elif not params["quick"]:
        truth("C1 QuantLib-Python present for the live oracle comparison (I4) -- required for the full run", False)
    if O["golden"] is not None:
        g = O["golden"]
        for blk_name in ("cases", "edge_cases"):
            blk = g[blk_name]
            ident, vl, ni = blk["identifiable"], blk["vega_limited"], blk["not_identifiable"]
            add(f"C1 golden {blk_name} ({blk['n']} rows, QuantLib {g['oracle']['version']}): the {ident['n']} rows with vega >= 1 recover their vol to 1e-10", ident["max_abs_sigma_error"], 0.0, 1e-10)
            add(f"C1 golden {blk_name}: those rows' prices reproduced to 1e-12 (relative above 1)", ident["max_abs_price_error_rel"], 0.0, 1e-12)
            if vl["n"]:
                truth(f"C1 golden {blk_name}: the {vl['n']} rows with 1e-8 <= vega < 1 recover their vol within 10x the bound price_tol x max(1, price) / vega (worst ratio {vl['max_ratio_sigma_error_to_bound']:.2f})", vl["max_ratio_sigma_error_to_bound"] <= 10.0)
                add(f"C1 golden {blk_name}: those rows' prices reproduced to 1e-12 (relative above 1)", vl["max_abs_price_error_rel"], 0.0, 1e-12)
            if ni["n"]:
                add(f"C1 golden {blk_name}: the {ni['n']} rows with vega < 1e-8 still reproduce their price to 1e-12 (relative above 1) -- the vol is not identifiable, the price is",
                    ni["max_abs_price_error_rel"], 0.0, 1e-12)
            truth(f"C1 golden {blk_name}: every row's price lies inside the no-arbitrage bounds to 1e-12 ({blk['n_inside_bounds']} of {blk['n']}; {blk['n_on_lower_bound']} sit on the lower bound -- no time value at double precision)", blk["n_inside_bounds"] == blk["n"])
            truth(f"C1 golden {blk_name}: every solve converged (statuses {blk['statuses']})", set(blk["statuses"]) == {"converged"})
        truth("C1 the golden file records its QuantLib version (I4)", bool(g["oracle"].get("version")))
    elif not params["quick"]:
        truth("C1 golden/bs_vanilla.json present for the committed-oracle comparison (I4) -- required for the full run", False)

    # C2 -- the mixture market
    M = res["market"]
    sym = M["symmetric"]
    sf = sym["features"]
    rms = M["symmetric"]["rms_vol"]
    add("C2 symmetric mixture: parity C - P = S_0 - K e^(-rT) holds at every strike (1e-12)", sym["smile_T1"]["parity_gap_max_abs"], 0.0, 1e-12)
    add("C2 symmetric mixture: the put's implied vol equals the call's where both vegas >= 1e-3 (1e-9)", sym["smile_T1"]["call_minus_put_implied_vol_max_abs_where_both_vega_ge_1e-3"], 0.0, 1e-9)
    truth(f"C2 symmetric mixture: every strike 60-160 has an implied vol ({sym['smile_T1']['n_strikes_with_vol']} of {len(sym['smile_T1']['strikes'])})", sym["smile_T1"]["n_strikes_with_vol"] == len(sym["smile_T1"]["strikes"]))
    truth("C2 symmetric mixture: a smile -- the implied vol at K = 60 and at K = 160 both exceed the vol at the forward", sf["points"]["K_60"]["implied_vol"] > sf["at_forward"] and sf["points"]["K_160"]["implied_vol"] > sf["at_forward"])
    truth("C2 symmetric mixture: the wings exceed the rms vol 0.447, the forward sits below it", sf["points"]["K_60"]["implied_vol"] > rms and sf["points"]["K_160"]["implied_vol"] > rms and sf["at_forward"] < rms)
    truth("C2 symmetric mixture: the wings stay below sigma_high = 0.6 on 60-160", sf["points"]["K_60"]["implied_vol"] < 0.6 and sf["points"]["K_160"]["implied_vol"] < 0.6)
    add("C2 symmetric mixture: the smile's minimum is at the forward F = 105.13, not the spot (within 0.5)", sf["minimum_fine_scan"]["K"], sf["forward"], 0.5)
    add("C2 symmetric mixture: the slope at the forward in log-moneyness is zero (1e-3)", sf["slope_at_forward_per_unit_log_moneyness"], 0.0, 1e-3)
    truth("C2 symmetric mixture: the smile is symmetric in log-moneyness, sigma(K) = sigma(F^2/K) (1e-9 at four pairs)", all(abs(s_["gap"]) < 1e-9 for s_ in sf["symmetry_about_forward"]))
    truth("C2 symmetric mixture: the implied vol at the forward is below the mean vol 0.40 and the mean vol below the rms 0.447", sf["at_forward"] < 0.40 < rms)
    add("C2 symmetric mixture at the money (K = 100): the mixture price 17.99 is below C(0.40) = 18.02 by less than 0.05 -- the price is almost linear in sigma there", M["symmetric"]["atm"]["mixture_price"], M["symmetric"]["atm"]["price_at_mean_vol"], 0.05)
    truth("C2 symmetric mixture at the money: mixture price < C(mean vol) < C(rms vol) -- the Jensen gap", M["symmetric"]["atm"]["mixture_price"] < M["symmetric"]["atm"]["price_at_mean_vol"] < M["symmetric"]["atm"]["price_at_rms_vol"])
    truth("C2 symmetric mixture at the money: the implied vol lies in (0.39, 0.40)", 0.39 < M["symmetric"]["atm"]["implied_vol"] < 0.40)
    truth("C2 symmetric mixture: the smile crosses the rms vol once on each side of the forward", len(sf["crosses_reference_vol_at_K"]) == 2 and sf["crosses_reference_vol_at_K"][0] < sf["forward"] < sf["crosses_reference_vol_at_K"][1])
    sk = M["skewed"]
    kf = sk["features"]
    add("C2 skewed mixture: parity holds at every strike (1e-12)", sk["smile_T1"]["parity_gap_max_abs"], 0.0, 1e-12)
    truth("C2 skewed mixture: skew -- the implied vol at K = 80 exceeds the vol at K = 120", kf["points"]["K_80"]["implied_vol"] > kf["points"]["K_120"]["implied_vol"])
    truth("C2 skewed mixture: the slope at the forward in log-moneyness is negative", kf["slope_at_forward_per_unit_log_moneyness"] < 0)
    truth("C2 skewed mixture: not symmetric -- sigma(K) != sigma(F^2/K) by more than 0.005 at K = 80", abs([s_ for s_ in kf["symmetry_about_forward"] if s_["K"] == 80.0][0]["gap"]) > 0.005)
    truth("C2 skewed mixture: still not flat -- the implied vol varies by more than 0.05 across 60-160", max(v for v in sk["smile_T1"]["implied_vol_call"] if v is not None) - min(v for v in sk["smile_T1"]["implied_vol_call"] if v is not None) > 0.05)
    Ku = res["market"]["kurtosis"]
    add("C2 the mixture's log S_T excess kurtosis on 10^6 draws matches the mixture-of-normals closed form (within 5 s.e.)", Ku["mixture"]["excess_kurtosis_mean"], Ku["mixture"]["exact_excess_kurtosis"], 5 * Ku["mixture"]["excess_kurtosis_se"])
    truth("C2 the mixture's excess kurtosis exceeds 1.5 (the lognormal's is 0)", Ku["mixture"]["excess_kurtosis_mean"] > 1.5)
    add("C2 the single lognormal's log S_T excess kurtosis is 0 (within 5 s.e.)", Ku["lognormal"]["excess_kurtosis_mean"], 0.0, 5 * Ku["lognormal"]["excess_kurtosis_se"])
    truth("C2 the mixture puts more than twice the normal's 0.27 % beyond 3 sd", Ku["mixture"]["fraction_beyond_3sd"] > 2 * Ku["lognormal"]["fraction_beyond_3sd_exact"])

    # C3 -- 2.6's battery and daily returns
    Bt = res["returns"]["battery_2_6"]
    rows = {r_["check"][:30]: r_ for r_ in Bt["rows"]}
    truth("C3 2.6's battery on the mixture: the log-return mean passes (matched by construction)", Bt["rows"][0]["pass_within_5se"])
    truth("C3 2.6's battery on the mixture: the log-return variance passes (matched by construction)", Bt["rows"][1]["pass_within_5se"])
    truth("C3 2.6's battery on the mixture: E[S_T] = F passes (the forward is the mixture's, and any lognormal's priced to the same forward)", Bt["rows"][4]["pass_within_5se"])
    truth(f"C3 2.6's battery on the mixture: the excess-kurtosis check FAILS, by more than 50 s.e. (z = {Bt['rows'][3]['z']:.0f})", not Bt["rows"][3]["pass_within_5se"] and abs(Bt["rows"][3]["z"]) > 50)
    truth("C3 2.6's battery on the mixture: each vol state alone is Gaussian (excess kurtosis 0 within 5 s.e.) -- the fat tails are the mixing", all(b_["gaussian_within_5se"] for b_ in Bt["by_state"]))
    D = res["returns"]["daily"]
    kb = D["pooled"]["kurtosis_minus_exact_at_p_hat_batches"]
    add("C3 daily returns, pooled: excess kurtosis matches the scale-mixture closed form 3 E[sigma^4]/E[sigma^2]^2 - 3 at the realised state fractions (batch mean of the gap within 5 s.e.)", kb["mean"], 0.0, 5 * kb["se"])
    truth(f"C3 daily returns, pooled: excess kurtosis above 1.5 ({D['pooled']['excess_kurtosis']:.2f}; a Gaussian's is 0)", D["pooled"]["excess_kurtosis"] > 1.5)
    truth(f"C3 daily returns, pooled: more than twice the normal's 0.27 % beyond 3 sd ({100 * D['pooled']['fraction_beyond_3sd']:.2f} %)", D["pooled"]["ratio_to_normal"] > 2.0)
    truth("C3 daily returns within each state: Gaussian (excess kurtosis 0 within 5 s.e.)", all(abs(b_["excess_kurtosis"]) <= 5 * b_["se_kurtosis"] for b_ in D["by_state"]))
    for b_ in D["by_state"]:
        add(f"C3 daily returns, state sigma = {b_['sigma']}: annualised sd is sigma (to 1 %)", b_["annualised_sd"], b_["sigma"], 0.01, "rel")
    add("C3 the pooled annualised sd of daily returns is the rms vol at the realised state fractions (to 0.5 %)", D["pooled"]["annualised_sd"], D["pooled"]["rms_vol_at_p_hat"], 0.005, "rel")
    truth("C3 per-path realised vol is bimodal: the two state means 2 sd apart, neither near the rms", all(abs(m_ - D["realised_vol_per_path"]["rms_vol"]) > 2 * s_ for m_, s_ in zip(D["realised_vol_per_path"]["mean_by_state"], D["realised_vol_per_path"]["sd_by_state"])))

    # C4 -- the hedge under the wrong model
    Hd = res["hedging"]
    c27 = params["cited_from_2_7"]
    ctrl = {p_["N"]: p_ for p_ in Hd["control"]["per_N"]}
    bs = {p_["N"]: p_ for p_ in Hd["mixture_bs_hedge"]["per_N"]}
    orc = {p_["N"]: p_ for p_ in Hd["mixture_oracle_hedge"]["per_N"]}
    Ns = Hd["Ns"]
    N_max = Ns[-1]
    for name, bk in (("control", ctrl), ("mixture, BS hedge", bs), ("mixture, oracle hedge", orc)):
        for N in Ns:
            add(f"C4 {name}, N = {N}: the bank-account P&L equals 2.7's telescoped formula per path (1e-9)", bk[N]["bookkeeping_identity_max_abs"], 0.0, 1e-9)
    add("C4 control: the realised vol of the paths is 0.40 (within 5 s.e.)", Hd["control"]["realised_vol"]["mean"], sigma, 5 * Hd["control"]["realised_vol"]["sd"] / sqrt(Hd["n_paths"]))
    for N in Ns:
        within_se(f"C4 control, N = {N}: mean hedged P&L is zero under the pricing drift", ctrl[N]["pnl_gross"], 0.0)
        within_se(f"C4 mixture BS hedge, N = {N}: mean hedged P&L is zero -- the price is the Q-expectation, whatever the hedge (2.8)", bs[N]["pnl_gross"], 0.0)
        within_se(f"C4 mixture oracle hedge, N = {N}: mean hedged P&L is zero", orc[N]["pnl_gross"], 0.0)
        for j, st_ in enumerate(bs[N]["by_state"]):
            within_se(f"C4 mixture BS hedge, N = {N}, state sigma = {st_['sigma']}: the mean P&L is C(sigma_j) - C_mix = {st_['expected_mean']:+.2f}", st_["pnl_gross"], st_["expected_mean"])
        for j, st_ in enumerate(orc[N]["by_state"]):
            within_se(f"C4 mixture oracle hedge, N = {N}, state sigma = {st_['sigma']}: the mean P&L is C(sigma_j) - C_mix = {st_['expected_mean']:+.2f}", st_["pnl_gross"], st_["expected_mean"])
    add(f"C4 control: sd sqrt N at N = {N_max} is 2.7's {c27['sd_sqrtN_4096']:.2f} (to 15 %; seed and drift differ)", ctrl[N_max]["sd_times_sqrtN"], c27["sd_sqrtN_4096"], 0.15, "rel")
    add("C4 control: the log-log slope of the spread against N over N >= 64 is -1/2 (within 0.06)", Hd["control"]["slopes_over_N_ge_64"]["sd_gross"], -0.5, 0.06)
    truth(f"C4 control: the spread falls at every step of N ({' > '.join(f'{ctrl[N]['pnl_gross']['sd']:.2f}' for N in Ns)})", all(ctrl[a]["pnl_gross"]["sd"] > ctrl[b]["pnl_gross"]["sd"] for a, b in zip(Ns, Ns[1:])))
    truth(f"C4 mixture BS hedge: the spread does NOT fall to zero -- sd at N = {N_max} exceeds 0.9 x sd at N = {Ns[-2]} ({bs[N_max]['pnl_gross']['sd']:.2f} vs {bs[Ns[-2]]['pnl_gross']['sd']:.2f})", bs[N_max]["pnl_gross"]["sd"] > 0.9 * bs[Ns[-2]]["pnl_gross"]["sd"])
    fac = 20.0 if N_max >= 4096 else 5.0
    truth(f"C4 mixture BS hedge: at N = {N_max} the spread is more than {fac:.0f}x the control's ({bs[N_max]['pnl_gross']['sd']:.2f} vs {ctrl[N_max]['pnl_gross']['sd']:.3f})", bs[N_max]["pnl_gross"]["sd"] > fac * ctrl[N_max]["pnl_gross"]["sd"])
    add("C4 mixture BS hedge: the log-log slope of the spread over N >= 64 is above -0.1 (a floor, not 1/sqrt N)", Hd["mixture_bs_hedge"]["slopes_over_N_ge_64"]["sd_gross"], 0.0, 0.1)
    truth(f"C4 mixture BS hedge: the within-state spread also plateaus -- at N = {N_max} it exceeds 0.8 x its value at N = {Ns[-2]} ({bs[N_max]['within_state_sd']:.2f} vs {bs[Ns[-2]]['within_state_sd']:.2f})", bs[N_max]["within_state_sd"] > 0.8 * bs[Ns[-2]]["within_state_sd"])
    add(f"C4 mixture oracle hedge: the within-state spread falls like 1/sqrt N -- log-log slope over N >= 64 is -1/2 (within 0.08)", Hd["mixture_oracle_hedge"]["slopes_over_N_ge_64"]["within_state_sd"], -0.5, 0.08)
    frac = 0.25 if N_max >= 4096 else 0.5
    truth(f"C4 mixture oracle hedge: the within-state spread at N = {N_max} is below {frac:g} x the BS hedge's ({orc[N_max]['within_state_sd']:.3f} vs {bs[N_max]['within_state_sd']:.2f})", orc[N_max]["within_state_sd"] < frac * bs[N_max]["within_state_sd"])
    bsd = Hd["mixture_paths"]["between_state_sd"]
    add(f"C4 mixture oracle hedge: the overall spread at N = {N_max} is the between-state sd sqrt(p(1-p)) |C(0.6) - C(0.2)| = {bsd:.2f} (to 1 %)", orc[N_max]["pnl_gross"]["sd"], bsd, 0.01, "rel")
    add(f"C4 mixture BS hedge: the overall spread at N = {N_max} exceeds the between-state sd {bsd:.2f} by less than 10 % -- the floor is mostly the unobserved state", bs[N_max]["pnl_gross"]["sd"], bsd, 0.10, "rel")
    truth(f"C4 mixture BS hedge: the overall spread at N = {N_max} exceeds the between-state sd (the wrong-Greeks piece on top)", bs[N_max]["pnl_gross"]["sd"] > bsd)
    truth("C4 mixture paths: the realised vol by state is 0.2 and 0.6 within 5 s.e. of the mean", all(abs(rv_["mean"] - rv_["sigma"]) <= 5 * rv_["sd"] / sqrt(cnt) for rv_, cnt in zip(Hd["mixture_paths"]["realised_vol_by_state"], Hd["mixture_paths"]["state_counts"])))

    # C5 -- transaction costs
    for name, bk in (("control", ctrl), ("mixture, BS hedge", bs)):
        for a, b in zip(Ns, Ns[1:]):
            if a >= 64:
                add(f"C5 {name}: the rebalancing cost's mean for N = {a} -> {b} grows by sqrt 4 = 2 (to 10 %)", bk[b]["cost_rebalance"]["mean"] / bk[a]["cost_rebalance"]["mean"], 2.0, 0.10, "rel")
    add("C5 control: the log-log slope of the rebalancing cost against N over N >= 64 is +1/2 (within 0.05)", Hd["control"]["slopes_over_N_ge_64"]["cost_rebalance_mean"], 0.5, 0.05)
    add("C5 mixture BS hedge: the log-log slope of the rebalancing cost against N over N >= 64 is +1/2 (within 0.05)", Hd["mixture_bs_hedge"]["slopes_over_N_ge_64"]["cost_rebalance_mean"], 0.5, 0.05)
    truth(f"C5 control: cost rises at every step of N ({' < '.join(f'{ctrl[N]['cost_rebalance']['mean']:.3f}' for N in Ns)})", all(ctrl[a]["cost_rebalance"]["mean"] < ctrl[b]["cost_rebalance"]["mean"] for a, b in zip(Ns, Ns[1:])))
    to = Hd["control"]["trade_off"]
    if N_max >= 1024:
        truth(f"C5 control: spread + cost is smallest at an interior N of the grid (N = {to['N_minimising_spread_plus_cost_on_grid']}) -- neither the coarsest nor the finest", Ns[0] < to["N_minimising_spread_plus_cost_on_grid"] < Ns[-1])
        truth(f"C5 control: at N = {N_max} the mean cost exceeds the spread -- costs win in the fine limit ({ctrl[N_max]['cost_total']['mean']:.2f} vs {ctrl[N_max]['pnl_gross']['sd']:.2f})", ctrl[N_max]["cost_total"]["mean"] > ctrl[N_max]["pnl_gross"]["sd"])
    truth(f"C5 control: at N = {Ns[0]} the spread exceeds the mean cost ({ctrl[Ns[0]]['pnl_gross']['sd']:.2f} vs {ctrl[Ns[0]]['cost_total']['mean']:.3f})", ctrl[Ns[0]]["pnl_gross"]["sd"] > ctrl[Ns[0]]["cost_total"]["mean"])
    within_se(f"C5 control, N = {N_max}: the net P&L's mean is minus the mean cost", ctrl[N_max]["pnl_net"], -ctrl[N_max]["cost_total"]["mean"])

    # D9 / P5
    P5 = res["quotes"]
    truth(f"P5 the stock at 110, 40 vol: the call is worth {P5['price_at_110_vol_0.40']:.2f}, more than 6 above the stale 18.02 price quote", P5["price_at_110_vol_0.40"] - P5["price_at_100_vol_0.40"] > 6.0)
    truth(f"P5 the stale 18.02 re-read at S = 110 is a much lower vol ({P5['implied_vol_of_18.02_at_110']:.3f}, below 0.25)", P5["implied_vol_of_18.02_at_110"] < 0.25)
    return checks


# --- main -------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--quick", action="store_true", help="a tenth of the paths and N up to 256 only, no JSON written; the oracle comparisons skipped if unavailable")
    args = parser.parse_args()
    q = args.quick

    params = {
        "seed": args.seed, "quick": q,
        "T": 1.0, "S0": 100.0, "K": 100.0, "r": 0.05, "sigma": 0.40, "q": 0.0,
        "formula": "C = S_0 e^(-qT) N(d_1) - K e^(-rT) N(d_2); d_1 = (ln(S_0/K) + (r - q + 1/2 sigma^2) T)/(sigma sqrt T); d_2 = d_1 - sigma sqrt T; vega = S_0 e^(-qT) phi(d_1) sqrt T (2.10)",
        "solver": {"sigma0": 0.2, "lo": 1e-6, "hi": 5.0, "price_tol": 1e-12, "sigma_tol": 1e-14, "max_iter": 100,
                   "method": "Newton on sigma with the analytic vega, the bracket [lo, hi] narrowed by the sign of the price error, a bisection step whenever Newton would leave it or vega is zero; stop when |price error| <= price_tol x max(1, |price|) or the bracket is narrower than sigma_tol",
                   "bounds": "max(S_0 e^(-qT) - K e^(-rT), 0) <= C <= S_0 e^(-qT) (call); max(K e^(-rT) - S_0 e^(-qT), 0) <= P <= K e^(-rT) (put) -- a price outside has no implied vol and is refused"},
        "grid": {"S0": [80.0, 100.0, 120.0], "K": [90.0, 100.0, 110.0], "r": [0.0, 0.05], "q": [0.0, 0.03], "sigma": [0.2, 0.4], "T": [0.25, 1.0, 2.0], "source": "2.9's grid (216 points), call and put"},
        "mixtures": {
            "symmetric": {"p": [0.5, 0.5], "sigmas": [0.2, 0.6], "forward_factors": [1.0, 1.0],
                          "model": "S_T = f_j F e^(-1/2 sigma_j^2 T + sigma_j sqrt T Z) with probability p_j; Sum p_j f_j = 1 keeps E^Q[S_T] = F; price = Sum p_j C_BS(f_j S_0, K, r, sigma_j, T)",
                          "rms_vol": sqrt(0.5 * 0.2 ** 2 + 0.5 * 0.6 ** 2), "mean_vol": 0.4},
            "skewed": {"p": [0.75, 0.25], "sigmas": [0.3, 0.6], "forward_factors": [1.05, 0.85],
                       "why": "the high-vol component carries the lower forward: down-moves come with high vol, the market's skew in miniature; 0.75 x 1.05 + 0.25 x 0.85 = 1"},
        },
        "smile": {"strikes": [60.0, 160.0, 101], "taus": [1.0, 0.5, 0.25, 0.05]},
        "kurtosis": {"n_draws": 100_000 if q else 1_000_000, "n_batches": 10},
        "daily": {"n_paths": 2_000 if q else 20_000, "steps": 252},
        "hedging": {"n_fine": 4096, "Ns": [4, 16, 64, 256] if q else [4, 16, 64, 256, 1024, 4096], "n_paths": 400 if q else 4000, "chunk_paths": 400 if q else 500,
                    "fee_k": 0.001, "fee_note": "10 basis points of the value of every share traded, at setup, at each rebalance and at the unwind",
                    "drift": "mu = r for every path set (Decision -- owner may overrule): under the pricing drift the discounted stock is a martingale, so E[hedged P&L] = E^Q[e^(-rT) payoff] - P_0 = 0 for every N and every hedge (2.8), and the spread carries the whole story; 2.7 showed the hedge is drift-blind in the limit"},
        "cited_from_2_7": {"source": "experiments/2_7_delta_hedging.json, scenario base (sigma_r = sigma_i = 0.4, mu = 0, seed 20261101, 4000 paths), per_N call.hedged_pnl_discounted",
                           "sd_by_N": {"4": 6.1818, "16": 3.2407, "64": 1.6382, "256": 0.8309, "1024": 0.4183, "4096": 0.2116}, "sd_sqrtN_4096": 13.543,
                           "vol_low_sd_4096": 1.245, "vol_high_sd_4096": 1.619, "note": "2.7's off-vol scenarios (sigma_r = 0.3 / 0.5 at sigma_i = 0.4) had spreads that stopped falling at about 1.2 and 1.6 -- the same floor, seen one vol at a time"},
    }
    T, S0, K, r, sigma = params["T"], params["S0"], params["K"], params["r"], params["sigma"]
    solver = {k_: params["solver"][k_] for k_ in ("sigma0", "lo", "hi", "price_tol", "sigma_tol", "max_iter")}
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    phi_err = phi_self_test()
    print(f"[2.11] Phi self-test: max abs error {phi_err:.2e}", flush=True)

    # --- C1: the solver
    C0 = float(price(S0, K, r, 0.0, sigma, T))
    base = implied_vol(C0, S0, K, r, 0.0, T, +1, trace=True, **solver)
    lower, upper = no_arbitrage_bounds(S0, K, r, 0.0, T, +1)
    bounds = {"lower_bound": lower, "upper_bound": upper, "price_at_sigma_lo": float(price(S0, K, r, 0.0, solver["lo"], T)), "price_at_sigma_hi": float(price(S0, K, r, 0.0, solver["hi"], T)),
              "refusals": {f"price_{p_}": {k_: v_ for k_, v_ in implied_vol(p_, S0, K, r, 0.0, T, +1, **solver).items()} for p_ in (4.0, 101.0, 99.5, 4.9, 60.0)}}
    print(f"[2.11] C1 base case C = {C0:.4f}: implied vol {base['sigma']:.15f} in {base['iterations']} iterations ({base['bisections']} bisections), status {base['status']}; "
          f"bounds ({lower:.3f}, {upper:.0f}); price at sigma = 5: {bounds['price_at_sigma_hi']:.2f}", flush=True)
    print("[2.11] C1 trace: " + "; ".join(f"it {t_['iteration']}: sigma {t_['sigma']:.10f}, error {t_['price_error']:+.2e}" for t_ in base["trace"]), flush=True)
    g = params["grid"]
    grid_points = [(S, k_, rr, qq, sg, t_) for S in g["S0"] for k_ in g["K"] for rr in g["r"] for qq in g["q"] for sg in g["sigma"] for t_ in g["T"]]
    grid_rt = solver_round_trip_grid(grid_points, solver)
    print(f"[2.11] C1 grid round trip: worst call {grid_rt['max_abs_sigma_error_call']:.1e}, put {grid_rt['max_abs_sigma_error_put']:.1e}; iterations {grid_rt['iterations']}; statuses {grid_rt['statuses']}", flush=True)
    live = quantlib_implied_vol(grid_points, solver)
    golden = solver_golden_check(Path(__file__).resolve().parent, solver)
    if live is None:
        print("[2.11] C1: QuantLib-Python not importable -- live oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        print(f"[2.11] C1: QuantLib {live['version']} blackFormulaImpliedStdDev at {live['n_points']} points, call and put: worst |ours - theirs| {live['max_abs_sigma_error']:.1e} ({live['worst_row']})", flush=True)
    if golden is None:
        print("[2.11] C1: golden/bs_vanilla.json not found -- committed-oracle comparison " + ("skipped (--quick)" if q else "MISSING (the full run requires it, I4)"), flush=True)
    else:
        for blk in ("cases", "edge_cases"):
            b_ = golden[blk]
            print(f"[2.11] C1 golden {blk}: {b_['n']} rows, {b_['n_inside_bounds']} inside the bounds ({b_['n_on_lower_bound']} on the lower bound), statuses {b_['statuses']}; "
                  f"vega >= 1: {b_['identifiable']['n']} rows, worst sigma error {b_['identifiable']['max_abs_sigma_error']:.1e} ({b_['identifiable']['worst_row']}), worst price error {b_['identifiable']['max_abs_price_error_rel']:.1e}, max iterations {b_['identifiable']['iterations_max']}; "
                  f"1e-8 <= vega < 1: {b_['vega_limited']['n']} rows, worst sigma error {b_['vega_limited']['max_abs_sigma_error']:.1e}, worst ratio to the bound {b_['vega_limited']['max_ratio_sigma_error_to_bound']:.2f} ({b_['vega_limited']['worst_row']}); "
                  f"vega < 1e-8: {b_['not_identifiable']['n']} rows, worst price error {b_['not_identifiable']['max_abs_price_error_rel']:.1e}, worst sigma error {b_['not_identifiable']['max_abs_sigma_error']:.3g}", flush=True)
    solver_res = {"base_case": base, "bounds_base_case": bounds, "grid_round_trip": grid_rt, "oracle": {"live": live, "golden": golden}}

    # --- C2: the market
    strikes = np.linspace(*params["smile"]["strikes"][:2], int(params["smile"]["strikes"][2]))
    market = {}
    for name in ("symmetric", "skewed"):
        mix = params["mixtures"][name]
        sm = smile(mix, S0, r, T, strikes, solver)
        ref = params["mixtures"]["symmetric"]["rms_vol"]
        feat = smile_features(mix, S0, r, T, solver, ref)
        market[name] = {"mixture": mix, "smile_T1": sm, "features": feat, "exact_log_moments": mixture_log_moments(mix, S0, r, T),
                        "smiles_by_tau": {f"tau_{tau:g}": smile(mix, S0, r, tau, strikes, solver) for tau in params["smile"]["taus"]}}
        print(f"[2.11] C2 {name} mixture: at the forward {feat['at_forward']:.4f}, at the spot {feat['at_spot']:.4f}, min {feat['minimum_fine_scan']['implied_vol']:.4f} at K = {feat['minimum_fine_scan']['K']:.2f} (F = {feat['forward']:.2f}); "
              f"K = 60: {feat['points']['K_60']['implied_vol']:.4f}, 80: {feat['points']['K_80']['implied_vol']:.4f}, 120: {feat['points']['K_120']['implied_vol']:.4f}, 160: {feat['points']['K_160']['implied_vol']:.4f}; "
              f"slope at F {feat['slope_at_forward_per_unit_log_moneyness']:+.4f}; symmetry gaps {[f'{s_['gap']:+.1e}' for s_ in feat['symmetry_about_forward']]}; crosses rms at {[f'{c_:.1f}' for c_ in feat['crosses_reference_vol_at_K']]}; "
              f"parity gap {sm['parity_gap_max_abs']:.1e}; call-put iv gap {sm['call_minus_put_implied_vol_max_abs_where_both_vega_ge_1e-3']:.1e}", flush=True)
    symm = params["mixtures"]["symmetric"]
    atm_mix = float(mixture_price(K, S0, r, T, symm, +1))
    market["symmetric"]["rms_vol"] = symm["rms_vol"]
    market["symmetric"]["atm"] = {"K": K, "mixture_price": atm_mix, "implied_vol": implied_vol(atm_mix, S0, K, r, 0.0, T, +1, **solver)["sigma"],
                                  "price_at_mean_vol": float(price(S0, K, r, 0.0, symm["mean_vol"], T)), "price_at_rms_vol": float(price(S0, K, r, 0.0, symm["rms_vol"], T)),
                                  "component_prices": [float(price(S0, K, r, 0.0, s_, T)) for s_ in symm["sigmas"]],
                                  "price_at_implied_vol_of_the_forward": float(price(S0, K, r, 0.0, market["symmetric"]["features"]["at_forward"], T))}
    print(f"[2.11] C2 at the money: mixture {atm_mix:.4f} = 1/2 x {market['symmetric']['atm']['component_prices'][0]:.4f} + 1/2 x {market['symmetric']['atm']['component_prices'][1]:.4f}; C(0.40) = {market['symmetric']['atm']['price_at_mean_vol']:.4f}; "
          f"C(0.447) = {market['symmetric']['atm']['price_at_rms_vol']:.4f}; implied {market['symmetric']['atm']['implied_vol']:.4f}", flush=True)
    kurt = kurtosis_study(rng, params["kurtosis"]["n_draws"], params["kurtosis"]["n_batches"], symm, S0, r, T, sigma)
    market["kurtosis"] = kurt
    print(f"[2.11] C2 kurtosis of log S_T on {kurt['n_draws']} draws: mixture {kurt['mixture']['excess_kurtosis_mean']:.3f} +- {kurt['mixture']['excess_kurtosis_se']:.3f} (exact {kurt['mixture']['exact_excess_kurtosis']:.3f}), "
          f"beyond 3 sd {100 * kurt['mixture']['fraction_beyond_3sd']:.3f} % vs normal {100 * kurt['lognormal']['fraction_beyond_3sd_exact']:.3f} %; lognormal {kurt['lognormal']['excess_kurtosis_mean']:+.3f} +- {kurt['lognormal']['excess_kurtosis_se']:.3f}", flush=True)

    # --- C3: 2.6's battery and the daily returns
    logS, state = draw_mixture_terminal(rng, params["kurtosis"]["n_draws"], symm, S0, r, T)
    battery = battery_2_6(logS, state, symm, S0, r, T)
    daily = daily_returns_study(rng, params["daily"]["n_paths"], params["daily"]["steps"], symm, S0, r, T)
    print(f"[2.11] C3 2.6's battery on the mixture ({battery['n']} draws, sigma_fit = {battery['sigma_fit']:.4f}): {battery['n_pass']} pass, {battery['n_fail']} fail -- "
          + "; ".join(f"{r_['check'][:28]}: z = {r_['z']:+.1f}" if "z" in r_ else f"sd S_T gap {100 * r_['relative_gap']:+.2f} %" for r_ in battery["rows"]), flush=True)
    print(f"[2.11] C3 daily returns ({daily['n_paths']} paths x {daily['steps']}): pooled kurtosis {daily['pooled']['excess_kurtosis']:.3f} (exact {daily['pooled']['exact_excess_kurtosis_scale_mixture']:.3f}), beyond 3 sd {100 * daily['pooled']['fraction_beyond_3sd']:.3f} % = {daily['pooled']['ratio_to_normal']:.1f} x normal; "
          f"by state kurtosis {[f'{b_['excess_kurtosis']:+.3f}' for b_ in daily['by_state']]}, annualised sd {[f'{b_['annualised_sd']:.4f}' for b_ in daily['by_state']]}; realised vol per path by state {[f'{m_:.3f}' for m_ in daily['realised_vol_per_path']['mean_by_state']]}", flush=True)

    # --- C4 / C5: the hedge under the wrong model, with costs
    sigma_imp = market["symmetric"]["atm"]["implied_vol"]
    H = params["hedging"]
    print(f"[2.11] C4 hedging: {H['n_paths']} paths x {H['n_fine']} fine steps, N in {H['Ns']}; control at sigma = {sigma}; mixture hedged at sigma_imp = {sigma_imp:.4f}, bought at {atm_mix:.4f}; oracle at the path's sigma_j; fee {H['fee_k']}", flush=True)
    hedging = hedging_scenarios(rng, H, T, S0, K, r, symm, sigma, sigma_imp, atm_mix, H["fee_k"])
    for name in ("control", "mixture_bs_hedge", "mixture_oracle_hedge"):
        rows = hedging[name]["per_N"]
        print(f"[2.11] C4 {name}: sd by N " + ", ".join(f"{r_['N']}: {r_['pnl_gross']['sd']:.3f}" for r_ in rows)
              + (f"; within-state sd " + ", ".join(f"{r_['N']}: {r_['within_state_sd']:.3f}" for r_ in rows) if name != "control" else "")
              + f"; mean at N = {rows[-1]['N']}: {rows[-1]['pnl_gross']['mean']:+.4f} +- {rows[-1]['pnl_gross']['se_of_mean']:.4f}; slopes {hedging[name]['slopes_over_N_ge_64']}", flush=True)
    print(f"[2.11] C4 between-state sd {hedging['mixture_paths']['between_state_sd']:.3f} (C_j = {[f'{c_:.3f}' for c_ in hedging['mixture_paths']['component_prices_C_j']]}); state counts {hedging['mixture_paths']['state_counts']}", flush=True)
    to = hedging["control"]["trade_off"]
    print("[2.11] C5 control trade-off: " + "; ".join(f"N = {r_['N']}: spread {r_['spread_sd']:.3f}, cost {r_['cost_mean']:.3f}, sum {r_['sum']:.3f}" for r_ in to["rows"]) + f"; best N = {to['N_minimising_spread_plus_cost_on_grid']}; cost ratios N -> 4N {[f'{c_['ratio']:.3f}' for c_ in to['cost_ratio_N_to_4N']]}", flush=True)

    # --- D9 / P5 quotes
    quotes = {"price_at_110_vol_0.40": float(price(110.0, K, r, 0.0, sigma, T)), "implied_vol_of_18.02_at_110": implied_vol(C0, 110.0, K, r, 0.0, T, +1, **solver)["sigma"],
              "price_at_100_vol_0.40": C0, "note": "P5: the stock moves 100 -> 110; the price quote 18.02 is stale (the call is now worth 24.74 at 40 vol), the vol quote 0.40 is not; re-read at 110, 18.02 would mean a vol of about 0.21"}
    print(f"[2.11] P5 quotes: at S = 110 and 40 vol the call is {quotes['price_at_110_vol_0.40']:.3f}; 18.02 at S = 110 implies sigma = {quotes['implied_vol_of_18.02_at_110']:.4f}", flush=True)

    results = {"phi_max_abs_error": phi_err, "solver": solver_res, "market": market, "returns": {"battery_2_6": battery, "daily": daily}, "hedging": hedging, "quotes": quotes,
               "d9": {"smiles": {name: {k_: {"strikes": v_["strikes"], "call_price": v_["call_price"], "put_price": v_["put_price"], "implied_vol": v_["implied_vol_call"], "forward": v_["forward"], "T": v_["T"]}
                                         for k_, v_ in market[name]["smiles_by_tau"].items()} for name in ("symmetric", "skewed")},
                      "solver_trace_base_case": base["trace"], "bounds_base_case": {"lower": lower, "upper": upper},
                      "kurtosis_table": {"mixture_log_S_T": kurt["mixture"]["excess_kurtosis_mean"], "mixture_exact": kurt["mixture"]["exact_excess_kurtosis"], "lognormal": 0.0,
                                         "daily_pooled": daily["pooled"]["excess_kurtosis"], "daily_by_state": [b_["excess_kurtosis"] for b_ in daily["by_state"]]},
                      "quotes": quotes, "units": "prices in currency; implied vols per 1.00; strikes in currency; fixtures carry no claim beyond C1-C5"}}
    checks = build_checks(results, params)

    out = {"page": "2.11", "script": Path(__file__).name, "params": params,
           "environment": {"numpy": np.__version__, "quantlib": live["version"] if live else None, "golden_oracle": golden["oracle"] if golden else None},
           "results": results, "checks": checks}
    out_path = Path(__file__).with_suffix(".json")
    if q:
        print(f"[2.11] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  ({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.11] {'checked (--quick)' if q else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s ({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
