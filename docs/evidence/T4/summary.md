# T4 — WASM artifact · evidence pack

## Work order (P3)

**Goal.** T4 as `ROADMAP.md` states it: an Emscripten build of Touchstone with an embind API
carrying every `PricingBackend` method (`touchstone-learn/src/demos/types.ts` at `m/L2`, read,
not edited) and the Monte Carlo, grid and bump-Greek entry points D7, D8 and D10 will need,
because L5 cannot edit this repository (I18); C++ exception catching switched on, each
exception reaching JavaScript as an error (ruling 3); size under 500 KB, reported with and
without exception support; built in CI; published as a GitHub release artifact tagged
`v0.4.0` (F11). Exit: the artifact builds in CI; a smoke test loads it in Node, reproduces
the RNG fixture and one golden price, and survives an input the library rejects. Over
500 KB, stop and return to the owner.

**Steps.** Branch `m/T4` from `1a9b465`.

1. Toolchain: Emscripten pinned to one exact release at least two weeks old, installed from
   the first-party `emscripten-core/emsdk` repository, locally and in CI alike.
2. The binding, `wasm/binding.cpp`: the seven `PricingBackend` methods under their
   `types.ts` names and shapes; `monteCarlo`, `crankNicolson` and its readable surface for
   D8, `bumpGreeks` over the closed form, the grid or the Monte Carlo for D10; the library's
   default settings exported once so the site does not retype them. Inputs read from plain
   JavaScript objects with partial settings allowed, as `types.ts` allows them.
3. Errors: every C++ exception caught inside the binding and thrown into JavaScript as an
   `Error` (`RangeError` for `std::invalid_argument`, as the TypeScript does), and a module
   that keeps working after any number of them.
4. CMake: the WASM target beside the library, the library's own sources unchanged; the
   project version to `0.4.0` (F11).
5. Size: the artifact built with and without exception support; both reported; the
   shipped one checked against 500 KB in CI.
6. The smoke test, `wasm/smoke.test.mjs` under Node: the RNG fixture; one named golden price
   (and the rest of the golden file, since it costs nothing); an input the library rejects,
   repeated until a leak would show, then the fixture again. Also each extra entry point
   once against the closed form, and the path fixture, so L5 inherits a binding already
   held to the numbers.
