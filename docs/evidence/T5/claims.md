# T5 — claims map for `ARCHITECTURE.md`

Every claim in `ARCHITECTURE.md`, numbered in the order it appears, against the test or file
that holds it. **Asserted** means a test fails if the claim stops being true. **Reported**
means a test or script prints the number and the pack quotes it, without a test bounding it
there. **Source** means the claim is about what the code, a build file or a document says,
and the cited file is where it can be read. Paths are from the repository root; line numbers
are at this branch's head and are given only where a file is long.

The last section records the independent check of every row: who made it, what it found and
what changed. The section before it maps what changed after the T5 tollgate: the sentences
added to `ARCHITECTURE.md`, and the README and comment sentences the tollgate's defects and
the scan that followed them rewrote.

## §0 Status, §1 What this is

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 1 | The document describes Touchstone 1.0.0 and is written as the source the portfolio's architecture page will be rendered from. | `CMakeLists.txt` (`VERSION 1.0.0`); `wasm/smoke.test.mjs` (the module's `version` equals it); `ROADMAP.md` T5 and P2 deliverables (P2 not yet run) | Source; asserted for the module |
| 2 | Prices European calls and puts on one underlying under Black–Scholes–Merton with constant rate, volatility and continuous dividend yield. | `include/touchstone/black_scholes.hpp` (file comment, `BlackScholesMarket`); `include/touchstone/contract.hpp` | Source |
| 3 | Three ways — closed form with six analytic Greeks, Monte Carlo, Crank–Nicolson — independent in method and not in every line: all three form scalars through `detail/scales.hpp`, the Monte Carlo and the grid share `payoff`, and the Monte Carlo takes its discount factor and discounted strike from `ClosedFormQuote`. | `include/touchstone/black_scholes.hpp`, `monte_carlo.hpp`, `pde.hpp`, `contract.hpp` (`payoff`); `src/monte_carlo.cpp` (`ClosedFormQuote quote`, `quote.discount_factor()`, `quote.discounted_strike()`, ~lines 222–318) | Source |
| 4 | The finite-difference grid also prices the American contract. | `include/touchstone/pde.hpp` (`crank_nicolson(const AmericanVanilla&, …)`); `tests/test_american.cpp` | Asserted |
| 5 | Implied volatility by two solvers; Greeks by bumping any pricer; Brownian and GBM paths from a frozen generator. | `include/touchstone/implied_vol.hpp`; `bump_greeks.hpp` (`VanillaPricer`); `paths.hpp`; `rng.hpp`, `docs/rng.md` | Source |
| 6 | One half of a pair with learn.garethcooke.com, whose demos are to run on this library compiled to WebAssembly; at 1.0.0 they run on a TypeScript backend, and moving them is L5, not yet run. | `ROADMAP.md` (L1 "on the TypeScript backend"; L5 unticked); `CONSTITUTION.md` I15 (A6); `wasm/binding.cpp` file comment | Source (programme documents; the site is not in this repository) |
| 7 | The closed form agrees with QuantLib's reference values on every row of the committed reference file (7,200 grid rows and 34 edge rows) within the tests' asserted tolerances. | `tests/test_closed_form.cpp` against `golden/bs_vanilla.json` (1e-10 grid, 1e-8 edge block; row counts asserted) | Asserted; worst 2.841e-13 (grid), 1.619e-11 (edge) reported in `tests.txt` §1 |
| 8 | The grid agrees with QuantLib's reference values on every row of the 7,200-row main block at 512 space intervals by 256 time steps, coarser than its defaults. (Reworded after the tollgate: it said "at a stated resolution" and stated none.) | `tests/test_pde.cpp` ("golden grid by Crank-Nicolson", 7,200 rows at 512 × 256; the edge block is only asserted to price more than 20 of 34) | Asserted |
| 9 | The Monte Carlo agrees with the closed form in units of its own standard error on the rows where enough paths finish in the money to score it. | `tests/test_monte_carlo.cpp` ("the golden grid, priced by Monte Carlo": 6,147 rows scored at 32,768 paths, worst \|z\| 3.559 against a bound of 5.648; 323 more re-run at 1,048,576; 764 too rare to score, 630 of them priced at exactly zero) | Asserted on the scored rows; the rest reported |
| 10 | The three agree side by side on 136 of the rows within stated, asserted tolerances. | `tests/test_three_way.cpp` (136 rows; grid and Monte Carlo each against the closed form, Monte Carlo scored on 119) | Asserted (each against the closed form; grid against Monte Carlo by implication, as the test states) |
| 11 | An input the closed form, the Monte Carlo or the path functions accept never produces a NaN. | See 85 | Asserted |
| 12 | A seed draws the same numbers here as the tutorial's TypeScript generator recorded in the committed fixture. | `tests/test_rng.cpp` against `golden/rng-known-answers.json`; `wasm/smoke.test.mjs` | Asserted (uniforms bit for bit; normals 30 of 30 bit for bit, tolerance 1e-12) |
| 13 | The timings in §7 are for one machine on one date. | `docs/evidence/T5/timing.txt` | Source |
| 14 | §7 is a measurement on one machine, not a comparison. | `ARCHITECTURE.md` §7; `docs/evidence/T5/timing.txt` §5 | Source |
| 15 | CI does not build with MSVC. | `.github/workflows/ci.yml` (gcc and clang jobs only); `CMakeLists.txt` warnings comment | Source |
| 16 | This repository's CI does not run a browser. | `.github/workflows/ci.yml`, `wasm.yml` (Node 22 only) | Source |
| 17 | No term structure, no stochastic volatility, no second underlying. | `CONSTITUTION.md` I21; `include/touchstone/black_scholes.hpp` (`BlackScholesMarket` holds one spot and constant `vol`, `rate`, `dividend_yield`) | Source |
| 18 | QuantLib is the oracle and Touchstone does not link it. | `CMakeLists.txt` (the library links only `touchstone_warnings`); `pyproject.toml` (QuantLib in the Python environment); `golden/generate_bs_vanilla.py` | Source |

