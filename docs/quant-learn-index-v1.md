# Derivatives for developers — index v1

Working title. Two things, linked both ways:

- **The learning area** — a separate section of the site, not under `/projects`, aimed at
  developers who work alongside quants. Tutorial pages, interactive demos, knowledge checks.
- **The project** — a pricing-and-risk library with a card and architecture page under
  `/projects`, the Anvil pattern. The tutorial's checks are the library's tests; the demos
  run on it.

Organising thesis: linear products (forwards, futures, swaps) are priced by discounting and
no-arbitrage; only nonlinear payoffs (options) need stochastic calculus.

Every page lists a **Check** — the test, experiment or question that fails if the reader
has misunderstood the page.

---

## Part 0 — Orientation

- **0.1 Why derivatives exist.** Risk transfer; hedgers, speculators, market makers; OTC vs
  exchange-traded.
- **0.2 Linear vs nonlinear.** The thesis, a map of the parts, how to use the demos, checks
  and exercises.
- **0.3 Conventions.** Notation, units (annualised vol, continuous vs simple rates, day
  counts), prerequisites, how to run the code.

## Part 1 — Products

Each page: what it is · who needs it and why · how it's priced · how it's risked · lifecycle
from booking to settlement.

- **1.0 Cash and discounting.** Time value, discount factors, zero and forward curves,
  compounding conventions. *Check:* the day-count bug — price a 6-month deposit with the
  wrong convention and see the size of the error.
- **1.1 Forwards.** Cash-and-carry gives F = S·e^((r−q)T) with no stochastics at all; MTM
  value after inception; delta of one. Lifecycle: trade → confirm → settle, physical or cash.
  *Check:* replicate a forward with spot plus borrowing; show the payoffs match.
- **1.2 Futures.** Exchange-traded forwards: clearing, initial and variation margin, daily
  settlement, rolling; why they exist (credit risk removed, liquidity); basis risk.
  *Check:* walk a margin account through a week of prices.
- **1.3 Swaps.** Interest rate swaps: PV(fixed) − PV(float), the par rate, why the floating
  leg is worth par at a reset; PV01 and bucketed curve risk; fixings, resets, netting,
  collateral — the forty lifecycle events. *Check:* price a 2-year swap by hand from a
  curve, perturb one curve point, predict which bucket moves.
- **1.4 Options.** Calls, puts, payoffs, moneyness, intrinsic vs time value; why they exist
  (asymmetry, leverage, income); European vs American; exercise, assignment, expiry. The
  price is the cost of hedging — the hook into Part 2. *Check:* payoff-diagram builder;
  combine legs into a straddle and a collar.
- **1.5 The trade lifecycle and the risk system.** Capture → confirmation → settlement →
  lifecycle events → EOD risk and P&L → reporting. Pricing, risk and P&L explain as system
  components; why the batch reruns everything overnight. *Check:* order the events of a
  swap's life and name the system that owns each.

## Part 2 — Stochastic calculus (learning starts here)

Engineer's level: every rule is verified numerically before it's derived. Python/numpy
experiments while learning; the same invariants become library tests.

- **2.1 Random walks and scaling.** Variance adds, standard deviation doesn't: √n. Why the
  continuous limit needs increments of size √dt. *Check:* simulate; verify variance ∝ t and
  that mean absolute distance does not grow linearly.
- **2.2 Brownian motion.** Definition (independent Gaussian increments, continuous paths);
  nowhere differentiable, self-similar, martingale, Markov. Simulation as a cumulative sum
  of √dt·Z. *Check:* zoom demo; test the increment distribution.
- **2.3 Quadratic variation.** Σ(ΔW)² → T while Σ|ΔW| → ∞. The rulebook: (dW)² = dt,
  dW·dt = 0, (dt)² = 0. The whole reason ordinary calculus fails. *Check:* the counter demo;
  a test asserting the QV of a simulated path is within tolerance of T.
- **2.4 The Itô integral.** Left-endpoint sums and why (non-anticipation: the integrand is
  the hedge you hold over the next interval); ∫W dW = ½W_T² − ½T; zero mean, martingale,
  Itô isometry; Stratonovich as an aside. *Check:* left-endpoint vs midpoint sums give
  different answers — assert which one matches ½W² − ½T.
- **2.5 Itô's lemma.** Second-order Taylor plus the rulebook:
  df = (f_t + a·f_x + ½b²·f_xx)dt + b·f_x dW. Worked: W², log S, e^(W−t/2).
  *Check:* simulate both sides for f = W²; assert e^(W_t − t/2) has constant mean.
- **2.6 SDEs and geometric Brownian motion.** dS = μS dt + σS dW; solve via log S; the
  −½σ² correction (mean vs median, volatility drag); exact sampling vs Euler–Maruyama; where
  the √dt comes from. Mean reversion (OU) as a second example. *Check:* Gaussian
  log-returns; E[S_T] = S₀e^(μT); Euler error vs dt. Spot-the-bug: σZ·dt instead of σZ·√dt.
- **2.7 Delta hedging and the Black–Scholes PDE.** Π = V − ΔS; Itô on V; choose Δ = ∂V/∂S
  to kill dW; riskless must earn r; μ vanishes. *Check:* hedging simulator — P&L spread
  falls as 1/√N with rebalance count N.
- **2.8 Risk-neutral pricing.** V = e^(−rT)·E^Q[payoff]; drift becomes r; Girsanov as
  reweighting paths, not changing volatility; Feynman–Kac ties the expectation to the PDE.
  *Check:* Monte Carlo under Q matches the PDE; discounted MC under the real-world drift
  does not.
- **2.9 The Black–Scholes formula.** Derive by integrating the lognormal against the payoff;
  what N(d₁) and N(d₂) mean; put–call parity; dividends; Black-76 for forwards and futures.
  *Check:* parity, σ→0 and T→0 limits, MC agreement.
