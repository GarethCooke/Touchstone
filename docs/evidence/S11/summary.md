# S11 — Teaching session · page 2.11 Where it breaks · evidence pack

### 2026-11-08 → 2026-11-09 · claude-fable-5-1 · S11 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved; drafts committed from the session's cloud clone. The last study milestone: the S track is complete.

Work order (P3): teach 2.11 per constitution §7, numbers before theory. Inputs: index
§2.11 (constant vol, continuous frictionless trading, lognormal returns vs reality; smile
and skew; why the model survives as a quoting convention — vol is the unit of price; bridge
to Part 3 and v2; check: back out implied vols from a synthetic skewed market and observe
they are not constant; demo D9), the S11 handover in the owner's project, `drafts/2.10.md`'s
"Into 2.11" (one σ assumed, the market does not; the Greeks become the language for how
prices react as the surface moves; vanna and volga), 2.7's three decisions (the spread
falls like 1/√N under the model; the hedge is drift-blind; hedged at σ_i while the stock
moves at σ_r the mean P&L is (σ_r² − σ_i²) × the gamma integral), 2.10's vega =
S₀φ(d₁)√T > 0, 2.6's test battery, the T-track's golden file (`golden/bs_vanilla.json`,
7,234 rows, QuantLib 1.43), the owner's predictions. Outputs: numpy experiment + JSON in
`touchstone/experiments/`; owner draft in `touchstone-learn/drafts/2.11.md`; checks drafted
by Fable, approved by the owner; S11 batch appended to the notation ledger; draft reviewed
against I1. Session opened 2026-11-08 on the Windows workstation with S10 committed and
ticked (touchstone main 94233e1) and touchstone-learn m/L2 at e35a987 (L2 batch 10 landed
during the session, 92a3173); closed 2026-11-09 with the drafts committed from the session's
cloud clone as the owner (m/L2 497cc91, `preview` fast-forwarded to it).

**Setup decisions (owner, 2026-11-08, before any code — "I accept your recommendations").**
(Q1/a) The synthetic market is a two-component lognormal mixture: the stock is GBM at
σ_low with probability p and at σ_high with probability 1 − p, the state fixed for the life
of the option and unknown when it is sold, the component forwards tied so E[S_T] = F; every
price is Σ p_j C(f_j S₀, K, r, σ_j, T), closed form. The symmetric case p = ½, σ = 0.2 / 0.6,
equal forwards; the skewed case p = ¾ / ¼, σ = 0.3 / 0.6, forwards 1.05 F / 0.85 F. (Q2/a)
One hedging break measured — 2.7's hedge with Black–Scholes deltas at the implied vol on the
mixture's paths — and the transaction-cost break in one table; Leland named for v2. (Q3/a)
One expiry's smile on the page; the four-τ smiles are D9 fixtures only; vanna and volga named,
not computed. (Q4/a) The page ends Part 2 with a bridge.

**Wording rulings (owner, 2026-11-09, on reading the notes).** The at-the-money reasoning
is approximate, not exact — "near the money the call price is approximately linear in σ,
so averaging prices is approximately averaging vols", the Jensen gap being the precise
statement. Quoting in vol "removes the inputs that are usually observable and leaves
volatility, the quantity options are primarily quoted and compared in" — not "the one input
the market disagrees about" (desks disagree about forwards, rates, dividends and borrow too).
The 7.54 floor is "uncertainty about which state was sold before the state became known" —
incompleteness, not a hedge failing. All three applied to the notes, the draft, the checks
and the ledger.

## Exit criteria (ROADMAP, Track S)

- [x] Experiment script and JSON in `touchstone/experiments/` — `2_11_where_it_breaks.py`
      and `.json` (seed 20261108, 157 checks, workstation run, QuantLib 1.43) on the owner's
      disk; committed by the owner with this pack.
- [x] Owner's draft page in `touchstone-learn/drafts/2.11.md` — interview-transcribed (I2),
      committed as the owner, m/L2 497cc91.
- [x] Draft checks approved by the owner — `drafts/2.11-checks.md`, Q1–Q6, "approved"
      2026-11-09.
- [x] Draft reviewed against I1 — thirteen flags raised with recommendations, all ruled "A"
      and applied; every quantitative sentence mapped to the JSON (the CLAIM MAP at the foot
      of the draft).
- [x] Notation batch — eleven rows appended to `drafts/notation.md`, approved 2026-11-09.

**Done**

