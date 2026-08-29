# T1 — Core: closed form and analytic Greeks · evidence pack

## Work order (P3)

**Goal.** T1 as the roadmap states it: a CMake project; the Black–Scholes closed form with a
dividend yield; analytic delta, gamma, vega, theta and rho; `N(x)` via `std::erfc`; tests
against the golden file to 1e-10, put–call parity, and the σ→0 and T→0 limits; GitHub Actions
on GCC and Clang with warnings as errors. Exit: CI green on both compilers, every named test
present.

**Steps.** Branch `m/T1` · vendor the two single headers the tests need · CMake with
warnings-as-errors and a header self-containment guard · `normal.hpp`, then the closed form ·
the four test suites · the workflow · an adversarial review of the numerics by a second
session · fix what it found · evidence.

**Decisions taken before starting**, all three put to the owner in-session: doctest vendored
as a single header rather than fetched; nlohmann/json vendored likewise, for the test target
only; and the CI criterion proved locally on both compilers with the workflow committed,
because this session has no credentials for the remote. Reasoning in **Decisions** below.

---

### 2026-08-29 · claude-opus-5 · Closed form and six analytic Greeks agreeing with QuantLib on 7234 rows to 3e-13, green on three compilers and under ASan/UBSan, with the domain it will not price stated and enforced

**Done**

1. **Branch and vendoring.** `m/T1` off `2926289`. `third_party/` holds doctest 2.4.12 and
   nlohmann/json 3.12.0 as single headers, each with its URL, licence and SHA-256 recorded in
   `third_party/README.md`. Both are behind a `touchstone_vendor` INTERFACE target that
   carries them as SYSTEM includes, so this project's warnings apply to this project's code
   and to nothing else. Only the test executable links it.

2. **CMake project.** C++20, no extensions, `RelWithDebInfo` by default. `touchstone` is a
   static library with `include/` as its only public surface. Warnings live in one INTERFACE
   target: fourteen of them plus `-Werror`, including `-Wconversion`, `-Wsign-conversion`,
   `-Wold-style-cast` and `-Wdouble-promotion`. An MSVC branch exists so the owner's Windows
   checkout configures; nothing has compiled it and nothing claims it works.

3. **A header self-containment guard**, following DepthCharge. CMake generates one
   translation unit per public header that includes only that header. A header that quietly
   depends on something its includer happened to pull in first fails at T1 rather than at T4,
   in the Emscripten binding, which is the least convenient place to find out.

4. **`include/touchstone/normal.hpp`.** `norm_pdf` and `norm_cdf`, the latter as
   `0.5 * erfc(-x/√2)` per tech-decision B3, with the reason for that route written where the
   next reader will need it: `1 - N(-x)` returns exactly zero at x = −10, where the true value
   is 7.6e-24.

5. **`include/touchstone/black_scholes.hpp` and `src/black_scholes.cpp`.** 262 lines of
   implementation. `EuropeanVanilla` (the contract) and `BlackScholesMarket` (what is
   observed) are separate types; `PriceAndGreeks` carries all seven values from one
   evaluation; seven single-value accessors exist for callers that want one. Every output is
   a raw partial derivative in `golden/SCHEMA.md`'s units.

   The seven expressions in `price_and_greeks` are that document's formulas verbatim, with no
   branch in them. Everything conditional lives in one `Kernel` struct, which is where the two
   singular quantities are computed — gamma, which divides by S and by the total volatility,
   and theta's diffusion term, which divides by √T.

6. **The σ→0 and T→0 limits are derived rather than approximated.** When σ√T is zero the
   terminal distribution is a point at the forward, `N(w d₁)` and `N(w d₂)` both tend to the
   indicator of finishing in the money, and to one half at the forward itself, where
   d₁ → v/2 → 0. Six of the seven outputs follow from that. The two that do not:

   - **gamma diverges** at the strike, and `+∞` is returned because that is the limit.
   - **vega does not.** This is the one that is easy to get wrong by treating "σ = 0" and
     "T = 0" as one degenerate case. With T still positive, a first unit of volatility buys
     `S e^{-qT} √T φ(0)` of option value — 38.7 at the values the test uses — and the limit is
     that number, not zero. With T zero it is zero. The code distinguishes them.
   - **theta's decay term** is zero when σ = 0 and `-∞` at expiry at the strike. σ = 0 *and*
     T = 0 together is an order-of-limits question with no answer; the order is chosen in the
     open and tested (**Decisions**).

