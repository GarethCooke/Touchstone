# T5 — Architecture write-up and v1.0.0 · evidence pack

## Work order (P3)

**Goal.** T5 as `ROADMAP.md` states it, which governs: `ARCHITECTURE.md` as the golden source
for the portal page, in the DepthCharge style, carrying measured timings for the five entry
points with the machine they were taken on, and the milestone and review history that the
source comments then leave out; README final; `v1.0.0`. Exit: every claim in
`ARCHITECTURE.md` maps to a test or a file; CI green; tag pushed. Tollgate F, a
bounded-claims review as for Temper's page. One session, this milestone only (P2).

**What the ROADMAP entry does not carry, quoted from the owner's instructions for this
session** (from the audits of T3a and T4):

> What T5 is for. ARCHITECTURE.md is the golden source the portfolio's architecture page will
> be rendered from (P2), and the tollgate is a Fable review of bounded claims: a reader should
> be able to tell in thirty seconds that nothing is claimed beyond what is demonstrated. The
> test of every sentence is whether a named test or file holds it.
>
> 1. Style. Read C:\Development\Projects\DepthCharge\ARCHITECTURE.md for the form and
>    C:\Development\Projects\Temper\ARCHITECTURE.md for the register. Both are read-only
>    (I18). If either is missing, say so and work from the ROADMAP's wording.
>
> 2. Claims map. Put docs/evidence/T5/claims.md in the pack: every claim in ARCHITECTURE.md,
>    numbered, against the test or file that holds it. Before you finish, have an agent that
>    did not write the document check each row against its citation, and record what it found
>    and what you changed. The tollgate checks this file row by row.
>
> 3. Timings (ruling 7). The five entry points are price_and_greeks, implied_vol,
>    bump_greeks, monte_carlo and crank_nicolson, at their defaults and a stated base case.
>    Commit the harness that takes them, with no new dependency (I19);
>    docs/evidence/T3a/timing.txt has an earlier one. Put its raw output in the pack with the
>    machine, compiler, flags and method. ARCHITECTURE.md states them as one machine's numbers
>    on one date. Measure only: no fast path, no tuning. Claim nothing for the WebAssembly
>    build unless you measure it the same way. F4: the "about eight milliseconds" in pde.hpp
>    is replaced by the measurement or cut.
>
> 4. History out of the comments (ruling 8). Milestone, tollgate, review and governance ids
>    leave the comments, and their history goes into ARCHITECTURE.md together with what T3a
>    already removed (history.md). By grep on main: 14 lines in 6 files under include/ and
>    src/, 25 in 11 test files, one in CMakeLists.txt, two in ci.yml. Ruling 8 names include/
>    and src/; do the other three places the same way. The reasoning stays where it is. A
>    reference to the tutorial, a page or a demo, is not history, as T3a left it.
>
> 5. Three pairs, decided together. require_valid, crank_nicolson and
>    crank_nicolson_surface in pde.hpp and pde.cpp are each written twice, once per exercise
>    style, forwarding to one template. Fold each to one declaration if every call site and
>    test compiles unchanged and the header reads at least as clearly. If not, leave them and
>    give the reason in ARCHITECTURE.md as a design decision.
>
> 6. defaults() in the binding carries four of the five settings types. Add the surface
>    sampling's, and its key to the smoke test.
>
> 7. F6. Add an .editorconfig that states what the sources already do. Add a .clang-format
>    only if clang-format then changes nothing in include/, src/, tests/ and wasm/; otherwise
>    leave it out and say so. No reformatting commit.
>
> 8. README final: no "In progress". It describes the library as released and points to
>    ARCHITECTURE.md. T5's status row reads "in review"; the owner's tick changes it.
>
> 9. Version. CMakeLists.txt goes to 1.0.0, because the release job holds the tag to it. Do
>    not create or push a tag, open a PR or merge (P4, P6): the tag follows the tollgate. In
>    the exit table, mark "tag pushed" as the owner's, after the tollgate.
>
> Standing rules, from the rulings note: no repeated code, tests included; common code is
> common; new and changed comments give reasoning, not history; the library's own rules
> stand. Every number the native suite, the golden file and the smoke test hold must be
> unchanged; say how you checked.

