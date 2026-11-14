# T5 — claims map for `ARCHITECTURE.md`

Every claim in `ARCHITECTURE.md`, numbered in the order it appears, against the test or file
that holds it. **Asserted** means a test fails if the claim stops being true. **Reported**
means a test or script prints the number and the pack quotes it, without a test bounding it
there. **Source** means the claim is about what the code, a build file or a document says,
and the cited file is where it can be read. Paths are from the repository root; line numbers
are at this branch's head and are given only where a file is long.

The last section records the independent check of every row: who made it, what it found and
what changed.

## §0 Status, §1 What this is

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 1 | The document describes Touchstone 1.0.0 and is the source of the portfolio's architecture page. | `CMakeLists.txt` (`VERSION 1.0.0`); `wasm/smoke.test.mjs` (the module's `version` equals it); `ROADMAP.md` T5 and P2 deliverables | Source; asserted for the module |
| 2 | Prices European calls and puts on one underlying under Black–Scholes–Merton with constant rate, volatility and continuous dividend yield. | `include/touchstone/black_scholes.hpp` (file comment, `BlackScholesMarket`); `include/touchstone/contract.hpp` | Source |
| 3 | Three independent ways: closed form with six analytic Greeks, Monte Carlo, Crank–Nicolson. | `include/touchstone/black_scholes.hpp`, `monte_carlo.hpp`, `pde.hpp` | Source |
| 4 | The finite-difference grid also prices the American contract. | `include/touchstone/pde.hpp` (`crank_nicolson(const AmericanVanilla&, …)`); `tests/test_american.cpp` | Asserted |
| 5 | Implied volatility by two solvers; Greeks by bumping any pricer; Brownian and GBM paths from a frozen generator. | `include/touchstone/implied_vol.hpp`; `bump_greeks.hpp` (`VanillaPricer`); `paths.hpp`; `rng.hpp`, `docs/rng.md` | Source |
| 6 | One half of a pair with learn.garethcooke.com, whose demos run on this library compiled to WebAssembly. | `README.md`; `CONSTITUTION.md` §1, I15 (A6); `wasm/binding.cpp` file comment | Source (programme documents; the site is not in this repository) |
| 7 | The closed form agrees with QuantLib's reference values within the tolerances the tests state and assert, on the committed grid. | `tests/test_closed_form.cpp` against `golden/bs_vanilla.json` (1e-10 grid, 1e-8 edge block) | Asserted; worst 2.841e-13 (grid), 1.619e-11 (edge) reported in `tests.txt` §1 |
| 8 | The grid agrees with QuantLib's reference values within stated, asserted tolerances on the committed grid. | `tests/test_pde.cpp` ("golden grid by Crank-Nicolson", 7,200 rows at 512 × 256) | Asserted |
| 9 | The Monte Carlo agrees with the closed form in units of its own standard error. | `tests/test_monte_carlo.cpp` ("the golden grid, priced by Monte Carlo": 6,147 rows scored, worst \|z\| 3.559 against a bound of 5.648) | Asserted |
| 10 | The three agree with each other within stated, asserted tolerances. | `tests/test_three_way.cpp` (136 rows) | Asserted |
| 11 | An input the library accepts never produces a NaN. | See 85 | Asserted |
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
| 26 | A GitHub release is made on a `v*` tag. | `.github/workflows/release.yml` | Source (it has not yet run; `docs/evidence/T4/summary.md`) |
| 27 | The release feeds the tutorial's demos. | `.github/workflows/release.yml` file comment; `CONSTITUTION.md` I17 | Source |
| 28 | The library is a static library of seven translation units and seventeen headers. | `CMakeLists.txt` (`add_library(touchstone STATIC` with seven sources; `TOUCHSTONE_HEADERS` lists seventeen) | Source |
| 29 | Its consumers here are the tests, the binding and the timing harness, which is built with the tests and never run by them. | `tests/CMakeLists.txt`, `wasm/CMakeLists.txt`, `bench/CMakeLists.txt`; `CMakeLists.txt` (`add_subdirectory(bench)` inside `if(TOUCHSTONE_BUILD_TESTS)`); no `add_test` names it | Source |

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
| 49 | The grid accepts either; every other entry point taking a contract accepts the European one only and refuses the American one at compile time. | `tests/test_contract.cpp` (concepts and `static_assert`s) | Asserted at compile time |
| 50 | `with_exercise` converts; nothing converts implicitly. | `tests/test_contract.cpp` (`!is_convertible_v` both ways; "with_exercise keeps every field") | Asserted |
| 51 | `BlackScholesMarket` is the market; `QuotedMarket` is it without the volatility. | `include/touchstone/black_scholes.hpp` | Source |
| 52 | Each family has a `require_valid` throwing `std::invalid_argument` with the reason; each entry point calls it first; a caller may call it directly. | `black_scholes.hpp`, `monte_carlo.hpp`, `pde.hpp`, `implied_vol.hpp`, `bump_greeks.hpp`, `paths.hpp` (declarations); `src/` (each entry point's first statement); the tests in 84 | Source; refusals asserted |
| 53 | Every Greek is a raw partial derivative: vega per 1.00 vol, theta per year, rho per 1.00 rate. | `include/touchstone/black_scholes.hpp` (`PriceAndGreeks`); `golden/SCHEMA.md`; `tests/test_closed_form.cpp` against the file's conventions | Asserted (against QuantLib in those units) |

## §5 How each method is built

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 54 | `N(x)` is evaluated through `std::erfc`. | `include/touchstone/normal.hpp` (`norm_cdf`) | Source |
| 55 | At x = −10 the subtraction `1 − N(10)` returns zero where the true value is 7.6e-24. | `include/touchstone/normal.hpp` comment; `tests/test_normal.cpp` (the subtraction demonstrated, ~line 73) | Asserted |
| 56 | A `ClosedForm` validates once, computes once, serves all seven outputs. | `include/touchstone/black_scholes.hpp`, `src/black_scholes.cpp`; `tests/test_closed_form.cpp` ("worst accessor error 0") | Source; accessors asserted equal |
| 57 | `ClosedFormQuote` is the volatility-free half, and both solvers build it once per solve. | `include/touchstone/black_scholes.hpp`; `src/implied_vol.cpp` (one `ClosedFormQuote` per search, ~lines 75–104); `tests/test_closed_form.cpp` (quote reused: 7,234 rows, 0 values not identical) | Source; reuse asserted |
| 58 | The Monte Carlo samples the terminal law exactly from one normal per path, or steps Euler–Maruyama over `steps` equal steps from the same generator. | `include/touchstone/monte_carlo.hpp`, `paths.hpp` (`Scheme`); `include/touchstone/detail/path_generator.hpp` | Source |
| 59 | It reports a standard error beside the price and a pathwise delta beside the delta. | `include/touchstone/monte_carlo.hpp` (`MonteCarloResult`); `tests/test_monte_carlo.cpp` ("the standard error is the spread of the estimator") | Asserted |
| 60 | With antithetics the sampling unit is the pair and the standard error comes from pair means. | `include/touchstone/monte_carlo.hpp` (`antithetic`, `samples`); `tests/test_monte_carlo.cpp` ("antithetic sampling reduces the variance it is supposed to") | Asserted |
| 61 | An Euler path may go negative and is not clipped. | `include/touchstone/paths.hpp` (`Scheme::EulerMaruyama`); `include/touchstone/contract.hpp` (`payoff` at a negative spot); `tests/test_contract.cpp` (`payoff(put, -5.0) == 105.0`) | Source; payoff asserted |
| 62 | The grid is in log-spot, where the coefficients are constant and one uniform grid serves every spot. | `include/touchstone/pde.hpp` ("The equation") | Source |
| 63 | Crank–Nicolson after two fully implicit half-step pairs (Rannacher), from a cell-averaged payoff. | `include/touchstone/pde.hpp` (`rannacher_steps{2}`, `smooth_payoff{true}`); `src/pde.cpp` (`advance`, `cell_average_payoff`); `tests/test_pde.cpp` (convergence with and without) | Source; convergence asserted |
| 64 | The spot is exactly on a node; the price is a node value and delta and gamma central differences about it. | `include/touchstone/pde.hpp` (`crank_nicolson`); `src/pde.cpp` (`make_grid`, `result`); `tests/test_pde.cpp` (spot node at `ln S`) | Asserted |
| 65 | Each step is a Thomas sweep without pivoting. | `include/touchstone/tridiagonal.hpp`; `src/tridiagonal.cpp`; `tests/test_tridiagonal.cpp` | Asserted |
| 66 | The diagonal dominance is measured and reported, with the mesh Péclet number, rather than assumed. | `include/touchstone/pde.hpp` (`PdeResult::dominance_margin`, `mesh_peclet`); `tests/test_pde.cpp` ("grid diagnostics": smallest dominance 1.000, worst Péclet 0.10) | Asserted |
| 67 | The American contract replaces the sweep with its projected form and raises the boundary to immediate exercise; every other line is shared. | `src/pde.cpp` (`GridSolver<E>::step`, `boundary_value`, `if constexpr`); `tests/test_tridiagonal.cpp` ("projected sweep vs PSOR"); `tests/test_american.cpp` | Source; asserted against three QuantLib lattices |
| 68 | `crank_nicolson_surface` runs the same solve and its last level at the spot is `crank_nicolson`'s price, bit for bit. | `tests/test_pde.cpp` ("the surface's last level, at the spot, is crank_nicolson's price") | Asserted |
| 69 | The two implied-vol solvers share the volatility-free half and the bounds and keep separate stopping rules. | `include/touchstone/implied_vol.hpp` (second solver's comment); `src/implied_vol.cpp` (`floor_of`, `ceiling_of`, `ClosedFormQuote`) | Source |
| 70 | `implied_vol` runs Newton from the Manaster–Koehler seed (Brenner–Subrahmanyam at the money) and hands over to Brent on `[0, max_vol]`, which always finishes because the bracket is established. | `include/touchstone/implied_vol.hpp` (`implied_vol`); `tests/test_implied_vol.cpp` ("Brent finishes what Newton cannot": 982 of 1,029 rows through Brent, worst reprice 1.07e-12) | Source; Brent path asserted |
| 71 | `implied_vol_safeguarded` is page 2.11's solver: Newton in a sign-narrowed bracket, bisecting where Newton would leave it, recording iterates on request. | `include/touchstone/implied_vol.hpp`; `tests/test_implied_vol.cpp` (committed trace iterate by iterate, worst 7.105e-15; "steps are recorded only when asked") | Asserted |
| 72 | It answers a price outside the bounds with a status and a volatility of zero or infinity, never a NaN; `implied_vol` refuses such a price with `std::invalid_argument`. | `include/touchstone/implied_vol.hpp` (`SafeguardedResult::vol`, `require_valid`); `tests/test_implied_vol.cpp` ("page 2.11's refusals…", "prices no volatility produces are refused"); `wasm/smoke.test.mjs` | Asserted |
| 73 | Bump Greeks take thirteen prices: the base, a pair for each of six inputs, and a wider spot pair for gamma. | `include/touchstone/bump_greeks.hpp` (`bump_greeks`, `detail::Bumped`) | Source |
| 74 | A second difference balances truncation against cancellation at a larger bump than a first difference. | `include/touchstone/bump_greeks.hpp` ("Choosing the bump") | Source (analysis), shown by 75 |
| 75 | `tests/test_bump_greeks.cpp` sweeps delta, gamma, vega and rho bumps from 1e-9 to 1e-2 and asserts each is most accurate at the default size (1e-6; 3e-5 for gamma) and more than ten times less accurate at both ends. | `tests/test_bump_greeks.cpp` ("the bump size has an optimum…": `sizes[]`, `axes[]`, `CHECK(best == expected)`, the two `* 10.0` checks) | Asserted |
| 76 | The generator is xoshiro128\*\* seeded through the MurmurHash3 finaliser, with 53-bit uniforms and AS241 normals, frozen by `docs/rng.md`. | `include/touchstone/rng.hpp`, `normal.hpp`; `docs/rng.md`; `tests/test_rng.cpp` | Source; fixture asserted |
| 77 | `brownian_path` and `gbm_path` write a whole path into a caller's span, one normal per step; both GBM schemes are driven by the same normals. | `include/touchstone/paths.hpp`; `tests/test_paths.cpp` (fixture; "increments are the stream's normals"; exact scheme on the same path) | Asserted |
| 78 | The Monte Carlo draws from the same generator through the same step. | `include/touchstone/detail/path_generator.hpp` (file comment); `tests/test_paths.cpp` ("Monte Carlo's per-path functions are one step of the same generator") | Asserted |
| 79 | Every scalar the methods form from a market and an expiry is written once in `detail/scales.hpp`, and the domain checks call the same functions. | `include/touchstone/detail/scales.hpp`; `src/black_scholes.cpp`, `src/pde.cpp`, `src/monte_carlo.cpp`; `tests/test_associations.cpp` | Source; associations asserted |
| 80 | A check grouping a product differently guards a different set of inputs; §10.2 has the input. | `tests/test_associations.cpp` ("the input a check on the summed drift accepts…") | Asserted |
| 81 | The binding is translation only: plain objects in, value types across, plain objects and `Float64Array`s back, under `PricingBackend`'s names, with `monteCarlo`, `crankNicolson`, `crankNicolsonSurface`, `bumpGreeks` beyond it. | `wasm/binding.cpp` (file comment, registrations at the end); `wasm/smoke.test.mjs` (each called) | Source; each asserted against the closed form |
| 82 | `defaults()` exports the default settings of every bound entry point that takes settings. | `wasm/binding.cpp` (`defaults`: five settings types); `wasm/smoke.test.mjs` ("the library's defaults are the module's": five keys) | Asserted |
| 83 | The artifact is one ES module and one `.wasm`, built by Emscripten 6.0.13 with C++ exception catching on. | `wasm/CMakeLists.txt` (`MODULARIZE`, `EXPORT_ES6`); `.github/workflows/wasm.yml` (`EMSDK_VERSION`); `CMakeLists.txt` (`TOUCHSTONE_WASM_EXCEPTIONS` ON, `-fwasm-exceptions`) | Source |

## §6 Invariants

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 84 | Validate, then compute: an input outside the domain is an `std::invalid_argument` naming the reason; the five test files assert refusals. | `tests/test_limits.cpp` (~547), `test_pde.cpp` (~515), `test_implied_vol.cpp` (~410, "settings, contracts and targets it cannot work with are refused"), `test_bump_greeks.cpp` (~258), `test_paths.cpp` (~256) | Asserted |
| 85 | Accepted input never gives a NaN; from the closed form price, delta, vega, rho, dividend rho are finite, gamma and theta may be infinite; a Monte Carlo estimate may saturate to infinity. | `include/touchstone/black_scholes.hpp` (`require_valid` comment); `tests/test_limits.cpp` (domain sweep: 16,570 priced, 9,350 refused, 550 infinite gammas, no NaN); `tests/test_monte_carlo.cpp` ("no input the closed form accepts makes the engine return a NaN", including an infinite standard error, ~line 720) | Asserted |
| 86 | Why: an infinity compares correctly against a tolerance; a NaN compares false against every test. | `include/touchstone/black_scholes.hpp` (`require_valid` comment) | Source (IEEE 754 behaviour) |
| 87 | Each product is formed once, in one association, through `detail/scales.hpp`, because floating-point multiplication does not associate. | `include/touchstone/detail/scales.hpp` (file comment); `tests/test_associations.cpp` | Asserted |
| 88 | Same seed, same result, bit for bit; the generator reproduces the TypeScript fixture. | `tests/test_rng.cpp` ("same seed, same numbers"; fixture); `tests/test_monte_carlo.cpp` ("same seed, same result"); `tests/test_paths.cpp` ("same seed, same path"); `wasm/smoke.test.mjs` | Asserted |
| 89 | The exercise style is part of the contract's type; `test_contract.cpp` fails by not compiling. | `tests/test_contract.cpp` | Asserted at compile time |
| 90 | No dependency: the library includes nothing outside the standard library; the vendored headers are linked by the test executable only. | `CMakeLists.txt` (`target_link_libraries(touchstone PRIVATE touchstone_warnings)`); `tests/CMakeLists.txt` (`touchstone_vendor`); every `#include` in `include/`, `src/` (`build.txt` §5) | Source |
| 91 | Nothing is thrown across the WebAssembly boundary: each bound function catches and returns an error, `errors.post.js` throws it; `RangeError`, `TypeError`, `Error`. | `wasm/binding.cpp` ("Errors"); `wasm/errors.post.js`; `wasm/smoke.test.mjs` (RangeError, TypeError, thrown-getter tests) | Asserted |
| 92 | An exception unwinding WebAssembly frames leaves the stack pointer behind; T4 measured a module killed at call 2,074. | `docs/evidence/T4/summary.md` (Done 3); `docs/evidence/T4/tests.txt` §2 | Reported (T4) |
| 93 | `wasm/smoke.test.mjs` makes 300,000 refused calls and then reproduces the fixtures. | `wasm/smoke.test.mjs` ("survives a hundred thousand refusals of each kind": three kinds) | Asserted |

## §7 Timings

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 94 | `bench/timing.cpp` times the five entry points at their defaults on the stated option and market; `implied_vol` inverts the closed-form price at σ = 0.2; `bump_greeks` is the closed-form overload. | `bench/timing.cpp` | Source |
| 95 | Taken 2026-11-14 on a Ryzen 7 3800X, Windows 11 Pro 10.0.26200, g++ 15.2.0 (MinGW-Builds), `-O3 -DNDEBUG -std=c++20`, static library. | `docs/evidence/T5/timing.txt` §3 | Reported |
| 96 | 25 rounds per process, pinned to one logical core at high priority; median of five batches per round; a batch at least 20 ms. | `bench/timing.cpp` (constants); `docs/evidence/T5/timing.txt` §2 (launch command) | Source |
| 97 | The table gives each of three processes' median round, lowest to highest: 74–76 ns, 336–349 ns, 1.39–1.41 µs, 1.78–1.79 ms, 4.71–4.74 ms. | `docs/evidence/T5/timing.txt` §4, §6 (raw output) | Reported |
| 98 | The WebAssembly build was not timed; nothing was tuned; there is no fast path. | `docs/evidence/T5/timing.txt` §5; `docs/evidence/T5/tests.txt` §2 (library objects byte-identical to `74987c7`'s) | Source; "nothing tuned" shown by identical objects |

## §8 Decisions

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 99 | Free functions are the public face; `ClosedForm` public because holding it saves repeated validation and arithmetic; grid solver and path generator internal. | `include/touchstone/black_scholes.hpp` ("The evaluation behind the free functions"); `ROADMAP.md` T3a passed line | Source |
| 100 | The three grid pairs are declared twice each and forward to one template in `pde.cpp`. | `include/touchstone/pde.hpp`; `src/pde.cpp` (`validated_grid`, `solve_to_today`, `sample_to_today`) | Source |
| 101 | `bump_greeks.hpp` declares a three-argument `require_valid` taking `BumpSizes`. | `include/touchstone/bump_greeks.hpp` | Source |
| 102 | With both headers included, `require_valid(option, market, {})` is ambiguous today, and with a template in the pair's place resolves silently to the `BumpSizes` overload, under g++ 15.2 and clang 22.1.7. | `docs/evidence/T5/build.txt` §4 (the probe and both compilers' output) | Reported (probe) |
| 103 | The other two pairs have no such neighbour. | `include/`, `src/`, `tests/`, `wasm/` (no other declaration of `crank_nicolson` or `crank_nicolson_surface`) | Source |
| 104 | Each implied-vol solver keeps its own stopping rule; the safeguarded one is held to page 2.11's committed trace iterate by iterate. | `include/touchstone/implied_vol.hpp`; `tests/test_implied_vol.cpp`; `ROADMAP.md` T3a passed line | Asserted |
| 105 | A refused implied-vol price returns zero or infinity with its status, never a NaN. | As 72; `ROADMAP.md` T3a passed line | Asserted |
| 106 | A path's step keeps two zero tests, which make an infinity times a zero impossible; T3a measured 1.5 ms of a 31.5 ms Euler run of 64 steps, and no faster formulation returning the same bits. | `include/touchstone/detail/path_generator.hpp` (`GbmStep`); `tests/test_paths.cpp` ("an accepted path never holds a NaN"); `docs/evidence/T3a/timing.txt` §2–4 | Asserted (no NaN); reported (cost) |
| 107 | Errors returned across the boundary; arguments structured-cloned first so a throwing getter throws before any WebAssembly frame exists. | `wasm/errors.post.js`; `docs/evidence/T4/summary.md` (Decisions); `wasm/smoke.test.mjs` ("a thrown getter on an argument reaches the caller as itself") | Asserted |
| 108 | An American option reaches the binding as `exercise: 'american'`; the grid's entry points accept it, every other refuses with a `TypeError`. | `wasm/binding.cpp`; `wasm/smoke.test.mjs` (the grid test; the TypeError test); `docs/evidence/T4/summary.md` | Asserted |
| 109 | WebAssembly exception handling, not Emscripten's JavaScript kind: 31,650 bytes against 79,115 at T4. | `docs/evidence/T4/summary.md` (Decisions); `docs/evidence/T4/build.txt` | Reported (T4) |
| 110 | Half-width defaults to 6 total volatilities, where the boundary's contribution is about 1.5e-8 and widening further buys nothing. | `include/touchstone/pde.hpp` (`half_width_sigmas`); `tests/test_pde.cpp` ("domain width at a fixed dx"); `docs/briefs/T3a-design-rulings.md` F10 | Asserted (domain-width test); source |
| 111 | The dominance margin is computed for every grid and reported in `PdeResult`, as is the Péclet number, reported rather than enforced. | `src/pde.cpp` (`GridSolver` constructor, `result`); `include/touchstone/pde.hpp` | Source |
| 112 | No `.clang-format`: the closest configuration found still rewrites lines, mostly hand-aligned comments and coefficient tables; `.editorconfig` states what the sources do. | `docs/evidence/T5/build.txt` §6 (the configuration, the counts, the kinds of change); `.editorconfig` and §7 there | Reported |

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
| 117 | T0: 7,200 grid rows and 34 edge rows from QuantLib 1.43, regenerated byte for byte in CI. | `golden/bs_vanilla.json` (`oracle.version`); `tests/test_closed_form.cpp` (7200 and 34 asserted); `.github/workflows/ci.yml` | Asserted |
| 118 | T1's, T2's, T3's, T3a's and T4's contents as listed. | `ROADMAP.md` (each milestone's deliverables and passed line); `docs/evidence/T3/summary.md` (Done 1, `scales.hpp`) | Source |
| 119 | T1's Fable tollgate: PASS. | `docs/evidence/T1/verdict.md` | Source |
| 120 | T4 released as `v0.4.0`. | `ROADMAP.md` T4 passed line | Source |
| 121 | T1's adversarial review: re-derived formulas, mutation, NaN search; seven real problems, all fixed; inputs kept in `test_limits.cpp`. | `docs/evidence/T1/summary.md` (Done 11); `tests/test_limits.cpp` ("inputs that used to be wrong, kept as regressions") | Source; regressions asserted |
| 122 | T2: a review flagged the hazard; redone by Fable: PASS WITH DEFECTS, defects in the pack and a comment, none in the library. | `docs/evidence/T2/summary.md` (Owner actions 3); `docs/evidence/T2/verdict.md` | Source |
| 123 | T3: the summed-drift check, the input σ = √(2·10³⁰⁰), q = 10³⁰⁰, r = 0, T = 10¹⁰, NaN in all seven outputs; repaired by `scales.hpp`; kept in `test_associations.cpp`. | `docs/evidence/T3/summary.md` (Done 1); `tests/test_associations.cpp` | Asserted |
| 124 | T3a's repeated-code review by a session that had not written the change; findings closed. | `docs/evidence/T3a/review.md` | Source |
| 125 | T4's audit by Fable: Node and headless Chromium, page and worker; the release job's upload defect; fixed by a flat assembly downloaded on every push. | `docs/evidence/T4/summary.md` (second entry); `.github/workflows/wasm.yml` (`downloaded` job) | Source; download checked in CI |
| 126 | T5's claims were checked one by one by an agent that did not write the document. | This file, last section | Source |
| 127 | The text removed from comments at T3a, as recorded. | `docs/evidence/T3a/history.md` | Source |
| 128 | The text removed from comments at T5, as recorded. | `git show 1755f0c ea23329 6d80fb0` (the removed lines) | Source |
| 129 | The sources' comments name no milestone, review or governance id. | `docs/evidence/T5/build.txt` §3 (the grep, its pattern and its empty result) | Source |

## The independent check

*Pending: filled in from the checking agent's report before the pack is final.*
