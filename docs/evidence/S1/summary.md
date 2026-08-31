# S1 — Teaching session · page 2.1 Random walks and scaling · evidence pack

### 2026-08-30 · claude-fable-5 · S1 taught; experiment committed; owner draft written, reviewed against I1, checks approved

Work order (P3): teach 2.1 per constitution §7, numbers before theory. Inputs: index
§2.1, experiments/README, T2 log, owner's predictions. Outputs: numpy experiment +
JSON in `touchstone/experiments/`; owner draft in `touchstone-learn/drafts/2.1.md`;
checks drafted by Fable, approved by the owner; draft reviewed against I1.

**Done**

- Predict-then-run: the owner's two gut predictions ("~0 after 10,000 steps",
  "4× time → about the same") captured before any code; both are the page's target
  misconceptions and both became approved check distractors.
- `experiments/2_1_random_walks.py` + `.json` — claims C1–C4, nine checks pass;
  committed by the owner to `main`. Determinism observed in the wild: the owner's
  re-run reproduced his JSON byte-for-byte; across machines (numpy 2.4.4 vs 2.5.2)
  coin results are bit-identical (integer arithmetic) while gaussian results agree
  to ~1e-9 (float accumulation order) — I6's "tolerances, never bit-exact", exactly.
- Teaching notes (claude.ai artifact, six sections, two figures, checkpoint and
  pincer tables) — archived as `teaching-notes.html` beside this file. Iterated
  in-session as the owner's questions exposed gaps: E[Sₙ] vs E|Sₙ| bars called out,
  log-log slopes derived from row ratios, W given a passport at first use of dW.
- Owner draft `touchstone-learn/drafts/2.1.md` — produced by interview transcription
  (Fable asks, owner speaks, Fable assembles verbatim in substance; I2 held: no page
  sentence is Fable's). I1 review passed after two defect rounds (inverted pincer
  directions; a σZ·dt-shaped bridge sentence; an out-of-scope (dW)² = dt claim —
  all fixed by the owner). Claim map in the draft's footer.
- Checks Q1–Q5 approved by the owner — `touchstone-learn/drafts/2.1-checks.md`.
- Notation ledger started and approved — `touchstone-learn/drafts/notation.md`
  (S1 batch, 12 entries incl. a W/dW preview); one batch appended per S-session.

**Decisions (with why)**

- Probability baseline "solid" (owner's choice after discussion): standard facts
  (variance of sums, CLT) assumed silently; the stochastic side taught in full.
  Matters from S4 onward where derivations lengthen.
- Notation ledger created (owner's request): glyph look-alikes trip readers more
  than concepts — E[Sₙ] vs E|Sₙ| caught the owner himself mid-session. Site
  placement (reference page / hover component / appendix) decided at L2.
- Proposed, not yet adopted — owner to rule at L2: "no glyph without a birth
  certificate" as an editorial rule; every symbol introduced at first use or
  glossaried; enforceable as a CI lint over the MDX.
- The draft claims neither the Gaussian limit shape (2.2) nor (dW)² = dt (2.3):
  2.1's committed experiment does not back them (I1).
- S-track outputs committed by the owner directly to `main`, no `m/S1` branch:
  P6's branch discipline protects unreviewed session work, whereas these are owner
  commits with the review already done in-session (§7: the session is the review).

**Not done**

- MDX conversion, snippet extraction, demo D1, check wiring — L1/L2 scope by design.

**Exact next step**

- Owner commits the three `touchstone-learn` files and this evidence pack, then
  ticks S1 in `ROADMAP.md` with a pointer here. Next milestone: S2 · 2.2 Brownian
  motion, fresh session per §7 — the ledger's W/dW rows are its opening material.