- Predict-then-run: the four setup questions ruled and five gut predictions captured before
  any code (2026-11-08), questions and answers recorded verbatim at the top of the notes.
  P1 (one price, one vol): right on both parts answered — exactly one σ, vega decides it;
  the range of prices with a vol was not answered (the measurement: 4.877 to 100). P2 (the
  fair mixture): right throughout — a smile, wings dear, lowest near the money, the ATM vol
  below the rms 0.447 because near the money the price is approximately linear in σ (the
  owner's reason, kept approximate by his ruling). P3 (the hedge as N → ∞): right — no, a
  residual unhedgeable risk remains. P4 (costs): right — √N, each trade ∼ 1/√N and N of
  them. P5 (the stale quote): right — the price quote goes stale, the vol quote is portable.
  Five for five; no prediction became a distractor, so the checks' distractors are the
  handover's listening list, marked ⚑ in the checks file.
- Experiment `experiments/2_11_where_it_breaks.py` (seed 20261108). C1 the implied-vol
  solver — Newton on σ with the analytic vega, bisection-safeguarded on [10⁻⁶, 5], stopping
  at a price error of 10⁻¹² (relative above 1, the golden file's rule) or a bracket of 10⁻¹⁴:
  the base case 18.0230 → σ = 0.400000000000 in four iterations from σ₀ = 0.2, no bisection,
  the error 7.6 → 0.068 → 3.8 × 10⁻⁶ → 7 × 10⁻¹⁵; the bounds 4.877 (S₀ − Ke^(−rT)) and 100
  (S₀), 4.0 and 101 refused with status, 99.5 reported above the σ = 5 cap (the price there
  98.79); 2.9's 216-point grid round-tripped call and put, 432 solves all converged, mean 3.1
  iterations, max 9, worst σ error 7.3 × 10⁻¹³; QuantLib `blackFormulaImpliedStdDev` at the
  same 432 points within 7.3 × 10⁻¹³; the golden file's 7,200 grid and 34 edge rows all
  inside the bounds (677 + 10 on the lower bound) and every solve converged, classed by vega:
  vega ≥ 1 (5,354 + 20 rows) recover σ to 4.6 × 10⁻¹¹ in at most 10 iterations; 10⁻⁸ ≤ vega
  < 1 (1,146 + 2) within the bound price_tol × max(1, price) / vega (worst ratio 0.98); vega
  < 10⁻⁸ (700 + 12) reproduce the price to 10⁻¹² but not the vol (up to 0.15 off — the price
  is flat in σ, so it carries no information about σ). C2 the market — the symmetric
  mixture's prices at 101 strikes 60–160, T = 1, every one with a vol; the smile's minimum
  0.3980 at K = F = 105.127 (slope there 10⁻¹⁴), 0.3990 at the spot, 0.4768 at K = 60,
  0.4524 at K = 160, crossing the rms 0.447 at K = 71.0 and 155.6, symmetric σ(K) = σ(F²/K)
  to 4 × 10⁻¹⁶ at three pairs and 3 × 10⁻¹³ at the fourth; parity C − P = S₀ − Ke^(−rT) to
  1.4 × 10⁻¹⁴ and the put's implied vol equal to the call's to 9.7 × 10⁻¹³ at all 101
  strikes; at the money 17.987 = ½ × 10.451 + ½ × 25.523 against C(0.40) = 18.023 and
  C(0.447) = 19.807, implied 0.399; the skewed mixture 0.448 at K = 60, 0.380 at the spot,
  0.370 at 120, minimum 0.369 at K = 131, slope at the forward −0.062 per unit log-moneyness,
  the symmetry broken by 0.035 at K = 80, parity to 1.8 × 10⁻¹⁴; the mixture's log S_T on
  10⁶ draws: excess kurtosis 1.816 ± 0.012 against the mixture-of-normals closed form
  1.8009, skewness −0.412 (exact −0.4095), 1.23 % beyond 3 sd against the normal's 0.27 %;
  the single lognormal 0.001 ± 0.004. C3 lognormal returns vs reality — 2.6's seven-check
  battery on the 10⁶ draws against the lognormal fitted to the first two log moments (σ_fit
  = 0.4543): mean (z −0.6), variance (−0.9), E[S_T] (−0.9) and the sd of S_T (+1.4 %, the
  3 % rule) pass; skewness (−168), kurtosis (+365) and the median (+71) fail; each state
  alone Gaussian (−0.004, −0.005); daily returns on 20,000 paths × 252 steps: pooled kurtosis
  1.892 against the scale-mixture closed form 1.898 at the realised state fractions, 1.26 %
  beyond 3 sd (4.7 × the normal), within each state −0.005 / −0.002 and annualised sd
  0.2001 / 0.5994; realised vol per path bimodal, 0.200 ± 0.009 and 0.599 ± 0.026. C4 the
  hedge under the wrong model — 2.7's hedge as a bank account (buy at P₀, short Δ, cash at
  r, rebalance N times, liquidate), equal to 2.7's telescoped formula per path to 10⁻¹² at
  every N; three books on 4,000 paths × 4,096 fine steps, N = 4 … 4096, drift r: the control
  (GBM at 0.4, hedged at 0.4) sd 6.048 → 0.206, sd·√N 12.1 → 13.2 (2.7's 13.54 within
  2.5 %), slope −0.499; the mixture hedged at σ_i = 0.3990 bought at 17.987: sd 10.515 →
  8.080, slope −0.004, within-state sd 7.538 → 2.832 (slope −0.039), per-state means
  −7.530 ± 0.042 and +7.624 ± 0.080 at N = 4096 against ∓7.536 = C(σ_j) − P₀ (within 5 s.e.
  at every N); the oracle hedge at the path's own σ_j: within-state sd 7.012 → 0.230 (slope
  −0.4995), overall 7.542 against the between-state √(p(1 − p))·|C(0.6) − C(0.2)| = 7.536;
  the mean zero in every book at every N. C5 costs — k = 10 bp on every share traded (setup
  0.063, each rebalance, unwind 0.063): the control's rebalancing cost 0.048 → 1.940, ratio
  per fourfold N 2.42, 2.07, 2.016, 2.001, 2.000, slope +0.502 (the mixture book +0.501);
  spread + cost 6.22, 3.41, 2.01, 1.445, 1.51, 2.27 — smallest at N = 256; the net P&L's sd
  0.846, 0.553, 0.761 at N = 256, 1024, 4096 — smallest at 1024, rising as the cost's own
  spread grows. D9 fixtures: both mixtures' smiles at τ = 1, ½, ¼, 0.05 (strike, call and
  put price, implied vol), the solver's trace, the kurtosis table, the P5 quotes (24.74 at
  S = 110 and 40 vol; 18.02 at 110 means σ = 0.211). 157 checks, all pass. Run in the
  container (27 s, numpy 2.5.3, QuantLib 1.44) and on the workstation (44 s, numpy 2.5.2,
  QuantLib 1.43, `uv run --frozen` with the environment under `~/tmp`, rebuilt in 11 s); the
  two JSONs agree to 2 parts in 10⁹ at worst (a Newton intermediate) and to 3 × 10⁻¹² on
  every quoted value. The workstation's JSON is the committed one (md5 7f91f566…).
