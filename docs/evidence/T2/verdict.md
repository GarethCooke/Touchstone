# T2 — review verdict

T2 review · 2026-08-30 · redone by Fable at the owner's request: the first run of this
review was made with Opus by mistake, and P8 gives reviews to Fable. Reviewer: a fresh
session in the owner's Claude Project (configured model id `claude-fable-5`), reaching the
checkout over the mount. T2's tollgate remains **V** — this verdict is input to the owner's
read-and-merge, not a substitute for it.

**Basis.** Read: `CONSTITUTION.md`, the T2 section of `ROADMAP.md`, `docs/evidence/T1/`
(summary and verdict), the whole T2 pack, and — because redoing an adversarial review
requires it — the T2 sources and tests in full. Beyond reading, the pack's claims were
re-established independently rather than taken on trust; the list is below, and it is the
substance of this verdict.

## Verdict

**PASS WITH DEFECTS.** All three exit criteria hold on the code as committed. The defects
are in the evidence pack and a comment, not in the library: the pack's headline Euler
figures come from a superseded run. Both are now fixed on the
branch — the figures in the second commit, the comments in the third — and nothing
blocks the merge.

## Independently verified

1. **The A4 copy is what it claims.** `docs/rng.md` and `golden/rng-known-answers.json`
   are byte-identical to `touchstone-learn`'s working tree **and** to its state at the pin:
   `git show bd16b71` on both files reproduces the digests in `golden/README.md` exactly.
   `bd16b71` is the L0-verdict commit and `dbd786d` the files' last touch, as stated.
2. **The pack describes this checkout.** All 32 build-input SHA-256s in `tests.txt` §8
   reproduce from the working tree (`sha256sum -c`: 32 of 32).
3. **The suite reproduces on an independent build.** A fresh container (Ubuntu 24.04,
   glibc 2.39 — a different machine from both hosts in `build.txt`, though the same
   platform generation as host B): g++ 13.3 and clang++ 18.1.3, `-Werror`, both clean;
   49 cases, 4,111,444 assertions, green on both; the two full outputs are identical to
   each other after path/line-number normalisation; and — the same run again under ASan
   and UBSan with `-fno-sanitize-recover=undefined` at sweep scale 16 — clean. Every
   number checked against `tests.txt` §2 matches exactly: the grid battery
   (6,147 rows: mean −0.020, sd 0.986, 19 beyond three, worst |z| 3.559 against 5.648),
   the delta and hit-count batteries, the deep re-run (323 rows), the antithetic battery
   (1,343 rows), the census (764/630, worst unasserted |z| 440.84), and the 400-run
   spread test. Except the Euler tables — defect 1.
4. **The fixture is the specification.** `docs/rng.md` was transcribed into a third
   implementation for this review (Python: exact 32-bit integer arithmetic for
   xoshiro128\*\* and fmix32, AS241 with the spec's coefficients and Horner order).
   From the spec alone it reproduces all 30 fixture uniforms and all 30 normals
   **bit-identically**. Three implementations — TypeScript, C++, this transcription — now
   agree exactly on what one specification says.
5. **AS241 is transcribed faithfully.** Scripted character-level comparison of all 48
   coefficients, spec against `normal.hpp`: identical. `unfmix32`'s two constants are the
   multiplicative inverses they claim to be (checked mod 2³²). The Cochran arithmetic
   behind the 450 cut-off reproduces: 6/2^1.5 = 2.1213, (2.12/0.1)² = 450.0.
6. **Seed separation, further than the suite asserts.** `test_rng.cpp` pins the first
   8,000 sweep seeds (closest pair 341,411 — reproduced). The grid's deep re-runs reach
   `stream_seed(14467)`; recomputed over all 14,468 indices actually used, the closest
   pair is 82,466 — comfortably clear of the ≤3 overlap the expansion cares about.
7. **The twelve reference values re-derived at 80 digits** (mpmath, two independent
   routes agreeing to 60 digits). All are correctly rounded inverses of the exact decimal
   p. One nuance the file's comment does not state: for four of them (p = 0.6, 0.9,
   0.925, 0.975) the double literal the test actually passes is not that decimal, and the
   inverse of the double sits 1–2 ulps away — so up to 2 of the 8-ulp budget is spent on
   decimal-versus-double before AS241 answers. The measured worst of 3.5e-16 relative
   shows the budget is still ample. Observation only.
