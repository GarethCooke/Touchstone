# T3a — the repeated-code review, and how each finding was closed

The exit criterion asks for a review for repeated code by a session that did not write the
change, with its findings closed. The review was run by a fresh agent session given the
owner's standing rule and the catalogue in `docs/briefs/T3a-design-rulings.md` §9, and told to
read every file under `include/`, `src/` and `tests/` at `a067ccc` and to edit nothing. It took
57 tool calls over about ten and a half minutes. Its report numbered its findings in three
groups; the numbers below are its numbers.

**Its verdict on the catalogue:** R1–R9, the `2^-53` literal and the four named test repeats
were closed at every site the brief cites. It then found more: some left over from the
catalogue, some introduced by this change, and a good deal of older repetition in the tests
that the catalogue, which only scanned them, had not listed.

**Closed** means changed so the thing is written once. **Kept** means not changed, with the
reason. Every finding it called *real* is closed except where a row below says why the two
places it named are not the same thing.

## 1 · The catalogue (R1–R9, `2^-53`)

| # | Review | Closure |
|---|---|---|
| 1.1–1.10 | Closed at every cited site | — |
| leftover in 1.2 | `option.strike * discount` in Monte Carlo is `K e^{-rT}` by hand | **Closed** — read from the `ClosedFormQuote` Monte Carlo now validates through (3.11) |
| leftover in 1.3 | Grid: `σ²/2` twice, the forward's drift in another association | **Closed** (3.6, 3.14) |
| leftover in 1.5 | The discounted intrinsic in Monte Carlo's overflow recovery | **Kept** — `w (S_T e^{-rT} − K e^{-rT})` with no `max`, for a path already known to be in the money: not the payoff, a different quantity |
| leftover in 1.9 | Three hand spellings of "finite and positive" in implied vol | **Closed** (3.16) |
| leftover in 1.10 | `2^-53` twice in `generate_paths.py` | **Closed** (3.35) |

## 2 · The four test repeats

| # | Review | Closure |
|---|---|---|
| 2.1 | `grid_stride` alias four times; `grid_stride == 1` | **Closed** — the four files use `sweep_scale` itself; `if constexpr (full_sweep)` |
| 2.2 | Copy-out lines in both readers; parallel `load()` bodies; Greek names in the golden reader | **Closed**: `GoldenCase` and `AmericanCase` extend `RowInputs`, so a row's inputs are assigned once; the golden reader reads the seven fields through `greek_fields`. **Kept**: the two `load()` bodies, which read different fields of different files and share every step that is the same (`fixture_path`, `read_json`, `require_schema`) |
| 2.3 | The per-field report and check block; members by hand elsewhere | **Closed** (3.20, 3.29) |
| 2.4 | The normal-drawing loop across files | **Closed** (3.28) |

## 3 · Other findings

