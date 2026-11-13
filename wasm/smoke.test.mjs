// The WebAssembly artifact, loaded in Node and held to the numbers the native
// suite is held to.
//
//   node --test wasm/smoke.test.mjs
//
// TOUCHSTONE_WASM names the built `touchstone.mjs`; the default is the build
// directory the README's commands create. Nothing here is a second
// implementation of anything: every expected value is read from a committed
// fixture, or is another entry point of the same module, or is a bound the
// library's own documentation states.

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const artifact = resolve(process.env.TOUCHSTONE_WASM ?? resolve(root, 'build-wasm/wasm/touchstone.mjs'))
const { default: createTouchstone } = await import(pathToFileURL(artifact).href)
const touchstone = await createTouchstone()

/** A committed JSON file. Python writes NaN as a bare token, which JSON has not got. */
const fixture = (path) =>
  JSON.parse(readFileSync(resolve(root, path), 'utf8').replace(/([:[,]\s*)NaN\b/g, '$1null'))

/** `golden/SCHEMA.md`'s comparison: absolute below 1, relative above. */
const scaledError = (actual, reference) => Math.abs(actual - reference) / Math.max(1, Math.abs(reference))

const rng = fixture('golden/rng-known-answers.json')
const golden = fixture('golden/bs_vanilla.json')
const paths = fixture('golden/paths-known-answers.json')
const experiment = fixture('experiments/2_11_where_it_breaks.json')

const greekFields = ['price', 'delta', 'gamma', 'vega', 'theta', 'rho', 'dividendRho']
const goldenField = { dividendRho: 'dividend_rho' }

const option = (row) => ({ strike: row.strike, expiryYears: row.expiry_years, type: row.type })
const market = (row) => ({ spot: row.spot, vol: row.vol, rate: row.rate, dividendYield: row.dividend_yield })

/** The one golden row the roadmap's criterion names, chosen by label so it reads as itself. */
const namedRow = golden.edge_cases.find((row) => row.label === 'one-day-atm')

const base = { strike: 100, expiryYears: 1, type: 'call' }
const baseMarket = { spot: 100, vol: 0.2, rate: 0.05, dividendYield: 0.02 }

/** Worst scaled error of the seven closed-form outputs on one golden row. */
const rowError = (row) => {
  const ours = touchstone.priceAndGreeks(option(row), market(row))
  return Math.max(...greekFields.map((field) => scaledError(ours[field], row[goldenField[field] ?? field])))
}

/** The RNG fixture, in full: uniforms to the bit, normals to `docs/rng.md` §6's 1e-12. */
const rngFixtureWorstNormal = () => {
  let worst = 0
  for (const vector of rng.vectors) {
    assert.deepEqual(Array.from(touchstone.uniforms(vector.seed, rng.count)), vector.uniforms,
      `uniforms, seed ${vector.seed}`)
    const normals = touchstone.normals(vector.seed, rng.count)
    vector.normals.forEach((z, i) => { worst = Math.max(worst, Math.abs(normals[i] - z)) })
  }
  return worst
}

test("the module says which version of the library it is: the project's", () => {
  const project = readFileSync(resolve(root, 'CMakeLists.txt'), 'utf8').match(/project\(touchstone\s+VERSION\s+([0-9.]+)/)
  assert.ok(project, 'CMakeLists.txt states a project version')
  assert.equal(touchstone.version, project[1])
})

test('the RNG fixture: uniforms to the bit, normals to 1e-12', () => {
  const worst = rngFixtureWorstNormal()
  assert.ok(worst <= 1e-12, `worst normal difference ${worst}`)
  console.log(`# rng: ${rng.vectors.length} seeds x ${rng.count}; uniforms exact; worst normal difference ${worst}`)
})

test('one golden price, and its Greeks, to the file\'s own tolerance', () => {
  const error = rowError(namedRow)
  assert.ok(error <= golden.tolerances.edge_cases, `worst scaled error ${error}`)
  console.log(`# golden '${namedRow.label}': price ${touchstone.priceAndGreeks(option(namedRow), market(namedRow)).price}` +
    ` against ${namedRow.price}; worst of seven ${error}`)
})

test('every golden row, to the file\'s own tolerances', () => {
  for (const [block, tolerance] of [['cases', golden.tolerances.cases], ['edge_cases', golden.tolerances.edge_cases]]) {
    let worst = 0
    for (const row of golden[block]) worst = Math.max(worst, rowError(row))
    assert.ok(worst <= tolerance, `${block}: worst scaled error ${worst} against ${tolerance}`)
    console.log(`# golden ${block}: ${golden[block].length} rows, worst scaled error ${worst} (tolerance ${tolerance})`)
  }
})

test('the path fixture, Brownian and GBM, to its own tolerance', () => {
  let worst = 0
  const compare = (ours, reference) => {
    assert.equal(ours.length, reference.length)
    reference.forEach((value, i) => { worst = Math.max(worst, scaledError(ours[i], value)) })
  }
  for (const p of paths.brownian) compare(touchstone.brownianPath(p), p.path)
  for (const p of paths.gbm) compare(touchstone.gbmPath(p), p.path)
  assert.ok(worst <= paths.tolerance.value, `worst ${worst}`)
  console.log(`# paths: ${paths.brownian.length} Brownian, ${paths.gbm.length} GBM; worst scaled difference ${worst}`)
})

test('page 2.11\'s committed trace, iterate by iterate', () => {
  const p = experiment.params
  const committed = experiment.results.solver.base_case
  const target = experiment.results.d9.quotes['price_at_100_vol_0.40']
  const result = touchstone.impliedVol({ strike: p.K, expiryYears: p.T, type: 'call' },
    { spot: p.S0, rate: p.r, dividendYield: p.q }, target, { trace: true })

  assert.equal(result.status, committed.status)
  assert.equal(result.iterations, committed.iterations)
  assert.equal(result.bisections, committed.bisections)
  assert.equal(result.trace.length, committed.trace.length)
  let worst = 0
  committed.trace.forEach((step, i) => {
    const ours = result.trace[i]
    assert.equal(ours.iteration, step.iteration)
    worst = Math.max(worst, Math.abs(ours.vol - step.sigma), scaledError(ours.price, step.price),
      scaledError(ours.priceError, step.price_error))
  })
  assert.ok(worst <= 1e-12, `worst ${worst}`)
  assert.ok(scaledError(result.bounds.lower, committed.lower_bound) <= 1e-12)
  assert.equal(result.bounds.upper, committed.upper_bound)
  console.log(`# 2.11 trace: ${result.trace.length} iterates, worst difference ${worst}`)
})

test('page 2.11\'s refusals come back with their status and no NaN', () => {
  const p = experiment.params
  const contract = { strike: p.K, expiryYears: p.T, type: 'call' }
  const quoted = { spot: p.S0, rate: p.r, dividendYield: p.q }
  for (const [key, committed] of Object.entries(experiment.results.solver.bounds_base_case.refusals)) {
    const result = touchstone.impliedVol(contract, quoted, Number(key.slice('price_'.length)))
    assert.equal(result.status, committed.status, key)
    assert.ok(!Number.isNaN(result.vol) && !Number.isNaN(result.priceResidual) && !Number.isNaN(result.vega), key)
    if (result.status === 'below_lower_bound') assert.equal(result.vol, 0)
    if (result.status === 'above_upper_bound') assert.equal(result.vol, Infinity)
  }
  assert.equal(touchstone.impliedVol(contract, quoted, 10).trace, undefined, 'no trace unless asked')
})

test('no-arbitrage bounds are the price at zero volatility and its limit at infinity', () => {
  const quoted = { spot: baseMarket.spot, rate: baseMarket.rate, dividendYield: baseMarket.dividendYield }
  const bounds = touchstone.noArbitrageBounds(base, quoted)
  assert.equal(bounds.lower, touchstone.priceAndGreeks(base, { ...baseMarket, vol: 0 }).price)
  assert.equal(bounds.upper, baseMarket.spot * Math.exp(-baseMarket.dividendYield * base.expiryYears))
})

test('Monte Carlo: within three standard errors of the closed form, and the same from the same seed', () => {
  const exact = touchstone.priceAndGreeks(base, baseMarket)
  for (const settings of [{}, { scheme: 'euler', steps: 64, paths: 8192, antithetic: true }]) {
    const mc = touchstone.monteCarlo(base, baseMarket, settings)
    assert.ok(Math.abs(mc.price - exact.price) <= 3 * mc.priceStandardError, JSON.stringify(mc))
    assert.ok(Math.abs(mc.delta - exact.delta) <= 3 * mc.deltaStandardError, JSON.stringify(mc))
    assert.deepEqual(touchstone.monteCarlo(base, baseMarket, settings), mc)
  }
  assert.deepEqual(touchstone.monteCarlo(base, baseMarket), touchstone.monteCarlo(base, baseMarket, touchstone.defaults().monteCarlo))
})

test('the grid: European at the closed form, American above it, both at the payoff\'s floor', () => {
  const put = { ...base, type: 'put' }
  const exact = touchstone.priceAndGreeks(put, baseMarket)
  const european = touchstone.crankNicolson(put, baseMarket)
  const american = touchstone.crankNicolson({ ...put, exercise: 'american' }, baseMarket)
  assert.ok(scaledError(european.price, exact.price) <= 1e-4, `${european.price} against ${exact.price}`)
  assert.ok(american.price > european.price)
  assert.ok(american.price >= put.strike - baseMarket.spot)
})

test('the grid\'s surface: every level read, today\'s the price', () => {
  const settings = { spaceIntervals: 128, timeSteps: 40 }
  const surface = touchstone.crankNicolsonSurface(base, baseMarket, settings, { everySteps: 8 })
  const price = touchstone.crankNicolson(base, baseMarket, settings)
  assert.equal(surface.logSpots.length, surface.nodes)
  assert.equal(surface.timesToExpiry.length, surface.levels)
  assert.equal(surface.values.length, surface.levels * surface.nodes)
  assert.equal(surface.levels, 1 + 40 / 8)
  assert.equal(surface.timesToExpiry[0], 0)
  assert.equal(surface.logSpots[surface.result.spotIndex], Math.log(baseMarket.spot))
  assert.equal(surface.values[(surface.levels - 1) * surface.nodes + surface.result.spotIndex], price.price)
  assert.deepEqual(surface.result, price)

  // A stride that does not divide the steps still ends on today.
  const uneven = touchstone.crankNicolsonSurface(base, baseMarket, settings, { everySteps: 7 })
  assert.equal(uneven.levels, 1 + Math.floor(40 / 7) + 1)
  assert.equal(uneven.timesToExpiry[uneven.levels - 1], surface.timesToExpiry[surface.levels - 1])
  assert.equal(uneven.values[(uneven.levels - 1) * uneven.nodes + uneven.result.spotIndex], price.price)
})

test('bump Greeks over each pricer', () => {
  const analytic = touchstone.priceAndGreeks(base, baseMarket)
  const closed = touchstone.bumpGreeks(base, baseMarket)
  for (const field of greekFields) {
    assert.ok(scaledError(closed[field], analytic[field]) <= 1e-6, `${field}: ${closed[field]} against ${analytic[field]}`)
  }
  const grid = touchstone.bumpGreeks(base, baseMarket, {}, { method: 'crankNicolson', settings: { spaceIntervals: 256, timeSteps: 128 } })
  assert.ok(scaledError(grid.delta, analytic.delta) <= 1e-3, `grid delta ${grid.delta}`)
  const americanPut = touchstone.bumpGreeks({ ...base, type: 'put', exercise: 'american' }, baseMarket, {},
    { method: 'crankNicolson', settings: { spaceIntervals: 256, timeSteps: 128 } })
  assert.ok(americanPut.delta < 0 && americanPut.delta > -1, `American put delta ${americanPut.delta}`)
  const paths = touchstone.bumpGreeks(base, baseMarket, { spotRelative: 1e-2 }, { method: 'monteCarlo' })
  assert.ok(Math.abs(paths.delta - analytic.delta) <= 0.05, `Monte Carlo delta ${paths.delta}`)
})

test('the library\'s defaults are the module\'s', () => {
  const defaults = touchstone.defaults()
  assert.deepEqual(Object.keys(defaults).sort(), ['bumpSizes', 'crankNicolson', 'impliedVol', 'monteCarlo'])
  assert.equal(defaults.impliedVol.initialVol, experiment.params.solver.sigma0)
  assert.equal(defaults.impliedVol.maxIterations, experiment.params.solver.max_iter)
})

// --- Refusals ---------------------------------------------------------------

/** `call()` must throw an instance of `Kind` whose message contains `words`. */
const refuses = (call, Kind, words) =>
  assert.throws(call, (error) => error instanceof Kind && error.message.includes(words))

test('an input the library rejects is a RangeError with the library\'s reason', () => {
  refuses(() => touchstone.priceAndGreeks({ ...base, strike: -1 }, baseMarket), RangeError, 'strike')
  refuses(() => touchstone.priceAndGreeks(base, { ...baseMarket, vol: NaN }), RangeError, 'vol')
  refuses(() => touchstone.priceAndGreeks(base, { ...baseMarket, rate: Infinity }), RangeError, '')
  refuses(() => touchstone.impliedVol(base, baseMarket, NaN), RangeError, '')
  refuses(() => touchstone.monteCarlo(base, baseMarket, { paths: 0 }), RangeError, '')
  refuses(() => touchstone.crankNicolson(base, { ...baseMarket, spot: 0 }), RangeError, '')
  refuses(() => touchstone.gbmPath({ seed: 1, steps: 0, horizon: 1, spot: 1, drift: 0, vol: 0.2, scheme: 'exact' }), RangeError, '')
  refuses(() => touchstone.uniforms(-1, 3), RangeError, 'seed')
  refuses(() => touchstone.uniforms(1.5, 3), RangeError, 'seed')
  refuses(() => touchstone.normals(1, 2 ** 32), RangeError, 'n')
})

test('an argument of the wrong shape is a TypeError naming the field', () => {
  refuses(() => touchstone.priceAndGreeks(null, baseMarket), TypeError, 'option must be an object')
  refuses(() => touchstone.priceAndGreeks({ ...base, type: 'straddle' }, baseMarket), TypeError, 'option.type')
  refuses(() => touchstone.priceAndGreeks(base, { ...baseMarket, vol: '0.2' }), TypeError, 'market.vol')
  refuses(() => touchstone.priceAndGreeks({ strike: 100, type: 'call' }, baseMarket), TypeError, 'option.expiryYears is required')
  refuses(() => touchstone.monteCarlo({ ...base, exercise: 'american' }, baseMarket), TypeError, 'European')
  refuses(() => touchstone.bumpGreeks(base, baseMarket, {}, { method: 'lattice' }), TypeError, 'pricer.method')
})

test('a thrown getter on an argument reaches the caller as itself', () => {
  const sentinel = new SyntaxError('from the getter')
  const hostile = { get strike () { throw sentinel }, expiryYears: 1, type: 'call' }
  assert.throws(() => touchstone.priceAndGreeks(hostile, baseMarket), (error) => error === sentinel)
})

test('the module survives a hundred thousand refusals of each kind, and then still agrees with the fixtures', () => {
  const before = touchstone.priceAndGreeks(option(namedRow), market(namedRow))
  const kinds = [
    () => touchstone.priceAndGreeks({ ...base, strike: -1 }, baseMarket),
    () => touchstone.priceAndGreeks({ ...base, type: 'straddle' }, baseMarket),
    () => touchstone.priceAndGreeks({ get strike () { throw new Error('getter') }, expiryYears: 1, type: 'call' }, baseMarket),
  ]
  const rounds = 100_000
  for (const kind of kinds) {
    let refused = 0
    for (let i = 0; i < rounds; i++) {
      try { kind() } catch { refused++ }
    }
    assert.equal(refused, rounds)
  }
  assert.deepEqual(touchstone.priceAndGreeks(option(namedRow), market(namedRow)), before)
  assert.ok(rngFixtureWorstNormal() <= 1e-12)
  // The largest single allocation in the smoke test, after all of that.
  const surface = touchstone.crankNicolsonSurface(base, baseMarket)
  assert.equal(surface.values.length, surface.levels * surface.nodes)
  console.log(`# survived ${kinds.length} x ${rounds} refusals; the named golden row and the RNG fixture unchanged;` +
    ` then a ${surface.levels} x ${surface.nodes} surface`)
})
