# S8 — Teaching session · page 2.8 Risk-neutral pricing · evidence pack

### 2026-11-04 · claude-fable-5-1 · S8 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved

Work order (P3): teach 2.8 per constitution §7, numbers before theory. Inputs: index
§2.8 (V = e^(−rT)·E^Q[payoff]; drift becomes r; Girsanov as reweighting paths, not
changing volatility; Feynman–Kac ties the expectation to the PDE; check: Monte Carlo
under Q matches the PDE, discounted MC under the real-world drift does not), the S8
handover in the owner's project, `drafts/2.7.md`'s "Into 2.8" (price as if the stock
drifted at r; Feynman–Kac named, not proved; the experiment: MC under the r-drift
matches the PDE price, under μ it does not), 2.7's hedged-book result (μ absent from 64
rebalances a year), 2.6's exact draw of S_T, 2.5's exponential martingale, the owner's
predictions. Outputs: numpy experiment + JSON in `touchstone/experiments/`; owner draft
in `touchstone-learn/drafts/2.8.md`; checks drafted by Fable, approved by the owner; S8
batch appended to the notation ledger; draft reviewed against I1. Session opened and
closed 2026-11-04 on the Windows workstation, the drafts committed from the session's
cloud clone.

**Setup decisions (owner, 2026-11-04, before any code).** (a) The "PDE price" the Monte
Carlo is compared against is the closed form, which 2.7 checked against the PDE at
10⁻¹⁵ on a grid and 2 × 10⁻¹³ at every point its hedges visited; 2.9 derives it. (b)
Girsanov is measured, not quoted: the μ-paths are reweighted by the likelihood ratio and
must reproduce the Q-price, with the paths' realised volatility unchanged.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and answers
  recorded verbatim at the top of the notes. P1 "above by 3.34%" (right on direction;
  3.34 is the closed-form gap e^(−rT)·E^P[payoff] − V = 3.337 in price units — 18.5 % of
  18.02, not 3.34 %; measured 3.40 ± 0.03); P2 "yes because replacing μ with r changes
  the distribution to the risk-neutral one, and the discounted expectation becomes the
  unique no-arbitrage price" (right — 18.010 ± 0.031, 0.4 s.e. from 18.023; the why names
  the result, the page's reason is 2.7's hedge); P3 "yes on the price, no on the
  expected payoff" (right, both); P4 "martingale" (right under Q; the second half,
  under the real-world drift, unanswered — a submartingale at μ = 0.3, a supermartingale
  at −0.2); P5 "no and no", the first clarified as "no to all" (volatility — right;
  drift — wrong, the weights move it; weight — wrong, it is exactly what changes; and
  reweighting does give the same price). P4's second half and P5 are the page's target
  misconceptions (check distractors Q3, Q4); P1's trap is Q1's.
