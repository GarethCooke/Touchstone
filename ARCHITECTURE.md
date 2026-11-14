# Touchstone — Architecture

**Status:** describes Touchstone 1.0.0, and is written as the source the portfolio's
architecture page will be rendered from. Every claim below is listed, numbered, against the
test or file that holds it, in [`docs/evidence/T5/claims.md`](docs/evidence/T5/claims.md).
The rules the programme runs by are in [`CONSTITUTION.md`](CONSTITUTION.md); this file
describes the library those rules produced.

---

## 1. What this is

Touchstone is a C++20 library that prices European calls and puts on one underlying under
Black–Scholes–Merton, with a constant rate, a constant volatility and a continuous dividend
yield, in three ways: the closed form with its six analytic Greeks, Monte Carlo, and
Crank–Nicolson finite differences. They are independent in method — a formula, a sample, a
grid — and not in every line: all three form their scalars through one file of scale
functions, the Monte Carlo and the grid share the payoff, and the Monte Carlo takes its
discount factor and discounted strike from the closed form's volatility-free half. The
finite-difference grid also prices the American contract. Around the three sit implied
volatility by two solvers, Greeks by bumping any pricer, and sample paths of Brownian and
geometric Brownian motion drawn from a frozen random-number generator.

It is one half of a pair. The other half is learn.garethcooke.com, a tutorial whose demos
are to run on this library compiled to WebAssembly. At 1.0.0 they run on a TypeScript
backend; moving them onto the WebAssembly build is the tutorial's milestone L5, not yet run.

**What is claimed.** That the closed form agrees with QuantLib's reference values on every
row of the committed reference file, and the grid on every row of its 7,200-row main block
at 512 space intervals by 256 time steps, coarser than its defaults; that the Monte Carlo
agrees with the closed form in units of its own standard error on the rows where enough
paths finish in the money to score it; that the three agree side by side on 136 of the rows;
all within tolerances the tests state and assert. That an input the closed form, the Monte
Carlo or the path functions accept never produces a NaN. That a seed draws the same numbers
here as the tutorial's TypeScript generator recorded in the committed fixture. And the
timings in §7, for one machine on one date.

**What is not.** The claim is never that Touchstone is fast, or faster than anything: §7 is
a measurement on one machine, not a comparison. Nothing is claimed for MSVC, which CI does
not build; for a browser, which this repository's CI does not run; or for anything outside
the scope above — no term structure, no stochastic volatility, no second underlying.
QuantLib is the oracle and never a dependency: Touchstone does not link it.

## 2. System overview

```
 QuantLib-Python ──► golden/bs_vanilla.json ─────────┐  regenerated and re-derived
 (the oracle, run     golden/american_vanilla.json   │  independently in CI
  by golden/*.py)                                    ▼
                    include/ + src/ ───────────► tests/  doctest; 18 ctest entries
                    the library: C++20,              ▲
                    standard library only            │  golden/rng-known-answers.json
                          │                          │  golden/paths-known-answers.json
                          │                          │  experiments/2_11_where_it_breaks.json
                          ▼
                    wasm/binding.cpp ──► touchstone.mjs + touchstone.wasm
                    translation only        │  smoke-tested in Node in CI
                                            ▼
                               a GitHub release on a v* tag ──► the tutorial's demos
```

The library is a static library of seven translation units and seventeen headers. Its
consumers in this repository are the tests, the WebAssembly binding, a check that compiles
each header on its own, and the timing harness in `bench/`, which is built with the tests and
never run by them.

## 3. Repo layout

| Path | Owns |
| --- | --- |
| `include/touchstone/` | The public headers: the whole API. `detail/` beneath it is internal. |
| `src/` | The implementation: closed form, Monte Carlo, paths, grid, implied vol, bump Greeks, tridiagonal solvers. |
| `tests/` | doctest suites, one ctest entry per suite and one that runs them all. |
| `wasm/` | The embind binding, its error shim, its build script and its Node smoke test. |
| `bench/` | The timing harness behind §7. |
| `golden/` | QuantLib-generated reference values, their generators and independent verifiers, and the two known-answer fixtures. |
| `experiments/` | numpy scripts behind the tutorial's Part 2 pages, each with its committed JSON result. |
| `third_party/` | doctest and nlohmann/json, single headers, linked by the test executable only. |
| `docs/` | The curriculum, the technology decisions, the RNG specification, rulings, and one evidence pack per milestone. |