7. **Four test suites, 22 cases, 255,999 assertions, about a third of a second.**
   `closed-form` sweeps all 7234 golden rows × 7 fields at the tolerances the file itself
   carries, reporting the worst scaled error per field whether it passes or fails.
   `parity` checks put–call parity and the six identities the Greeks inherit from it, reading
   the golden file for its parameter sweep and for nothing else — every number it compares is
   one this library produced, so it would fail even if the oracle were wrong about every row.
   `limits` is the σ→0 and T→0 work above. `normal` covers `N(x)` including the far tail.
   Five ctest entries: one per suite so a red run names the misunderstanding, plus one that
   runs the whole binary so a mistyped filter can leave a suite unregistered but never unrun.

8. **Every tolerance in the suite is a measured bound with a reason, not a number that
   passed.** Six assertions failed on the first run, all of them mine rather than the
   library's, and each was replaced by the conditioning of the quantity:

   - `N(x)`'s relative accuracy is limited by the rounding of *x*, not by `erfc`. The input is
     uncertain by |x|·ε/2 and that arrives amplified by |d ln N/dx| = φ/N, which grows like
     |x|. The bound is therefore `(4 + x²)·ε`, and the observed errors sit an order inside it
     at x = −3, −10 and −30.
   - Parity's bound is 1e-13, not the 1e-14 first tried, because the identity is a difference
     of two numbers of order S: one ulp of the grid's largest spot is 2.8e-14. Worst observed
     1.4e-14, at S = K = 80.
   - `N(x) + N(−x) − 1` is bounded by ε, one ulp of 1.0, and observed at ε/2 — the smallest a
     sum near 1 can be wrong by.

9. **GitHub Actions.** Three jobs. `build` is the matrix the roadmap names: GCC and Clang on
   ubuntu-24.04, warnings as errors, configure, build, ctest. `golden` picks up the two checks
   T0's pack recommended for T1 — the verifier on every row, and a regeneration that requires
   `git diff --exit-code` to be clean. `sanitizers` runs the suite under ASan and UBSan.

10. **The regeneration check was tested before it was made blocking.** T0 proved the golden
    file reproducible by hand on one machine; a check that requires byte-identity on GitHub's
    runners is only worth having if byte-identity survives a change of machine. It does:
    regenerating on Ubuntu 24.04 in this session's container, from the committed lockfile,
    produced SHA-256 `938ed1bb…0334` — the same digest T0 recorded. Recorded in `tests.txt`
    §6, and it independently confirms T0's claim on a second platform.

11. **An adversarial review by a second session, and eleven fixes from it.** A fresh session
    was given `golden/SCHEMA.md` and the sources and asked to find errors rather than confirm
    the work. It re-derived every formula, mutated the implementation to test whether the
    suite would notice, and searched the input domain for NaNs. It found the transcription
    correct and eleven of its mutants killed, and it found seven real problems. All seven are
    fixed:

    | What it found | Why it mattered | Fix |
    |---|---|---|
    | `K e^{-rT}` was computed before the "nothing against nothing" guard | `0 × ∞` is NaN, so the guard shipped a poisoned kernel and the zeros it promised never happened | Guard moved above all arithmetic |
    | The degenerate branch decided "at the forward" on `S e^{-qT} − K e^{-rT} == 0` | Not the quantity d₁ sees. With S = 0 and a long enough expiry both terms underflow to zero, so a put priced its delta at −0.5 where the answer is −1 | Both branches now decide on `ln(S/K) + (r−q)T`, the numerator of d₁ |
    | `else` was reached whenever σ ≠ 0, but commented "T == 0" | σ√T can underflow with both positive. theta returned −∞ where the true value is −2e-249 | Three-way branch on σ, then T, then the formula |
    | gamma formed `S·v` then divided | The product underflows for a small enough spot, so gamma returned `+∞`, or `0/0`, where the true value is 1.5e134 | Two divisions instead: `φ/S/v` |
    | The at-the-forward test used r = q | Every mutation confined to that path survived, and its theta assertion was true for any coefficients | An approach sweep with r ≠ q pinning delta, vega and gamma's coefficient |
    | gamma and theta's divergences were asserted only as `isinf` | Catches "forgot to diverge", not "diverged when it shouldn't" — which is exactly what two of the bugs above did | Sweeps: `γ·S·σ√T → e^{-qT}φ(0)` and `θ·√T → −Sφ(0)σ/2` |
    | Six inputs in the documented domain returned NaN | All from overflow — `e^{-rT}`, `S e^{-qT}`, `S/K`, `T·K e^{-rT}` — and a NaN compares false against every tolerance a caller might write | The domain is now stated and enforced: see **Decisions** |

    Each fix was then checked by putting the defect back. Reverting the log-moneyness branch
    fails 2 assertions, the decay branch 2, gamma's two divisions 1042, and the domain check
    1026 — so none of these is a change with no test behind it. The guard-ordering fix is the
    exception and is named as one: once the domain check landed, a discount factor can no
    longer be infinite, so `0 × ∞` is unreachable and the guard is belt-and-braces rather than
    load-bearing. Numbers in `tests.txt` §8.

    Three of its findings were left as they are, deliberately, and all three are recorded under
    **Not done**.

