# S5 — Teaching session · page 2.5 Itô's lemma · evidence pack

### 2026-09-27 · claude-fable-5-1 · S5 taught; experiment run on the owner's machines; owner draft written, reviewed against I1, checks and notation batch approved

Work order (P3): teach 2.5 per constitution §7, numbers before theory. Inputs: index
§2.5 (second-order Taylor plus the rulebook; df = (f_t + a·f_x + ½b²·f_xx) dt + b·f_x dW;
worked W², log S, e^(W − t/2); check: simulate both sides for f = W², assert e^(W_t − t/2)
has constant mean), experiments/README, the S4 evidence pack, the S5 handover in the
owner's project, `drafts/2.4.md`'s "Into 2.5" section, 2.3's identity
W_T² = 2Σ W·ΔW + Σ(ΔW)² and rulebook rows, 2.3 C4 (Σ|ΔW|³ → 0 like 1/√n), the owner's
predictions. Outputs: numpy experiment + JSON in `touchstone/experiments/`; owner draft in
`touchstone-learn/drafts/2.5.md`; checks drafted by Fable, approved by the owner; S5 batch
appended to the notation ledger; draft reviewed against I1. Session opened 2026-09-14 and
ran across 2026-09-14 … 27 in six sittings on two machines (the Windows workstation, then
the owner's Mac, then the workstation again); the link dropped and recovered many times and
cost nothing.

**Done**

- Predict-then-run: five gut predictions captured before any code, questions and answers
  recorded verbatim at the top of the notes. P1 "growing – continuously compounding at a
  rate of approx sqrt t" (growing: right; the rate: wrong — e^(t/2), a constant rate ½);
  P2 "1 / sqrt t" (wrong: c = ½, and 1/√t is not a constant); P3 "3W dt" (right);
  P4 "No, because the quadratic variation vanishes" (right); P5 "no, because this vanishes,
  sum(dw^3) -> 0 as dt ->0" (right, and the signed sum dies faster than the reason says).
  P1 and P2 are the same miss — "W_t is about √t" applied to the exponential — and are
  check distractors Q2 and Q3; P3 is Q4's right answer.
- `experiments/2_5_ito_lemma.py` + `.json` — claims C1–C5, 196 checks pass, seed
  20260914, 66 s on the Windows workstation (`uv run --frozen`, numpy 2.5.2); the container
  run on numpy 2.4.4 agrees to every printed digit, the largest difference 5 parts in 10⁹ of
  a 10⁻⁶ residual; `--quick` 7 s. Committed interim from the Mac as `touchstone` `main`
  82f32f7 (2026-09-26).
  C1 (400 paths drawn once at 10⁶ steps, read on n = 10² … 10⁶; g = x²): the (ΔW)²-form is
  exact to 2.3 × 10⁻¹⁵ on every path and grid; the dt-form's residual is Σ(ΔW)² − T to
  10⁻¹⁵, mean 0 within s.e., sd 0.134 … 0.0014 against T√(2/n), slope −0.498.
  C2 (same paths; g = eˣ, x³): the (ΔW)²-form residual (third order and beyond) has rms
  0.0105 … 1.0 × 10⁻⁶ for eˣ and 0.0388 … 3.8 × 10⁻⁶ for x³, slopes −1.001 and −0.998;
  for x³ it equals Σ(ΔW)³ to 10⁻¹⁵ and the fourth-order residual is ≤ 8 × 10⁻¹⁵; the
  (ΔW)²-vs-dt noise ½Σ g″((ΔW)² − dt) has mean 0 within 5 s.e. and rms matching
  √(½dt·Σ g″² dt) (x³ to 2 % from n = 10⁴; eˣ to 30 %, heavy-tailed), the dt-form residual's
  spread 0.120 … 0.0013 (eˣ), 0.271 … 0.0029 (x³), slopes −0.481, −0.491; Σ|ΔW|³ mean
  0.162 … 0.0016 against 2√(2/π)T^(3/2)/√n, slope −0.501; Σ(ΔW)³ mean 0, sd 0.0388 …
  3.8 × 10⁻⁶ against √15·T^(3/2)/n, slope −0.998.
  C3 (20,000 paths at n = 10⁴): E[e^(W_t)] = 1.0506, 1.1378, 1.2998, 1.4684, 1.6546
  (± 0.0024 … 0.0149) at t = 0.1, 0.25, 0.5, 0.75, 1 against e^(t/2) = 1.0513 … 1.6487,
  within 2.1 s.e.; E[e^(W_t − ½t)] = 0.9993 … 1.0036, within 2.1 s.e. of 1; the growth
  split E[S(t)] = −0.0007 … +0.0014 (0 within noise), E[D(t)] = 0.0513 … 0.6533 against
  e^(t/2) − 1 within 1.5 s.e.; candidates e^(W_t − t) → 0.6087 and e^(W_t − √t) → 0.6087 at
  t = 1; martingale corr −0.0165, conditional means −0.0137, −0.0057 ± 0.0099.
  C4 (x(t) = t²): chain-rule residual × n → 1.2556 (eˣ), 4/3, 12/5, slopes −1.000; the dt
  term added gives −0.7313, −1, −1 at n = 10⁶ (−0.7145, −0.9867, −0.9612 at n = 100).
  C5 (coin walk): x² both residuals ≤ 1.4 × 10⁻¹³; x³ both = dt·W_T to 4 × 10⁻¹⁶ (n = 100:
  W_T = 0.6, 0.4, −0.4, 1.0, −0.6 → 0.006, 0.004, −0.004, 0.010, −0.006); fourth order
  ≤ 8 × 10⁻¹⁵.
- Teaching notes (claude.ai artifact, seventeen versions; archived as `teaching-notes.html`
  beside this file): section map card (a standing opener from now, at the owner's request),
  predictions, ten numbered sections, one canvas figure with the zoom viewer, draft checks,
  the ledger batch, a site proposal. Iterated on the owner's questions: the x² identity
  re-cited to 2.3 (he caught it); a "what problem it solves" panel and, after "I don't
  recall us saying that", an eight-rung ladder from 2.3's identity through 2.4's −½T to the
  lemma, with the two rungs 2.4 never wrote (the flip to d-notation; dt as (ΔW)² per step);
  the general form built in three additions, then cut to three lines from add 1's line
  before (dW)² = dt, with the undo step shown; "push" and "kick size" replaced by drift and
  volatility, glossed; drift-first ordering applied everywhere (his ask for consistency);
  the two-variable cross term written out (the ½ eaten by f_tx = f_xt); f_tx as an order of
  differentiation; "smooth" as an assumption about f, never W; x as the slot and W its
  occupant; add 2 cut to its two facts after "are we using this anywhere?".
- Owner draft `touchstone-learn/drafts/2.5.md` — interview transcription, twelve questions
  (hook; what was done; the x² table; the eˣ/x³ table; the two forms; the remainder;
  E[e^W]; why ½ and not √t; the general form and log S; the smooth curve; the coin; into
  2.6) plus a plan section, "What this page shows, and how", drafted by Fable at the
  owner's request after "we just spring into things … and I don't really know why" and
  accepted by him as it stood — the one Fable-written passage on the page, marked in place
  (F35; I2 exception at the owner's instruction). Thirty-five flags raised, all ruled by the
  owner in-session and applied: seven notation re-sets after pastes stripped superscripts,
  fractions and roots (F1, F13, F19, F22, F25, F28, F31 — "eW", "−12T", "et" for e^(√t),
  "+t or −t" for ±√t); two substantive corrections (F26: the (Δx)² term named where the dt
  term was meant; F29: "the chain rule is exact" on the coin, where it is the lemma that is
  exact); number-checks against the JSON (F3, F4, F5, F6, F7, F12, F16, F27 — "to the printed
  digit" twice, "the same at 10⁶ as at 100", a threefold-per-row claim true of the spread
  and not of path 1); a dropped ⅙ (F11) and a dropped factor 6 (F8); the notes' colour words
  and P-labels removed at assembly (F33, F34); a one-clause addition tying the coin
  expansion's ½t to ½g″(ΔW)², proposed and accepted (F21); "the index's check" → "this
  page's check" (F18); "Euler steps match pathwise" → "how the gap shrinks with dt" (F32).
  Claim map in the footer, nineteen entries; the general form and log S marked derived not
  measured; "Into 2.6" previewed not claimed.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.5-checks.md`, drift-first.
- Notation ledger S5 batch, 14 rows — `touchstone-learn/drafts/notation.md`, approved:
  Itô's lemma; the order of terms; ½g″ dt; the two forms; the remainder; Σ(ΔW)³ vs Σ|ΔW|³;
  E[e^W] = e^(t/2); the exponential martingale; f_t, f_x, f_xx, f_tx; dX = a dt + b dW;
  smooth; (dW)² = dt ↺; Taylor's ½ and ⅙; heavy tail.
- Not S5's to build, recorded for the owner and the L track: a `point` line per Part 2 page
  on the site (eleven draft lines in §10 of the notes; site copy is the owner's, I13);
  `Claude outputs/` in `.gitignore` (a one-line owner edit); 2.4's "Into 2.5" paragraph is
  the one committed line in dW-first order.

**Decisions (with why)**

- Fine grid 10⁶, not 2.4's 2 × 10⁶: no midpoints are needed, and the exp-heavy passes are
  the runtime.
- The handover said the (ΔW)²-form residual has slope −½; it has slope −1. The bound
  Σ|ΔW|³ → 0 like 1/√n is what 2.3 measured and it is loose by √n: the signed cubes cancel
  (odd moment), so the remainder is 1/n. The script measures both sums and the page teaches
  the difference — P5's answer with a number on it.
- Checks compare each residual's rms to the paths' own √(½dt·Σ g″(Wᵢ)² dt) rather than to
  the closed form, because for eˣ the weight e^(2W) is heavy-tailed and its 400-path mean
  scatters by tens of percent; eˣ's levels are checked to 30 % and its rates (slopes) to
  0.05, x³'s levels to 15 %; the closed forms are reported as limits. The page carries one
  honest line on it.
- Drift first — a dt + b dW — everywhere from 2.5 on, at the owner's ask for consistency;
  matches the index's general form and 2.6's dS = μS dt + σS dW. Taylor expansions stay in
  power order. Ledger row records it.
- F35: a Fable-drafted plan section on an owner-authored page, at the owner's explicit
  request, marked in the file as such — I2's rule is that sessions do not author Part 2
  prose; the owner asked for exactly this passage and accepted it unchanged, and the
  STATUS comment says so, so a later reader knows which paragraphs are whose.
- Ran on two machines. The Mac's Cowork VM cannot download Python 3.12 for `uv` inside the
  shell's time budget; `--quick` was verified there on the VM's Python 3.10 / numpy 2.2.6;
  the committed JSON is the Windows run. `git status` from the linked shell (either machine)
  leaves an `index.lock` the shell cannot delete — read-only git only, as S4 found.
- Session ran at Fable effort "high" throughout; the owner did not ask to change it.

**Not done**

- MDX conversion, snippet extraction (`taylor_sums`, `increment_sums`), check wiring — L2
  batch 5 by design: page 2.5 into the site as `draft` on `m/L2`, an Opus/Claude Code
  session, the owner's next ask ("I want to see these on the actual preview site").
- The `point` field per page — proposal only; the owner rewrites the eleven lines, an L
  session wires them (`src/data/curriculum.ts`, `PageRow`, `page.route.tsx`), the roadmap
  entry is the owner's (I18).
- `.gitignore` line for `Claude outputs/` in both repos — proposed, not applied.
- Leftovers the owner may delete: `.git/s5-wip-commit-msg.txt` (Mac, `touchstone`),
  `.git/s5-commit-msg.txt` (both repos, workstation).

**Exact next step**

- Owner, on the workstation: `touchstone` is on `main` at 82f32f7 after the pull — commit
  `docs/evidence/S5/` with the supplied message, tick S5 in `ROADMAP.md` (line 228) with a
  pointer here, push. `touchstone-learn` on `main`: commit `drafts/2.5.md`,
  `drafts/2.5-checks.md`, `drafts/notation.md` with the supplied message, push. Then L2
  batch 5. Next milestone: S6 · 2.6 SDEs and geometric Brownian motion, fresh session per
  §7, from the S6 handover in the owner's project — the draft's "Into 2.6", the general form
  with a = μS and b = σS, the −½σ² already worked on 2.5, and 2.1's √dt are its opening
  material; the index's 2.6 check is "Gaussian log-returns; E[S_T] = S₀e^(μT); Euler error
  vs dt; spot-the-bug σZ·dt instead of σZ·√dt".
