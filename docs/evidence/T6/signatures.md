# T6 — proposed signatures, for the owner's ruling

2026-11-19 · claude-opus-5-5 · at `fbf90f9` on `m/T6`. Nothing below is built. The brief
(`docs/briefs/T6-browser-build-needs.md`, "The session proposes the signatures, and stops")
asks for the C++ and the JavaScript signature of each need with one line of reasoning each.
The choices that need a ruling are collected as a numbered list at the end. Each one carries
a recommendation and the alternative.

Conventions kept from `v1.0.0`: the JavaScript shapes follow the binding's existing ones
(camelCase fields, `'call'`/`'put'`, `'exact'`/`'euler'`, partial settings filled from the
library's defaults). Arrays arrive as `ArrayLike<number>` (a `Float64Array` or a plain array)
and leave as `Float64Array` copies. A refusal by the library arrives as a `RangeError` and an
argument of the wrong shape as a `TypeError`. Nothing `v1.0.0` exports changes its signature
or its numbers.

---

## 1 · The payoff

**C++** (`contract.hpp`, beside the scalar `payoff`, which is unchanged):

```cpp
/// `payoff(option, s)` at each spot, in order.
template <Exercise E>
[[nodiscard]] std::vector<double> payoff(const Vanilla<E>& option, std::span<const double> spots);
```

*Why:* it loops over the one payoff definition, so the loop is a library function with its own
test and the binding has no loop of its own. It throws nothing, because the scalar refuses nothing.

**JavaScript:**

```ts
payoff(option: { strike: number; type: 'call' | 'put' }, spots: ArrayLike<number>): Float64Array
```

*Why an array and not one call a point:* every caller on the site draws many points. D6
draws its curve at a plot's width of spots, D11 draws every leg at those spots, and D5 takes
one payoff for each of its paths. Each crossing costs microseconds, because of the structured
clone and the object reads (`priceAndGreeks` is 8.43 µs a call in the brief's timing), and
hundreds of crossings a redraw is the cost need 4 exists to remove. `chart.curve` calls a
function once a pixel, so at L5 D6 and D11 sample the plot's spots into an array first. They
have to do that for need 4's prices anyway. *Why only strike and type:* the payoff depends on
nothing else, and a leg on D11's diagram has no expiry. Making the caller supply an expiry or
an exercise style the function never reads would be the trap `QuotedMarket` exists to avoid.
The binding calls the library with a European vanilla of that strike, that direction and an
expiry of zero. The exercise style does not enter the payoff.

## 2 · N(x) and the normal density

**C++:** none. `norm_cdf` and `norm_pdf` (`normal.hpp`) as they are.

**JavaScript:**

```ts
normCdf(x: number): number
normPdf(x: number): number
```

*Why one call a point:* the site calls these at most a few hundred times per redraw (D4 needs
two values a histogram bin) and 481 times once (page 0.3's figure, at build time). At a few
microseconds a call, that is under a millisecond a redraw. A scalar export needs no new library
function and no new native test. An array form would need both, and nothing measured calls
for it. A NaN argument returns NaN, as the library's function and the site's TypeScript both
do (ruling 4).

## 3 · A sample of paths

**C++** (`paths.hpp`):

```cpp
/// The grid a sample is stepped on when the caller supplies the normals: a
/// horizon and a step count. No seed, because nothing is drawn.
struct StepGrid {
    double horizon{1.0};     ///< T: each path runs over [0, T].
    std::size_t steps{1};    ///< Steps per path; dt = T / steps.
};

/// Throws `std::invalid_argument` unless: `steps >= 1`; the horizon is finite
/// and positive; `normals.size()` is a multiple of `steps`; every normal is
/// finite; the process is valid as `require_valid(PathGrid, GbmDynamics, steps + 1)`
/// requires; and `values == (normals.size() / steps) * (steps + 1)`.
void require_valid(const StepGrid& grid,
                   const GbmDynamics& dynamics,
                   std::span<const double> normals,
                   std::size_t values);

/// A sample of paths of S. Path p is S stepped under `scheme` from S_0 by
/// normals [p*steps, (p+1)*steps) and written to paths [p*(steps+1), (p+1)*(steps+1)),
/// as `gbm_path` writes one path.
void gbm_paths(const StepGrid& grid,
               const GbmDynamics& dynamics,
               Scheme scheme,
               std::span<const double> normals,
               std::span<double> paths);
```

*Why:* this is the brief's suggestion, and it meets all four requirements.

- **Path `p` takes the `p`-th run of normals.** That is how the function is defined. Path 0
  of `normals(seed, P·steps)` is `gbm_path`'s path at that seed, because both go through
  `detail::walk` with the same `GbmStep`. The native test holds the two exactly equal and the
  fixture holds them to its stated tolerance.
- **Both schemes from the same normals.** The caller makes two calls with one array.
- **The recorded-increments test.** `tests/d4-experiment.test.ts` passes its z (the
  experiment's increments over √dt, as it computes them now) to `gbmPaths`. That holds the
  library itself to the numpy experiment's paths, which is stronger than holding the site's
  copy of the arithmetic to them.
- **Not one crossing a step.** A sample by seed is `gbmPaths(spec, normals(seed, P·steps))`:
  two crossings whatever its size.

The finiteness check on the normals is what keeps "an accepted input never produces a NaN"
true. With a volatility of zero, an infinite normal would make the step's exponent
`0 · ∞`. `gbm_path` and the new function share their per-path loop in `detail`, so the step
is written once. No Brownian sample is proposed, because nothing on the site needs one. The
`σ·Z·dt` teaching device stays in the demo layer, as the brief says.

**JavaScript:**

```ts
gbmPaths(
  spec: { horizon: number; steps: number; spot: number; drift: number; vol: number; scheme: 'exact' | 'euler' },
  normals: ArrayLike<number>,
): Float64Array   // length (normals.length / steps) * (steps + 1), path-major
```

*Why flat:* the caller knows `steps`, so path `p` is
`subarray(p*(steps+1), (p+1)*(steps+1))`, the same slicing `sampleNormals` already does.
The spec is `gbmPath`'s without the seed. A `seed` field is refused with a `TypeError` that
says the normals are drawn by `normals(seed, n)` (ruling 6).

**Known answers:** `golden/generate_paths.py` gains a sample section: for a stated seed, path
count and step count, both schemes, every value of every path stepped from
`normals(seed, P·steps)`, written by the same independent transcription. Its path 0 is the
existing `gbm` entry at that seed.

## 4 · The closed form at many points

**C++** (`black_scholes.hpp`):

```cpp
/// What a sweep of the closed form holds fixed: the contract's strike and
/// direction, and the market's volatility, rate and dividend yield. The spot and
/// the time to expiry are the sweep's coordinates, so they are not fields here.
/// A field that the function overrode would be a trap, for the same reason
/// `QuotedMarket` has no volatility.
struct ClosedFormSweep {
    double strike{};
    OptionType type{OptionType::Call};
    double vol{};
    double rate{};
    double dividend_yield{};
};

/// The seven outputs, one array each, in the points' order.
struct PriceAndGreeksColumns {
    std::vector<double> price;
    std::vector<double> delta;
    std::vector<double> gamma;
    std::vector<double> vega;
    std::vector<double> theta;
    std::vector<double> rho;
    std::vector<double> dividend_rho;
};

/// Throws `std::invalid_argument` unless the two spans have the same length and
/// each point (spots[i], times_to_expiry[i]), with `sweep`, is in the domain of
/// `require_valid(EuropeanVanilla, BlackScholesMarket)`. The message names the
/// first point refused.
void require_valid(const ClosedFormSweep& sweep,
                   std::span<const double> spots,
                   std::span<const double> times_to_expiry);

/// The closed form at each point: the same `ClosedForm` as `price_and_greeks`,
/// built from `EuropeanVanilla{strike, times_to_expiry[i], type}` and
/// `BlackScholesMarket{spots[i], vol, rate, dividend_yield}`.
[[nodiscard]] PriceAndGreeksColumns price_and_greeks(const ClosedFormSweep& sweep,
                                                     std::span<const double> spots,
                                                     std::span<const double> times_to_expiry);
```

*Why:* the loop is the library's, and each point is the existing `ClosedForm`, so no formula
is written a second time. Every point is validated before any is computed, so a refusal
returns nothing for the whole call. *Why pairs and not a spot-by-time grid:* D5's points are
pairs (a path's value at a date and the time left), which a grid cannot express. D6's curve
is one time repeated, which pairs can express. *Why columns:* the binding then turns each
`std::vector` into a `Float64Array` the way it already turns `PdeSurface`'s, with no loop of
its own. *Why all seven:* five more outputs cost five more copies, and one shape is simpler
than a selector (ruling 7).

**JavaScript:**

```ts
priceAndGreeksAt(
  sweep: { strike: number; type: 'call' | 'put'; vol: number; rate: number; dividendYield: number },
  spots: ArrayLike<number>,
  timesToExpiry: ArrayLike<number>,
): { price: Float64Array; delta: Float64Array; gamma: Float64Array; vega: Float64Array;
     theta: Float64Array; rho: Float64Array; dividendRho: Float64Array }
```

*Why:* the field names are `priceAndGreeks`'s, with arrays in place of numbers. An
`exercise: 'american'` field is refused, as `priceAndGreeks` refuses it. The brief's budget
applies: if 200,000 points take more than 200 ms through the module, the build session stops
and returns, and a selector of outputs is the first thing it would propose.

## 5 · Newton, then Brent

**C++:** none. `implied_vol`, `ImpliedVolSettings` and `ImpliedVolResult` as they are.

**JavaScript:**

```ts
impliedVolNewtonBrent(
  option: { strike: number; expiryYears: number; type: 'call' | 'put'; exercise?: 'european' },
  market: { spot: number; rate: number; dividendYield: number }, price: number,
  settings?: { priceTolerance?: number; maxVol?: number; maxIterations?: number },
): { vol: number; priceResidual: number; vega: number; iterations: number;
     method: 'newton' | 'brent' | 'exact'; converged: boolean }
```

`defaults()` gains `impliedVolNewtonBrent: { priceTolerance: 1e-14, maxVol: 10, maxIterations: 64 }`.
A price `require_valid` refuses arrives as a `RangeError` carrying the library's message.

*Why this name:* `impliedVol` is the interface's name and belongs to the safeguarded solver.
Page 3.4 names the two solvers by their methods, so the export does too. The arguments are
`impliedVol`'s. The result is the library's `ImpliedVolResult`, field for field. It has no
`bounds`, because `noArbitrageBounds` gives them.

---

## For the owner's ruling

| # | Question | Proposed | Alternative |
|---|---|---|---|
| 1 | Payoff: one call a point, or many | Array only: `payoff(option, spots)` | Also a scalar `payoff(option, spot)` |
| 2 | Payoff: what the option object must carry | `strike` and `type` only | The full option object, with `expiryYears` required as elsewhere |
| 3 | N(x) and the density: one call a point, or many | Scalar only; no library change | Array forms, each a new library function and test |
| 4 | `normCdf(NaN)` | Returns NaN, as the library and the site's TypeScript do | The binding refuses NaN with a `RangeError`: a rule the library does not have, written in the binding only |
| 5 | Paths: by caller's normals, by seed, or both | By normals only (`gbm_paths` / `gbmPaths`); a sample by seed is `normals` then `gbmPaths` | Also a seeded form, one crossing instead of two, at the cost of one more function and test |
| 6 | `gbmPaths` given a `seed` field | Refused with a `TypeError` | Ignored, as the binding ignores unknown fields elsewhere |
| 7 | Closed form at many points: which outputs | All seven columns | Price and delta only; or a selector |
| 8 | Closed form at many points: the fixed inputs | A new `ClosedFormSweep` with no spot and no expiry | `EuropeanVanilla` and `BlackScholesMarket` with their expiry and spot overridden by the points |
| 9 | The second solver's JavaScript name | `impliedVolNewtonBrent` | `impliedVolDefault`, which is the library's word but not the page's |
| 10 | `defaults()` gains a key | Yes: its signature and every existing key's value are unchanged; the object it returns has one key more | A separate export for the new solver's defaults |
| 11 | Empty input (no spots, no normals) | An empty result, not a refusal | A refusal |

Ruling 10 is the one place an existing export returns something different from what it
returned at `v1.0.0`. The roadmap's exit says "nothing `v1.0.0` exports has changed its
signature or its numbers", and this change keeps both. It is listed because it is the
nearest thing to an exception.
