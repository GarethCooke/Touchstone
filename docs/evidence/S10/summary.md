# S10 — Teaching session · page 2.10 Greeks · evidence pack

### 2026-11-05 → 2026-11-08 · claude-fable-5-1 · S10 taught; experiment run on the owner's workstation; owner draft written, reviewed against I1, checks and notation batch approved; drafts committed from the session's cloud clone

Work order (P3): teach 2.10 per constitution §7, numbers before theory. Inputs: index
§2.10 (delta, gamma, vega, theta, rho — what each measures and who watches it; the PDE
re-read as a P&L statement: theta pays for gamma; check: bump-and-revalue matches
analytic, the hedging simulator with realised ≠ implied vol shows the gamma P&L; D6 and
D5), the S10 handover in the owner's project, `drafts/2.9.md`'s "Into 2.10" (the Greeks
as derivatives of the formula; delta already met as N(d₁); what each measures, why
traders watch it, how it emerges from the formula), 2.9's delta by bump and as the
share-measure probability, 2.7's PDE check and its gamma P&L (−3.76 / 0.00 / +3.74),
the T-track's golden Greeks (`golden/bs_vanilla.json`, seven columns, raw partials,
QuantLib 1.43), the owner's predictions. Outputs: numpy experiment + JSON in
`touchstone/experiments/`; owner draft in `touchstone-learn/drafts/2.10.md`; checks
drafted by Fable, approved by the owner; S10 batch appended to the notation ledger;
draft reviewed against I1. Session opened 2026-11-05 on the Windows workstation with S9
committed (touchstone main 06b6a18) and closed 2026-11-08; the drafts committed from
the session's cloud clone as the owner (m/L2 e35a987, `preview` fast-forwarded to it).

**Setup decisions (owner, 2026-11-05, before any code).** (Q1/a) The gamma P&L —
hedged at σ_i while the stock moves at σ_r — is 2.7's measured result, cited and
re-read on 2.10, not re-measured; S10's experiment shows what is new, the per-step
attribution Θδt + ½Γ(δS)² + (rSΔ − rV)δt of the option's change on the hedged book.
(Q2/a) Vega and rho per unit (vega per 1.00 of σ, rho per 1.00 of r, theta per year),
the golden file's and T0's convention, with the desk scalings named once. (Q3/a) The
put's Greeks beside the call's, through parity.

**Done**

- Predict-then-run: five gut predictions captured before any code (2026-11-07,
  after a first answer that gave the definitions only), questions and answers
  recorded verbatim at the top of the notes. P1 (the stock 100 → 101): right —
  ≈ 0.627 and slightly more because of positive gamma; the actual change is 0.632,
  Δ + ½Γ = 0.6321. P2 (gamma): half — "at the strike" is a short-expiry statement
  (the peak is at 74.8 with a year to run, 0.0123 against 0.0095 at the strike);
  "gamma goes up" as T → 0 right; "the hedged book neither gains nor loses but needs
  re-hedging" half — it gains ½Γ(δS)² on a move either way and pays theta while
  nothing moves, zero only in expectation. P3 (theta): half — "deep in the money"
  wrong (there the call is a forward and its theta is the carry alone, −4.76; the
  trough is −10.20 at S = 114); "gamma pays for theta and vice versa" right in
  substance, the course's phrase is "theta pays for gamma". P4 (vega): right — "no";
  "largest at strike" (103.0); "shrinks with T" clarified 2026-11-08 as "shrinks as T
  shrinks", both lines kept on the record and the clarified reading scored;
  "+0.375 (about +0.38)" against the measured 0.3783. P5 (rho): wrong — "through
  both" is true of the differentiation and false of the result (the d-terms cancel
  by S₀φ(d₁) = Ke^(−rT)φ(d₂), leaving KTe^(−rT)N(d₂) = 44.7); the signs reversed
  (call +44.7, put −50.4); "both pieces" is the strike piece alone. P2, P3 and P5
  became check distractors (Q2, Q3, Q4, Q6).
