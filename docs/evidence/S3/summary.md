# S3 — Teaching session · page 2.3 Quadratic variation · evidence pack

### 2026-09-06 · claude-fable-5-1 · S3 taught; experiment committed; owner draft written, reviewed against I1, checks and notation batch approved

Work order (P3): teach 2.3 per constitution §7, numbers before theory. Inputs: index
§2.3, experiments/README, S2 evidence pack, the closing paragraph of `drafts/2.2.md`
and the ledger's ΔW/dW rows (opening material), owner's predictions. Outputs: numpy
experiment + JSON in `touchstone/experiments/`; owner draft in
`touchstone-learn/drafts/2.3.md`; checks drafted by Fable, approved by the owner; S3
batch appended to the notation ledger; draft reviewed against I1. Session opened
2026-09-06 from the S3 handover written by a Fable session that lost the device link;
the link held this time (one drop mid-session, recovered on its own).

**Done**

- Predict-then-run: five gut predictions captured before any code. P1 "settles on 1"
  (right), P2 "a number, 1" for Σ|ΔW| (wrong: ∞ like √n), P3 "they are the same"
  (right, to 0.0014 at n = 10⁶), P4 "Σ(Δf)² looks like sin²(2πt)" (wrong: both are
  numbers, 0 and 4 — the sum read as a curve), P5 "Σ ΔW·Δt → 1 and Σ(Δt)² → 1" (wrong:
  both → 0 like 1/n). P2, P4, P5 are check distractors Q2, Q3, Q4.
- `experiments/2_3_quadratic_variation.py` + `.json` — claims C1–C5, 59 checks pass,
  seed 20260906, 40 s on the owner's machine. Written in the session container (numpy
  2.4.4), run on the owner's machine via `uv run --frozen` (numpy 2.5.2): every sum,
  mean and sd agrees to the last digit; only `polyfit`/`corrcoef` outputs differ in
  the 16th significant figure (BLAS). C1 Σ(ΔW)² mean 1.003, 0.998, 1.000, 1.000, 1.000
  at n = 10² … 10⁶ with sd 0.150, 0.0441, 0.0143, 0.00436, 0.00139 against T·√(2/n)
  (slope −0.507), every one of 400 paths within 3.5 sd of T, single-term relative sd
  1.414, corr(Σ(ΔW)², W_T) = −0.007 on a separate 20,000-path run; C2 Σ|ΔW|/√(nT) =
  0.798 at every n, slope +0.4999; C3 n·Σ(Δf)² = 19.74 at every n (slope −1.000),
  Σ|Δf| = 4.000; C4 rms Σ ΔW·Δt = 0.967/n (slope −1.000), Σ(Δt)² = 1/n, Σ|ΔW|³ =
  1.596/√n (slope −0.500); C5 coin walk Σ(ΔW)² = T to 4 × 10⁻¹⁶, Σ|ΔW|/√(nT) = 1.
- Design decision in the script: paths are drawn once at n = 10⁶ and coarsened by
  10 at a time, so the five rows are the same path on five grids (coarse increments
  are sums of fine ones, so each coarsening is exactly Brownian). The page says so.
  Chunk size is memory-only: draws are consumed row by row, verified by rerunning
  with chunk 5 vs 20 — JSON identical except the recorded parameter.
