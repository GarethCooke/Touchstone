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

/** One golden row reproduced on its own, chosen by label so it reads as itself. */
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
  assert.deepEqual(Object.keys(defaults).sort(),
    ['bumpSizes', 'crankNicolson', 'impliedVol', 'impliedVolNewtonBrent', 'monteCarlo', 'surfaceSampling'])
  assert.deepEqual(defaults.surfaceSampling, { everySteps: 1 })
  assert.equal(defaults.impliedVol.initialVol, experiment.params.solver.sigma0)
  assert.equal(defaults.impliedVol.maxIterations, experiment.params.solver.max_iter)
  assert.deepEqual(Object.keys(defaults.impliedVolNewtonBrent).sort(), ['maxIterations', 'maxVol', 'priceTolerance'])
})

// --- What the demos draw from: the payoff, N(x), a sample of paths, the closed
// form at many points, and the second solver ---------------------------------

test('the payoff at many spots, either direction, below zero included', () => {
  assert.deepEqual(Array.from(touchstone.payoff({ strike: 100, type: 'call' }, [80, 100, 120])), [0, 0, 20])
  assert.deepEqual(Array.from(touchstone.payoff({ strike: 100, type: 'put' }, new Float64Array([-5, 80, 120]))), [105, 20, 0])
  assert.ok(touchstone.payoff(base, [1]) instanceof Float64Array)
  assert.equal(touchstone.payoff({ strike: 100, type: 'put' }, []).length, 0)
})

test('N(x) and the density, at the native suite\'s reference values', () => {
  // tests/test_normal.cpp's correctly rounded references and its bound,
  // (4 + x^2) eps relative.
  const tolerance = (x) => (4 + x * x) * Number.EPSILON
  const relative = (actual, reference) => Math.abs(actual - reference) / Math.abs(reference)
  assert.equal(touchstone.normCdf(0), 0.5)
  for (const [x, n] of [[1, 0.8413447460685429], [-1, 0.15865525393145705], [1.96, 0.9750021048517795],
    [-3, 0.0013498980316300946], [-10, 7.619853024160526e-24], [-30, 4.906713927148187e-198]]) {
    assert.ok(relative(touchstone.normCdf(x), n) <= tolerance(x), `N(${x}) = ${touchstone.normCdf(x)}`)
  }
  for (const [x, phi] of [[0, 0.3989422804014326779399461], [1, 0.2419707245191433497978302]]) {
    assert.ok(relative(touchstone.normPdf(x), phi) <= 2 * Number.EPSILON, `phi(${x}) = ${touchstone.normPdf(x)}`)
  }
  assert.ok(Number.isNaN(touchstone.normCdf(NaN)) && Number.isNaN(touchstone.normPdf(NaN)))
})

test('a sample of paths: the fixture\'s samples, and path 0 is gbmPath\'s at the seed', () => {
  let worst = 0
  for (const sample of paths.samples) {
    const { seed, path_count: count, steps, horizon, spot, drift, vol, scheme } = sample
    const flat = touchstone.gbmPaths({ horizon, steps, spot, drift, vol, scheme }, touchstone.normals(seed, count * steps))
    assert.equal(flat.length, count * (steps + 1))
    sample.paths.forEach((reference, p) => {
      reference.forEach((value, k) => { worst = Math.max(worst, scaledError(flat[p * (steps + 1) + k], value)) })
    })
    assert.deepEqual(flat.subarray(0, steps + 1), touchstone.gbmPath({ seed, horizon, steps, spot, drift, vol, scheme }))
  }
  assert.ok(paths.samples.length > 0)
  assert.ok(worst <= paths.tolerance.value, `worst ${worst}`)
  console.log(`# samples: ${paths.samples.length}; worst scaled difference ${worst}`)
})

test('the closed form at many points is priceAndGreeks at each, over the golden file', () => {
  // The file's rows, grouped by what a sweep holds fixed, as the native suite
  // groups them, each point held to the one-point export to the bit.
  const sweeps = new Map()
  for (const row of [...golden.cases, ...golden.edge_cases]) {
    const key = [row.strike, row.type, row.vol, row.rate, row.dividend_yield].join()
    if (!sweeps.has(key)) sweeps.set(key, [])
    sweeps.get(key).push(row)
  }
  let points = 0
  for (const rows of sweeps.values()) {
    const { strike, type, vol, rate, dividend_yield: dividendYield } = rows[0]
    const columns = touchstone.priceAndGreeksAt({ strike, type, vol, rate, dividendYield },
      rows.map((row) => row.spot), new Float64Array(rows.map((row) => row.expiry_years)))
    rows.forEach((row, i) => {
      const one = touchstone.priceAndGreeks(option(row), market(row))
      for (const field of greekFields) assert.equal(columns[field][i], one[field], `${row.label ?? ''} ${field}`)
      points++
    })
  }
  assert.equal(points, golden.cases.length + golden.edge_cases.length)
  console.log(`# priceAndGreeksAt: ${sweeps.size} sweeps of ${points} points, each identical to priceAndGreeks`)
})