- `experiments/2_8_risk_neutral_pricing.py` + `.json` — claims C1–C5, 131 checks pass,
  seed 20261104, 5.1 s on the Windows workstation (`uv run --frozen`, Python 3.12.15,
  numpy 2.5.2); the container run (numpy 2.5.3) agrees to every printed digit, the
  largest difference among non-rounding values 9 parts in 10¹¹; `--quick` 0.4 s.
  Parameters S₀ = K = 100, r = 0.05, σ = 0.4, T = 1; V = 18.023, the forward 4.877.
  S_T drawn exactly (2.6's decision 1), never Euler; paths stepped exactly where needed.
  C1 (10⁶ draws at μ = −0.2, 0, 0.05, 0.1, 0.3, 0.6): discounted mean payoff 6.77, 15.11,
  18.01, 21.42, 38.96, 79.64 (± 0.02–0.07) against the closed form under μ (within 5
  s.e. in every row), the gap to the price −11.25, −2.92, −0.01, +3.40, +20.93, +61.62 —
  −622, −103, −0.4, +99, +439, +877 s.e. — increasing with μ; E[S_T] = S₀e^(μT) in every
  row; the forward's discounted mean S₀e^((μ−r)T) − Ke^(−rT), equal to 4.877 only at
  μ = r (4.86 ± 0.04).
  C2 (the Q-run): nested estimates 18.22 ± 0.95, 18.35 ± 0.31, 18.06 ± 0.10,
  18.010 ± 0.031 at n = 10³ … 10⁶ (0.2, 1.1, 0.4, 0.4 s.e.); batches of 100, 1,000 and
  10,000 draws (10,000, 1,000, 100 batches): rms error 3.16, 0.975, 0.298 against the
  reported sd/√n 3.12, 0.988, 0.312; slope −0.512; the forward 4.19 / 1.29 / 0.385
  against 4.16 / 1.32 / 0.416, slope −0.519; E^Q[S_T] = 105.11 ± 0.04 against 105.13.
  C3 (10⁵ paths × 256 exact steps at μ = r, 0.3, −0.2): E[e^(−rt)S_t] = 99.98 ± 0.06,
  100.00 ± 0.09, 99.99 ± 0.11, 100.01 ± 0.13 at t = ¼, ½, ¾, 1 under Q with sd 20.2,
  28.9, 35.7, 41.8 (S₀√(e^(σ²t) − 1) to 3 %); 106.50, 113.45, 120.85, 128.65 (± 0.07–0.17)
  at μ = 0.3 and 93.89, 88.14, 82.86, 77.81 at −0.2, each within 5 s.e. of S₀e^((μ−r)t)
  and 96–215 s.e. from S₀; path by path e^(−rt)S_t = S₀·e^(σW̃_t − ½σ²t) to 5.7 × 10⁻¹³.
  C4 (Girsanov on C1's own draws, L = e^(−λW_T − ½λ²T), λ = (μ − r)/σ): reweighted prices
  18.11 ± 0.07, 18.05 ± 0.04, 18.07 ± 0.03, 18.00 ± 0.01, 18.05 ± 0.01 at μ = −0.2, 0,
  0.1, 0.3, 0.6 (worst 2.8 s.e.); the reweighted forward within 5 s.e. of 4.877; mean
  L = 1 within 5 s.e.; mean L² = e^(λ²T) within 5 s.e.; ESS/n = 0.676, 0.985, 0.984,
  0.677, 0.158 against e^(−λ²T) = 0.677, 0.985, 0.985, 0.677, 0.151; the in-the-money
  share 24.3 %, 42.2 %, 52.0 %, 70.8 %, 90.4 % of paths → 47.0–47.2 % of weight against
  Φ(d₂) = 0.4701. On the stepped paths: mean log-return 0.222 → −0.029 (μ = 0.3) and
  −0.281 → −0.031 (−0.2) against (r − ½σ²)T = −0.030; realised vol 0.3999 → 0.3994 and
  0.4000 → 0.3998 (realised variance within 5 s.e. of 0.16, weighted and unweighted);
  the reweighted discounted stock 99.75–99.98 at every checkpoint. Found, not
  predicted: the s.e. of the reweighted price is 0.073, 0.037, 0.027, 0.015, 0.009
  against the Q-run's 0.031 — importance sampling; asserted only as the ordering
  (μ = 0.3 below the Q-run, −0.2 above).
  C5 (Feynman–Kac in numbers): V_MC(t, S) on S = 50 … 200 (16 points) at τ = 1 and ½,
  10⁶ common draws per point, within 1.7 s.e. (τ = 1) and 0.3 s.e. (τ = ½) of the closed
  form at every point; the PDE residual on V_MC by central differences (h = 2 %) rms
  0.044 and 0.026 (max 0.083, 0.056) against the closed form's own finite-difference
  residual 0.0016 and 0.0033 and the replication noise 0.052 and 0.033; under 1 % of the
  PDE's largest term (rms 5.19, 6.27); the analytic residual 1.8 × 10⁻¹⁵.
  numpy has no erf: Φ is Hart's rational approximation (West 2005), copied from 2.7's
  script and self-tested against `math.erf` to 2.2 × 10⁻¹⁶ before anything runs.
- Teaching notes (claude.ai artifact, four versions; archived as `teaching-notes.html`
  beside this file): an opening "what this page is about" section added at the owner's
  request ("wtf this page is actually about"), the section-map card, predictions scored,
  what ran, then the three questions a developer writing a Monte Carlo pricer asks
  (which drift; how many paths and how you know; whether paths at another drift can be
  reused), each with its table and a canvas figure from the JSON (the discounted mean
  against μ with the closed-form curve and the reweighted points; rms error against n
  log-log for the call and the forward; the S_T histograms of the Q-run, the μ = 0.3 run
  and the μ = 0.3 run reweighted; E[e^(−rt)S_t] against t at three drifts with the
  reweighted means); the bridge from 2.7's hedge to V = e^(−rT)·E^Q[payoff] in six rungs
  (2.7's result; pick the drift; the exponential martingale; the expectation and
  Feynman–Kac; Girsanov as the weight; why "risk-neutral"), placed after the
  measurements; the martingale and the PDE on the numbers; draft checks; the ledger
  batch; the interview plan. The owner's question in review, "what is Girsanov", was
  answered in the chat as the discrete argument (the per-step probability ratio
  1/(1 ± λ√dt), its log −λΔW − ½λ²dt by 2.5's second-order move, summed to
  −λW_T − ½λ²T) and offered for rung 5. The owner's "computing using Monte Carlo
  only?" fixed the framing: the page is about the pricing principle, with Monte Carlo as
  the one evaluator the page runs, the formula (2.9) and the grid (3.3) the other two.
- Owner draft `touchstone-learn/drafts/2.8.md` — interview transcription, nine questions
  (hook; plan; what was done; which drift; how many paths; reuse; why — from the hedge
  to the expectation; the martingale and the PDE checked; into 2.9), all nine answered
  by the owner in his own words in one sitting, the five tables placed in the draft with
  value-path comments. Eleven flags raised, all ruled by the owner in-session and
  applied: F1 "risk-free" is the course's term for r, ruled course-wide ("riskless"
  retired; the page says risk-free throughout, the rest of the course changes in L2
  batch 7 follow-up 2); F2 "B" the plan's three questions as bold run-in lines, the
  owner's sentences turned into questions; F3 "A" "and the terminal condition" dropped —
  2.7 measured the PDE residual only (applied again in "Into 2.9"); F4 "B" "across the
  whole surface" → "across a grid of (t, S)"; F5 "A" "Geometric Brownian motion (GBM)"
  written out at first use; F6 "A" "Each pricer reports a standard error of 0.312" kept,
  the claim map noting the figure is sd/√n from the full run; F7 "A" importance sampling
  "which 3.2 takes up with the other variance-reduction methods"; F8 "B" Φ(d₂) not
  written on this page (the S6 ruling: N(·) from 2.9 on, Φ only on 2.6) — "the
  risk-neutral probability of finishing in the money, 47.0 %"; F9 "B" "essentially
  unchanged" → "unchanged to one part in a thousand"; F10 "A" the section references
  §5/§6 replaced by links to the page's own sections; F11 "A" "two maturities" → "two
  times to expiry, τ = 1 and ½". Twenty-four pasted LaTeX runs re-set to the course's
  plain notation across the nine answers, each confirmed by the owner. "Into 2.9"
  previewed, not claimed. "approved" 2026-11-04.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.8-checks.md`: one per
  question on the page (the drift; the error law with Feynman–Kac as its last
  distractor; reweighting), one for the martingale from both sides, one for the why.
- Notation ledger S8 batch, 13 rows — `touchstone-learn/drafts/notation.md`, approved:
  P — the real-world measure; Q — the risk-neutral measure; E^Q[·]; V = e^(−rT)·E^Q[payoff]
  — the pricing formula; the r-drift; W̃ — the Q-Brownian motion; λ = (μ − r)/σ — the
  market price of risk; L — the likelihood ratio, Girsanov's weight; Girsanov's theorem;
  Feynman–Kac; s.e. = sd/√n ↺; ESS = n·e^(−λ²T); e^(−rt)S_t — the discounted stock, a
  Q-martingale ↺. Symbol and name divided by a dash.
- L2 batch 7 follow-ups, run from this session's cloud clone because the owner's
  workstation clone was behind `origin/m/L2`: follow-up 1 (the mirror of the batch-7
  rulings into the 2.7 page, checks and test) turned out to have landed from the S7
  session at 06:50 as 2778a91, ten minutes after this session's opening check; the
  Opus agent spawned here for it made the same changes, ran 566 tests and both builds
  clean, found `origin/m/L2` moved and stopped without committing, as briefed. Its one
  finding — three header cells the draft carried beyond the page it was copied from —
  was ruled "A" by the owner (the page as reviewed stands) and applied with the S7
  ledger row's "agree within five s.e." as e1fff81 (drafts only). Follow-up 2 (the
  course-wide "risk-free" pass across drafts, pages and tests; the five-s.e. mirror to
  the 0.3 ledger; the cell-for-cell page-against-draft table test) was spawned at
  21:56 as an Opus agent — its result is in `docs/evidence/L2/batch-7/follow-up-2/` in
  `touchstone-learn`, not here.

**Decisions (with why)**

- Setup (a): the closed form as the PDE's solution, said plainly in "what was done" with
  the one sentence that makes the borrowing honest (2.7 checked it against the PDE).
  Without it C1's "matches the PDE" has no fixed target; solving the PDE on a grid is
  3.3's.
- Setup (b): Girsanov measured. The index's "reweighting paths, not changing volatility"
  became two numbers (the weighted drift −0.029 against −0.030; the weighted realised vol
  0.3994 against 0.3999) and a histogram that lies on the Q-run's bin for bin.
- The six drifts, with 0.6 included to show the cost of a large |λ| (ESS 16 %); 10⁶
  exact draws (the price to ±0.03); 10⁵ stepped paths on 256 steps; the batches at
  n = 100, 1,000, 10,000 so each has at least 100 batches (the rms-vs-s.e. check's
  tolerance is 5/√(2B)); the surface at 16 × 2 points with h = 2 % and two replications
  to measure the noise — recorded as owner-may-overrule in the notes; none overruled.
- The s.e.-ratio finding (reweighting towards the payoff beats the Q-run) is asserted
  as an ordering only and stays an aside on the page, because its explanation is
  importance sampling, which the index gives to 3.2 under variance reduction.
- The 5-s.e. convention for means; the batch rms within 5 s.e. of an rms estimated from
  B batches; ESS within a delta-method 5 s.e.; the C5 residual bounded by the closed
  form's FD residual plus 5 × the replication noise and by 2 % of the largest term;
  `--quick` widens by √10. 131 checks.
- "Risk-free", not "riskless", from this page on and across the course — the owner's
  ruling, with the reasoning that it is the term desks and the standard texts use; the
  S8 ledger records it.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction, check wiring — L2 batch 8 by design: page 2.8
  into the site as `draft` on `m/L2`, an Opus/Claude Code session. No demo is assigned
  to the page; fixtures the site could draw are named in the draft's STATUS comment.
  The in-page anchors and the 2.5 anchor in `drafts/2.8.md` follow the conventions
  pass's slugging and are L2's to verify.
- The ROADMAP tick for S8 (line 231) — the owner's (I18, P7). Also the owner's, in
  `touchstone`: the stray backslashes in the S5 and S7 pointers on lines 228 and 230
  (`\docs/evidence/S5/summary.md`, `\docs/evidence/S7/summary.md`); "riskless must earn
  r" in the index's §2.7 line (and the matching summary line in the site's
  `curriculum.ts`, which mirrors it) and the docstring of
  `experiments/2_7_delta_hedging.py` — the course's term is now "risk-free"; the index's
  §3.2 line if importance sampling is to join antithetics and control variates there;
  the index line "mean reversion (OU) as a second example" under §2.6 (carried from S6).
- In `touchstone-learn`, the owner's: the `m/L2` → `main` merge; the workstation clone,
  behind `origin/m/L2` since 2bfcc65 — `git pull --ff-only origin m/L2` before any
  local work there.
- Leftovers the owner may delete: `.git/s6-interim-commit-msg.txt` and
  `.git/s7-interim-commit-msg.txt` in `touchstone`.

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at dd0ee6b — commit
  `experiments/2_8_risk_neutral_pricing.{py,json}` and `docs/evidence/S8/` with the
  supplied message (`.git/s8-commit-msg.txt`), tick S8 (line 231) in `ROADMAP.md` with a
  pointer to this file in the same commit, push. `touchstone-learn` `m/L2`: the drafts
  (`drafts/2.8.md`, `drafts/2.8-checks.md`, `drafts/notation.md`) are committed from the
  session's cloud clone as the owner, on top of follow-up 2; pull on the workstation.
  Then L2 batch 8 (2.8 onto the preview site), and the next milestone: S9 · 2.9 The
  Black–Scholes formula, fresh session per §7, from the S9 handover in the owner's
  project — the draft's "Into 2.9" (the lognormal integral; N(d₁), N(d₂) emerging from
  the algebra; the formula derived from the expectation), the index's checks (parity,
  σ → 0 and T → 0 limits, MC agreement), and 2.8's Q-run (18.010 ± 0.031) and in-the-money
  mass (47.0 % = Φ(d₂)) are its opening material.

## Exit criteria (ROADMAP, track S)

- [x] Experiment script and JSON committed to `touchstone/experiments/` — on the owner's
      disk, uncommitted at close; commit message supplied (`.git/s8-commit-msg.txt`).
- [x] Owner's draft page in `touchstone-learn/drafts/2.8.md` — written in the owner's words,
      interview-transcribed, "approved".
- [x] Draft checks approved by the owner — Q1–Q5, `drafts/2.8-checks.md`.
- [x] Draft reviewed against I1 — eleven flags, all ruled and applied; every quantitative
      sentence mapped to `2_8_risk_neutral_pricing.json` in the review (claim map in the
      draft's footer).
- [ ] ROADMAP tick — the owner's (I18).

## Files

- `touchstone/experiments/2_8_risk_neutral_pricing.py`, `.json` (131 checks, seed 20261104)
- `touchstone/docs/evidence/S8/summary.md` (this file), `teaching-notes.html` (v3)
- `touchstone-learn/drafts/2.8.md`, `2.8-checks.md`, `notation.md` (S8 batch appended)
- `touchstone-learn/drafts/2.7.md`, `notation.md` — the owner's rulings of 2026-11-04 on
  the batch-7 follow-up (e1fff81) and the course-wide "risk-free" pass (follow-up 2)
