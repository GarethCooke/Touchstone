# T6 — what the demos need from the browser build (2026-11-19)

The owner's ruling of 2026-11-19 and what it rests on. T6's work order derives from its ROADMAP
entry and this note. Where the two disagree the ROADMAP entry wins, and the disagreement is a
defect to report. File and line references are at `touchstone` `2a05686`, whose library is
1.0.0's, and `touchstone-learn` `cade59a`.

## Why T6 exists

L5 moves every demo onto the library's WebAssembly build and then removes the site's
TypeScript numerics (constitution I15, as amended by A6). L5 cannot edit this repository
(I18). T4's binding was written to carry everything L5 would need. A reading of every file in
`touchstone-learn` that imports the TypeScript numerics, and a run of the `v1.0.0` release in
Node, found that it does not. The site uses the things below, and the build gives it none of
them.

## The ruling

Put to the owner on the rulings page "L5 entry rulings" as the item `library-release`. He chose
A, which read:

> One library session before L5's first: Opus in Touchstone, a new milestone in the roadmap
> (your edit; I give you the paste), released as v1.1.0. It exports the payoff, N(x) and the
> density; adds a function that returns many paths from one seed; adds a closed-form entry that
> takes arrays of spot and time, for D5; and exports the Newton–Brent solver. The session
> proposes the exact signatures and you rule on them, as at T3a. L5 then vendors v1.1.0, every
> demo runs on the library, and the index's sentence "From L5 every demo runs on the WASM build
> of the library" is true as written, D11 included. ARCHITECTURE.md changes, so the portfolio's
> Touchstone write-up is refreshed afterwards.

## Standing rules

T3a's stand (`docs/briefs/T3a-design-rulings.md`), and are repeated because they decide this
work:

- **No repeated code.** A formula, a rule or a list is written once, in the tests as in the
  library. Each need below already has its arithmetic in the library; T6 exposes it and writes
  none of it again.
- **The binding translates and does no arithmetic.** Where a need is a loop over many points
  or many paths, the loop is a library function with its own test, and the binding calls it.
  `crank_nicolson_surface` joined the library at T4 for this reason.
- **Comments give the reasoning, not the history.** No milestone, review or governance id in a
  comment. The history goes in `ARCHITECTURE.md` §10.
- The library's own rules (`ARCHITECTURE.md` §6): validate, then compute; an accepted input
  never produces a NaN; each product formed once, through `detail/scales.hpp`; the same seed
  gives the same result; no dependency in the library; nothing thrown across the WebAssembly
  boundary.
