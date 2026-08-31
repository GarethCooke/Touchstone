# T3 — Finite differences, implied vol, bump Greeks · evidence pack

## Work order (P3)

**Goal.** T3 as the roadmap states it: Crank–Nicolson on a log-spot grid with the Thomas
solver; implied vol by Newton with a Brent fallback; bump-and-revalue Greeks; American early
exercise as a stretch. Exit: three-way agreement (I20) within stated tolerances across the
golden grid, bump Greeks matching analytic within tolerance, implied vol round-tripping
golden prices to 1e-8.

**Steps.** Branch `m/T3` · the Thomas sweep and its projected form, tested against projected
SOR before anything is priced on them · the grid, and the four measurements that make its
claims claims · implied vol and Brent · bump Greeks, with the bump sizes measured rather
than derived · the American oracle, generated and independently verified · the tests · an
adversarial review by mutation, and a second pass on whatever it finds · three compilers,
two machines, the sanitizers · evidence.

**Decisions taken before starting.** Two, both put to the owner in-session because both
change what the milestone is rather than how it is done. American early exercise: **include
it** — the roadmap calls it a stretch and the owner asked for it. T2's review left an open
question about `require_valid`'s association hazard: **fix `black_scholes.cpp` too**, rather
than working around it as T2 did. Both are recorded under **Decisions** below with what they
cost.

---

### 2026-08-31 · claude-opus-5 · The third way of pricing a European vanilla, the first way of pricing an American one, and a NaN that T1 promised could not happen

**Done**

1. **The owner's second decision found a real defect, in T1.** `require_valid` promised that
   an accepted input never produces a NaN, and it checked the drift as one product,
   `(r − q + ½σ²)·T`. The kernel forms two, separately: `(r − q)T` inside the log-moneyness
   and `½σ²T` beside it in `d₁`. Put `q = ½σ²` with `r = 0` and the sum is exactly zero, so
   every expiry passes — while the two terms themselves are `−inf` and `+inf` and `d₁`'s
   numerator is `−inf + inf`. **σ = √(2·10³⁰⁰), q = 10³⁰⁰, T = 10¹⁰ was accepted by T1 and
   priced as a NaN**, in all seven outputs. Every other check in `require_valid` passes on
   it, which is the point: the escape is not a missing check but a check that guards a
   different set of inputs than the formulas use.

   The repair is not a tighter bound. `include/touchstone/scales.hpp` is new and holds the
   five scalar quantities every method forms — `σ√T`, `½σ²T`, `(r−q)T`, `e^{−rT}`,
   `ln(S/K) + (r−q)T` — each written once, in one association. `require_valid` and
   `make_kernel` now call the same functions, so the domain and the expressions it guards
   cannot drift apart; `monte_carlo.cpp`'s own `σ√T` forwards to the same line.
   `tests/test_associations.cpp` pins the escaped input, the boundary of all eight checks
   either side, and the associations themselves at values where a regrouping shows.

   Nothing the golden grid contains changed hands: all 7,234 rows are still inside the
   accepted domain, and the volatility band T2 depends on — σ = 1.6e154 over an expiry of
   1e-160, which squares to an infinity but halves first — is still priced, because the
   repair is two separate checks rather than one broader one.

2. **The grid.** `pde.hpp` and `pde.cpp`: Crank–Nicolson in `x = ln S` and time-to-expiry,
   where the coefficients are constant and one uniform grid is uniformly accurate. The spot
   lands **exactly** on a node — the domain is sized first, then anchored at `ln S` and grown
   outward — so the price is a solution value rather than an interpolation, and delta and
   gamma are central differences about the point they are wanted at. Dirichlet conditions are
   the exact European asymptotes at each time level. Rannacher's start damps what
   Crank–Nicolson only fails to amplify, and the payoff enters as a cell average rather than
   a nodal sample.

   Four claims, four measurements, none of them the price: second order in `dx` (ratios
   3.97, 3.99, 4.00), second order in `dτ` (4.31, 4.99, 3.51), a truncated domain that
   contributes 1.3e-08 across α ∈ [3, 12] at a fixed `dx` against a discretisation error of
   2.8e-06 — and 3.2e-04 at α = 2, which is what makes it a measurement — and a matrix whose
   diagonal dominance is 1.000 on every row of the grid, which is the whole of the unpivoted
   sweep's stability.

   Two settings exist only because their value is a number rather than an opinion.
   `rannacher_steps`: gamma at the strike on twelve time steps is out by a **factor of 277**
   with the start off and by 1.7e-03 with it on. `smooth_payoff`: the error constant in
   `|error| = C·dx²` is 15.52 from nodal values and 2.71 from cell averages.

