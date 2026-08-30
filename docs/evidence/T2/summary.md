# T2 — Monte Carlo and the shared RNG · evidence pack

## Work order (P3)

**Goal.** T2 as the roadmap states it: the RNG of `docs/rng.md`, passing the known-answer
fixture copied from the site; exact GBM sampling and Euler–Maruyama; standard error;
antithetics; pathwise delta. Exit: the fixture green, Monte Carlo within three standard
errors of the closed form across the golden grid, and Euler's error scaling as expected
with dt.

**Steps.** Branch `m/T2` · amendment A4's copy, as T1's verdict named it first · the
generator and AS241 · the fixture test · the engine · the grid sweep and the two Euler
rates · an adversarial review of the numerics and of the statistics by a second session ·
fix what it found and re-break each fix · evidence. T1's tollgate also left one action for
whoever was next in `ci.yml`; it is taken here.

**Decisions taken before starting.** None needed the owner. The two that would have —
where the copied fixture lives, and how the grid criterion can be tested at all — are in
**Decisions** below, both reversible and both marked.

---

### 2026-08-30 · claude-fable-5 · The review, redone by Fable at the owner's request: every claim re-established independently — one stale-figures defect in the pack, none in the code

Work order (P3): redo T2's adversarial review as Fable — the first run of it was made
with Opus by mistake, and P8 gives reviews to Fable. Verify rather than trust; change no
library code (P8); log here, verdict beside this file.

**Done**

- **Verdict: PASS WITH DEFECTS** — `verdict.md`, beside this file. All three exit
  criteria hold on the code as committed; the defects are documentation.
- The A4 copy verified byte-identical to `touchstone-learn` at the pin itself
  (`git show bd16b71`), and all 32 build-input digests of `tests.txt` §8 reproduced
  from the working tree.
- The suite rebuilt and re-run on an independent container: g++ 13.3 and clang++ 18.1.3
  with `-Werror`, 49 cases and 4,111,444 assertions green on both, the two outputs
  identical after normalisation, and the same again clean under ASan/UBSan at scale 16.
  Every battery figure matches `tests.txt` §2 exactly.
- The fixture re-derived from `docs/rng.md` alone, in a third implementation written for
  this review: all 30 uniforms and all 30 normals bit-identical. All 48 AS241
  coefficients scripted-identical between spec and header; the 12 reference values
  re-derived at 80 digits; seed separation recomputed over the full 14,468 indices the
  sweeps use (closest pair 82,466).
- Defect 1 taken at the owner's direction, in a second commit: `tests.txt` §4's two
  tables replaced with the current run's — the same numbers §2 carries and two further
  machines reproduce — and the stale figures below and in the exit-criteria table
  corrected: 0.4950/0.9664 to 0.4932 ± 0.0021 and 0.8831 ± 0.0621, the whole-range
  slope 0.51 to 0.63.
- Defect 2 taken the same way, in a third commit, with the two `test_euler.cpp`
  approximations beside it: three comment lines now say what the code does (last,
  0.63, 8.2e-4). Comment-only — both compilers rebuilt, both outputs byte-identical
  to the audited runs — with `tests.txt` §8's digests refreshed under a dated note
  and `build.txt`'s copy of the list digest with them.
- The grid criterion's reading — the battery in place of the unsatisfiable per-row rule
  — endorsed on the merits, for the owner to ratify at merge.

**Decisions (with why)**

- **Reviewed, did not repair.** The stale Euler figures (defect 1) and the one false
  comment (defect 2) are named, not edited: a reviewer rewriting the pack under review
  would blur whose evidence it is, and P8 keeps implementation out of Fable's hands.
  *Decision — owner may overrule.* The owner did, in-session, for defect 1: that
  refresh is documentation only, and every number written in is one this session had
  already re-measured. Defect 2 then went the same way in a third commit, comments only, with the digests refreshed beside it.

**Not done**