- Teaching notes v1 published 2026-11-08 as a private artifact (plain summary first,
  section-map card, the setup rulings, predictions as posed and answered, what ran, A–F
  with eight tables and four canvas figures, the reasoning in five rungs after the numbers,
  decisions, draft checks, draft ledger, the interview plan); v2 at close (the three wording
  rulings, the approvals, the commit) is `teaching-notes.html` beside this file.
- Owner draft `drafts/2.11.md`: all nine interview answers in one attached file on
  2026-11-09, tripled LaTeX re-set (fourteen runs, "Black-Scholes" set with the en dash,
  confirmed "2 confirmed"), transcribed with eight tables and value-path comments; audited
  against the JSON — thirteen flags F1–F13, all wording, none a wrong number, all ruled "A"
  ("1 accept recommendations") and applied: F1 "every production pricer" softened; F2 "the
  first two moments"; F3 the control on its own paths, only the two mixture books sharing
  (I1); F4 the two machines' agreement as 2 parts in 10⁹ (I1); F5 the 700 flat golden rows as
  both kinds — deep in with no time value, deep out with almost no value (I1); F6 σ₀ = 0.2;
  F7 the wings named at K = 60 and 160, still climbing (I1); F8 the skewed mixture's weights
  and vols (I1); F9 the lognormal fitted to the mixture, not the reverse (I1); F10 the median
  among the failing checks (I1); F11 1.26 % against 0.27 % (I1); F12 random walks before
  Brownian motion and GBM written out; F13 "you gave in P2" removed. 2.10 linked now that it
  routes (L2 batch 10, 92a3173); 3.x plain. "3 approved" 2026-11-09.
- Checks `drafts/2.11-checks.md` Q1–Q6, one per section, approved. Ledger: the S11 batch (11
  rows) appended to `drafts/notation.md`, approved; the 2.9 suite's "to 10⁻¹²" pin reads the
  ledger from its S9 batch to end of file, so the bounds row says "(within 10⁻¹²)". `npm
  test`: 1,009 pass in the clone (the suite grew from 966 with batch 10). Committed as the
  owner from the cloud clone: touchstone-learn m/L2 497cc91, `preview` fast-forwarded to it.

**Decisions (with why)**

- Drift μ = r on every hedging path set, not 2.7's μ = 0 — owner may overrule. Under the
  pricing drift the discounted stock is a martingale, so E[hedged P&L] = 0 for every N and
  every hedge (2.8) and E[P&L | state j] = C(σ_j) − P₀ exactly; the spread carries the whole
  story and the per-state means are the price gaps at every N. 2.7 showed the hedge is
  drift-blind in the limit; the control's sd·√N = 13.21 against 2.7's 13.54 at μ = 0 confirms
  the choice costs nothing.