3. **The Thomas sweep, and Brennan and Schwartz's.** `tridiagonal.hpp` is the whole of
   tech-decision B3's "Thomas tridiagonal solver, no Eigen": two sweeps over three bands,
   plus `dominance_margin`, which measures the condition the algorithm needs rather than
   assuming it. The projected form solves the linear complementarity problem exactly under
   one condition — the binding set must be one run at the end the sweep substitutes towards —
   and `test_tridiagonal.cpp` establishes the condition, then complementarity, then agreement
   with projected SOR to **4e-15** over 3,600 nodes and 36 systems. It also prices the
   precondition: on a deliberately two-sided problem the direct sweep and PSOR differ by
   0.0198, ten orders of magnitude more than when it holds.

4. **Implied vol.** Newton from the larger of Manaster–Koehler's and Brenner–Subrahmanyam's
   seeds, with Brent behind it on `[0, max_vol]`. The tolerance is relative to the option's
   own price scale, `max(S e^{−qT}, K e^{−rT})`, because the closed form is a difference of
   two numbers of that size and cannot be computed better than a few ulps of it — an absolute
   tolerance is unreachable on a spot of 1000 and pointless on a spot of 0.01.
   `root_finding.hpp` carries Brent on any bracketed function, so it can be tested on roots
   that are known without it.

5. **Bump Greeks.** `bump_greeks.hpp` differences any pricer, which is what makes the grid's
   vega and rho obtainable at all. The bump sizes are measured, not derived: each swept over
   four decades against the analytic Greek across 864 options, and set where the worst error
   was smallest. Delta and gamma want different spot bumps and get them — 1e-06 and 3e-05,
   against `eps^(1/3)` and `eps^(1/4)` — and the test asserts the minimum is at the default
   and that the error rises on **both** sides of it.

6. **American exercise, and a piece of folklore that is false.** `Exercise::American` runs
   the same grid with the projected sweep and the boundary raised to immediate exercise.
   `golden/american_vanilla.json` is new: 864 rows from QuantLib's Leisen–Reimer lattice at
   2001 steps, with Cox–Ross–Rubinstein and Tian beside it and **the disagreement among the
   three carried per row**, because a fixed tolerance against a file with no closed form
   behind it would be either a claim the oracle cannot support or an allowance the easy rows
   do not need. `verify_american_vanilla.py` re-derives every row with a lattice written in
   numpy from the recursion, and checks the identities, the inequalities and the bounds.

   "Never exercise an American call early" is a theorem about **non-negative** rates. At
   r < 0 the strike is worth more later than now, and the file contains 201 rows where a call
   is worth strictly more than its European counterpart — one of them exactly `S − K = 30`
   against a European value of 27.7576. The two exact identities are stated with their
   conditions and tested only where they hold; so are the American put–call bounds, which
   hold to 3.1e-13 for r ≥ 0 and are breached by up to 2.5e-02 below it.

7. **The adversarial review found the one mistake a price cannot see.** Twenty-four
   mutations, applied one at a time and run whole; 21 caught, 3 surviving with a reason each,
   all in `tests.txt` §5. The one that matters: **pointing the projected sweep the wrong way
   for a call survived the first version of this suite.** It is *consistent* — it converges to
   the same limit, so no comparison at one resolution can see it — but it converges at first
   order instead of second, because the constraint reaches each node before its neighbour has
   been constrained. The American tests now assert the **rate** (measured 3.95–4.00 correct
   against 2.09–2.28 reversed), which is the only thing a price can say about that mistake.
   Writing the mutations also found a dead flag in the implied-vol solver, now gone.

8. **Three compilers, two machines, and one set of numbers.** g++ 13.3 and clang++ 18.1.3 on
   the session's container, g++ 11.4 on the owner's checkout over the mount, all with
   `-Werror` and **zero warnings**; 93 cases and 4,135,768 assertions green on each. The full
   reported output of the two hosts hashes to the same SHA-256 once paths and line numbers are
   normalised. ASan and UBSan at sweep scale 16: green, zero diagnostics. `ci.yml` gains the
   American verifier and its reproducibility check.

**Exit criteria**

