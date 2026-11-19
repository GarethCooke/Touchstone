# T6 — the review for repeated code, and how each finding was closed

**Who.** A separate agent, started fresh by this session with no part in writing the change,
given the standing rules (the brief's "Standing rules" and `ARCHITECTURE.md` §6) and the
range `fbf90f9..ed82a47` over `include/`, `src/`, `tests/`, `wasm/`, `golden/`, `bench/` and
`CMakeLists.txt`. It was asked for repeated code first, then arithmetic in the binding,
history in comments, and the library's own rules, with correctness defects noted
separately. It read the touched files whole and the code around them. It edited nothing.

**What it found.** 0 high, 3 medium (R1, R3, R4), 6 low (R2, R5 to R9), and three
correctness notes (C1 and C2 low, C3 information). It found no history in a comment beyond
R9, no exception that could leave the module, and no product formed outside
`detail/scales.hpp`.

**How each was closed.** Everything marked fixed is in `1129614` unless another commit is
named. The native suites, the smoke test and the differential in `tests.txt` ran after it.

| # | Finding (summarised) | Closed by |
| --- | --- | --- |
| R1 · medium | A path holds `steps + 1` values, and a sample is laid out path after path. That rule was written in several places: `sample_values`, `gbm_paths`'s loop, the binding's sizing, the tests, and the smoke and timing scripts. The binding's `plus_one`, for `gbmPath`, predates the change. | **Fixed in the library and the binding.** `src/paths.cpp` writes the per-path size once (`path_values`) and lays the sample out once (`step_sample`). `sample_values` is no longer public. The binding no longer sizes a sample (see R2). **Not changed:** the binding's `plus_one`, which belongs to v1.0.0's `gbmPath` and `brownianPath` and which this milestone does not touch; and the tests and scripts that read the layout from the outside. A test that holds the layout has to state it, and each now states it once, through `slice` in `test_paths.cpp`. |
| R2 · low | `gbm_paths` made its caller size the output, so the binding called `sample_values` and then `gbm_paths` called it again. The binding also allocated before validating, and every test repeated the sizing. | **Fixed.** A second `gbm_paths` returns its sample in a vector, after validating the inputs and before allocating, as `payoff` and the sweep return theirs. The binding and the tests call it. The ruled form, which writes into the caller's span, stays and is still tested. |
| R3 · medium | The seven closed-form outputs were listed in four places: the library's new pairing, the tests' `greek_fields`, the binding's `Fields<PriceAndGreeks>` and the smoke test. A new test existed only to check that two of those lists agreed. | **Fixed.** `price_and_greeks_columns` is the only place an output is paired with a member. `greek_fields` in the tests and `Fields<PriceAndGreeks>` in the binding hold only names: the golden file's and JavaScript's, in that order. Each takes its member from the pairing. The cross-check is gone. The smoke test reads the names from the module's own `priceAndGreeks` result. |
| R4 · medium | The smoke test copied `test_normal.cpp`'s reference values and its tolerance formula. | **Fixed.** The references and each row's tolerance are in `golden/normal-known-answers.json`, and both suites read them. The derivation of `(4 + x^2) eps` stays in `test_normal.cpp`'s comment. The values are unchanged: they are the ones `test_normal.cpp` held in its source, computed with mpmath at 60 digits. mpmath is not installed here, so they were carried over rather than recomputed, and `golden/README.md` says so. While the values were being moved, it came to light that the smoke test's copy had held φ to 2 ulps where the native suite holds 1e-16 and 4e-16. Both now read the same numbers. |
| R5 · low | The test, the smoke test and the binding each wrote out again the fields a sweep holds fixed. | **Fixed.** `ClosedFormSweep` has a defaulted `<=>`. The native test keys its map by the sweep, built by one `sweep_of(row)`, and the smoke test does the same with one `sweepOf`. In the binding, the sweep's names are the option's and the market's field constants, and `QuotedMarket`'s are the market's too. |
| R6 · low | `test_paths.cpp` read a row's dynamics twice and had two copies of its report block. | **Fixed.** `dynamics_of(row)` and `Agreement::report`. The v1.0.0 fixture's report prints exactly what it printed before. |
| R7 · low | The smoke test's Newton-then-Brent test built a quoted market twice and repriced twice. It also copied `1e-8` and `7000` from the native test. | **Fixed:** `quoted(row)`, from which `market(row)` is now built, and `repriceError`. **Kept:** `1e-8`, the exit criterion the native test names, and `7000`, its floor on rows solved. A smoke test in another language has to state a criterion to hold it, and the comment names where it comes from. |
| R8 · low | "The first n normals of a seed" is written three times: the generator's `draw`, the tests' `normals_from` and the binding's `draws`. The binding's copy is a loop. | **Not changed.** All three predate this change. The binding's copy is v1.0.0's `normals` and `uniforms`, which this milestone must leave alone. Each copy is held to `golden/rng-known-answers.json` on its own side: by `test_rng.cpp` natively and by the smoke test through the module. That same fixture holds the agreement that "path 0 of a sample is `gbm_path`'s path" relies on. A library `normals(seed, n)` that the binding called would close it. That is a new public function, which needs a ruling of its own. |
| R9 · low | A comment in `wasm/timing.mjs` named a demo id. | **Fixed:** it now says "a hedge sample at 256 rebalances". |
| C1 · low | A NaN spot gives a payoff of 0. The binding's comment said the library refuses NaN "where it refuses them for one value", and the payoff refuses nothing. | **The comment is corrected:** the closed form and the paths refuse NaN and the infinities, and the payoff and the normal functions, which refuse nothing, answer them. **The behaviour is the ruling's.** The ruled proposal says the array payoff "throws nothing, because the scalar refuses nothing", and v1.0.0's scalar payoff is what the grid and the Monte Carlo already use. Listed for the owner in the summary. |
| C2 · low | `normCdf(NaN)` and `normPdf(NaN)` return NaN. | **Ruling 4** (`normal-nan`, A): returns NaN, as the library's function and the site's TypeScript do. `ARCHITECTURE.md` §6's second rule covers the closed form, the Monte Carlo and the path functions, which N(x) is not. No change. |
| C3 · info | The sweep computed the points before a refused one, then threw them away. Nothing was observable, but the ruled proposal says "every point is validated before any is computed". | **Fixed.** `price_and_greeks` over a sweep calls `require_valid` over every point first. Its cost is in `timing.txt` §1: one call of 200,000 points went from 31.0 ms to 36.4 ms. |

**Checked and found clean by the reviewer:** no milestone, review, ruling or constitution id
in an added comment; `ownBuffer`'s size comparison is translation; `write_gbm_steps` removed
the duplicate that `write_gbm` had held, and the generator's `gbm_steps` did the same in
Python; the validation helpers in `src/paths.cpp` move the old checks without restating
them; every new product goes through `GbmStep` or `ClosedForm`; nothing new depends on
anything but its inputs; and the binding's other new code is translation.