12. **The domain the library will price is now part of the contract.** `require_valid` checks
    the financial conditions it always did, and now also that the six products the formulas
    form are representable: the two discount factors, the discounted spot and strike, the
    moneyness S/K, T times each discounted quantity, and r and q times them. Accepting an
    input is a promise that no output will be NaN — held to a 25,920-point sweep across the
    boundary of that domain, with spots and strikes from 1e-300 to 1e300, vols from 1e-300 to
    1e100 and expiries from 1e-300 to 1e300. 16,570 priced, no NaN in any of seven outputs;
    9,350 rejected with a message that names which product overflowed; 550 with the infinite
    gamma the mathematics has at the strike.

13. **Green on three compilers and two machines.** GCC 11.4 on the owner's checkout, GCC 13.3
    and Clang 18.1.3 in this session's container, all with `-Werror`; and the whole suite
    again under ASan and UBSan with `-fno-sanitize-recover`, clean. The worst scaled error per
    field is identical to four significant figures on all three, and the domain sweep
    classifies all 25,920 inputs identically. `tests.txt` §5 carries the SHA-256 of all
    sixteen files on both machines, so the Clang result is a result about this checkout.

14. **README updated.** It said "there is no C++ in this repository"; it now says what the
    library does, at the level that is demonstrated, and what each ctest entry would catch.

**Decisions (with why)**

- **doctest, vendored as a single header.** *Owner chose in-session.* Tech-decision B1 says
  "whatever Anvil uses, for consistency; Catch2 if there's no precedent to follow" — and there
  is a precedent: Anvil and DepthCharge both use doctest. Committing the header rather than
  fetching it at configure time keeps builds reproducible offline and byte-pinned; I17 forbids
  submodules, and a `FetchContent` pull would put the network on the critical path of every CI
  run.
- **nlohmann/json, on the same terms, test target only.** *Owner chose in-session.* The golden
  file is JSON and C++20 has no parser. The alternative — a purpose-built reader for a file
  written one row per line — would be untested code sitting between the oracle and every
  assertion in the suite, where a bug could mask a pricing failure rather than reveal one.
  Reading the file as written also means `SCHEMA.md` stays the contract: the tolerances, the
  counts and the schema id are read from the file rather than restated in the tests. This
  follows DepthCharge's `dc_engine_anvil` pattern, where the one target that touches nlohmann
  is the one target that must never reach the constrained platform. **An I19 amendment is
  proposed below**; the owner's in-session choice is the stronger authority either way.
- **The contract and the market are separate types.** `EuropeanVanilla{strike, expiry, type}`
  and `BlackScholesMarket{spot, vol, rate, dividend_yield}` rather than one flat struct. A
  strike is agreed; a volatility is observed. The distinction earns its keep at T3, where
  implied vol solves for `market.vol` given a price and the contract is what stays fixed, and
  at T5, where the write-up has to explain the difference anyway. *Decision — owner may
  overrule*, though every call site would change.