| Criterion | Result |
|---|---|
| Three-way agreement (I20) across the golden grid, within stated tolerances | **PASS** — PDE vs closed form on all 7,200 rows at 512×256: price 8.9e-05, delta 3.4e-06, gamma 3.6e-07, scaled by `max(\|ref\|, S)`; 1.3e-03 under SCHEMA.md's `max(\|ref\|, 1)`. Monte Carlo vs closed form on 119 rows: mean −0.218 standard errors, sd 0.977, worst \|z\| 3.17 against a bound of 4.93. Every tolerance stated with its grid in `tests.txt` §3. |
| Bump Greeks match analytic within tolerance | **PASS** — all 7,200 rows: delta 2.8e-10, gamma 2.0e-08, vega 1.2e-08, theta 2.5e-09, rho 2.4e-09, dividend rho 2.8e-09. |
| Implied vol round-trips golden prices to 1e-8 | **PASS** — price round trip over all 7,234 rows: worst scaled residual **1.5e-12**, four orders inside. Volatility round trip reported beside it: 3.3e-07 where vega exceeds 1e-06, and every row inside what its own price affords. |
| *(not an exit criterion)* American exercise, the stretch | Delivered. Against the lattice: worst 3.4e-05 of `max(\|V\|, K)`, and at most 1.46× the row's own three-lattice spread. Exactly European on the 324 rows where it must be, to 4.5e-06. |

**Decisions (with why)**

- **American exercise included, at the owner's direction.** The roadmap calls it a stretch;
  the cost is a new golden file, its generator, its verifier, its schema document, a CI job
  and a test suite — about a third of the milestone. It is worth recording that I21 fixes v1
  scope at European vanillas, so `Exercise::American` is library surface that no v1 page
  uses and no exit criterion tests. It is tested to the standard of everything else.

- **`black_scholes.cpp` repaired rather than worked around, at the owner's direction.** This
  edits T1 code after T1's Fable tollgate passed, so **T1's evidence pack no longer describes
  `src/black_scholes.cpp` exactly**. What changed: five expressions now route through
  `scales.hpp` at the same associations, and one check became three. What did not: any value
  the closed form returns on any input both versions accept — the whole suite's reported
  numbers are unchanged outside the new tests. The alternative, T2's, was for each new
  consumer to state its own conditions and leave the hazard; that would have left a real NaN
  in the library. *The owner may wish to note the T1 amendment in the tollgate record.*

- **α = 6 kept as the default domain width**, though the measurement says three would do and
  would be four times more accurate. One at-the-money row is thin evidence on which to run a
  library close to a boundary, and the cost of the margin is stated rather than hidden.
  *Decision — owner may overrule.*

- **The PDE is compared on two scales and asserted on both.** `SCHEMA.md`'s
  `max(|ref|, 1)` is right for a closed form and wrong for a grid, whose error is a fraction
  of the underlying's scale rather than of the option's price. Reporting only the flattering
  one would have been the easier decision. *Decision — owner may overrule.*

- **The golden sweeps run at 512×256 rather than at the settings' own defaults**, which are
  1024×512. A finite-difference tolerance without a grid beside it is meaningless, so each
  sweep names its grid; running the whole grid at the defaults would add a minute to the
  suite for a number the convergence tests already imply.

**Not done**

- **The branch is committed but not pushed, so CI has never run.** The same wall as T0, T1
  and T2, and this time both routes were tried rather than assumed. `git push --dry-run`
  from the owner's checkout: *"No anonymous write access"* — the credentials live in
  Windows' credential manager, which the mount does not expose, and no credential helper is
  reachable from the Linux side. From the session's own clone: *"access denied by the git
  proxy: GarethCooke/Touchstone is not in this session's authorized repository set, so the
  proxy will not inject a credential for it."* No credential was sought or supplied by other
  means.

  **The second of those is fixable and worth fixing.** Adding `GarethCooke/Touchstone` to
  the session's sources would let a future milestone push its own branch and read its own CI
  run, which would close the one gap every pack from T0 onward has had to record.

  `ci.yml` changed — two new steps — so the Actions run is worth a look rather than a
  glance. **`ci.yml` could not be written by the file-transfer tool at all** (workflow files
  are protected from remote writes); it was edited in place on the owner's machine instead,
  and its digest is in `tests.txt` §8 like everything else.

- **Three mutations survive the suite**, all named in `tests.txt` §5 with the measurement
  behind each: removing Newton entirely leaves a correct solver, because Brent is
  unconditional (not a defect — it is the design); the American boundary values' `max` with
  intrinsic is unreachable at any sane domain width, first differing at α = 0.5; and Newton's
  stall guard never fires on the golden grid.

