# L5 entry — the owner's rulings (2026-11-19)

Nine items were put to the owner on the rulings page "L5 entry rulings"
(`https://claude.ai/artifact/AksWLQoVwc6rXwk79B79X7`) before anything of L5 was drafted or built.
He answered at 14:38 UTC on 2026-11-19 with the recommended option on every item. This note is
the record: his answer, each question with the option he chose, and the edits the answers make
in this repository.

## His answer, verbatim

````text
L5 entry rulings, 19 November 2026
drafting: A
code-shown: A
numbers: A
length: A
page-3-7: A
american: A
library-release: A
d9-market-data: A
numpy-pin: A
````

## The questions, and the option he chose

### `drafting` — Who drafts pages 3.1 to 3.7

Who writes the first draft of Part 3’s seven pages?

**A.** Fable sessions draft them, as for Part 1: 3.1 with 3.2, 3.3 with 3.4, 3.5 with 3.6, and 3.7 alone. Each session gives you a rulings page. The roadmap’s L5 entry gains “Fable drafts for 3.1–3.7”, which is your edit; I give you the paste.

### `code-shown` — What code a Part 3 page shows

When 3.1 shows how N(x) is computed, or 3.3 shows a time step of the grid, what does the reader see?

**A.** The library’s own C++, copied into the site at the pinned release and shown by line range. The site’s check holds each copy to that release by its hash. Python appears only for an experiment script (next item) and for the QuantLib generators on 3.7.

### `numbers` — What holds a Part 3 page’s numbers

Where does a number printed on a Part 3 page come from, and what fails if it is wrong?

**A.** Three sources, in this order. First, a site test that runs the library’s browser build and holds the page’s number to its output. Second, where the claim is about the library itself, the library’s own test or committed file, cited (the golden file, the timings in ARCHITECTURE.md). Third, an experiment script with a result file, only for a number the library cannot produce: the explicit scheme going unstable on 3.3, a control variate on 3.2.

### `length` — How long a Part 3 page is

What length should a drafting session aim at?

**A.** The same as Part 1: 1,300 to 1,800 words of prose a page.

### `page-3-7` — Page 3.7, “Reading QuantLib”

Is that summary right for 3.7, and does the index get a line for it? The index is yours to edit; I give you the paste.

> How the QuantLib-Python oracle generates the golden values, and how to read the library those values come from.

**A.** Keep the summary as it is, and add it to the index as 3.7’s line.

### `american` — American options on 3.3

What does 3.3 say about American options, and do the two sentences change?

**A.** 3.3 has a section on early exercise, with numbers from the library’s grid, and D8’s heatmap gets a European and American switch. The two sentences change as worded above. I21 is amended to allow American exercise on the grid alone, which is your action; I give you the wording.

### `library-release` — What the library’s browser build is missing

Does the library change before L5 starts, and if so by how much?

**A.** One library session before L5’s first: Opus in Touchstone, a new milestone in the roadmap (your edit; I give you the paste), released as v1.1.0. It exports the payoff, N(x) and the density; adds a function that returns many paths from one seed; adds a closed-form entry that takes arrays of spot and time, for D5; and exports the Newton–Brent solver. The session proposes the exact signatures and you rule on them, as at T3a. L5 then vendors v1.1.0, every demo runs on the library, and the index’s sentence “From L5 every demo runs on the WASM build of the library” is true as written, D11 included. ARCHITECTURE.md changes, so the portfolio’s Touchstone write-up is refreshed afterwards.

### `d9-market-data` — D9 and a snapshot of Deribit’s market

Is a Deribit snapshot still wanted for D9?

**A.** No snapshot in v1. D9 keeps its generated smiles, and 3.4 describes a real smile in words with a cited source. The roadmap’s L5 entry loses “with a Deribit fixture (I7)”, and its exit line “D9’s fixture carries source and date” is met by the generated fixture. Both are your edits; I give you the paste.

### `numpy-pin` — The numpy version the site’s build installs

Is numpy pinned in the site’s build?

**A.** Yes: pinned to 2.5.2 in L5’s first batch, one line.

Under `american`, "the two sentences change as worded above" refers to this wording, shown to him
on the page:

- Page 0.0: "Everything in Parts 2 and 3 is done for one underlying, with a constant rate, a
  constant volatility, a dividend yield and European exercise. The one exception is 3.3, where
  the finite-difference grid also prices an American option."
- Page 0.3, the row for European and American: "Parts 2 and 3 price European options only, except
  the grid on 3.3, which also prices an American one."

Both pages are `touchstone-learn`'s and change in the batch that publishes 3.3.

One thing the page told him was wrong, and is corrected in the edits. It said the roadmap's exit
line "D9's fixture carries source and date" is met by the generated fixture. That fixture carries
its source and the source's SHA-256 and no date, so the exit line is reworded to say so.