**Read first (P1):** `CONSTITUTION.md`; `ROADMAP.md` (T5); `docs/evidence/T4/summary.md`;
`docs/briefs/T3a-design-rulings.md` (rulings 7 and 8, the smaller defects);
`docs/evidence/T3a/history.md`; both reference documents, which exist and were read, not
edited.

**Steps.** Branch `m/T5` from `74987c7`.

1. Baselines before any edit: the native suite with every assertion printed, the Release
   library's object files, the WebAssembly artifact and its smoke test, all on main.
2. The three pairs: a compiled probe of what folding does to overload resolution, then the
   decision.
3. The timing harness in `bench/`, standard library only; three pinned runs on an idle
   machine; the raw output, machine, compiler, flags and method in `timing.txt`.
4. History out of the comments in `include/`, `src/`, `tests/`, `CMakeLists.txt` and
   `ci.yml` (and the one `wasm/` line), every removed text kept for `ARCHITECTURE.md`; F4.
5. `defaults()`'s fifth key; `.editorconfig` measured before written; `.clang-format` tried
   against the condition.
6. `ARCHITECTURE.md` in DepthCharge's form and Temper's register; README final; 1.0.0.
7. The claims map, then an independent check of every row by an agent that did not write
   the document, its findings recorded and closed.
8. Every number unchanged, shown four ways; evidence; push; read CI on the final commit.

---

### 2026-11-14 · claude-opus-5-5 · ARCHITECTURE.md with 138 mapped claims, each checked against its source, five entry points timed on one machine, history out of the comments, and 1.0.0 — with every object file and every printed assertion as main had them

**Done**

1. **`ARCHITECTURE.md`**, in DepthCharge's numbered form: what this is, with what is claimed
   and what is not, up front; system overview; repo layout; the public surface; how each
   method is built; the library's invariants, each with why and what holds it; timings;
   decisions with rationale; out of scope; history; changes to the document. Temper's
   register: bounded, "the claim is never … it is …".
2. **The claims map**, `claims.md`: 138 rows, every claim in the document in order, each
   against the test or file that holds it and labelled asserted, reported or source. An
   agent that had not written the document checked the first 129 adversarially: 9 did not
   hold and 26 needed correcting, and it found nine unmapped sentences, now rows 130–138.
   Every finding was verified against the code and every one is closed (**The claims
   check**, below).
3. **Timings** (ruling 7), `bench/timing.cpp`: the five entry points at their defaults on a
   call struck at 100, one year, S = 100, σ = 0.2, r = 0.05, q = 0.02; batches of at least
   20 ms, 25 rotated rounds, three processes pinned to one core at high priority. On a Ryzen
   7 3800X, g++ 15.2 `-O3`, 2026-11-14: `price_and_greeks` 74–76 ns, `implied_vol`
   336–349 ns, `bump_greeks` 1.39–1.41 µs, `monte_carlo` 1.78–1.79 ms, `crank_nicolson`
   4.71–4.74 ms (`timing.txt`, raw output included). Standard library only; built with the
   tests under the same warnings; never run by ctest. Nothing tuned. The WebAssembly build
   was not timed and nothing is claimed for it. F4: pde.hpp's "about eight milliseconds" is
   cut — it was 4.7 ms here — and the header points to `ARCHITECTURE.md`.