- Experiment `experiments/2_10_greeks.py` (seed 20261105): C1 the six analytic
  Greeks (Δ, Γ, vega, Θ, ρ, ∂V/∂q) against central bumps at the base case, the put
  and 2.9's 216-point grid, to 10⁻⁷ (5 × 10⁻⁵ relative in S, σ, T; 10⁻⁵ absolute in
  r, q; 10⁻⁴ relative for Γ's second difference); the Γ bump study from h = 10⁻¹ to
  10⁻⁶ relative (the V: 9.6 × 10⁻⁶ … 1.6 × 10⁻¹⁰ at 10⁻⁴ … 1.8 × 10⁻⁶); the one-unit
  moves (S 100 → 101: 0.6321 vs Δ 0.6274 + ½Γ 0.0047; σ 0.40 → 0.41: 0.3783 vs
  0.3784; r 0.05 → 0.06: 0.4497 vs 0.4472; one day: −0.0269). C2 the oracle — all
  seven columns of `golden/bs_vanilla.json` at 7,200 grid and 34 edge rows to the
  file's tolerances (worst 2.8 × 10⁻¹³ grid, 1.6 × 10⁻¹¹ edge, the one-day deep-ITM
  theta relative), QuantLib `BlackCalculator` live at 216 points call and put (worst
  1.1 × 10⁻¹³); the first time the golden Greeks are read on an S page. C3 the PDE
  as a P&L statement on paths — 2.7's hedge re-run (4,000 exact-GBM paths at 4096
  fine steps, μ = 0, σ_i = 0.4, hedged at N = 256 and 4096) at σ_r = 0.3, 0.4, 0.5,
  every step attributed: the attribution identity exact per path (10⁻¹²); theta cost
  + carry + Σe^(−rt)½σ_i²S²Γδt = 0 on every path (10⁻¹³ — the PDE); at σ_r = σ_i the
  gamma gain 7.58 ± 0.05 equals the theta cost 9.71 less carry 2.14 (sum 0.003 ±
  0.003); at σ_r = 0.3 / 0.5 the hedged P&L −3.80 ± 0.02 / +3.72 ± 0.03 is
  (σ_r² − σ_i²) × the gamma integral (54.3 / 41.4) and sits within 1.5 combined
  s.e. of 2.7's −3.76 / +3.74 (cited in the JSON, not re-measured); the remainder's
  rms 0.11 → 0.013 from N = 256 to 4096 while the theta cost's spread (sd 3.3) does
  not fall. C4 shapes — each Greek against S on [40, 200] at τ = 1, ½, ¼, 0.05 (Γ
  peaks at Ke^(−(r + 3σ²/2)τ) = 74.8, 86.5, 93.0, 98.6 to one grid step; vega at
  Ke^((σ²/2 − r)τ) = 103.0, 101.5, 100.8, 100.2; Θ's trough at 114, 107, 103, 101)
  and against T at the money (Γ√T → φ(0)/(S₀σ) = 0.009974, vega/√T → S₀φ(0) =
  39.894, Θ√T → −S₀σφ(0)/2 = −7.979). C5 parity's Greeks across the grid to
  3 × 10⁻¹⁴ and at the base case (put Δ −0.3726, Θ −5.048, ρ −50.405). D6 fixtures:
  the five Greeks of the call and the put against S at the four τ, the base-case
  readout with the desk scalings. 165 checks, all pass. Run in the container (28 s,
  numpy 2.5.3, QuantLib 1.44) and on the workstation (59.4 s, Python 3.12.15, numpy
  2.5.2, QuantLib 1.43, `uv run --frozen` with the environment under `~/tmp`,
  rebuilt in 13 s); the two JSONs agree to 3 parts in 10¹³ in every value that is
  not itself round-off, with identical paths. The workstation's JSON is the committed
  one (md5 351b6cd3…).
- Teaching notes v1 published 2026-11-07 as a private artifact (plain summary first,
  section-map card, predictions as posed and answered, what ran, A–F with eight
  tables and six canvas figures, the derivation in ten rungs after the numbers,
  decisions, draft checks, draft ledger, the interview plan); v2 at close (the
  P4 re-score, approvals recorded) is `teaching-notes.html` beside this file.
- Owner draft `drafts/2.10.md`: all nine interview answers in one attached file on
  2026-11-08, tripled LaTeX re-set (~40 runs, confirmed "1 confirmed"), transcribed
  with eight tables and value-path comments; audited against the JSON — eleven flags
  F1–F11, all ruled "A" ("accept recommendations") and applied: F1 the C++ in Part 3,
  to the file's tolerances (I1); F2 the one-rate-point move 0.45 with ρ × 0.01 = 0.447
  (I1); F3 the units sentence (Q2/a); F4 the put's numbers in the prose (Q3/a); F5
  "near expiry and at the money" (I1); F6 the sign — theta cost net of carry equals
  the assumed gamma gain (I1); F7 2.7's totals cited in the prose (Q1/a); F8 the
  option's change split into theta, delta and gamma terms, the carry the cash leg's
  (I1); F9 theta's and rho's watchers; F10 Γ's peak from 87.8 to 74.8; F11 2.9 linked
  (L2 batch 9 landed 2026-11-06, m/L2 at b26f529), 2.11, 3.1, 3.5 plain. "2.10
  approved, checks approved, ledger approved" 2026-11-08.
- Checks `drafts/2.10-checks.md` Q1–Q6, one per section, approved. Ledger: the S10
  batch (12 rows) appended to `drafts/notation.md`, approved; the S9 pins stop at the
  next batch heading and hold. `npm test`: 966 pass in the clone (the suite grew from
  787 with batch 9 and the 2.8 follow-ups). Committed as the owner from the cloud
  clone: touchstone-learn m/L2 e35a987, `preview` fast-forwarded to it.

**Decisions (with why)**

- Γ's bump step 10⁻⁴ × S, not the handover's 10⁻²: the study put the floor of the V
  there (1.6 × 10⁻¹⁰ against 9.1 × 10⁻⁸ at 10⁻²); the first differences at 5 × 10⁻⁵
  relative after vega's grid error at 10⁻⁴ (1.2 × 10⁻⁷) crossed the 10⁻⁷ line; r and
  q bumped absolutely (they can be zero) at 10⁻⁵ after 10⁻⁴ gave 6.7 × 10⁻⁶
  truncation. One tolerance, 10⁻⁷, for all six.
- One claim dropped during the quick run: "the theta cost's mean moves by less than
  a fifth of the gamma gain's across σ_r" — false, because the theta cost is a path
  integral and the paths at σ_r = 0.3 stay near the strike where Θ is most negative
  (−10.87 against −8.69 at 0.5). Replaced by two true ones: the hedged P&L's mean
  rises with σ_r through zero, and the gamma gain's move exceeds the theta cost's.
- The 2.7 citation in C3 is a 5-combined-s.e. check against this run's N = 4096
  means on fresh paths, not a reproduction; the page cites 2.7's numbers (Q1/a).
- "Theta pays for gamma", one direction, from 2.7's ledger; the owner's "and vice
  versa" not carried.
- Θ's trough stated as "near the strike" with the number (−10.20 at S = 114), not
  "at the money".
- Figures (the Γ V, the four shape curves, the attribution bars) belong to the notes
  and to D6; the page has tables (2.9's F8 ruling carried).
- The dividend-rho checked and named once (rung 10, one ledger row); vanna, volga,
  charm named once as not on this page. The index's five are the page's five.
- Seed 20261105 (the opening date); 4,000 paths × 4096 fine steps as 2.7; the
  216-point grid as 2.9.

**Not done**

- The `touchstone` files are on the owner's disk, uncommitted: `experiments/
  2_10_greeks.{py,json}`, `docs/evidence/S10/{summary.md, teaching-notes.html}`; the
  message in `.git/s10-commit-msg.txt`; the ROADMAP tick (line 233) his, in the same
  commit.
- Page 2.10 is not on the site: L2 batch 10 (Opus/Claude Code: MDX, checks Q1–Q6
  wired, the S10 ledger batch on 0.3 — bound the S9 page-side hash first if batch 9
  did not —, snippets, D6's Greeks panel from `results.d6`, D5's link). Once 2.10
  routes (`/stochastic-calculus/greeks`) the plain "2.10" in the S10 batch's first row
  and on 2.9's "Into 2.10" are re-linked at the conventions pass.
- The ledger-wide "·" → dash pass (S1–S6 rows) is still the owner's to ask for.
- The "riskless" → "risk-free" pass over the earlier drafts, the site and the test
  pins (S8's F1) — who runs it not yet ruled.
- Owner items carried from S9: the stray backslashes on ROADMAP lines 228, 230, 231
  and now 232 (`\docs/evidence/S9/…`); the index's §2.7 line "riskless must earn r"
  and the `2_7_delta_hedging.py` docstring; the index's §2.6 OU line and §3.2
  importance-sampling line; the `m/L2` → `main` merge in touchstone-learn; the
  `.git/s7-*`, `s8-`, `s9-commit-msg.txt` leftovers in touchstone.

**Exact next step**

- Owner, on the workstation: `touchstone` on `main` at 06b6a18 — commit
  `experiments/2_10_greeks.{py,json}` and `docs/evidence/S10/` with the supplied
  message (`.git/s10-commit-msg.txt`), tick S10 (line 233) in `ROADMAP.md` with a
  pointer to this file in the same commit, push. `touchstone-learn`: `git pull
  --ff-only origin m/L2` to pick up e35a987. Then L2 batch 10 (2.10 onto the preview
  site with D6's Greeks), and the last study milestone: S11 · 2.11 Where it breaks,
  fresh session per §7, from the S11 handover in the owner's project — the draft's
  "Into 2.11" (one σ in the formula, a different implied σ for every strike; the
  Greeks as the language of the surface; vanna and volga previewed), the index's
  §2.11 line, 2.7's three decisions and 2.10's D are its opening material.

## Exit criteria (ROADMAP, track S)

- [x] Experiment script and JSON committed to `touchstone/experiments/` — on the
      owner's disk, uncommitted at close; commit message supplied
      (`.git/s10-commit-msg.txt`).
- [x] Owner's draft page in `touchstone-learn/drafts/2.10.md` — written in the
      owner's words, interview-transcribed, flags ruled "A", "2.10 approved";
      committed as m/L2 e35a987.
- [x] Draft checks approved by the owner — Q1–Q6, `drafts/2.10-checks.md`.
- [x] Draft reviewed against I1 — eleven flags, all ruled and applied (five of them
      I1 corrections: F1, F2, F5, F6, F8); every quantitative sentence mapped to
      `2_10_greeks.json` in the review (claim map in the draft's footer).
- [ ] ROADMAP tick — the owner's (I18).

## Files

- `touchstone/experiments/2_10_greeks.py`, `.json` (165 checks, seed 20261105)
- `touchstone/docs/evidence/S10/summary.md` (this file), `teaching-notes.html` (v2, close)
- `touchstone-learn/drafts/2.10.md`, `2.10-checks.md`, `notation.md` (S10 batch appended)
  — m/L2 e35a987