- **A compiled static library, not header-only.** T2 and T3 add Monte Carlo and a PDE solver,
  which want translation units; a static library is also the natural link target for T4's
  embind wrapper. Header-only would push all of that into headers and pay for it in every
  consumer's compile time, including the Emscripten build with its 500 KB budget.
- **The singularities live in `Kernel`, not in the formulas.** The seven expressions in
  `price_and_greeks` read exactly as `SCHEMA.md` writes them, which is what makes them
  checkable line by line against the document. Everything conditional is in one place, and the
  price of that is one `exp` computed by `price()` that `price()` does not use. Measured
  against the alternative — seven functions each carrying the degenerate branch — this is the
  right trade at this size. *Decision — owner may overrule*; if T3's bump Greeks profile badly,
  an unchecked fast path is the answer, not a fatter API.
- **Out-of-domain inputs throw; they do not return NaN.** A NaN compares false against every
  tolerance a caller might test it with, so a silent NaN is worse than a loud stop: it fails
  the check that was meant to catch it. The check is one `if` per pricing call and two
  `exp`s duplicated with the kernel. *Decision — owner may overrule.* It has one consequence
  worth flagging now: exceptions cost binary size under Emscripten, and T4 has a 500 KB
  budget. If that bites, the answer is a `_nothrow` variant, not silence.
- **Infinities are returned where the limit is infinite.** gamma at the strike as σ√T → 0,
  and theta at expiry at the strike. `+∞` is the limit; a NaN would not be, and a large finite
  number would be a lie. An infinity also compares correctly against a tolerance, which a NaN
  does not.
- **σ = 0 and T = 0 together: no diffusion wins.** The double limit does not exist — σ→0 then
  T→0 gives a decay term of zero, the other order gives −∞. With no volatility there is no
  time value to lose, whatever the expiry, so zero is returned. The decision is stated in the
  code and has its own test rather than being an accident of branch order.
- **No `-ffp-contract` flag.** GCC and Clang contract differently, so the same expression can
  land on different last ulps. I6 settles it: "Agreement is to stated tolerances, never
  bit-exact." Adding a flag to chase bit-identity would be paying for a property the
  constitution does not ask for — and in the event, all three compilers agree to four
  significant figures on every reported number anyway.
- **`DOCTEST_CONFIG_VOID_CAST_EXPRESSIONS`.** Every entry point is `[[nodiscard]]`, and
  `CHECK_THROWS_AS` discards its expression. This is doctest's own switch for that, and it
  casts to void, which is what the standard blesses as deliberate. The alternative is a
  `static_cast<void>` at every such call site.
- **A sanitizer job in CI, which nothing requires.** Not named in the roadmap or in B7. It is
  cheap, it is proven green here, and T2's Monte Carlo — buffers, indices, a hand-written RNG
  — is exactly the code that wants it already in place rather than added after the first
  mysterious failure. Its own job, so a failure names itself. *Decision — owner may overrule.*
- **The golden regeneration check is blocking, not advisory**, because it was tested first on
  a machine unrelated to the one that generated the file. Had the bytes differed, it would
  have gone in as advisory with the platform-dependence recorded as a finding.

**Not done**

- **The branch is committed but not pushed, so CI has never run.** This is the one exit
  criterion not demonstrated, and it is the same wall T0 hit: this session reaches the
  repository through a mount of the Windows folder, and the owner's GitHub credentials live in
  Windows' credential manager, which the mount does not expose. `git push` fails with
  `could not read Username for 'https://github.com'`. No credential was sought or supplied by
  other means. What *is* demonstrated is the substance of the criterion — both compilers
  green with warnings as errors, on two machines, on byte-identical sources. What is not is
  that the workflow file itself runs, which no local evidence can establish. `git push -u
  origin m/T1` and one look at the Actions tab closes it.
- **MSVC and Emscripten are not built.** The MSVC warning branch in `CMakeLists.txt` exists so
  the owner's Windows checkout configures rather than dying on unknown flags. It is not
  exercised and nothing claims it works. Emscripten is T4.
