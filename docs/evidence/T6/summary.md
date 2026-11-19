# T6 — What the demos need from the browser build · evidence pack

## Work order (P3)

**Goal.** T6 is defined by its `ROADMAP.md` entry and by the owner's ruling of 2026-11-19 in
`docs/briefs/T6-browser-build-needs.md`. Where the two disagree, the roadmap governs. The
binding exports the payoff, N(x) and the normal density. The library steps a sample of
geometric Brownian motion paths, exact and Euler, path by path from one stream, and the
binding carries it. A closed-form entry point takes many spots and times to expiry in one
call, and has its binding. The binding exports `implied_vol` (Newton, then Brent) beside the
safeguarded solver. `ARCHITECTURE.md`, its claims list and the README are made current, and
the version goes to 1.1.0. The signatures are proposed by the session and ruled on by the
owner before any of them is built. One session, two at most, and this milestone only (P2).

**Read first (P1):** `CONSTITUTION.md` (through A12); `ROADMAP.md` (T6); the brief; the
previous milestone's log, `docs/evidence/T5/summary.md`; `docs/briefs/T3a-design-rulings.md`
for the standing rules; `wasm/binding.cpp`, `wasm/errors.post.js`, `paths.hpp`,
`detail/path_generator.hpp`, `src/paths.cpp`, `black_scholes.hpp`, `contract.hpp`,
`normal.hpp` and `implied_vol.hpp`. I also read the site's call sites in `touchstone-learn`
at `8d7293c` without editing anything (I18): `experiments/euler.ts`, `experiments/hedging.ts`,
`tests/d4-experiment.test.ts`, `D6BlackScholes.tsx` and `chart.ts`.

**Roadmap against brief.** I found no disagreement. The roadmap says the library steps a
sample "path by path from one stream". The proposal meets that with a library function that
steps each path from its run of the stream's normals, where the stream is the library's own
generator, exported as `normals`. Ruling 5 in `signatures.md` asks whether the owner reads
the roadmap the same way.

**Steps.** Branch `m/T6` from `fbf90f9`.

1. **Proposal, then stop.** `signatures.md`: the C++ and JavaScript signature of each need,
   with one line of reasoning each, and the choices for the owner's ruling. Nothing is built
   before the ruling. *(This session.)*
2. Baselines on `main` before any edit: the native suite with every assertion printed on both
   compilers and under the sanitizers; the Release object files; the WebAssembly artifact, its
   size and its smoke test; and the brief's two timings rerun on this machine.
3. The library: the ruled functions in `contract.hpp`, `paths.hpp` and `black_scholes.hpp`,
   each with its native test. `gbm_path` and `gbm_paths` share one per-path loop in `detail`.
   `generate_paths.py` and its fixture are extended by the same independent transcription.
4. The binding: the ruled exports, translation only, and the new solver's settings in
   `defaults()`. An array argument costs its own length whatever larger array it is a slice
   of (ruling 12), and a getter or proxy that throws still does so before the module is
   entered. `smoke.test.mjs` calls each new export and holds it to a number the native tests
   hold, and holds ruling 12.
5. Measurement: the cost of one closed-form point through the module in Node, measured beside
   the brief's two figures, and 200,000 points taken twice: as one call, and as 781 calls of
   256 points, each a slice of one array (ruling 12). The audit's four `structuredClone`
   timings are rerun on this machine and reported beside the result. If 200,000 points take
   more than 200 ms in either pattern, stop and return to the owner. Size is reported with and
   without exception catching, against 500,000 bytes.
