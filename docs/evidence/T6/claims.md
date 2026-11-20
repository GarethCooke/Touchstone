# T6 — claims map for what 1.1.0 added to or changed in `ARCHITECTURE.md`

`docs/evidence/T5/claims.md` maps every claim of the 1.0.0 document. This file maps the
claims 1.1.0 added and those it changed, numbered on from T5's last (160), in the order they
appear in the document. **Asserted**, **Reported** and **Source** mean what they mean there:
a test fails if the claim stops being true; a test or script prints the number and this pack
quotes it; the cited file is where the claim can be read. A T5 row a T6 row replaces is named
in the last column, and the T5 row no longer holds as written. Paths are from the repository
root.

## Status, §1 What this is

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 161 | The document describes Touchstone 1.1.0. Its claims are mapped in T5's claims file and, for those 1.1.0 added or changed, in this one. | `CMakeLists.txt` (`VERSION 1.1.0`); `wasm/smoke.test.mjs` ("the module says which version of the library it is"); this file | Source; asserted for the module. Replaces 1, 130 |
| 162 | Sample paths of Brownian and geometric Brownian motion from a frozen generator: one path from a seed, or a whole sample stepped from the normals a caller supplies. | `include/touchstone/paths.hpp` (`gbm_path`, `gbm_paths`); `tests/test_paths.cpp` | Source; asserted in 170–173. Extends 5 |
| 163 | At 1.1.0 the tutorial's demos run on a TypeScript backend; moving them is L5, not yet run. | `ROADMAP.md` (L5 unticked); `CONSTITUTION.md` I15 | Source. Replaces 6 |
| 164 | An input the path functions accept never produces a NaN, `gbm_paths` among them. | `tests/test_paths.cpp` ("an accepted path never holds a NaN, however extreme", which steps each extreme as one path and as a sample; "a sample with no normals is empty, and a sample that cannot be stepped is refused", the non-finite normals) | Asserted. Extends 11, 85 |

## §2 System overview, §3 Repo layout, §4 The public surface

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 165 | The tests read three known-answer fixtures beside the reference files and page 2.11's experiment: the generator's, the paths' and the normal distribution's. | `tests/CMakeLists.txt` (`TOUCHSTONE_RNG_FIXTURE_PATH`, `TOUCHSTONE_PATHS_FIXTURE_PATH`, `TOUCHSTONE_NORMAL_FIXTURE_PATH`); `golden/README.md` | Source. Extends 21, 35 |
| 166 | `wasm/` holds the binding, its error shim, its build script, its Node smoke test and its timing script; `golden/` holds three known-answer fixtures. | `wasm/binding.cpp`, `errors.post.js`, `build.sh`, `smoke.test.mjs`, `timing.mjs`; `golden/rng-known-answers.json`, `paths-known-answers.json`, `normal-known-answers.json` | Source. Replaces 33, 35 |
| 167 | `price_and_greeks` over a `ClosedFormSweep` evaluates many (spot, time to expiry) points; European only, with no defaults. | `include/touchstone/black_scholes.hpp` (`ClosedFormSweep`, which has no exercise style); `src/black_scholes.cpp` (`at_each_point`, which builds a `EuropeanVanilla` at each point); `tests/test_closed_form.cpp` | Source |
| 168 | `gbm_paths` steps a sample from the caller's normals; its grid defaults to a horizon of 1 and one step a path. | `include/touchstone/paths.hpp` (`StepGrid`: `horizon{1.0}`, `steps{1}`) | Source |
| 169 | `payoff` accepts either exercise style, at one spot or at each of many. | `include/touchstone/contract.hpp` (the two `payoff` templates over `Vanilla<E>`); `tests/test_contract.cpp` ("the payoff at many spots is the payoff at each, in order", a European call and an American put) | Asserted |