- **Two review findings left as they are, deliberately.**
  - `std::log(s / k)` forms the quotient before the logarithm, so a moneyness that overflows
    a double loses the ratio. `require_valid` now rejects exactly those inputs rather than
    pricing them. The apparent fix — `log(s) − log(k)` — would be worse where it matters:
    those two logarithms agree in every digit near the money, and the subtraction would lose
    precision across the whole of the useful domain to buy accuracy across none of it.
  - At the forward, `S e^{-qT}` and `K e^{-rT}` are the same number by construction, so no
    test at the forward can tell an implementation that uses one from an implementation that
    uses the other. The review found mutants exploiting this; they are unobservable rather
    than uncaught. Said plainly in `test_limits.cpp` beside the assertion that cannot be
    written.
- **`n₁` and `n₂` are not distinguished by the limits suite**, because both equal the
  indicator on the degenerate branch. `closed-form` distinguishes them on 7200 rows, where
  swapping them fails immediately. Recorded because a reader of `test_limits.cpp` alone might
  believe otherwise.
- **No performance measurement.** Nothing in T1 asks for one and no claim here rests on speed.
  T4's size budget and T2's path counts are where it starts to matter.
- **No install or export targets, no `find_package` support.** The only consumers are this
  repository's tests, T4's Emscripten build, and the site's vendored artifact. None of them
  needs one, and I17 forbids the arrangement that would.
- **Carried over from T0, unchanged.** `docs/rng.md` is still absent — amendment A4 brings it
  at T2. The constitution's companions list still names `docs/index-v1.md` where the file is
  `docs/quant-learn-index-v1.md`. `_to_delete/` at the repository root is still 279 MB and
  still un-deletable from this session's mount.

**Exact next step**

The owner pushes `m/T1` and confirms the Actions run is green on both compilers. T1's tollgate
is **F**, so a fresh Fable session then receives §6's prompt verbatim with this pack. On a
pass, tick T1 in `ROADMAP.md` with a pointer here; T2 unlocks, and it needs L0's `docs/rng.md`
and its known-answer fixture copied in under amendment A4 as its first act.

---

## Exit criteria

| Criterion | Result | Evidence |
|---|---|---|
| CI green on both compilers | **pending push** | The workflow is committed and both compilers are green with `-Werror` on two machines over byte-identical sources — `build.txt`, hosts A and B; `tests.txt` §5. No Actions run has happened because the branch cannot be pushed from this session: see **Not done**. This is the only criterion not closed. |
| Every test named in the deliverables present | **pass** | Golden file to 1e-10: `test_closed_form.cpp`, 7200 rows × 7 fields, worst 2.8e-13 — `tests.txt` §2–3. Put–call parity: `test_parity.cpp`, 3617 pairs, seven identities, worst 1.4e-14. σ→0 and T→0 limits: `test_limits.cpp`, both limits derived independently and approached as well as evaluated. |

## Deliverables

| Deliverable | Result | Where |
|---|---|---|
| CMake project | **pass** | `CMakeLists.txt`, `tests/CMakeLists.txt`, `third_party/CMakeLists.txt`. C++20, warnings as errors on GCC and Clang, five ctest entries, a header self-containment guard. |
| Black–Scholes closed form with dividend yield | **pass** | `src/black_scholes.cpp`. Agrees with QuantLib on 7234 rows; worst price error 1.2e-13 against a 1e-10 tolerance. |
| Analytic delta, gamma, vega, theta, rho | **pass** | All five, plus `dividend_rho` because the golden file carries it and T3's bump Greeks will need it. Worst error 2.8e-13, in `dividend_rho`. |
| `N(x)` via `std::erfc` | **pass** | `include/touchstone/normal.hpp`. `0.5 * erfc(-x/√2)`; `test_normal.cpp` demonstrates that the alternative loses the left tail. |
| Tests: golden file to 1e-10 | **pass** | `tests.txt` §3 — the margin table, field by field. |
| Tests: put–call parity | **pass** | `test_parity.cpp` — parity and the six Greek identities, plus parity re-established on the degenerate branch. |
| Tests: σ→0 and T→0 limits | **pass** | `test_limits.cpp` — 573 lines. Both limits, the at-the-forward cases, the divergence rates, and the domain sweep. |
| GitHub Actions on GCC and Clang with warnings as errors | **pass (committed, unrun)** | `.github/workflows/ci.yml`. Three jobs: the two-compiler matrix, sanitizers, and the golden-file check. Valid YAML, structure verified; no run yet, per **Not done**. |

