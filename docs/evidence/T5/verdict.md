# T5 — tollgate verdict

Tollgate T5 · 2026-11-14 · Fable review per constitution §6: bounded claims.
Reviewer: the Fable session in the owner's Claude Project that audited T3a and T4 and wrote
the points the T5 session carried (configured model id `claude-fable-5-2`). §6 asks for a
fresh session that reads only the pack. This one was neither, at the owner's choice: it had
the two earlier audits behind it, and it rebuilt and re-ran rather than read.

**Basis.** Read: `CONSTITUTION.md` and the T5 entry of `ROADMAP.md` at `74987c7`;
`ARCHITECTURE.md` and `README.md` in full; the T5 pack's `summary.md`, `claims.md` and
`tollgate.md` in full, and `tests.txt` and `build.txt` where a figure needed them; every
header changed between `main` and `m/T5`; `bench/timing.cpp`. Re-established rather than
taken on trust:

- **Build and suite.** g++ 13.3.0, warnings as errors: 0 warnings and 18 of 18 ctest entries
  at `7110c84` and again at `948ad76`; 120 cases, 4,140,490 assertions. Every figure
  `claims.md` quotes from the suite came out the same in this run.
- **No number moved.** The seven library sources compiled at `-O3` give object files
  byte-identical to `main`'s, at `7110c84` and at `948ad76`.
- **The history.** No milestone, tollgate, review or governance id is left in a comment
  under `include/`, `src/`, `tests/`, `wasm/`, `bench/`, the CMake files or the workflows.
  All 46 texts §10.3 quotes as removed at T5 are on `main` word for word.
- **The document against the code.** §4's table of defaults against the headers; seven
  translation units, seventeen headers, 18 ctest entries; no inheritance and no virtual
  function; no include outside the standard library.
- **The timings.** The harness is sound: an opaque call into a static library, a volatile
  sink, medians of medians. Run here on a cloud VM it gives 48 ns, 213 ns, 846 ns, 1.35 ms
  and 4.56 ms, the same order as §7's. §7's own figures are one machine's and were not
  reproduced; §7 says as much.
- **The artifact.** The 1.0.0 build from the owner's machine passes the branch's smoke test,
  17 of 17 on Node 22, loads in headless Chromium 153 in a page and in a worker, and returns
  the values the released 0.4.0 does.
- **The session's decision on the three pairs.** With the real headers,
  `require_valid(option, market, {})` is ambiguous today; with the grid's overloads folded
  to a template it compiles and picks the bump sizes.
- **CI.** Run 43581338088 on `948ad76`: six jobs, all green.

## Verdict

**PASS WITH DEFECTS.** Given at `7110c84`. Every defect is wording, none is in
`ARCHITECTURE.md`'s own claims beyond one unstated resolution, and all were closed on
`m/T5` before the merge.

- **Every claim in `ARCHITECTURE.md` maps to a test or a file — pass.** `claims.md` numbers
  each claim against what holds it. The session had an agent that did not write the document
  check 129 rows; 9 did not hold and 26 needed narrowing, and each was corrected. This
  tollgate re-read the corrected rows against their sources and found them sound.
- **CI green — pass.**
- **Tag pushed — the owner's**, after this verdict. This file is saved by the tick that
  follows the release.

The document holds §1's register. It says first what is claimed and what is not, gives its
timings as one machine's on one date, and names what the three methods share instead of
calling them independent. The defects below are all one failure: where the check narrowed
the document, the same claim was left standing, unnarrowed, in the README or in a header.

## Defects

Against §1's register and I1, and for the first against the deliverable "README final".

1. **`README.md`, opening list — medium.** "Three independent ways"; the Monte Carlo held
   "across the golden file's rows"; the grid held "on the same rows". Each says more than
   `ARCHITECTURE.md` §1. Closed at `948ad76`.
2. **`pde.hpp`, file comment — low.** "Shares no arithmetic with either of them beyond the
   scale functions": it shares `payoff` with the Monte Carlo. Closed at `948ad76`.
3. **`monte_carlo.hpp`, file comment — low.** Claimed independence in the discount factor
   and the payoff, both of which are shared. Closed at `948ad76`.
4. **`monte_carlo.hpp`, `MonteCarloSettings` — medium.** "About a cent of standard error at
   typical parameters." Measured here at the defaults: 0.0766 on §7's option, and a median of
   0.0625 over the golden file's 7,200 main-block rows. The figure is dropped. Closed at
   `948ad76`.
5. **`pde.hpp`, `PdeSettings`, and `ARCHITECTURE.md` §1 — low.** The comment said the suite
   holds every golden row to 3e-4 at the defaults; the suite holds every row at 512 × 256
   and 136 rows at the defaults. True when run here, 2.232e-5 at worst over all 7,200 rows,
   but held by nothing. §1 said "at a stated resolution" without stating it. Closed at
   `948ad76`.

The session's own scan then found more of the same kind in `normal.hpp`, `bump_greeks.hpp`
and three test files, and closed them at `948ad76`; `tollgate.md` §2 lists each.

The re-check of `948ad76` found four more, which the first scan made here had missed. They
were issued with their replacement text and closed on `m/T5` before the merge, under three
gates: the old phrases gone, the object files still byte-identical to `main`'s, CI green.

6. **`bump_greeks.hpp`, choosing the bump — low.** Gamma off the grid at "a relative error
   of 26,000 at a bump of 1e-9, falling to 2e-5 at 1e-2", credited to the test. The test
   measures the default bump and 1e-2 only. True when run here, 2.617e4 and 2.143e-5, but
   held by nothing. Now what the test measures and asserts: 4.9e-3 against 2.1e-5, the first
   more than fifty times the second.
7. **`pde.hpp`, `PdeResult::mesh_peclet` — low.** "At the default settings it stays below
   0.06, which `tests/test_pde.cpp` asserts." The test asserts below 0.15 at 512 × 256, where
   it measures 0.10. Measured here at the defaults over all 7,200 rows: 0.0509. Now the
   test's grid and bound, and that the number is proportional to `dx`.
8. **`bump_greeks.hpp`, `require_valid` — low.** A one-sided difference's error "a hundred
   thousand times larger": held by nothing. Now the orders of the two errors, without a
   figure.
9. **`bump_greeks.hpp`, the sweep's floors — low.** Vega's floor given as 2e-10: 2.07e-10
   with g++ 15.2 on the owner's machine, 2.95e-10 with g++ 13.3 here. Now a range, named as
   a rounding floor.

Not defects, for the record. The session's report counted seven CI jobs where six ran; the
pack is right. No second agent re-checked the rows the corrections added; this tollgate read
them. Nothing is claimed for MSVC, for a second machine's timings, or for a browser in this
repository's CI, and the document says so.

## Amendments

None proposed. One departure from §6 is recorded above and in `ROADMAP.md`: the tollgate was
not a fresh session and did not confine itself to the pack. Whether §6 should allow that for
a milestone whose exit criterion is a claim-by-claim check is the owner's question.

## Unlocks

P2 — card and architecture page (entry: T5 ✓). I11's condition for a Touchstone card on the
portal is met. L5's library-side entries, T3 and T4, are met; it waits on L3.

First step: a portal brief in the portfolio repository, since P2's executor is Opus via a
portal brief. The page is rendered from `ARCHITECTURE.md` and takes a `writeup-sources`
entry for the `Touchstone` repository, with its baseline at the commit `v1.0.0` tags.