## §5 How each method is built

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 170 | `price_and_greeks` over a `ClosedFormSweep` holds the strike, direction, volatility, rate and dividend yield fixed, evaluates a `ClosedForm` at each pair, and returns one array per output; every point is validated before any is computed; a refused point refuses the call, and the message names the point. | `src/black_scholes.cpp` (`at_each_point`; `price_and_greeks(const ClosedFormSweep&, …)` calls `require_valid` over the sweep first); `tests/test_closed_form.cpp` ("a sweep is the closed form at each point, to the bit, over the golden file": 382 sweeps, 7,234 points, no value differing; "a sweep refuses what a point refuses, and says which point") | Asserted (each point identical to the one-point closed form; every row of the file covered; the refusal and its index); the counts reported; the order of validation source |
| 171 | `gbm_paths` steps path `p` from the `p`-th run of `steps` normals, through the same per-path loop as `gbm_path`. | `src/paths.cpp` (`detail::write_gbm_steps`, called by `PathGenerator::write_gbm`, and by both `gbm_paths` through `step_sample`); `tests/test_paths.cpp` ("a sample from one stream", every path equal to that run stepped alone) | Source (one loop); asserted (each run) |
| 172 | Path 0 of a sample drawn as `steps × paths` normals from one seed is `gbm_path`'s path at that seed, bit for bit. | `tests/test_paths.cpp` ("a sample from one stream: path 0 is gbm_path's at the seed", both schemes, three seeds, `==` on the vectors); `wasm/smoke.test.mjs` (the same through the module, `deepEqual`); `golden/generate_paths.py` (refuses to write a sample whose path 0 is not its seed's single path) | Asserted |
| 173 | Both schemes can be stepped from one array of normals, and normals recorded elsewhere can be stepped too. | `include/touchstone/paths.hpp` (`gbm_paths` takes the normals as an argument); `tests/test_paths.cpp` ("both schemes from the same normals") | Asserted for the first; source for the second |
| 174 | A normal that is not finite is refused, because at a volatility of zero an infinite one would make a step's exponent `0 × ∞`. | `src/paths.cpp` (`validated_values`, which `require_valid(const StepGrid&, …)` and the returning `gbm_paths` both call); `tests/test_paths.cpp` (±∞ and NaN, at volatilities 0 and 0.2); `wasm/smoke.test.mjs` (a `RangeError` for an infinite normal) | Asserted |
| 175 | The binding exports, beyond the 1.0.0 set, `payoff` at many spots, `normCdf`, `normPdf`, `gbmPaths`, `priceAndGreeksAt` and `impliedVolNewtonBrent` (the library's `implied_vol`) beside `impliedVol` (the safeguarded solver). | `wasm/binding.cpp` (the registrations at the end); `wasm/smoke.test.mjs` (each called and held: the payoff's values; N(x) and φ to `golden/normal-known-answers.json`, the references and tolerances `tests/test_normal.cpp` reads; the fixture's samples; every golden row as a sweep, identical to `priceAndGreeks`; the price round trip over the golden file inside 1e-8, and Brent with one Newton step) | Asserted. Extends 81 |
| 176 | `defaults()` exports the default settings of every bound entry point that takes settings. | `wasm/binding.cpp` (`defaults`: six settings types); `wasm/smoke.test.mjs` ("the library's defaults are the module's": six keys) | Asserted. Replaces 82 |
| 177 | An array argument is a `Float64Array` or a plain array of numbers. | `wasm/binding.cpp` (`read_numbers`); `wasm/smoke.test.mjs` (a string, a hole, a BigInt, a `Float32Array` and a number each refused with a `TypeError`) | Asserted |
| 178 | A loop over points or paths is a library function called once, so a demo's redraw crosses the boundary a few times rather than once a point. | `wasm/binding.cpp` (`payoffs`, `gbm_sample`, `closed_form_at`: one library call each); `docs/evidence/T6/timing.txt` (200,000 points: one call against 200,000 calls) | Source; the cost reported |

## §6 Invariants, §7 Timings, §8 Decisions, §9 Out of scope

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 179 | `wasm/smoke.test.mjs` makes 500,000 refused calls, 100,000 of them a throwing getter refused before the module is entered, and then reproduces the RNG fixture and one golden row exactly as before. | `wasm/smoke.test.mjs` ("survives a hundred thousand refusals of each kind": five kinds) | Asserted. Replaces 93 |
| 180 | §7 does not time the WebAssembly build. | `ARCHITECTURE.md` §7 (`bench/timing.cpp` is native) | Source. Replaces 98's first clause |
| 181 | A typed array that is a view into part of a larger buffer is copied into a buffer of its own before the clone, because the clone copies a view's whole buffer; a slice costs its own length. | `wasm/errors.post.js` (`ownBuffer`); `wasm/smoke.test.mjs` ("a slice of a larger array is handed over as itself, and costs its own length": two 256-value slices of 200,704-value arrays, one a path of a sample and one of times to expiry, each reach the clone in a 2,048-byte buffer; "a getter on an array argument still throws before the module is entered"); `docs/evidence/T6/timing.txt` (the clone's cost for each) | Asserted; the cost reported |
| 182 | Not claimed, because not done here: an MSVC build; a browser loading the artifact in this repository's CI, which runs it in Node; any timing beyond §7. The closed form was timed through the WebAssembly module in Node on one machine, and `docs/evidence/T6/timing.txt` records it as that machine's numbers; nothing in the document claims them. | `docs/evidence/T6/timing.txt`; `wasm/timing.mjs` | Source. Replaces 115 |

## §10 History, §11 Changes

| # | Claim | Held by | How |
| --- | --- | --- | --- |
| 183 | §10.1's T6 row: 2026-11-20, released as `v1.1.0`; the payoff at many spots, a sample from the caller's normals, the closed form at many points, their bindings with `normCdf`, `normPdf` and `impliedVolNewtonBrent`; an array argument costs its own length; 1.1.0; signatures proposed and ruled on before any was built. | `docs/evidence/T6/signatures.md` (the ruling, at its top); `docs/evidence/T6/summary.md`; `CMakeLists.txt` | Source |
| 184 | §11: 2026-11-19, Touchstone 1.1.0. | This branch's history | Source |

## The independent check

An agent that did not write this file or the document checked every row against the sentence
it maps and against each cited source, on 9e9b196, and edited nothing. Its verdicts: 17 rows
hold; seven hold with a correction, each made above; none fails; one changed sentence was
unmapped. It could not run the native test binaries in its own environment, so it re-derived
the sweep figures from `golden/bs_vanilla.json`: 7,234 points in 382 sweeps, as the test
reports. `timing.txt` and `summary.md` were not yet committed when it ran, and their
citations were marked pending.

| Row | What it found | What changed |
| --- | --- | --- |
| 167 | The header does not build a `EuropeanVanilla`; `at_each_point` in the source does. | The source is cited for it. |
| 170 | The counts are printed by the test, not asserted; the order of validation is only in the code. | "How" says which part is asserted, reported and source. |
| 171 | `write_gbm_steps` is reached through `step_sample`, which both `gbm_paths` call. | Said so. |
| 174 | The finiteness check is in `validated_values`. | Cited. |
| 176 | "The second solver's included" goes beyond the document's sentence. | Dropped. |
| 181 | The test hands over two slices of two arrays, one a path of a sample. | Said so. |
| 182 | §9 dropped "a timing of the WebAssembly build", and T5's row 115 still states the old list; no T6 row mapped the new one. | Row 182 now states §9's list and replaces 115. |