4. **History out of the comments** (ruling 8): 48 lines on main (`build.txt` §3, every one
   listed) in `include/`, `tests/`, `CMakeLists.txt`, `ci.yml` and one in `wasm/`; none
   remain. Each comment keeps its reasoning; three test-case names and one test message that
   carried milestone ids are renamed. The claims check found one more, outside the grep's
   scope: `third_party/CMakeLists.txt`'s "the WASM artifact at T4", now corrected.
   `ARCHITECTURE.md` §10 has the milestones, the reviews and what they changed, and every
   removed text, T3a's and this session's.
5. **The three pairs stay** (Decisions).
6. **`defaults()` carries `surfaceSampling`**, and the smoke test expects five keys and its
   value, `{ everySteps: 1 }`.
7. **F6.** `.editorconfig`, every property measured on the files it covers before it was
   written, then checked: 178 files, 0 failures (`build.txt` §7). **No `.clang-format`**:
   the closest of four configurations still rewrites 46 lines in 14 files — hand-aligned
   coefficient tables and continuation lines — and the condition was zero (`build.txt` §6,
   the configuration and its whole remaining diff).
8. **README final**: no "In progress"; describes 1.0.0; points to `ARCHITECTURE.md` and the
   claims map; T5 "in review". It also corrects a figure: "agreeing with QuantLib on 7234
   committed reference rows to better than 3e-13" was true of the 7,200-row grid
   (2.84e-13) and not of the 34-row edge block, whose worst is theta at 1.62e-11
   (`tests.txt` §1). Both are now given. And "whose demos run on it" was the plan, not the
   state: the demos run on the TypeScript backend until L5. Both sentences now say so.
9. **Version 1.0.0** in `CMakeLists.txt`. No tag, no PR, no merge.
10. **Every number unchanged, four ways** (`tests.txt` §2): the seven library object files
    at `-O3` byte-identical to main's; all 4,140,490 assertions printed with their values
    at main and at the head, 14,407,953 lines each, identical but for the three renames;
    the smoke test's output identical but for durations; `golden/`, `experiments/` and
    `docs/rng.md` untouched.

**Exit criteria**

| Criterion | Result |
| --- | --- |
| Every claim in `ARCHITECTURE.md` maps to a test or a file | **PASS** — `claims.md`, 138 rows; the independent check's 9 failures and 26 corrections closed, its 9 unmapped sentences mapped (**The claims check**) |
| CI green | *Pending — the run on the final commit* |
| Tag pushed | **OWNER'S, after the tollgate** (P4, P6). CMake says 1.0.0, which `release.yml` holds the tag to. Commands under **Exact next step**. |
| Deliverable: `ARCHITECTURE.md`, DepthCharge style, golden source for the portal page | **DONE** |
| …with measured timings for the five entry points and the machine | **DONE** — §7; `timing.txt` |
| …with the milestone and review history the comments leave out | **DONE** — §10 |
| Deliverable: README final | **DONE** |
| Brief 4: no milestone, tollgate, review or governance id in the comments | **PASS** — `build.txt` §3: the grep is empty at the head |
| Brief 5: the three pairs decided | **DONE** — left, reason in `ARCHITECTURE.md` §8 |
| Brief 6: `defaults()` with the fifth key | **PASS** — smoke test, 17 of 17 |
| Brief 7: `.editorconfig`; `.clang-format` only if it changes nothing | **DONE** — no `.clang-format`, and why |
| Standing: every number unchanged | **PASS** — four checks, `tests.txt` §2 |
| Standing: no new dependency (I19) | **PASS** — the harness includes the standard library and the library only |

**Decisions (with why)** — each *Decision — owner may overrule*:

- **The three pairs stay pairs.** Folding `require_valid` into a template is unsafe here:
  `bump_greeks.hpp` declares a three-argument `require_valid` taking `BumpSizes`, so in a
  file with both headers `require_valid(option, market, {})` is today ambiguous and does not
  compile, and after a fold it would compile and validate bump sizes, because a non-template
  wins a tie. The probe shows both, on g++ 15.2 and clang 22.1.7 (`build.txt` §4).
  `crank_nicolson` and `crank_nicolson_surface` have no such neighbour, but the brief asks
  for the three decided together, and a header where the validator is a pair and its two
  solvers templates reads as though the validator differed. No logic is repeated: each pair
  is two one-line forwarders to one template. The folded solvers were not built.