test('Newton then Brent: the price round trip over the golden file, and Brent alone', () => {
  // tests/test_implied_vol.cpp's exit criterion, through the module: every row
  // with a solution repriced inside 1e-8; the rest refused as a RangeError.
  let worst = 0
  let solved = 0
  let refused = 0
  const methods = { newton: 0, brent: 0, exact: 0 }
  for (const row of [...golden.cases, ...golden.edge_cases]) {
    const quoted = { spot: row.spot, rate: row.rate, dividendYield: row.dividend_yield }
    let found
    try {
      found = touchstone.impliedVolNewtonBrent(option(row), quoted, row.price)
    } catch (error) {
      assert.ok(error instanceof RangeError, error.message)
      refused++
      continue
    }
    assert.equal(found.converged, true)
    methods[found.method]++
    solved++
    worst = Math.max(worst, scaledError(touchstone.priceAndGreeks(option(row), { ...quoted, vol: found.vol }).price, row.price))
  }
  assert.ok(solved > 7000 && worst <= 1e-8, `${solved} solved, worst ${worst}`)

  // One Newton step allowed: Brent finishes, inside the same criterion.
  let fellBack = 0
  let rows = 0
  let worstBrent = 0
  for (let i = 0; i < golden.cases.length; i += 7) {
    const row = golden.cases[i]
    const quoted = { spot: row.spot, rate: row.rate, dividendYield: row.dividend_yield }
    let found
    try { found = touchstone.impliedVolNewtonBrent(option(row), quoted, row.price, { maxIterations: 1 }) } catch { continue }
    rows++
    if (found.method === 'brent') fellBack++
    worstBrent = Math.max(worstBrent, scaledError(touchstone.priceAndGreeks(option(row), { ...quoted, vol: found.vol }).price, row.price))
  }
  assert.ok(fellBack > rows * 0.9 && worstBrent <= 1e-8, `${fellBack} of ${rows} in Brent, worst ${worstBrent}`)
  console.log(`# impliedVolNewtonBrent: ${solved} rows solved (${refused} refused), worst scaled reprice ${worst};` +
    ` Newton ${methods.newton}, Brent ${methods.brent}, exact ${methods.exact};` +
    ` with one Newton step ${fellBack} of ${rows} in Brent, worst ${worstBrent}`)
})

// --- An array argument costs its own length -----------------------------------

test('a slice of a larger array is handed over as itself, and costs its own length', () => {
  // A demo hands one path's spots to the module as a subarray of a whole
  // sample. The clone that keeps a throwing getter out of the module copies a
  // view's whole buffer, so the view is first given a buffer of its own: what
  // reaches the clone is the slice's bytes and no more.
  const whole = touchstone.gbmPaths({ horizon: 1, steps: 255, spot: 100, drift: 0.05, vol: 0.2, scheme: 'exact' },
    touchstone.normals(1, 255 * 784))
  const third = whole.subarray(2 * 256, 3 * 256)
  const own = Float64Array.from(third)
  const sweep = { strike: 100, type: 'call', vol: 0.2, rate: 0.05, dividendYield: 0 }
  const times = new Float64Array(whole.length).fill(0.5)

  const cloned = []
  const clone = globalThis.structuredClone
  globalThis.structuredClone = (value) => {
    for (const argument of value) if (ArrayBuffer.isView(argument)) cloned.push(argument.buffer.byteLength)
    return clone(value)
  }
  let fromSlice
  try {
    fromSlice = touchstone.priceAndGreeksAt(sweep, third, times.subarray(0, 256))
  } finally {
    globalThis.structuredClone = clone
  }
  assert.deepEqual(cloned, [256 * 8, 256 * 8], 'each slice reached the clone in a buffer of its own length')
  assert.deepEqual(fromSlice, touchstone.priceAndGreeksAt(sweep, own, new Float64Array(256).fill(0.5)))
  assert.deepEqual(touchstone.payoff(base, third), touchstone.payoff(base, own))
  assert.equal(third.length, 256, 'the caller\'s view is untouched')
})