- The golden file's three vega classes (≥ 1; 10⁻⁸ to 1; < 10⁻⁸): the handover asked for
  10⁻¹⁰ "where vega is not vanishing"; a 10⁻¹² price fixes σ to 10⁻¹² / vega, so 10⁻¹⁰ holds
  where vega ≥ 1, the error bound is the honest check in between, and below 10⁻⁸ only the
  price round-trips. Recorded as the page's lesson about identifiability, not as a defect.
- The oracle hedge is on the page as the device that separates the floor's two pieces; it
  is not a strategy anyone can run.
- The skewed mixture's parameters (¾ / ¼, σ 0.3 / 0.6, forwards 1.05 F / 0.85 F) chosen so
  the forward is preserved and the tilt visible (0.08 across the strikes) with no wing beyond
  the solver's cap.
- k = 10 basis points per unit of stock traded, charged at setup, each rebalance and the
  unwind, with setup and unwind reported separately so the √N law is read on the rebalancing
  alone. "Spread + cost" adds an sd to a mean and is labelled a reading aid; the net P&L's
  sd is tabled beside it.
- 2.6's battery run against the lognormal fitted to the mixture's first two log moments
  (σ_fit = 0.4543), not against 0.4 or the rms: fitting the two moments is what makes "which
  check catches it" a fair question.
- Daily-return statistics compared against the closed form at the realised state fractions,
  with the s.e. from batches of paths: the state is per path, so 20,000 paths, not 5 million
  returns, is the sample size for p̂.
- Figures (the smile, the realised-vol histogram, the spread against N, the cost trade-off)
  belong to the notes and to D9; the page has tables (2.9's F8 ruling carried).
- Seed 20261108 (the opening date); 4,000 paths × 4,096 fine steps as 2.7 and 2.10; the
  216-point grid as 2.9.

**Not done**

- The `touchstone` files are on the owner's disk, uncommitted: `experiments/
  2_11_where_it_breaks.{py,json}`, `docs/evidence/S11/{summary.md, teaching-notes.html}`;
  the message in `.git/s11-commit-msg.txt`; the ROADMAP tick (line 234) his, in the same
  commit.
- Page 2.11 is not on the site: L2 batch 11 (Opus/Claude Code: MDX, checks Q1–Q6 wired,
  the S11 ledger batch on 0.3, snippets `implied_vol` / `no_arbitrage_bounds` /
  `mixture_price` / `smile` / `hedge_book` / `quantlib_implied_vol` / `solver_golden_check`,
  demo D9 — the implied-vol solver and smile viewer — from `results.d9.*`; the page ends
  Part 2 so it has no "Into" section and the conventions pass has nothing to re-link). Once
  2.11 routes (`/stochastic-calculus/where-it-breaks`), 2.10's "Into 2.11" is re-linked and
  the ledger's plain "2.11" mentions (the S6 realised-volatility row, the S11 rows) likewise.
- The owner has not yet reviewed page 2.10 on the preview (L2 batch 10's open exit
  criterion), nor its pack's flags ("theta is most negative near the strike where gamma is
  largest"; three figures in the S10 rows).
- With S11 done the S track is complete and L2's entry (S1–S11) is met; L2 itself closes
  after batch 11 with the single F tollgate over all eleven pages (ROADMAP: a fresh Fable
  session, the tollgate prompt verbatim), then the `m/L2` → `main` merge is the owner's.
- Owner items carried: the stray backslashes on ROADMAP lines 228, 230, 231, 232 (`\docs/
  evidence/S5/…` etc.); the index's §2.7 line "riskless must earn r" and the
  `2_7_delta_hedging.py` docstring; the index's §2.6 OU line and §3.2 importance-sampling
  line; the `.git/s7-*`, `s8-`, `s9-`, `s10-commit-msg.txt` leftovers in touchstone; the
  ledger-wide "·" → dash pass (S1–S6 rows) and the "riskless" → "risk-free" pass over the
  earlier drafts, the site and the test pins (S8's F1) — who runs each not yet ruled.

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at 94233e1 — commit
  `experiments/2_11_where_it_breaks.{py,json}` and `docs/evidence/S11/` with the supplied
  message (`.git/s11-commit-msg.txt`), tick S11 (line 234) in `ROADMAP.md` with a pointer to
  this file in the same commit (the word "evidence:" outside the backticks, only the path
  inside), push. `touchstone-learn`: `git pull --ff-only origin m/L2` to pick up 497cc91.
  Then L2 batch 11 (2.11 onto the preview site with D9), his review of 2.10 and 2.11 on the
  preview, and the L2 F tollgate over 2.1–2.11 in a fresh Fable session per §6.
