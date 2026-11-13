# T3a — design rulings (2026-11-12)

The owner's rulings from the design walkthrough of 2026-11-10 to 12, made before T4 binds the
library. The walkthrough read every header and source at `dd139e1`; file and line references
below are at that commit. T3a's work order derives from its ROADMAP entry and this note. Where
the two disagree the ROADMAP entry wins, and the disagreement is a defect to report.

## Standing rules (owner, 2026-11-12)

- **No repeated code.** A formula, a rule or a list is written once. This covers the tests as
  well as the library. A review for repeated code, by a session that did not write the change,
  is part of T3a's exit.
- **Common code is common.** Where two types or two code paths share behaviour, they share its
  definition.
- **Comments give the reasoning, not the history.** New and changed comments name no milestone,
  tollgate, review or governance id. The history already in the sources moves to
  `ARCHITECTURE.md` at T5 (ruling 8).
- The library's own rules stand: validate, then compute; an accepted input never returns a NaN;
  each product is formed one way, through `scales.hpp`; raw partial derivatives; same seed, same
  result; no dependency in the library.

## The rulings

| # | Question | Ruling |
|---|---|---|
| 1 | Paths have no home in the library | Add a path API to the library. Every demo moves onto the library at L5 and the TypeScript numerics are then retired (constitution A6). |
| 2 | Two implied-vol solvers | The library gains page 2.11's solver as a second, step-recording method. Newton–Brent stays the default. |
| 3 | Errors across the WASM boundary | Exceptions stay. T4 switches catching on and reports the size both ways. |
| 4 | Exercise style is a solver setting | `AmericanVanilla` becomes a contract type of its own. Condition: common code must be common. |
| 5 | What counts as public | `scales.hpp` moves under `detail/`. The per-path Monte Carlo functions stay public. |
| 6 | Structure | Free functions stay the public face, with three small classes underneath. |
| 7 | Performance | Measure first. No fast path until a number calls for one. |
| 8 | Comments | Keep the reasoning, move the history to `ARCHITECTURE.md` at T5. |
| 9 | Repeated code | Remove all nine repeats listed below, in T3a. |

### 1 · Paths

The site's `PricingBackend` has `brownianPath` and `gbmPath`, and five of its seven demos are
built on them. The library returns no path: `terminal_growth_exact` and `terminal_growth_euler`
(`include/touchstone/monte_carlo.hpp:131-146`) give the terminal factor only, with the drift
fixed at `r − q`.

Build: functions that write a whole path into a caller's `std::span<double>`.

- Brownian: `steps + 1` values, `W₀ = 0`, increments `√dt·Z` taken in order from the seeded
  stream.
- GBM, with the drift `μ` an explicit argument, in two schemes driven by the same normals:
  exact-stepped, `S_(k+1) = S_k · exp((μ − σ²/2)·dt + σ·√dt·Z_k)`, and Euler,
  `S_(k+1) = S_k · (1 + μ·dt + σ·√dt·Z_k)`.

`touchstone-learn/src/demos/paths.ts` is the behaviour to match, to the tolerance `docs/rng.md`
sets for normals. A known-answer fixture for paths is generated here; the site takes it at L5
(I17 runs Touchstone → site). The path generator of ruling 6 is this API's home, and
`monte_carlo` consumes it.

### 2 · The second solver

Page 2.11 teaches Newton with a bisection guard and D9 prints its steps. The library's solver
is Newton from a computed seed with Brent behind it, and records no steps.

Build, beside Newton–Brent: Newton on σ with the analytic vega, inside a bracket that the sign
of each price error narrows; a step that would leave the bracket, or a vega of zero, is
replaced by a bisection. Defaults as the experiment's: start 0.2, bracket [1e-6, 5], stop at a
price error within 1e-12 × max(1, |price|) or a bracket narrower than 1e-14, give up after 100
iterations. A price outside the no-arbitrage bounds is refused with a status, not an exception.
Statuses: `converged`, `below_lower_bound`, `above_upper_bound`, `below_sigma_lo`,
`above_sigma_hi`, `max_iter`. It records every iterate when asked.

Source of truth: `experiments/2_11_where_it_breaks.py` and its JSON. Test: the committed
base-case trace reproduced iterate by iterate. The two solvers share what they have in common:
the price-and-vega evaluation and the bounds. Each keeps its own stopping rule. (Corrected
2026-11-13: this sentence first listed a shared tolerance rule, against the defaults above.)