7. CI: a `wasm` job in `ci.yml` that builds, size-checks, smoke-tests and uploads the
   artifact; a `release.yml` that runs the same from a `v*` tag and creates the GitHub
   release with the artifact attached. The session does not push the tag or create the
   release (owner's instruction); it gives the commands for after the merge.
8. README status; evidence; push the branch and read the Actions run.

**Decisions taken before starting** (each *Decision — owner may overrule*):

- **The artifact is one `.wasm` plus an ES-module glue file** (tech-decision B4), loaded by
  a factory, `createTouchstone()`, in the browser and in Node.
- **The binding is not the `PricingBackend` itself.** It carries every method under the
  interface's name, with the interface's argument and result shapes, so that L5's
  `wasmBackend` is a wrapper of a few lines; the wrapper and the `name` field are the site's.
- **A refused implied-vol price comes through as the library returns it**: σ = 0 below the
  lower bound and σ = +∞ above the upper one, with the status. That was T3a's decision and
  the owner let it stand at the merge; `types.ts` still says NaN, which is L5's to change
  (I18).
- **What the binding refuses that the TypeScript coerces**: a seed that is not an integer in
  `[0, 2^32)`, a count or step number that is not a non-negative integer. The library's
  seed is a `uint32`, and silently wrapping a seed of `-1` would make two backends draw
  different streams from what the caller thinks is one seed.

---

### 2026-11-13 · claude-opus-5-5 · Touchstone in the browser: 174 KB with exception catching, every `PricingBackend` method and the three entry points the later demos need, held to the fixtures in Node, and no refusal that can kill it

**Done**

1. **The artifact** (`wasm/`). `touchstone.mjs`, an ES module whose default export
   `createTouchstone()` resolves to the module, and `touchstone.wasm` beside it: Emscripten
   6.0.13, `-O3`, embind. The library's sources are unchanged and built under Emscripten for
   the first time, with the project's warnings and `-Werror`: 0 warnings (`build.txt` §2).
2. **The binding** (`wasm/binding.cpp`). The seven `PricingBackend` methods —
   `uniforms`, `normals`, `brownianPath`, `gbmPath`, `priceAndGreeks`, `noArbitrageBounds`,
   `impliedVol` — under their `types.ts` names, taking and returning the shapes `types.ts`
   declares: camelCase fields, `'call'`/`'put'`, `'exact'`/`'euler'`, partial settings filled
   from the library's defaults, `Float64Array` paths, the step trace when `trace` is set.
   Beyond the interface: `monteCarlo` (D7); `crankNicolson` and `crankNicolsonSurface`, the
   grid's solution at every node and every *n*-th level, expiry to today, for D8, both
   accepting `exercise: 'american'`; `bumpGreeks` over the closed form, the grid (European
   or American) or the Monte Carlo, for D10; `defaults()`, the library's settings, so the site
   never retypes them; and `version`. Each value type's JavaScript fields are written once,
   as a table that both reads and writes it; each enumeration's names likewise. No
   arithmetic happens on the way through.
3. **Errors (ruling 3), and what it took for the module to survive them.** Catching is on
   (`-fwasm-exceptions`). Every C++ exception is caught inside the module and becomes a
   JavaScript error: `RangeError` for an input the library rejects (its own message, as the
   TypeScript throws `RangeError`), `TypeError` for an argument of the wrong shape, `Error`
   otherwise. The first design threw that error from inside the module, and it died within
   200,000 refusals. **Anything thrown through WebAssembly frames, C++ or JavaScript, leaves
   the module's stack pointer behind**: embind restores it only around calls that
   stack-allocate their arguments, and the 64 KB stack runs out. Measured: a JavaScript
   throw from inside a call kills the module at call 2,074; the build without catching,
   whose every refusal is an abort thrown the same way, at refusal 178 (`tests.txt` §2). So
   nothing is thrown through the module: each bound function *returns* the error, and
   `wasm/errors.post.js` throws it once the call has returned; and the arguments are
   structured-cloned in JavaScript first, so that a getter or a proxy on a caller's object
   runs, and throws if it throws, before the module is entered.
4. **Size, both ways** (`build.txt` §3). Shipped, with catching: **173,890 bytes** (.wasm
   145,104 + .mjs 28,786), 56,017 gzipped: 35% of the 500,000-byte budget, read strictly as
   the two files uncompressed. Without catching: 142,240 bytes, 50,024 gzipped. Catching
   costs 31,650 bytes. `wasm/build.sh` builds both, writes the report, and fails over budget.
5. **The smoke test** (`wasm/smoke.test.mjs`, `node --test`, no package). 17 tests, all
   passing (`tests.txt` §1). The criterion: the module loads in Node; the RNG fixture
   reproduces (uniforms to the bit, normals worst 0 against 1e-12); the golden row
   `one-day-atm` reproduces, price and six Greeks, worst 6.2e-14 against the file's 1e-8;
   and an input the library rejects is a `RangeError` with the library's reason — then
   100,000 refusals each by the library, by the binding and by a throwing getter, after which
   the named row is identical to the bit, the RNG fixture still reproduces and a 4.2 MB grid
   surface is still allocated. Beyond the criterion: all 7234 golden rows (worst 2.8e-13 on
   the grid), the path fixture **to the bit**, page 2.11's trace iterate by iterate to
   7.1e-15 (as native) and its refusals with no NaN, and each extra entry point against the
   closed form.
6. **CI and the release.** `.github/workflows/wasm.yml` installs Emscripten from the
   first-party emsdk repository at the pinned tag, runs `wasm/build.sh` and the smoke test on
   Node 22 (the site's), and uploads the artifact. `ci.yml` calls it on every push;
   `release.yml` calls it on a `v*` tag, checks the tag against `CMakeLists.txt`'s version,
   and creates the GitHub release with `touchstone.mjs`, `touchstone.wasm`, `size.txt` and
   `SHA256SUMS`: the files that passed the smoke test in the same run. The project version
   is 0.4.0 (F11). The session pushed no tag and created no release.
7. **The native side is unchanged**: g++ 15.2 locally, 0 warnings, 18 of 18 ctest entries
   (`tests.txt` §3); CI's three native jobs in `tests.txt` §4.

**Exit criteria**

| Criterion | Result |
|---|---|
| Artifact builds in CI | **PASS** — run 43436214813 on `103af47`: the `wasm` job built both ways, checked the size, ran the smoke test on Node 22 (17 of 17) and uploaded the artifact; gcc 13.3, clang 18.1.3, ASan+UBSan and the golden job green beside it (`tests.txt` §4). |
| A smoke test loads it in Node | **PASS** — `wasm/smoke.test.mjs`; locally on Node 24, in CI on Node 22. |
| …reproduces the RNG fixture | **PASS** — all three seeds; uniforms identical, normals worst difference 0 (tolerance 1e-12). |
| …and one golden price | **PASS** — `one-day-atm`, price 0.4203523730423484 against 0.4203523730423497, all seven outputs within 6.2e-14 (tolerance 1e-8); and all 7234 rows within the file's tolerances. |
| …and survives an input the library rejects | **PASS** — `RangeError` with the library's message; 300,000 refusals of three kinds, then the fixtures again, unchanged. Without the design of Done 3 the module dies at call 2,074 (or, without catching, refusal 178). |
| Size under 500 KB, reported with and without exception support | **PASS** — 173,890 bytes with, 142,240 without; gzipped 56,017 and 50,024. |
| Every `PricingBackend` method, and the entry points D7, D8 and D10 need | **PASS** — the seven methods with `types.ts`'s shapes; `monteCarlo`, `crankNicolson`, `crankNicolsonSurface`, `bumpGreeks`; each exercised by the smoke test. |
| C++ exception catching on, each exception reaching JavaScript as an error | **PASS** — `-fwasm-exceptions`; `RangeError`, `TypeError` or `Error`, never a C++ exception and never a crash. |
| Published as a GitHub release artifact tagged `v0.4.0` | **SET UP, NOT RUN** — by the owner's instruction the session pushed no tag. `release.yml` runs on the tag; the commands are under **Exact next step**. |

**Decisions (with why)** — each *Decision — owner may overrule*, besides those in the work
order:

- **Errors are returned across the boundary and thrown in JavaScript** (Done 3). The
  alternative that keeps everything in C++, throwing the JavaScript error from inside the
  module, is the one measured to die. The cost is `errors.post.js`, 35 lines, and the bound
  functions staying on the module under `raw_` names, hidden from enumeration rather than
  deleted because embind's overload dispatch looks them up by name.
- **Arguments are structured-cloned before the call.** It runs every getter in JavaScript,
  keeps NaN and the infinities (which the library must see to refuse), and costs one clone
  of a few small objects per call. A side effect: an argument whose fields live on its
  prototype (a class with getters) arrives without them and is refused as missing. Plain
  objects, which is what `types.ts` describes, are unaffected.
- **WebAssembly exception handling, not Emscripten's JavaScript-based kind.** 31,650 bytes
  against 79,115, and native unwinding rather than a JavaScript wrapper around every call
  that might throw. Both pass the smoke test. Emscripten 6.0.13 emits the legacy form of the
  proposal by default (`WASM_LEGACY_EXCEPTIONS`), the form supported longest; no browser was
  run here (Not done).
- **An American option is an `exercise: 'american'` field**, which the grid's entry points
  accept and every other entry point refuses with a `TypeError`: the library refuses it at
  compile time, and a field ignored there would price the wrong contract. `types.ts` has no
  such field; L5 adds it if D8 or D10 shows the American contract.
- **`bumpGreeks` over the Monte Carlo uses the same seed at every bumped point**: common
  random numbers, which `monte_carlo` with one `settings` gives by itself. Without them a
  bumped difference is mostly sampling noise.
- **Bound: what the interface and D7, D8, D10 need, and no more.** Newton–Brent
  (`implied_vol`), the per-path Monte Carlo functions and the individual closed-form
  accessors are not bound; `priceAndGreeks` and the 2.11 solver cover every demo the roadmap
  lists. Adding one later is a library milestone, because the site cannot (I18).
- **Two parity differences from the TypeScript that L5 will meet**, both the library's
  behaviour rather than the binding's: `noArbitrageBounds` validates its inputs and refuses
  an invalid option with a `RangeError` where the TypeScript returns numbers; and a refused
  implied-vol price gives σ = 0 or +∞ (work order).
- **The release is published, not drafted**, when the tag is pushed: the owner pushing the
  tag is the decision to publish. Its assets are the four files of Done 6.
- **Node in the library's CI** runs the smoke test only, with Node's own test runner and no
  package: the roadmap's exit names Node, and nothing is installed from npm. No new
  dependency in the library, its tests or the artifact.
- **The budget is read strictly**: both files, uncompressed, against 500,000 bytes.

**Not done**

- **The release has not run.** `release.yml`'s build half is `wasm.yml`, which CI runs on
  every push; its release job (the tag check, whose `sed` was run locally against
  `CMakeLists.txt` and gave 0.4.0; the download; `gh release create`) runs for the first
  time on the owner's tag. Linting the workflows with `actionlint` was declined by the
  session's permissions; the three files parse as YAML, and GitHub accepted `ci.yml`'s call
  of `wasm.yml`.
- **No browser loaded the artifact.** Node only, here and in CI; the browser is L5's, which
  has the site to load it in. ENVIRONMENT includes `web` and `worker`.
- **No timing.** Ruling 7 leaves performance to T5; nothing here claims a speed in WebAssembly.
- **The site was not touched** (I18). For L5: `types.ts` says a refused price gives NaN and
  that the library has no path API (F9); F8 is still the site's; an American option needs
  the `exercise` field above; and `golden/paths-known-answers.json` is now reproduced to
  the bit by the module itself.
- **MSVC in CI** (F7's other half) remains out of scope.

**Exact next step**

The owner reads this pack and merges `m/T4` into `main`; then, once `main`'s CI is green,
pushes the tag that runs the release (P4: the session does not):

```bash
git checkout main
git pull --ff-only origin main
git log -1 --format='%h %s'            # the merge of m/T4
gh run list --branch main --limit 1    # CI on that commit: completed, success
git tag -a v0.4.0 -m "Touchstone 0.4.0: the WebAssembly artifact"
git push origin v0.4.0
gh run watch "$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
gh release view v0.4.0                 # four assets: touchstone.mjs, touchstone.wasm, size.txt, SHA256SUMS
```

If the release run fails, delete the tag (`git push origin :refs/tags/v0.4.0`, then
`git tag -d v0.4.0`), fix on a branch, and tag again after the merge. T5 then unlocks.

## Amendments

**None proposed.** Node runs the smoke test because the roadmap's exit names it; it is in the
programme's stack already (I19, the site's) and adds no package. Emscripten is in I19.

## Owner actions

1. **Read this pack and merge `m/T4`.** T4's tollgate is V.
2. **Push `v0.4.0`** with the commands above, and tick T4 once the release exists.
3. **Rule, if you disagree, on returning errors rather than throwing them across the
   boundary** (Decisions). It is the one design here the evidence forced rather than chose.

## What is in this pack

- `summary.md` — this file.
- `build.txt` — the toolchain and why that version, how the artifact is built, its size both
  ways and the JavaScript-EH comparison, the native build.
- `tests.txt` — the smoke test's whole output, the two ways the module dies and the probes
  that measured them, the native suite, CI.
- `diff.txt` — `git diff --stat` against `1a9b465`.
- No `screenshots/`: T4 has no UI.
