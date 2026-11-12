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

### 2026-11-12 · claude-opus-5-5 · The library settled: one contract template, one closed-form evaluation, one sweep, one path generator, two solvers — and every number the suite reported before still reported, but two

**Done**

1. **Behaviour preserved, measured rather than asserted.** `main` was built first on both
   local compilers and the suite's whole reported output kept. After the refactor the same
   output differs from it in exactly **two numbers**, on both compilers, and both come from
   one deliberate change (item 4): American-against-European grid on the put identity rows,
   2.492e-13 → 2.784e-13 (bound 1e-11), and the projected sweep against projected SOR in the
   lower region, 3.109e-15 → 2.665e-15. Every golden sweep, every Monte Carlo statistic,
   every convergence ratio and every implied-vol residual is unchanged to the last digit
   printed. The branch's output is also identical between g++ 15 (MinGW runtime) and
   clang 22 (MSVC runtime). `tests.txt` §2.

2. **Contracts (ruling 4).** `contract.hpp`: `Vanilla<Exercise>` holds the three fields once;
   `EuropeanVanilla` and `AmericanVanilla` are its two specialisations, and existing
   `EuropeanVanilla{K, T, type}` code builds unchanged. `with_exercise` is the one explicit
   way across. `payoff` is written once there and read by the Monte Carlo and the grid (R5).
   `exercise` is gone from `PdeSettings`; the grid takes either contract through one
   `GridSolver<E>` whose European and American solves differ only by `if constexpr` on the
   sweep and the boundary raise. `tests/test_contract.cpp` holds the refusal as
   compile-time facts: every entry point of the closed form and its two classes, Monte
   Carlo, both implied-vol solvers and their bounds, and both forms of bump Greeks refuse an
   `AmericanVanilla`; the grid and `payoff` accept it; neither contract converts to the
   other.

3. **The closed-form evaluation (ruling 6, R1, R2).** `ClosedForm` validates once and
   computes once; the seven free functions are each one construction and one read, and each
   formula is written once, in its accessor. Its volatility-free half, `ClosedFormQuote`
   (discount factors, discounted spot and strike, forward log-moneyness, `√T`), is what
   both implied-vol solvers build once per solve and evaluate at each step; `S e^{-qT}` and
   `K e^{-rT}` are formed in one place. Reused at a row's volatility, the quote gives the
   one-shot evaluation to the bit on all 7234 golden rows. Both public.

4. **One Thomas sweep (R7), and the grid solver (ruling 6, F3).** The plain solve and both
   directions of the projected one are now one template sweep, the put's direction being
   the same sweep over the mirrored index range. It keeps the classic Thomas arithmetic, so
   every European solve is bit-identical to before; the projected solves moved from the
   pivot form to it, which is item 1's two numbers. `detail::GridSolver<E>` builds its two
   matrices once (they were rebuilt and rescanned every step), and its solution can be
   stepped and read level by level for D8: stepping it reproduces `crank_nicolson` to the
   bit, and today's solution matches the closed form at all 509 nodes within three total
   volatilities of the spot to 8.8e-7 of `max(V, S)`.

5. **Paths (ruling 1).** `paths.hpp`: `brownian_path` and `gbm_path` write a whole path into
   the caller's span, exact-stepped or Euler, drift explicit, on `detail::PathGenerator`,
   which Monte Carlo now draws from too (R4: the exact growth and its discounted form are one
   step with two drifts). `golden/paths-known-answers.json` — 3 Brownian and 10 GBM paths,
   one an Euler path that goes negative — is generated by `golden/generate_paths.py`, a
   plain-Python transcription of `docs/rng.md` and the site's `paths.ts` that first
   reproduces `rng-known-answers.json`. The library reproduces it to **1.7e-16** (tolerance
   1e-12; 636 of 672 values to the bit). Run under Node against the same file, the site's
   own `paths.ts` reproduces it to 1.7e-16 too — the agreement L5 needs, measured now. The
   exact scheme equals GBM's solution on the same Brownian path to 8.6e-16 at 1 to 365 steps.

