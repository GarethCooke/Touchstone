# T0 — Repo, experiments, golden values · evidence pack

## Work order (P3)

**Goal.** T0 as the roadmap states it: a README pointing at the constitution, a `uv` project,
`experiments/` with a README describing the script-plus-JSON discipline,
`golden/generate_bs_vanilla.py` producing prices and Greeks for European calls and puts over a
parameter grid from QuantLib-Python, and `golden/bs_vanilla.json` committed with the QuantLib
version recorded. Exit: the generator reruns reproducibly, the JSON schema is documented, no
C++ yet.

**Steps.** Branch `m/T0` · repo hygiene so the mount stops generating line-ending noise · `uv`
project pinned by lockfile · README and `experiments/README.md` · the generator · the golden
file · `SCHEMA.md` · an independent verifier · evidence.

**Decisions taken before starting**, all three put to the owner in-session: the grid is a full
cartesian product plus a separately labelled edge block; `golden/` is top-level rather than
nested under `experiments/`; the Greeks are raw partial derivatives rather than the scaled
quantities a desk quotes. Reasoning in **Decisions** below.

---

### 2026-08-29 · claude-opus-5 · Golden file generated and cross-checked: 7200-row grid plus a 34-row edge block from QuantLib 1.43, byte-reproducible, with the oracle's two precision limits measured and documented

**Done**

1. **Branch and hygiene.** `m/T0` off `211477e`. `.gitattributes` (mirroring the learn site's,
   plus `*.py` and `*.toml`) and `.gitignore`. The working tree had CRLF-only churn on
   `LICENSE` and `README.md` at session start; restored to their committed content, so the
   diff carries no line-ending noise.
2. **`uv` project.** `pyproject.toml` at the repository root, `requires-python = ">=3.12"`,
   `.python-version` pinning 3.12, `uv.lock` committed. Two dependencies: QuantLib 1.43 and
   numpy 2.5.2. `package = false` — this is a script runner, not a library.
3. **README.** What Touchstone is, the governance table, the two rules that shape the code
   (I4 and I20), a milestone status table, the layout, and how to run the Python side. The
   owner's existing one-line description is kept as the opening claim rather than rewritten.
4. **`experiments/README.md`.** The script-plus-JSON discipline as six rules — one script one
   JSON one commit, name for the page it serves, seed everything, record the inputs in the
   output, print nothing that matters, no plotting here — plus what the results are for and
   what deliberately does not live there. The folder is otherwise empty by design: the
   experiments arrive one per teaching session (§7).
5. **`golden/generate_bs_vanilla.py`.** `AnalyticEuropeanEngine` on
   `BlackScholesMertonProcess`, Actual/365 Fixed, null calendar, evaluation date fixed in
   source. Main grid: 5 spots × 5 strikes × 4 vols × 3 rates × 3 yields × 4 expiries × 2 types
   = **7200 rows**. Edge block: 17 labelled near-degenerate parameter sets × 2 types = **34
   rows**. The script applies no arithmetic of its own to anything QuantLib returns.
6. **`golden/bs_vanilla.json`.** 2.4 MB, 7234 rows, one row per line so `git diff` names the
   rows that moved. Carries `oracle.version` (`1.43`), the engine and day-count conventions,
   the units of every field, the tolerances, and the axes — so a consumer reads the file's own
   terms rather than re-deriving them from this document.
7. **`golden/SCHEMA.md`.** Document structure, every field with its units, the closed-form
   formulas the file must satisfy, the grid, the edge block, **Precision**, the tolerances,
   how to regenerate, and the four downstream consumers.
8. **`golden/verify_bs_vanilla.py`.** An independent re-derivation of all seven values for all
   7234 rows using `math.erfc`, put–call parity on all 3617 matched pairs, the sign and unit
   conventions asserted rather than trusted, and the document's own structure checked. Passes
   at 10⁻¹³ of each quantity's natural scale; worst observed deviation 1.7 × 10⁻¹⁴.