## §2 System overview

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 19 | QuantLib-Python, run by `golden/*.py`, produces `golden/bs_vanilla.json` and `golden/american_vanilla.json`. | `golden/generate_bs_vanilla.py`, `golden/generate_american_vanilla.py`; each JSON's `oracle` block | Source |
| 20 | Both files are regenerated and re-derived independently in CI. | `.github/workflows/ci.yml`, job `golden` (`verify_*` and regenerate-then-`git diff --exit-code`) | Asserted in CI |
| 21 | The tests are doctest, with 18 ctest entries. | `tests/CMakeLists.txt` (17 suites in the loop, plus `ts_all`) | Source |
| 22 | The tests also read the RNG fixture, the path fixture and page 2.11's experiment JSON. | `tests/CMakeLists.txt` (`TOUCHSTONE_RNG_FIXTURE_PATH`, `TOUCHSTONE_PATHS_FIXTURE_PATH`, `TOUCHSTONE_EXPERIMENT_2_11_PATH`) | Source |
| 23 | The library uses the standard library only. | See 90 | Source |
| 24 | The binding is translation only and produces `touchstone.mjs` and `touchstone.wasm`. | `wasm/binding.cpp` file comment; `wasm/CMakeLists.txt` | Source |
| 25 | The artifact is smoke-tested in Node in CI. | `.github/workflows/ci.yml` calls `wasm.yml`, step "Smoke test" | Asserted in CI |
| 26 | A GitHub release is made on a `v*` tag. | `.github/workflows/release.yml`; the `v0.4.0` release, published 2026-11-13 with four assets (`gh release view v0.4.0`) | Source; it has run once |
| 27 | The release is for the tutorial's demos. | `.github/workflows/release.yml` file comment; `CONSTITUTION.md` I17 | Source (design intent; L5 has not run) |
| 28 | The library is a static library of seven translation units and seventeen headers. | `CMakeLists.txt` (`add_library(touchstone STATIC` with seven sources; `TOUCHSTONE_HEADERS` lists seventeen) | Source |
| 29 | Its consumers here are the tests, the binding, the header self-containment check, and the timing harness, which is built with the tests and never run by them. | `tests/CMakeLists.txt`, `wasm/CMakeLists.txt`, `bench/CMakeLists.txt`; `CMakeLists.txt` (`touchstone_header_check`; `add_subdirectory(bench)` inside `if(TOUCHSTONE_BUILD_TESTS)`); no `add_test` names the harness | Source |

## §3 Repo layout

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 30 | `include/touchstone/` holds the public headers; `detail/` is internal. | `include/touchstone/detail/grid_solver.hpp`, `path_generator.hpp` ("Internal rather than public"); `namespace touchstone::detail` | Source |
| 31 | `src/` implements closed form, Monte Carlo, paths, grid, implied vol, bump Greeks, tridiagonal solvers. | `src/` (seven files) | Source |
| 32 | `tests/`: doctest suites, one ctest entry per suite and one that runs them all. | `tests/CMakeLists.txt` | Source |
| 33 | `wasm/`: binding, error shim, build script, Node smoke test. | `wasm/binding.cpp`, `errors.post.js`, `build.sh`, `smoke.test.mjs` | Source |
| 34 | `bench/`: the timing harness behind §7. | `bench/timing.cpp` | Source |
| 35 | `golden/`: QuantLib reference values, generators, independent verifiers, two known-answer fixtures. | `golden/` (`generate_*.py`, `verify_*.py`, `rng-known-answers.json`, `paths-known-answers.json`) | Source |
| 36 | `experiments/`: numpy scripts behind Part 2 pages, each with committed JSON. | `experiments/README.md`; `experiments/*.py`, `*.json` | Source |
| 37 | `third_party/`: doctest and nlohmann/json, single headers, linked by the test executable only. | `third_party/CMakeLists.txt` (`touchstone_vendor`); `tests/CMakeLists.txt` | Source |
| 38 | `docs/`: curriculum, technology decisions, RNG specification, rulings, evidence packs. | `docs/quant-learn-index-v1.md`, `tech-decisions-v1.md`, `rng.md`, `briefs/`, `evidence/` | Source |

## §4 The public surface

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 39 | Free functions over plain value types, with three classes underneath: `ClosedForm` (with `ClosedFormQuote`) public, `detail::GridSolver` and `detail::PathGenerator` internal. | `include/touchstone/black_scholes.hpp`; `include/touchstone/detail/grid_solver.hpp`, `path_generator.hpp` | Source |
| 40 | No inheritance and no virtual function anywhere in the library. | `include/`, `src/` (no `virtual`, no base-class list; checked by grep, `build.txt` §5) | Source |
| 41 | Entry-point table: headers and contracts as listed. | The headers named in the table; `tests/test_contract.cpp` for which contracts each accepts | Source; contracts asserted |
| 42 | `monte_carlo` defaults: seed 1; 32,768 paths; exact terminal sampling; no antithetics. | `include/touchstone/monte_carlo.hpp` (`MonteCarloSettings`: `seed{1}`, `paths{1u << 15}`, `Scheme::ExactTerminal`, `antithetic{false}`) | Source |
| 43 | Grid defaults: 1,024 intervals; 512 steps; half-width 6; 2 Rannacher steps; cell-averaged payoff; every level kept. | `include/touchstone/pde.hpp` (`PdeSettings`, `SurfaceSampling`) | Source |
| 44 | `implied_vol` defaults: tolerance 1e-14 of the price scale; volatility up to 10; 64 Newton steps. | `include/touchstone/implied_vol.hpp` (`ImpliedVolSettings`) | Source |
| 45 | `implied_vol_safeguarded` defaults: 0.2; [1e-6, 5]; 1e-12; 1e-14; 100. | `include/touchstone/implied_vol.hpp` (`SafeguardedSettings`); `tests/test_implied_vol.cpp` ("the defaults are the experiment's") | Source; asserted against the experiment |
| 46 | `bump_greeks` defaults: closed form or any `VanillaPricer`; 1e-6 and 3e-5 relative spot; 1e-6 vol, rate, yield; 1e-5 years. | `include/touchstone/bump_greeks.hpp` (`BumpSizes`, the two overloads) | Source |
| 47 | Path defaults: seed 1; horizon 1. | `include/touchstone/paths.hpp` (`PathGrid`) | Source |
| 48 | `EuropeanVanilla` and `AmericanVanilla` are both `Vanilla<E>`, fields written once. | `include/touchstone/contract.hpp`; `tests/test_contract.cpp` (`is_same_v` static_asserts) | Asserted at compile time |
| 49 | The grid accepts either; every other pricing entry point accepts the European one only and refuses the American one at compile time; `payoff` accepts either. | `tests/test_contract.cpp` (concepts and `static_assert`s over the closed form, `ClosedForm`, Monte Carlo, implied vol, bump Greeks, the grid and `payoff`); the other `require_valid` overloads take `const EuropeanVanilla&` by signature | Asserted at compile time for the functions the concepts name; source for the rest |
| 50 | `with_exercise` converts; nothing converts implicitly. | `tests/test_contract.cpp` (`!is_convertible_v` both ways; "with_exercise keeps every field") | Asserted |
| 51 | `BlackScholesMarket` is the market; `QuotedMarket` is it without the volatility. | `include/touchstone/black_scholes.hpp` | Source |
| 52 | Every entry point validates before it computes and refuses with `std::invalid_argument` naming the reason; each family has a `require_valid` a caller can call; two refusals sit outside them: `monte_carlo`'s total-variance check and `crank_nicolson_surface`'s stride of zero. | `black_scholes.hpp`, `monte_carlo.hpp`, `pde.hpp`, `implied_vol.hpp`, `bump_greeks.hpp`, `paths.hpp` (declarations); `src/monte_carlo.cpp` (~237), `src/pde.cpp` (`sample_to_today`); the closed form validates in `ClosedForm`'s constructor; the tests in 84 | Source; refusals asserted |
| 53 | Every Greek is a raw partial derivative: vega per 1.00 vol, theta per year, rho per 1.00 rate. | `include/touchstone/black_scholes.hpp` (`PriceAndGreeks`); `golden/SCHEMA.md`; `tests/test_closed_form.cpp` against the file's conventions | Asserted (against QuantLib in those units) |