- **2.10 Greeks.** Delta, gamma, vega, theta, rho — what each measures and who watches it.
  The PDE re-read as a P&L statement: theta pays for gamma; a delta-hedged option earns
  ½ΓS²(σ²_realised − σ²_implied)dt. *Check:* bump-and-revalue matches analytic; hedging
  simulator with realised ≠ implied vol shows the gamma P&L.
- **2.11 Where it breaks.** Constant vol, continuous frictionless trading, lognormal returns
  vs reality; smile and skew; why the model survives as a quoting convention (vol is the
  unit of price). Bridge to Part 3 and v2. *Check:* back out implied vols from a synthetic
  skewed market; observe they aren't constant.

## Part 3 — Implementation

- **3.1 Closed form in code.** N(x) numerics; edge cases (T→0, σ→0, deep ITM/OTM); units
  and conventions; reference implementation and its tests.
- **3.2 Monte Carlo.** Exact GBM vs Euler; standard error and convergence; antithetics and
  control variates; seeds and reproducibility; parallelism; when MC is the only option
  (path dependence, many assets).
- **3.3 Finite differences.** Discretise the PDE; explicit, implicit, Crank–Nicolson;
  stability; American options via early exercise; when PDE beats MC.
- **3.4 Implied vol and the surface.** Root finding; the surface as an object;
  interpolation; where it lives in the system and who owns it.
- **3.5 Greeks in practice.** Analytic vs bump-and-revalue (bump sizes, MC noise) vs
  pathwise and AAD; what's actually on the risk report.
- **3.6 In the system.** Pricing library ↔ market data ↔ trade store ↔ risk engine; the EOD
  batch; P&L explain; model validation; why the quant's library has separate model and
  calibration layers.

Checks throughout: each page's test suite plus one spot-the-bug.

## Part 4 — Later (v2 candidates, not commitments)

Vol surfaces properly (arbitrage-free interpolation, SVI) · local vol (Dupire) · stochastic
vol (Heston) · jumps · rates (curve building, multi-curve, caps and swaptions, SABR) ·
exotics (barriers, Asians, digitals and why they're hard to hedge) · American options in
depth · counterparty risk (CVA) · credit (CDS).

---

## The project — pricing and risk library, v1

- **Scope:** European vanillas, one underlying, constant rate and vol, dividend yield.
- **Pricers:** closed form; MC (exact and Euler); Crank–Nicolson FD, American as a stretch.
- **Also:** implied vol solver; Greeks analytic and bump, AAD as a stretch.
- **Tests:** the Part 2 and Part 3 checks, verbatim.
- **Builds:** native C++20; WASM for the site's demos; Python bindings optional.
- **On the site:** project card, architecture page, live demo.

## Demos (interactive, embedded in the pages)

- **D1** Random walk → Brownian motion, zoom to show self-similarity (2.1–2.2)
- **D2** Quadratic variation counter: Σ(ΔW)² vs Σ|ΔW| as steps increase (2.3)
- **D3** ∫W dW with left-endpoint vs midpoint sums (2.4)
- **D4** GBM path generator: exact vs Euler, dt vs √dt toggle, distribution at T (2.6)
- **D5** Delta-hedging simulator — the flagship: rebalance count, realised vs implied vol,
  P&L distribution (2.7, 2.10)
- **D6** Black–Scholes pricer: sliders, Greeks, price-vs-spot curve over the payoff (2.9–2.10)
- **D7** Monte Carlo convergence with error bars (3.2)
- **D8** PDE grid heatmap of V(S, t) (3.3)
- **D9** Implied vol solver and smile viewer (2.11, 3.4)
- **D10** Bump-and-revalue risk table (3.5)

Simple ones in TypeScript; the heavy ones on the WASM build.

## Knowledge checks

- **Multiple choice per page**, 3–6 questions. Each wrong answer encodes a specific
  misconception and the feedback names it.
- **Predict-then-run:** commit to a number, then run the demo.
- **Spot the bug:** one wrong line — √dt, right-endpoint integral, missing −½σ²,
  discounting under the wrong drift.
- **Make the tests pass:** an exercises repo with failing tests per chapter. The
  developer-native "something else".
- **Checkpoints** at the end of each part; progress in localStorage, no accounts, resettable.

## Build order (learning first)

1. **Now — Part 2 as chat sessions**, one topic each, 2.1 → 2.11. Per session: concept,
   derivation, a numpy experiment you run, then your draft page; I review for claims the
   code can't back. Output: draft pages plus experiment scripts, which become demos and tests.
2. **Scaffold the learning area:** route, page template (maths + code), quiz component,
   progress store, demo slot. One agentic session; brief in `docs/briefs`.
3. **Library v1** in C++20 with the Part 2 invariants as tests; WASM build; project card and
   architecture page.
4. **Part 3 pages**, written alongside the library.
5. **Parts 0 and 1** — material you already know; fastest to write.
6. **Wire demos and checkpoints; launch v1.**
7. **Part 4 topics** as separate mini-cycles.

## Open decisions

1. Name and route for the learning area — `/learn`, or something on-theme.
2. Library name — Crucible, Anvil, Temper set the pattern.
3. Snippet language in the tutorial: Python/numpy recommended for readability; the library
   stays C++20.
4. Maths depth: engineer's level throughout, with optional "for the curious" boxes where
   measure theory would otherwise intrude.
5. Licences, separately: code (MIT / Apache-2.0) and prose (CC BY 4.0 / CC BY-NC / all
   rights reserved).
6. How much of Part 1 ships in v1 — recommend all of 1.0–1.5, one page each.
7. Which pages you write vs co-draft — the maths pages should be in your words.
