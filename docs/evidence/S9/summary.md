# S9 — Teaching session · page 2.9 The Black–Scholes formula · evidence pack

### 2026-11-05 · claude-fable-5-1 · S9 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved; drafts committed from the session's cloud clone

Work order (P3): teach 2.9 per constitution §7, numbers before theory. Inputs: index
§2.9 (derive by integrating the lognormal against the payoff; what N(d₁) and N(d₂)
mean; put–call parity; dividends; Black-76 for forwards and futures; check: parity,
σ → 0 and T → 0 limits, MC agreement), the S9 handover in the owner's project,
`drafts/2.8.md`'s "Into 2.9" (the lognormal integral; N(d₁), N(d₂) emerging from the
algebra; the formula derived from the expectation; three views of one value), 2.8's
Q-run (18.010 ± 0.031) and in-the-money mass (47.0 % = Φ(d₂)), 2.7's delta 0.63 and
its PDE check of the closed form, 2.6's exact draw, the T-track's golden file
(`golden/bs_vanilla.json`, QuantLib 1.43), the owner's predictions. Outputs: numpy
experiment + JSON in `touchstone/experiments/`; owner draft in
`touchstone-learn/drafts/2.9.md`; checks drafted by Fable, approved by the owner; S9
batch appended to the notation ledger; draft reviewed against I1. Session opened and
closed 2026-11-05 on the Windows workstation; the drafts committed from the session's
cloud clone as the owner (m/L2 302c7ab, `preview` fast-forwarded to it).

**Setup decisions (owner, 2026-11-05, before any code).** (a) Scope: the call, the
put, put–call parity, a continuous dividend yield q and Black-76, as the index lists
— one integral done once, three substitutions. (b) N(d₁) explained as the probability
of exercise under the measure that uses the stock as numeraire, measured on the
draws in one line, and also as the delta 2.7 hedged with.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and
  answers recorded verbatim at the top of the notes. P1 (the split at the strike;
  the probability 2.8 measured): right — the two expectations E^Q[S_T·1{S_T > K}]
  and E^Q[1{S_T > K}], the second "about 47.0 %, matching Φ(d₂) ≈ 0.470"; the owner
  said the question was badly posed ("needs better wording") and his phrase "the
  average stock price on the paths that finish above the strike" names the
  conditional mean E^Q[S_T | S_T > K] = 140.3, which is not in the price — taken on
  as Q3's second distractor and as a page sentence. P2: right throughout —
  d₁ = 0.325, d₂ = −0.075, N(d₁) = 0.627 > N(d₂) = 0.470 by 0.157, and "how much of
  the stock's value comes from the paths that finish in the money" is N(d₁) in plain
  words; he said d₁ and d₂ were "introduced out of nowhere", which fixed the page's
  structure (the thresholds are born in the algebra, rungs 4 and 5, not named
  before). P3: right — S₀ − Ke^(−rT) ≈ 4.8, "only arb". P4: right on all three
  limits with the reasons. P5: right — cheaper; q replaces r by r − q in d₁, d₂ and
  multiplies the stock term by e^(−qT); the Black-76 half (r leaves d₁, survives in
  the discount) unanswered. No prediction wrong; the handover's listening list
  (N(d₁) as the exercise probability; parity needs the model; σ → 0 gives 0;
  dividends make the call dearer) became check distractors Q3, Q4, Q5, Q6.
