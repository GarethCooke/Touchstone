# S2 — Teaching session · page 2.2 Brownian motion · evidence pack

### 2026-09-05 · claude-fable-5-1 · S2 taught; experiment committed; owner draft written, reviewed against I1, checks approved

Work order (P3): teach 2.2 per constitution §7, numbers before theory. Inputs: index
§2.2, experiments/README, S1 evidence pack and ledger (the W/dW rows were the opening
material), owner's predictions. Outputs: numpy experiment + JSON in
`touchstone/experiments/`; owner draft in `touchstone-learn/drafts/2.2.md`; checks
drafted by Fable, approved by the owner; S2 batch appended to the notation ledger;
draft reviewed against I1.

**Done**

- Predict-then-run: four gut predictions captured before any code. P1 "sd = √0.5 −
  √0.25" (sd subtracts), P2 "slope flattens toward 0", P3 "mean 1.5, spread √2"
  (mean right, spread unconditional), P4 "×10" (right). P1, P2 and P3's spread are
  the page's target misconceptions and are check distractors Q1, Q2, Q3.
- `experiments/2_2_brownian_motion.py` + `.json` — claims C1–C4, 68 checks pass, seed
  20260903, ~18 s. Written in the session container (numpy 2.4.4), then run on the
  owner's machine via `uv run` (numpy 2.5.2): the two JSONs agree to every printed
  digit. C1 increments N(0, lag) at four lags with Gaussian tails and zero
  consecutive correlation; C2 mean |ΔW| ∝ √h (slope +0.499) and mean |ΔW/h| ∝ 1/√h
  (slope −0.501) across six decades on a 10⁻⁶ grid; C3 Var √c·W(1/c) = 1 for c = 4,
  10, 100; C4 W(2) on W(1) slope 0.9985, residual variance 1.006, coefficient on
  W(0.5) −0.008, conditional sd 0.971 for W(1) ∈ [1.4, 1.6].
- Finding not in the plan: the coin walk's k-step increments have excess kurtosis
  exactly −2/k (measured −2, −0.198, −0.023, −0.001 at k = 1, 10, 100, 250). The first
  draft of the script asserted Gaussian tails for the coin at every lag and failed
  seven checks on the lattice; the check now tests −2/k, which is the precise claim
  and lets the page show the CLT arriving rather than assert it. Became Q5.
- Teaching notes (claude.ai artifact, nine sections, two canvas figures, six tables)
  — archived as `teaching-notes.html` beside this file. Iterated in-session: §6
  rewritten when the owner asked what "regress" really measures (filter vs fitted
  line, each number's reading); a kurtosis figure (Laplace / Gaussian / uniform /
  10-step coin sum at unit variance) added at the owner's request.
- Owner draft `touchstone-learn/drafts/2.2.md` — interview transcription, eight
  questions. I2 held: every page sentence is the owner's, including the hook. Six
  review flags ruled by the owner: "random walk" (F1), "is normally distributed"
  (F2), ΔW not W(dt) (F3), "typical size of the slope" and "tends to its derivative"
  (F4), tidied spread sentence (F5), "begins to build the rules" for I1 scope (F6).
  Substantive corrections made by the owner mid-interview: independence of
  increments added as property 2 (distinct from Markov — noted that Markov ⇏
  independent increments); √c not c for the zoom; conditional vs unconditional
  expectation and variance for the 1.5 example (four rounds). Claim map in the
  draft's footer; the draft claims neither (dW)² = dt nor anything about ∫W dW.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.2-checks.md`.
- Notation ledger S2 batch, ten rows — `touchstone-learn/drafts/notation.md`; approved
  by the owner. The batch exists because the owner named
  the trap himself: "it's the notation again" — the 0.5 in W(0.5) read as an sd.

**Decisions (with why)**

- Independence of increments is listed as its own property, ahead of martingale,
  with Markov folded into it as a consequence (owner's ruling after discussion):
  the S1 index summary lists "martingale, Markov" without independence, and
  independence is what the experiment measures directly.
- Coin-walk tail fractions are reported in the JSON but not checked: increments of
  a ±1 walk sit on a lattice, and "beyond exactly 1 sd" falls between lattice points.
  Excess kurtosis = −2/k is checked instead (tolerance 0.02).
- Roughness measured on 100 paths at dt = 10⁻⁶ rather than on the 40,000-path
  ensemble at dt = 10⁻³: the slope argument needs six decades of h, and 10⁸ windows
  per h gives the log-log slopes to three decimals.
- "Nowhere differentiable" is stated in the notes and draft as demonstrated at six
  scales, not proved for all h (I1 register).
- Session ran at Fable effort "high" throughout; the owner asked twice whether to
  change it — no.

**Not done**

- MDX conversion, snippet extraction, D1 wiring, check wiring — L2 scope by design.
- Ledger placement on the site (reference page / hover component / appendix) —
  still the L2 decision from S1.
- The device shell became unavailable late in the session; the three learn-site
  files were written via the file bridge rather than edited in place. No content
  impact.

**Exact next step**

- Owner commits `experiments/2_2_brownian_motion.{py,json}`
  and `docs/evidence/S2/` to `touchstone` `main`, and `drafts/2.2.md`,
  `drafts/2.2-checks.md`, `drafts/notation.md` to `touchstone-learn` `main`; ticks S2 in
  `ROADMAP.md` with a pointer here. Next milestone: S3 · 2.3 Quadratic variation, fresh
  session per §7 — the draft's closing paragraph and the ledger's ΔW/dW rows are its
  opening material; D2 (L1) already measures Σ(ΔW)².