- **Governance named without an id counts as history too.** Besides ids, the comments named
  the roadmap, the constitution and tech-decisions as the authority for a choice (three
  lines with no id). Each now states the reason instead; the counts in `build.txt` §3 are
  therefore wider than the owner's 14/25/1/2, and every line is listed. Kept, as not
  history: references to the tutorial, its pages and demos; `tests/rng_fixture.hpp`
  reporting `docs/rng.md`'s own word, "amendment", for regenerating its fixture.
- **Test-case names and one test message are comments for this purpose.** Three names and
  the three-way report's opening words carried milestone or invariant ids and would have
  printed them on every run; they are renamed, and that is the whole of the difference in
  the suite's output.
- **F4 is cut, not replaced in the header.** A time belongs with its machine and date, and
  a header outlives both; pde.hpp now points to `ARCHITECTURE.md`.
- **No timing of the WebAssembly build.** The brief allows it only if measured the same way,
  and a call through the module includes embind's conversion and a structured clone that a
  native call does not, so the same harness would not be measuring the same thing.
  `ARCHITECTURE.md` claims nothing for it.
- **The timing method.** Batches, because `price_and_greeks` takes less time than a clock
  read resolves; rotated rounds, so no entry point always follows the same one; three
  processes, so the figure is shown not to depend on one process; the range of the three
  medians, not one number. The harness is built in CI under the warnings so it keeps
  compiling; it is never run there, because a time on a shared runner describes the runner.
- **`surfaceSampling`** names the fifth key after the settings type, as `bumpSizes` does.
- **`.editorconfig`** states no `max_line_length` (C++ lines run to 121 characters), and
  exempts the vendored headers from trailing-whitespace trimming, since `doctest.h` has a
  line that an editor would otherwise change.
- **`ARCHITECTURE.md` adapts DepthCharge's form** where Touchstone differs: §7 Timings is
  added; DepthCharge's amendment log becomes §10 History, because the constitution, not
  this file, is Touchstone's normative document; §11 records changes to this file.

**Not done**

- **The tag.** The owner's, after the tollgate.
- **No WebAssembly timing, no Clang timing, no second machine.** §7 says so.
- **The folded `crank_nicolson` and `crank_nicolson_surface` were not built** against the
  suite; the decision does not rest on them.
- **Observed, not changed:** `PdeSettings`' comment says the defaults "hold every row to
  3e-4 of the underlying's own scale" on the golden grid. The suite runs the whole grid at
  512 × 256 (worst price 8.9e-5 on that scale) and the defaults (1024 × 512) on 136 rows of
  it (worst 2.2e-5); it does not run the defaults on every row. `ARCHITECTURE.md` does not
  repeat the claim. Outside this milestone's brief; for the owner.
- **`golden/SCHEMA.md` still says "T1 tests them directly"**: outside the five places the
  brief names.
- **`actionlint`** not run; no workflow changed beyond comments.
- **The site was not touched** (I18). For L5: `defaults()` now has `surfaceSampling`.

**Exact next step**

The owner opens the Fable tollgate (F) with the constitution's prompt for T5. On PASS, the
owner merges `m/T5`, ticks T5 in `ROADMAP.md`, and once `main`'s CI is green pushes the tag
that runs the release (P4: the session does not):

```bash
git checkout main
git pull --ff-only origin main
git log -1 --format='%h %s'            # the merge of m/T5
gh run list --branch main --limit 1    # CI on that commit: completed, success
git tag -a v1.0.0 -m "Touchstone 1.0.0"
git push origin v1.0.0
gh run watch "$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
gh release view v1.0.0                 # four assets: touchstone.mjs, touchstone.wasm, size.txt, SHA256SUMS
```