## §5 How each method is built

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 54 | `N(x)` is evaluated through `std::erfc`. | `include/touchstone/normal.hpp` (`norm_cdf`) | Source |
| 55 | At x = −10 the subtraction `1 − N(10)` returns zero where the true value is 7.6e-24. | `include/touchstone/normal.hpp` comment; `tests/test_normal.cpp` (the subtraction demonstrated, ~line 73) | Asserted |
| 56 | A `ClosedForm` validates once, computes once, serves all seven outputs. | `include/touchstone/black_scholes.hpp`, `src/black_scholes.cpp` | Source (the accessors are asserted within 1e-15 of `price_and_greeks` and measured identical, `tests/test_closed_form.cpp`) |
| 57 | `ClosedFormQuote` is the volatility-free half, and both solvers build it once per solve. | `include/touchstone/black_scholes.hpp`; `src/implied_vol.cpp` (one `ClosedFormQuote` per search, ~lines 75–104); `tests/test_closed_form.cpp` (quote reused: 7,234 rows, 0 values not identical) | Source; reuse asserted |
| 58 | The Monte Carlo samples the terminal law exactly from one normal per path, or steps Euler–Maruyama over `steps` equal steps from the same generator. | `include/touchstone/monte_carlo.hpp`, `paths.hpp` (`Scheme`); `include/touchstone/detail/path_generator.hpp` | Source |
| 59 | It reports a standard error beside the price, and a pathwise delta with its own standard error. | `include/touchstone/monte_carlo.hpp` (`MonteCarloResult`); `tests/test_monte_carlo.cpp` ("the standard error is the spread of the estimator"; pathwise delta vs analytic in standard errors) | Asserted |
| 60 | With antithetics the sampling unit is the pair and the standard error comes from pair means. | `include/touchstone/monte_carlo.hpp` (`antithetic`, `samples`); `tests/test_monte_carlo.cpp` ("the standard error is the spread of the estimator", antithetic leg) | Asserted |
| 61 | An Euler path may go negative and is not clipped. | `include/touchstone/paths.hpp` (`Scheme::EulerMaruyama`); `include/touchstone/contract.hpp` (`payoff` at a negative spot); `tests/test_contract.cpp` (`payoff(put, -5.0) == 105.0`) | Source; payoff asserted |
| 62 | The grid is in log-spot, where the coefficients are constant and one uniform grid serves every spot. | `include/touchstone/pde.hpp` ("The equation") | Source |
| 63 | Crank–Nicolson after two fully implicit half-step pairs (Rannacher), from a cell-averaged payoff. | `include/touchstone/pde.hpp` (`rannacher_steps{2}`, `smooth_payoff{true}`); `src/pde.cpp` (`advance`, `cell_average_payoff`); `tests/test_pde.cpp` (convergence order with the start; gamma at the strike with and without it; both payoff constants) | Source; convergence asserted |
| 64 | The spot is exactly on a node; the price is a node value and delta and gamma central differences about it. | `include/touchstone/pde.hpp` (`crank_nicolson`); `src/pde.cpp` (`make_grid`, `result`); `tests/test_pde.cpp` (spot node at `ln S`) | Asserted |
| 65 | Each step is a Thomas sweep without pivoting. | `include/touchstone/tridiagonal.hpp`; `src/tridiagonal.cpp`; `tests/test_tridiagonal.cpp` | Asserted |
| 66 | The diagonal dominance is measured and reported, with the mesh Péclet number, rather than assumed. | `include/touchstone/pde.hpp` (`PdeResult::dominance_margin`, `mesh_peclet`); `tests/test_pde.cpp` ("grid diagnostics": smallest dominance 1.000, worst Péclet 0.10) | Asserted |
| 67 | The American contract replaces the sweep with its projected form and raises the boundary to immediate exercise; every other line is shared. | `src/pde.cpp` (`GridSolver<E>::step`, `boundary_value`, `if constexpr`); `tests/test_tridiagonal.cpp` ("projected sweep vs PSOR"); `tests/test_american.cpp` | Source; asserted against three QuantLib lattices |
| 68 | `crank_nicolson_surface` runs the same solve and its last level at the spot is `crank_nicolson`'s price, bit for bit. | `tests/test_pde.cpp` ("the surface's last level, at the spot, is crank_nicolson's price") | Asserted |
| 69 | The two implied-vol solvers share the volatility-free half and the bounds and keep separate stopping rules. | `include/touchstone/implied_vol.hpp` (second solver's comment); `src/implied_vol.cpp` (`floor_of`, `ceiling_of`, `ClosedFormQuote`) | Source |
| 70 | `implied_vol` runs Newton from the Manaster–Koehler seed (Brenner–Subrahmanyam at the money) and hands over to Brent on `[0, max_vol]`, which always finishes because the bracket is established. | `include/touchstone/implied_vol.hpp` (`implied_vol`); `tests/test_implied_vol.cpp` ("Brent finishes what Newton cannot": 982 of 1,029 rows through Brent, worst reprice 1.07e-12) | Source; Brent path asserted |
| 71 | `implied_vol_safeguarded` is page 2.11's solver: Newton in a sign-narrowed bracket, bisecting where Newton would leave it, recording iterates on request. | `include/touchstone/implied_vol.hpp`; `tests/test_implied_vol.cpp` (committed trace iterate by iterate, worst 7.105e-15; "steps are recorded only when asked") | Asserted |
| 72 | It answers a price outside the bounds with a status and a volatility of zero or infinity, never a NaN; `implied_vol` refuses such a price with `std::invalid_argument`. | `include/touchstone/implied_vol.hpp` (`SafeguardedResult::vol`, `require_valid`); `tests/test_implied_vol.cpp` ("page 2.11's refusals…", "prices no volatility produces are refused"); `wasm/smoke.test.mjs` | Asserted |
| 73 | Bump Greeks take thirteen prices: the base and six central pairs — vol, rate, yield, expiry, and two in spot, narrow for delta and wider for gamma. | `include/touchstone/bump_greeks.hpp` (`bump_greeks`, `detail::Bumped`: twelve points) | Source |
| 74 | A second difference balances truncation against cancellation at a larger bump than a first difference. | `include/touchstone/bump_greeks.hpp` ("Choosing the bump") | Source (analysis), shown by 75 |
| 75 | `tests/test_bump_greeks.cpp` sweeps delta, gamma, vega and rho bumps from 1e-9 to 1e-2 and asserts each is most accurate at the default size (1e-6; 3e-5 for gamma) and more than ten times less accurate at both ends. | `tests/test_bump_greeks.cpp` ("the bump size has an optimum…": `sizes[]`, `axes[]`, `CHECK(best == expected)`, the two `* 10.0` checks) | Asserted |
| 76 | The generator is xoshiro128\*\* seeded through the MurmurHash3 finaliser, with 53-bit uniforms and AS241 normals, frozen by `docs/rng.md`. | `include/touchstone/rng.hpp`, `normal.hpp`; `docs/rng.md`; `tests/test_rng.cpp` | Source; fixture asserted |
| 77 | `brownian_path` and `gbm_path` write a whole path into a caller's span, one normal per step; both GBM schemes are driven by the same normals. | `include/touchstone/paths.hpp`; `tests/test_paths.cpp` (fixture; "increments are the stream's normals"; exact scheme on the same path) | Asserted |
| 78 | The Monte Carlo draws from the same generator through the same step. | `include/touchstone/detail/path_generator.hpp` (file comment); `tests/test_paths.cpp` ("Monte Carlo's per-path functions are one step of the same generator") | Asserted |
| 79 | The products the domain checks guard (σ√T, ½σ²T, (r − q)T, the discount factors and the rest) are each written once in `detail/scales.hpp`, and the checks call the same functions. | `include/touchstone/detail/scales.hpp`; `src/black_scholes.cpp`, `src/pde.cpp`, `src/monte_carlo.cpp`; `tests/test_associations.cpp` | Source; associations asserted |
| 80 | A check grouping a product differently guards a different set of inputs; §10.2 has the input. | `tests/test_associations.cpp` ("the input a check on the summed drift accepts…") | Asserted |
| 81 | The binding is translation only: plain objects in, value types across, plain objects and `Float64Array`s back, under `PricingBackend`'s names, with `monteCarlo`, `crankNicolson`, `crankNicolsonSurface`, `bumpGreeks` beyond it. | `wasm/binding.cpp` (file comment, registrations at the end; `types.ts` is the site's and not in this repository); `wasm/smoke.test.mjs` (each called) | Source; each extra entry point asserted against the closed form or, for the surface, against `crankNicolson` |
| 82 | `defaults()` exports the default settings of every bound entry point that takes settings. | `wasm/binding.cpp` (`defaults`: five settings types); `wasm/smoke.test.mjs` ("the library's defaults are the module's": five keys) | Asserted |
| 83 | The artifact is one ES module and one `.wasm`, built by Emscripten 6.0.13 with C++ exception catching on. | `wasm/CMakeLists.txt` (`MODULARIZE`, `EXPORT_ES6`); `.github/workflows/wasm.yml` (`EMSDK_VERSION`); `CMakeLists.txt` (`TOUCHSTONE_WASM_EXCEPTIONS` ON, `-fwasm-exceptions`) | Source |

