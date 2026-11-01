# S6 — Teaching session · page 2.6 SDEs and geometric Brownian motion · evidence pack

### 2026-11-01 · claude-fable-5-1 · S6 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved

Work order (P3): teach 2.6 per constitution §7, numbers before theory. Inputs: index
§2.6 (dS = μS dt + σS dW; solve via log S; the −½σ² correction, mean vs median, volatility
drag; exact sampling vs Euler–Maruyama; where the √dt comes from; mean reversion (OU) as a
second example; check: Gaussian log-returns, E[S_T] = S₀e^(μT), Euler error vs dt,
spot-the-bug σZ·dt), experiments/README, the S5 evidence pack, the S6 handover in the
owner's project, `drafts/2.5.md`'s "The general form, and log S" and "Into 2.6", 2.5's
E[e^(W_t)] = e^(t/2), 2.3's Σ(ΔW)² → T, 2.2's W_T = √T·Z, 2.1's √dt, the owner's
predictions. Outputs: numpy experiment + JSON in `touchstone/experiments/`; owner draft in
`touchstone-learn/drafts/2.6.md`; checks drafted by Fable, approved by the owner; S6 batch
appended to the notation ledger; draft reviewed against I1. Session opened 2026-10-01 and
ran across 2026-10-01 … 11-01 in five sittings on two machines (the Windows workstation,
the owner's Mac for one review sitting, then the workstation); the container behind the
session was replaced once and the notes were recovered from the published artifact.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and answers
  recorded verbatim at the top of the notes. P1 "equal to S₀; median of S_T = T", clarified
  on F1 as "median is below" (right on both: E[S_T] = S₀, median S₀e^(−½σ²T) = 0.92 S₀);
  P2 "about 0.1 %?, the gap shrinks 100x" (wrong on both: 1.15 % rms at n = 100, 10× for
  100× the steps — the page's target misconception, check distractors Q3); P3 "too big by
  100 times" (factor right, direction wrong: too small — Q5's distractor); P4 "Gaussian,
  mean (μ − ½σ²)T" (right); P5 "stops at sqrt(t) - a guess" ("stops" right; at σ²/(2θ) =
  0.04, a constant — parked with OU).
- `experiments/2_6_sdes_and_gbm.py` + `.json` — claims C1–C5, 121 checks pass, seed
  20261001, 89 s on the Windows workstation (`uv run --frozen`, Python 3.12.14, numpy
  2.5.2); the container run on numpy 2.4.4 agrees to every printed digit, the largest
  difference 7 parts in 10⁸ of a 10⁻⁹ residual; `--quick` about 9 s. Parameters S₀ = 100,
  μ = 0.1 (working case) and μ = 0 (the owner's P1 case), σ = 0.4, T = 1.
  C1 (exact sampling, 10⁶ paths, one normal each): log-return mean 0.0198 ± 0.0004 against
  (μ − ½σ²)T = 0.02, variance 0.1596 against 0.16, skewness −0.005 ± 0.002, excess kurtosis
  +0.001 ± 0.005; E[S_T] = 110.47 ± 0.05 against 110.52, median 102.05 ± 0.05 against
  102.02, 57.9 % of paths below the mean against Φ(0.2) = 0.579; the drag
  E[log S_T] − log E[S_T] = −0.0798 ± 0.0004 against −0.08. μ = 0: mean 100.02 ± 0.04,
  median 92.30 ± 0.05 against 92.31.
  C2 (1,000 paths drawn once at 10⁶ steps, read on n = 10² … 10⁶; Euler against the exact
  solution on the same increments): rms relative gap in S_T 1.150 %, 0.361 %, 0.109 %,
  0.034 %, 0.012 % against ½σ²T√(2/n), slope −0.501; gap mean 0 within s.e. on every grid
  (−0.02 % ± 0.04 % at n = 100); path 1 at n = 100: Σ(ΔW)² = 1.438, gap −3.42 %. 20,000
  Euler paths at n = 10⁴ with no closed form in the simulation: mean log-return
  0.0211 ± 0.0028 against 0.02 (μT = 0.1 is 28 s.e. away), E[S_T] = 110.62 ± 0.32, median
  101.99 ± 0.36; μ = 0: 100.15 ± 0.30 and 92.55 ± 0.33.
  C3 (the σZ·dt step on the same grids): realised volatility σ√dt — 0.0399, 0.0127, 0.0040,
  0.00126, 0.00040 against the correct step's 0.3997 … 0.4000, slope −0.500; sd of
  log S^bug_T 0.0385 … 0.000385 against 0.40; the sum-of-squares realised volatility of the
  buggy path reads √(σ² + μ²)√dt because the drift becomes kick-sized (0.0410 against 0.0412
  at n = 100).
  C4 (the Euler gap decomposed): gap in log S minus −½σ²(Σ(ΔW)² − T) has rms 5.7 × 10⁻⁴ …
  5.7 × 10⁻⁸, slope −1.001; path 1 at n = 100: −0.0350 against the measured −0.0348; the
  (ΔS)²-form Taylor remainder along the Euler path has slope −1.002; ⅓Σx³ has sd matching
  σ³√15·T^(3/2)/(3n) to 3 %. 2.5's lemma measured for the first time with a ≠ 0, b ≠ 1.
  C5 (OU, θ = 2, σ = 0.4, X₀ = 1, 20,000 paths at n = 10⁴): mean X₀e^(−θt) within 2 s.e. at
  five checkpoints; Var(X_t) 0.0132, 0.0252, 0.0343, 0.0377, 0.0395 against
  σ²(1 − e^(−2θt))/(2θ), limit 0.04; Var(W_t) = t on the same normals; Euler against the
  exact OU step 3 × 10⁻⁵ rms. In the JSON, not on the page.
- Teaching notes (claude.ai artifact, five versions; archived as `teaching-notes.html`
  beside this file): section map card, predictions, the bridge from 2.5's d(log S) line to
  the solution in six rungs, then — after the owner's "most of this, I'm a bit so what —
  sections 3 onwards" at v1 — a re-cut around the three decisions a developer makes with the
  model (draw or step; if step, how many; how to know it is right), two canvas figures from
  the JSON (path 1 at n = 100, three methods; the S_T histogram with mean and median), draft
  checks, the ledger batch, the interview plan. Two corrections from the owner's review
  questions: "nobody sees the median" (the mean/median/mode distinction, and that the median
  carries through exp while the mean does not), and "we would never hedge just one path"
  (the stepping rule rewritten as means-ignore-it-spreads-keep-it, and the page made to say
  that GBM steps exactly, S_{i+1} = S_i·e^((μ − ½σ²)dt + σΔWᵢ), so Euler is the fallback
  for models with no solution and GBM is where its cost can be measured).
- Owner draft `touchstone-learn/drafts/2.6.md` — interview transcription, nine questions
  (hook; plan; what was done; decision 1 — draw S_T directly; decision 2 — if you step, know
  what it costs; decision 3 — test the simulator; solving the SDE; why the mean and the
  median differ; into 2.7). The plan section "What this page shows, and how" drafted by
  Fable at the owner's request and accepted as it stood — the one Fable-written passage on
  the page, marked in place (F2; I2 exception at the owner's instruction, as 2.5's F35).
  Seventeen flags raised, all ruled by the owner in-session and applied: one sentence
  appended to the hook, proposed and accepted (F1); seven notation re-sets after pastes
  stripped superscripts, fractions, roots and — twice — the S₀ from the log lines (F5, F8,
  F10, F11, F13, F15, F17); wording and consistency rulings (F3 the closed form's place in
  the 20,000-path run; F4 "the same seeded experiment"; F6 and F16 "typical path" → "the
  point a single path is as likely to finish above as below"; F9 E[S^E_T] = S₀(1 + μ dt)ⁿ
  added in brackets; F12 the grid-independence sentence; F14 ½b²f″(S) → ½b²·∂²f/∂x² to match
  2.5); the owner's standing instruction that GBM is written out as "Geometric Brownian
  motion (GBM)" at first use on every page (F7). Three tables built from the JSON with
  value-path comments; snippet slot naming `exact_at_T`, `grid_sums`, `euler_many`; claim
  map in the footer, fourteen entries; "Into 2.7" previewed not claimed. Every table value
  re-checked against the JSON on the owner's disk after assembly.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.6-checks.md`: one per
  decision plus the −½σ² from both sides (Q2 prices the forgotten drag; Q4 is
  means-vs-spreads).
- Notation ledger S6 batch, 11 rows — `touchstone-learn/drafts/notation.md`, approved: SDE;
  GBM; solve; the closed-form sample; Euler–Maruyama; the stepping error (means ignore it,
  spreads keep it); −½σ² · volatility drag; mean vs median (lognormal); log-return;
  √dt in the step ↺; realised volatility · the three tests.
- Not S6's to do, recorded for the owner: the ROADMAP tick for S5 (line 228) was never
  made — 2b4677b's message says "ROADMAP ticked" but the file still reads ☐ S5; the index
  line "mean reversion (OU) as a second example" under §2.6 is the owner's to drop (I18)
  if the Decision below stands.

**Decisions (with why)**

- μ = 0.1 for the page's working case rather than the P1 question's μ = 0, so that the
  drift is visible in every table and 2.5's general form is measured with a ≠ 0; the owner's
  μ = 0 case is run beside it in C1 and in the 20,000-path Euler run. S₀ = 100.
- The page is cut around three developer decisions, not around the five claims. The owner's
  reaction to v1 was "so what" from §3 on; every section now opens with what it decides and
  the material that served no decision went to the claim map (the (ΔS)²-form remainder
  columns, the cubic term's sd).
- Mean reversion (OU) is in the JSON (C5) and off the page — Decision, owner may overrule.
  Nothing in v1 (European vanillas, constant vol, I21) uses it; it would be a fourth section
  with no decision attached. The JSON keeps C5 so the index line can be honoured later
  without a rerun.
- The stepping rule is "means ignore it, spreads keep it", not "a price barely feels it, a
  hedge feels all of it": the owner pointed out that no one hedges one path. A hedging
  simulator follows many paths and reads their P&L spread; a zero-mean noise cancels out of
  a mean and adds to a variance. And GBM itself never needs Euler — the solution holds
  between grid points — so 2.7 steps exactly, and Euler's √dt error is taught here because
  GBM is the one model where it can be measured against the truth.
- "The price you will probably see" was wrong and is gone: the median is the point a single
  path is as likely to finish above as below, not a price anyone observes. In log space mean
  and median coincide; the median survives the exponential and the mean does not.
- The realised-volatility test uses the demeaned per-step sd, √(n/T)·sd(rᵢ), because on the
  buggy path the drift μ dt is kick-sized and the sum-of-squares version reads
  √(σ² + μ²)√dt; both are in the JSON and the page uses the one that isolates σ.
- Checks compare to 5 s.e. from the sample where the sample sets the tolerance (C1's four
  moments, C2's gap mean, C5's means and variances) and to 15 % relative where a closed-form
  rms is compared with a 1,000-path estimate; the gap-vs-remainder ratio is checked against
  2/√n. 121 checks; `--quick` widens by √(1000/n_paths).
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction (`exact_at_T`, `grid_sums`, `euler_many`), check
  wiring, demo D4 — L2 batch 6 by design: page 2.6 into the site as `draft` on `m/L2`, an
  Opus/Claude Code session. The link anchors in `drafts/2.6.md` follow the conventions
  pass's slugging and are L2's to verify against the rendered headings.
- The ROADMAP ticks for S5 (line 228, missed at S5 close) and S6 (line 229) — the owner's
  (I18, P7).
- The index edit dropping OU from §2.6 — the owner's, if the Decision stands.
- Leftovers the owner may delete: `.git/s6-interim-commit-msg.txt` in `touchstone` (the
  interim commit was never made; the closing message supersedes it).

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at 8494711 — commit
  `experiments/2_6_sdes_and_gbm.{py,json}` and `docs/evidence/S6/` with the supplied message
  (`.git/s6-commit-msg.txt`), tick S5 (line 228) and S6 (line 229) in `ROADMAP.md` with
  pointers to the evidence packs in the same commit, push. `touchstone-learn` on `m/L2` at
  508c5e9 — commit `drafts/2.6.md`, `drafts/2.6-checks.md`, `drafts/notation.md` with the
  supplied message (`.git/s6-commit-msg.txt`), push; merge `m/L2` into `main` when L2's
  conventions pass is accepted, so the drafts live on `main` as 2.1–2.5's do. Then L2 batch
  6 (2.6 onto the preview site). Next milestone: S7 · 2.7 Delta hedging and the Black–Scholes
  PDE, fresh session per §7, from the S7 handover in the owner's project — the draft's "Into
  2.7", the general form on V(t, S) with a = μS and b = σS, the exact GBM step for the
  simulator, and the means-vs-spreads rule for the P&L distribution are its opening
  material; the index's 2.7 check is "hedging simulator — P&L spread falls as 1/√N with
  rebalance count N".