6. **The second solver (ruling 2).** `implied_vol_safeguarded`: Newton on σ inside a bracket
   the sign of each error narrows, bisecting where Newton would leave it, the experiment's
   defaults and statuses, every iterate recorded on request. It reproduces page 2.11's
   committed trace **iterate by iterate to 7.1e-15** (4 iterations, no bisection, as
   committed), all five of the experiment's other recorded targets (two refusals, one above
   the bracket, two harder solves in 8 and 5 iterations, exactly as committed), and
   round-trips all 7234 golden prices to 1.0e-12 against the 1e-8 criterion. It shares the
   quote and the bounds with Newton–Brent.

7. **The rest of the nine, and the smaller ones.** `scales.hpp` under `detail/` (ruling 5)
   with the products R3 names formed there — `carry_rate`, `drift_time`, `log_discount`,
   `variance`, `total_variance`; one list of bumped points that `require_valid` checks and
   `bump_greeks` prices (R6); Monte Carlo's hold-aside rule once (R8); the finite-and-signed
   predicates once (R9); `2^-53` once; the undeclared `total_volatility` overload gone (F2);
   settings defaulted on `monte_carlo` and `crank_nicolson` (F5); `VanillaPricer` and
   `RealFunction` concepts on the two templates. In the tests: one sweep-scale header, one
   Greek-field table, one fixture reader for all four JSON files, one shared-path loop.

8. **Compilers, sanitizers, CI.** On the final tree, locally: g++ 15.2 `-Werror`, 0
   warnings; clang 22, 0 warnings outside the tests (doctest's `__COUNTER__` and the CRT's
   `getenv` in them); MSVC `cl.exe` 19.44, one warning, `getenv` in a test; clang
   ASan+UBSan, 0 diagnostics. 116 cases and 4,140,435 assertions on all three compilers (93
   and 4,135,768 before), with g++'s and clang's output identical line for line. **CI on
   `47c8108`, the last code commit: all four jobs green, 0 warnings** — g++ 13.3, clang
   18.1.3, GCC ASan+UBSan, and the golden job, which regenerated the path fixture
   byte-for-byte. `build.txt`, `tests.txt` §§1, 7, 8.

9. **The repeated-code review, and closing it.** A fresh agent session, given the owner's
   rule and the brief's catalogue and told to edit nothing, read every file under
   `include/`, `src/` and `tests/`. It confirmed R1–R9, `2^-53` and the four test repeats
   closed, and then found 45 more: some left over from the catalogue, some introduced here
   (the two solvers' validation, `ClosedForm` copying its quote's fields, the two concepts,
   the log-drift formed in two associations), and a good deal of older repetition in the
   tests the catalogue had only scanned — the worst-error idiom hand-written at 17 sites,
   SCHEMA.md's scaled error re-implemented six ways. Every finding it rated real is
   closed. In three of them part of what it named is kept, each because the two places
   are different things: Monte Carlo's discounted intrinsic in its overflow recovery, the
   two fixture readers' `load()` bodies, and three signed or differently scaled figures
   in the American suite. Of its ten borderline findings, two are closed, two partly, and
   six kept with the reason.
   **`review.md` has every finding and its closure.** Closing them moved no number the
   suite reports: the library's fixes changed nothing in its output, and the tests' changed
   one message and the assertion count (`tests.txt` §7).

**Exit criteria**

| Criterion | Result |
|---|---|
| Every test that was green is green, on both compilers and under the sanitizers | **PASS** — all 93 baseline cases still pass, now 116 of 116. CI on `47c8108`: g++ 13.3 18/18, clang 18.1.3 18/18, GCC ASan+UBSan 18/18. Locally: g++ 15.2, clang 22 and MSVC 19.44 116/116, clang ASan+UBSan 116/116 with 0 diagnostics. Reported numbers unchanged but two, both explained (Done 1). |
| A path fixture | **PASS** — `golden/paths-known-answers.json` and its generator; reproduced to 1.7e-16 against 1e-12; the site's `paths.ts` reproduces it too; CI regenerates it byte-for-byte. |
| The second solver against page 2.11's committed trace | **PASS** — iterate by iterate to 7.1e-15, iteration and bisection counts and status as committed; the five other committed targets likewise. |
| An American contract refused by the closed form at compile time | **PASS** — `tests/test_contract.cpp`, `static_assert`s over concepts: the file fails to compile if any of the refusals stops holding. |
| The free functions' signatures unchanged except where a ruling changes them | **PASS** — every change is listed under **Decisions** with the ruling behind it; no existing call in the tests needed changing except the American suite's (ruling 4) and one include of `scales.hpp` (ruling 5). |
| A review for repeated code by a session that did not write the change, its findings closed | **PASS** — `review.md`: every finding closed, or kept with the reason it is not a repeat; the suite's reported numbers unchanged by the closing. |
| No new dependency | **PASS** — none in the library or the tests; `generate_paths.py` uses the Python standard library only. |

