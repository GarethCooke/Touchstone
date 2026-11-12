# T3a — Settle the library before it is bound · evidence pack

## Work order (P3)

**Goal.** T3a as `ROADMAP.md` states it, derived through the owner's rulings of 2026-11-12
(`docs/briefs/T3a-design-rulings.md`): a path API; a second, step-recording implied-vol
solver beside Newton–Brent; `AmericanVanilla` as a contract type of its own and `exercise`
gone from `PdeSettings`; `scales.hpp` under `detail/`; three classes beneath the free
functions; the nine repeats (and the tests' own) removed; the README's status current. Exit:
every test that was green still green on both compilers and under the sanitizers; a test for
each new piece; free-function signatures unchanged except where a ruling changes them; a
repeated-code review by a session that did not write the change, its findings closed; no new
dependency.

**Steps.** Branch `m/T3a` from `6b8a60a`.

1. Baseline: build `main` with this machine's two compilers and keep the suite's full
   reported output, so the refactor can be diffed number by number rather than only
   pass/fail.
2. Mechanical moves: `scales.hpp` → `detail/`; the finite-and-signed predicates once (R9);
   `2^-53` once; the quantities `scales.hpp` exists to form, formed there (R3).
3. Contracts: `Vanilla<Exercise>` with the two aliases, one definition of the payoff (R5),
   American overloads of the grid, `exercise` removed from `PdeSettings`; a compile-time
   refusal test.
4. The closed-form evaluation: one class that validates and computes once, its
   volatility-free half reused by both implied-vol solvers (R1, R2).
5. The grid solver: one Thomas sweep for all three uses (R7); a class that builds its two
   matrices once (F3) and keeps its solution readable for D8.
6. The path generator and the path API; the fixture generated here from an independent
   transcription of `paths.ts`; Monte Carlo moved onto the generator (R4, R8, F2).
7. The second solver, against page 2.11's committed trace and refusals.
8. Bump Greeks from one list of bumped points (R6); concepts on the two templates; settings
   defaulted on all four entry points (F5).
9. The tests' own repeats; then the suite's reported numbers diffed against the baseline,
   and every difference explained.
10. A repeated-code review by a fresh session; its findings closed.
11. README status, CI, evidence; push the branch and read the Actions run.

**Decisions taken before starting** (each *Decision — owner may overrule* unless marked):

- **Visibility of the three classes**: the walkthrough's suggestion — the closed-form
  evaluation public, the grid solver and path generator in `include/touchstone/detail/`, so
  T4's binding and the tests can reach them without their being API.
- **Refusals in the second solver return no NaN.** The experiment and the site return NaN
  for a price outside the no-arbitrage bounds; the library's standing rule is that an
  accepted input never returns one. Below the lower bound the solver returns σ = 0 (the
  closest any volatility gets) and above the upper bound σ = +∞, each with its residual
  against the bound and the status that says it was refused.
- **History removed from comments is kept, not lost.** Ruling 8 moves it to
  `ARCHITECTURE.md` at T5; where T3a has to change a comment that carries it, the removed
  text goes verbatim into `docs/evidence/T3a/history.md` for T5 to pick up.
- **Local compilers are g++ 15.2 (MinGW) and clang 22 (MSVC target)**, both newer than CI's
  g++ 13 and clang 18. CI on Ubuntu remains the authoritative run for both compilers and the
  sanitizers; the branch is pushed for it (P6).

---
