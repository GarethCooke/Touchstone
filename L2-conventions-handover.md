# Handover — L2 conventions pass: Leibniz partials + cross-reference links

Executor: Opus / Claude Code, in `touchstone-learn` on branch `m/L2`.
Owner rulings (2026-09-29): notation split rule; every cross-reference is a link.
Protocol: P1 first — read `touchstone/CONSTITUTION.md` and `touchstone/ROADMAP.md`.
Scope is formatting only. Do not reword the owner's Part 2 prose beyond the notation and link changes below.

## Ruling 1 — derivative notation (split rule)

- Function of x alone: primes. `g'(x)`, `g''(x)` → g′, g″. Unchanged where already used.
- Function of t and x: Leibniz partials. `\frac{\partial f}{\partial t}`, `\frac{\partial f}{\partial x}`, `\frac{\partial^2 f}{\partial x^2}`.
- Retire subscript partials everywhere: f_t, f_x, f_xx, f_{xx}, and variants on other letters.
- Differentiate with respect to the placeholder x, never W or S. Write ∂f/∂x evaluated at (t, W_t), not ∂f/∂W.
- Keep a (drift) and b (volatility). They are glossed at first use.
- Put dt before dW in drift-plus-noise lines (S5 ruling). Taylor expansions stay in power order.
- The number of terms does not change. This is a notation change only.

Canonical lemma (KaTeX):

```latex
df = \left( \frac{\partial f}{\partial t} + a\,\frac{\partial f}{\partial x} + \tfrac{1}{2} b^2 \frac{\partial^2 f}{\partial x^2} \right) dt + b\,\frac{\partial f}{\partial x}\, dW
```

If a display overflows at 380px width, break it after the `dt` term with `aligned`. Do not revert to subscripts to save width.

Worked examples, same notation:

```latex
d(W^2) = dt + 2W\,dW
d(\log S) = \left(\mu - \tfrac{1}{2}\sigma^2\right) dt + \sigma\,dW
d\!\left(e^{W - t/2}\right) = \left(-\tfrac{1}{2} f + \tfrac{1}{2} f\right) dt + f\,dW = f\,dW
```

The session that produced these examples set f = x², log x and e^{x−t/2} respectively. Check each against 2.5 as drafted and keep the page's own intermediate lines.

## Ruling 2 — every cross-reference is a link

- Any mention of another page or section becomes a link to that page, and to the heading anchor when the mention points at a specific part. Mentions include "2.4", "page 2.3", "2.4's", "Into 2.5", "see 0.3", and "Part 2".
  - Example: in "…and why 2.4's −½T was just one…", link "2.4's" to the 2.4 page, at the anchor of the section where −½T appears if that section has a heading.
- Take routes and anchors from the site's own route source (`routable.mjs` / the page manifest). Do not hand-build slugs.
- A reference to a page that is not routable yet (tbc) stays plain text. List it in the evidence pack. It must not break the production build.
- Apply the links in both the site MDX and the matching `drafts/*.md`, using the same link syntax, so the next conversion is mechanical.
- Link text stays as written. Do not reword it to "click here" or similar.

## Deliverables

1. Sweep every draft in `drafts/` and every site MDX page for Ruling 1. Report each file and the number of lines changed.
2. Sweep the same files for Ruling 2. Report the links added and any left plain because the page is tbc.
3. Add a "Derivatives" section to page 0.3 Conventions. Use the proposed text below. It is marked for owner approval, so do not treat it as final.
4. Append ledger rows to `drafts/notation.md` for ∂f/∂t, ∂f/∂x, ∂²f/∂x² (born: 2.5) and a retirement note for subscript partials.
5. Extend `npm run check:notation` in report-only mode, as it is now:
   - Flag subscript partials (`f_t`, `f_x`, `f_{xx}` and similar on any single letter).
   - Flag unlinked page references (a bare `\b\d\.\d{1,2}\b` in prose outside links, headings and maths).
6. Build a static export and confirm it passes. Check 2.5 and 0.3 at 380px width.
7. Update the evidence pack at `touchstone/docs/evidence/L2/` with what changed, the tbc list and the build result.
8. Write the commit message, matching the repo's convention, to `.git/l2-conventions-commit-msg.txt` in each repo touched. Do not commit. The commit is the owner's.

## Proposed 0.3 text (owner to approve)

> ### Derivatives
>
> A function of one variable gets primes: g′(x), g″(x). Once time enters, as in f(t, x), we switch to partial derivatives: ∂f/∂t, ∂f/∂x, ∂²f/∂x². The switch itself tells you f depends on t as well as x.
>
> We always differentiate with respect to the placeholder x, then evaluate along the path: ∂f/∂x at (t, W_t), never ∂f/∂W.
>
> In this notation, [Itô's lemma](2.5 link) reads:
>
> [canonical lemma display]
>
> where a is the drift and b the volatility. Drift-plus-noise lines always put dt before dW.

## Out of scope

- Any rewording of Part 2 prose beyond the two rulings.
- ROADMAP.md edits. These are owner actions under I18/A1. Propose them in the pack if needed.