## 4. The public surface

Free functions over plain value types. Underneath, three classes hold the state the
functions would otherwise recompute: `ClosedForm` (public, with its volatility-free half
`ClosedFormQuote`), `detail::GridSolver` and `detail::PathGenerator` (internal). There is no
inheritance and no virtual function anywhere in the library.

| Entry point | Header | Contract | Defaults |
| --- | --- | --- | --- |
| `price_and_greeks`, and `price`, `delta`, `gamma`, `vega`, `theta`, `rho`, `dividend_rho` | `black_scholes.hpp` | European | — |
| `monte_carlo` | `monte_carlo.hpp` | European | seed 1; 32,768 paths; exact terminal sampling; no antithetics |
| `crank_nicolson`, `crank_nicolson_surface` | `pde.hpp` | European or American | 1,024 space intervals; 512 time steps; half-width 6 σ√T; 2 Rannacher steps; cell-averaged payoff; every level kept |
| `implied_vol` (Newton, then Brent) | `implied_vol.hpp` | European | price tolerance 1e-14 of the price scale; volatility up to 10; 64 Newton steps |
| `implied_vol_safeguarded` (Newton with a bisection guard) | `implied_vol.hpp` | European | start 0.2; bracket [1e-6, 5]; price tolerance 1e-12; bracket width 1e-14; 100 iterations |
| `bump_greeks` | `bump_greeks.hpp` | European | over the closed form, or any `VanillaPricer`; relative spot bumps 1e-6 (delta) and 3e-5 (gamma); 1e-6 in vol, rate and yield; 1e-5 years in expiry |
| `brownian_path`, `gbm_path` | `paths.hpp` | — | seed 1; horizon 1 |

**The contract's exercise style is its type.** `EuropeanVanilla` and `AmericanVanilla` are
both `Vanilla<E>`, so their fields are written once. The grid accepts either; every other
pricing entry point accepts the European one only, and refuses the American one at compile
time. `payoff`, which both exercise styles share, accepts either. `with_exercise` converts
one contract to the other, and nothing converts implicitly.

**The market is a type of its own,** `BlackScholesMarket`, and `QuotedMarket` is the same
market without its volatility, for the functions whose job is to find it.

**Every entry point validates before it computes,** and refuses an input outside its domain
with `std::invalid_argument` naming the reason. Each family has a `require_valid` a caller
can call to ask without pricing. Two refusals sit outside them: `monte_carlo`'s check that
`σ²T` is representable, and `crank_nicolson_surface`'s refusal of a stride of zero.

**Every Greek is a raw partial derivative:** vega per 1.00 of volatility, theta per year,
rho per 1.00 of rate. Scaling for display is the caller's.

## 5. How each method is built

**The closed form** evaluates `N(x)` through `std::erfc`, so the left tail survives: at
`x = −10` the subtraction `1 − N(10)` returns zero where the true value is 7.6e-24. A
`ClosedForm` validates once, computes once, and serves all seven outputs; its
`ClosedFormQuote` is the half that does not depend on the volatility, and both implied-vol
solvers build it once per solve.

**The Monte Carlo** draws one normal per path and samples the terminal law exactly, or steps
Euler–Maruyama over `steps` equal steps from the same generator. It reports the standard
error beside the price, and a pathwise delta with its own standard error. With antithetics
the sampling unit is the pair, and the standard error is computed from pair means, so that
the variance reduction does not also shrink the error bar it is judged by. An Euler path may
go negative and is not clipped, because clipping would change the rate the scheme converges
at.