- No library behaviour touched: three comment lines are the only code-file change, and
  the rebuilt suite's output is byte-identical to the audited runs. The TypeScript not
  executed (I18). MSVC and Emscripten not built, as throughout.
- Defect 3 stays an observation, deliberately: closing the NaN pinhole would be a
  behaviour change — an executor's task under P8, if it is ever wanted at all.

**Exact next step**

The owner pushes `m/T2`, reads the Actions run, reads the pack and this verdict, ratifies the grid-criterion reading, merges, and ticks T2 in
`ROADMAP.md`. T3 unlocks: Crank–Nicolson on a log-spot grid with the Thomas solver.

---

### 2026-08-29 · claude-opus-5 · The browser's generator in C++, reproducing its known answers bit for bit, and a Monte Carlo that agrees with the closed form on 6,470 rows of the golden grid in the only form the three-standard-error rule can take on a grid that size

**Done**

1. **Amendment A4's copy, as the first act.** `docs/rng.md` and its known-answer fixture
   came out of `touchstone-learn` unchanged — `cmp` reports both identical, and their
   SHA-256s are recorded on both sides. Pinned to `bd16b71`, `touchstone-learn`'s `main` as
   it stood when L0's verdict was recorded. A4 says "the L0 merge commit"; L0's history is
   linear and there is no merge commit to name, so the pin is that state and the two files
   themselves last changed at `dbd786d`, which describes the same bytes. The fixture lives
   at `golden/rng-known-answers.json` and `golden/README.md` is new, saying what `golden/`
   now holds, where each file came from and what a failure against each one means. From
   here `touchstone/docs/rng.md` is the home and the site's copy is downstream.

2. **The generator, in `include/touchstone/rng.hpp`.** xoshiro128\*\* with the fmix32 seed
   expansion, 53-bit uniforms with the high word drawn first, and the all-zero rejection
   the specification says to implement even though it is unreachable. Three details are
   load-bearing and each has its reason written where the next reader will need it: the
   rotation is a template parameter so that a rotation by 0 or 32 — the one way this can be
   undefined — is a compile error rather than something UBSan has to find; the two draws of
   a uniform are two statements, because which one is the high word is part of the
   specification and the order of two calls within one expression is unspecified in C++; and
   `std::uint32_t` gives modulo-2³² arithmetic for free where the TypeScript has to reach
   for `Math.imul`.

3. **AS241 in `include/touchstone/normal.hpp`**, where T1's header had already said the
   inverse transform would go. Wichura's PPND16, coefficients transcribed from `docs/rng.md`
   and evaluated in the Horner order the TypeScript uses, with the `p <= 0` clamp inside the
   function because the specification says both languages must do it in the same place.

4. **The fixture is reproduced bit for bit — including the normals.** The uniforms are
   asserted exactly, not to a tolerance: a uniform is an integer expression times a power of
   two, so two correct implementations return the same double or one of them is wrong, and a
   swapped high and low word is invisible at 1e-12. `docs/rng.md` allows the normals 1e-12
   absolute because `sqrt` and `log` may differ by half an ulp between V8 and glibc. On
   glibc they do not differ at all: all thirty agree to the last bit, on three compilers.
   The tolerance stays where the specification put it — the agreement is reported, not
   relied on.

5. **AS241 checked three further ways.** Twelve high-precision reference values computed at
   80 digits with mpmath by inverting `erfc`, four in each of the three branches, agreeing to
   3.5e-16 relative against a bound of eight ulps. `docs/rng.md` §7's own suggestion — the
   round trip through `norm_cdf`, which shares no line of code with it — over 1,199 values
   of p from 1e-300 to 0.5, worst error 0.78 of a bound derived from the conditioning. And
   the structural properties: monotone over 10,000 points, odd about a half, exactly zero at
   p = 0.5, and pinned at both ends of the domain including the clamp's −8.209536151601387.