| # | Severity | Finding | Closure |
|---|---|---|---|
| 3.1 | real | The two solvers validate budget, tolerance, target and bracket separately | **Closed** — `require_valid_budget`, `require_valid_target`, `bracket_of` |
| 3.2 | real | "The answer at a volatility" written four ways | **Closed** — one `answer(result, vol, closed_form, target)` for both solvers; the safeguarded result is no longer copied on return |
| 3.3 | real | `ClosedForm` re-declares and copies seven of the quote's fields | **Closed** — `ClosedForm` holds its `ClosedFormQuote` and reads through it; `quote()` exposes it |
| 3.4 | real | Vega and theta's diffusion term each written twice in the constructor | **Closed** — `phi1` per branch, vega once after; the decay term one local lambda |
| 3.5 | real | The two concepts are one shape | **Closed** — `detail::returns_double<F, Args...>`; `VanillaPricer` and `RealFunction` are it |
| 3.6 | real | The log-price drift in two associations | **Closed** — `detail::log_drift_time`, used by the exact step, the grid's forward, and per unit time as the grid's convection coefficient |
| 3.7 | real | The risk-neutral step built three times | **Closed** — `risk_neutral_step`, `discounted_exact_step`; the generator is built from a step |
| 3.8 | real | The cell average's call and put branches mirror each other | **Closed** — one expression over the in-the-money part of the cell |
| 3.9 | real | Central differences in bump Greeks and the grid | **Closed** — `detail::central_first`, `central_second` |
| 3.10 | real | `θ dt a`, `θ dt c` formed in `build` and in `step` | **Closed** — stored with their matrix |
| 3.11 | real | `K e^{-rT}` by hand in Monte Carlo | **Closed** — see 1.2 |
| 3.12 | real | Brent's bisection fallback written twice | **Closed** — one fallback after an `interpolated` flag |
| 3.13 | real | Tridiagonal conformability twice | **Closed** — `bands_conform` |
| 3.14 | small | `σ²/2` twice; the check and the coefficient formed differently | **Closed** — `diffusion_coefficient`; the domain check guards twice it, which is the diagonal's product |
| 3.15 | small | "A put is in the money at the low end" three times | **Closed** — `in_the_money_below` |
| 3.16 | small | R9 leftovers | **Closed** |
| 3.17 | real | SCHEMA.md's scaled error re-implemented six ways in tests | **Closed** — every copy calls `scaled_error` |
| 3.18 | real | The spot-scaled grid error five times | **Closed** — `scaled_error(actual, reference, floor)`; `grid_error` is that with the spot. **Kept**: `test_american.cpp`'s two *signed* shortfalls (one-sided measurements, not an absolute error) and its American-against-European figure (a difference of two grid values over the exact price's scale) |
| 3.19 | real | "Track the worst and its row" hand-written at 17 sites | **Closed** — all 17 use `Largest<Row>`; `Worst` is built on it |
| 3.20 | real | The worst-per-field report and check three times | **Closed** — `WorstPerField` beside `greek_fields`; the reports print exactly as before |
| 3.21 | real | The forward contract's seven sensitivities in two tests | **Closed** — `forward_contract`; parity uses it, the collapsed limit scales it |
| 3.22 | real | `BlackScholesMarket` → `QuotedMarket` four times | **Closed** — `QuotedMarket::of`, public |
| 3.23 | real | Payoff values checked in two tests | **Closed** — `test_contract.cpp` only |
| 3.24 | real | Wide grid bumps and the grid pricer in two files | **Closed** — `tests/grid_bumps.hpp` |
| 3.25 | real | Settings repeated within `test_three_way` | **Closed** — `grid_settings()`, `path_settings()` |
| 3.26 | real | The standard-normal battery and the Poisson bound re-written | **Closed** — `Standardised::mean_bound`, `standard_deviation_bound`, `within_poisson` |
| 3.27 | real | Mean and variance two-pass four times | **Closed** — `moments`; `fit_log_log` returns its x-moments |
| 3.28 | real | Drawing n normals repeated | **Closed** — `fill_normals`, `normals_from` in `rng_fixture.hpp` |
| 3.29 | real | The seven Greek members spelled out by hand | **Closed** — loops over `greek_fields` (the collapsed limit keeps two explicit exact-zero checks, on purpose) |
| 3.30 | real | The RNG fixture's five keys listed twice | **Closed** — one table with member pointers |
| 3.31 | real | `asymptotic_below` and its report line twice | **Closed** |
| 3.32 | real | The domain-width case solves the same grids twice | **Closed** — one pass, kept errors |
| 3.33 | real | Admission rules written twice | **Closed** — `enough_in_the_money`, `has_signal`, `full_sweep` |
| 3.34 | real | `relative` defined twice | **Closed** — `relative_error` |
| 3.35 | real | `2^-53` and `1e-12` twice in the generator | **Closed** — named constants; the fixture's bytes unchanged on both platforms |
| 3.36 | borderline | Two hold-aside mechanisms with opposite policies | **Closed** — one `HeldAside`, keeping the first. The accumulator kept the last before; the difference is only the sign of an estimate already saturated at infinity, which the header says is not to be read |
| 3.37 | borderline | Bounds classification in both solvers | **Kept** — the rules differ by specification (`>= ceiling` against `> upper + tol`), and each solver follows its own; what is common — the quote and the bounds — is shared |
| 3.38 | borderline | Newton step and slope guard in both solvers | **Kept** — the step is Newton's one-line formula; the guards differ (a fixed bracket and a stall count against a moving bracket) |
| 3.39 | borderline | Brenner–Subrahmanyam's scale is vega at `d1 = 0` | **Kept** — it is a named, cited seed, and writing it as "vega at a volatility that makes `d1` zero" would obscure what it is |
| 3.40 | borderline | The products the domain check forms and the accessors form | **Kept** — they round identically (the accessors' sign flips are exact), and the check forms exactly the products the header lists |
| 3.41 | borderline | `grow` and `write_gbm`, two walks | **Closed** — one `walk` with a visitor |
| 3.42 | borderline | Settings boilerplate | **Kept** — the two refusal-test styles test different things; `test_american` states its grid on purpose, as `test_pde` argues a grid sweep should; the `#error` guards each name their own file; the field-by-field throws carry different messages over a shared predicate |
| 3.43 | borderline | Iterating every golden row five ways | **Kept** — the five walks differ in which blocks they visit and at what stride |
| 3.44 | borderline | Parallel accessor lists; the entry-point list in prose | **Closed** for the prose (the message no longer re-lists what the concepts say). **Kept**: the accessor list in `test_closed_form` and the concept list in `test_contract` make different claims — values against compile-time acceptance |
| 3.45 | borderline | Smaller patterns | **Closed**: `Bands::zeros`, `payoff_at_node`, `bonferroni_bound`. **Kept**: `bump_greeks`' early down-bump checks (they exist for their messages); the up/down pairs (inherent to a list of bumped points); `RunningMean` (the library's Welford accumulator is internal to `monte_carlo.cpp`); the one-line overload bodies (inherent to the free-function API) |
| 3.46 | deliberate | Independent checks | On record; not defects |

## What closing them changed in the numbers

The library's fixes moved no number the suite reports. The tests' fixes changed what the suite
prints in the places `tests.txt` §7 lists, and nothing it asserts.
