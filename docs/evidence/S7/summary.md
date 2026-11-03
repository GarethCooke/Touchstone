# S7 — Teaching session · page 2.7 Delta hedging and the Black–Scholes PDE · evidence pack

### 2026-11-03 · claude-fable-5-1 · S7 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved

Work order (P3): teach 2.7 per constitution §7, numbers before theory. Inputs: index
§2.7 (Π = V − ΔS; Itô on V; choose Δ = ∂V/∂S to kill dW; riskless must earn r; μ vanishes;
check: hedging simulator — P&L spread falls as 1/√N with rebalance count N; demo D5), the
S7 handover in the owner's project, `drafts/2.6.md`'s "Into 2.7" (the general form on
V(t, S) with a = μS, b = σS), 2.6's exact GBM step and its means-ignore-it-spreads-keep-it
rule, 2.5's general form, 2.3's Σ(ΔW)² → T, the owner's predictions. Outputs: numpy
experiment + JSON in `touchstone/experiments/`; owner draft in
`touchstone-learn/drafts/2.7.md`; checks drafted by Fable, approved by the owner; S7 batch
appended to the notation ledger; draft reviewed against I1. Session opened 2026-11-01 and
ran across 2026-11-01 and 11-03 in two sittings on the Windows workstation.

**Setup decision (owner, 2026-11-01, before any code).** 2.7 needs a V and a Δ to hedge
with and the course derives the formula only at 2.9. Ruled: (a) the closed form is used on
2.7 as a candidate function — "the formula 2.9 derives" — and the forward, V = S − Ke^(−rτ),
Δ = 1, hedged the same way, is the control. On the owner's challenge in review ("we are
using 2.9's function before doing 2.9?") the page says what licenses the borrowing: the
function's derivatives are substituted into the PDE and the residual is checked at every
point the hedge visits; a function that satisfies the PDE with the payoff condition is the
price whatever 2.9 later says about how to find it.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and answers
  recorded verbatim at the top of the notes. P1 "0 on average with a spread which shrinks
  like 1/√N" (right, both); P2 "yes and yes" (hedged mean follows the drift — wrong from
  64 rebalances a year; unhedged — right); P3 "zero, proportional to implied vol" (wrong on
  both: +3.74 on an 18.02 option, ∝ (σ²_r − σ²_i) × the gamma delivered); P4 "spread 0, does
  not depend on N" (right, both); P5 "dS cancels, leaving dV − dV = 0" (half: the ∂V/∂S·dS
  term cancels and dW and μ with it; what is left is (∂V/∂t + ½σ²S²·∂²V/∂S²) dt, not 0 —
  the PDE says it equals r(V − ΔS) dt). P2, P3 and P5 are the page's target misconceptions
  (check distractors Q2, Q3, Q5).
