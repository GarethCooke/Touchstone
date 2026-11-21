# Gamma's default bump: say why it is the default, and hold it — brief

For Claude Code in `Touchstone`, Sonnet 5.5, effort low, ultracode off, one session. Written
2026-11-21 by the third Part 3 drafting session (claude-fable-5-2), against `main` at
`1faeac8`.

## Why

The owner ruled on 2026-11-21, on the page "Part 3 rulings 3.5–3.6", item `default-3-5`, and
again in session the same day once the item had been corrected: "Comment and test
(Recommended)". The default stays 3e-5. The header's comment says it is the best size for
the worst case over the golden grid, and that a typical option does better near 1e-4. A new
assertion holds that.

`bump_greeks.hpp` calls `spot_relative_for_gamma`'s default of 3e-5 a measured optimum, and
the sweep in `tests/test_bump_greeks.cpp` holds it to be the best of seven sizes over nine
options. The sweep tries nothing between 3e-5 and 1e-3. On those nine options a bump of 1e-4
is about eleven times more accurate than the default (2.57e-10 against 2.84e-9), which is
what the comment's own analysis, `eps^(1/4)` or 1.2e-4, would lead a reader to expect. So
the comment's evidence does not support its default.

The default is right all the same. Over the 7,200 rows of the main golden grid the worst
gamma error, by the tests' own `scaled_error`, is:

| Gamma's bump | Worst error | Where |
|---|---|---|
| 1e-5 | 1.27e-7 | put, S=60, K=90, vol 0.30, 1,826 days |
| 2e-5 | 3.8e-8 | |
| 3e-5, the default | 2.59e-8 | |
| 4e-5 | 4.4e-8 | |
| 1e-4 | 2.67e-7 | call, S=80, K=80, vol 0.05, 91 days |

The wider bump is closer on 4,956 of the 7,200 rows and ten times worse on the worst one: a
three-month option at a volatility of 0.05 has a gamma that is a narrow spike. With the
default moved to 1e-4 the suite fails twice, on the gamma tolerance of 1e-7 in "bumped and
analytic agree over the golden grid" (2.67e-7) and on the same bound in
`tests/test_three_way.cpp` (1.43e-7). The rows at 1e-5, 3e-5 and 1e-4 were measured with
g++ 13.3 and clang 18 on Linux, which agree to every digit shown; the `v1.1.0` browser build
gives 1.3e-7, 2.6e-8 and 2.7e-7 for them. The rows at 2e-5 and 4e-5 are the browser build's
only.

So nothing the library returns changes. A comment says what the default is chosen for, a
test holds it, and `ARCHITECTURE.md` says the same in one sentence.

## The six edits

Each is an exact replacement. If a Replace block is not found exactly once, stop and report.
The six, applied to `main` at `1faeac8`, are the tree the session built and tested.

### 1. `include/touchstone/bump_greeks.hpp`, the file comment, "Choosing the bump": one clause

Replace:

```
// two spot bumps below, and hence `BumpSizes` at all: these numbers are a
// property of the arithmetic, not of the option, and they should be visible
// rather than buried.
```

With:

```
// two spot bumps below, and hence `BumpSizes` at all: the scale of these numbers
// is a property of the arithmetic, not of the option, and they should be visible
// rather than buried.
```

### 2. `include/touchstone/bump_greeks.hpp`, the file comment: a new paragraph after the one on the measured defaults

Replace:

```
// order of magnitude of the `eps^(2/3)` (a first difference) or `eps^(1/2)`
// (the second) the analysis predicts.
//
```

With:

```
// order of magnitude of the `eps^(2/3)` (a first difference) or `eps^(1/2)`
// (the second) the analysis predicts.
//
// For gamma the default is chosen for the worst option, and that is not the
// typical one. A bump of 1e-4, close to the analysis's 1.2e-4, is the more
// accurate on most of the golden grid. But a short option at a low volatility
// has a gamma that is a narrow spike, the fourth derivative in its truncation
// term is large, and there the wider bump loses more than it gains. The same
// test measures the worst gamma error over the whole grid at 1e-5, at the
// default and at 1e-4, and asserts that each neighbour's is more than three
// times the default's (it measures five times and ten). A caller who knows the
// option can do better than the default; the default cannot know the option.
//
```

### 3. `include/touchstone/bump_greeks.hpp`, the comment on `BumpSizes::spot_relative_for_gamma`

Replace:

```
    /// `dS = spot_relative_for_gamma * S`, for gamma. Measured optimum;
    /// `eps^(1/4)` is 1.2e-4.
```

With:

```
    /// `dS = spot_relative_for_gamma * S`, for gamma. Measured optimum for the
    /// worst option of the golden grid; `eps^(1/4)` is 1.2e-4, and most options
    /// do better near it.
```

### 4. `tests/test_bump_greeks.cpp`, one include

Replace:

```
#include <cstddef>
#include <iomanip>
```

With:

```
#include <cstddef>
#include <initializer_list>
#include <iomanip>
```

### 5. `tests/test_bump_greeks.cpp`, a new test case, between the sweep and the grid

Replace:

```
        MESSAGE(table.str());
    }

    TEST_CASE("bumping a grid gets the grid's Greeks, at the grid's bump size")
```

With:

```
        MESSAGE(table.str());
    }

    TEST_CASE("gamma's default bump is the best for the worst option, not for the typical one")
    {
        // The sweep above tries nothing between 3e-5 and 1e-3. A bump of 1e-4,
        // near the analysis's `eps^(1/4)`, is closer than the default on most of
        // the main grid, and the default is the right one all the same. This is
        // the measurement that says so: the *worst* error over the grid is
        // smallest at the default, because a short option at a low volatility has
        // a gamma that is a narrow spike, and the fourth derivative in its
        // truncation term makes a wide bump expensive. A default has to serve
        // that option too.
        const auto& file = touchstone::testing::golden_file();

        struct Candidate {
            double size;
            Worst worst{};
        };
        Candidate narrower{1e-5};
        Candidate at_default{BumpSizes{}.spot_relative_for_gamma};
        Candidate wider{1e-4};
        std::size_t rows = 0;
        std::size_t wider_is_closer = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += sweep_scale) {
            const GoldenCase& row = file.cases[i];
            const double analytic = touchstone::price_and_greeks(row.option, row.market).gamma;
            const auto error_at = [&](Candidate& candidate) {
                BumpSizes bumps{};
                bumps.spot_relative_for_gamma = candidate.size;
                const double bumped = touchstone::bump_greeks(row.option, row.market, bumps).gamma;
                candidate.worst.observe(bumped, analytic, row);
                return touchstone::testing::scaled_error(bumped, analytic);
            };
            error_at(narrower);
            const double own = error_at(at_default);
            if (error_at(wider) < own) {
                ++wider_is_closer;
            }
            ++rows;
        }

        std::ostringstream report;
        report << "gamma's bump over " << rows << " rows of the main grid; the wider is closer on "
               << wider_is_closer;
        for (const Candidate* candidate : {&narrower, &at_default, &wider}) {
            report << "\n    at " << candidate->size << ": " << candidate->worst.describe("gamma");
        }
        MESSAGE(report.str());

        // The worst row is one row, and a scaled-down sweep may not hold it.
        if (touchstone::testing::full_sweep) {
            CHECK(narrower.worst.error() > at_default.worst.error() * 3.0);
            CHECK(wider.worst.error() > at_default.worst.error() * 3.0);
            CHECK(wider_is_closer * 2 > rows);
        }
    }

    TEST_CASE("bumping a grid gets the grid's Greeks, at the grid's bump size")
```

### 6. `ARCHITECTURE.md`, §5, the paragraph on bump Greeks: one sentence added

Replace:

```
Greeks, and asserts that each is most accurate at the size `BumpSizes` defaults to (1e-6;
3e-5 for gamma) and more than ten times less accurate at both ends of the sweep.
```

With:

```
Greeks, and asserts that each is most accurate at the size `BumpSizes` defaults to (1e-6;
3e-5 for gamma) and more than ten times less accurate at both ends of the sweep. Gamma's
default is the worst case's optimum and not the typical option's: over the main golden grid
a bump of 1e-4 is the more accurate on most rows, and the worst gamma error at 1e-5 and at
1e-4 is each more than three times the default's, which the same file asserts.
```

## What not to change

- The default, `spot_relative_for_gamma{3e-5}`.
- The sweep's sizes, its nine options or its assertions.
- Any tolerance.
- Anything under `docs/evidence/`: those files record what earlier tollgates found.
- No tag and no release. `v1.1.0` stays the newest, and the learn site stays pinned to it.

## Checks

1. Build and run the whole suite the way this repository's own instructions say. The session
   ran `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`, `cmake --build build`, then `ctest`
   in `build`: 18 of 18. On the owner's machine an earlier session needed the mingw `bin`
   directory first on `PATH` before g++ and the test executables would run.
2. The new test case prints its three worst errors. Expect 1.27e-7, 2.59e-8 and 2.67e-7, and
   "the wider is closer on 4956"; the last digits may differ on another compiler.
3. If any of the new test case's three assertions fails, stop and report the three errors
   and the count. Do not loosen an assertion and do not change the default.
4. With `-DTOUCHSTONE_SWEEP_SCALE=16`, which CI's sanitizer job uses, the three assertions
   stand aside and the suite still passes. Running that build is optional.

## Commit and pull request

On a branch `fix/gamma-bump-default` from `main`, one commit, and a pull request for the
owner to merge. The commit message, in full:

```
Bump Greeks: say what gamma's default bump is chosen for, and hold it

The header called the 3e-5 default a measured optimum on the evidence of
a sweep over nine options, which tries no size between 3e-5 and 1e-3. On
those nine a bump of 1e-4 is about eleven times more accurate, as the
header's own eps^(1/4) would suggest. The default is right for another
reason: over the 7,200 rows of the main golden grid the worst gamma error
is 2.59e-8 at 3e-5, against 1.27e-7 at 1e-5 and 2.67e-7 at 1e-4. The wider
bump is closer on 4,956 rows and ten times worse on the worst, a
three-month option at a volatility of 0.05 whose gamma is a narrow spike.

A new test case, "gamma's default bump is the best for the worst option,
not for the typical one", measures the three sizes over the grid and
asserts that each neighbour's worst error is more than three times the
default's and that the wider bump is closer on most rows. The header's
comment and one sentence of ARCHITECTURE.md §5 say the same. The default,
the sweep and every tolerance are unchanged, and nothing the library
returns changes.

The owner's ruling of 2026-11-21 (Part 3 rulings 3.5-3.6, default-3-5,
corrected and ruled again in session). The brief is
docs/briefs/bump-sizes.md.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

Add four paths and no others: `include/touchstone/bump_greeks.hpp`,
`tests/test_bump_greeks.cpp`, `ARCHITECTURE.md` and `docs/briefs/bump-sizes.md`.

## Report

The commit's hash, the pull request's number, the suite's count, and the four figures the
new test case printed.