6. A review for repeated code by a session that did not write the change; its findings closed.
7. `ARCHITECTURE.md` (the status line, §1's version, §4, §5, §10.1, §11), the claims list, the
   README, and 1.1.0 in `CMakeLists.txt`. No tag is pushed: the owner tags `v1.1.0` after the
   merge.

**Decisions.** Recorded in `signatures.md` as recommendations for the owner's ruling. None is
taken under P4's "owner may overrule", because the brief reserves the signatures for the
owner.

---

### 2026-11-19 · claude-opus-5-5 · the owner's ruling recorded; the five needs built as ruled, with ruling 12; reviewed, measured, documented as 1.1.0; pull request open

**Exit criteria** (`ROADMAP.md` T6)

| Criterion | State | Where |
| --- | --- | --- |
| Every test that was green is green, on both compilers and under the sanitizers | **Pass.** g++ 15.2 and clang 22.1 here: 18/18, 126 cases, 4,203,630 assertions (before: 120, 4,140,490). CI: g++ 13.3, clang 18.1 and asan + ubsan, 18/18 | `tests.txt` §1, §6 |
| Nothing `v1.0.0` exports has changed its signature or its numbers | **Pass**, with ruling 10's one extra key in `defaults()`. Five of seven library objects byte-identical; every printed assertion line of the before run present after but 17 on g++, each accounted for (N(x)'s checks, which now take runtime arguments, and counts); v1.0.0's smoke test passes 16 of 17 on the new artifact, the 17th the extra key; 31,518 calls of every v1.0.0 export identical on both artifacts | `tests.txt` §2 |
| Each new piece has its test; the smoke test calls each new export through the module | **Pass.** Six new native cases, three extended; seven new smoke tests, each export held to what the native suite holds | `tests.txt` §1, §3 |
| The cost of one closed-form point through the module, measured and reported | **Pass.** 0.18 µs a point in one call of 200,000 (36.4 ms); 0.29 µs in 781 calls of 256 slices (57.1 ms); 11.3 µs one call a point. Inside the 200 ms budget in both patterns | `timing.txt` |
| No arithmetic in the binding | **Pass** for everything this milestone added: sizes, loops and layouts are the library's. v1.0.0's `plus_one` and its `normals` loop predate it and are unchanged (`review.md`, R1 and R8) | `review.md` |
| A review for repeated code by a session that did not write the change, its findings closed | **Pass.** 0 high, 3 medium, 6 low, 3 notes; each fixed or answered with its reason | `review.md` |
| Artifact under 500 KB, reported | **Pass.** 214,865 bytes here, 214,863 in CI, with catching; 173,196 without | `build.txt` §2(d) |
| No new dependency | **Pass.** The library includes only the standard library and its own headers; `golden/normal-known-answers.json` is data | `build.txt` §3 |
| Released as `v1.1.0` | **Owner's step.** `CMakeLists.txt` is at 1.1.0; no tag was pushed | — |

**Done**
- Recorded the owner's ruling at the top of `signatures.md`: his answer verbatim, the mapping of
  the first eleven items to the questions, and ruling 12 with its text and its grounds. Added
  ruling 12 to steps 4 and 5 of the work order (`6839301`).
- Emscripten 6.0.13 from `emscripten-core/emsdk`, in `C:\local\emsdk`, outside the repository
  (`build.txt` §1).
- Step 2, baselines on main's code before any edit: the native suite with every assertion
  printed on g++ and Clang, the Release objects, the artifact, its size and its smoke test,
  and the brief's timings (`b7add7f` is the first edit).
- Step 3, the library (`b7add7f`, `1129614`): `payoff` over spans; `StepGrid`, its
  `require_valid` and `gbm_paths` in two forms, one writing into the caller's span as ruled
  and one returning its sample; `ClosedFormSweep`, `PriceAndGreeksColumns`, the pairing
  `price_and_greeks_columns`, `require_valid` and `price_and_greeks` over a sweep. `gbm_path`
  and `gbm_paths` share one per-path loop. The path fixture gains a samples section from the
  same independent transcription, generated on Linux; its existing paths are unchanged.
- Step 4, the binding (`ed82a47`, `1129614`): `payoff`, `normCdf`, `normPdf`, `gbmPaths`,
  `priceAndGreeksAt`, `impliedVolNewtonBrent`, and `defaults().impliedVolNewtonBrent`. Ruling
  12: `errors.post.js` gives a partial typed-array view a buffer of its own before the clone.
  The smoke test holds that each slice reaches the clone at its own length, and that a getter
  or a proxy still throws before the module is entered.
- Step 5, measurement (`timing.txt`, `wasm/timing.mjs`): the closed form through the module
  three ways, the audit's four clone timings, and the brief's two figures, on this machine.
- Step 6, the review (`review.md`) and its closure (`1129614`, `2b54642`). A second agent
  checked every claim row; its seven corrections are made (`claims.md`, last section).
- Step 7: `ARCHITECTURE.md`, `docs/evidence/T6/claims.md` (rows 161 to 184), the README, and
  1.1.0 (`9e9b196`). Branch pushed; pull request opened to main.

**Decisions (with why)** — each reversible; owner may overrule.
- **emsdk was checked, not reinstalled.** `C:\local\emsdk` was already a checkout of
  `emscripten-core/emsdk` at tag 6.0.13, clean, with sdk 6.0.13 installed: T4 put it there.
  The previous session's note that no emsdk was found was wrong for this machine. A second
  copy of the same release would have changed nothing the builds use.
