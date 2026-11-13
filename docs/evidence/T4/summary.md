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