## §6 Invariants

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 84 | Validate, then compute; the six test files assert refusals. | `tests/test_limits.cpp` (~547), `test_monte_carlo.cpp` ("settings that cannot be run are refused", total variance), `test_pde.cpp` (~515), `test_implied_vol.cpp` (~410, ~654), `test_bump_greeks.cpp` (~258), `test_paths.cpp` (~256) | Asserted |
| 85 | An input the closed form, the Monte Carlo or the path functions accept never gives a NaN; closed-form price, delta, vega, rho, dividend rho finite, gamma and theta possibly infinite; a Monte Carlo estimate or path value may saturate to infinity; the grid, implied vol and bump Greeks are not swept; `norm_inv` at p ≥ 1 is the documented exception. | `include/touchstone/black_scholes.hpp` (`require_valid` comment); `tests/test_limits.cpp` (domain sweep: 16,570 priced, 9,350 refused, 550 infinite gammas, no NaN); `tests/test_monte_carlo.cpp` ("no input the closed form accepts…", infinite standard error ~720); `tests/test_paths.cpp` ("an accepted path never holds a NaN"); `tests/test_associations.cpp`; `include/touchstone/normal.hpp`, `tests/test_rng.cpp` (`isnan(norm_inv(1.0))`) | Asserted |
| 86 | Why: an infinity compares correctly against a tolerance; a NaN makes every ordered comparison false, so `error <= tolerance` fails on it and `error > tolerance` passes it. | IEEE 754 comparison semantics; `include/touchstone/black_scholes.hpp` (`require_valid` comment) | Source |
| 87 | Each product is formed once, in one association, through `detail/scales.hpp`, because floating-point multiplication does not associate. | `include/touchstone/detail/scales.hpp` (file comment); `tests/test_associations.cpp` | Asserted |
| 88 | Same seed, same result, bit for bit; the generator reproduces the TypeScript fixture. | `tests/test_rng.cpp` ("same seed, same numbers"; fixture); `tests/test_monte_carlo.cpp` ("same seed, same result"); `tests/test_paths.cpp` ("same seed, same path"); `wasm/smoke.test.mjs` | Asserted |
| 89 | The exercise style is part of the contract's type; `test_contract.cpp` fails by not compiling. | `tests/test_contract.cpp` | Asserted at compile time |
| 90 | No dependency: the library includes nothing outside the standard library; the vendored headers are linked by the test executable only. | `CMakeLists.txt` (`target_link_libraries(touchstone PRIVATE touchstone_warnings)`); `tests/CMakeLists.txt` (`touchstone_vendor`); every `#include` in `include/`, `src/` (`build.txt` §5) | Source |
| 91 | Nothing is thrown across the WebAssembly boundary: each bound function catches and returns an error, `errors.post.js` throws it; `RangeError`, `TypeError`, `Error`. | `wasm/binding.cpp` ("Errors"); `wasm/errors.post.js`; `wasm/smoke.test.mjs` (RangeError, TypeError, thrown-getter tests) | Asserted for `RangeError` and `TypeError`; source for `Error` |
| 92 | An exception unwinding WebAssembly frames leaves the stack pointer behind; T4 measured a module killed at call 2,074. | `docs/evidence/T4/summary.md` (Done 3); `docs/evidence/T4/tests.txt` §2 | Reported (T4) |
| 93 | `wasm/smoke.test.mjs` makes 300,000 refused calls, 100,000 of them a throwing getter refused before the module is entered, and then reproduces the RNG fixture and one golden row exactly as before. | `wasm/smoke.test.mjs` ("survives a hundred thousand refusals of each kind") | Asserted |