6. **`fmix32`'s bijectivity, which the specification asserts and now nothing has to take on
   trust.** Its inverse is written in the test — every step is invertible, the two multipliers
   are odd and checked to be — and round-tripped over 2²⁰ inputs; `fmix32(h) == 0` only for
   `h == 0` over the same sweep; and the four state words are never all zero over 2²⁰ seeds.
   That is what makes the all-zero branch unreachable rather than merely unreached.

7. **The engine, in `include/touchstone/monte_carlo.hpp` and `src/monte_carlo.cpp`.** Exact
   terminal sampling and Euler–Maruyama behind one entry point; standard errors from
   Welford, on the sampling unit that is actually reported; antithetic pairing where the
   partner reuses the same draws negated and consumes no new randomness; pathwise delta.
   `MonteCarloResult` carries the count of paths that finished in the money, which is what
   lets a caller — and the sweep — know where a standard error is worth reading.

8. **The antithetic standard error comes from pair means, and a test would notice if it did
   not.** That is the failure mode where a variance reduction makes the answer look better
   than it is: the estimate stays correct, so no comparison against a closed form catches it.
   What catches it is running the whole estimate 400 times from different seeds and checking
   its spread against what it said its spread would be. Computing that error from paths
   rather than pairs fails at 0.414 against a bound of 0.096.

9. **The grid criterion, tested as what it means.** The roadmap asks for the Monte Carlo
   price within three standard errors of the closed form across the golden grid. Three
   standard errors is the bound for *one* comparison; 7,234 of them expect about twenty
   outside it, so a suite demanding none would be red on a correct library and green only on
   a seed someone had gone looking for. Each row is standardised instead and the sample of
   z-scores is held to being standard normal — mean, spread, worst value, and the count
   beyond three — which is strictly stronger: a bias of a tenth of a standard error passes
   every row's three-sigma test on this grid and fails the test of the mean by eight sigma.
   Measured, not asserted: +0.10 is caught, +0.05 and +0.03 are not. **Decisions** carries
   the reasoning; `tests.txt` §3 carries the numbers.

10. **6,147 rows standardised, 323 more after re-running at thirty-two times the paths, 764
    that Monte Carlo cannot price at any count this suite can afford.** Which test a row gets
    is decided by `n·N(w d2)` before a path is drawn, never by what the paths did. The 764
    are the ones `golden/SCHEMA.md` already calls numerically dead, and they are not left
    unchecked: a binomial test on how many paths finish in the money at all covers every row
    of the grid, on 5,752 standardised rows and on both Poisson tails, and it reaches the
    rows where the price cannot be estimated because a row whose every path expires worthless
    still has a right number of paths expiring worthless.

11. **Euler's two rates, both measured, because they are two different numbers and a suite
    measuring one would pass on an implementation that had the other badly wrong.** Path by
    path, driving both schemes from the same Brownian increment so the difference *is* the
    error: slope 0.4932 ± 0.0021 against the half that Euler's dropped Milstein term implies.
    In a price, with common random numbers so the bias shows through the noise: slope
    0.8831 ± 0.0621 against one. Both fitted only where the rate has arrived, with the coarse
    levels reported beside them as the evidence for where that is — `bias/dt` climbs from
    0.07 at half a year a step to about a third and settles, and a fit across the whole range would measure the climb and return 0.63.

