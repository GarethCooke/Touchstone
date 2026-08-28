# S0 — Learn site scaffold (learn.garethcooke.com)

**Track:** Agentic · **Status:** Not started · **Size:** one session, two at most — the
content pipeline is copied from Crucible, not designed; the new work is the curriculum data,
status gating, one template page, one demo and one check.
**Executes in the `touchstone-learn` repo** (new, private). Crucible's repo is read-only
source material: copy configuration from it, never edit it. The portfolio repo is not touched
(its card and nav item are a later brief in the MP-portal pattern, gated on publication). The
`touchstone` library repo is not touched.
**Reads first:** `../touchstone/CONSTITUTION.md`; this brief; `../touchstone/docs/index-v1.md`
(the curriculum — page ids, titles, summaries, checks, demos) and
`../touchstone/docs/tech-decisions-v1.md` (why each choice); Crucible's `README.md`,
`next.config.*`, `package.json`, its MDX/Shiki setup and its design-token copy; then
`node_modules/next/dist/docs/` before using any Next API. Next 16, React 19 and Tailwind v4 are
all newer than training data.

**Where this brief overrides those docs:** the library is named **Touchstone**; the learning
area is a companion site, not a route on the portfolio; Part 3 gains a page, **3.7 Reading
QuantLib**; `index-v1.md` A1 wording is "copy Crucible's config into a fresh repo", not "fork".

## Goal

A deployable static site whose index shows the whole v1 curriculum — every page listed, all
greyed as TBC — with the content pipeline proven end to end by a single template page:
KaTeX maths, a Shiki-highlighted Python snippet extracted from a runnable file, one
interactive demo (D1) on the TypeScript compute backend with the shared RNG, and one
multiple-choice check with per-option feedback and localStorage progress.

Production shows a holding page until at least one curriculum page is published; the preview
branch shows everything. Nothing on the public site ever claims what doesn't exist yet.

**Done means:** `npm run build` and `PREVIEW=1 npm run build` both produce a static export;
the preview build renders the index and `/template` correctly in light and dark (screenshots
in the log); `npm test` passes (RNG known answers, gating, curriculum integrity);
`npm run check:snippets` runs every file in `snippets/` without error.

## Decisions taken here, so the session does not have to make them at 11 p.m.

**Copy Crucible's configuration; do not fork it.** Take: the Next config and static-export
settings, the MDX pipeline (remark/rehype set), the Shiki setup, the Tailwind v4 theme with
the token copy, the fonts, `ThemeProvider` and the theme toggle, `amplify.yml`, lint and
format config. Leave: every post, every benchmark, every chart specific to a benchmark, the
Google Benchmark harness, and anything named Crucible. If Crucible has a snippet-extraction
component, reuse it; if not, build the one described below.

**Node 22, pinned.** `.nvmrc` and `engines`. The last portal session found Node 18 locally
against Next 16's floor of 20.9.

**Routes.** `/` is the index. Pages live at `/{part-slug}/{page-slug}` — for example
`/stochastic-calculus/quadratic-variation`. Part slugs: `orientation`, `products`,
`stochastic-calculus`, `implementation`, `later`. `/template` exists only in preview.

**`src/data/curriculum.ts` is the single source of truth**, mirroring the portfolio's
`projects.ts`. It exports `parts` and `pages`. A page carries `id` ("2.3"), `slug`, `part`,
`title`, `summary` (one line, from `index-v1.md`), `status: "tbc" | "draft" | "published"`,
and optional `demos: DemoId[]`. Prose lives in `content/{part-slug}/{page-slug}.mdx` and is
looked up by slug; MDX carries no frontmatter — the curriculum entry is authoritative. Part 4
is a part with no pages and a `note` listing the v2 candidates; it renders as a paragraph.

**Gating.** `generateStaticParams` emits `published` pages, plus `draft` when
`process.env.PREVIEW === "1"`. The index lists every page: `tbc` greyed, unlinked, labelled
TBC; `draft` shown only in preview; `published` linked. In production the curriculum tree
renders only if at least one page is `published`; otherwise the index is the holding page.
Sitemap: published only. Preview builds set `robots: { index: false }`.

**Maths.** `remark-math` + `rehype-katex` at build time, KaTeX CSS bundled, no client JS for
equations. A small macro file, `src/lib/katex-macros.ts`, so `\dW`, `\E`, `\Q` render
identically on every page. Keep it to what the template page uses.