## Invariants exercised

- **I4** — nothing links QuantLib. The library's only inputs are doubles; the oracle is a
  committed JSON file, and the one place it is produced is still `golden/generate_bs_vanilla.py`.
- **I6** — no randomness at T1, and nothing here is asserted bit-exact. Every comparison is to
  a stated tolerance, and each tolerance is the conditioning of the quantity rather than a
  number that happened to pass.
- **I19** — the stack as named: C++20, CMake, GCC and Clang, GitHub Actions. The two vendored
  headers are the exception, and an amendment is proposed for them below rather than assumed.
- **I20** — three-way agreement is not yet exercisable; T2 and T3 supply the other two ways.
  What T1 adds to T0's one independent agreement is a second: the closed form against QuantLib
  on 7234 rows, in C++ this time, at a few hundred times inside the required tolerance.
- **I21** — scope exactly as fixed: European vanillas, one underlying, constant rate and
  volatility, dividend yield. Nothing else is priced and nothing else is stubbed.
- **I18** — nothing outside `touchstone` was written. `touchstone-learn` was not touched.
- **I3** — no snippet from this milestone is shown anywhere yet; when L1's D6 and T5's
  write-up quote this code, they will quote files that run in CI.
- **P2** — T2's work was not begun. The RNG is absent, `docs/rng.md` is absent, and no Monte
  Carlo scaffolding was added in anticipation.
- **P4** — three decisions were put to the owner in-session, at the top. The rest are
  reversible and marked where they may be overruled. Nothing irreversible or public-facing was
  decided: no licence, hostname, visibility or spending change, and no push to `main`.

## Amendments proposed

**One.** In §8's format, for the owner or the tollgate to accept or reject:

> **A5** · 2026-08-29 · I19 · library stack is "C++20, CMake, GCC and Clang, Emscripten,
> GitHub Actions" → the same, plus doctest and nlohmann/json vendored as single headers in
> `third_party/`, linked by the test executable only and reachable from neither
> `include/touchstone/` nor the WASM artifact · reason: I19 requires additions to be
> amendments; tech-decision B1 already directs the choice of test framework to "whatever Anvil
> uses", and the golden file is JSON, which C++20 cannot read without either a dependency or
> an untested parser of our own sitting between the oracle and every assertion · authority:
> owner, in-session during T1, to be confirmed at this tollgate.

Nothing else. Two governance notes from T0 remain outstanding and are the owner's to formalise
if wanted: QuantLib entering under I4 rather than as an I19 addition, and tech-decision B2's
"in `experiments/`" being superseded by the roadmap's `golden/`.

## Owner actions

1. **`git push -u origin m/T1`**, then confirm the Actions run is green on both compilers.
   That closes the one open exit criterion. This session had no credentials for the remote,
   as at T0.
2. **Run the F tollgate.** A fresh Fable session, §6's prompt verbatim, this pack.
3. **Accept or reject amendment A5**, and re-upload `CONSTITUTION.md` to the Claude Project if
   it is accepted.
4. **Still outstanding from T0:** delete `_to_delete/` (279 MB) and the `tmp_obj_*` files under
   `.git/objects/`; this session's mount refuses every unlink, so they are still there. One
   file was added to `_to_delete/gitlocks/` during this milestone: a stale `.git/index.lock`
   left by an earlier interrupted git call, which had to be moved aside rather than removed
   before the commit could be made. Nothing in the repository references any of it.

## What is in this pack

- `summary.md` — this file.
- `build.txt` — configure and build on host A (GCC 11.4, the owner's checkout) and host B
  (GCC 13.3, Clang 18.1.3, and the ASan/UBSan build), with the compiler and libc versions.
- `tests.txt` — ctest; the full doctest output with the worst scaled error per field; the
  margin table; what each suite would catch; the SHA-256 of all sixteen build inputs on both
  hosts; the golden file regenerated byte-identically on a third platform; T0's verifier re-run.
- `diff.txt` — `git diff --stat` against `2926289`, the milestone's base. 2,646 insertions
  and 9 deletions across 20 files outside the two vendored headers; those two account for
  another 32,660 lines and are not this session's code.
- No `screenshots/`. P5 requires them for UI; T1 has none, and will not until L1 renders D6.