- `experiments/2_9_black_scholes_formula.py` + `.json` — claims C1–C5 and the D6
  fixtures, 91 checks pass, seed 20261105, 1.8 s on the Windows workstation
  (`uv run --frozen`, Python 3.12.15, numpy 2.5.2, QuantLib 1.43 — the environment
  rebuilt in 14 s); the container run (numpy 2.5.3, QuantLib 1.44) agrees to 6 parts
  in 10¹³ in every non-rounding value, the draws identical; `--quick` 3 s, skipping
  the oracle if QuantLib or the golden file is absent. Base case S₀ = K = 100,
  r = 0.05, σ = 0.4, T = 1: d₁ = 0.325, d₂ = −0.075, N(d₁) = 0.6274,
  N(d₂) = 0.4701, C = 18.0230, P = 13.1459, C − P = 4.8771 = S₀ − Ke^(−rT).
  C1 (the integral): composite Gauss–Legendre (64 × 32) of e^(−rT)·max(S − K, 0)
  against the lognormal density in S, and in z after the substitution, equals the
  closed form to 2 × 10⁻¹⁴ and 1 × 10⁻¹⁴; the two pieces S₀N(d₁) = 62.741 and
  Ke^(−rT)N(d₂) = 44.718 each to 10⁻¹³; on a 216-point grid of (S₀, K, r, q, σ, T)
  the worst error 2.8 × 10⁻¹³. On 10⁶ exact draws: call 18.011 ± 0.031 (−0.4 s.e.),
  put 13.122 ± 0.017, Q(S_T > K) = 0.4707 ± 0.0005 against N(d₂), the stock piece
  62.79 ± 0.07, the strike piece 44.77 ± 0.05, the share-measure ratio
  0.6278 ± 0.0005 against N(d₁) (delta-method s.e.), E^Q[S_T] = 105.14 ± 0.04, the
  conditional mean 140.23 ± 0.06 against 140.30; the central-bump delta 0.62741
  against N(d₁) = 0.62741.
  C2 (parity): |C − P − (S₀e^(−qT) − Ke^(−rT))| ≤ 2 × 10⁻¹⁴ across the grid; per path
  the payoffs differ by S_T − K exactly (max |·| = 0 on 10⁶ draws); the Monte Carlo
  difference 4.889 ± 0.042 on the same draws, its s.e. the forward's (sd of S_T
  41.6), larger than the call's 0.031; with q = 0.03 and 0.08: 1.958 ± 0.040 against
  1.9216, −2.832 ± 0.039 against −2.8113.
  C3 (limits): σ → 0 at S₀ = 90, 95.123 (F = K), 100, 110 — gaps to
  max(S₀ − Ke^(−rT), 0) monotone, zero to 10⁻⁹ by σ = 10⁻³ off the kink, and at the
  kink linear with C/σ → 37.949 against Ke^(−rT)√T/√(2π) = 37.949 (10⁻⁸ relative);
  T → 0 at S₀ = 90, 100, 110 — gaps to max(S₀ − K, 0) monotone, 5 × 10⁻⁶ = rKT at
  S₀ = 110 and T = 10⁻⁶, and at S₀ = K the fall S₀σ√(T/2π) with C/√T → 15.960
  against 15.958 and N(d₁), N(d₂) → 0.5001, 0.5000; S₀ → ∞ (to 6400) — the gap to
  the forward is the put, 0.67, 3 × 10⁻³, 10⁻⁶, …, 10⁻²⁵, N's → 1 to 10⁻¹²;
  S₀ → 0 (to 0.78) — the call 0.62, 2 × 10⁻³, …, 5 × 10⁻³⁴, N's → 0.
  C4 (dividends and Black-76): at q = 0, 0.03, 0.08 the closed form with S₀e^(−qT),
  Black-76 with F = S₀e^((r−q)T) and the integral give one number to 10⁻¹²
  (18.022951, 16.210727, 13.491561); Black-76's d₁ with no r equals the closed
  form's with r − q to 10⁻¹⁴ (0.325, 0.250, 0.125); 2.8's simulator with the drift
  r − q gives 18.011 ± 0.031, 16.230 ± 0.030, 13.495 ± 0.027 (−0.4, +0.6, +0.1 s.e.);
  the forward control S₀e^(−qT) − Ke^(−rT) within 5 s.e. at each q; across the grid
  the call is decreasing in q and the put increasing at every point.
  C5 (the oracle, I4 — the first time on an S page): QuantLib 1.43's BlackCalculator
  at the 216-point grid, worst 3.6 × 10⁻¹⁴ on price (call and put) and 10⁻¹⁵ on
  delta; its AnalyticEuropeanEngine on a BlackScholesMertonProcess on dates (the
  golden generator's engine, T = 365 days under Actual/365 Fixed) at the base case,
  1.4 × 10⁻¹⁴ on price and 3 × 10⁻¹⁶ on delta; all 7,200 grid cases and 34 edge cases
  of `golden/bs_vanilla.json` (QuantLib 1.43, T0), worst 1.2 × 10⁻¹³ and
  1.7 × 10⁻¹⁴ on price, 4.3 × 10⁻¹⁵ and 1.0 × 10⁻¹⁴ on delta, to the file's own
  tolerances (10⁻¹⁰ and 10⁻⁸, relative above 1); the fresh Q-run as the index's "MC
  agreement". Both QuantLib versions recorded in the JSON (`environment.quantlib`,
  `environment.golden_oracle`).
  D6 fixtures: call and put against S on [40, 200] (step 1) at τ = 1, ½, ¼, 0.05,
  the payoffs, the forward line, N(d₁) and N(d₂) against S; parity holds on the
  curves to 3 × 10⁻¹⁴ and the call sits on or above its payoff everywhere.
  Phi is Hart's rational approximation (West 2005), copied from 2.8's script and
  self-tested against `math.erf` to 2.2 × 10⁻¹⁶; on the page the function is N(·).