9. **Two properties of the oracle found, measured and written into `SCHEMA.md`.** Both would
   otherwise have surfaced at T1 as a failing test with no explanation:

   - **106 rows carry a slightly negative price** (all deep out-of-the-money puts, most
     negative −1.66 × 10⁻¹⁴, true values around 10⁻¹⁹). QuantLib's value there is the residue
     of a cancellation between two numbers of order *S*, so it lands on either side of zero.
     Not clamped — see Decisions. The consequence is a comparison rule, now stated in the
     file: relative above 1.0, absolute below.
   - **QuantLib's theta error scales as `S·ε/T`.** It derives theta by a route that divides by
     the year fraction. Measured across all six expiries in the file, the error times *T* is
     constant at one to two ulps of spot: 1.5 × 10⁻¹³ of spot at one day, 5.2 × 10⁻¹⁷ at five
     years. So golden theta on a one-day option is good to ~10⁻¹¹ absolute, not 10⁻¹⁵ — inside
     the edge block's 10⁻⁸ but only one order inside the main grid's 10⁻¹⁰. The main grid's
     shortest expiry is 91 days, where the effect is negligible; the one-day rows are in the
     edge block partly for this reason.

10. **Verified and logged.** Reproducibility proved by regenerating twice and comparing
    SHA-256 against the committed file; all three identical. Build and test logs in this pack.

**Decisions (with why)**

- **The grid is a full cartesian product plus a separately labelled edge block.** *Owner chose
  in-session* from three options. "A grid of spot, strike, vol, rate, dividend yield and
  expiry" reads as a product, and 7200 rows costs 2.4 MB and about a second to generate.
  Keeping the near-degenerate corners in their own block means a test can say *these are the
  hard ones* rather than discovering it from a failure, and lets them carry their own
  tolerance without loosening the main grid's.
- **`golden/` is top-level, not `experiments/golden/`.** *Owner chose in-session.* The roadmap
  lists `golden/generate_bs_vanilla.py` alongside `experiments/` rather than inside it, and
  the two folders serve different masters: `experiments/` is the teaching track's output under
  §7, `golden/` is the library's test oracle. Worth noting for the record that
  tech-decision **B2 says reference values are generated "in `experiments/`"** — superseded by
  the roadmap's explicit path. `docs/tech-decisions-v1.md` is a companion, not normative, so
  no amendment is required; the owner may want to correct that sentence.
- **Greeks are raw partial derivatives, not market conventions.** *Owner chose in-session*
  after discussion. Vega per 1.00 of vol, theta per year, rho per 1.00 of rate. The file's only
  readers are assertions: T1's tests, T3's bump-vs-analytic comparison, L1's D6. A per-day
  theta would put a convention factor — and a choice between 365, 365.25 and 252 — inside the
  oracle, where an arithmetic identity belongs, and the same factor would have to be applied
  identically in the generator, the C++ and the TypeScript. A test could then fail because two
  of them disagreed about a divisor, which says nothing about whether Black–Scholes is right.
  QuantLib itself treats the scaling as a separate layer: `thetaPerDay()` is exactly
  `theta()/365` with a hardcoded divisor that ignores the configured day counter. Scaling
  belongs at the point of display, where D6 can apply it once and the tutorial can explain it.
- **Expiries are whole numbers of days; `T` is exactly `days/365`.** Under Actual/365 Fixed
  this makes the year fraction exact, so nothing rounds between the grid definition and the
  number the C++ is handed. Both `expiry_days` and `expiry_years` are in every row.
- **The evaluation date is fixed in source and no timestamp is written into the output.**
  Byte-identity is a stronger proof of "reruns reproducibly" than a value comparison with a
  tolerance, and it makes an unexpected diff informative. Git records when the file was
  generated; the file does not need to.
- **Negative prices are not clamped, and no value is post-processed.** I4 makes QuantLib the
  oracle; the file's authority comes from being *what QuantLib said*. Clamping would be our
  arithmetic silently improving the oracle, and would hide exactly the numerical behaviour a
  C++ implementation needs to expect. Documented in `SCHEMA.md` instead, with the comparison
  rule that makes it a non-issue.
- **A verifier was written, though the roadmap does not list one.** A generator that drives
  QuantLib wrongly — dividend handle where the rate handle belongs, an accessor meaning
  something other than what the schema claims — produces a perfectly self-consistent file full
  of wrong numbers, and nothing else in the pipeline would notice before T1. It uses
  `math.erfc` rather than scipy specifically because that is the route `std::erfc` gives the
  C++ (B3), so a disagreement here is one the library would also have had. It is also what
  found both precision properties above. *Decision — owner may overrule*, though removing it
  would leave the file's correctness resting on a single implementation.
- **Dependencies are QuantLib and numpy only.** A9 lists numpy, scipy, matplotlib and `uv` for
  the experiments; scipy and matplotlib are not needed by anything at T0, and adding unused
  pins to a lockfile that is meant to be a reproducibility guarantee is cost without benefit.
  They enter when the first experiment needs them. *Decision — owner may overrule.*
