# S4 — Teaching session · page 2.4 The Itô integral · evidence pack

### 2026-09-14 · claude-fable-5-1 · S4 taught; experiment run on the owner's machine; owner draft written, reviewed against I1, checks and notation batch approved and committed

Work order (P3): teach 2.4 per constitution §7, numbers before theory. Inputs: index
§2.4 (left-endpoint sums and non-anticipation; ∫W dW = ½W_T² − ½T; zero mean,
martingale, Itô isometry; Stratonovich as an aside; demo D3), experiments/README, the
S3 evidence pack, the S4 handover in the owner's project, `drafts/2.3.md`'s "Into 2.4"
paragraph and its x² identity W_T² = 2Σ W·ΔW + Σ(ΔW)², the ledger's rulebook and
Taylor rows, the owner's predictions. Outputs: numpy experiment + JSON in
`touchstone/experiments/`; owner draft in `touchstone-learn/drafts/2.4.md`; checks
drafted by Fable, approved by the owner; S4 batch appended to the notation ledger;
draft reviewed against I1. Session opened 2026-09-08 with the device link up and ran
across 2026-09-08 … 14 (the owner's questions on the notes took four sittings); the
link dropped and recovered several times and cost nothing.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and
  answers recorded verbatim at the top of the notes at the owner's request. P1
  "T·W_T" (wrong: ½W_T² − ½T; a gut guess with no reasoning behind it, so its check
  label is the units check), P2 and P3 "T·W_T, the same" for midpoint and right
  endpoint (wrong: ½W_T² and ½W_T² + ½T — the "all three agree" intuition the page
  exists to kill), P4 "0" (right for the left sum; the midpoint version has E = ½T),
  P5 "because that represents the value that the change affects" (right idea,
  sharpened on the page to the position held over the step). P1 and P2/P3 are check
  distractors Q1 and Q2.
- `experiments/2_4_ito_integral.py` + `.json` — claims C1–C4, 108 checks pass, seed
  20260908, 36 s on the owner's machine (`uv run --frozen`, numpy 2.5.2; the
  container run on numpy 2.4.4 agrees to every printed digit except the 16th
  significant figure of three `polyfit` slopes and one `corrcoef`, as in S3).
  C1: 400 paths drawn once at 2 × 10⁶ steps and read on n = 10² … 10⁶, so every grid's
  midpoints are real path values (coarsening factors 20,000 … 2, all even); the three
  identities left = ½W_T² − ½Σ(ΔW)², right = ½W_T² + ½Σ(ΔW)², mid = ½W_T² +
  ½(Σδ₁² − Σδ₂²) hold to 2 × 10⁻¹⁵ on every path and grid; errors from the limits have
  mean within 5 s.e. of 0 and sd 0.0722 … 0.00075 (left, right) against T/√(2n) and
  0.0496 … 0.00054 (mid) against T/(2√n), slopes −0.494; gaps right − left mean
  1.0075 … 1.0001, mid − left mean 0.5096 … 0.5000. C2 (20,000 paths, n = 10⁴):
  E[left] = −0.0041 ± 0.0049, E[mid] = 0.4959, E[right] = 0.9960; isometry
  E[left²] = 0.4839 ± 0.0118 against ½T²(1 − 1/n) = 0.49995; running I(t) mean 0 and
  mean-square ½t² at t = 0.25 … 1, R(t) mean t; corr(first half, second half) =
  −0.010. C3: x(t) = t², all three sums within Σ(Δx)² of ½, n·Σ(Δx)² = 4/3 −
  1/(3n²), gap slope −1.000. C4: ±√dt coin, left = ½W_T² − ½T and right = ½W_T² + ½T
  exactly (5 × 10⁻¹⁴) on every grid; the n = 100 path with W_T = −1.0 has left = 0.
