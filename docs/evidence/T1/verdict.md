# T1 — tollgate verdict

Tollgate T1 · 2026-08-29 · Fable review per constitution §6.
Reviewer: a fresh session in the owner's Claude Project (serving model Fable 5; the
session's configured model id is `claude-opus-5`).

**Basis.** Read: `CONSTITUTION.md` at `49881b8` (includes A5), the T1 section of
`ROADMAP.md`, `docs/evidence/T1/summary.md`. Opened, because the exit criteria needed
them: `tests.txt`, `build.txt`, `diff.txt`, `.github/workflows/ci.yml`, the branch's git
state, and the live GitHub Actions result. No C++ source was re-read; no defect required it.

## Verdict

**PASS.**

- **CI green on both compilers — closed.** The pack left this pending, said so plainly,
  and named the closing action; the owner has since performed it. `m/T1` is pushed and
  workflow run #1 — https://github.com/GarethCooke/Touchstone/actions/runs/33259180653 —
  ran on push of `704aecc`, conclusion success. The `gcc` and `clang` jobs each completed
  Configure, Build and Test; the two jobs nothing required (`asan + ubsan`, `golden file`)
  are green as well, and the golden job's regeneration produced the committed file
  byte-identically on yet another machine, the fourth so far.
- **The CI result is a result about the audited bytes.** All sixteen SHA-256 digests in
  `tests.txt` §5 reproduce exactly from commit `704aecc` — the commit CI checked out is
  byte-identical to the tree both hosts built and tested. Verified independently at this
  tollgate.
- **Every test named in the deliverables present — pass.** Golden file to 1e-10
  (`test_closed_form.cpp`: 7,234 rows × 7 fields, worst scaled error 2.8e-13, in
  `dividend_rho`); put–call parity (`test_parity.cpp`: parity plus its six Greek
  identities, worst 1.4e-14); σ→0 and T→0 limits (`test_limits.cpp`: both limits derived
  and approached, divergence rates asserted, and the 25,920-point domain sweep). All on
  the branch, all run: 22 cases, 255,999 assertions, green on GCC 11 and 13, Clang 18,
  and under ASan/UBSan with `-fno-sanitize-recover`.

The pack holds §1's register throughout: every tolerance is a conditioning argument
rather than a number that passed; each fix carries the count of assertions that fail when
it is reverted, and the one that carries no such number is named as belt-and-braces; what
is not demonstrated — MSVC, Emscripten, the unobservable at-the-forward mutants — is said
outright. The adversarial second-session review with defects re-broken exceeds what this
tollgate enforces and is the pattern T2 and T3 should copy. Confirmed in passing:
`_to_delete/` is untracked, so the 279 MB is local clutter only and none of it is public.

## Defects

None against T1's delivered work. Two notes, neither blocking merge:

1. **Exit criterion "CI green", durability — low.** All four jobs warn that
   `actions/checkout@v4` and `actions/setup-python@v5` target Node 20, which the runners
   now force onto Node 24; when GitHub removes that shim the workflow stops running.
   Fix: bump both actions to their latest major in the T2 branch — two lines in `ci.yml`.
2. **Constitution preamble, companions list — housekeeping, pre-existing.** It names
   `docs/index-v1.md`; the file is `docs/quant-learn-index-v1.md`. Third evidence pack to
   carry the observation. Fix: one word, the owner's edit, no amendment needed.

## Amendments

- **A5 — confirmed.** The pack asked this tollgate to confirm the owner's in-session
  choice; the owner recorded A5 himself at `49881b8` (authority: owner, during T1), which
  §8 permits. On substance this tollgate concurs: both headers are byte-pinned with URL,
  licence and SHA-256 recorded in `third_party/README.md`, sit behind a SYSTEM-include
  INTERFACE target, and are linked by the test executable only — I19's purpose, a fixed
  and inspectable stack, is intact. The Project's constitution copy syncs from `main`, so
  it updates itself at merge.
- **Nothing new proposed.** Two T0 governance notes stay open at the owner's option:
  QuantLib's standing under I4 rather than I19, and tech-decision B2's `experiments/`
  superseded by the roadmap's `golden/`. Neither blocks the path to T5.

## Unlocks

T2 — Monte Carlo and the shared RNG (entry: T1 ✓, L0 ✓).

First step: after the owner merges `m/T1` and ticks T1 in `ROADMAP.md` with a pointer to
`docs/evidence/T1/`, the T2 session's first act is amendment A4's copy — `docs/rng.md`
and its known-answer fixture from `touchstone-learn` into `touchstone/docs/`, pinned to
the L0 merge commit, after which `touchstone/docs/rng.md` is the home. Then the RNG per
that specification against the fixture, exact GBM sampling and Euler–Maruyama, standard
error, antithetics, pathwise delta — toward T2's exit: fixture green, MC within three
standard errors of the closed form across the golden grid, Euler error scaling as
expected with dt. While in `ci.yml`, take defect 1's action-version bump.