- Teaching notes (claude.ai artifact, eleven sections plus the notation batch, three
  canvas figures, six tables) — archived as `teaching-notes.html` beside this file.
  Iterated in-session more heavily than S1 or S2: §3 rewritten four times (units of
  dt carried through; the "141 %" phrasing dropped; mean/variance bullets; the
  mechanism paragraph cut to four sentences at the owner's request); asides added
  for what squaring does to a Gaussian (with a χ²₁ density figure), for E|Z| =
  √(2/π), for the calculus of sin(2πt) (chain rule spelled out), and for the two
  words in the title; §7 rewritten around the exact g = x² identity before the
  general Taylor series; a max|W| column added when the footnote referred to a
  number not in the table.
- Owner draft `touchstone-learn/drafts/2.3.md` — interview transcription, ten
  questions plus one follow-up (Q8b, the general Taylor line). I2 held: every page
  sentence is the owner's, including the hook. Thirty-six review flags raised, the
  substantive ones ruled by the owner mid-interview: F2 max|ΔW| dropped (not in the
  JSON); F3 "Σ ΔW should stay near 0" dropped (it is W_T); F8 "same path, five
  grids"; F13 sd formula 2/√n → √(2/n) (numbers were right, formula was not); F14
  variance-vs-sd in the closing; F16 "mean becomes closer to 1" → "mean stays at 1";
  F23 coin |ΔW| = √dt; F28 cross term is exactly dt·W_T, → 0 like 1/n, not T·√dt
  (slope −1 in the JSON, not −½); F30 "only (dW)² survives" → the five-line
  rulebook with Σ ΔW = W_T (random) alongside Σ dt and Σ(ΔW)² (deterministic);
  F7 keep, F10 reword ("running total" → total over [0, T] in the limit), F25 add
  19.74/n. Typos applied silently. Claim map in the draft's footer, 16 entries each
  pointing at a JSON field; the draft claims nothing about ∫W dW beyond "short by T".
- Checks Q1–Q5 approved by the owner unchanged — `touchstone-learn/drafts/2.3-checks.md`.
  Q5 is the Taylor version; the coin alternative was offered and not taken.
- Notation ledger S3 batch, 18 rows — `touchstone-learn/drafts/notation.md`; approved
  by the owner. Most rows were born from the session's own questions: Z² / χ²₁
  (mean 1, variance 2 from E[Z⁴] = 3; not N(1, 2)); χ²ₖ; [a, b) and [0, ∞); [W]_T;
  quadratic vs total variation; the rulebook's "= 0"; f′ vs f″ vs a quote mark; the
  chain rule; the three integrals of f′; φ(z); E|Z|; odd moments; log-log slopes;
  Taylor. The owner asked for the squared-Gaussian fact to be on the site, then
  chose the ledger over a page subsection.

**Decisions (with why)**

- Correlation of Σ(ΔW)² with max|W| is reported and bounded (|ρ| < 0.05), not
  asserted zero: it is positive of order 1/√n (bigger kicks, bigger excursions).
  Correlation with W_T is checked at zero (|ρ| < 0.03) because E[(ΔW)³] = 0 exactly.
  A 20,000-path run at n = 10⁴ exists only to pin these; 400 paths give ±0.05.
- Σ|ΔW|³ measured and a fourth rulebook line, (dW)³ = 0, shown in the notes: not in
  the index, but it is why the Taylor argument stops at second order and 2.4 needs it.
- "Infinite total variation" and "→ T" are stated in the draft as demonstrated across
  five decades, not proved for all n (I1 register, as 2.2's "nowhere differentiable").
- Running on the owner's machine: `uv run` inside the linked-folder shell cannot
  reuse the Windows `.venv`; ran with `UV_PROJECT_ENVIRONMENT`/`UV_CACHE_DIR` outside
  the mount and `--frozen`, so numpy is the lock-file's 2.5.2 either way. Two
  earlier attempts died at exit 137 because the device shell was running a stale
  copy of the script (chunk 20); recommitting under a new staged name fixed it.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction, D2 wiring and self-check against the JSON,
  check wiring — L2 scope by design.
- Ledger placement on the site — still the L2 decision from S1.
- The index's "test asserting QV within tolerance of T" as a library test on T2's GBM
  paths — not this session's scope (§7 outputs only); the JSON is the fixture.
- `ROADMAP.md` line 225 "Brownian motionn" — owner's typo, untouched (I18).

**Exact next step**

- Owner commits `experiments/2_3_quadratic_variation.{py,json}` and
  `docs/evidence/S3/` to `touchstone` `main`, and `drafts/2.3.md`,
  `drafts/2.3-checks.md`, `drafts/notation.md` to `touchstone-learn` `main`; ticks S3
  in `ROADMAP.md` with a pointer here. Next milestone: S4 · 2.4 The Itô integral,
  fresh session per §7 — the draft's "Into 2.4" paragraph, the x² identity
  W_T² = 2Σ W·ΔW + T (this page stops at "short by T"), and the ledger's rulebook and
  Taylor rows are its opening material; D3 (∫W dW, left-endpoint vs midpoint) is the
  demo.