### 3 · Errors

The library keeps throwing `std::invalid_argument`. At T4 the Emscripten build switches
exception catching on, the binding turns each exception into a JavaScript error (the
TypeScript closed form throws `RangeError` today), and the artifact's size is reported with and
without exception support. Over 500 KB, T4 stops and returns to the owner. Emscripten's
documentation states that catching is off by default at `-O1` and above and that a thrown
exception then terminates the application.

### 4 · Exercise style

Today `PdeSettings::exercise` (`include/touchstone/pde.hpp:126`) makes one `EuropeanVanilla`
value mean two contracts. Build: two contract types and no flag. The fields are defined once:

```cpp
template <Exercise E>
struct Vanilla { double strike{}; double expiry_years{}; OptionType type{OptionType::Call}; };
using EuropeanVanilla = Vanilla<Exercise::European>;
using AmericanVanilla = Vanilla<Exercise::American>;
```

A standalone sketch of this compiled under g++ 13.3 in C++20: existing
`EuropeanVanilla{100.0, 1.0, OptionType::Call}` code builds unchanged, and an `AmericanVanilla`
handed to a function taking `const EuropeanVanilla&` is a compile error. It was not tried
against the library. The grid accepts either type; the closed form, Monte Carlo and implied vol
accept the European one only, with a test that the refusal is at compile time. The European and
American solves share every line that is not specific to early exercise.

### 5 · Public surface

`scales.hpp` moves to `include/touchstone/detail/`. Its functions are already in
`namespace touchstone::detail`. The eight per-path Monte Carlo functions
(`include/touchstone/monte_carlo.hpp:122-201`) stay public, folded into the path API where the
two overlap.

### 6 · Structure

The public face stays free functions over plain value types. Underneath, three classes hold
the state that nothing holds today. No inheritance, no virtual functions.

- **A closed-form evaluation**, built once from a contract and a market: it validates once and
  computes once, and price, delta and the rest read it. Its volatility-independent half (the
  discount factors, the discounted spot and strike, the forward log-moneyness, √T) is what
  implied vol reuses on every step.
- **A grid solver** that owns the grid, the two matrices and the solution. The matrices are
  built once. The solution is readable, because L5's D8 will draw it.
- **A path generator** that owns the random-number generator and the scheme.

Whether each class is public is the session's to propose (Decision — owner may overrule). The
walkthrough's suggestion: the closed-form evaluation public, the other two internal.

Not ruled, included as the walkthrough's default: the two unconstrained templates,
`bump_greeks<Pricer>` and `brent<Function>`, gain concepts.

### 7 · Performance

No fast path in T3a. T5 measures the five entry points and states the numbers with the machine
they were taken on. Rough first timings, 2026-11-12, cloud machine, g++ 13.3 `-O3`, shared
hardware, indicative only: `price_and_greeks` about 60 ns, of which validation about 17 ns;
`implied_vol` at the base case 0.3 to 0.4 µs; `bump_greeks` over the closed form about 0.8 µs;
`monte_carlo` at its defaults 1.4 to 1.8 ms; `crank_nicolson` at its defaults about 6.8 ms.

### 8 · Comments

At T5, with the write-up: the milestone ids, review history and governance ids in
`include/` and `src/` (about thirty references in eleven files, by grep) move to
`ARCHITECTURE.md`. The numerical reasoning stays where it is.

### 9 · The nine repeats

