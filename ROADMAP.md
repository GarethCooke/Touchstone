# ROADMAP — Touchstone programme

Version 1 · 2026-08-28 · Home: `touchstone/ROADMAP.md`. Governed by `CONSTITUTION.md`.
Each milestone lists **Entry** (what must be done first), **Deliverables**, **Exit** (checkable
criteria — the tollgate tests exactly these), **Tollgate** (V self-verified · F Fable review),
**Executor**, and **Size**. Session logs live in the executing repo's evidence pack
(constitution P7, A1); the owner ticks the box and adds a one-line pointer here when the
tollgate has passed. Every UI exit criterion is read as including I22: usable at 390 px,
evidenced by screenshots.

## Tracks

- **S — Study** (teaching sessions, Fable + owner): S1–S11 → pages 2.1–2.11.
- **L — Learn site** (`touchstone-learn`, Opus): L0–L6.
- **T — Touchstone library** (`touchstone`, Opus): T0–T6.
- **P — Portal** (portfolio repo, Opus via a portal brief): P1–P2.

## Suggested order

L0 → T0 → S1… (owner's cadence, in parallel with everything below) → T1 → L1 → T2 → T3 →
L2 (once S11 is done) → L4a → L3 → P1 → L4b → T3a → T4 → T5 → T6 → L5 → P2 → L6.

Fable-review tollgates, eight in total: L0, L1, L2, T1, T5, L5, P2, L6.

## Dependency map

| Milestone | Needs |
|---|---|
| L1 | L0, T0 (golden values for D6) |
| L2 | L0, L1, S1–S11 |
| L3 | L2 |
| L4a | L2 batch 1's draft-routing fix; Fable drafts for 0.1–0.3 |
| L4b | L3, Fable drafts for 1.0–1.5 |
| L5 | L3, T3, T4, T6 |
| L6 | L4, L5, P1, P2 |
| T1 | T0 |
| T2 | T1, L0 (RNG fixture) |
| T3 | T2 |
| T3a | T3 |
| T4 | T3a |
| T5 | T4 |
| T6 | T5 |
| P1 | L3 |
| P2 | T5 |

---

## Track L — Learn site

### ☑ L0 — Scaffold
**Entry:** both repos created — `touchstone` public, `touchstone-learn` private (I12);
`touchstone/docs/` holds the constitution companions; Node 22 installed locally.
**Deliverables:** everything in `docs/briefs/S0-learn-site-scaffold.md`, which is this
milestone's work order.
**Exit:** `npm run build` and `PREVIEW=1 npm run build` both succeed; preview renders the
index and `/template` in light and dark at desktop and 390 px, with D1 and the check
operable by touch (I22); `npm test` green (RNG known answers, gating,
curriculum integrity); `npm run check:snippets` green; `docs/rng.md` and the RNG fixture
exist; production build renders the holding page only.
**Tollgate:** F. **Executor:** Opus. **Size:** one session, two at most.

### ☑ L1 — Demos D1–D6 on the TypeScript backend
**Entry:** L0, T0.
**Deliverables:** D2 quadratic-variation counter; D3 Itô integral, left-endpoint vs midpoint;
D4 GBM paths, exact vs Euler with the dt/√dt toggle; D5 delta-hedging simulator with
rebalance count and realised-vs-implied vol; D6 Black–Scholes pricer with Greeks and the
price-versus-payoff curve. Each with a property or known-answer test.
**Exit:** D2: quadratic variation of a simulated path within tolerance of T. D3: left-endpoint
sum matches ½W_T² − ½T within tolerance and the midpoint sum does not. D4: Euler error
shrinks with dt at the expected rate. D5: log–log slope of hedging-P&L standard deviation
against rebalance count is −0.5 ± 0.1. D6: prices and Greeks match the T0 golden file to
1e-10. All demos deterministic under seed (I6); all render in light and dark at desktop and 390 px
and are operable by touch (I22).
**Tollgate:** F. **Executor:** Opus. **Size:** two to three sessions; may split L1a (D2–D4)
and L1b (D5–D6) with one tollgate at the end.
**Passed** 2026-08-30 — evidence: `touchstone-learn/docs/evidence/L1/`.

### ☑ L2 — Part 2 ingestion
**Entry:** L0, L1, S1–S11; batches ingest as drafts land, each batch's drafts and experiments
committed; the F tollgate runs once, at the end, over all eleven.
**Deliverables:** MDX for every Part 2 page from the owner's drafts, verbatim in substance;
snippets extracted from the committed experiments; demos embedded per the index; checks with
at least three questions per page; status `draft`.
**Exit:** curriculum integrity test green; every snippet runs; every check meets I5; preview
renders every page; the owner has reviewed each page.
**Tollgate:** F — content review against I1: every claim backed by a test, an experiment
result or a source. **Executor:** Sonnet (mechanical), Opus if the conversion is not clean.
**Size:** batches allowed; one tollgate at the end.
**Passed** 2026-11-15 — evidence: `touchstone-learn/docs/evidence/L2/`, with the verdict in
`verdict.md`. PASS WITH DEFECTS: eight, all low, D1–D8 to close before L3.

### ☑ L3 — First publication
**Entry:** L2 passed; the `seed + p` batch; L4a if it has run.
**Deliverables:** 2.1–2.11 set to `published`, and 0.1–0.3 with them if L4a has run; landing
paragraph live; sitemap; the production index renders the tree (I10).
**Exit:** production shows Part 2 end to end, preceded by Part 0 if L4a has run; no `tbc` page
is a route; the owner signs off.
**Tollgate:** V, then owner. **Executor:** Opus. **Size:** under an evening.
Unlocks P1.
**Passed** 2026-11-16 — evidence: `touchstone-learn/docs/evidence/L3/`. Self-verified; the owner
merged `m/L3` (pull request #6) and production shows Part 0 and Part 2 end to end. By his
rulings of 2026-11-15 the landing paragraph is the L0 brief's, unchanged, and it is also the
site's description.

### ☑ L4a — Part 0
**Entry:** L2 batch 1 merged — its `scripts/routable.mjs` per-mode fix is what lets a `draft`
page exist without breaking the production build; Fable drafts for 0.1 and 0.2. 0.3's notation
ledger is already live from L2 batch 1 under a labelled placeholder; the rest of 0.3 lands here.
**Deliverables:** 0.1, 0.2 and 0.3 as MDX with checks. 0.2 carries the thesis, the map of the
parts, and how to read a demo and a check — written about the affordances, not as a tour of
specific demos, so that D7–D10 (L5) and D11 (L4b) arriving later does not date it. No demos, no
snippets, no experiments: Part 0 makes no quantitative claim that needs one. Any
market-structure figure on 0.1 carries a cited source (I1).
**Exit:** the three pages `draft`, or `published` if L3 has already run; checks meet I5;
curriculum integrity green; both build modes green; I22 at 390 px; owner review.
**Tollgate:** V. **Executor:** Opus. **Size:** one session.
Retires the I2 exception at the head of 2.1: with 0.1 and 0.2 in front of it, 2.1 stops being
the first page a reader meets, and its opening paragraph can be rewritten knowing what
precedes it rather than to compensate for nothing preceding it.
**Fable drafts for 0.1 and 0.2** — done 2026-09-05, `touchstone-learn/drafts/`, Project note `touchstone/L4a-drafting-session.md`
**Passed** 2026-11-15 — evidence: `touchstone-learn/docs/evidence/L4a/`. Self-verified; the owner
read the three pages on the preview and approved them. By his rulings of that day 0.1 and 0.2
carry four static figures, which are neither demos nor snippets.

### ☑ L4b — Part 1
**Entry:** L3; Fable drafts for 1.0–1.5.
**Deliverables:** pages with checks; the payoff-diagram builder (new demo, D11) for 1.4; the
margin-account walk for 1.2 as a worked table; the day-count example for 1.0 as a runnable
snippet.
**Exit:** pages `published`; snippets run; checks meet I5; owner review.
**Tollgate:** V. **Executor:** Opus. **Size:** two sessions.
By the owner's ruling of 2026-11-17, 0.2's map and its sections on reading a demo and a
check become page 0.0 "How to use this site", with no check (A11), built as one more batch
on `m/L4b` before the close — brief: `touchstone-learn/docs/briefs/L4b-page-0.0.md`.
**Passed** 2026-11-19 — evidence: `touchstone-learn/docs/evidence/L4b/`. Self-verified; the owner
read the six pages and the payoff-diagram builder on the preview and approved them, merged
`m/L4b` (pull request #8), and production shows Parts 0, 1 and 2 end to end. By his rulings of
2026-11-17, 1.5 says its swap must be cleared and is margined, and nothing a reader can see
says who decided something or when, the experiment scripts included.

### ☐ L5 — Part 3 and demos D7–D10 on the WASM backend
**Entry:** L3, T3, T4, T6; Fable drafts for 3.1–3.7.
**Deliverables:** `wasmBackend` behind `PricingBackend` (I15), on the `v1.1.0` artifact,
carrying every demo: D1–D6, D9 and D11 move onto it from the TypeScript numerics; D7 Monte
Carlo convergence with error bars; D8 PDE grid heatmap, European and American; D9 implied-vol
solver and smile viewer on its generated fixture; D10 bump-and-revalue risk table; pages
3.1–3.7 from the Fable drafts, reviewed by the owner (I2).
**Exit:** TS and WASM backends agree on every known-answer and demo test within tolerance;
the TypeScript numerics are then removed and the suite runs on WASM alone (A6);
D9's fixture carries its source and that source's hash; pages `published` after owner review.
**Tollgate:** F. **Executor:** Opus. **Size:** three sessions.
By the owner's rulings of 2026-11-19: Fable sessions draft Part 3 as they drafted Part 1; a
Part 3 page shows the library's own C++, copied at the pinned release, and its numbers are held
by a site test that runs the browser build, with an experiment script only for a number the
library cannot produce; 3.3 covers early exercise on the grid (A12); D9 keeps its generated
smiles and takes no Deribit snapshot, because Deribit's terms do not allow its market data to
be published without written approval; numpy is pinned in the site's build.

### ☐ L6 — Launch v1
**Entry:** L4, L5, P1, P2.
**Deliverables:** end-of-part checkpoints; progress reset and export; Umami wired; licences
committed; `touchstone-learn` public; README current.
**Exit:** every v1 page `published`; every check answerable; no placeholder text anywhere;
`touchstone-learn` public with its licences; the portal's link and card live.
**Tollgate:** F — final claims review of the whole site, plus owner. **Executor:** Opus.
**Size:** one session.

## Track T — Touchstone library

### ☑ T0 — Repo, experiments, golden values
**Entry:** repo exists, public, `LICENSE` (MIT) committed (I12).
**Deliverables:** README stating what Touchstone is and pointing at the constitution; `uv`
project; `experiments/` with a README describing the script-plus-JSON discipline;
`golden/generate_bs_vanilla.py` using QuantLib-Python to produce prices and Greeks for
European calls and puts over a grid of spot, strike, vol, rate, dividend yield and expiry;
`golden/bs_vanilla.json` committed with the QuantLib version.
**Exit:** the generator reruns reproducibly; JSON schema documented; no C++ yet.
**Tollgate:** V. **Executor:** Opus, or Sonnet (mechanical). **Size:** under an evening.
**Passed** 2026-08-29 — evidence: `docs/evidence/T0/`.

### ☑ T1 — Core: closed form and analytic Greeks
**Entry:** T0.
**Deliverables:** CMake project; Black–Scholes closed form with dividend yield; analytic
delta, gamma, vega, theta, rho; N(x) via `std::erfc`; tests: golden file to 1e-10, put–call
parity, σ→0 and T→0 limits; GitHub Actions on GCC and Clang with warnings as errors.
**Exit:** CI green on both compilers; every test named in the deliverables present.
**Tollgate:** F — this milestone sets the code patterns for everything after it.
**Executor:** Opus. **Size:** one to two sessions.
**Passed** 2026-08-29 — evidence: `docs/evidence/T1/`.

### ☑ T2 — Monte Carlo and the shared RNG
**Entry:** T1, L0.
**Deliverables:** RNG per `docs/rng.md`, passing the known-answer fixture copied from the
site; exact GBM sampling and Euler–Maruyama; standard error; antithetics; pathwise delta.
**Exit:** RNG fixture green; MC price within three standard errors of closed form across the
golden grid; Euler error scales as expected with dt.
**Tollgate:** V. **Executor:** Opus. **Size:** one to two sessions.
**Passed** 2026-08-30 — evidence: `docs/evidence/T2/`.
Grid-criterion reading ratified at merge,

### ☑ T3 — Finite differences, implied vol, bump Greeks
**Entry:** T2.
**Deliverables:** Crank–Nicolson on a log-spot grid with the Thomas solver; implied vol by
Newton with Brent fallback; bump-and-revalue Greeks; American early exercise as a stretch.
**Exit:** three-way agreement (I20) within stated tolerances across the golden grid; bump
Greeks match analytic within tolerance; implied vol round-trips golden prices to 1e-8.
**Tollgate:** V. **Executor:** Opus. **Size:** two sessions.
**Passed** 2026-08-31 — evidence: `docs/evidence/T3/`. American exercise included as
the stretch; `require_valid` repaired in `black_scholes.cpp`, which edits T1 after
its tollgate.

### ☑ T3a — Settle the library before it is bound
**Entry:** T3; the owner's design rulings of 2026-11-12 in
`docs/briefs/T3a-design-rulings.md`, from which the session derives its work order.
**Deliverables:** a path API: Brownian and GBM paths written into a caller's span,
exact-stepped and Euler, with an explicit drift; a second implied-vol solver, Newton with a
bisection guard, recording its steps, beside Newton–Brent; `AmericanVanilla` as a contract
type of its own, sharing one definition of its fields with `EuropeanVanilla`, and `exercise`
gone from `PdeSettings`; `scales.hpp` under `include/touchstone/detail/`; three classes
beneath the free functions: a closed-form evaluation that validates and computes once, a grid
solver that owns its matrices and its solution, a path generator; the nine repeats the rulings
list removed, and the tests' with them; the README's status current.
**Exit:** every test that was green is green, on both compilers and under the sanitizers;
each new piece has its test: a path fixture, the second solver against page 2.11's committed
trace, an American contract refused by the closed form at compile time; the free functions'
signatures unchanged except where a ruling changes them; a review for repeated code by a
session that did not write the change, its findings closed; no new dependency.
**Tollgate:** V. **Executor:** Opus. **Size:** two to three sessions.
**Passed** 2026-11-13 — evidence: `docs/evidence/T3a/`. The session's four decisions stand:
each implied-vol solver keeps its own stopping rule; a refused price returns a volatility of
zero or infinity with its status, never a NaN; `ClosedForm` is public and the grid solver and
path generator are in `detail/`; a path's step keeps its zero tests.

### ☑ T4 — WASM artifact
**Entry:** T3a.
**Deliverables:** Emscripten build with an embind API carrying every `PricingBackend` method
and the Monte Carlo, grid and bump-Greek entry points D7, D8 and D10 will need, since L5
cannot edit this repository (I18); C++ exception catching switched on, each exception reaching
JavaScript as an error; size under 500 KB, reported with and without exception support; built
in CI; published as a GitHub release artifact tagged `v0.4.0`.
**Exit:** artifact builds in CI; a smoke test loads it in Node, reproduces the RNG fixture
and one golden price, and survives an input the library rejects. Over 500 KB, the session
stops and returns to the owner.
**Tollgate:** V. **Executor:** Opus. **Size:** one session.
**Passed** 2026-11-13 — evidence: `docs/evidence/T4/`. Released as `v0.4.0`. In CI at
`9a2cdb4` the artifact is 172,654 bytes with exception catching and 141,576 without, against
500,000. An audit outside the session ran the smoke test on the built artifact and loaded it
in headless Chromium, in a page and in a worker. The session's decisions stand: an error is
returned across the boundary and thrown in JavaScript, since anything thrown through the
module's frames in time kills it; an American option is an `exercise` field that only the
grid's entry points accept; a seed or count that is not a non-negative integer is refused.
`crank_nicolson_surface` joined the library here, so that the binding only translates.

### ☑ T5 — Architecture write-up and going public
**Entry:** T4.
**Deliverables:** `ARCHITECTURE.md` as the golden source for the portal page, in the
DepthCharge style, carrying measured timings for the five entry points with the machine they
were taken on, and the milestone and review history that the source comments then leave out;
README final; `v1.0.0` tag.
**Exit:** every claim in `ARCHITECTURE.md` maps to a test or a file; CI green; tag pushed.
**Tollgate:** F — bounded-claims review, as for Temper's page. **Executor:** Opus.
**Size:** one session. Unlocks P2.
**Passed** 2026-11-14 — evidence: `docs/evidence/T5/`, with the verdict in `verdict.md`.
Released as `v1.0.0`. Fable's verdict was PASS WITH DEFECTS: nine, all wording in the README
and in header comments, all closed before the merge. The tollgate was the Fable session that
had audited T3a and T4, not a fresh one as §6 asks; the owner accepted it. The session's
decisions stand: the three exercise-style pairs in `pde.hpp` stay as overloads, since a
template would let an untyped `{}` settle silently on the bump sizes; no `.clang-format`; a
comment that cites the roadmap or the constitution as its authority counts as history.

### ☑ T6 — What the demos need from the browser build
**Passed** 2026-11-20 — evidence: `docs/evidence/T6/`. Released as `v1.1.0`. The owner ruled on
twelve signature questions before anything was built (`signatures.md`). In CI at the tag the
artifact is 214,863 bytes with exception catching and 173,194 without, against 500,000. Through
the module in Node, 200,000 closed-form points take 36 ms in one call and 57 ms as 781 calls of
256-point slices, against 2,255 ms one point a call. An audit outside the session built the
head with CI's compilers and under the sanitizers, ran the release's files in Node and in
headless Chromium, and held them to `v1.0.0`'s answers and to the site's TypeScript numerics.
The session's decisions stand: `gbm_paths` also returns its sample in a vector;
`price_and_greeks_columns` is the one pairing of the sweep's columns with a point's outputs;
`ClosedFormSweep` has an ordering; N(x)'s references are a fixture,
`golden/normal-known-answers.json`; the binding's `plus_one` and its `normals` loop, which
predate T6, are unchanged.
**Entry:** T5; the owner's ruling of 2026-11-19 in `docs/briefs/T6-browser-build-needs.md`, from
which the session derives its work order.
**Deliverables:** the binding exports the payoff, N(x) and the normal density; the library
steps a sample of geometric Brownian motion paths, exact and Euler, path by path from one
stream, and the binding carries it; a closed-form entry point that takes many spots and times
to expiry in one call, and its binding; the binding exports `implied_vol` (Newton, then Brent)
beside the safeguarded solver; the signatures proposed by the session and ruled on by the owner
before any is built; `ARCHITECTURE.md`, its claims list and the README current; version 1.1.0.
**Exit:** every test that was green is green, on both compilers and under the sanitizers;
nothing `v1.0.0` exports has changed its signature or its numbers; each new piece has its test,
and the smoke test calls each new export through the module; the cost of one closed-form point
through the module is measured and reported; no arithmetic in the binding; a review for
repeated code by a session that did not write the change, its findings closed; artifact under
500 KB, reported; no new dependency; released as `v1.1.0`.
**Tollgate:** V. **Executor:** Opus. **Size:** one session, two at most.
Unlocks L5.

## Track P — Portal (portfolio repo)

### ☑ P1 — Nav item
**Entry:** L3.
**Deliverables:** a fourth nav item between Projects and Contact, external link with the
`↗` marker, no active state; the sitemap untouched.
**Exit:** live on garethcooke.com in light and dark; mobile menu verified.
**Tollgate:** V, then owner. **Executor:** Opus via a portal brief. **Size:** under an hour.
**Passed** 2026-11-16 — evidence: `garethcooke-portfolio/docs/briefs/P1-touchstone-nav.md`, the
brief and its session log. Self-verified; the owner merged pull request #5 and the item is live
on garethcooke.com as "Touchstone ↗", opening `touchstone.garethcooke.com`. The word is the
owner's ruling of that day.

### ☑ P2 — Card and architecture page
**Entry:** T5.
**Deliverables:** Touchstone project entry after Temper and before MorayGlow; `View source`,
`Open the tool` (the site's D6), `Design & architecture` write-up rendered from
`ARCHITECTURE.md` with a `writeup-sources` entry.
**Exit:** page passes the site's drift check; claims bounded; light and dark verified.
**Tollgate:** F. **Executor:** Opus via a portal brief. **Size:** one session.
**Passed** 2026-11-16 — evidence: `garethcooke-portfolio/docs/briefs/P2-touchstone-portal.md`, the
brief and its session log, with the verdict in `docs/evidence/P2/verdict.md`. Fable's verdict was
PASS WITH DEFECTS: eight, two medium and six low, all wording or record on the card and the
write-up, closed in the portfolio's pull request #6 (`b46cba9`), which the tollgate re-checked. By
its ruling the write-up now names and links the tutorial. The first build was a Fable cloud
session's at the owner's request, not Opus's as P8 and the Executor line above ask; the owner
accepted it.

## Track S — Study (Fable + owner)

One fresh session per topic. Exit for each: experiment script and JSON committed to
`touchstone/experiments/`; owner's draft page in `touchstone-learn/drafts/`; draft checks
approved by the owner; the draft reviewed against I1. No tollgate — the session is the
review.

- ☑ S1 · 2.1 Random walks and scaling — evidence: `docs/evidence/S1/`
- ☑ S2 · 2.2 Brownian motion — evidence: `docs/evidence/S2/`
- ☑ S3 · 2.3 Quadratic variation — evidence: `docs/evidence/S3/summary.md`
- ☑ S4 · 2.4 The Itô integral — evidence: `docs/evidence/S4/summary.md`
- ☑ S5 · 2.5 Itô's lemma — evidence: `docs/evidence/S5/summary.md`
- ☑ S6 · 2.6 SDEs and geometric Brownian motion — evidence: `docs/evidence/S6/summary.md`
- ☑ S7 · 2.7 Delta hedging and the Black–Scholes PDE — evidence: `docs/evidence/S7/summary.md`
- ☑ S8 · 2.8 Risk-neutral pricing — evidence: `docs/evidence/S8/summary.md`
- ☑ S9 · 2.9 The Black–Scholes formula — evidence: `docs/evidence/S9/summary.md`
- ☑ S10 · 2.10 Greeks — evidence: `docs/evidence/S10/summary.md`
- ☑ S11 · 2.11 Where it breaks — evidence: `docs/evidence/S11/summary.md`

## Later (v2 — enters only by amendment, constitution I21)

Vol surfaces and SVI · local vol · Heston · jumps · rates and curve building · SABR ·
exotics · American options in depth · CVA · CDS · live market data with a fetcher.