- **Public additions beyond the ruled signatures**, each to keep a rule written once:
  - `gbm_paths` returning a vector (the review's R2), so that neither the binding nor a test
    sizes a sample;
  - `price_and_greeks_columns`, the one pairing of columns with outputs, which the sweep, the
    tests and the binding read;
  - a defaulted `<=>` on `ClosedFormSweep`, so that a sweep can key a map (R5).
  None changes a ruled signature.
- **Ruling 12's "how".** A typed array whose bytes are not its whole buffer is copied with
  `slice()` before `structuredClone`, in `errors.post.js`, where the clone already is; a whole
  array and every other argument pass as before. A proxy is not a view and still meets the
  clone, which refuses it before the module is entered, as at v1.0.0.
- **Accepted arrays:** a `Float64Array`, or a plain array whose every element is a number,
  checked in one call when all are finite and element by element otherwise. Any other typed
  array, a string, a hole and a BigInt are each a `TypeError`. The proposal named these two
  kinds.
- **The sweep validates every point before computing any.** The ruled proposal says so; it
  cost 31.0 ms → 36.4 ms for 200,000 points (`review.md`, C3).
- **N(x)'s references moved to `golden/normal-known-answers.json`** (R4) so the module is held
  to the native suite's numbers rather than a copy. The values are carried over, not
  recomputed: mpmath is not installed here.
- **The path fixture keeps schema `paths@1`:** the samples section is an addition, and every
  existing reader reads what it read before.
- **`ARCHITECTURE.md` beyond the brief's list:** §2, §3, §6's seventh rule, §7, §8 and §9 each
  held a sentence this change made untrue (the fixtures, `wasm/`'s contents, 300,000 refusals,
  "the WebAssembly build, which was not timed").
- **The claims are in `docs/evidence/T6/claims.md`,** numbered on from T5's, with the T5 rows
  they replace named; T5's pack is left as its tollgate read it.
- **Local Clang** targets MinGW's libstdc++, with two vendored-header diagnostics of Clang 22
  left as warnings on the command line (`build.txt` §2(b)). CI's Clang 18 is the authoritative
  run.

**Not done**
- No tag pushed and nothing merged: the owner tags `v1.1.0` on the merged commit.
- The sanitizers were not run on this machine (MinGW has none; installing a Linux toolchain in
  WSL would have changed the system); CI ran them, green.
- The timings are on Node 24.13.1, the installed Node; none on Node 22, which CI and the brief
  used.
- Left as they are, with reasons in `review.md`: v1.0.0's `plus_one` and `normals` loop in the
  binding (R1, R8), and a NaN spot's payoff of zero, which is the ruled behaviour (C1). R8's
  fix would be a library `normals(seed, n)`, a new public function for a later ruling.
- The Clang before-run's output file has a patch of binary data in `test_rng.cpp`'s lines; the
  comparison there rests on g++ (`tests.txt` §2(b)).

**For the owner**
- `payoff` at a NaN spot returns 0, silently, as the scalar always has (`review.md`, C1). A
  demo that passes a NaN will draw a flat payoff rather than fail.
- On g++, `norm_cdf` on a literal is folded at compile time to the correctly rounded value,
  so a test that calls it on a literal measures the compiler, not the library. The
  N(x) references now go through runtime arguments (`tests.txt` §2(b)).

**Exact next step**
- The owner reviews the pull request, merges it, tags `v1.1.0` on the merged commit so
  `release.yml` publishes, and ticks T6 in `ROADMAP.md`. Then L5 vendors v1.1.0, and the
  portfolio's write-up is refreshed from the new `ARCHITECTURE.md`.

### 2026-11-19 · claude-opus-5-5 · signatures proposed for all five needs; stopped for the owner's ruling

**Done**
- Read what P1 and the brief name (listed in the work order).
- Wrote `docs/evidence/T6/signatures.md`. It has a C++ and a JavaScript signature for each of
  the five needs, with the reasoning for each, and eleven questions for the owner's ruling,
  each with a recommendation and its alternative. In summary:
  - **Payoff:** an array overload of the library's `payoff`, and `payoff({strike, type}, spots)`
    in JavaScript.
  - **N(x) and the density:** scalar `normCdf` and `normPdf`, with no library change.
  - **Paths:** `StepGrid` and `gbm_paths`, which step many paths from the caller's normals, and
    `gbmPaths(spec, normals)` in JavaScript.
  - **Closed form at many points:** `ClosedFormSweep`, `PriceAndGreeksColumns` and a
    `price_and_greeks` overload over paired spots and times to expiry, and
    `priceAndGreeksAt(sweep, spots, timesToExpiry)` in JavaScript.
  - **Newton, then Brent:** `impliedVolNewtonBrent`, with its settings under the same key in
    `defaults()`.

**Decisions (with why)**
- None taken. The brief says the owner rules on the signatures, so every choice is in
  `signatures.md` as a recommendation.

**Not done**
- Steps 2 to 7: nothing is built, measured or changed in the library, the binding, the
  fixtures or the documents.
- Emscripten is not installed on this machine (`emcc` is not on the path, and no emsdk was
  found). The build session needs the emsdk release that CI pins, installed as T4 installed
  it, before it can take the baselines or the measurement in step 5.

**Exact next step**
- The owner rules on the eleven questions at the end of `docs/evidence/T6/signatures.md`.
  The next session records the ruling at the top of that file and starts at step 2 of the
  work order.