- Teaching notes (claude.ai artifact, nine sections plus draft checks and the
  notation batch, two canvas figures with a click-to-enlarge zoom viewer added on
  request, seven tables) — archived as `teaching-notes.html` beside this file.
  Iterated 25 versions on the owner's questions: the identity card reordered to
  P1 · left, P2 · mid, P3 · right after the notes' left/right/mid order had him read
  the right-endpoint line as the midpoint one; a trapezoid line added when he reached
  for "(1 + 2)/2" — (left + right)/2 = ½W_T² exactly on every grid, the midpoint-time
  sum only in the limit; asides added for the telescoping written out at n = 3, the
  midpoint identity derived, and three checks on a candidate answer (units kill
  T·W_T, the chain-rule ½ kills W_T², E = 0 kills ½W_T² and forces the −½T); the
  "how fast" paragraph rebuilt four times into a two-row subtraction (grid value
  minus n → ∞ value) after "limit" was read as a maximum and W_T was thought to be
  in the gap — it is in both values and cancels; the path-5 line "paid ½T in
  quadratic variation" corrected to "paid T, and the identity subtracts half".
- Owner draft `touchstone-learn/drafts/2.4.md` — interview transcription, eleven
  questions (hook; experiment; reading the table; the identity; the limit; zero mean;
  the finance reason; Stratonovich; the smooth curve; the coin; into 2.5). I2 held:
  every page sentence is the owner's, hook included. Seven of his pastes arrived with
  superscripts and fractions stripped (x2, 12, WT2); Fable re-set the notation and he
  confirmed each (F7, F9, F11, F13, F16, F20, F24). Twenty-seven flags raised, all
  ruled by the owner in-session and applied: F1 "exactly that T" → "or half of it";
  F2 one path drawn → 400; F3 "universal" → "not limited to path 1" (I1 register);
  F4 "drifts upward toward" → "settles at" (path 1 overshoots at 10⁴–10⁵); F5 midpoint
  "halfway to the printed digits" → "near halfway, closing on halfway" (0.02 off at
  n = 100); F6 "paid ½T in quadratic variation" → "paid T, subtracts half" (Fable's
  slip in the notes, echoed); F8 "nothing stochastic survives" → "nothing of the
  path's interior — only the endpoint"; F10 ½x_T² qualified "x starting at 0";
  F12 "before tᵢ" → "up to tᵢ"; F14, F18, F22, F25 notes-section numbers replaced;
  F15 E[right] = T qualified to h = S = W, the general bonus being the price's
  quadratic variation, and right − left = Σ(ΔS)² ≥ 0 path by path; F17 an inverted
  sentence (Itô keeps the QV term; the midpoint cancels it); F19 "the only integral"
  → "the only one of the three"; F21 a missing dt in Σ(Δx)² ≈ dt·∫(2t)² dt; F23
  "to six figures" → five at n = 100 (4/3 − 1/(3n²)); F26 the 2.5 check run twice,
  g = x² exact on the grid and a non-quadratic g in the limit only; F27 "Into 2.5"
  marked previewed, not claimed. Claim map in the footer, 16 entries each pointing at
  a JSON field.
- Checks Q1–Q5 approved by the owner unchanged — `touchstone-learn/drafts/2.4-checks.md`.
- Notation ledger S4 batch, 15 rows — `touchstone-learn/drafts/notation.md`; approved
  by the owner as they stood in the notes. Rows born from the session's questions:
  "limit" (read as a bound), the two kinds of equality on the page, units of W,
  telescoping (and Σ ΔWᵢ = W_T on every grid, after "what is W_T" came up mid-page),
  δ₁/δ₂, the endpoint a sum reads at, s.e., E[X²] vs Var.
- Committed by the owner 2026-09-14: `touchstone-learn` `main` 82dd621 (draft,
  checks, ledger batch), pushed; the L2 batch-3 session's uncommitted evidence-pack
  edit committed on `m/L2` first so `main` could be checked out. `touchstone`: this
  pack and the experiment are the owner's to commit (below).

**Decisions (with why)**