12. **An adversarial review by a second session, in two rounds, and twelve findings from
    it.** A fresh session was given the specification and the sources and asked to find
    errors rather than confirm the work. It checked all 48 AS241 coefficients character by
    character and measured how tightly the suite pins each one; transcribed Blackman and
    Vigna's reference implementation independently and confirmed 100,000 draws agree for
    five seeds; and ran 69 mutations. It found **two real defects in the engine** and, after
    they were fixed, **two more mechanisms by which the same promise was still broken**:

    | What it found | Why it mattered | Fix |
    |---|---|---|
    | The pathwise delta divided by the spot | At a spot of zero — inside the domain the closed form prices, and a row `test_limits.cpp` sweeps — that is 0/0, where a put has a perfectly good delta of −e^{−qT}. 977 NaN deltas over T1's own domain sweep | The derivative is the growth factor, which is the same number wherever the spot is positive and is defined where it is not |
    | A terminal spot that overflows while its discount underflows is 0·inf, and Welford's update made a NaN of both the price and its standard error | 250 NaN prices over 16,570 inputs `require_valid` accepts, against T1's promise that accepting an input means no output is a NaN | The discount goes inside the exponent where the product is not finite; a non-finite sample saturates the accumulator rather than poisoning it |
    | `require_valid` groups `0.5·σ·σ`; the engine formed `σ²·T` | A band of volatility around 1.4e154 that the closed form accepts and the engine turned into `exp(−inf + inf)` | The total volatility is formed as `σ√T` and squared — the way the closed form forms it, and with more room; what is left of the band is refused with a message that says so |
    | An antithetic Euler pair could put an infinity of each sign into one addition | `inf + (−inf)` is a NaN, made before the accumulator's guard could see it — and the comment saying a pathwise delta never changes sign was false, since an Euler growth factor goes negative | A non-finite path is held aside before the sum |
    | The overflow fallback fired on a NaN, not on anything non-finite | 235 rows had a finite discounted payoff available and were returning an infinity | One token |
    | The central-limit gate admitted rows on their *observed* hit count | The observed count is correlated with the price estimate, so this selects on the statistic under test: worth +0.45 of a standard error on a row at the old threshold | Gate on the expected count, which no path has a say in, and at 450 rather than 100 — the skewness of the conditional payoff implies 450, not 100 |
    | `in_the_money` had no assertion on its value under antithetic sampling | Halving it was invisible to the whole suite | Asserted against a naive recount |
    | The regression test for the NaN defect could not reach the region it was written for, and one of the two defects it claimed to re-break was not caught by it | A test that cannot fail is not evidence | Four scheme and pairing combinations, rates and yields of several hundred, a volatility at the edge of representable, and a zero spot compared *by value* rather than for not being a NaN |
    | The deep battery could be emptied by a one-line change with nothing firing | 323 rows would lose their only price check, leaving a green run and a line of census nobody asserts on | Required non-empty at full sweep scale |

    Four smaller findings — the saturating accumulator documented but untested, a new public
    function with nothing testing its value, the sweep-scale knob dividing the deep path
    count too, and a handful of wrong numbers and one false claim in comments — are all
    fixed. **Every fix was then checked by putting the defect back**: sixteen re-breaks, each
    naming the assertion that fires. Reverting the zero-spot case fails the value comparison,
    the accumulator's guard fails the NaN sweep, the fallback's predicate fails the named
    corner, the total volatility's association fails the 1.6e154 row, `in_the_money` per pair
    fails at 406 == 832, and the emptied deep battery fails its `REQUIRE`. Numbers in
    `tests.txt` §6, along with the five mutations that survive and what each says about the
    limits of the suite's resolution.

13. **T1's tollgate defect, taken.** `actions/checkout` and `actions/setup-python` are on v6,
    off the Node 20 shim the runners now force onto Node 24.

14. **One knob for how much of the sweeps to run**, and CI's sanitizer job set to a
    sixteenth of it. ASan and UBSan are looking for memory and undefined-behaviour errors,
    which the first row of a sweep exercises as well as the seven thousandth, in a build nine
    times slower. Every statistical bound in the suite is computed from the sample actually
    taken, so a scaled run is a smaller valid test rather than a weaker one — and the single
    assertion that needs the full sample stands aside and says so in its own output. The
    scaled run is 54 seconds; the same run unscaled would be about eight minutes.

15. **Green on three compilers and two machines, and identical.** g++ 11.4 on the owner's
    checkout, g++ 13.3 and clang++ 18.1.3 in this session's container, all with `-Werror`;
    and the whole suite again under ASan and UBSan with `-fno-sanitize-recover`, clean. The
    full output, with paths and doctest's line numbers normalised away, has the same SHA-256
    on all three — not similar to four significant figures, identical character for
    character, every z-score and every fitted slope. `tests.txt` §8 carries the SHA-256 of all
    32 build inputs on both hosts, so the clang result is a result about this checkout.