**Snippets.** A `<Snippet file="..." lines="a-b" />` server component reads
`snippets/<file>` at build time and renders it through the Shiki pipeline. Every file in
`snippets/` must run: `npm run check:snippets` executes each with `python3`. No prose-only
code anywhere on the site.

**Demos.** `src/demos/` holds a `PricingBackend` interface, a `tsBackend.ts` implementation,
a `registry.ts` mapping demo ids `D1`–`D10` to components, and a `<Demo id="D1" />` client
component that dispatches by id. Only D1 is implemented; the others render a "not built"
placeholder in preview and are never referenced by a published page. Define only what D1
needs in the interface (`uniforms(seed, n)`, `normals(seed, n)`), with a comment that it grows
with the demos. D1 draws on a 2D canvas via `requestAnimationFrame`: a step-count control
(10 → 100 000), a seed input, and a zoom control that shows self-similarity. No D3 for D1.

**Shared RNG — specified here so the C++ port matches later.** Generator: xoshiro128\*\*
(Blackman & Vigna reference implementation). Seed expansion: fmix32, the MurmurHash3
finaliser, applied to `seed + i` for `i` in 0..3, rejecting an all-zero state. Uniform
double from two outputs: `((hi >>> 5) * 2^26 + (lo >>> 6)) * 2^-53`. Normals by inverse CDF
using AS241 (Wichura, PPND16) — pure rational approximations, no `erfc` needed, portable.
Write `docs/rng.md` stating all of this with the constants, and record known-answer vectors
(first ten uniforms and first ten normals for seeds 1, 42 and 2^31−1) in
`src/demos/__fixtures__/rng-known-answers.json`; `npm test` checks them. The Touchstone
library will copy the fixture and pass the same test.

**Checks.** `src/checks/` with a typed schema: `prompt`, `options`, `correct` index,
`feedback` per option, `misconception` tag. Questions live beside the page as
`content/{part-slug}/{page-slug}.checks.ts`. Client component; feedback for the chosen option
appears after answering; progress in localStorage under `learn:progress:v1`; a reset button on
the index. No accounts, no network.

**Tests.** Add `vitest` with three suites: RNG known answers; gating (which statuses emit in
each mode); curriculum integrity (unique ids and slugs, every `.mdx` under `content/` has a
curriculum entry and every non-`tbc` entry has an `.mdx`).

**Copy.** Two texts, both owner-may-edit, both used verbatim until edited.

Holding page (production, until first publication):
> Derivatives for developers who work alongside quants. In progress.

Landing paragraph (index, once the tree renders):
> Derivatives for developers who work alongside quants. What the products are and why they
> exist, how they're priced and risked, and what happens to a trade over its life — then the
> stochastic calculus behind the option pricers, taught at engineer's level: every rule
> verified numerically before it's derived, every page with a check that fails if you've
> misunderstood it.

Site title: "Derivatives for developers". Meta description: the holding-page line. No mention
of Touchstone anywhere on the site until the library exists.

**Analytics.** Umami script wired to `NEXT_PUBLIC_UMAMI_ID`; a no-op when unset.

**Licence.** None until the decision is made. `README.md` carries a one-line reminder to add
`LICENSE` (code) and a prose licence before the repo goes public.

Overrule any of the above if you disagree; each is a judgement, not a finding. Record the
change and the reason in the log.

## Curriculum data (populate `curriculum.ts` from this; summaries from `index-v1.md`)

