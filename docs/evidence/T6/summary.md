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