## §7 Timings

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 94 | `bench/timing.cpp` times the five entry points at their defaults on the stated option and market; `implied_vol` inverts the closed-form price at σ = 0.2; `bump_greeks` is the closed-form overload. | `bench/timing.cpp` | Source |
| 95 | Taken 2026-11-14 on a Ryzen 7 3800X, Windows 11 Pro 10.0.26200, g++ 15.2.0 (MinGW-Builds), `-O3 -DNDEBUG -std=c++20`, static library. | `docs/evidence/T5/timing.txt` §3 | Reported |
| 96 | 25 rounds per process, pinned to one logical core at high priority; median of five batches per round; a batch at least 20 ms. | `bench/timing.cpp` (constants); `docs/evidence/T5/timing.txt` §2 (launch command) | Source |
| 97 | The table gives each of three processes' median round, lowest to highest: 74–76 ns, 336–349 ns, 1.39–1.41 µs, 1.78–1.79 ms, 4.71–4.74 ms. | `docs/evidence/T5/timing.txt` §4, §6 (raw output) | Reported |
| 98 | The WebAssembly build was not timed; nothing was tuned for this measurement — the library timed is main's, object file for object file; there is no fast path. | `docs/evidence/T5/timing.txt` §5; `docs/evidence/T5/tests.txt` §2(a) | Source; identity shown by the objects (T3a's earlier tuning of `monte_carlo` is in main's library and `docs/evidence/T3a/timing.txt`) |

## §8 Decisions

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 99 | Free functions are the public face; `ClosedForm` public because holding it saves repeated validation and arithmetic; grid solver and path generator internal. | `include/touchstone/black_scholes.hpp` ("The evaluation behind the free functions"); `ROADMAP.md` T3a passed line | Source |
| 100 | The three grid pairs are declared twice each and forward to one template in `pde.cpp`. | `include/touchstone/pde.hpp`; `src/pde.cpp` (`validated_grid`, `solve_to_today`, `sample_to_today`) | Source |
| 101 | `bump_greeks.hpp` declares a three-argument `require_valid` taking `BumpSizes`. | `include/touchstone/bump_greeks.hpp` | Source |
| 102 | A probe mirroring the two headers' declarations shows: with both visible, `require_valid(option, market, {})` is ambiguous today, and with a template in the pair's place resolves to the `BumpSizes` overload, under g++ 15.2 and clang 22.1.7. | `docs/evidence/T5/build.txt` §4 (the probe and both compilers' output for both cases) | Reported (probe; not the real headers) |
| 103 | The other two pairs have no such neighbour. | `include/`, `src/`, `tests/`, `wasm/` (no other declaration of `crank_nicolson` or `crank_nicolson_surface`) | Source |
| 104 | Each implied-vol solver keeps its own stopping rule; the safeguarded one is held to page 2.11's committed trace iterate by iterate. | `include/touchstone/implied_vol.hpp`; `tests/test_implied_vol.cpp`; `ROADMAP.md` T3a passed line | Asserted |
| 105 | The safeguarded solver answers a price outside the bounds with zero or infinity and its status, never a NaN; `implied_vol` refuses it. | As 72; `ROADMAP.md` T3a passed line | Asserted |
| 106 | A path's step keeps two zero tests, which make an infinity times a zero impossible; T3a measured 1.5 ms of a 31.5 ms Euler run of 64 steps, and timed one alternative returning the same bits, no faster. | `include/touchstone/detail/path_generator.hpp` (`GbmStep`); `tests/test_paths.cpp` ("an accepted path never holds a NaN"); `docs/evidence/T3a/timing.txt` §2–4 (after 31.506, attribution 30.047; exp2) | Asserted (no NaN); reported (cost) |
| 107 | Errors returned across the boundary; arguments structured-cloned first so a throwing getter throws before any WebAssembly frame exists. | `wasm/errors.post.js`; `docs/evidence/T4/summary.md` (Decisions); `wasm/smoke.test.mjs` ("a thrown getter on an argument reaches the caller as itself") | Asserted |
| 108 | An American option reaches the binding as `exercise: 'american'`; the grid's entry points and `bumpGreeks` over the grid accept it, every other entry point refuses with a `TypeError`. | `wasm/binding.cpp` (`european`, the grid pricer in `bumped`); `wasm/smoke.test.mjs` (grid test; American put through `bumpGreeks`; `monteCarlo` refusal) | Asserted |
| 109 | WebAssembly exception handling, not Emscripten's JavaScript kind: 31,650 bytes against 79,115 at T4. | `docs/evidence/T4/summary.md` (Decisions); `docs/evidence/T4/build.txt` | Reported (T4) |
| 110 | Half-width 6 by default; `pde.hpp` estimates the boundary's contribution there as exp(−α²/2) ≈ 1.5e-8; `tests/test_pde.cpp` finds the price moves at most 1.3e-8 for α from 3 to 12 on one row, against a discretisation error of 2.8e-6. | `include/touchstone/pde.hpp` (`half_width_sigmas`); `tests/test_pde.cpp` ("domain width at a fixed dx"; `tests.txt` §1); `docs/briefs/T3a-design-rulings.md` F10 | Source (estimate); reported and asserted (test) |
| 111 | The dominance margin is computed for every grid and reported in `PdeResult`, as is the Péclet number, reported rather than enforced. | `src/pde.cpp` (`GridSolver` constructor, `result`); `include/touchstone/pde.hpp` | Source |
| 112 | No `.clang-format`: the closest configuration still rewrites 46 lines in 14 files — coefficient tables, initialiser rows, continuation lines, switch and enum layout; `.editorconfig` states what the sources do. | `docs/evidence/T5/build.txt` §6 (the configurations, the counts, the whole remaining diff); `.editorconfig`, `build.txt` §7 | Reported |

## §9 Out of scope

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 113 | Out of scope for v1, entering only by amendment: surfaces, local and stochastic vol, jumps, rates and curves, exotics, credit, live market data. | `CONSTITUTION.md` I21; `ROADMAP.md` "Later (v2)" | Source |
| 114 | American exercise priced by the grid alone, no closed form, no early-exercise boundary reported. | `include/touchstone/contract.hpp` (`Exercise::American`); `include/touchstone/pde.hpp` (`PdeResult` fields); `tests/test_contract.cpp` | Source; closed-form refusal asserted |
| 115 | Not done here: an MSVC build; a browser in CI; a timing of the WebAssembly build; any timing beyond §7. | `.github/workflows/ci.yml`, `wasm.yml`; `docs/evidence/T5/timing.txt` §5 | Source |

## §10 History

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 116 | Milestone dates: T0, T1 2026-08-29; T2 2026-08-30; T3 2026-08-31; T3a, T4 2026-11-13. | `ROADMAP.md` ("Passed" lines) | Source |
| 117 | T0: 7,200 grid rows and 34 edge rows from QuantLib 1.43, reproducible byte for byte; CI regenerates it from T1 on. | `golden/bs_vanilla.json` (`oracle.version`); `tests/test_closed_form.cpp` (7200 and 34 asserted); `docs/evidence/T0/summary.md` (by hand); `.github/workflows/ci.yml` (first in 704aecc, T1) | Asserted (counts); source |
| 118 | T1's, T2's, T3's, T3a's and T4's contents as listed. | `ROADMAP.md` (each milestone's deliverables and passed line); `docs/evidence/T3/summary.md` (Done 1, `scales.hpp`) | Source |
| 119 | T1's Fable tollgate: PASS. | `docs/evidence/T1/verdict.md` | Source |
| 120 | T4 released as `v0.4.0`. | `ROADMAP.md` T4 passed line | Source |
| 121 | T1's adversarial review: re-derived formulas, mutation, NaN search; seven real problems, all fixed; four of the inputs kept as regressions. | `docs/evidence/T1/summary.md` (Done 11); `tests/test_limits.cpp` ("inputs that used to be wrong, kept as regressions": four subcases) | Source; regressions asserted |
| 122 | T2: a review flagged the hazard; redone by Fable: PASS WITH DEFECTS, defects in the pack and a comment, none in the library. | `docs/evidence/T2/summary.md` (Owner actions 3); `docs/evidence/T2/verdict.md` | Source |
| 123 | T3: the summed-drift check, the input σ = √(2·10³⁰⁰), q = 10³⁰⁰, r = 0, T = 10¹⁰, NaN in all seven outputs; repaired by `scales.hpp`; kept in `test_associations.cpp`. | `docs/evidence/T3/summary.md` (Done 1); `tests/test_associations.cpp` | Asserted |
| 124 | T3a's repeated-code review by a session that had not written the change; each finding closed or kept with a reason. | `docs/evidence/T3a/review.md` | Source |
| 125 | T4's audit by Fable: Node and headless Chromium, page and worker; the release job's upload defect; fixed by a flat assembly downloaded on every push. | `docs/evidence/T4/summary.md` (second entry); `.github/workflows/wasm.yml` (`downloaded` job) | Source; download checked in CI |
| 126 | T5's claims were checked one by one by an agent that did not write the document: 9 said more than their sources held, 26 needed narrower wording or a better citation; each was corrected. | This file, last section | Source |
| 127 | The text removed from comments at T3a, as recorded. | `docs/evidence/T3a/history.md` | Source |
| 128 | The text removed from comments at T5, as recorded. | `git show 1755f0c ea23329 6d80fb0` and the commit that corrected `third_party/CMakeLists.txt` (the removed lines) | Source |
| 129 | The comments in `include/`, `src/`, `tests/`, `wasm/`, `bench/`, the CMake files and the workflows name no milestone, review or governance id; the golden-file and experiment scripts and documents still do. | `docs/evidence/T5/build.txt` §3 (the grep, its pattern, scope and empty result; `third_party/CMakeLists.txt` added after the check) | Source |