- Paths drawn at 2 × 10⁶ steps, twice the finest reported grid, so that every grid's
  midpoints are path values: interpolating a Brownian midpoint is wrong (the true
  midpoint is the endpoint average plus an independent N(0, dt/4) kick) and would force
  δ₁ = δ₂ on every step, killing the term the midpoint result depends on. Cost: 2× the
  normals. Runtime stayed at 36 s.
- Midpoint means midpoint-in-time, W(mᵢ), not the endpoint average — both are used as
  definitions of the Stratonovich integral (same limit), and the index's D3 says
  "midpoint sums". The endpoint average is the trapezoid, exact on every grid; the
  notes carry both and say which the JSON's "mid" is.
- The midpoint identity is checked in two forms (mid = left + Σδ₁² + Σδ₁δ₂ and
  mid = ½W_T² + ½(Σδ₁² − Σδ₂²)) because the second makes the limit plain and gives
  the error's sd, T/(2√n), which the JSON also checks.
- Smooth control is x(t) = t², not 2.3's sin(2πt): a full sine wave has x_T = 0, so all
  three sums would go to 0 and the convergence to ½x_T² would be invisible.
- A memory leak found and fixed in this script, and present in 2.3's: `"W_T":
  w[:, -1]` keeps a view into each simulated chunk, so the whole chunk stays alive
  for the run — 80 chunks × 80 MB = 6.4 GB here (killed the container at 375/400
  paths), 80 × 40 MB = 3.2 GB in 2.3 on a VM with 3.9 GB, the likely cause of S3's
  two exit-137 deaths. Fixed with `.copy()` on the three retained views; peak RSS
  now ~500 MB. `2_3_quadratic_variation.py` line 79 still has the view (the
  2026-09-08 `--quick` commit did not touch it); a one-line `.copy()` changes no
  number in its JSON. Proposed, not applied — the owner's call, outside this
  milestone (P2).
- Nothing in the JSON claims Σ(ΔW)² → T; that is 2.3's demonstrated result, cited.
  "Into 2.5" is marked previewed, not claimed, in the claim map, as 2.3's "Into 2.4".
- Running on the owner's machine: as in S3, `uv run --frozen` with
  `UV_PROJECT_ENVIRONMENT`/`UV_CACHE_DIR` outside the mount (the VM's env had been
  cleared; `uv sync --frozen` reinstalled numpy 2.5.2 and quantlib 1.43 in 5 s). A
  backgrounded run dies when the shell call returns (twice); the run has to fit inside
  one foreground call, which at 36 s it does.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction, D3 wiring and self-check against the JSON,
  check wiring — L2 scope by design. L2 will want a `--quick` flag on
  `2_4_ito_integral.py` as it added to 2.3's for the snippet check (I3); the same
  shape applies (a tenth of the paths, tolerances widened by √(400/n_paths), no JSON).
- The `.copy()` fix to `2_3_quadratic_variation.py` — proposed above, not applied.
- `Touchstone/Claude outputs/` — the desktop app's copies of this session's chat files,
  untracked; not for committing, the owner can delete it.
- Stale `.git/index.lock` files left in both checkouts by `git status` from the
  linked-folder shell, which cannot delete files: the owner removed
  `Touchstone-Learn`'s; `Touchstone\.git\index.lock` (zero bytes, 2026-09-14 16:11)
  must go before the commit below.

**Exact next step**

- Owner removes `Touchstone\.git\index.lock`, commits
  `experiments/2_4_ito_integral.{py,json}` and `docs/evidence/S4/` to `touchstone`
  `main` with the supplied message, ticks S4 in `ROADMAP.md` with a pointer here,
  pushes. Next milestone: S5 · 2.5 Itô's lemma, fresh session per §7 — the draft's
  "Into 2.5" section (the ½g″ dt term as the −½T in general; the two-sided check for
  g = x² exact and a non-quadratic g in the limit), the ledger's Taylor, rulebook and
  Itô-integral rows, and 2.3's Σ|ΔW|³ → 0 are its opening material; the index's 2.5
  check is "simulate both sides for f = W²; assert e^(W_t − t/2) has constant mean".