- **QuantLib-Python enters under I4 and B2, not as an I19 addition.** I19's experiments stack
  reads "Python 3.12+, numpy, scipy, uv" and does not name QuantLib, but I4 requires reference
  values to be generated by QuantLib-Python, so the dependency is constitutionally mandated
  rather than an addition to the stack. Recorded rather than proposed as an amendment; the
  owner may prefer I19 to name it explicitly.
- **Tolerances live in the file, not in the tests that read it.** `tolerances.cases` = 10⁻¹⁰
  (the roadmap's T1 figure), `tolerances.edge_cases` = 10⁻⁸. A test that hard-codes them will
  drift from the data it is testing.
- **The Python environment lives outside the checkout in this session, but every artefact and
  every log came from the checkout.** The Windows folder is mounted here without permission to
  unlink, so `uv sync` cannot complete in place: it installs, then fails removing its own
  staging directory. `UV_PROJECT_ENVIRONMENT` points the interpreter at the session's own
  filesystem. This is narrower than L0's defect **D5** — there the whole source tree was
  mirrored; here the scripts, the JSON and the logs are all the committed checkout's, and only
  the interpreter is elsewhere. On Windows `uv sync` creates `.venv` in the checkout normally;
  the owner should confirm once (owner action 3).
- **No CI workflow.** T1's deliverables include "GitHub Actions on GCC and Clang"; adding a
  Python workflow now would pre-empt that design, and P2 forbids beginning the next milestone.
  Recommended for T1 in **Not done** below.

**Not done**

- **No C++**, which is the exit criterion, not an omission. No `CMakeLists.txt`, no `src/`, no
  `tests/`.
- **`experiments/` holds only its README.** By design: the scripts arrive one per teaching
  session S1–S11 under §7. The folder and its discipline exist now so the first one has
  somewhere to land and a shape to follow.
- **Nothing runs in CI.** The verifier and the reproducibility check are run by hand. This is
  the same gap L0's tollgate raised as **D2** for the learn site. Recommended for T1: a
  workflow step that runs `uv run golden/verify_bs_vanilla.py`, and one that regenerates the
  golden file and fails if `git diff --exit-code golden/bs_vanilla.json` is dirty. That second
  one turns "reruns reproducibly" from a claim in this pack into a standing check.
- **Carried over from L0's verdict, still outstanding and not this milestone's to fix.**
  Amendment **A4** is not yet recorded in `CONSTITUTION.md` §8, and `docs/rng.md` is still
  absent from `touchstone` — the companions list names it but L0 wrote it in
  `touchstone-learn`. Neither blocks T0. **A4 blocks T2**, whose deliverable is "RNG per
  `docs/rng.md`, passing the known-answer fixture copied from the site" — the copy I17
  currently forbids.
- **Naming mismatch, flagged not fixed.** The constitution's companions list names
  `docs/index-v1.md`; the file is `docs/quant-learn-index-v1.md`. Renaming a document the
  constitution points at is the owner's call, and `curriculum.ts` already cites the current
  name.
- **The branch is committed but not pushed**, which leaves P6 half-satisfied. This session
  reaches the repository through a mount of the Windows folder, and the owner's GitHub
  credentials live in Windows' credential manager, which the mount does not expose: `git push`
  fails with `could not read Username for 'https://github.com'`. No credential was sought or
  supplied by other means. `git push -u origin m/T0` from the owner's own shell is the whole
  of the remaining step; the commit itself is complete and the tree is clean.

**Exact next step**

The owner pushes `m/T0`, reviews this pack and merges it — T0's tollgate is **V**,
self-verified, so there is no Fable session to run. Then tick T0 in `ROADMAP.md` with a pointer to
`docs/evidence/T0/`. T1 and L1 both unlock; L1 needs nothing from T0 but this golden file, and
T1's first act under P3 is writing its work order from the T1 roadmap entry.

---

## Exit criteria

| Criterion | Result | Evidence |
|---|---|---|
| The generator reruns reproducibly | **pass** | `tests.txt` §1 — the committed file and two fresh runs share one SHA-256, `938ed1bb…0334`; `cmp` reports byte-identity both ways. Evaluation date fixed in source, no timestamp in the output. |
| JSON schema documented | **pass** | `golden/SCHEMA.md` — 15 fields with units, the closed-form definitions, the grid, the edge block, precision limits, tolerances, consumers. The file also carries its own `conventions`, `tolerances`, `axes` and `fields` blocks. |
| No C++ yet | **pass** | `diff.txt` — 13 files, none of them `.cpp`, `.hpp` or `CMakeLists.txt`. |

## Deliverables

| Deliverable | Result | Where |
|---|---|---|
| README stating what Touchstone is and pointing at the constitution | **pass** | `README.md` — governance table links `CONSTITUTION.md`, `ROADMAP.md`, both companions and the evidence folder. |
| `uv` project | **pass** | `pyproject.toml`, `.python-version`, `uv.lock`; `build.txt` shows `uv lock --check` and `uv sync` clean. |
| `experiments/` with a README describing the script-plus-JSON discipline | **pass** | `experiments/README.md`. |
| `golden/generate_bs_vanilla.py` using QuantLib-Python over a grid of spot, strike, vol, rate, dividend yield and expiry, calls and puts | **pass** | 7200-row product over exactly those six axes × 2 types, plus a 34-row edge block. |
| `golden/bs_vanilla.json` committed with the QuantLib version | **pass** | `oracle.version` = `1.43`, alongside the binding, engine, day count, calendar and evaluation date. |

## Invariants exercised

- **I4** — QuantLib runs in exactly one file, `golden/generate_bs_vanilla.py`, and its output
  is committed as versioned JSON. Nothing links QuantLib; nothing else imports it. The
  generator applies no arithmetic to what the oracle returns, which is what makes the file's
  authority QuantLib's rather than ours.
- **I6** — the generator has no random component, and determinism is proved by byte-identity
  rather than asserted.
- **I12** — the repository is public under MIT; `LICENSE` was committed by the owner before
  this session, which was T0's entry criterion.
- **I20** — not yet exercisable: three-way agreement needs T2 and T3. What this milestone
  does establish is the reference the three will be compared against, and one independent
  agreement — closed form against QuantLib, to a few ulps, on 7234 rows.
- **I21** — v1 scope respected exactly: European vanillas, one underlying, constant rate and
  volatility, dividend yield. The model string in the JSON says so.
- **I18** — nothing outside `touchstone` was written. `touchstone-learn` was read only, for
  L0's log and verdict.
- **I13** — the owner's existing one-line README description is preserved verbatim as the
  opening claim. No site copy was invented; nothing here reaches the tutorial.
- **P4** — three decisions were put to the owner in-session (grid shape, golden path, Greek
  conventions). The rest are reversible and marked where they may be overruled. Nothing
  irreversible or public-facing was decided: no licence, hostname, visibility or spending
  change, and no push to `main`.

## Amendments proposed

None. Two governance notes are recorded above rather than proposed as amendments: QuantLib
entering under I4 rather than as an I19 stack addition, and tech-decision B2's "in
`experiments/`" being superseded by the roadmap's explicit `golden/` path. Both are the
owner's to formalise if they want them formal.

**A4 from L0's verdict remains unrecorded** and should be settled before T2 opens.

## Owner actions

1. `git push -u origin m/T0` — see **Not done**; this session had no credentials for the
   remote. Then merge (tollgate V, self-verified) and tick T0 in `ROADMAP.md` with a pointer
   here.
2. **Delete `_to_delete/` at the repository root — 279 MB.** It holds two half-installed
   `.venv` directories and a stale git lock file. This session's mount refused every delete,
   so they were moved there rather than removed; `_to_delete/` is in `.gitignore` and nothing
   references it. A handful of `tmp_obj_*` files under `.git/objects/` have the same cause and
   are equally safe to remove.
3. Confirm `uv sync` and `uv run golden/verify_bs_vanilla.py` work natively in the Windows
   checkout — see the environment decision above. If they do, T0's proof is complete on the
   owner's machine as well as here.
4. Outstanding from L0's verdict: record **A4** in `CONSTITUTION.md` §8 and re-upload it to
   the Claude Project. This is the one item that blocks a later milestone (T2).

## What is in this pack

- `summary.md` — this file.
- `build.txt` — `uv --version`, `uv lock --check`, `uv sync`, the interpreter and library
  versions, and the generator run.
- `tests.txt` — reproducibility (three runs, one hash), the full verifier output with worst
  deviation per field, and the grid's coverage by price band.
- `diff.txt` — `git diff --stat` against `211477e`, the milestone's base.
- No `screenshots/`. P5 requires them for UI; T0 has none, and will not until L1 renders D6.