## Claims added after the check (unmapped at first)

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 130 | Status: every claim is listed, numbered, in this file. | This file, rows 1–142 | Source |
| 131 | Touchstone is a C++20 library. | `CMakeLists.txt` (`CMAKE_CXX_STANDARD 20`, required, no extensions) | Source |
| 132 | The binding is an embind binding. | `wasm/CMakeLists.txt` (`-lembind`); `wasm/binding.cpp` (`emscripten/bind.h`) | Source |
| 133 | Scaling Greeks for display is the caller's. | `include/touchstone/black_scholes.hpp` (file comment); `PriceAndGreeks` units | Source |
| 134 | One `template <Exercise E>` declaration per pair was considered; all three stay pairs. | `include/touchstone/pde.hpp` (the six declarations); `docs/evidence/T5/summary.md` (Decisions) | Source |
| 135 | §10.1's T5 row: passed 2026-11-14; this document, the timings, comments without history, 1.0.0; released as `v1.0.0`; Fable tollgate PASS WITH DEFECTS, all wording, closed before the merge. | `ROADMAP.md` (T5's Passed line); `docs/evidence/T5/verdict.md`; the `v1.0.0` tag and its release; `ARCHITECTURE.md`; `docs/evidence/T5/timing.txt`; `build.txt` §3; `CMakeLists.txt`; `README.md` status row | Source |
| 136 | Each milestone has an evidence pack under `docs/evidence/<milestone>/`. | `docs/evidence/T0/` … `T5/` | Source |
| 137 | §11: first version 2026-11-14, with 1.0.0. | This branch's history | Source |
| 138 | Each claim corrected after the check is worded as the source holds it. | The section below | Source |

## After the tollgate