- **Measure first** (T3a's ruling 7: "No fast path until a number calls for one"). Need 4 is
  the number that calls for one. T6 reports what it measures and tunes nothing else.

## The session proposes the signatures, and stops

Before any of it is built, the session writes its proposed signatures, the C++ one and the
JavaScript one for each need, with one line of reasoning each, and stops for the owner's
ruling. He rules on the list. Nothing below fixes a name or a shape. Where this note makes a
suggestion it says so, and the session may propose otherwise with its reason.

## The needs

### 1 · The payoff of one option

- **In the library:** `payoff(const Vanilla<E>&, double spot)`, `include/touchstone/contract.hpp:84`.
  It accepts either exercise style and a negative spot.
- **In the build:** not exported.
- **On the site:** `intrinsic()` in `src/demos/blackScholes.ts`, called from `D6BlackScholes.tsx`
  (the payoff curve under the price), `payoff.ts` (D11: every leg of a position), `experiments/hedging.ts`
  (D5: once a path) and `src/data/part-0-figures.ts` (the payoff figure on page 0.2).
- **Needed:** the library's payoff, callable from JavaScript. D6 and D11 draw it along a curve
  of some hundreds of spots at each redraw; the session says whether one call a point is
  enough or whether need 4's entry should carry it.

### 2 · N(x) and the normal density

- **In the library:** `norm_cdf` and `norm_pdf`, `include/touchstone/normal.hpp:28` and `:14`.
- **In the build:** not exported.
- **On the site:** `normCdf` in `experiments/euler.ts` (`lognormalShares`, the exact lognormal
  curve D4 draws over its histogram: two values a bin); `normPdf` in `kurtosis.ts` (the
  kurtosis figure on page 0.3: 481 points).
- **Needed:** both, callable from JavaScript. `norm_inv` is not needed: the site reaches it
  only through `normals`.

### 3 · A sample of paths

- **In the library:** `gbm_path` writes one path a seed (`include/touchstone/paths.hpp:84`).
  `detail::PathGenerator` already grows a path through normals it is handed
  (`include/touchstone/detail/path_generator.hpp`, `grow`). No public function returns more than
  one path, or steps a path from normals the caller supplies.
- **In the build:** `gbmPath`, one path a call.
- **On the site:** no sample calls `gbmPath`. `stepPath` in `experiments/euler.ts` steps a path
  from its normals in TypeScript, exact and Euler: the library's two steps written a second
  time. Its callers:
  - `terminalDistribution` and `eulerConvergence` (D4) and `hedgeSample`, `hedgeFirstPaths`
    and `hedgeExperiment` (D5). Each draws `backend.normals(seed, paths * steps)` once, and
    path `p` takes the `p`-th run of `steps` normals (`sampleNormals`). Path 0 is therefore
    the path `gbmPath` draws from that seed. `seed + p` would not do: seed 2's paths would be
    seed 1's shifted by one, and a seed box that moves one path in two thousand looks broken.
  - `eulerConvergence` steps both schemes from the same normals on every path.
  - `tests/d4-experiment.test.ts` steps normals that did not come from the site's generator:
    the increments recorded in page 2.6's numpy experiment, to show the site's stepping
    reproduces the experiment's paths.
  - `misscaledPath`, the `σ·Z·dt` bug, is a teaching device and stays in the demo layer, built
    from `normals` (I15's last sentence). It is not T6's.
- **Sizes:** D4 runs up to 2,000 paths and budgets 400,000 normals a sample
  (`distributionPaths`); D5 budgets 200,000 hedge steps (`samplePaths`). A sample is redrawn
  at every move of a slider.
- **Needed:** the library steps every path the site draws, exact and Euler, such that
  - path `p` of a sample is driven by the `p`-th run of `steps` normals of one stream, and
    path 0 equals `gbm_path`'s at that seed, to the tolerance
    `golden/paths-known-answers.json` states;
  - both schemes can be driven by the same normals;
  - the recorded-increments test above can still be held, or the proposal says what holds it
    instead;
  - a sample does not cost one crossing of the boundary a step.
- **Suggestion, not a ruling:** a public function that steps many paths from normals the
  caller supplies answers all four, and a sample by seed is then `normals` and that function.
  A function that takes a seed and a path count answers the first, second and fourth only.
- **Known answers:** `golden/generate_paths.py` and its fixture are extended for whatever is
  added, by the same independent transcription, and the site takes the fixture at L5.

### 4 · The closed form at many points

- **In the library:** `price_and_greeks` and `delta` (`include/touchstone/black_scholes.hpp:96`,
  `:100`), one point a call. `ClosedFormQuote` holds what does not depend on the volatility.
- **In the build:** `priceAndGreeks`, one point a call, two objects in and one out.
- **On the site:** `experiments/hedging.ts` calls `delta` and `price` from `blackScholes.ts`
  directly: `hedgeOnePath` takes a delta at every rebalance date of every path, at that date's
  spot and the time left; `runningHolderPnl` takes a price and a delta at every date of one
  path. D6 takes a price at each spot of its curve.
- **The number.** Timed on 2026-11-19 in the cloud container, Node 22.23.5, vitest, the
  `v1.0.0` release: `delta` in TypeScript 0.246 µs a call; the build's
  `priceAndGreeks(...).delta` 8.43 µs a call. D5's live sample of 200,000 hedge steps took 48 ms
  on the TypeScript numerics (`hedgeSample`, N = 256, 781 paths); 200,000 calls through the
  build took 1,685 ms. Shared hardware, one run, not a browser. Indicative, and the ratio is
  the finding.
- **Needed:** one call that evaluates the closed form at many (spot, time to expiry) pairs
  with the strike, the direction, the volatility, the rate and the dividend yield fixed, and
  returns at least price and delta as arrays. Validation as for one point.
- **To report:** the cost of one point through the module in Node, on the session's machine,
  beside a rerun of the two figures above on that machine. If 200,000 points take more than
  200 ms, stop and return to the owner.

### 5 · Newton, then Brent

- **In the library:** `implied_vol` (`include/touchstone/implied_vol.hpp:164`), the default
  solver, with `ImpliedVolSettings` and a result that says which method finished.
- **In the build:** only `implied_vol_safeguarded`, under the interface's name `impliedVol`.
- **On the site:** nothing yet. Page 3.4 is about root finding and will print both solvers'
  numbers, held by a site test that runs the build.
- **Needed:** `implied_vol` callable from JavaScript under a name of its own, its settings
  optional and in `defaults()`, its refusal of a price outside the bounds arriving as the
  `RangeError` it is.

## What else T6 changes

- **`ARCHITECTURE.md`:** the status line and §1 (the version), §4's table, §5's paragraphs on
  the paths and the binding, a row in §10.1, a line in §11. §1's sentence that the tutorial's
  demos run on a TypeScript backend stays true until L5 and is not T6's to change. Every new
  claim is added to the claims list with the test or file that holds it, as T5 did
  (`docs/evidence/T5/claims.md`).
- **The README,** where it lists what the build exports.
- **`wasm/smoke.test.mjs`:** each new export called through the module and held to a number
  the native tests already hold.
- **The version:** 1.1.0 in `CMakeLists.txt`. The owner tags `v1.1.0` on the merged commit and
  `release.yml` publishes; the session pushes no tag.
- **Size:** reported with and without exception catching, against 500,000 bytes. `v1.0.0` is
  173,040.

## What T6 does not do

- Change the signature or the behaviour of anything `v1.0.0` exports. The site's
  `PricingBackend` is written against those seven names.
- Add a hedging simulation, a histogram or any other demo logic to the library. Those are
  teaching devices and are built in the demo layer from the backend's outputs.
- Touch `touchstone-learn` or the portfolio (I18).

## For L5 (not T6's to change)

- A refused price differs by design: the site's TypeScript `impliedVol` returns a volatility of
  NaN and the library's safeguarded solver returns zero or infinity with its status. L5's
  parity tests say so.
- `forwardValue` in `blackScholes.ts` needs nothing new: it is a call's price less a put's.
- Pages 0.2 and 0.3 draw static figures from the payoff and the density, so the site's build
  loads the module in Node as well as in the browser.
- The portfolio's write-up of this repository renders `ARCHITECTURE.md`; it is refreshed after
  T6 merges.

## What this note did not do

It read `wasm/binding.cpp`, the public headers, `ARCHITECTURE.md` and the site files named
above, and ran the `v1.0.0` release in Node. It did not read `src/`, the tests or the build
scripts, and it tried none of the changes. The timings are one run on shared hardware.