- `experiments/2_7_delta_hedging.py` + `.json` — claims C1–C5, 204 checks pass, seed
  20261101, 68 s on the Windows workstation (`uv run --frozen`, Python 3.12.15, numpy
  2.5.2); the container run (numpy 2.5.3) agrees to every printed digit, the largest
  difference among non-rounding values 3 parts in 10¹⁰; `--quick` about 7 s. Parameters
  S₀ = K = 100, r = 0.05, σ_implied = 0.4, T = 1, μ = 0 as the base; V₀ = 18.02, Δ₀ = 0.63.
  The stock stepped exactly (2.6's closed-form step, never Euler); 4,000 paths drawn once at
  4,096 steps and hedged at N = 1, 2, 4, 16, 64, 256, 1024, 4096 (2.6's nested grids — the
  same path hedged more or less often; N = 1 the static hedge, N = 2 the once-reset one;
  slopes fitted over N ≥ 4). The hedge: buy one call, short Δ shares, cash at r; at each
  grid time the cash accrues, Δ is reset and the difference paid from or into cash; at T
  the call pays off and the shares are bought back. P&L quoted at T unless marked
  discounted. numpy has no erf: Φ is Hart's rational approximation (West 2005), self-tested
  against `math.erf` to 2 × 10⁻¹⁶ before anything runs.
  C1 (realised = implied, μ = 0): hedged sd 11.8, 8.86, 6.50, 3.41, 1.72, 0.874, 0.440,
  0.223 at N = 1 … 4096, slope −0.488 over N ≥ 4, sd × √N 13.0 → 14.2; mean within 5 s.e.
  of 0 from N = 64, small positive below (+0.30 ± 0.19 at N = 1, +0.19 ± 0.10 at N = 4);
  unhedged mean −3.11 ± 0.47 against the closed form −3.10, sd 29.6 against 29.8 at every
  N, 2,394 of 4,000 paths losing the whole premium; the static hedge already removes more
  than half the unhedged spread (29.6 → 11.8, the linear exposure taken out once).
  C2 (μ ∈ {−0.2, 0, +0.3}): from N = 64 hedged mean 0 within 5 s.e. and sd equal across
  drifts within 5 s.e. (1.63 / 1.72 / 1.69 at N = 64; 0.208 / 0.223 / 0.209 at N = 4096);
  unhedged mean −11.67 (closed form −11.86), −3.11, +22.07 (+22.07), sd 19.6 / 29.6 / 51.5.
  Below N = 64 the drift leaves an O(dt) trace: +0.72 ± 0.11 at N = 4, μ = 0.3, fading
  roughly like 1/N, sd within 15 %. The static hedge is not drift-blind: at N = 1 sd 17.6 at
  μ = 0.3 against 11.8 at μ = 0, mean +3.5 ± 0.3 — drift-blindness is bought by rebalancing.
  C3 (σ_realised ∈ {0.3, 0.4, 0.5}, hedged at 0.4): discounted mean −3.76 ± 0.02,
  0.00 ± 0.004, +3.74 ± 0.03 at N = 4096 against (σ²_r − σ²_i) × E[Σ e^(−rt)·½ΓS²dt] =
  −0.07 × 53.7, 0, +0.09 × 41.6 on the same paths (within 1 s.e.; within 5 s.e. at every
  N ≥ 16); realised vol measured 0.3000 / 0.3999 / 0.5000. Path by path the P&L minus the
  gamma P&L Σ e^(−rt)·½ΓS²((δS/S)² − σ²_i dt) has rms 0.54 → 0.06 of the P&L's spread. The
  spread that stays: 1.25 and 1.62 (discounted) at N = 4096 against 0.21 for the base case,
  and it is the gamma integral's own spread — sd 17.7 around a mean of 41.6 (σ_r = 0.5),
  × 0.09 = 1.60 against the measured 1.62; 17.6 × 0.07 = 1.23 against 1.25.
  C4 (the forward, Δ = 1, same paths, every N, every scenario): |P&L| ≤ 4.4 × 10⁻¹¹.
  C5 (the PDE): analytic Θ, Δ, Γ substituted, residual 6.6 × 10⁻¹⁵ on S ∈ [50, 200] ×
  t ∈ [0, 0.9], ≤ 1.4 × 10⁻¹³ at every (t, S) the hedges visited; central differences from
  V's values alone, residual rms 0.0286, 0.00718, 0.00180, 0.000449 at h = 4 %, 2 %, 1 %,
  0.5 % of S and τ, slope 1.998. The discounted P&L equals Σ e^(−rt)[δV − Δ δS −
  (V − ΔS)(e^(r dt) − 1)] path by path to 10⁻¹² (bookkeeping, no model); with δV replaced
  by Itô's lemma to second order the residual's rms falls faster than the P&L's spread
  (ratio 0.54 → 0.06): slope −1.005 over the first half of the life, −0.770 over the second
  (the payoff's kink), −0.793 whole — asserted as a split and a bound, not as −1.
- Teaching notes (claude.ai artifact, eight versions; archived as `teaching-notes.html`
  beside this file): section map card, predictions scored, what ran, then the three
  decisions a hedger makes (how often to rebalance; what to do about the drift; which σ to
  hedge at), each opening with what it decides; three canvas figures from the JSON (sd
  against N log-log for three scenarios with the unhedged line and the 1/√N reference; the
  hedged P&L histograms at N = 4, 256, 4096 beside the unhedged one; path 1 at N = 256 with
  its running P&L); the bridge from 2.6's "Into 2.7" to the PDE in six rungs and a seventh
  for the per-step P&L ½ΓS²((δS/S)² − σ²dt), placed after the measurements at the owner's
  standing instruction (theory after numbers); the PDE checked; draft checks; the ledger
  batch; the interview plan. Changes from the owner's review questions: "why isn't the
  spread at N = 4 half the unhedged spread?" (N = 1 and 2 added to the grid — the static
  hedge removes the linear exposure once, rebalancing works on the curvature; and the
  static hedge turned out not to be drift-blind); "what is Γ?" and "Γ = ∂²V/∂S² · gamma
  looked like a product" (the ledger's symbol/name separator changed to a dash); "we are
  using 2.9's function before doing 2.9?" (the candidate-function sentence); "I don't get
  [the spread that stays]" (the gamma integral's sd put against the measured spread); every
  rung and section mention made a link after "you keep mentioning stuff without linking".
- Owner draft `touchstone-learn/drafts/2.7.md` — interview transcription, nine questions
  (hook; plan; what was done; decision 1 — how often to rebalance; decision 2 — the drift;
  decision 3 — which volatility; why — from dV to the PDE; the PDE checked and what the
  hedger is left with; into 2.8), all nine answered by the owner in his own words; the owner
  asked for decision 1 tightened from five paragraphs to three, done with his sentences.
  Twelve flags raised, all ruled by the owner in-session and applied: F1 "has sold" →
  "holds" (the experiment's side of the book; the seller named as the mirror image); F2 the
  gamma integral written discounted as the JSON measures it; F3 "realised quadratic
  variation" linked to 2.3 and given a ledger row; F4 "has bought" → "holds", plan questions
  as run-in lines; F5 Black–Scholes en dash; F6 "Geometric Brownian motion (GBM)" written out
  at first use, 2.6 and 2.9 linked; F7 the static hedge's 11.8 was not in the JSON when first
  quoted — N = 1, 2 added and re-run before the page could say it (I1); F8 "essentially
  unchanged" → "unchanged within standard error"; F9 decision 3 quoted mixed conventions —
  discounted throughout, said once; F10 Δ meant both the hedge ratio and a step change —
  ruled "A": Δ is delta, step changes are δS, δV on this page; F11 "Itô's lemma" linked to
  2.5's general form; F12 "six rebalance frequencies" → eight after F7 (Fable's
  inconsistency, caught at approval). Twenty-one pasted LaTeX runs re-set to the course's
  plain notation across the nine answers, each confirmed by the owner. "Into 2.8" previewed,
  not claimed. "2.7 approved" 2026-11-03.
- Page 2.6 repaired in this session (owner's rulings "both" and "add", 2026-11-03), committed
  by the owner as touchstone-learn ad24832 and 736f568: the page never wrote its own model —
  dS = μS dt + σS dW lived only in 2.5's "Into 2.6", the S6 ledger row and check Q1 — so the
  line was added to the hook and to "Solving the SDE", and, after the owner hunted for a
  derivation that does not exist, a hook sentence saying it is a modelling choice (2.2's
  Brownian motion with drift applied to returns, so moves scale with the price and it cannot
  go below zero; 2.11 tests it). Mirroring into the MDX is Claude Code's, on `m/L2`.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.7-checks.md`: one per
  decision plus the PDE from both sides (Q4 the forward; Q5 what cancels and what is left).
- Notation ledger S7 batch, 13 rows — `touchstone-learn/drafts/notation.md`, approved:
  V(t, S); Δ — delta; Γ — gamma; Θ — theta; Π — the hedged portfolio; rebalance — N; r — the
  riskless rate; K, τ; the Black–Scholes PDE; μ vanishes ↺; realised vs implied volatility ↺;
  realised quadratic variation (of the stock) ↺; gamma P&L. Symbol and name divided by a dash
  in this batch (the owner's catch: "·" reads as a product beside a formula).

**Decisions (with why)**

- Setup (a) with the forward as control — above. The forward on the page, not only in the
  JSON: Γ = 0 so the per-step term is identically zero and one hedge at inception is exact,
  which is the course's thesis in one table column.
- r = 0.05, K = S₀ = 100 (at the money), μ = 0 as the base (the owner's P2 as posed), 4,000
  paths — the handover left these open; recorded as owner-may-overrule in the notes.
- The page is cut around three hedger's decisions and the derivation sits after the
  measurements — the owner's S6 instruction ("decisions first, measure second; theory after
  numbers"); v1 had the bridge before the decisions and was re-cut on the handover re-read.
- N = 1 and 2 added to the grid on 2026-11-03 so the static hedge is a measured row, not a
  side calculation; every slope is fitted over N ≥ 4, where the 1/√N law applies, and the
  JSON records `slopes_fitted_over_N`. The N ≥ 4 numbers did not change (same paths).
- C1/C2's "mean 0 within s.e." is asserted from N = 64; below it the checks bound the O(dt)
  trace of a coarse hedge (|mean| < 0.17 sd, sd within 15 % across drifts, N ≥ 4) and at
  N = 1 assert the opposite — that the static hedge is drift-sensitive — because the run
  showed +0.72 ± 0.11 at N = 4, μ = 0.3 and 17.6 against 11.8 at N = 1. The page says when μ
  vanishes rather than that it does.
- The Itô-remainder slope is asserted as a split (−1 ± 0.1 over the first half of the life;
  between −1 and −0.65 overall; the second half carrying more than the first), not as −1:
  the payoff's kink makes V's higher derivatives grow like 1/τ, and the run measured −0.77
  near expiry. The page mentions it briefly, at the owner's ruling, and claims only "faster
  than the P&L; 1/N where V is smooth".
- Decision 3 is quoted discounted to today throughout, because the identity P&L =
  (σ²_r − σ²_i) × gamma integral is exact in discounted terms; decisions 1 and 2 at T.
- Φ by Hart's rational approximation with a self-test rather than a scipy dependency
  (`pyproject.toml` has numpy and QuantLib only; I4 keeps QuantLib an oracle).
- The 5-s.e. convention from 2.5/2.6 for means; 15 % × √(4000/n_paths) relative for rms
  quantities; the bias bound 0.12 + 3/√n_paths; `--quick` widens accordingly. 204 checks.
- Δ/δ: Δ is the option's delta as the index and 2.10 have it; δS, δV mark a grid step on
  this page only — a recorded one-page exception to 2.3–2.6's ΔW, in the ledger.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction, check wiring, demo D5 (the flagship delta-hedging
  simulator, shared with 2.10) — L2 batch 7 by design: page 2.7 into the site as `draft` on
  `m/L2`, an Opus/Claude Code session. Fixtures in the JSON: `results.scenarios.*.per_N[*]`,
  `…base.first_paths` (five paths at N = 256 with the running P&L of path 1), `…histograms`.
  The link anchors in `drafts/2.7.md` follow the conventions pass's slugging and are L2's to
  verify.
- The 2.6 MDX mirror of ad24832/736f568 — Claude Code's, in progress on the owner's disk at
  close (uncommitted changes to `content/stochastic-calculus/sdes-and-gbm.mdx`,
  `docs/evidence/L2/batch-6/summary.md`, `tests/page-2-6.test.ts`).
- The ROADMAP tick for S7 (line 230) — the owner's (I18, P7). Also the owner's: the stray
  backslash in the S5 pointer on line 228 (`\docs/evidence/S5/summary.md`); the index line
  "mean reversion (OU) as a second example" under §2.6 (carried from S6); the `m/L2` → `main`
  merge in touchstone-learn.
- The "·" separator in the S1–S6 ledger rows reads as a product beside a formula (the
  owner's catch); the S7 batch uses a dash and the earlier rows are untouched — a
  ledger-wide pass is the owner's to ask for.
- Leftovers the owner may delete: `.git/s6-interim-commit-msg.txt` and
  `.git/s7-interim-commit-msg.txt` in `touchstone` (neither interim commit was made; the
  closing message supersedes both).

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at 2903301 — commit
  `experiments/2_7_delta_hedging.{py,json}` and `docs/evidence/S7/` with the supplied message
  (`.git/s7-commit-msg.txt`), tick S7 (line 230) in `ROADMAP.md` with a pointer to this file
  in the same commit, push. `touchstone-learn` on `m/L2` at 736f568 — commit
  `drafts/2.7.md`, `drafts/2.7-checks.md`, `drafts/notation.md` with the supplied message
  (`.git/s7-commit-msg.txt`), push; Claude Code's 2.6 mirror and L2 batch 7 (2.7 onto the
  preview site) follow on the same branch. Next milestone: S8 · 2.8 Risk-neutral pricing,
  fresh session per §7, from the S8 handover in the owner's project — the draft's "Into
  2.8" (price as if the stock drifted at r; V = e^(−rT)·E^Q[payoff]; Feynman–Kac named),
  the exact GBM step with μ → r, 2.7's hedged-book result that μ is absent, and the index's
  check (Monte Carlo under Q matches the PDE; discounted MC under the real-world drift does
  not) are its opening material.

## Exit criteria (ROADMAP, track S)

- [x] Experiment script and JSON committed to `touchstone/experiments/` — on the owner's
      disk, uncommitted at close; commit message supplied (`.git/s7-commit-msg.txt`).
- [x] Owner's draft page in `touchstone-learn/drafts/2.7.md` — written in the owner's words,
      interview-transcribed, "2.7 approved".
- [x] Draft checks approved by the owner — Q1–Q5, `drafts/2.7-checks.md`.
- [x] Draft reviewed against I1 — twelve flags, all ruled and applied; every quantitative
      sentence mapped to `2_7_delta_hedging.json` in the review (claim map in the draft's
      footer).
- [ ] ROADMAP tick — the owner's (I18).

## Files

- `touchstone/experiments/2_7_delta_hedging.py`, `.json` (204 checks, seed 20261101)
- `touchstone/docs/evidence/S7/summary.md` (this file), `teaching-notes.html` (v8)
- `touchstone-learn/drafts/2.7.md`, `2.7-checks.md`, `notation.md` (S7 batch appended)
- `touchstone-learn/drafts/2.6.md` — the model line and the "assumed, not derived" sentence
  (committed by the owner, ad24832 and 736f568)