**The grid** solves the pricing equation in log-spot, where its coefficients are constant and
one uniform grid serves every spot. It runs Crank–Nicolson after two fully implicit half-step
pairs (Rannacher's start), from a payoff averaged over each node's cell, and places the spot
exactly on a node, so the price is a node value and delta and gamma are central differences
about it. Each step is a Thomas sweep without pivoting; the matrix's diagonal dominance, which
is the condition that sweep needs, is measured and reported with the mesh Péclet number
rather than assumed. The American contract replaces the sweep with its projected form and
raises the boundary to immediate exercise; every other line of the solve is shared.
`crank_nicolson_surface` runs the same solve and keeps the solution at the levels asked for,
and its last level at the spot is `crank_nicolson`'s price, bit for bit.

**Implied volatility** has two solvers that share the closed form's volatility-free half and
the no-arbitrage bounds, and keep separate stopping rules. `implied_vol` runs Newton from the
Manaster–Koehler seed (Brenner–Subrahmanyam at the money) and hands over to Brent on
`[0, max_vol]`, which always finishes because `require_valid` has established the bracket.
`implied_vol_safeguarded` is the solver the tutorial's page 2.11 teaches: Newton inside a
bracket the sign of each error narrows, bisecting wherever Newton would leave it, recording
every iterate on request. It answers a price outside the no-arbitrage bounds with a status
and a volatility of zero or infinity, never a NaN; `implied_vol` refuses such a price with
`std::invalid_argument`.

**Bump Greeks** take thirteen prices: the base and six central pairs — one each in
volatility, rate, dividend yield and expiry, and two in spot, a narrow one for delta and a
wider one for gamma, because a second difference balances truncation against
cancellation at a larger bump than a first difference does. `tests/test_bump_greeks.cpp`
sweeps the bumps for delta, gamma, vega and rho from 1e-9 to 1e-2 against the analytic
Greeks, and asserts that each is most accurate at the size `BumpSizes` defaults to (1e-6;
3e-5 for gamma) and more than ten times less accurate at both ends of the sweep.

**The generator and the paths.** The generator is xoshiro128\*\* seeded through the
MurmurHash3 finaliser, with 53-bit uniforms and normals by Wichura's AS241 inverse, frozen by
[`docs/rng.md`](docs/rng.md). `brownian_path` and `gbm_path` write a whole path into a span
the caller owns, one normal per step, and both GBM schemes are driven by the same normals, so
two paths from one seed differ by discretisation and nothing else. The Monte Carlo draws from
the same generator through the same step.

**One association per product.** The products the domain checks guard — `σ√T`, `½σ²T`,
`(r − q)T`, the discount factors and the rest — are each written once, in
`detail/scales.hpp`, and the checks call the same functions the formulas do. A check
that formed the same quantity with a different grouping would guard a different set of inputs
from the one the formulas use (§10.2 has the input that showed it).

**The WebAssembly binding** is translation and nothing else: plain JavaScript objects in, the
library's value types across, plain objects and `Float64Array`s back, under the names and
shapes of the tutorial's `PricingBackend` interface, with `monteCarlo`, `crankNicolson`,
`crankNicolsonSurface` and `bumpGreeks` beyond it, and `defaults()` exporting the library's
default settings for every bound entry point that takes settings. The artifact is one ES
module and one `.wasm`, built by Emscripten 6.0.13 with C++ exception catching on.

## 6. Invariants (the library's own rules)

1. **Validate, then compute.** Every entry point checks its inputs before it computes, and
   an input outside the domain is an `std::invalid_argument` naming the reason (§4 names the
   two checks that sit outside a `require_valid`).
   *Why:* a domain stated in code is a domain that can be tested at its boundary.
   *Held by:* `tests/test_limits.cpp`, `tests/test_monte_carlo.cpp`, `tests/test_pde.cpp`,
   `tests/test_implied_vol.cpp`, `tests/test_bump_greeks.cpp`, `tests/test_paths.cpp`, each
   of which asserts the refusals.
2. **An input the closed form, the Monte Carlo or the path functions accept never produces a
   NaN.** From the closed form, price, delta, vega, rho and dividend rho are finite; gamma
   and theta may be infinite, where the true value is unbounded or exceeds a double. A Monte
   Carlo estimate or a path value may saturate to infinity the same way. None of them may be
   a NaN. The grid, the implied-vol solvers and bump Greeks are held to the reference grid
   and to their refusals, not swept for NaNs. One documented exception: `norm_inv` accepts a
   probability of one or more and returns a NaN.
   *Why:* an infinity compares correctly against a tolerance, while a NaN makes every
   ordered comparison false, so a check written as `error <= tolerance` fails on it and one
   written as `error > tolerance` passes it.
   *Held by:* the domain sweep in `tests/test_limits.cpp`, the Monte Carlo's in
   `tests/test_monte_carlo.cpp`, `tests/test_paths.cpp`, and `tests/test_associations.cpp`;
   the exception by `tests/test_rng.cpp`.
3. **Each product is formed once, in one association,** through `detail/scales.hpp`.
   *Why:* floating-point multiplication does not associate, so a check and a formula that
   group one product differently guard different domains.
   *Held by:* `tests/test_associations.cpp`.
4. **The same seed gives the same result,** bit for bit, and the generator reproduces the
   committed fixture produced by the tutorial's TypeScript.
   *Held by:* `tests/test_rng.cpp`, `tests/test_monte_carlo.cpp`, `tests/test_paths.cpp`,
   and the smoke test through the module.
5. **The exercise style is part of the contract's type.**
   *Why:* a function that can price only one of two contracts should refuse the other before
   the program runs, rather than price it as the wrong thing.
   *Held by:* `tests/test_contract.cpp`, which fails by not compiling.
6. **No dependency in the library.** The library includes nothing outside the C++ standard
   library; doctest and nlohmann/json are linked by the test executable only.
   *Held by:* `CMakeLists.txt`, where the library target links nothing but the project's
   warning flags, and `tests/CMakeLists.txt`, where the test executable alone links the
   vendored headers; every `#include` under `include/` and `src/` names a standard header or
   one of the library's own.
7. **Nothing is thrown across the WebAssembly boundary.** Each bound function catches every
   C++ exception and returns a JavaScript error, which `wasm/errors.post.js` throws once the
   call has returned: `RangeError` for an input the library refuses, `TypeError` for an
   argument of the wrong shape, `Error` otherwise.
   *Why:* an exception unwinding WebAssembly frames leaves the module's stack pointer behind;
   T4 measured a module killed by it at call 2,074.
   *Held by:* `wasm/smoke.test.mjs`, which makes 300,000 refused calls — 100,000 of them a
   throwing getter, refused before the module is entered — and then reproduces the RNG
   fixture and one golden row exactly as before.

## 7. Timings — one machine, one date

`bench/timing.cpp` times the five entry points at their defaults on one option: a call
struck at 100 with a year to expiry, on a spot of 100, a volatility of 0.2, a rate of 0.05 and
a dividend yield of 0.02. `implied_vol` inverts the closed-form price of that option at that
volatility; `bump_greeks` is the overload over the closed form.

Taken on 2026-11-14 on an AMD Ryzen 7 3800X under Windows 11 Pro 10.0.26200, with g++ 15.2.0
(MinGW-Builds), `-O3 -DNDEBUG -std=c++20`, the library as a static library. Each process was
pinned to one logical core at high priority as it started and ran 25 rounds; each round took
the median of five batches of each entry point, a batch being as many calls in a row as take
at least 20 ms. The table gives each of three processes' median round, lowest to highest.

| Entry point | Median of one call, three runs |
| --- | --- |
| `price_and_greeks` | 74 – 76 ns |
| `implied_vol` | 336 – 349 ns |
| `bump_greeks` | 1.39 – 1.41 µs |
| `monte_carlo` | 1.78 – 1.79 ms |
| `crank_nicolson` | 4.71 – 4.74 ms |

These are one machine's numbers on one date, with one compiler at one setting of its flags.
They say nothing about another machine, compiler or flag, about the WebAssembly build, which
was not timed, or about inputs other than the one above. Nothing was tuned for this
measurement: the library timed is main's, object file for object file, and there is no fast
path. The raw output, the
machine and the method are in `docs/evidence/T5/timing.txt`.

## 8. Decisions already made (with rationale)

- **Free functions over plain value types, with three classes underneath.** The functions
  are the public face; `ClosedForm` is public because a caller that wants several outputs,
  or one input at many volatilities, gains by holding it; the grid solver and the path
  generator are internal.
- **The grid's three entry points stay overloaded per exercise style.** `require_valid`,
  `crank_nicolson` and `crank_nicolson_surface` are each declared twice in `pde.hpp`, and
  each pair forwards to one template in `pde.cpp`, so no logic is written twice. One
  `template <Exercise E>` declaration per pair was considered. For `require_valid` it is
  unsafe: `bump_greeks.hpp` declares a three-argument `require_valid` taking `BumpSizes`,
  and where both headers are included `require_valid(option, market, {})` is today an
  ambiguous call that does not compile, while with a template in the pair's place overload
  resolution prefers the non-template and the same line validates bump sizes instead of a
  grid. A probe that mirrors the two headers' declarations shows both outcomes under g++
  15.2 and clang 22.1.7. The other two pairs have no such neighbour, but the validator and
  the two solvers it guards are one family, and a header in which two are templates and the
  third a pair reads as though the third were different. All three stay pairs.
- **Each implied-vol solver keeps its own stopping rule.** `implied_vol` stops relative to
  the scale the price is computed at; the safeguarded solver stops as page 2.11's experiment
  specifies, and is held to that experiment's committed trace iterate by iterate.
- **The safeguarded solver answers a price outside the bounds with a volatility of zero or
  infinity and its status,** never a NaN; `implied_vol` refuses it.
- **A path's step keeps its two zero tests,** which make an infinity times a zero impossible
  in a path. T3a measured their cost on one machine at 1.5 ms of a 31.5 ms Euler run of 64
  steps, and timed one alternative that returned the same bits, which was no faster.
- **Errors are returned across the WebAssembly boundary and thrown in JavaScript** (§6, 7),
  and arguments are structured-cloned before the module is entered, so that a getter that
  throws does so before any WebAssembly frame exists.
- **An American option reaches the binding as an `exercise: 'american'` field,** which the
  grid's entry points and `bumpGreeks` over the grid accept, and every other entry point
  refuses with a `TypeError`.
- **WebAssembly's own exception handling, not Emscripten's JavaScript-based kind:** at T4 it
  cost 31,650 bytes against 79,115.
- **The grid's half-width defaults to 6 total volatilities.** `pde.hpp` estimates the
  boundary's contribution there as `exp(−α²/2)`, about 1.5e-8; `tests/test_pde.cpp` widens
  the domain at a fixed step on one row and finds the price moves by at most 1.3e-8 for any
  half-width from 3 to 12, against a discretisation error of 2.8e-6.
- **Thomas without pivoting, with its precondition measured:** the dominance margin is
  computed for every grid and reported in `PdeResult`, as is the mesh Péclet number, which
  is reported rather than enforced.
- **No `.clang-format`.** The closest configuration found still rewrites 46 lines in 14
  files — hand-aligned coefficient tables and initialiser rows, continuation lines, switch
  and enum layout — and the sources are not reformatted to suit a tool. `.editorconfig`
  states what the sources already do.

## 9. Deliberately unspecified / out of scope

Out of scope for v1, and entering only by amendment of the constitution: volatility surfaces,
local and stochastic volatility, jumps, rates and curve building, exotics, credit, and live
market data. American exercise is priced by the grid alone, with no closed form and no
early-exercise boundary reported.

Not claimed, because not done here: an MSVC build; a browser loading the artifact in this
repository's CI, which runs it in Node; a timing of the WebAssembly build; any timing beyond
§7.

## 10. History

### 10.1 Milestones

| Milestone | Passed | What it added |
| --- | --- | --- |
| T0 | 2026-08-29 | The golden file: 7,200 grid rows and 34 edge rows from QuantLib 1.43, reproducible byte for byte; CI regenerates it from T1 on. |
| T1 | 2026-08-29 | The CMake project; the closed form and its analytic Greeks; `N(x)` through `erfc`; the golden-file, parity and limit tests; CI on GCC and Clang with warnings as errors. Fable tollgate: PASS. |
| T2 | 2026-08-30 | The shared generator, reproducing the tutorial's known answers; Monte Carlo, exact and Euler, with standard errors, antithetics and a pathwise delta. |
| T3 | 2026-08-31 | Crank–Nicolson with the Thomas solver; implied volatility by Newton and Brent; bump Greeks; American exercise as the stretch; `scales.hpp` and the repaired `require_valid`. |
| T3a | 2026-11-13 | The path API; the second implied-vol solver; `AmericanVanilla` as a type; `scales.hpp` under `detail/`; the three classes; nine repeated pieces of code removed. |
| T4 | 2026-11-13 | The WebAssembly artifact and its release workflow; `crank_nicolson_surface`; released as `v0.4.0`. |
| T5 | — | This document, the timings in §7, comments that carry reasoning and not history, version 1.0.0. In review. |

Each has an evidence pack under `docs/evidence/<milestone>/`.

### 10.2 Reviews, and what they changed

- **T1.** An adversarial review by a second session re-derived every formula, mutated the
  implementation to see whether the suite noticed, and searched the domain for NaNs. It
  found seven real problems, and all were fixed; four of the inputs are kept in
  `tests/test_limits.cpp` as regressions. The Fable tollgate passed T1.
- **T2.** A review flagged a hazard in `require_valid`: its checks formed the same products
  the formulas did, but nothing made them form them the same way. The review was redone by
  Fable at the owner's request: PASS WITH DEFECTS, the defects in the evidence pack and a
  comment, none in the library.
- **T3.** The hazard was real. T1's check took the drift as one product, `(r − q + ½σ²)T`,
  while the formulas form `(r − q)T` and `½σ²T` separately; at `σ = √(2·10³⁰⁰)`, `q =
  10³⁰⁰`, `r = 0`, `T = 10¹⁰` the sum is zero and the input passed, while the two terms are
  −∞ and +∞ and all seven outputs were NaN. The repair was `scales.hpp`, and
  `tests/test_associations.cpp` keeps the input.
- **T3a.** A review for repeated code by a session that had not written the change; each of
  its findings is closed or kept with a reason in `docs/evidence/T3a/review.md`.
- **T4.** An audit by Fable loaded the artifact in Node and in headless Chromium, in a page
  and in a worker, and found the release job would have failed on the tag: its files were
  uploaded under their build paths, not flat. They are now assembled flat and downloaded on
  every push.
- **T5.** The claims in this document were checked one by one against their citations by an
  agent that did not write it. Of 129 claims, 9 said more than their sources held — among
  them that every accepted input avoids a NaN, that the three methods share no arithmetic,
  and that the tutorial's demos already run on the WebAssembly build — and 26 needed a
  narrower wording or a better citation. Each was corrected before 1.0.0;
  `docs/evidence/T5/claims.md` records them.
- **T5 tollgate.** Fable passed T5 with defects, all of them wording: the claims the check
  had narrowed here still stood unnarrowed in the README's opening list and in the file
  comments of `pde.hpp` and `monte_carlo.hpp`, and two settings comments gave figures
  nothing held. `MonteCarloSettings` promised about a cent of standard error at the
  defaults, where §7's option measures 0.077; `PdeSettings` said the suite held every golden
  row to 3e-4 at the defaults, where the suite runs the defaults on 136 rows and the whole
  grid only at a coarser resolution. A scan for more of both kinds found them in
  `normal.hpp`, `bump_greeks.hpp` and three test files. The tollgate's re-check found four
  more, in `bump_greeks.hpp` and `pde.hpp`. All were corrected before 1.0.0;
  `docs/evidence/T5/tollgate.md` lists each.

### 10.3 What the comments used to say

The comments in `include/`, `src/`, `tests/`, `wasm/`, `bench/`, the CMake files and the
workflows give reasoning and name no milestone, review or governance id. Where a comment
carried such history, the text is recorded here as it was. The golden-file and experiment
scripts and their documents, outside that list, still name ids.

Removed at T3a (`docs/evidence/T3a/history.md`):

| Was in | Text removed |
| --- | --- |
| `include/touchstone/scales.hpp`, file comment | "T2's review found exactly that gap and left it for T3; the file below is the repair, and `tests/test_associations.cpp` is what holds it shut." |
| same | "**Three methods must agree (I20).**" |
| `src/black_scholes.cpp`, `require_valid` | "T1 checked their sum instead — `(r - q + 0.5 sigma^2) T` — and that is a different domain, by more than an ulp." and "T1 accepted it and returned a NaN price for it, which is the one outcome this function exists to rule out." |
| `src/monte_carlo.cpp`, `Accumulator::add` | "which is the failure mode T1 ruled out for the closed form" |
| `src/monte_carlo.cpp`, `monte_carlo` | "Rejected rather than returned, for T1's reason:" |
| `src/monte_carlo.cpp`, `total_volatility` | "T3 moved the expression itself into `scales.hpp`; this signature stays because the callers below read better with it." |
| `include/touchstone/monte_carlo.hpp`, `Scheme::EulerMaruyama` | "…and claims need tests (I1)." |
| `include/touchstone/pde.hpp`, `Exercise::American` | "v1 has no closed form for this and QuantLib is the oracle for it" |
| `CMakeLists.txt`, header self-containment | "which at T4 is the Emscripten binding" |

Removed at T5:

| Was in | Text removed |
| --- | --- |
| `include/touchstone/black_scholes.hpp`, file comment | "Scope is the constitution's I21" |
| `include/touchstone/bump_greeks.hpp`, file comment | "Tech-decision B6 puts analytic and bump-and-revalue Greeks in v1" |
| `include/touchstone/implied_vol.hpp`, file comment | "Tech-decision B3 fixes the method" |
| `include/touchstone/implied_vol.hpp`, `price_tolerance` | "the 1e-8 round trip the roadmap asks for" |
| `include/touchstone/monte_carlo.hpp`, file comment | "Constitution I20 wants closed form, Monte Carlo and finite differences to agree. T1 built the first; this is the second" |
| `include/touchstone/monte_carlo.hpp`, `seed` | "(I6)" |
| `include/touchstone/monte_carlo.hpp`, `price_standard_error` | "(I20)" |
| `include/touchstone/normal.hpp`, file comment | "the closed form here at T1, the inverse transform the Monte Carlo will need at T2, the implied-vol solver at T3" |
| `include/touchstone/normal.hpp`, `norm_cdf` | "by decision B3" |
| `include/touchstone/pde.hpp`, file comment | "Constitution I20 wants closed form, Monte Carlo and finite differences to agree. T1 built the first and T2 the second; this is the third" |
| `include/touchstone/pde.hpp`, `PdeSettings` | "at about eight milliseconds", which no measurement supported; §7 has one |
| `include/touchstone/rng.hpp`, file comment | "(constitution I16)" and "Nothing here may be changed without amending the constitution" |
| `include/touchstone/tridiagonal.hpp`, file comment | "Tech-decision B3 puts a Thomas solver at the centre of the Crank-Nicolson scheme and rules out a linear-algebra dependency" |
| `tests/rng_fixture.hpp`, file comment | "at L0" |
| `tests/test_associations.cpp`, file comment | "T1 made the promise", "T2's review found the promise's method fragile … and left it for T3. T3 found it was not merely fragile: one input got through." |
| `tests/test_associations.cpp`, test names | "the input T1 accepted and returned a NaN for"; "the volatility band T2 relies on is still priced" |
| `tests/test_associations.cpp`, four comments | "T1's drift check was"; "T2's Monte Carlo prices this row"; "the whole of T2's accepted band"; "or T1's evidence describes a library that no longer exists" |
| `tests/test_bump_greeks.cpp`, file comment | "the two halves of constitution I20's second sentence meet: \"analytic and bump Greeks likewise\"" |
| `tests/test_closed_form.cpp` | "the roadmap's stated T1 figure" |
| `tests/test_euler.cpp`, file comment | "have to be tested here (I1)" |
| `tests/test_implied_vol.cpp`, file comment | "The roadmap's exit criterion for this is one sentence" |
| `tests/test_limits.cpp`, file comment | "The two limits the roadmap names for T1" and, ending a quotation of `golden/SCHEMA.md`, "and T1 tests them directly rather than against this file." |
| `tests/test_limits.cpp`, regressions | "Each of these came from an adversarial review of this library's first version" |
| `tests/test_monte_carlo.cpp` | "Constitution I6." and "T1 made this a promise for the closed form" |
| `tests/test_pde.cpp` | "the way T1 does" |
| `tests/test_rng.cpp` | "at L0" and "Constitution I6, in its simplest form." |
| `tests/test_three_way.cpp` | "Constitution I20, stated as one test." with its quotation; "the same discipline T2 established"; "the second sentence of I20"; "T2 established that rule"; and the report's opening words, "I20 on" |
| `CMakeLists.txt`, warnings | "Tech-decision B1:" |
| `third_party/CMakeLists.txt` | "the WASM artifact at T4" |
| `.github/workflows/ci.yml` | "Tech-decision B7:"; "T0 proved the generator reproducible by hand. This is that proof as a standing check"; "T3's American reference." |
| `wasm/smoke.test.mjs` | "The one golden row the roadmap's criterion names" |

## 11. Changes to this document

| Date | Change |
| --- | --- |
| 2026-11-14 | First version, with Touchstone 1.0.0. |