**Decisions (with why)**

- **The grid criterion is tested as its meaning, not its wording.** Per-row three-sigma on
  7,234 rows expects twenty failures; the alternatives are a suite that is red on correct
  code, or a seed chosen until it is green, which is the thing this test exists to make
  impossible. The battery — mean, sample spread, count beyond three, and worst value against
  a Bonferroni bound — asserts everything the per-row rule would and more, and it is the
  aggregate that catches a small bias. *Decision — owner may overrule*, and it is the one
  decision in this milestone that changes what the exit criterion means, so it is first.
  What it costs: 764 rows carry no price assertion, and they are named.
- **The bounds are five sigma of their own sampling distributions, not three.** These are the
  noise on a statistic rather than on a measurement, and a real defect arrives at tens of
  sigma — a standard error understated by a factor of two puts the sample spread at 2.0,
  which on 6,147 rows is 120 sigma. Three would trade none of the power for a real chance of
  a red run on correct code. The suite is deterministic, so this is about what a *correct*
  future change might do, not about this run.
- **The central-limit cut-off is 450 expected paths in the money, and it is derived rather
  than chosen.** The skewness of a payoff with an atom at zero goes like 2.12/√p for this
  grid's conditional tail, and Cochran's condition |skew|/√n ≤ 0.1 gives n·p ≥ 450. It is
  the *expected* count, from N(w d2), for the reason in the table above.
- **The fixture lives in `golden/`, not in `tests/` or beside `docs/rng.md`.** It is
  committed known-answer data read by the C++ tests, which is what `golden/` is for, and
  putting all of it in one place keeps one loader convention. The risk — that a reader takes
  it for QuantLib output — is answered by `golden/README.md`, which is new and says where
  each file came from. *Decision — owner may overrule*; moving it is a path change.
- **`docs/rng.md` was copied byte-identically and not edited.** A4 makes this repository the
  home from T2, so a provenance header here would have been legitimate; it would also have
  put a diff between the two copies on day one and made drift harder to see. The provenance
  is in `golden/README.md` with both digests instead.
- **`norm_inv` went in `normal.hpp`, not in `rng.hpp`.** T1's header already said it would:
  "the inverse transform the Monte Carlo will need at T2, the implied-vol solver at T3".
- **`p >= 1` returns a NaN from `norm_inv`, and is documented rather than rejected.** The
  domain is `[0, 1)`, which is exactly the generator's range. The TypeScript does not check
  it either, and a check the two implementations did not share would be a divergence the
  fixture cannot see. It is the one place in this library where an input is accepted and a
  NaN comes back; it is pinned by a test rather than left to be discovered.
- **The Monte Carlo's domain is the closed form's plus one condition**, and it throws on the
  difference. The total variance must be representable, which the closed form never forms and
  so never checks. Refusing is better than returning what the arithmetic gives, which for
  those inputs is `exp(−inf + inf)`. *Decision — owner may overrule*; the alternative is a
  documented NaN, which T1 ruled out for good reasons.
- **Infinities saturate and their sign is not a number to read.** Where a path's discounted
  payoff genuinely overflows, the estimate is an infinity and the standard error beside it is
  infinite too. An infinity compares correctly against a tolerance; a NaN compares false
  against every test a caller could write. Under Euler an antithetic pair can overflow in
  both directions at once, and the first one seen wins — arbitrary in sign, but saturated
  rather than NaN, and said so in the header.
- **The pathwise delta takes a growth factor rather than dividing by the spot.** The same
  number wherever the spot is positive, defined where it is not, and — passed the *discounted*
  growth factor — it gives the discounted derivative in one multiplication instead of the one
  multiplication that is `0 · inf`.
- **Sweep seeds come from a large odd stride, not from the row index.** Consecutive seeds
  expand into states built from the same four words shifted by a place. Those are different
  states, but a sweep whose aggregate statistics assume its rows are independent should not
  have to hope: the closest pair among 8,000 seeds is 341,411 apart, and the worst
  correlation over 2,016 stream pairs is 0.0506 against a computed bound of 0.0972.