8. **The grid criterion's reading — endorsed.** The roadmap's sentence taken per-row is
   unsatisfiable on this grid: ~20 exceedances are expected of a correct estimator, and
   on 764 rows the estimate and its error bar collapse together (worst |z| 440.8 on a
   correct engine). The battery asserts everything the per-row rule could and more — a
   +0.10 SE bias passes every row and fails the mean leg, measured not asserted — the
   gate is a-priori (expected hits from N(w d2), transcribed from `SCHEMA.md` rather than
   taken from the library), the deep re-run and both Poisson tails close the coverage,
   and the 764 are named. This is the criterion's meaning, tested honestly. It is also
   the one decision that changes what an exit criterion means, and the pack rightly
   leaves it marked for the owner to ratify at merge.

## Defects

1. **Euler exit criterion, evidence — low (documentation).** `summary.md`'s headline
   figures and `tests.txt` §4's two tables (strong 0.4950 ± 0.0021, residual 0.0115;
   weak 0.9664 ± 0.0697; bias/dt 0.0696 → 0.2982) do not reproduce from the committed
   code. The code produces §2's figures — strong **0.4932 ± 0.0021**, residual 0.0084;
   weak **0.8831 ± 0.0621**; bias/dt 0.0722 → 0.3523 — confirmed here on two compilers,
   identical on both. The likely cause is capture before review finding 11's seed fix
   (`4000 + steps` → `stream_seed`), which changed the drawn paths; `tests.txt` thereby
   contradicts itself between §2 and §4. The criterion passes on the true figures — both
   slopes inside their stated bounds, every fitted level resolved at ≥ 8.1 of its own SE
   — so the defect is the pack's, not the scheme's. **Fixed in this session**, at the owner's direction, in a second commit on `m/T2`:
   §4's two tables replaced with the current run's, the summary's quoted figures
   corrected, and the whole-range slope 0.51 → 0.63. The code and its tests remain
   untouched; two comment approximations in `test_euler.cpp` join defect 2's class —
   an extrapolated 512-step bias of 6.5e-4 where the current fit gives 8.2e-4, and
   "a slope near a half" for the whole-range fit that now returns 0.63.
2. **`src/monte_carlo.cpp`, `Accumulator::add` comment — cosmetic.** The comment says
   the first non-finite sample is kept ("Whichever arrived first"); the code keeps the
   last — each new non-finite sample overwrites `overflowed_`. Behaviour is fine, since
   the sign of a saturated estimate is documented as not a number to read; the sentence
   is not. **Fixed at the owner's direction** in a third commit, together with the two
   `test_euler.cpp` approximations defect 1's note records (6.5e-4 → 8.2e-4, "near a
   half" → 0.63, in the code comments and in `tests.txt` §4's closing line).
   Comment-only: the suite was rebuilt on both compilers and both outputs are
   byte-identical to the audited runs; `tests.txt` §8's digests are refreshed under a
   dated note, and `build.txt`'s copy of the list digest with them.
3. **Observation, no action.** The never-a-NaN promise has a measure-zero corner under
   Euler: a running growth product saturated at ±inf, followed within the same path by a
   step factor that rounds to exactly 0.0, makes the growth NaN — the price contribution
   then collapses to zero through `payoff`'s comparison and the delta reaches the result
   as a NaN mean beside an infinite standard error. Reaching it needs a normal draw to
   land on specific single doubles (order n·2⁻⁵³ per path even at adversarial inputs), so
   no fixed-seed sweep can exhibit it — the same class as the suite's own `>`-versus-`>=`
   resolution note, and worth a line beside it if recorded at all.

## Amendments

None proposed. Concur with the pack that A4 was executed rather than amended and that the
linear-history pin is sound — verified at the commit, point 1 above. The two standing
governance notes (QuantLib's standing under I4; tech-decision B2's `experiments/` against
the roadmap's `golden/`) remain open at the owner's option, as at T0 and T1.

## Unlocks

T3 — finite differences, implied vol, bump Greeks (entry: T2, on the owner's merge).
First step per the roadmap: Crank–Nicolson on a log-spot grid with the Thomas solver,
toward I20's three-way agreement — for which T2 now supplies the second way and the
standard errors to compare the third against. Owner actions, in order: `git push -u origin m/T2` and read the Actions run (`ci.yml` changed: both
actions to v6, sanitizer job at a sixteenth); read the pack, ratify the grid-criterion
reading, merge, tick T2 in `ROADMAP.md`; consider `require_valid`'s association hazard
(the pack's Not-done) before T3 forms new products; delete `.git/stale-locks/` and
`_to_delete/` from Windows — the latter now also holds `t2-src.tgz`, this review's
source snapshot, which served its purpose the moment the digests matched.
