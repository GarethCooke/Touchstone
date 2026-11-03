"""Delta hedging and the Black-Scholes PDE -- the experiment behind page 2.7.

Serves page 2.7 (docs/quant-learn-index-v1.md). The stock is page 2.6's
Geometric Brownian motion (GBM),

    dS = mu S dt + sigma S dW        (drift first),

stepped EXACTLY, never by Euler: S_{i+1} = S_i exp((mu - 1/2 sigma^2) dt
+ sigma dW_i), 2.6's closed-form step. The option is a European call with
value V(t, S). Page 2.7's argument: a portfolio holding the option and short
Delta shares, Pi = V - Delta S, has by 2.5's general form (a = mu S, b =
sigma S)

    dPi = (dV/dt + 1/2 sigma^2 S^2 d2V/dS2) dt + (mu S dV/dS - Delta mu S) dt
          + (sigma S dV/dS - Delta sigma S) dW,

so the choice Delta = dV/dS removes BOTH the dW term and mu; what is left is
riskless, must earn r, and that is the Black-Scholes PDE

    dV/dt + 1/2 sigma^2 S^2 d2V/dS2 + r S dV/dS - r V = 0.

Session S7's setup decision (owner, 2026-11-01): the call's V and Delta are
taken from the closed-form formula as a black box -- the course derives it
only at 2.9 -- and the experiment measures only what 2.7 claims: the hedged
P&L. A forward, whose value S - K e^(-r tau) needs no stochastic calculus,
is hedged the same way as the control (Delta = 1, zero gamma).

The hedge is discrete and self-financing: buy the call at V_0, short Delta_0
shares, hold the balance in cash at r; at each of N rebalance times the cash
accrues, the share position is reset to the new Delta, and the difference is
paid from or into cash; at T the call pays off, the shares are bought back,
and what is left is the P&L. The same path is hedged at every N (drawn once
at 4096 steps and coarsened, 2.6's nested-grid shape), so N = 1 ... 4096 hedge
the SAME Brownian path more or less often. N = 1 is the static hedge (Delta_0
shares held to expiry) and N = 2 the once-reset one; the 1/sqrt N law and its
slopes are fitted over the rebalanced hedges, N >= 4.

  C1  Realised = implied, mu = 0: the hedged P&L has mean 0 (within s.e.) from
      N = 64 and a spread that falls like 1/sqrt N (log-log slope -1/2 over
      N >= 4): 4x the rebalances halves it. The static hedge at N = 1 already
      removes more than half of the unhedged spread -- the option's linear
      exposure, taken out once; rebalancing works on the curvature that is
      left. The unhedged call's P&L (buy it, fund it at r, hold to expiry)
      has a spread that does not move with N, matching the closed form under
      the real-world drift.
  C2  The drift test: mu in {-0.2, 0, +0.3} on the same N grid. From N = 64
      the hedged P&L's mean and spread do not move with mu (within s.e.); at
      N = 4 and 16 the drift leaves an O(dt) trace (a mean under 17 % of the
      spread, a spread within 15 %) that the finer grids remove. The unhedged
      P&L's mean moves with mu at every N, matching the closed form. mu
      vanishes from the hedged book, not from the stock -- in the limit the
      lemma describes, and visibly by 64 rebalances a year. The static hedge
      (N = 1) is NOT drift-blind: its spread at mu = +0.3 is well above its
      spread at mu = 0, because a Delta set once goes stale as the drift
      carries S away from it. Drift-blindness is bought by rebalancing.
  C3  Realised != implied: sigma_realised in {0.3, 0.4, 0.5}, the stock
      stepped at sigma_realised, the hedge priced and rebalanced at the
      implied 0.4. The mean hedged P&L has the sign of sigma_r^2 - sigma_i^2
      and equals (sigma_r^2 - sigma_i^2) x E[Sum e^(-rt) 1/2 Gamma S^2 dt]
      measured on the same paths (2.10's line, previewed); path by path the
      P&L tracks Sum e^(-rt) 1/2 Gamma S^2 ((dS/S)^2 - sigma_i^2 dt), the
      gamma P&L, with a residual that shrinks like 1/N.
  C4  The forward as control: V = S - K e^(-r tau), Delta = 1, hedged on the
      same paths at every N: P&L identically zero to rounding. A linear payoff
      needs no stochastic calculus -- the course's thesis in one row.
  C5  The PDE itself. (i) On every (t, S) the hedge visits, the closed form's
      theta, delta and gamma satisfy dV/dt + 1/2 sigma^2 S^2 Gamma + r S Delta
      - r V = 0 to rounding; and on a (t, S) grid, with the Greeks taken by
      finite differences from V alone, the residual falls like h^2 (ties to
      3.3's PDE page). (ii) The discrete hedge's P&L is EXACTLY Sum e^(-rt)
      [dV - Delta dS - (V - Delta S)(e^(r dt) - 1)] path by path (the
      bookkeeping identity dPi = dV - Delta dS - r Pi_cash dt), and replacing
      dV by Ito's lemma (theta dt + Delta dS + 1/2 Gamma (dS)^2) reproduces
      it with an rms residual that falls faster than the P&L's own spread
      (slope between -1 and -0.65 against the P&L's -1/2). Split by
      half-life: over the first half, where V is smooth, Taylor's remainder
      is O(dt) (slope -1, 2.6's C4 again); over the second half, towards the
      payoff's kink at expiry, it is shallower -- the lemma wants a smooth
      V, and the call's gets less smooth as tau -> 0. With the PDE, the
      dt-form of the sum is zero; what the hedger is left with is 2.5's
      (dW)^2 - dt noise, scaled by 1/2 Gamma S^2 sigma^2.

Run from the repository root:

    uv run experiments/2_7_delta_hedging.py [--seed 20261101] [--quick]

--quick runs a tenth of the paths for the learn site's build-time snippet
check (I3): the statistical tolerances widen by the square root of the
path-count ratio so the same claims are still asserted, and NO JSON is
written -- the committed result is always the full run.

Writes 2_7_delta_hedging.json beside this file: parameters in, results out,
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


# --- the normal CDF, vectorised ----------------------------------------------
#
# numpy has no erf. This is Hart's 1968 rational approximation as given by
# West (2005), accurate to about 1e-14 in double precision; main() checks it
# against math.erf before anything else runs.


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


# --- the closed form, as a black box (2.9 derives it) --------------------------


def call_greeks(S, tau, K, r, sigma):
    """Value, delta, gamma, theta of a European call at time-to-expiry tau > 0."""
    S = np.asarray(S, dtype=float)
    st = sigma * sqrt(tau)
    d1 = (np.log(S / K) + (r + 0.5 * sigma * sigma) * tau) / st
    d2 = d1 - st
    disc = exp(-r * tau)
    Nd1, Nd2, nd1 = Phi(d1), Phi(d2), phi(d1)
    V = S * Nd1 - K * disc * Nd2
    delta = Nd1
    gamma = nd1 / (S * st)
    theta = -S * nd1 * sigma / (2.0 * sqrt(tau)) - r * K * disc * Nd2
    return V, delta, gamma, theta


def call_payoff(S, K):
    S = np.asarray(S, dtype=float)
    return np.maximum(S - K, 0.0), (S > K).astype(float)


def forward_value(S, tau, K, r):
    """A forward struck at K: V = S - K e^(-r tau), delta 1, gamma 0, theta -r K e^(-r tau)."""
    S = np.asarray(S, dtype=float)
    disc = exp(-r * tau)
    return S - K * disc, np.ones_like(S), np.zeros_like(S), -r * K * disc * np.ones_like(S)


def unhedged_closed_form(S0, K, T, mu, sigma_r, V0, r) -> dict:
    """Buy the call at V_0 (priced at the implied vol), fund it at r, hold to T, under the
    REAL-WORLD drift mu and realised vol sigma_r: E[payoff] and sd of the P&L in closed form
    (the lognormal integrated against the payoff -- the same integral 2.9 does with r)."""
    st = sigma_r * sqrt(T)
    d1 = (log(S0 / K) + (mu + 0.5 * sigma_r * sigma_r) * T) / st
    d2 = d1 - st
    E_pay = S0 * exp(mu * T) * float(Phi(d1)) - K * float(Phi(d2))
    E_pay2 = (S0 * S0 * exp((2.0 * mu + sigma_r * sigma_r) * T) * float(Phi(d1 + st))
              - 2.0 * K * S0 * exp(mu * T) * float(Phi(d1)) + K * K * float(Phi(d2)))
    funding = V0 * exp(r * T)
    return {"mean": E_pay - funding, "sd": sqrt(max(E_pay2 - E_pay * E_pay, 0.0)),
            "E_payoff": E_pay, "funding_cost_at_T": funding}


# --- the hedge -----------------------------------------------------------------


def hedge_chunk(S, T, K, r, sigma_i, instrument) -> dict[str, np.ndarray]:
    """Hedge every path in S (m paths x (N+1) prices on an even grid) N times.

    Returns per-path arrays: pnl_T (the book at T), pnl_disc (Sum e^(-rt) of the exact
    step identity), ito (the same sum with dV replaced by theta dt + Delta dS + 1/2 Gamma
    (dS)^2), gamma_pnl (Sum e^(-rt) 1/2 Gamma S^2 ((dS/S)^2 - sigma_i^2 dt)), gamma_dt
    (Sum e^(-rt) 1/2 Gamma S^2 dt), pde_max (max |PDE residual| at the points visited),
    V0 and the unhedged P&L (payoff - V0 e^(rT)), plus the running P&L of the first path.
    """
    m, Np1 = S.shape
    N = Np1 - 1
    dt = T / N
    accr = exp(r * dt) - 1.0
    greeks = (lambda s, tau: call_greeks(s, tau, K, r, sigma_i)) if instrument == "call" \
        else (lambda s, tau: forward_value(s, tau, K, r))
    terminal = (lambda s: call_payoff(s, K)) if instrument == "call" \
        else (lambda s: (s - K, np.ones_like(s)))

    Si = S[:, 0]
    V, delta, gamma, theta = greeks(Si, T)
    V0 = V.copy()
    cash = -V + delta * Si
    pnl_disc = np.zeros(m)
    ito = np.zeros(m)
    ito_resid_first_half = np.zeros(m)        # Taylor's remainder over the steps with tau >= T/2
    ito_resid_second_half = np.zeros(m)       # ... and over the steps nearer expiry
    gamma_pnl = np.zeros(m)
    gamma_dt = np.zeros(m)
    pde_max = 0.0
    running = [0.0]
    for i in range(N):
        tau_next = T - (i + 1) * dt
        S1 = S[:, i + 1]
        if i + 1 < N:
            V1, d1, g1, th1 = greeks(S1, tau_next)
        else:
            V1, d1 = terminal(S1)
            g1 = th1 = None
        dS = S1 - Si
        df = exp(-r * (i + 1) * dt)
        carry = (V - delta * Si) * accr           # what the cash leg earns or costs this step
        step = (V1 - V) - delta * dS - carry
        pnl_disc += df * step
        taylor = theta * dt + delta * dS + 0.5 * gamma * dS * dS
        ito += df * (taylor - delta * dS - carry)
        if tau_next >= 0.5 * T:
            ito_resid_first_half += df * ((V1 - V) - taylor)
        else:
            ito_resid_second_half += df * ((V1 - V) - taylor)
        gamma_pnl += df * 0.5 * gamma * (dS * dS - sigma_i * sigma_i * Si * Si * dt)
        gamma_dt += df * 0.5 * gamma * Si * Si * dt
        pde = theta + 0.5 * sigma_i * sigma_i * Si * Si * gamma + r * Si * delta - r * V
        pde_max = max(pde_max, float(np.abs(pde).max()))
        cash = cash * exp(r * dt) + (d1 - delta) * S1
        running.append(float((V1[0] - d1[0] * S1[0] + cash[0])))
        Si, V, delta, gamma, theta = S1, V1, d1, g1, th1
    pnl_T = V + cash - delta * Si
    payoff = V
    unhedged = payoff - V0 * exp(r * T)
    return {"pnl_T": pnl_T, "pnl_disc": pnl_disc, "ito": ito, "gamma_pnl": gamma_pnl,
            "ito_first": ito_resid_first_half, "ito_second": ito_resid_second_half,
            "gamma_dt": gamma_dt, "pde_max": np.array([pde_max]), "V0": V0,
            "unhedged": unhedged, "running_first": np.array(running)}


def stats(x: np.ndarray) -> dict[str, float]:
    sd = float(x.std(ddof=1))
    return {"mean": float(x.mean()), "sd": sd, "se_of_mean": sd / sqrt(x.size),
            "se_of_sd": sd / sqrt(2.0 * (x.size - 1)),
            "rms": float(sqrt((x * x).mean())), "max_abs": float(np.abs(x).max())}


def loglog_slope(xs, ys) -> float:
    return float(np.polyfit(np.log10(xs), np.log10(ys), 1)[0])


def histogram(x: np.ndarray, lo: float, hi: float, bins: int) -> dict:
    counts, _ = np.histogram(x, bins=bins, range=(lo, hi))
    return {"lo": lo, "hi": hi, "bins": bins, "counts": [int(c) for c in counts],
            "below_lo": int((x < lo).sum()), "above_hi": int((x >= hi).sum())}


def scenario(rng, n_paths, n_fine, Ns, chunk_paths, T, S0, K, r, mu, sigma_r, sigma_i,
             keep_first, label) -> dict:
    """Draw n_paths exact-GBM paths at n_fine steps once, hedge each at every N in Ns."""
    dt_f = T / n_fine
    acc = {inst: {N: {k: [] for k in ("pnl_T", "pnl_disc", "ito", "gamma_pnl", "ito_first", "ito_second", "gamma_dt", "unhedged", "V0")}
                  for N in Ns} for inst in ("call", "forward")}
    pde_max = {N: 0.0 for N in Ns}
    first_paths = {}
    realised = []
    for start in range(0, n_paths, chunk_paths):
        m = min(chunk_paths, n_paths - start)
        Z = rng.standard_normal((m, n_fine))
        logS = np.empty((m, n_fine + 1))
        logS[:, 0] = log(S0)
        np.cumsum((mu - 0.5 * sigma_r * sigma_r) * dt_f + sigma_r * sqrt(dt_f) * Z, axis=1, out=logS[:, 1:])
        logS[:, 1:] += log(S0)
        S_fine = np.exp(logS)
        lr = np.diff(logS, axis=1)
        realised.append(lr.std(axis=1, ddof=1) * sqrt(n_fine / T))
        for N in Ns:
            S = S_fine[:, :: n_fine // N].copy()            # the same path, read on N steps
            for inst in ("call", "forward"):
                h = hedge_chunk(S, T, K, r, sigma_i, inst)
                for k in acc[inst][N]:
                    acc[inst][N][k].append(h[k])
                if inst == "call":
                    pde_max[N] = max(pde_max[N], float(h["pde_max"][0]))
                    if start == 0 and N == keep_first["N"]:
                        first_paths = {"N": N, "S": S[:keep_first["paths"]].tolist(),
                                       "pnl_T": h["pnl_T"][:keep_first["paths"]].tolist(),
                                       "running_pnl_first_path": h["running_first"].tolist()}
    realised = np.concatenate(realised)
    per_N = []
    for N in Ns:
        c = {k: np.concatenate(v) for k, v in acc["call"][N].items()}
        f = {k: np.concatenate(v) for k, v in acc["forward"][N].items()}
        V0 = float(c["V0"][0])
        hedged = stats(c["pnl_T"])
        disc = stats(c["pnl_disc"])
        resid_ito = stats(c["pnl_disc"] - c["ito"])
        resid_gamma = stats(c["pnl_disc"] - c["gamma_pnl"])
        per_N.append({
            "N": N, "dt": T / N,
            "call": {
                "hedged_pnl_T": hedged,
                "hedged_pnl_discounted": disc,
                "sd_times_sqrtN": hedged["sd"] * sqrt(N),
                "bookkeeping_identity_max_abs": float(np.abs(c["pnl_disc"] - c["pnl_T"] * exp(-r * T)).max()),
                "ito_residual": resid_ito,
                "ito_residual_over_sd": resid_ito["rms"] / disc["sd"],
                "ito_residual_first_half": stats(c["ito_first"]),
                "ito_residual_second_half": stats(c["ito_second"]),
                "mean_over_sd": hedged["mean"] / hedged["sd"],
                "gamma_pnl": stats(c["gamma_pnl"]),
                "gamma_pnl_residual": resid_gamma,
                "gamma_pnl_residual_over_sd": resid_gamma["rms"] / disc["sd"],
                "gamma_dt_mean": float(c["gamma_dt"].mean()),
                "gamma_dt_se": float(c["gamma_dt"].std(ddof=1) / sqrt(c["gamma_dt"].size)),
                "mean_predicted_by_vol_gap": (sigma_r ** 2 - sigma_i ** 2) * float(c["gamma_dt"].mean()),
                "pde_residual_max_abs_at_visited_points": pde_max[N],
                "unhedged_pnl_T": stats(c["unhedged"]),
                "unhedged_closed_form": unhedged_closed_form(S0, K, T, mu, sigma_r, V0, r),
            },
            "forward": {"pnl_T_max_abs": float(np.abs(f["pnl_T"]).max()),
                        "pnl_T_rms": float(sqrt((f["pnl_T"] ** 2).mean()))},
        })
    base_N = Ns[0]
    # slopes are fitted over the rebalanced hedges, N >= 4: N = 1 and 2 are the static and
    # once-reset hedges, kept in per_N as the comparison the 1/sqrt N law does not cover
    fit = [p for p in per_N if p["N"] >= 4]
    fit_N = [p["N"] for p in fit]
    out = {
        "label": label, "mu": mu, "sigma_realised": sigma_r, "sigma_implied": sigma_i,
        "n_paths": n_paths, "n_fine": n_fine,
        "V0": float(np.concatenate(acc["call"][base_N]["V0"])[0]),
        "realised_vol": {"mean": float(realised.mean()), "sd": float(realised.std(ddof=1)),
                         "expected": sigma_r},
        "per_N": per_N,
        "slopes_fitted_over_N": fit_N,
        "slopes": {
            "hedged_sd": loglog_slope(fit_N, [p["call"]["hedged_pnl_T"]["sd"] for p in fit]),
            "ito_residual_rms": loglog_slope(fit_N, [p["call"]["ito_residual"]["rms"] for p in fit]),
            "ito_residual_first_half_rms": loglog_slope(fit_N, [p["call"]["ito_residual_first_half"]["rms"] for p in fit]),
            "ito_residual_second_half_rms": loglog_slope(fit_N, [p["call"]["ito_residual_second_half"]["rms"] for p in fit]),
            "gamma_pnl_residual_rms": loglog_slope(fit_N, [p["call"]["gamma_pnl_residual"]["rms"] for p in fit]),
            "unhedged_sd": loglog_slope(fit_N, [p["call"]["unhedged_pnl_T"]["sd"] for p in fit]),
        },
    }
    if first_paths:
        out["first_paths"] = first_paths
    # histograms for demo D5: hedged P&L at the smallest and a mid N, and unhedged
    hist = {}
    for N in (Ns[0], keep_first["N"], Ns[-1]):
        x = np.concatenate(acc["call"][N]["pnl_T"])
        hist[f"hedged_N{N}"] = histogram(x, -20.0, 20.0, 80)
    hist["unhedged"] = histogram(np.concatenate(acc["call"][base_N]["unhedged"]), -40.0, 120.0, 80)
    out["histograms"] = hist
    return out


# --- C5 (i): the PDE by finite differences on a (t, S) grid --------------------


def pde_finite_differences(K, r, sigma, T, S_lo, S_hi, n_S, t_lo, t_hi, n_t, h_rel_list) -> dict:
    S = np.linspace(S_lo, S_hi, n_S)
    ts = np.linspace(t_lo, t_hi, n_t)
    rows = []
    analytic_max = 0.0
    for h_rel in h_rel_list:
        res = []
        for t in ts:
            tau = T - t
            h = h_rel * S
            k = h_rel * tau
            V, delta, gamma, theta = call_greeks(S, tau, K, r, sigma)
            analytic_max = max(analytic_max, float(np.abs(theta + 0.5 * sigma ** 2 * S ** 2 * gamma + r * S * delta - r * V).max()))
            Vp, *_ = call_greeks(S + h, tau, K, r, sigma)
            Vm, *_ = call_greeks(S - h, tau, K, r, sigma)
            Vtp, *_ = call_greeks(S, tau - k, K, r, sigma)     # later time: tau smaller
            Vtm, *_ = call_greeks(S, tau + k, K, r, sigma)
            dVdS = (Vp - Vm) / (2 * h)
            d2VdS2 = (Vp - 2 * V + Vm) / (h * h)
            dVdt = (Vtp - Vtm) / (2 * k)
            res.append(dVdt + 0.5 * sigma ** 2 * S ** 2 * d2VdS2 + r * S * dVdS - r * V)
        res = np.array(res)
        rows.append({"h_rel": h_rel, "rms": float(sqrt((res ** 2).mean())), "max_abs": float(np.abs(res).max())})
    return {"grid": {"S": [S_lo, S_hi, n_S], "t": [t_lo, t_hi, n_t]},
            "analytic_greeks_residual_max_abs": analytic_max,
            "finite_differences": rows,
            "slope_rms_vs_h": loglog_slope([x["h_rel"] for x in rows], [x["rms"] for x in rows])}


# --- checks --------------------------------------------------------------------


def build_checks(res, params) -> list[dict]:
    checks = []
    slack = sqrt(4000 / params["paths"]["n_paths"])
    Ns = params["paths"]["Ns"]
    bias_tol = 0.12 + 3.0 / sqrt(params["paths"]["n_paths"])   # 0.167 at 4,000 paths: the trace plus 3 s.e. of mean/sd

    def add(claim, measured, expected, tol, mode="abs"):
        ok = abs(measured - expected) <= tol if mode == "abs" else abs(measured / expected - 1) <= tol
        checks.append({"claim": claim, "measured": float(measured), "expected": float(expected),
                       "tolerance": float(tol), "mode": mode, "pass": bool(ok)})

    add("Phi: Hart/West normal CDF agrees with math.erf on [-9, 9] (max abs diff < 1e-13)", res["phi_max_abs_error"], 0.0, 1e-13)

    sc = res["scenarios"]
    base = sc["base"]
    fine = 64   # from here on, the O(dt) traces of discrete hedging are below the s.e.
    # C1
    for p in base["per_N"]:
        N, c = p["N"], p["call"]
        if N >= fine:
            add(f"C1 N={N}: hedged P&L mean is 0 (within 5 s.e.)", c["hedged_pnl_T"]["mean"], 0.0, 5 * c["hedged_pnl_T"]["se_of_mean"])
        else:
            add(f"C1 N={N}: hedged P&L mean is small against its spread (|mean| < {bias_tol:.2f} sd; the O(dt) trace of hedging only {N} times)", c["mean_over_sd"], 0.0, bias_tol)
        add(f"C1 N={N}: unhedged P&L mean matches the closed form under mu (within 5 s.e.)", c["unhedged_pnl_T"]["mean"], c["unhedged_closed_form"]["mean"], 5 * c["unhedged_pnl_T"]["se_of_mean"])
        add(f"C1 N={N}: unhedged P&L sd matches the closed form (within 5 s.e.)", c["unhedged_pnl_T"]["sd"], c["unhedged_closed_form"]["sd"], 5 * c["unhedged_pnl_T"]["se_of_sd"])
    sds = {p["N"]: p["call"]["hedged_pnl_T"]["sd"] for p in base["per_N"]}
    add("C1: log-log slope of hedged P&L sd vs N is -1/2", base["slopes"]["hedged_sd"], -0.5, 0.05 * slack)
    add("C1: log-log slope of unhedged P&L sd vs N is 0 -- it does not shrink", base["slopes"]["unhedged_sd"], 0.0, 0.02 * slack)
    add(f"C1: sd(N={Ns[-1]}) / sd(N=4) is sqrt(4/{Ns[-1]}) (to 15 %)", sds[Ns[-1]] / sds[4], sqrt(4 / Ns[-1]), 0.15 * slack, "rel")
    add("C1: the static hedge (N = 1, Delta_0 shares held to expiry) already removes more than half of the unhedged spread", float(sds[1] < 0.5 * base["per_N"][0]["call"]["unhedged_pnl_T"]["sd"]), 1.0, 0.0)
    last = base["per_N"][-1]["call"]
    add(f"C1 N={Ns[-1]}: unhedged sd / hedged sd is at least 20", float(last["unhedged_pnl_T"]["sd"] / last["hedged_pnl_T"]["sd"] >= 20.0), 1.0, 0.0)
    add("C1: realised volatility of the stepped paths is sigma_realised (to 1 %; 2.6's check)", base["realised_vol"]["mean"], base["realised_vol"]["expected"], 0.01 * slack, "rel")

    # C2
    drift = {k: sc[k] for k in ("drift_down", "base", "drift_up")}
    for k, s in drift.items():
        for p in s["per_N"]:
            c = p["call"]
            if p["N"] >= fine:
                add(f"C2 {k} mu={s['mu']:+.1f} N={p['N']}: hedged P&L mean is 0 (within 5 s.e.)", c["hedged_pnl_T"]["mean"], 0.0, 5 * c["hedged_pnl_T"]["se_of_mean"])
            elif p["N"] >= 4:
                add(f"C2 {k} mu={s['mu']:+.1f} N={p['N']}: hedged P&L mean is small against its spread (|mean| < {bias_tol:.2f} sd; the drift's O(dt) trace at {p['N']} rebalances)", c["mean_over_sd"], 0.0, bias_tol)
            add(f"C2 {k} mu={s['mu']:+.1f} N={p['N']}: unhedged P&L mean matches the closed form under mu (within 5 s.e.)", c["unhedged_pnl_T"]["mean"], c["unhedged_closed_form"]["mean"], 5 * c["unhedged_pnl_T"]["se_of_mean"])
    for i, p in enumerate(base["per_N"]):
        N = p["N"]
        b, d, u = (drift[k]["per_N"][i]["call"] for k in ("base", "drift_down", "drift_up"))
        for lab, o in (("+0.3", u), ("-0.2", d)):
            se_sd = sqrt(b["hedged_pnl_T"]["se_of_sd"] ** 2 + o["hedged_pnl_T"]["se_of_sd"] ** 2)
            if N >= fine:
                add(f"C2 N={N}: hedged P&L sd at mu={lab} equals sd at mu=0 (within 5 s.e.)", o["hedged_pnl_T"]["sd"], b["hedged_pnl_T"]["sd"], 5 * se_sd)
            elif N >= 4:
                add(f"C2 N={N}: hedged P&L sd at mu={lab} is within 15 % of sd at mu=0 (the drift's O(dt) trace at {N} rebalances)", o["hedged_pnl_T"]["sd"], b["hedged_pnl_T"]["sd"], 0.15, "rel")
        if N == 1:
            add(f"C2 N={N}: the static hedge is NOT drift-blind -- sd at mu=+0.3 is more than 15 % above sd at mu=0 (drift-blindness is bought by rebalancing)", float(u["hedged_pnl_T"]["sd"] > 1.15 * b["hedged_pnl_T"]["sd"]), 1.0, 0.0)
        se_m = sqrt(u["unhedged_pnl_T"]["se_of_mean"] ** 2 + d["unhedged_pnl_T"]["se_of_mean"] ** 2)
        add(f"C2 N={N}: unhedged mean at mu=+0.3 minus mean at mu=-0.2 is more than 5 s.e. from 0 -- mu is still in the stock", float(abs(u["unhedged_pnl_T"]["mean"] - d["unhedged_pnl_T"]["mean"]) > 5 * se_m), 1.0, 0.0)

    # C3
    for k in ("vol_low", "vol_high"):
        s = sc[k]
        sign = 1.0 if s["sigma_realised"] > s["sigma_implied"] else -1.0
        for p in s["per_N"]:
            c = p["call"]
            add(f"C3 {k} sigma_r={s['sigma_realised']} N={p['N']}: hedged P&L mean has the sign of sigma_r^2 - sigma_i^2 and is more than 5 s.e. from 0", float(sign * c["hedged_pnl_T"]["mean"] > 5 * c["hedged_pnl_T"]["se_of_mean"]), 1.0, 0.0)
            add(f"C3 {k} sigma_r={s['sigma_realised']} N={p['N']}: discounted hedged P&L mean is (sigma_r^2 - sigma_i^2) x E[Sum e^(-rt) 1/2 Gamma S^2 dt] on the same paths (within 5 s.e.)", c["hedged_pnl_discounted"]["mean"], c["mean_predicted_by_vol_gap"], 5 * c["hedged_pnl_discounted"]["se_of_mean"])
    for k in ("vol_low", "base", "vol_high"):
        s = sc[k]
        for p in s["per_N"]:
            c = p["call"]
            add(f"C3 {k} N={p['N']}: P&L minus the gamma P&L Sum e^(-rt) 1/2 Gamma S^2 ((dS/S)^2 - sigma_i^2 dt) is small against the P&L's own spread (rms ratio < 4/sqrt N)", c["gamma_pnl_residual_over_sd"], 0.0, 4.0 / sqrt(p["N"]))
        add(f"C3 {k}: log-log slope of rms(P&L minus gamma P&L) vs N is between -1 and -0.65 -- steeper than the P&L's -1/2", s["slopes"]["gamma_pnl_residual_rms"], -0.825, 0.175 + 0.05 * (slack - 1))

    # C4
    for p in base["per_N"]:
        add(f"C4 N={p['N']}: the forward hedged with Delta = 1 has P&L identically 0 on every path (max abs < 1e-8)", p["forward"]["pnl_T_max_abs"], 0.0, 1e-8)
    for k in ("drift_up", "vol_high"):
        p = sc[k]["per_N"][-1]
        add(f"C4 {k} N={p['N']}: the forward's P&L is 0 whatever mu or sigma_realised (max abs < 1e-8)", p["forward"]["pnl_T_max_abs"], 0.0, 1e-8)

    # C5
    pde = res["pde"]
    add("C5 (i): analytic theta, delta, gamma satisfy the PDE on the (t, S) grid (max abs < 1e-9)", pde["analytic_greeks_residual_max_abs"], 0.0, 1e-9)
    for row in pde["finite_differences"]:
        add(f"C5 (i) h_rel={row['h_rel']}: finite-difference PDE residual rms is bounded by 10 h_rel^2 x K", row["rms"], 0.0, 10.0 * row["h_rel"] ** 2 * params["K"])
    add("C5 (i): log-log slope of the finite-difference residual vs step size is 2", pde["slope_rms_vs_h"], 2.0, 0.1)
    for p in base["per_N"]:
        c = p["call"]
        add(f"C5 (i) N={p['N']}: the PDE holds at every (t, S) the hedge visited (max abs < 1e-9)", c["pde_residual_max_abs_at_visited_points"], 0.0, 1e-9)
        add(f"C5 (ii) N={p['N']}: discounted P&L equals Sum e^(-rt) [dV - Delta dS - (V - Delta S)(e^(r dt) - 1)] path by path (max abs < 1e-8)", c["bookkeeping_identity_max_abs"], 0.0, 1e-8)
        add(f"C5 (ii) N={p['N']}: replacing dV by Ito's lemma leaves a residual small against the P&L's spread (rms ratio < 4/sqrt N)", c["ito_residual_over_sd"], 0.0, 4.0 / sqrt(p["N"]))
    add("C5 (ii): log-log slope of rms(Ito residual) vs N is between -1 and -0.65 -- steeper than the P&L's -1/2", base["slopes"]["ito_residual_rms"], -0.825, 0.175 + 0.05 * (slack - 1))
    add("C5 (ii): over the first half of the option's life (tau >= T/2, V smooth) the Ito residual's rms has slope -1 -- Taylor's remainder is O(dt)", base["slopes"]["ito_residual_first_half_rms"], -1.0, 0.1 * slack)
    add("C5 (ii): over the second half (towards the payoff's kink) the slope is shallower than -1 by at least 0.1 -- the lemma's smoothness is wearing thin", float(base["slopes"]["ito_residual_second_half_rms"] > -0.9), 1.0, 0.0)
    for p in base["per_N"]:
        c = p["call"]
        add(f"C5 (ii) N={p['N']}: the second half of the life carries more of the Ito residual than the first (rms ratio > 1)", float(c["ito_residual_second_half"]["rms"] > c["ito_residual_first_half"]["rms"]), 1.0, 0.0)
    return checks


# --- main ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--quick", action="store_true",
                        help="a tenth of the paths, wider tolerances, no JSON written")
    args = parser.parse_args()

    q = args.quick
    params = {
        "seed": args.seed,
        "T": 1.0, "S0": 100.0, "K": 100.0, "r": 0.05, "sigma_implied": 0.40,
        "model": "dS = mu S dt + sigma S dW (drift first), stepped exactly: S_{i+1} = S_i exp((mu - 1/2 sigma^2) dt + sigma dW_i); call priced and hedged at sigma_implied from the closed form (2.9) as a black box",
        "hedge": "buy one call at V_0, short Delta shares, cash at r; rebalance N times on an even grid; P&L reported at T (pnl_T) and discounted to 0 (pnl_discounted)",
        "paths": {"n_fine": 4096, "Ns": [1, 2, 4, 16, 64, 256, 1024, 4096],
                  "n_paths": 400 if q else 4000, "chunk_paths": 500,
                  "keep_first": {"N": 256, "paths": 5}},
        "scenarios": {
            "base": {"mu": 0.0, "sigma_realised": 0.40},
            "drift_down": {"mu": -0.2, "sigma_realised": 0.40},
            "drift_up": {"mu": 0.3, "sigma_realised": 0.40},
            "vol_low": {"mu": 0.0, "sigma_realised": 0.30},
            "vol_high": {"mu": 0.0, "sigma_realised": 0.50},
        },
        "pde_grid": {"S": [50.0, 200.0, 151], "t": [0.0, 0.9, 10], "h_rel": [0.04, 0.02, 0.01, 0.005]},
    }
    T, S0, K, r, si = params["T"], params["S0"], params["K"], params["r"], params["sigma_implied"]
    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()

    phi_err = phi_self_test()
    print(f"[2.7] Phi self-test: max abs error {phi_err:.2e}", flush=True)

    P = params["paths"]
    scenarios = {}
    for label, s in params["scenarios"].items():
        print(f"[2.7] scenario {label}: mu = {s['mu']:+.1f}, sigma_realised = {s['sigma_realised']}, "
              f"hedged at sigma_implied = {si}; {P['n_paths']:,} paths, N = {P['Ns']}", flush=True)
        scenarios[label] = scenario(rng, P["n_paths"], P["n_fine"], P["Ns"], P["chunk_paths"], T, S0, K, r,
                                    s["mu"], s["sigma_realised"], si, P["keep_first"], label)

    g = params["pde_grid"]
    print("[2.7] PDE by finite differences on the (t, S) grid", flush=True)
    pde = pde_finite_differences(K, r, si, T, g["S"][0], g["S"][1], g["S"][2], g["t"][0], g["t"][1], g["t"][2], g["h_rel"])

    results = {"phi_max_abs_error": phi_err, "scenarios": scenarios, "pde": pde}
    checks = build_checks(results, params)

    out = {
        "page": "2.7",
        "script": Path(__file__).name,
        "params": params,
        "environment": {"numpy": np.__version__},
        "results": results,
        "checks": checks,
    }
    out_path = Path(__file__).with_suffix(".json")
    if args.quick:
        print(f"[2.7] --quick: {out_path.name} NOT written (the committed result is the full run)")
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['claim']}  "
              f"({c['measured']:.4g} vs {c['expected']:.4g})")
    print(f"[2.7] {'checked (--quick)' if args.quick else 'wrote ' + out_path.name} in {time.perf_counter() - t0:.1f}s "
          f"({len(checks) - len(failed)}/{len(checks)} checks pass)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
