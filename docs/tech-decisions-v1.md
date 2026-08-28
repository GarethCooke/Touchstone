# Technology decisions — v1 register

Languages, in one line: **TypeScript** for the site and demos · **Python** for experiments,
tutorial snippets, the QuantLib oracle and the exercises · **C++20** for the library ·
**WASM** as the bridge from library to browser.

Grouped by when each decision binds. Each entry is a recommendation; overrule by editing the
line. A1, A5–A6 and B2 are the ones worth a full ADR; the rest are conventions.

---

## A — Decide now (the scaffold brief and session 2.1 need these)

**A1. Where the learning area lives — companion microsite on the Crucible stack.**
Next.js static export, MDX, Shiki, D3, Amplify; scaffold forked from Crucible. The portfolio
carries a card and a link once the site is real.
*Why:* Crucible already proves this exact content shape — post + code + committed results +
visualisation. The portfolio's write-up pages are hand-built TSX and won't scale to
twenty-six pages of maths prose. Deploy isolation makes gating trivial, and the copy-tokens
rule for companion sites already exists.
*Alternative:* `/learn` inside the portfolio repo with MDX added — one fewer repo, but a new
content pipeline in the Next 16 codebase and the portfolio's register exposed to drafts.
*Owner call:* hostname. `learn.garethcooke.com` or a themed name; keep the URL boring even
if the title isn't.

**A2. Content model — MDX per page; `curriculum.ts` as the single source of truth.**
Order, part, title, summary, status, check ids and demo ids live in `curriculum.ts`
(mirrors `projects.ts`); prose lives in MDX. Status drives routes, sitemap and nav.

**A3. Maths — KaTeX at build time** (remark-math + rehype-katex), no client JS for
equations. One shared macro file for notation so `dW`, `σ`, `N(d₁)` render identically on
every page. *Alternative:* MathJax — client-side and slower.

**A4. Code — Shiki at build time**, as Crucible. Snippets: Python on tutorial pages, C++ on
library pages, TypeScript on demo pages. Every snippet is extracted from a file that
actually runs; no prose-only code.

**A5. Demos — TypeScript compute first, WASM later, behind one interface.**
A `Demo` client component per demo id, mounted from MDX. Compute sits behind a
`PricingBackend` interface with a TS implementation now and a WASM implementation once the
library exists. *Why:* demos must not wait for Phase 3, and v1 maths is cheap in JS —
10⁵ Monte Carlo paths and small Crank–Nicolson grids are fine. Rendering: D3 for charts
(Crucible precedent); plain 2D canvas for animated paths (D1, D2, D4, D5), since SVG chokes
past ~10⁴ points.

**A6. Deterministic randomness — one RNG and one normal transform, implemented identically
in TS and C++.** A small 32-bit generator (xoshiro128\*\*: fast in JS, trivial in C++; two
draws per double) and inverse-CDF normals (Acklam or AS241). *Why:* "same seed, same
picture" in the browser and in the library's tests is what makes the demos a test of the
library. Agreement is to tolerance, not bit-exact — libm and V8 differ in the last ulps.

**A7. Knowledge checks — typed question data beside each page; progress in localStorage.**
Schema: prompt, options, correct index, per-option feedback, misconception tag. No accounts,
no backend; reset and export buttons. Checkpoint pages compose questions by tag.

**A8. Gating and preview.** `status: 'tbc' | 'draft' | 'published'`. Production builds
publish only `published`; an Amplify preview branch builds with `PREVIEW=1` and shows
drafts. `tbc` entries appear in the index as greyed text and never as routes. The portfolio
links to the site only once Part 2 has real pages.

**A9. Learning-phase tooling — scripts, not notebooks, committed from day one.**
Python 3.12+, numpy, scipy, matplotlib, `uv` for the environment. Create the library repo
now with only an `experiments/` folder: one script per section
(`2_3_quadratic_variation.py`), each writing a JSON result committed beside it — Crucible's
discipline. These become the demo fixtures and the library's tests.

**A10. Local toolchain — Node ≥ 20.9.** The last portal session found Node 18 locally
against Next 16's floor and had to fetch Node 22 into scratch. Fix it once with nvm or fnm.

## B — Decide at library kick-off (Phase 3)

**B1. Language and build.** C++20, CMake, GCC and Clang both green, warnings as errors.
Test framework and formatting: whatever Anvil uses, for consistency; Catch2 if there's no
precedent to follow.

**B2. QuantLib as oracle via golden files.** Reference values generated with
QuantLib-Python in `experiments/`, committed as JSON; the C++ tests read them. The library
never links QuantLib. *Why:* the oracle becomes versioned data — no heavyweight dependency,
fast CI, and the generating script is itself a Part 3 page ("reading QuantLib").
*Alternative:* link QuantLib in the test target via vcpkg — slow builds for no gain.

**B3. Numerics.** Doubles throughout. N(x) via `std::erfc`. Inverse CDF shared with TS
(A6). Thomas tridiagonal solver for Crank–Nicolson; no Eigen. Implied vol by Newton with a
Brent fallback; Jäckel's rational solver is a later upgrade if it earns a page.

**B4. WASM.** Emscripten + embind; one `.wasm` plus glue; size budget ~500 KB. Built in
the library's CI, published as a GitHub release artifact; the site vendors a pinned version
into `public/`. No submodules.

**B5. Python bindings.** pybind11, optional, v1.1. Nicer Part 3 pages; not on the critical
path.

**B6. Greeks.** Analytic and bump-and-revalue in v1; pathwise for Monte Carlo. AAD is a
stretch — if attempted, a minimal tape, never a dependency.

**B7. CI.** GitHub Actions on the library: native build and tests on Linux with both
compilers, WASM build, golden-file check, artifact upload. The portfolio keeps
build + lint as its gate.

## C — Later, or after the first demos exist

**C1. Exercises repo (Phase 6).** Separate repo, Python/pytest, one folder per chapter with
failing tests. A C++ variant only if there's demand.

**C2. Live market data.** None in v1; the site is static. If v2 wants it, a small
serverless fetcher with caching. Deribit and FRED snapshots remain the fixtures.

**C3. Analytics.** Umami, as on the portfolio. Optional quiz-completion events, no PII.

**C4. Licences.** Placeholders until decided: MIT for code, CC BY 4.0 for prose. TBC.

**C5. Drift discipline.** Part 3 pages that describe the library get a `writeup-sources`
entry pointing at the library's `ARCHITECTURE.md`, the same check the portfolio runs on its
write-ups. Adopt when the first 3.x page exists.