The T5 tollgate (Fable, PASS WITH DEFECTS) found five places where a claim the check had
narrowed here still stood unnarrowed, or a figure stood with nothing holding it. Rows
139–142 are the sentences this added to `ARCHITECTURE.md`; row 8 above was reworded.
Rows 143–155 are the sentences rewritten outside it, in the README and in comments, by the
five defects and by the scan for more of the kind (`tollgate.md` §2 lists each with its old
text). Rows 156–159 are the four sentences the tollgate's re-check found, in its own words,
and row 160 the sentence it added to §10.2. Line references are at this branch's head.

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 139 | §10.2: Fable passed T5 with defects, all of them wording; claims the check had narrowed still stood unnarrowed in the README's opening list and the file comments of `pde.hpp` and `monte_carlo.hpp`, and two settings comments gave figures nothing held. | The tollgate's verdict (the owner's message of 2026-11-14, quoted in `tollgate.md` §1); `git show 7110c84:README.md`, `7110c84:include/touchstone/pde.hpp`, `7110c84:include/touchstone/monte_carlo.hpp` | Source |
| 140 | §10.2: `MonteCarloSettings` promised about a cent of standard error at the defaults; §7's option measures 0.077. | `git show 7110c84:include/touchstone/monte_carlo.hpp`; `tollgate.md` §3 (0.076610 at `MonteCarloSettings{}` on `bench/timing.cpp`'s base case) | Reported (pack) |
| 141 | §10.2: `PdeSettings` said the suite held every golden row to 3e-4 at the defaults; the suite runs the defaults on 136 rows and the whole grid only at a coarser resolution. | `git show 7110c84:include/touchstone/pde.hpp`; `tests/test_pde.cpp` (`sweep_settings`, 512 × 256); `tests/test_three_way.cpp` (`grid_settings`, 1,024 × 512, 136 rows) | Source |
| 142 | §10.2: a scan for more of both kinds found them in `normal.hpp`, `bump_greeks.hpp` and three test files; all were corrected before 1.0.0; `tollgate.md` lists each. | `tollgate.md` §2; `git diff 7110c84 -- include tests` | Source |
| 143 | README: three ways, independent in method though not in every line; `ARCHITECTURE.md` §1 names what they share. | As row 3 | Source |
| 144 | README: the Monte Carlo is held to the closed form in standard-error units on the 6,470 of the golden file's 7,234 rows where enough paths finish in the money to score it; the other 764 are too rare to score. | `tests/test_monte_carlo.cpp` ("the golden grid, priced by Monte Carlo": 6,147 scored at 32,768 paths + 323 re-run at 1,048,576 = 6,470; 764 too rare); as row 9 | Asserted on the scored rows; the rest reported |
| 145 | README: the grid is held to QuantLib's values on the 7,200-row grid at 512 × 256, coarser than its defaults; the 34-row edge block is reported, not held; it also prices the American contract. | `tests/test_pde.cpp` (`sweep_settings`; "golden grid by Crank-Nicolson"; "the edge block, where a grid has less to work with", which asserts only that more than 20 of 34 price); `tests/test_american.cpp`; as rows 4 and 8 | Asserted (main block, American); reported (edge block) |
| 146 | `pde.hpp`, file comment: the grid never uses `N(d)` and never draws a random number; it shares the scale functions of `detail/scales.hpp` with both others and `payoff` with the Monte Carlo. | `src/pde.cpp` (includes `detail/scales.hpp`, not `normal.hpp`, `rng.hpp` or `ClosedFormQuote`; `payoff_at` calls `payoff`, line 209); `src/monte_carlo.cpp` (`payoff(option, terminal)`, line 302) | Source |
| 147 | `monte_carlo.hpp`, file comment: it samples the terminal distribution where the closed form evaluates `N(d)`; its discount factor and discounted strike come from `ClosedFormQuote`, its payoff is the grid's, and its scalars go through `scales.hpp`; what it checks is the terminal law, the discretisation, the sampling and the estimator. | `src/monte_carlo.cpp` (`ClosedFormQuote quote`, `quote.discount_factor()`, `quote.discounted_strike()`, `payoff`, lines 222–318) | Source |
| 148 | `MonteCarloSettings`: the defaults promise no accuracy of their own; the standard error depends on the option, and `MonteCarloResult` reports it beside every price. | `include/touchstone/monte_carlo.hpp` (`MonteCarloResult::price_standard_error`); `tollgate.md` §3 (at the defaults over the main block: 10th percentile 0.0002, median 0.0625, 90th 0.2594) | Source; reported (pack) |
| 149 | `PdeSettings`: `tests/test_pde.cpp` holds the golden grid's 7,200 rows at 512 × 256 to 2e-4 of the underlying's scale in price; `tests/test_three_way.cpp` holds 136 of them at the defaults' 1,024 × 512 to 5e-5. | `tests/test_pde.cpp` (`fields`: price 2e-4, scaled by max(\|ref\|, S); worst 8.928e-5); `tests/test_three_way.cpp` (`grid_settings`; `CHECK_MESSAGE(worst_grid.value() <= 5e-5, …)`; worst 2.160e-5) | Asserted |
| 150 | `tests/test_three_way.cpp`, file comment: the three are different methods, not wholly separate code; a mistake in a shared piece shows only against a method that does not share it. | `ARCHITECTURE.md` §1; row 3 | Source (reasoning) |
| 151 | `normal.hpp`, `norm_inv`: `docs/rng.md` §4 gives AS241's accuracy as about 1e-16; `tests/test_rng.cpp` round-trips p from 1e-300 to 0.5 through `norm_cdf` and asserts p comes back within (4 + 4x²) machine epsilons; the error that implies in x reaches 3.1 ulps in the far tail. | `docs/rng.md` §4; `tests/test_rng.cpp` (`round_trip_tolerance` and its comment; "AS241 round-trips through N(x)": 1,199 values, worst 0.778 of the bound, at p = 1e-179) | Asserted (the bound); reported (3.1 ulps) |
| 152 | `bump_greeks.hpp`: each default bump is the size with the smallest worst scaled error; the test sweeps the delta, gamma, vega and rho bumps from 1e-9 to 1e-2 over nine options, asserts the default is the minimum and both ends are more than ten times worse; the floors are 1e-10 (delta), 3e-9 (gamma), 2e-10 (vega), each within an order of magnitude of `eps^(2/3)` ≈ 3.7e-11 or `eps^(1/2)` ≈ 1.5e-8. | `tests/test_bump_greeks.cpp` ("the bump size has an optimum, and it is where the analysis says"; 3 markets × 3 options; reported floors 1.04e-10, 2.84e-9, 2.07e-10) | Asserted (minimum, ends); reported (floors) |
| 153 | `bump_greeks.hpp`: a pricer with error `d` has its best bump larger by `(d / eps)^(1/3)`, about 360 times at `d` = 1e-8. | Arithmetic: (1e-8 / 2.22e-16)^(1/3) = 356 | Source (arithmetic) |
| 154 | `bump_greeks.hpp`: the test measures delta off the grid at the default bump and at one a thousand times wider, and asserts the two errors are within a factor of ten. | `tests/test_bump_greeks.cpp` ("bumping a grid gets the grid's Greeks, at the grid's bump size": `spot_relative` 1e-6 against `grid_bumps()`'s 1e-3; two `CHECK`s at a factor of ten; measured 9.48e-7 and 1.91e-7) | Asserted |
| 155 | Test comments: the grid bumps are a hundred to a thousand times the defaults; delta's error moves by less than a factor of ten between bumps three decades apart; gamma's at the default bumps is more than fifty times the wide bumps' (asserted), over two hundred measured. | `tests/grid_bumps.hpp` against `BumpSizes` (1e-3 against 1e-6 four times, 1e-3 against 1e-5, 1e-2 against 3e-5); `tests/test_bump_greeks.cpp` (`fine_gamma > wide_gamma * 50.0`; measured 4.89e-3 against 2.14e-5) | Asserted; reported |
| 156 | `bump_greeks.hpp`, choosing the bump: the same test measures gamma's relative error as 4.9e-3 at the default bump against 2.1e-5 at a bump of 1e-2, and asserts the first is more than fifty times the second; two hundred times, from the bump size alone. | `tests/test_bump_greeks.cpp` ("bumping a grid gets the grid's Greeks, at the grid's bump size": `fine_gamma > wide_gamma * 50.0`; reported 4.89e-3 and 2.14e-5, `tests.txt` §1); `tests/grid_bumps.hpp` (`spot_relative_for_gamma = 1e-2`) | Asserted (fifty); reported (4.9e-3, 2.1e-5, the ratio of 228) |
| 157 | `pde.hpp`, `PdeResult::mesh_peclet`: on the golden grid at 512 × 256 it reaches 0.10, and `tests/test_pde.cpp` asserts it stays below 0.15 there; it is proportional to `dx`, so the defaults' grid, twice as fine, halves it. | `tests/test_pde.cpp` (`CHECK(worst_peclet.value() < 0.15)`; reported 1.018e-01, `tests.txt` §1); `include/touchstone/pde.hpp` (`\|nu\| dx / sigma^2`); `tollgate.md` §2 (0.0509 at the defaults over all 7,200 rows, measured) | Asserted (0.15); reported (0.10); reported in the pack (the halving) |
| 158 | `bump_greeks.hpp`, `require_valid`: a one-sided difference is first order, so its error falls only as the bump where the central difference's falls as the bump squared. | The Taylor expansion in the file comment ("Choosing the bump": the central difference's error is `(h^2 / 6) f'''`); a forward difference's leading term is `(h / 2) f''` | Source (analysis) |
| 159 | `bump_greeks.hpp`, the sweep's floors: about 1e-10 for delta, 3e-9 for gamma and 2e-10 to 3e-10 for vega, rounding floors that move a little between compilers. | `tests/test_bump_greeks.cpp` (the sweep's table: 1.04e-10, 2.84e-9, 2.07e-10 with g++ 15.2, `tests.txt` §1; vega 2.95e-10 with g++ 13.3, the tollgate's run) | Reported |
| 160 | §10.2: the tollgate's re-check found four more, in `bump_greeks.hpp` and `pde.hpp`. | `tollgate.md` §2, rows G–J; `git diff 948ad76 -- include` | Source |