| id | part | slug | title |
|---|---|---|---|
| 0.1 | orientation | why-derivatives-exist | Why derivatives exist |
| 0.2 | orientation | linear-vs-nonlinear | Linear vs nonlinear |
| 0.3 | orientation | conventions | Conventions |
| 1.0 | products | cash-and-discounting | Cash and discounting |
| 1.1 | products | forwards | Forwards |
| 1.2 | products | futures | Futures |
| 1.3 | products | swaps | Swaps |
| 1.4 | products | options | Options |
| 1.5 | products | trade-lifecycle | The trade lifecycle and the risk system |
| 2.1 | stochastic-calculus | random-walks | Random walks and scaling |
| 2.2 | stochastic-calculus | brownian-motion | Brownian motion |
| 2.3 | stochastic-calculus | quadratic-variation | Quadratic variation |
| 2.4 | stochastic-calculus | ito-integral | The Itô integral |
| 2.5 | stochastic-calculus | ito-lemma | Itô's lemma |
| 2.6 | stochastic-calculus | sdes-and-gbm | SDEs and geometric Brownian motion |
| 2.7 | stochastic-calculus | delta-hedging-and-the-pde | Delta hedging and the Black–Scholes PDE |
| 2.8 | stochastic-calculus | risk-neutral-pricing | Risk-neutral pricing |
| 2.9 | stochastic-calculus | black-scholes-formula | The Black–Scholes formula |
| 2.10 | stochastic-calculus | greeks | Greeks |
| 2.11 | stochastic-calculus | where-it-breaks | Where it breaks |
| 3.1 | implementation | closed-form-in-code | Closed form in code |
| 3.2 | implementation | monte-carlo | Monte Carlo |
| 3.3 | implementation | finite-differences | Finite differences |
| 3.4 | implementation | implied-vol-and-the-surface | Implied vol and the surface |
| 3.5 | implementation | greeks-in-practice | Greeks in practice |
| 3.6 | implementation | in-the-system | In the system |
| 3.7 | implementation | reading-quantlib | Reading QuantLib |

All `tbc`. Demo ids per page are in `index-v1.md`'s demo list (D1 → 2.1 and 2.2, and so on).
Part 4 (`later`) carries the v2 candidate list from `index-v1.md` as its `note`.

## Steps

1. **Bootstrap.** New Next app matching Crucible's versions; copy the configuration listed
   above; tokens copied per the companion-site rule; `.nvmrc`; `amplify.yml`. Build once,
   empty, before adding anything.
2. **Curriculum.** `curriculum.ts` from the table; `content/` directory tree with no files
   yet except the template's.
3. **Index.** Holding page vs curriculum tree per the gating rule; parts as sections; page
   rows with id, title, summary, status treatment; the reset-progress control.
4. **Pipeline.** MDX with KaTeX and macros; the `Snippet` component; `snippets/random_walk.py`
   (a random walk in numpy, ten to fifteen lines, printing variance against step count);
   `check:snippets` script.
5. **Demo D1.** Interface, `tsBackend` with the RNG as specified, registry, `Demo`
   component, the canvas renderer, `docs/rng.md`, the known-answer fixture.
6. **Check component** and the template's three questions (placeholder questions about the
   random walk are fine — they are not curriculum content).
7. **`/template`** — heading, one placeholder paragraph clearly marked as placeholder, Itô's
   lemma in display maths, the snippet, D1, the check. Preview only.
8. **Gating, sitemap, robots.** Both build modes; the three vitest suites.
9. **README** — what the site is, the stack, commands, both build modes, the gating rule,
   the licence reminder, and the relationship to Touchstone and the portfolio.
10. **Verify and log.** Both builds; screenshots of index and `/template`, light and dark;
    tests and snippet check green. Write the session log entry below.

## Not in scope

- Any curriculum content beyond `/template`. No Part 2 prose, no real questions.
- Demos D2–D10, the WASM backend, the Touchstone library, the exercises repo.
- Portfolio changes (project card, nav item). Separate brief, gated on publication.
- Amplify app, custom domain, preview branch, Umami site — owner actions, below.

## Owner actions

Before the session: create `touchstone` (public, MIT licence) and `touchstone-learn` (private); clone
them side by side; put `CONSTITUTION.md` and `ROADMAP.md` at the root of `touchstone` and
`index-v1.md` and `tech-decisions-v1.md` in `touchstone/docs/`; drop this brief into
`touchstone-learn/docs/briefs/S0-learn-site-scaffold.md`; commit both repos to `master`;
install Node 22 locally; open the session on a folder that contains both repos.

After the session: commit and push; create the Amplify app on the repo with `master` as
production; add the custom domain `learn.garethcooke.com`; add a `preview` branch deploy with
environment variable `PREVIEW=1`; create the Umami site and set `NEXT_PUBLIC_UMAMI_ID`; open
both deployments and check the holding page and the preview index.

## Session log

### YYYY-MM-DD · model · one-line summary

**Done** — what shipped, by step.
**Decisions (with why)** — anything that overrode this brief, and owner decisions taken
mid-session.
**Not done** — what was left, and why.
**Exact next step** — the first thing the next session or the owner does.