**Decisions (with why)**

Every change to a public declaration, with the ruling behind it:

- `Exercise` moved from `pde.hpp` to `contract.hpp`; `PdeSettings::exercise` removed;
  `crank_nicolson` and the grid's `require_valid` gained `AmericanVanilla` overloads (ruling 4).
- `payoff` moved from `monte_carlo.hpp` to `contract.hpp` and became
  `template <Exercise E> constexpr double payoff(const Vanilla<E>&, double)` — one definition
  for the Monte Carlo and the grid (ruling 4's condition, R5). Every existing call compiles
  unchanged.
- `scales.hpp` is now `detail/scales.hpp` (ruling 5).
- `monte_carlo` and `crank_nicolson` take `settings = {}` (F5).
- `bump_greeks<Pricer>` and `brent<Function>` are constrained by `VanillaPricer` and
  `RealFunction` (ruling 6's stated default).
- `QuotedMarket` moved from `implied_vol.hpp` to `black_scholes.hpp`, beside the class that
  takes it; `Scheme` moved from `monte_carlo.hpp` to `paths.hpp`, which both now use. Both
  headers that had them still include them.
- New: `ClosedForm` and `ClosedFormQuote` (with `quote()`, `require_valid(vol)` and
  `discount_factor()` on the quote), `QuotedMarket::of`, `with_exercise`, the path API, the
  second solver and its types and `to_string`.

And the judgement calls, each *Decision — owner may overrule*:

- **The closed-form evaluation is public; the grid solver and the path generator are in
  `detail/`.** The walkthrough's suggestion. Both internal classes are header-visible so
  that T4's binding can reach `GridSolver` for D8's surface without its becoming API.
- **The second solver returns no NaN.** The experiment and the site's `types.ts` give NaN
  for a price outside the no-arbitrage bounds. Here, below the lower bound the answer is
  σ = 0 and above the upper bound σ = +∞, each with its residual against the bound, and the
  status says the price was refused. The standing rule is that an accepted input never
  returns a NaN, and a refusal by status is an accepted input. L5's binding either passes
  the saturated values through or maps them to NaN for D9; it is the site's choice.
- **The two solvers do not share a stopping rule, and the brief says they should.** The
  rulings list "the tolerance rule" among what the two share. They have none in common:
  ruling 2 fixes the second solver's at the experiment's `1e-12 × max(1, |price|)`, and
  Newton–Brent's is relative to the price's own computing scale, `max(S e^{-qT}, K e^{-rT})`,
  which its passing tests rest on. Each keeps its own; what they do share is the quote and
  the bounds. This is a disagreement inside the brief, not between the brief and the
  roadmap, and it is reported rather than resolved.
- **The single sweep keeps Thomas's own arithmetic.** Either form could have been the one;
  this one leaves every European number unchanged and moves only the projected solves, by
  round-off (Done 1).
- **Newton–Brent's seed reads the quote's forward log-moneyness**, `ln(S/K) + (r - q)T`,
  where it formed `ln(S e^{-qT} / K e^{-rT})` — the same quantity, now formed one way. No
  reported number moved.
- **`price_scale`, `lowest_price` and `highest_price` now validate their inputs**, because
  they read a `ClosedFormQuote`. Two of them did arithmetic on unvalidated input before.
- **Validation order.** `require_valid` checks the volatility-free fields first and the
  volatility after, so an input with two faults may now name a different one first. No
  test depends on which.
- **Zero is absorbing in a path**, and a factor of zero takes a path there: that is what
  makes an infinity times a zero impossible. It differs from `paths.ts` only where
  `paths.ts` would produce a NaN or a negative zero.
- **The path fixture's bytes are Linux's**, because CI regenerates and diffs on Linux; on
  Windows one `exp` differs in the last bit (`build.txt` §5).
- **The test reader accepts Python's `NaN`.** The 2.11 JSON contains bare `NaN` literals,
  which JSON does not have; `read_python_json` reads them as `null`, outside strings only.
- **`test_tridiagonal.cpp`'s two `[]` writes became `.at()`**, for g++ 15's false positive
  (`build.txt` §2). Not a repeat; a local compiler's warning.
- **Monte Carlo's saturated estimate keeps the first non-finite contribution**, not the
  last: one hold-aside rule for the accumulator and the sample total (review 3.36). Only
  the sign of an estimate already at infinity can differ, and no reported number moved.

**Not done**

- **No performance measurement** (ruling 7). The grid now builds its matrices once rather
  than every step, and the implied-vol solvers no longer revalidate the whole input at every
  step; neither was timed, and nothing here claims a speed. F4's "about eight milliseconds"
  in `pde.hpp` stays for T5 to measure or cut.
- **MSVC is built and run here, not in CI.** `cl.exe` 19.44 built the final tree at the
  project's `/W4 /permissive-` with one warning, the CRT's `getenv` deprecation in a test,
  and passed 116 cases (`build.txt` §6). That is F7's MSVC half done once on one machine,
  not claimed as supported. Emscripten is T4's.
- **The history still in unchanged comments stays** until T5 moves it (ruling 8); the
  history T3a removed from the comments it changed is in `history.md`.
- **F6** (`.clang-format`, `.clang-tidy`, `.editorconfig`) is the owner's; **F10** and
  **F11** are not T3a's.
- **The site was not touched** (I18). Three things there now follow from this branch, for
  L5: `types.ts` and `paths.ts` say the library has no path API (F9) and it now does; D9's
  trace can come from `implied_vol_safeguarded`, which reports σ = 0 or +∞ where the site
  reports NaN; and `golden/paths-known-answers.json` is the fixture the site takes.
- **The constitution's companions list still names `docs/index-v1.md`** where the file is
  `docs/quant-learn-index-v1.md` — carried by every pack since T0, one word, the owner's.

**Exact next step**

The owner reads this pack and merges `m/T3a`, then ticks T3a in `ROADMAP.md`. T4 unlocks:
the Emscripten build and its embind API, which now has `ClosedForm`, the path API, both
solvers, and `detail::GridSolver` for D8 to bind, and whose header self-containment check
already covers every header it will include.

---

### 2026-11-12 · claude-opus-5-5 · Monte Carlo walks each path once again, with the step and the draw inlinable; no reported number moved; on this machine the defaults are back to main's time and Euler at 64 steps is 10% behind it

An independent timing of `main` against this branch (g++ 13.3, -O3) found Monte Carlo
slower on the branch — Euler at 64 steps 20.6 → 28.5 ms a call, the defaults 1.17 → 1.29 ms
— and named two causes in the code: under Euler each path was walked twice, once for the
growth factor and once for the discounted one, where `main` carried both through one loop;
and `GbmStep::factor` was defined in `src/paths.cpp`, so every step was a call across
translation units with a branch on the scheme. This entry fixes both, without changing a
number the suite reports.

**Done**

1. **One walk carries both factors.** `detail::walk` and `detail::grow` take an
   `std::array<double, N>` of starting values and advance every one by the same factor, formed
   once per step and multiplied into each value in the order given. Under Euler, Monte Carlo
   grows `{1, e^{-rT}}` in one walk where it made two, and the multiplications are `main`'s in
   `main`'s order: growth times the factor, then discounted growth times the factor. A path
   written out and `terminal_growth_euler` are the same walk with one value. The stepping is
   still written once.
2. **The factor is visible to the inliner.** `GbmStep`, its constructor and `factor`, moved
   from `src/paths.cpp` into `detail/path_generator.hpp`. At -O3 g++ inlines it, and tests the
   scheme once before the loop rather than at every step (seen in the assembly; `timing.txt`
   §4).
3. **`PathGenerator::draw` moved into the header too**, which was not asked for. Under the
   exact scheme a path is one normal, so `draw` was a call across translation units at every
   step, as the factor was. Moving it is what brought the default setting back to `main`'s
   time (`timing.txt` §4).
4. **No reported number moved.** Both local compilers: 116 cases, 4,140,435 assertions, all
   passed, and the suite's whole output identical to the branch's final runs; g++ and clang
   identical to each other; g++ at -Werror with no warning (`tests.txt` §9, `build.txt` §7).
5. **Timed before and after, on this machine only**: g++ 15.2 (MinGW), the library at
   Release (-O3 -DNDEBUG), AMD Ryzen 7 3800X, Windows 11; 15 rounds, order rotated, pinned to
   one core; medians (`timing.txt`):

   | `monte_carlo`, one call | `main` | branch as pushed | this change |
   |---|---|---|---|
   | Euler, 64 steps, 32768 paths | 28.58 ms | 35.77 ms | 31.51 ms |
   | defaults (exact, 32768 paths) | 1.712 ms | 1.756 ms | 1.718 ms |

   Under Euler that is 59% of the loss recovered, and 2.9 ms (10%) still behind `main`. At
   the defaults it is 6 µs from `main`, inside the spread of `main`'s own runs.
6. **CI**: pending; recorded below when the run completes.

**Decisions** (each *Decision — owner may overrule*)

- **`draw` moved as well as the factor**, for the reason in Done 3, and measured.
- **The exact scheme keeps its one multiplication** by the discount rather than carrying
  `{1, e^{-rT}}` through its one-step walk. In a walk zero is absorbing, so where the discount
  has underflowed to zero and the growth overflowed, the carried value would be zero; the
  multiplication gives a NaN there instead, which sends it to the exponential recovery and a
  finite value. Everywhere else the two agree.
- **`advance` is unchanged, and its zero tests cost about 1.5 ms of the 2.9 ms Euler still
  lags `main`**: without them (a build made only to measure this, never committed) the call
  is 30.0 ms. Those tests are what keep an infinity times a zero, and so a NaN, out of every
  path. A form returning the same bits in every case with one test on the product in place
  of two on the operands measured no faster (`timing.txt` §3, §4). The rule stays, and so
  does the time.
- **No compile-time dispatch on the scheme.** Once g++ can see the factor it already chooses
  one loop per scheme at entry.

**Not done**

- **The rest of the Euler gap**: about 1.5 ms at 64 steps on this machine that is neither
  the two causes named nor `advance`, and was not attributed.
- **No other compiler, flag or machine was timed**: not CI's g++ 13.3, which the independent
  timing used, not clang or MSVC, not RelWithDebInfo's -O2. Nothing here claims a time for
  them. Whether g++ at -O2 also lifts the scheme's test out of the loop was not checked; GCC
  unswitches loops at -O3.
- **The local sanitizer and MSVC builds were not re-run** for this change; CI's sanitizer job
  is.
- **No benchmark was added to the repository.** The harness and its driver are reproduced in
  `timing.txt` and built by hand; ruling 7 leaves performance to T5.

**Exact next step**

The owner reads this entry and `timing.txt`, then merges `m/T3a` as the first entry's next
step says.

## Amendments

**None proposed.** No dependency, technology or invariant changes. The rulings brief is the
authority for everything here, and the one disagreement inside it — the shared tolerance
rule — is reported under **Decisions** rather than settled by amendment.

## Owner actions

1. **Read this pack and merge `m/T3a`.** T3a's tollgate is V. CI: see the Monte Carlo
   timing entry, which records the run on the last commit to touch code.
2. **Rule on the two solvers' stopping rules** if the brief meant them to share one
   (Decisions). Nothing waits on it.
3. **Rule on NaN against saturation** for the second solver's refusals before L5 binds it,
   if the site's NaN is what D9 should get from the library itself.
4. **Rule on `advance`'s zero tests** if their measured cost under Euler (about 1.5 ms of a
   31.5 ms call at 64 steps, on this machine) is not worth what they rule out. Nothing waits
   on it.

## What is in this pack

- `summary.md` — this file.
- `build.txt` — the toolchains, the baseline's two local-compiler warnings, the branch's
  zero-warning build, the sanitizer runs, and the fixture's bytes on two platforms.
- `tests.txt` — the runs; the baseline diff and its two numbers; the new tests' reported
  numbers; the site's `paths.ts` against the fixture; the review; CI.
- `review.md` — the repeated-code review's findings, and how each was closed.
- `history.md` — the history removed from changed comments, kept verbatim for T5.
- `timing.txt` — Monte Carlo timed on `main`, the branch as first pushed, and after the
  timing follow-up: machine, compiler, flags, method, results, the harness and its driver.
- `diff.txt` — `git diff --stat` against `6b8a60a`.
- No `screenshots/`: T3a has no UI.