- Teaching notes (claude.ai artifact, three versions; archived as
  `teaching-notes.html` beside this file): the opening "what this page is about,
  and what it is trying to achieve", the section-map card, the predictions scored
  with the owner's text verbatim, what ran, then six questions with their tables and
  four canvas figures from the JSON (the Q-density of S_T with the 10⁶-draw
  histogram and the stock-weighted density over the same strike; call, put and the
  forward line against S; the call at four τ over the payoff; N(d₁) and N(d₂)
  against S), the derivation in eleven rungs placed after the numbers (the
  expectation; S_T lognormal; the split at the strike; d₂ born from the inequality;
  d₁ born from completing the square; assembly; why N(d₁) is a probability, the
  delta, and the conditional mean that is not in the price; the put; parity from
  no-arbitrage alone; q and Black-76; the edges), the decisions the owner may
  overrule, draft checks, the ledger batch, the interview plan.
- Owner draft `touchstone-learn/drafts/2.9.md` — interview transcription, nine
  questions (hook; plan; what was done; the integral and its two pieces; what N(d₁)
  and N(d₂) mean; the put and parity; the edges; a dividend yield and Black-76; into
  2.10), all nine answered by the owner in his own words in one burst (sent as one
  file), the six tables placed in the draft with value-path comments. Twelve flags
  raised, all ruled "A" by the owner in-session ("recommendations accepted") and
  applied: F1 max(S_T − K, 0) in place of (·)⁺, as 2.8 wrote it; F2 "they all give
  18.023" (the formulas equal it, only Monte Carlo converges); F3 the grid
  comparison is integral-against-closed-form and the Monte Carlo ran at the base
  case and two yields (I1 — the sentence claimed more than the JSON shows); F4
  "Constitution I4" not named on a reader-facing page; F5 Z glossed, 2.6's exact
  draw and 2.8's r-drift linked; F6 "table A/B" → links to the page's own sections
  (S8's F10); F7 the Monte Carlo estimate named with its error bar; F8 the notes'
  figures 1–3 → the density picture in words, the two price-vs-spot pictures as
  D6's; F9 Black-76's d₁ written out; F10 the simulation agrees within its s.e., the
  formulas to machine precision (I1); F11 gamma is the delta's own sensitivity to
  spot; F12 "already" dropped from D6. About fifty pasted LaTeX runs re-set to the
  course's plain notation across the nine answers, confirmed by the owner in one
  word. Standing rules applied without a ruling: "Geometric Brownian motion (GBM)";
  "Black–Scholes" and "put–call" with the index's en dash; every page reference a
  link (2.8 ×4 with anchors, 2.7 ×2, 2.6 ×1; 2.10 plain); the cumulative normal
  N(·) throughout; drift first. "Into 2.10" previewed, not claimed.
- Checks Q1–Q6 approved by the owner — `touchstone-learn/drafts/2.9-checks.md`:
  one per section (three views; N(d₂); N(d₁); parity; the σ → 0 edge; the dividend
  yield and Black-76 — Q6 offered and kept by the owner's ruling "A").
- Notation ledger S9 batch, 13 rows — `touchstone-learn/drafts/notation.md`,
  approved: N(x) — the cumulative normal ↺ (Φ renamed from this page on, the S6
  ruling); 1{S_T > K} — the indicator of exercise; d₂ — the exercise threshold;
  d₁ = d₂ + σ√T — the threshold after the stock-weighting shift; N(d₂) — the
  risk-neutral probability of exercise; N(d₁) — the share-measure probability of
  exercise, the delta; S₀N(d₁) and Ke^(−rT)N(d₂) — the two pieces; C — the
  Black–Scholes call price; P — the put price; C − P = S₀e^(−qT) − Ke^(−rT) —
  put–call parity; q — the continuous dividend yield; F = S₀e^((r−q)T) — the forward
  price; Black-76 — the formula written in F. The 2.9 mention in the N(x) row is
  plain (the conventions test refuses a link to a tbc page).
- The drafts committed from the session's cloud clone as the owner, on top of L2
  batch 8 follow-up 3 (93ccdb2, which landed during the session — the session's
  first commit attempt fetched, found the branch moved, and stopped, as the
  standing brief says; the drafts were re-based and the 787 tests re-run before the
  second attempt): `touchstone-learn` m/L2 302c7ab, `preview` fast-forwarded to it.
  One test changed in the same commit: `tests/page-2-8.test.ts` froze the S8 ledger
  batch in `drafts/notation.md` as a hash of the text from "## S8 batch" to the end
  of the file, which any later batch breaks; it now stops at the next batch heading,
  with the pinned value unchanged and the page side untouched.

**Decisions (with why)**

- Setup (a) and (b) as the owner ruled at open; the conditional mean
  E^Q[S_T | S_T > K] measured and recorded (140.23 ± 0.06 against 140.30) because the
  owner's P1 reached for it, and the difference between it and the partial
  expectation E^Q[S_T·1{S_T > K}] is the content of N(d₁).
- The oracle in three layers rather than one: a live QuantLib call at the page's
  grid proves the formula against the oracle as it runs today; the generator's
  engine on dates proves it against the conventions the golden file was made with;
  the golden file proves it against the 7,234 numbers the C++ tests use. The JSON
  records both versions (1.43 on the workstation, 1.44 in the container).
- Quadrature by composite Gauss–Legendre, no scipy, so the script's dependencies
  stay numpy and QuantLib (pyproject); done in S as the page writes the integral
  and in z as the derivation does it, so both spellings are checked.
- The grid 3 × 3 × 2 × 2 × 2 × 3 = 216 points; q = 0.03 and 0.08 (the second puts the
  forward below the strike); the limit tables' spots including the two kinks
  (F = K for σ → 0, S₀ = K for T → 0) so the rates are measured, not just the
  limits; 10⁶ fresh draws per q; the 5-s.e. convention; the delta-method s.e. for
  the ratio estimator of N(d₁). Recorded as owner-may-overrule in the notes; none
  overruled.
- `--quick` skips the live oracle and the golden-file comparison with a notice when
  QuantLib or the file is absent, so the learn site's build-time snippet check (I3)
  still runs the script; the full run requires both and fails without them (I4).
- The D6 fixtures carried in the JSON (the index assigns D6 to 2.9–2.10); N(d₁),
  N(d₂) curves included for 2.10's delta.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction, check wiring, the S9 ledger batch onto 0.3 and
  the D6 pricer on the page — L2 batch 9 by design: page 2.9 into the site as
  `draft` on `m/L2`, an Opus/Claude Code session. Once 2.9 routes, the plain "2.9"
  mentions on 2.7, 2.8, the S6 Φ row, the S7 V(t, S) row, the S8 Feynman–Kac row and
  the S9 N(x) row are re-linked at the conventions pass. The anchors in the draft's
  links to 2.8 and 2.6 are L2's to verify.
- The ROADMAP tick for S9 (line 232) — the owner's (I18, P7). Also the owner's, in
  `touchstone`: the stray backslashes in the S5, S7 and S8 pointers on lines 228,
  230 and 231; "riskless must earn r" in the index's §2.7 line and the docstring of
  `experiments/2_7_delta_hedging.py`; the index's §2.6 OU line and §3.2
  importance-sampling line (carried from S6 and S8).
- In `touchstone-learn`, the owner's: the `m/L2` → `main` merge; the workstation
  clone, now one commit behind `origin/m/L2` (302c7ab) — `git pull --ff-only origin
  m/L2` before any local work there. L2 batch 8's pack flags five items of page 2.8
  for the owner's ruling (an Itô-sentence slip in the "why" section, Q4's forward
  parenthesis, Q5's "10⁸ paths", table 6's largest term, nine rounded cells) — the
  batch's thread, not this session's.
- Leftovers the owner may delete: `.git/s7-commit-msg.txt`,
  `.git/s7-interim-commit-msg.txt` and `.git/s8-commit-msg.txt` in `touchstone`.

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at 27fbff5 — commit
  `experiments/2_9_black_scholes_formula.{py,json}` and `docs/evidence/S9/` with the
  supplied message (`.git/s9-commit-msg.txt`), tick S9 (line 232) in `ROADMAP.md`
  with a pointer to this file in the same commit, push. `touchstone-learn`:
  `git pull --ff-only origin m/L2` to pick up 302c7ab. Then L2 batch 9 (2.9 onto the
  preview site with D6), and the next milestone: S10 · 2.10 Greeks, fresh session
  per §7, from the S10 handover in the owner's project — the draft's "Into 2.10"
  (the Greeks as derivatives of the formula derived here; delta already met as
  N(d₁); what each measures and who watches it), the index's §2.10 line, 2.7's
  Δ and Γ, the D6 pricer, and the T-track's golden Greeks (raw partials: vega per
  unit vol, theta per year, rho per unit rate) are its opening material.