| # | What is written more than once | Where |
|---|---|---|
| R1 | Price, delta, theta, rho and dividend rho: once in `price_and_greeks`, again in each accessor | `src/black_scholes.cpp:240-247`, `251-290` |
| R2 | `S·e^(−qT)` and `K·e^(−rT)`, in five places | `src/black_scholes.cpp:58-59`, `175-176`; `src/implied_vol.cpp:47-48`, `85-88`, `181-183` |
| R3 | Quantities `scales.hpp` exists to form once, formed by hand: the discount factor, `(r − q)·T`, `(σ√T)²`, `σ²` | `src/monte_carlo.cpp:266`, `181`, `180`, `199`, `259`; `src/pde.cpp:209`, `253` |
| R4 | `terminal_growth_exact` and `discounted_growth_exact`: one body, differing by the `r·T` term | `src/monte_carlo.cpp:175-183`, `192-202` |
| R5 | The payoff `max(w·(S − K), 0)`: `payoff` and `intrinsic_at` | `src/monte_carlo.cpp:225-229`; `src/pde.cpp:82-86` |
| R6 | The list of bumped points: built once to validate (ten points) and once to price (twelve) | `src/bump_greeks.cpp:41-65`; `include/touchstone/bump_greeks.hpp:123-163` |
| R7 | One sweep, three copies: the plain solver and the two mirror-image branches of the projected one | `src/tridiagonal.cpp:65-76`, `95-112`, `117-129` |
| R8 | Monte Carlo's hold-aside rule for a non-finite contribution: once for price, once for delta | `src/monte_carlo.cpp:288-291`, `332-341`, `348-349` |
| R9 | The finite-and-signed checks, spelled three ways | `src/black_scholes.cpp:133`; `src/bump_greeks.cpp:15`; `src/implied_vol.cpp:96`, `102`; `src/pde.cpp:183`, `217` |

Smaller: `2^−53` is a literal in both `include/touchstone/rng.hpp:112` and
`include/touchstone/normal.hpp:112`.

The tests were scanned, not read. Repeated five-line blocks account for 224 of 3,684 code
lines, mostly include and `using` blocks. Four real repeats showed: the
`TOUCHSTONE_SWEEP_SCALE` fallback in at least four test files; row parsing in
`american_file.cpp` and `golden_file.cpp`; the table of Greek members in
`test_closed_form.cpp` and `test_parity.cpp`; a path loop twice in `test_euler.cpp`. T3a's
review reads the tests.

## Smaller defects

| # | Defect | Where it is fixed |
|---|---|---|
| F1 | The README describes the library as of T1 (`README.md:5-8`, `45-47`, `74`) | T3a brings the status current; "README final" stays with T5 |
| F2 | `total_volatility(const BlackScholesMarket&, double)` has external linkage and no declaration (`src/monte_carlo.cpp:170-173`) | T3a |
| F3 | "Two matrices, each built once" (`src/pde.cpp:284-286`), but both are rebuilt and rescanned on every step (`306-313`) | T3a, by ruling 6's grid solver |
| F4 | "about eight milliseconds" (`include/touchstone/pde.hpp:74-75`) has no recorded measurement | T5 measures it or cuts it |
| F5 | Settings are defaulted for `implied_vol` and the closed-form `bump_greeks`, required for `monte_carlo` and `crank_nicolson` | T3a defaults all four |
| F6 | No `.clang-format`, `.clang-tidy` or `.editorconfig` | Open; the owner's |
| F7 | MSVC and Emscripten have never built the library | T4 closes the Emscripten half |
| F10 | T3's owner action 4, grid half-width 6 against 3 | Left at 6; the owner has not overruled |
| F11 | No version tags; CMake says 0.1.0 | T4 tags `v0.4.0`; `v1.0.0` stays with T5 |

F8 and F9 are the site's and are listed below.

## For T4

- The binding carries every `PricingBackend` method and also `monte_carlo`, `crank_nicolson`
  and `bump_greeks`, because L5 needs them for D7, D8 and D10 and cannot edit this repository
  (I18).
- Exceptions and size as ruling 3. Tag as F11.

## For the site (L track; not T3a's to change)

- At L5 every demo moves onto the WASM backend and the TypeScript numerics are removed once the
  two backends agree (A6). D9's trace then comes from the library's second solver.
- `src/demos/types.ts`, `tsBackend.ts`, `paths.ts` and `impliedVol.ts` carry comments that
  describe the earlier plan.
- F8: `requireValid` at `src/demos/blackScholes.ts:106` still checks the summed drift
  `(r − q + ½σ²)·T`, the form T3 replaced here (`src/black_scholes.cpp:181-202`). T3's pinned
  input passes it and gives `d₁ = NaN` by that file's own arithmetic. The walkthrough
  replicated the arithmetic; it did not run the module.
- F9: `types.ts` and `paths.ts` say the library exposes path sampling. It does after T3a.

## What the walkthrough did not do

It read all of `include/` and `src/`, both CMake files, the CI workflow, and the decisions in
the T1 to T3 packs. It did not read the 6,429 lines of tests, the golden generators or the
experiments, and it did not run the test suite. Its timings are rough. "No wrong formula found"
is a statement about reading, not about re-derivation.