## The independent check

**Who and how.** A fresh agent session, given `ARCHITECTURE.md`, this file and the
repository, told to check every row against its citation adversarially and to edit nothing,
at `a83dfd3`. It read every cited file, used `git grep`, `git show`, `git log` and
`gh release view`, and did not rebuild or rerun the suite (it used `tests.txt`). About eleven
minutes, 80 tool calls.

**What it found**, over rows 1–129: 93 hold; 26 hold but needed a correction to the wording,
citation or label; 9 did not hold; 1 (row 126) could not be checked because this section was
pending. It also listed nine factual sentences with no row. The author verified each finding
against the code before changing anything; every one stood.

**The nine that did not hold, and what changed:**

| Row | Finding | Change |
| --- | --- | --- |
| 3 | "Three independent ways": the Monte Carlo takes its discount factor and discounted strike from `ClosedFormQuote`, all three share `scales.hpp`, two share `payoff`. | §1 says they are independent in method, not in every line, and names what they share. |
| 6 | The demos do not run on the WebAssembly build yet: L1 put them on the TypeScript backend and L5, which moves them, has not run. | §1 says "are to run" and says where they run now. README likewise (two sentences). |
| 9 | The Monte Carlo is scored on 6,147 + 323 of 7,234 rows; 764 are too rare to score. | §1 bounds the claim to the rows where enough paths finish in the money. |
| 11 | "An accepted input never produces a NaN" is false for `norm_inv` at p ≥ 1 (asserted NaN in `test_rng.cpp`), and the grid, implied vol and bump Greeks have no NaN sweep. | §1 and §6.2 name the three families that are swept, say the others are not, and name the exception. |
| 52 | Not every refusal is in a `require_valid`: `monte_carlo`'s total-variance check and the surface's stride of zero are not. | §4 and §6.1 say so; §6.1 cites `test_monte_carlo.cpp`. |
| 73 | "A pair for each of six inputs and a wider spot pair" is fifteen prices, not thirteen. `bump_greeks.hpp`'s comment double-counted the same way. | §5 lists the six pairs. The header comment is corrected too (a comment only; the library's object files are still byte-identical to main's). |
| 102 | `build.txt` recorded clang's output only for the folded case. | Clang's ambiguity error for the unfolded case is recorded (`build.txt` §4), and §8 says the probe mirrors the declarations rather than including the headers. |
| 108 | `bumpGreeks` over the grid accepts an American option, and the smoke test asserts it. | §8 names it among the entry points that accept one. |
| 112 | The 46 remaining clang-format lines contain no comment changes. | §8 names what they are. |

**The 26 corrections** (rows 1, 26, 27, 29, 49, 56, 59, 60, 63, 79, 81, 84, 85, 86, 91, 93,
98, 105, 106, 110, 117, 121, 124, 128, 129, and row 10's label), in short:

- **Present tense for future work:** the portal page (1) and the release feeding the demos (27)
  are intended, not done; row 26's note that the release had not run was stale (`v0.4.0` was
  published 2026-11-13).
- **Overbroad wording:** the consumers list missed the header check (29). `payoff` accepts
  either contract (49). "Every scalar" in `scales.hpp` became "the products the checks guard"
  (79). "No faster formulation" became "one alternative, no faster" (106). The half-width's
  1.5e-8 is an estimate, and the test's measurement is now quoted beside it (110). Four of
  T1's inputs are kept, not all (121). Some T3a findings were kept with a reason, not closed
  (124). The comment-grep's scope is now stated (129). That last check also found
  `third_party/CMakeLists.txt`'s "the WASM artifact at T4", project-written and outside the
  grep's scope; it is corrected and recorded in §10.3.
- **Wrong citation or label:** antithetic pair means (60), the Rannacher test (63),
  "accessors asserted equal" (56), the surface tested against `crankNicolson`, not the closed
  form (81), the plain `Error` branch not asserted (91), the smoke test re-checking one row
  and the RNG fixture rather than every fixture (93), "nothing was tuned" true of this
  measurement, not of T3a (98), the safeguarded solver named where §8 meant it (105), T0
  regenerating by hand and CI from T1 (117), §10.3's "three comments" that quoted four (128).
- **Imprecise reasoning:** a NaN does not compare false against *every* test; `x != x` is
  true. §6.2 now says what a NaN does to `<=` and `>` (86). Row 85 now includes
  `test_associations.cpp`, which §6.2 cites.
- **Row 10's label:** the test compares the grid and the Monte Carlo with each other only
  through the closed form, as it states.

**The nine unmapped sentences** are rows 130–138 above.

**Noted, not changed:** row 96. The launch command sets affinity and priority right after
`Start-Process` returns, so the harness's calibration may start before the pin takes
effect; the rounds are pinned. `timing.txt` §2 now says so. Row 40: the binding has one
class with a base, `ArgumentError : std::runtime_error`; the claim is about the library,
and the binding is not part of it.

**Not re-checked by a second agent.** The author made these corrections and re-read every
changed row against its citation; the checking agent did not see the corrected document.