## The edits

9 edits in three files. Each "Replace" text occurs exactly once in its file. Nothing else
changes. They were applied to a clone at `2a05686` before this note was written.

### 1 · `CONSTITUTION.md` — I21

Replace:

````text
- **I21 — v1 scope is fixed.** European vanillas, one underlying, constant rate and
  volatility, dividend yield. Anything else is Part 4 and enters only by amendment.
````

With:

````text
- **I21 — v1 scope is fixed.** European vanillas, one underlying, constant rate and
  volatility, dividend yield; and American exercise of the same vanillas on the
  finite-difference grid alone. Anything else is Part 4 and enters only by amendment.
````

### 2 · `CONSTITUTION.md` — A12, added after A11 as the last line of the file

Replace:

````text
  proposed by tollgate P2 and declined by the owner on 2026-11-16; the number is not reused.
````

With:

````text
  proposed by tollgate P2 and declined by the owner on 2026-11-16; the number is not reused.
- **A12** · 2026-11-19 · I21 · European vanillas, one underlying, constant rate and volatility,
  dividend yield → the same, and American exercise of the same vanillas on the
  finite-difference grid alone · reason: the library's grid has priced the American contract
  since T3, held to QuantLib's lattices in `golden/american_vanilla.json`; the index's line for
  3.3 names early exercise; and page 3.3 and D8 are to show it. The closed form, the Monte
  Carlo, implied volatility and every other page stay European · authority: owner, 2026-11-19.
````

### 3 · `ROADMAP.md` — Tracks

Replace:

````text
- **T — Touchstone library** (`touchstone`, Opus): T0–T5.
````

With:

````text
- **T — Touchstone library** (`touchstone`, Opus): T0–T6.
````

### 4 · `ROADMAP.md` — Suggested order

Replace:

````text
L2 (once S11 is done) → L4a → L3 → P1 → L4b → T3a → T4 → T5 → L5 → P2 → L6.
````

With:

````text
L2 (once S11 is done) → L4a → L3 → P1 → L4b → T3a → T4 → T5 → T6 → L5 → P2 → L6.
````

### 5 · `ROADMAP.md` — Dependency map, L5

Replace:

````text
| L5 | L3, T3, T4 |
````

With:

````text
| L5 | L3, T3, T4, T6 |
````

### 6 · `ROADMAP.md` — Dependency map, T6

Replace:

````text
| T5 | T4 |
````

With:

````text
| T5 | T4 |
| T6 | T5 |
````

### 7 · `ROADMAP.md` — L5's entry

Replace:

````text
**Entry:** L3, T3, T4.
**Deliverables:** `wasmBackend` behind `PricingBackend` (I15), carrying every demo: D1–D6
and D9 move onto it from the TypeScript backend; D7 Monte Carlo convergence
with error bars; D8 PDE grid heatmap; D9 implied-vol solver and smile viewer with a Deribit
fixture (I7); D10 bump-and-revalue risk table; pages 3.1–3.7, drafted with the owner per I2.
**Exit:** TS and WASM backends agree on every known-answer and demo test within tolerance;
the TypeScript numerics are then removed and the suite runs on WASM alone (A6);
D9's fixture carries source and date; pages `published` after owner review.
**Tollgate:** F. **Executor:** Opus. **Size:** three sessions.
````

With:

````text
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
````

### 8 · `ROADMAP.md` — T6's entry, added after T5's and before Track P

Replace:

````text
comment that cites the roadmap or the constitution as its authority counts as history.

## Track P — Portal (portfolio repo)
````

With:

````text
comment that cites the roadmap or the constitution as its authority counts as history.

### ☐ T6 — What the demos need from the browser build
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
````

### 9 · `docs/quant-learn-index-v1.md` — 3.7's line, added after 3.6's

Replace:

````text
  batch; P&L explain; model validation; why the quant's library has separate model and
  calibration layers.
````

With:

````text
  batch; P&L explain; model validation; why the quant's library has separate model and
  calibration layers.
- **3.7 Reading QuantLib.** How the QuantLib-Python oracle generates the golden values, and how
  to read the library those values come from.
````

## What the rulings change outside these three files

- **This repository:** milestone T6, whose brief is `docs/briefs/T6-browser-build-needs.md`.
- **`touchstone-learn`, at L5:** everything in the note under L5's roadmap entry; the two sentences
  above; 3.7's summary in `curriculum.ts`, which stands as it is; numpy pinned to 2.5.2 in
  `amplify.yml`, the version in this repository's `uv.lock`.
- **The portfolio:** its write-up of this repository is refreshed after T6 changes
  `ARCHITECTURE.md`.