test('a getter on an array argument still throws before the module is entered', () => {
  const sentinel = new SyntaxError('from the getter')
  const view = new Float64Array(1024).subarray(10, 20)
  Object.defineProperty(view, 'byteLength', { get () { throw sentinel } })
  assert.throws(() => touchstone.payoff(base, view), (error) => error === sentinel)
  const proxied = new Proxy([1, 2, 3], { get () { throw sentinel } })
  assert.throws(() => touchstone.payoff(base, proxied), (error) => error === sentinel || error instanceof DOMException)
  assert.deepEqual(Array.from(touchstone.payoff(base, [90, 110])), [0, 10])
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
  refuses(() => touchstone.crankNicolsonSurface(base, baseMarket, {}, { everySteps: 0 }), RangeError, 'every_steps')
  refuses(() => touchstone.gbmPath({ seed: 1, steps: 0, horizon: 1, spot: 1, drift: 0, vol: 0.2, scheme: 'exact' }), RangeError, '')
  refuses(() => touchstone.uniforms(-1, 3), RangeError, 'seed')
  refuses(() => touchstone.uniforms(1.5, 3), RangeError, 'seed')
  refuses(() => touchstone.normals(1, 2 ** 32), RangeError, 'n')

  const sweep = { strike: 100, type: 'call', vol: 0.2, rate: 0.05, dividendYield: 0.02 }
  refuses(() => touchstone.priceAndGreeksAt(sweep, [90, 100, -1], [1, 1, 1]), RangeError, 'at point 2 ')
  refuses(() => touchstone.priceAndGreeksAt(sweep, [90, 100], [1]), RangeError, 'one time to expiry for each spot')
  refuses(() => touchstone.priceAndGreeksAt({ ...sweep, vol: -0.2 }, [90], [1]), RangeError, 'vol')
  const spec = { horizon: 1, steps: 4, spot: 100, drift: 0.05, vol: 0.2, scheme: 'exact' }
  refuses(() => touchstone.gbmPaths(spec, touchstone.normals(1, 7)), RangeError, 'whole number of runs')
  refuses(() => touchstone.gbmPaths({ ...spec, steps: 0 }, []), RangeError, 'at least one step')
  refuses(() => touchstone.gbmPaths({ ...spec, vol: 0 }, [0, 0, Infinity, 0]), RangeError, 'finite')
  refuses(() => touchstone.impliedVolNewtonBrent(base, baseMarket, 1000), RangeError, 'no finite volatility')
  refuses(() => touchstone.impliedVolNewtonBrent(base, baseMarket, NaN), RangeError, '')

  // No points, no normals: an empty result rather than a refusal.
  assert.deepEqual(touchstone.priceAndGreeksAt(sweep, [], []).price, new Float64Array(0))
  assert.equal(touchstone.gbmPaths(spec, []).length, 0)
})

test('an argument of the wrong shape is a TypeError naming the field', () => {
  refuses(() => touchstone.priceAndGreeks(null, baseMarket), TypeError, 'option must be an object')
  refuses(() => touchstone.priceAndGreeks({ ...base, type: 'straddle' }, baseMarket), TypeError, 'option.type')
  refuses(() => touchstone.priceAndGreeks(base, { ...baseMarket, vol: '0.2' }), TypeError, 'market.vol')
  refuses(() => touchstone.priceAndGreeks({ strike: 100, type: 'call' }, baseMarket), TypeError, 'option.expiryYears is required')
  refuses(() => touchstone.monteCarlo({ ...base, exercise: 'american' }, baseMarket), TypeError, 'European')
  refuses(() => touchstone.bumpGreeks(base, baseMarket, {}, { method: 'lattice' }), TypeError, 'pricer.method')

  refuses(() => touchstone.payoff(base, [1, '2']), TypeError, 'spots[1] must be a number')
  refuses(() => touchstone.payoff(base, [1, , 3]), TypeError, 'spots[1] must be a number')
  refuses(() => touchstone.payoff(base, [1, 2n]), TypeError, 'spots[1] must be a number')
  refuses(() => touchstone.payoff(base, new Float32Array(2)), TypeError, 'spots must be a Float64Array or an array of numbers')
  refuses(() => touchstone.payoff(base, 100), TypeError, 'spots must be')
  refuses(() => touchstone.payoff({ strike: 100 }, [1]), TypeError, 'option.type is required')
  refuses(() => touchstone.normCdf('1'), TypeError, 'x must be a number')
  const spec = { horizon: 1, steps: 4, spot: 100, drift: 0.05, vol: 0.2, scheme: 'exact' }
  refuses(() => touchstone.gbmPaths({ ...spec, seed: 1 }, touchstone.normals(1, 4)), TypeError, 'normals(seed')
  refuses(() => touchstone.gbmPaths({ ...spec, scheme: 'milstein' }, touchstone.normals(1, 4)), TypeError, 'spec.scheme')
  refuses(() => touchstone.priceAndGreeksAt({ strike: 100, type: 'call', vol: 0.2, rate: 0.05, dividendYield: 0, exercise: 'american' },
    [100], [1]), TypeError, 'European')
  refuses(() => touchstone.priceAndGreeksAt({ strike: 100, type: 'call', vol: 0.2, rate: 0.05 }, [100], [1]), TypeError,
    'sweep.dividendYield is required')
  refuses(() => touchstone.impliedVolNewtonBrent({ ...base, exercise: 'american' }, baseMarket, 10), TypeError, 'European')
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
    () => touchstone.payoff(base, [100, 'one hundred']),
    () => touchstone.priceAndGreeksAt({ strike: 100, type: 'call', vol: 0.2, rate: 0.05, dividendYield: 0 }, [100, -1], [1, 1]),
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