If the release run fails, delete the tag (`git push origin :refs/tags/v1.0.0`, then
`git tag -d v1.0.0`), fix on a branch, and tag again after the merge. P2 then unlocks.

## The claims check

A fresh agent, told to be adversarial and to edit nothing, checked rows 1–129 of `claims.md`
against their citations at `a83dfd3`: **93 held, 26 held with a correction needed, 9 did not
hold, 1 could not be checked** (row 126, which pointed at this then-pending section). It
also found nine factual sentences with no row. I verified each finding against the code
before changing anything; all stood. `claims.md`'s last section has the full account. The
nine that did not hold:

- **"Three independent ways" (3).** The Monte Carlo takes its discount factor and
  discounted strike from the closed form's `ClosedFormQuote`; all three share `scales.hpp`.
  §1 now says the methods are independent in method, not in every line, and what they share.
- **The demos run on WebAssembly (6).** They do not yet; L5 moves them. §1 and the README
  are corrected.
- **The Monte Carlo agrees on the grid (9).** It is scored on the rows with enough paths in
  the money, 6,147 + 323 of 7,234. The claim is now bounded to those.
- **No accepted input gives a NaN (11).** `norm_inv(1.0)` is an asserted NaN, and the grid,
  implied vol and bump Greeks are not swept. §1 and §6.2 now name the swept families and
  the exception.
- **Every refusal is in a `require_valid` (52).** Two are not: Monte Carlo's total variance
  and the surface's stride of zero. §4 and §6.1 now say so.
- **Thirteen prices (73).** My breakdown summed to fifteen; so did `bump_greeks.hpp`'s
  comment. Both are corrected. The library's object files are still byte-identical to
  main's.
- **The probe on clang (102).** Only the folded case's clang output was recorded. The
  unfolded case's error is now in `build.txt` §4.
- **Every binding entry point but the grid refuses an American option (108).**
  `bumpGreeks` over the grid accepts one. §8 is corrected.
- **The clang-format remainder "mostly comments" (112).** It has none. §8 says what it is.

The 26 corrections narrow wording, fix citations or labels, or move present tense to future
where the work is not done. They cover the portal page, the release feeding the demos, the
consumers list, `payoff`, "every scalar", one T3a alternative rather than all, the
half-width's 1.5e-8 being an estimate, four of T1's inputs, kept T3a findings, the grep's
scope, the antithetic and Rannacher citations, the `Error` branch, what the smoke test
re-checks, "nothing tuned", the safeguarded solver named, T0 versus T1 for CI regeneration,
and what a NaN does to a comparison. The corrected document was not re-checked by a second
agent. I re-read every changed row against its citation.

## Amendments

**None proposed.** The harness adds no dependency; `.editorconfig` is a description of the
sources, not a stack addition.

## Owner actions

1. **Run the T5 tollgate** (F) on this pack; `claims.md` is the row-by-row check.
2. **On PASS, merge, tick, and push `v1.0.0`** with the commands above.
3. **Rule, if you disagree, on the three pairs** (Decisions), and on counting governance
   named without an id as history.
4. **Consider the `PdeSettings` comment** under Not done.

## What is in this pack

- `summary.md` — this file.
- `claims.md` — every claim in `ARCHITECTURE.md`, numbered, with what holds it, and the
  independent check.
- `timing.txt` — the harness's method, the machine, compiler and flags, the launch command,
  and the raw output of the three runs.
- `build.txt` — toolchains, builds and sizes, the history grep before and after, the
  overload probe, the structural greps, the `.clang-format` attempts, the `.editorconfig`
  measurements.
- `tests.txt` — the native suite at the head with every reported figure, the four checks
  that no number moved, the smoke test, CI.
- `diff.txt` — `git diff --stat` against `74987c7`.
- No `screenshots/`: T5 has no UI.