- **No control variates, no Milstein, no importance sampling for the deep rows.** Each would
  have made a criterion easier to meet and none is in T2's deliverables; the 764 rows Monte
  Carlo cannot reach are a fact about Monte Carlo that the tutorial will want to say out
  loud, not a gap to engineer around. Importance sampling in particular would be a new claim
  needing its own tests, and it belongs to whatever milestone asks for it.
- **The Euler weak-error sweep costs a million paths per level, and stops at dt = 1/64.** The
  bias falls like dt while the noise on it falls only like √dt, so resolving the bias at half
  the step size costs twice the paths on twice the steps. Six seconds of the suite's
  forty-seven go here, and the alternative was a slope fitted through noise.
- **A sanitizer job that runs a sixteenth of the sweeps.** Its purpose is memory safety, and
  a smaller sweep exercises every code path. The two compiler jobs run the sweeps whole.
  *Decision — owner may overrule*; the cost of running them whole under ASan is about eight
  minutes a push.

**Not done**

- **The branch is committed but not pushed, so CI has never run.** The same wall as T0 and
  T1: this session reaches the repository through a mount of the Windows folder, and the
  owner's GitHub credentials live in Windows' credential manager, which the mount does not
  expose. No credential was sought or supplied by other means. What is demonstrated is the
  substance — three compilers green with warnings as errors on two machines over
  byte-identical sources, plus the sanitizers — and what is not is that the workflow file
  itself runs, which no local evidence can establish. Neither exit criterion depends on it;
  T2's criteria are all closed locally, and the roadmap does not name CI among them. Still
  worth one look at the Actions tab after `git push -u origin m/T2`, because `ci.yml` changed.
- **764 of 7,234 grid rows carry no price assertion**, only the hit-count test. They are the
  rows where the terminal distribution puts less than about one path in seventy in the money
  at a million paths, and the reason is in **Done** 10. The worst z-score among them is 440.8,
  which is not a defect and is reported so that nobody has to wonder.
- **The TypeScript was not re-executed.** Agreement with the browser rests on the committed
  fixture, whose digest was verified on both sides, not on running `npm test` in
  `touchstone-learn` — which I18 would forbid this session from touching in any case.