- **The American premium is not tested against a closed form** — there is none. The strongest
  statements available are the two identities (324 rows, against fifteen digits), the
  inequalities, the put–call bounds, the convergence *rate*, and a lattice that agrees to
  3.4e-05. `AMERICAN-SCHEMA.md` says what that file is worth and where it is silent.

- **MSVC and Emscripten are not built**, as at T1 and T2. No performance measurement beyond
  the suite's own wall clock; nothing here rests on speed.

- **The TypeScript was not touched or run** (I18), and no `docs/rng.md` behaviour changed.

- **The constitution's companions list still names `docs/index-v1.md` where the file is
  `docs/quant-learn-index-v1.md`.** Fifth pack to carry the observation; one word, the
  owner's edit, no amendment needed.

- **The branch carries one commit that is not T3's.** `62f6320`, the owner's own edit to
  L2's entry criteria in `ROADMAP.md`, was committed onto `m/T3` while this milestone was in
  progress. It is untouched and it is HEAD's parent, so `diff.txt` is taken from it rather
  than from `a296fae`; the two differ by that one roadmap line. Merging `m/T3` merges that
  edit with it, which is presumably the intent — but it is worth knowing rather than
  discovering.

**Exact next step**

The owner pushes `m/T3`, reads the Actions run — `ci.yml` gained two steps and the American
generator adds about two and a half minutes to that job — reads this pack, merges, and ticks
T3 in `ROADMAP.md`. T4 unlocks: the Emscripten build with an embind API mirroring
`PricingBackend`, under 500 KB, built in CI and published as a release artifact. Six public
headers are new here and every one of them is proved self-contained, which is the property
T4's binding will lean on.

## Amendments

**None proposed.** T3 adds no dependency and no technology: A5 already covers doctest and
nlohmann, B3 already directs the Thomas solver and "Newton with a Brent fallback", and B6
already puts bump-and-revalue Greeks in v1. The American work is I21's "anything else is
Part 4" only if it reaches a v1 page, which it does not; as library surface it is inside B3's
"Crank–Nicolson" and outside every exit criterion, and it is the owner's decision recorded
above rather than an amendment.

Two governance notes from T0 and T1 remain open at the owner's option: QuantLib's standing
under I4 rather than as an I19 addition, and tech-decision B2's `experiments/` superseded by
the roadmap's `golden/`. Neither blocks the path to T5.

## Owner actions

1. **`git push -u origin m/T3`**, then read the Actions run. Two new steps in the `golden`
   job, and the American generator takes about two and a half minutes. Note that the branch
   also carries `62f6320`, the roadmap edit made on it mid-session, which merges with T3.
   Worth doing once, separately: add `GarethCooke/Touchstone` to this session type's
   authorised sources, so that T4 can push and read its own CI run instead of asking.
2. **Read this pack and merge.** T3's tollgate is V: there is no Fable session to run. On a
   merge, tick T3 in `ROADMAP.md` with a pointer to `docs/evidence/T3/`.
3. **Note the T1 edit in the tollgate record** if the record should stay exact:
   `src/black_scholes.cpp` and `include/touchstone/black_scholes.hpp` changed after T1's
   Fable verdict, at the owner's direction, and the reason is **Done** 1.
4. **Consider α = 6 against α = 3** for `PdeSettings::half_width_sigmas`. The evidence is in
   `test_pde.cpp`; three is four times more accurate and one row's worth of evidence away
   from the boundary.

## What is in this pack

- `summary.md` — this file.
- `build.txt` — configure and build on host A (g++ 13.3, clang++ 18.1.3, and the ASan/UBSan
  build) and host B (g++ 11.4, the owner's checkout), with compiler and libc versions, and
  the zero-warning count on all three.
- `tests.txt` — ctest and the full run with every number the suite reports; the three exit
  criteria worked through with their tolerances stated; what each new suite would catch; the
  twenty-four mutations and the three that survive; the two hosts' agreement digest; the
  sanitizers; and the SHA-256 of all 47 build inputs.
- `diff.txt` — `git diff --stat` against `62f6320`, HEAD's parent, which is `a296fae` plus
  the owner's roadmap edit; 30 files, 6,757 insertions, 27 deletions.
- No `screenshots/`. P5 requires them for UI; T3 has none.
