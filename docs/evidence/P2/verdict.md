# P2 — tollgate verdict

Tollgate P2 · 2026-11-16 · Fable review per constitution §6: bounded claims.
Reviewer: a fresh Fable session in the owner's Claude Project (configured model id
`claude-fable-5-2`), which built none of P2 and changed nothing.

**Basis.** §6's prompt names `docs/evidence/P2/summary.md`. P2 has none: it was built in
`garethcooke-portfolio`, whose convention is the brief. Read in its place:

- `CONSTITUTION.md` and the P2 entry of `ROADMAP.md`, in `touchstone` at `804ffdf`.
- `docs/briefs/P2-touchstone-portal.md` in `garethcooke-portfolio` at `543d82a`, in full.
- The card's data in `src/data/projects.ts`, and `src/app/touchstone/architecture/page.tsx`
  and `diagrams.tsx`, in full, at `543d82a`. §6 says a tollgate does not re-read the
  codebase; with no pack, the page's source was the only place to read what is rendered.
- `ARCHITECTURE.md` at `c7b8705` in full, and its claims map `docs/evidence/T5/claims.md`.
- The two live pages, `garethcooke.com/projects/touchstone` and
  `garethcooke.com/touchstone/architecture`, in the owner's Chrome.

The portfolio could not be attached to the cloud session. `master` at `543d82a` was read
from the git objects in the owner's connected folder, whose working tree was on
`p1-touchstone-nav`. `src/lib/` was read from that working tree.

Re-established rather than taken on trust:

- **The drift check.** `check:writeups`, run on `543d82a` against `touchstone` at `804ffdf`:
  `/touchstone/architecture` is `ok` at `c7b8705`. `c7b8705` is on `main` and is the last
  commit to touch `ARCHITECTURE.md`; the two before it are `739ac3c` and `cbbfd72`.
- **The live page is `master`.** `543d82a` built in the cloud with stand-in fonts gives the
  write-up's text as 26,567 characters, SHA-256 `ae7da7cd…8e7947` after whitespace is
  collapsed. The live page gives the same length and the same hash. The live card's
  description, overview and six key decisions read word for word as `projects.ts` has them.
- **Every number on the write-up.** 201 tokens that hold a digit, each compared with the
  source: none is on the page that the source lacks, apart from section references and the
  notes' "1.0.0". None of the source's is missing, §10.3's tables aside, which the brief
  has summarised.
- **Every "independent", "always", "never", "every", "any", "all", "only", "each", "no" and
  "nothing".** 110 sentences on the write-up hold one. 49 are the source's sentence
  verbatim; the other 61 were read against it one by one, and 60 are the source's sentence
  re-cut, a table cell, a heading, a caption or one of the page's own notes. The one that
  claims more than the source is defect 1. On the
  card every number and every such sentence was checked against `ARCHITECTURE.md` and the
  claims map; defects 1 to 6 are what did not hold.
- **The links.** The write-up's 78 outside links all go to `github.com/GarethCooke/Touchstone`,
  and each of the 43 paths in `REPO_FILES` exists on `main`. Neither page names
  `learn.garethcooke.com`. The card's three buttons go to the repository, to
  `/touchstone/architecture`, and to
  `touchstone.garethcooke.com/stochastic-calculus/black-scholes-formula#demo-d6`, which
  opens page 2.9 with the D6 pricer in view.
- **Light and dark.** Both live pages read in dark and in light at desktop width. On the
  cloud build, in both themes at 1,440 px and at 390 px: no page overflows sideways; at
  390 px three tables and both figures scroll inside their cards, as the owner ruled on
  2026-11-14, and nothing is clipped.

## Verdict

**PASS WITH DEFECTS.** Given at `garethcooke-portfolio` `543d82a`. Eight defects: two
medium, six low. Seven are wording or comments and one is the record. None is in
`ARCHITECTURE.md`, and none is in what the write-up renders from it below its opening
sentence.

- **The page passes the site's drift check — pass.** The manifest's `refreshedAt` is
  `c7b8705`, and the page renders the source as it stands there: T5's completed row, §11's
  second row.
- **Claims bounded — pass with defects.** The write-up holds §1's register. It gives "What
  is claimed" and "What is not" complete and near the top, each figure with its condition,
  and the three methods' independence with its qualification. The card's overview does the
  same for the reference file, the resolution, the scored rows and the timings' machine.
  The defects are six sentences on the card and one on the write-up that say more than the
  source, or other than it.
- **Light and dark verified — pass.**
- **Deliverables — pass.** The entry sits after Temper and before MorayGlow, with "View
  source", "Design & architecture" and "Open the tool"; the manifest has its entry.
- **I11 — pass.** The card went live after T5's tollgate, and the link to the tutorial
  after L3.

The known points, ruled:

- **"In progress".** Still true: 13 of the tutorial's 27 pages are unwritten. Stands.
- **"Open the tool".** The button works. The overview says the tutorial's demos run on a
  TypeScript backend at 1.0.0. It does not say that the button opens one of them. Defect 2.
- **The comment at lines 54–56 of the write-up's page.** Corrected: defect 7.
- **Whether the write-up should now name the tutorial's address.** Yes, as the source does,
  and as a link. The source's sentence is "The other half is touchstone.garethcooke.com, a
  tutorial whose demos…". The page left the name out for one reason, I11 before Part 2 was
  published, and that reason ended at L3. The site's menu and the card both link the
  tutorial now. This reverses the P2 brief's "named in prose without a link", so it is the
  owner's to accept; the defects brief carries it as an item he can strike.