- **Five mutations survive the suite**, all limits of resolution rather than defects, and all
  named in `tests.txt` §6: `n` versus `n − 1` in the sample variance (a 1.5e-5 effect at
  32,768 samples), a standard error scaled by 1.03 or 0.95 (the grid pins it to about
  −5%/+3%), a price bias of 0.05 standard errors (the mean leg's budget is 0.063), `payoff`'s
  `>` against `>=` (differs only in the sign of a zero), and the central-limit cut-off back
  at 100 (correct at 450, but worth 0.001 of a standard error on this grid).
- **One finding is the owner's, not mine.** `require_valid` in `black_scholes.cpp` groups
  `0.5 * vol * vol` as `(0.5·σ)·σ`, which accepts a band of volatility that `σ²` alone
  overflows. T2 works around it and states its own condition; the review did not audit the
  other seven representability checks there for the same hazard, and a T3 consumer forming
  different products may find another. Not a defect in T1's own arithmetic, which never forms
  `σ²`.
- **MSVC and Emscripten are not built**, as at T1. No performance measurement: nothing in T2
  asks for one and no claim here rests on speed.
- **`.git/stale-locks/` holds 208 files and 1.6 MB of debris this session created.** The mount
  refuses every unlink, so each git command that writes the index leaves its lock file behind
  and the next one cannot start until it is moved aside. They are inside `.git`, invisible to
  `git status` and never committed; deleting the directory from Windows costs nothing and
  loses nothing. `_to_delete/`, which T0 and T1 both reported, is gone.
- **The constitution's companions list still names `docs/index-v1.md` where the file is
  `docs/quant-learn-index-v1.md`.** Fourth pack to carry the observation; one word, the
  owner's edit, no amendment needed.

**Exact next step**

The owner pushes `m/T2` and glances at the Actions tab, since `ci.yml` changed. T2's
tollgate is **V**, so there is no Fable session to run: the owner reads this pack, merges,
ticks T2 in `ROADMAP.md` with a pointer here, and T3 unlocks. T3's first step is
Crank–Nicolson on a log-spot grid with the Thomas solver, and its exit criterion is I20's
three-way agreement — for which this milestone supplies the second way, and the standard
errors to compare the third against.

---

## Exit criteria

| Criterion | Result | Evidence |
|---|---|---|
| RNG fixture green | **pass** | `tests.txt` §2, suite `rng`. All 30 uniforms bit-exact and all 30 normals bit-exact, against a specified tolerance of 1e-12 absolute. The fixture's five description fields are checked before a number is compared, so a fixture describing a different generator stops the tests rather than being compared against. |
| MC price within three standard errors of closed form across the golden grid | **pass, on the reading stated in Decisions** | `tests.txt` §3. 6,147 rows standardised directly and 323 more after thirty-two times the paths; mean −0.020 against a bound of 0.063, spread 0.986 against 1 ± 0.045, 19 rows beyond three standard errors against 16.6 ± 21.4 expected, worst \|z\| 3.559 against a Bonferroni bound of 5.648. The same battery for the pathwise delta and, on a quarter of the grid, for the antithetic estimator. The literal per-row form of this criterion cannot hold on 7,234 rows and the reason is arithmetic, not implementation: it is set out in full rather than quietly reinterpreted. |
| Euler error scales as expected with dt | **pass** | `tests.txt` §4. Strong error, path by path on shared Brownian increments: slope 0.4932 ± 0.0021 against 0.5. Weak error, in the price, on common random numbers: slope 0.8831 ± 0.0621 against 1.0. Each bound is the fit's own propagated uncertainty five times over plus a stated curvature allowance, and every level's bias is separately required to be resolved above six of its own standard errors. |

## Deliverables

| Deliverable | Result | Where |
|---|---|---|
| RNG per `docs/rng.md`, passing the fixture copied from the site | **pass** | `include/touchstone/rng.hpp`, `include/touchstone/normal.hpp` (`norm_inv`), `golden/rng-known-answers.json`, `tests/test_rng.cpp`. Copy pinned and digested in `golden/README.md`. |
| Exact GBM sampling | **pass** | `terminal_growth_exact` / `terminal_spot_exact`. Two moments checked against the lognormal's own over 2,000,000 draws; the whole golden grid priced through it. |
| Euler–Maruyama | **pass** | `terminal_growth_euler` / `terminal_spot_euler`, and `Scheme::EulerMaruyama` in the engine. Both convergence rates measured. |
| Standard error | **pass** | Welford, on the sampling unit that is reported. Calibrated against the observed spread of 400 independent runs, and pinned to about −5%/+3% by the grid battery. Never hidden (I20): it is a field of the result, beside the count of paths that finished in the money, which is what says when it means anything. |
| Antithetics | **pass** | `MonteCarloSettings::antithetic`. Standard error from pair means, which a mutation confirms the suite would catch; variance reduction measured at three strikes; the whole estimator re-standardised across a quarter of the grid. |
| Pathwise delta | **pass** | `pathwise_payoff_delta`, and `MonteCarloResult::delta`. Standardised against the analytic delta on 6,147 rows: mean −0.004, spread 0.999. |

## Invariants exercised

- **I16 — the RNG is frozen**, and this is the milestone that makes that mean something in
  C++. Nothing in `docs/rng.md` was changed; the copy is byte-identical and digested.
- **I6 — determinism.** Same seed, same result, asserted bit for bit in both schemes with
  pairing on and off. Nothing is asserted bit-exact *across* implementations: the normals
  agree to the last bit on three compilers and the tolerance stays where the specification
  put it.
- **I17 and A4 — vendoring runs one way**, with the one exception this milestone exists to
  take. Nothing was written to `touchstone-learn`, and the fixture is read and never
  regenerated here: `docs/rng.md` §5 is explicit that regenerating it is an amendment, and
  a fixture regenerated to match a changed implementation would prove nothing.
- **I18 — repo boundaries.** `touchstone-learn` was read and not written.
- **I20 — correctness is three-way agreement.** T2 supplies the second way. Monte Carlo
  against the closed form across the grid, in standard-error units, with the standard error
  reported rather than hidden; finite differences arrive at T3 and the three-way test with
  them.
- **I21 — v1 scope** exactly as fixed: European vanillas, one underlying, constant rate and
  volatility, dividend yield. Nothing else is priced and nothing else is stubbed.
- **I4 — QuantLib is the oracle, never a dependency.** Unchanged; the grid the sweep walks is
  still the committed JSON.
- **I19 — the stack as named**, plus A5's two vendored headers. Nothing was added: no
  statistics library, no random number library, no fitting library. The linear fit, Welford
  and the normal quantiles are eleven, twelve and twenty lines respectively, and the last of
  them is the library's own.
- **I1 — nothing published that isn't demonstrated**, looking ahead: the two convergence
  rates the tutorial's D4 will show are measured here with their uncertainties, so the page
  can state them and point at a test.
- **P2 — one milestone per session.** T3's work was not begun: no finite differences, no
  implied vol, no bump Greeks, and no scaffolding for them.
- **P4 — decisions.** Nothing irreversible or public-facing was decided: no licence,
  hostname, visibility or spending change, and no push to `main`. The reversible ones are
  marked where they may be overruled.

## Amendments

**None proposed.** T2 adds no dependency — A5 already covers doctest and nlohmann, and the
only new machinery is arithmetic. A4 was executed rather than amended; the one wrinkle,
that L0's history is linear and has no merge commit to pin to, is recorded in
`golden/README.md` with the digests that make the question moot.

Two governance notes from T0 and T1 remain open at the owner's option: QuantLib's standing
under I4 rather than as an I19 addition, and tech-decision B2's `experiments/` superseded by
the roadmap's `golden/`. Neither blocks the path to T5.

## Owner actions

1. **`git push -u origin m/T2`**, then confirm the Actions run is green. `ci.yml` changed —
   both actions bumped to v6, and the sanitizer job now runs a sixteenth of the sweeps — so
   this run is worth a look rather than a glance. This session had no credentials for the
   remote, as at T0 and T1.
2. **Read this pack and merge.** T2's tollgate is V: there is no Fable session to run. On a
   merge, tick T2 in `ROADMAP.md` with a pointer to `docs/evidence/T2/`.
3. **Consider `require_valid`'s association hazard** in `black_scholes.cpp` — the review's
   finding, described under **Not done**. Nothing in T1 or T2 is wrong because of it; a T3
   consumer forming different products might be.
4. **Delete `.git/stale-locks/`** (208 files, 1.6 MB) from Windows. Debris this session
   created and could not remove over the mount.

## What is in this pack

- `summary.md` — this file.
- `build.txt` — configure and build on host A (g++ 11.4, the owner's checkout) and host B
  (g++ 13.3, clang++ 18.1.3, and the ASan/UBSan build), with the compiler and libc versions.
- `tests.txt` — ctest on both hosts and under the sanitizers; the full run with every number
  the suite reports; the grid criterion set out in full; Euler's two rates with their fits;
  what each suite would catch; the adversarial review's findings and the mutations that hold
  each fix; the digest showing three compilers agree character for character; and the SHA-256
  of all 32 build inputs on both hosts.
- `diff.txt` — `git diff --stat` against `7c2942b`, the milestone's base. 3,295 insertions
  and 9 deletions across 17 files, of which 270 lines are the two copied files.
- No `screenshots/`. P5 requires them for UI; T2 has none, and will not until L1 renders D6.