## Exit criteria (ROADMAP, track S)

- [x] Experiment script and JSON committed to `touchstone/experiments/` — on the
      owner's disk, uncommitted at close; commit message supplied
      (`.git/s9-commit-msg.txt`).
- [x] Owner's draft page in `touchstone-learn/drafts/2.9.md` — written in the owner's
      words, interview-transcribed, flags ruled "A", "recommendations accepted";
      committed as m/L2 302c7ab.
- [x] Draft checks approved by the owner — Q1–Q6, `drafts/2.9-checks.md`.
- [x] Draft reviewed against I1 — twelve flags, all ruled and applied (two of them
      I1 corrections: F3, F10); every quantitative sentence mapped to
      `2_9_black_scholes_formula.json` in the review (claim map in the draft's
      footer).
- [ ] ROADMAP tick — the owner's (I18).

## Files

- `touchstone/experiments/2_9_black_scholes_formula.py`, `.json` (91 checks, seed 20261105)
- `touchstone/docs/evidence/S9/summary.md` (this file), `teaching-notes.html` (v2, close)
- `touchstone-learn/drafts/2.9.md`, `2.9-checks.md`, `notation.md` (S9 batch appended),
  `tests/page-2-8.test.ts` (the S8 hash bounded) — m/L2 302c7ab
