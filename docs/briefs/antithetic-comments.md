# Three comments on the antithetic standard error — brief

For Claude Code in `Touchstone`, Sonnet 5.5, effort low, ultracode off, one session. To run
after T6 has merged and `v1.1.0` is tagged. Written 2026-11-20 by the first Part 3 drafting
session (claude-fable-5-2).

## Why

The owner ruled on 2026-11-20, on the page "Part 3 rulings 3.1–3.2", item `antithetic-3-2`:
"A (A paste for Claude Code in Touchstone corrects the three comments, after T6 has merged)".

Three comments say that an antithetic standard error computed from the paths, and not from
the pairs, is too small. For a vanilla, which is all the library prices, it is too large.
The two halves of a pair are negatively correlated, so the pair mean varies less than two
independent paths, and a standard error that leaves that correlation out is the plain
estimator's: it hides the improvement. It is too small only where the halves are positively
correlated, as for a straddle. `experiments/3_2_variance_reduction.py` measures both: for
the call, 0.173 from the paths against a spread of 0.145 over 1,600 runs; for a straddle,
0.155 from the paths against a spread of 0.201.

The code is right and so is every assertion. Only comments change. No number moves, and no
test is added, removed or changed.

## The three edits

Each is an exact replacement. If a Replace block is not found exactly once, stop and report.

### 1. `include/touchstone/monte_carlo.hpp`, the comment on `antithetic`

Replace:

```
    /// The sampling unit is then the *pair*, not the path, and the standard
    /// error is computed from pair means. Computing it from the paths instead
    /// would ignore the very correlation the technique creates and report an
    /// error bar that is too small — the failure mode where a variance
    /// reduction makes the answer look better than it is.
```

With:

```
    /// The sampling unit is then the *pair*, not the path, and the standard
    /// error is computed from pair means. Computing it from the paths instead
    /// would ignore the very correlation the technique creates and report an
    /// error bar that is not the estimator's. For a vanilla, whose halves are
    /// negatively correlated, it would be too wide: plain sampling's bar, with
    /// the improvement hidden. For a payoff whose halves move together it
    /// would be too narrow.
```

### 2. `tests/test_monte_carlo.cpp`, in "the standard error is the spread of the estimator"

Replace:

```
        // be what the standard error said it would be. This is the test that
        // catches an antithetic standard error computed from paths rather than
        // from pairs — the failure mode where a variance reduction makes the
        // answer look better than it is, which no comparison against a closed
        // form would notice, because the estimate itself stays correct.
```

With:

```
        // be what the standard error said it would be. This is the test that
        // catches an antithetic standard error computed from paths rather than
        // from pairs — an error bar that is not the estimator's, too wide for
        // a vanilla because it leaves out the pair's negative correlation —
        // which no comparison against a closed form would notice, because the
        // estimate itself stays correct.
```

### 3. `ARCHITECTURE.md` §5, the Monte Carlo paragraph

Replace:

```
the sampling unit is the pair, and the standard error is computed from pair means, so that
the variance reduction does not also shrink the error bar it is judged by. An Euler path may
```

With:

```
the sampling unit is the pair, and the standard error is computed from pair means, so that
the error bar is the estimator's own and not plain sampling's. An Euler path may
```

## Check

- `git diff --stat` names those three files and no other.
- The library builds and `ctest` passes as it did before the change.
- `grep -rn "too small — the failure\|look better than it is\|judged by" include src tests ARCHITECTURE.md` prints nothing.

## Commit

On a branch `fix/antithetic-comments` from `main`, one commit, pushed, with a pull request
for the owner to merge. Do not push to `main`. The message:

```
Monte Carlo: three comments on the antithetic standard error say which way it is wrong

An antithetic standard error computed from the paths, and not from the
pairs, is not too small for a vanilla: it is too wide. The two halves of a
pair are negatively correlated, and a standard error that leaves that out
is plain sampling's, with the improvement hidden. It is too narrow only
for a payoff whose halves move together. experiments/3_2_variance_reduction.py
measures both: 0.173 against a spread of 0.145 for the call, 0.155 against
0.201 for a straddle.

The comment on MonteCarloSettings::antithetic, the comment in "the standard
error is the spread of the estimator", and one sentence of ARCHITECTURE.md
§5. Comments and prose only: no code, no assertion and no number changes.

The owner's ruling of 2026-11-20 (Part 3 rulings 3.1-3.2, antithetic-3-2: A).
```

`ARCHITECTURE.md` changes, so the portfolio's `/touchstone/architecture` page will report
drift at `npm run check:writeups`; that refresh is already row 11 of the L5 handover.

## Report

The commit, the pull request's number, the `ctest` line, and `git status`.