## Defects

Against the exit criterion "claims bounded" and §1's register, except 8, which is against
P5 and P7.

1. **The opening sentence, in four places — medium.** "…and holds the three to each other
   and to QuantLib's reference values." The Monte Carlo is not held to QuantLib's values:
   `tests/test_monte_carlo.cpp` holds it to the closed form (claims 9 and 144), and
   `ARCHITECTURE.md` §1 and the README both say so. The sentence is the card's
   `description`, which is also all the projects index shows; the write-up's opening line;
   and, shortened, the write-up's `description` and Open Graph text. Fix: "holds the closed
   form and the grid to QuantLib's reference values, the Monte Carlo to the closed form, and
   the three to each other".
2. **The card's overview, last paragraph — medium.** Nothing on the card says what "Open the
   tool" opens. The card is the library's; the button opens the tutorial's pricer, which
   runs on the tutorial's TypeScript until L5. A reader who presses it can take the pricer
   for the library. The owner's ruling of 2026-11-14 put the button in on the footing that
   the overview says so. Fix: one sentence after "…they run on a TypeScript backend." The
   sentence comes out again when L5 moves the demos.
3. **Key decision 3 — low.** "The test that holds this passes by failing to compile." The
   test passes by compiling. `ARCHITECTURE.md` §6 has "`tests/test_contract.cpp`, which
   fails by not compiling", and the test's own comment says a change that lets an American
   contract through "fails to compile this file". Fix: "The test that holds this fails by
   not compiling."
4. **The card's overview, fifth paragraph — low.** "The library has rules of its own, each
   held by a named test." Rule 6, no dependency, is held by two CMake files and the include
   lists (claim 90, marked "Source"), not by a test. The source and the write-up both say
   "the test or file". Fix: "each held by a named test or file".
5. **The card's overview, the timings — low.** The five figures travel with the machine,
   the compiler and "one date", and without the input. §7 times one option, a call struck
   at 100 with a year to expiry on a spot of 100, and says its figures say nothing "about
   inputs other than the one above". Fix: name the option.
6. **Key decision 1 — low.** "A mistake in one of them shows up as a disagreement with a
   number on it." Not where the mistake is in code the methods share. The source of the
   reasoning, `tests/test_three_way.cpp` (claim 150), says "a mistake in a shared piece
   shows only against a method that does not share it". Fix: carry that clause.
7. **Four comments in the write-up's source — low, not rendered.** `page.tsx` lines 26 and
   694 and `diagrams.tsx` line 20 give `cbbfd72` as the source commit, as "the last commit
   to touch the file" and as "the manifest's refreshedAt commit"; it is none of them since
   the two refreshes that followed. `page.tsx` lines 54–56 explain the missing address by
   I11, which no longer bars it. Fix: the comments name the manifest and no commit, so that
   a refresh cannot leave them behind; lines 49–56 are rewritten to what is now true.
8. **The record — low.** P2 has no evidence in either repository. The brief has no session
   log, where P1's has one. Its screenshots and its figure-by-figure list, which the brief
   says "the tollgate reads first", are not in the repository.
   Its Acceptance and Out-of-scope sections still say "no `liveUrl`" and list "the 'Open
   the tool' link" as out of scope, against its own first decision. Fix: a session log in
   the brief from what the commits and pull requests #3 and #4 show, and the two lines
   brought into step with the ruling.

Not defects, for the record.

- Key decision 4 gives `require_valid`'s reason for all three pairs of overloads. The
  source says the other two stay for the family's sake. The card claims nothing false.
- Key decision 2 says "a committed reference file" where there are two. It says less than
  the source, not more.
- `docs/evidence/T5/claims.md` row 6 in `touchstone` still names `learn.garethcooke.com`.
  It is T5's record and the live write-up links to it. The owner's, if he wants it changed.
- The owner's portfolio folder is on `p1-touchstone-nav`, which is merged. The defects
  brief branches from `origin/master`.
- The cloud build used stand-in fonts and had no `public/` folder, so its screenshots show
  layout and theme and not the real typeface. The live pages were read at desktop width
  only: the owner's Chrome window did not resize.

## Amendments

One proposed, for the owner to rule.

- **A10 · P5, P7, §6.** Before: every milestone's evidence pack is
  `docs/evidence/<milestone>/` in the executing repository, and the tollgate reads its
  `summary.md`. After: the same, and for a Track P milestone the pack is the portal brief
  and its session log in the portfolio's `docs/briefs/`; the session log records the light,
  dark and 390 px checks and where their screenshots are; the verdict is saved in
  `touchstone/docs/evidence/<milestone>/verdict.md`. Reason: P1 and P2 were both built that
  way, ROADMAP's P1 line already cites the brief as its evidence, and this tollgate had to
  be told what to read in the pack's place. Authority: tollgate P2, if the owner accepts.

## Unlocks

- **P2's tick,** once the defects are closed in `garethcooke-portfolio`. This file is saved
  by the tick.
- **L6's entry** then waits on L4 and L5 alone: P1 and P2 are done.
- **Next: the Part 1 drafts, 1.0–1.5,** which are L4b's entry and do not yet exist. First
  step: a fresh Fable session in the Project drafts 1.0 from `docs/quant-learn-index-v1.md`
  for the owner's review, by the L4a drafting session's pattern.
