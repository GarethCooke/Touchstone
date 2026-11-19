// What the closed form costs through the WebAssembly module in Node: one point a
// call, many points in one call, and many points as many calls each handed a
// slice of one array, the way a hedge sample hands over one path's spots at a
// time. Beside them, what the argument clone costs for a slice, a whole array
// and a plain array, since that is where a slice's cost would hide.
//
//   node wasm/timing.mjs
//
// TOUCHSTONE_WASM names the built `touchstone.mjs`, as for the smoke test.
// Each figure is the median of `runs` timed runs after one untimed one; the
// spread is printed beside it. One machine's numbers: nothing here is asserted.

import { cpus, totalmem } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const artifact = resolve(process.env.TOUCHSTONE_WASM ?? resolve(root, 'build-wasm/wasm/touchstone.mjs'))
const { default: createTouchstone } = await import(pathToFileURL(artifact).href)
const touchstone = await createTouchstone()

const runs = 9

/** `body()` timed `runs` times after one untimed run: median, least and most, in ms. */
const time = (body) => {
  body()
  const taken = []
  for (let r = 0; r < runs; r++) {
    const start = performance.now()
    body()
    taken.push(performance.now() - start)
  }
  taken.sort((a, b) => a - b)
  return { median: taken[runs >> 1], least: taken[0], most: taken[runs - 1] }
}

const report = (label, { median, least, most }, per) => {
  const each = per === undefined ? '' : `   ${((median * 1000) / per).toFixed(3).padStart(8)} µs each`
  console.log(`${label.padEnd(58)} ${median.toFixed(3).padStart(10)} ms` +
    `  (${least.toFixed(3)} to ${most.toFixed(3)})${each}`)
}

// A hedge sample at 256 rebalances: 781 paths, a delta at each of the 256
// dates before expiry. The spots are the paths of one sample, as `gbmPaths`
// returns them; the times to expiry are the time left at each date.
const expiry = 1
const dates = 256
const paths = 781
const sweep = { strike: 100, type: 'call', vol: 0.2, rate: 0.05, dividendYield: 0 }
const spec = { horizon: expiry, steps: dates, spot: 100, drift: 0.05, vol: 0.2, scheme: 'exact' }
const sample = touchstone.gbmPaths(spec, touchstone.normals(1, paths * dates))
const left = Float64Array.from({ length: paths * (dates + 1) }, (_, i) => expiry * (1 - (i % (dates + 1)) / dates))
const points = 200_000
const spots = sample.slice(0, points)
const times = left.slice(0, points).map((t) => Math.max(t, 1 / dates))

console.log(`Node ${process.version}; ${cpus()[0].model.trim()}, ${cpus().length} logical processors,` +
  ` ${Math.round(totalmem() / 2 ** 30)} GB; module ${touchstone.version} at ${artifact}`)
console.log(`median of ${runs} runs after one untimed run; the range in brackets`)
console.log()

{
  const option = { strike: sweep.strike, expiryYears: 0, type: sweep.type }
  const market = { spot: 0, vol: sweep.vol, rate: sweep.rate, dividendYield: sweep.dividendYield }
  let sink = 0
  report(`priceAndGreeks(...).delta, ${points.toLocaleString('en')} calls of one point`, time(() => {
    for (let i = 0; i < points; i++) {
      option.expiryYears = times[i]
      market.spot = spots[i]
      sink += touchstone.priceAndGreeks(option, market).delta
    }
  }), points)
  if (Number.isNaN(sink)) throw new Error('unreachable')
}

report(`priceAndGreeksAt, one call of ${points.toLocaleString('en')} points`,
  time(() => touchstone.priceAndGreeksAt(sweep, spots, times)), points)

report(`priceAndGreeksAt, ${paths} calls of ${dates} points, each a slice`, time(() => {
  for (let p = 0; p < paths; p++) {
    const from = p * (dates + 1)
    touchstone.priceAndGreeksAt(sweep, sample.subarray(from, from + dates), left.subarray(from, from + dates))
  }
}), paths * dates)

console.log()
const whole = new Float64Array(200_704).map((_, i) => 100 + (i % 97))
const slice = whole.subarray(1024, 1024 + 256)
const own = Float64Array.from(slice)
const plain = Array.from(whole)
const reps = 1000
for (const [label, value, count] of [
  ['structuredClone, a 256-value subarray of 200,704', slice, reps],
  ['structuredClone, a 256-value Float64Array of its own', own, reps],
  ['structuredClone, the whole 200,704-value Float64Array', whole, reps / 10],
  ['structuredClone, the same values as a plain array', plain, reps / 100],
]) {
  report(label, time(() => { for (let r = 0; r < count; r++) structuredClone(value) }), count)
}
