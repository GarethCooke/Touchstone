# T5 — the tollgate's defects, and what changed

## 1. The verdict

The T5 tollgate (Fable, 2026-11-14) ran against `7110c84`: **PASS WITH DEFECTS**. It rebuilt
the branch with g++ 13.3 and warnings as errors: 0 warnings, 18 of 18, 120 cases, 4,140,490
assertions. It found all seven library object files at -O3 byte-identical to main's, every
figure in `claims.md` reproduced, all 46 texts in `ARCHITECTURE.md` §10.3 present on main
word for word, and the artifact passing the smoke test and loading in headless Chromium,
page and worker. It kept the three pairs, on the overload hazard reproduced with the real
headers.

It found five defects, all wording. In each, a claim `ARCHITECTURE.md` had already narrowed
still stood unnarrowed somewhere a reader would meet it, or a figure stood with nothing
holding it:

1. `README.md`, opening list: "three independent ways"; the Monte Carlo held "across the
   golden file's rows"; the grid held "on the same rows".
2. `pde.hpp`, file comment: "shares no arithmetic with either of them beyond the scale
   functions", where it shares `payoff` with the Monte Carlo.
3. `monte_carlo.hpp`, file comment: "an independent one", where it takes its discount
   factor and discounted strike from `ClosedFormQuote` and its payoff from the grid.
4. `monte_carlo.hpp`, `MonteCarloSettings`: "about a cent of standard error at typical
   parameters", where §7's option measures 0.0766.
5. `pde.hpp`, `PdeSettings`: "hold every row to 3e-4 … which `tests/test_pde.cpp`
   measures", where the suite runs the whole grid only at 512 × 256. And `ARCHITECTURE.md`
   §1's "at a stated resolution", which stated none.

It asked for a scan for more figures of the kind. It also corrected the report on one
point: the workflow has six jobs, not seven. `tests.txt` §5 said seven as well; it now
says six.

## 2. What changed

Comments and documents only. Each old text is at `7110c84`.

| # | Where | Was | Now | `claims.md` |
| --- | --- | --- | --- | --- |
| 1 | `README.md`, opening list | "three independent ways"; Monte Carlo held "across the golden file's rows"; grid held "on the same rows" | Independent in method, not in every line, and `ARCHITECTURE.md` §1 names what they share. The Monte Carlo is held on the 6,470 of 7,234 rows where enough paths finish in the money; the other 764 are too rare to score. The grid is held on the 7,200-row grid at 512 × 256, coarser than its defaults, and the edge block is reported, not held. | 143–145 |
| 2 | `pde.hpp`, file comment | "shares no arithmetic with either of them beyond the scale functions" | Names what it shares: `scales.hpp` with both others, `payoff` with the Monte Carlo. | 146 |
| 3 | `monte_carlo.hpp`, file comment | "an independent one. A discretisation, a discount factor or a payoff misread the same way twice …" | The method is independent and not every line is. It names what is shared (the discount factor and discounted strike from `ClosedFormQuote`, the payoff, `scales.hpp`) and says what the Monte Carlo can check: the terminal law, the discretisation, the sampling and the estimator. | 147 |
| 4 | `monte_carlo.hpp`, `MonteCarloSettings` | "Defaults price a European vanilla to about a cent of standard error at typical parameters." | Dropped. The defaults promise no accuracy of their own, and `MonteCarloResult` reports the standard error beside every price. | 148 |
| 5 | `pde.hpp`, `PdeSettings` | "on the golden grid they hold every row to 3e-4 of the underlying's own scale and the typical row to far less, which `tests/test_pde.cpp` measures" | What the suite asserts: 7,200 rows at 512 × 256 to 2e-4 in price (`test_pde.cpp`), and 136 rows at the defaults' own 1,024 × 512 to 5e-5 (`test_three_way.cpp`). | 149 |
| 5 | `ARCHITECTURE.md` §1 | "at a stated resolution" | "at 512 space intervals by 256 time steps, coarser than its defaults" | 8 |
| A | `tests/test_three_way.cpp`, file comment | "three implementations that share no arithmetic" | Different methods, not wholly separate code; a mistake in a shared piece shows only against a method that does not share it. | 150 |
| B | `normal.hpp`, `norm_inv` | "Accurate to about 1e-16 relative over the whole range, which `tests/test_rng.cpp` re-establishes" | The test asserts a round trip within (4 + 4x²) eps, and its own comment measures up to 3.1 ulps in x. The comment now gives the 1e-16 as `docs/rng.md` §4's figure and says what the test asserts and measures. | 151 |
| C | `bump_greeks.hpp`, choosing the bump | A sweep "over four decades … across a grid of 864 options" with floors "3e-10 for delta, 2e-8 for gamma and 1e-8 for vega" | Nothing in the repository holds that sweep. The comment now cites the test's sweep instead: 1e-9 to 1e-2 over nine options, with the minimum and both ends asserted. Its reported floors are 1e-10, 3e-9 and 2e-10. | 152 |
| D | `bump_greeks.hpp`, same | "a finite-difference grid at around 1e-6 relative, a Monte Carlo at 1e-3 … several hundred times larger for the grid" | No figure for either pricer. The ratio is given as `(d / eps)^(1/3)`, about 360 at `d` = 1e-8 (arithmetic). The old 1e-6 gave about 1,700, not "several hundred". | 153 |
| E | `bump_greeks.hpp`, same | delta off the grid "flat to within a factor of five across four decades of bump size" | The two bumps are three decades apart (1e-6 and 1e-3) and the test asserts a factor of ten; it measures 4.96. The comment now says what is asserted. | 154 |
| F | `tests/grid_bumps.hpp`; `tests/test_bump_greeks.cpp`, three comments | "A grid is accurate to about 1e-6 relative"; "over four decades" (the sizes span seven); "a thousand times the defaults"; "around 1e-8 relative"; "the grid's 1e-6 … at a bump of 1e-9 … twenty-six thousand" | No accuracy figure for the grid. The comments now give the sweep's real range, "a hundred to a thousand times the defaults", and the asserted factors (ten for delta, fifty for gamma) with gamma's measured ratio of 228. | 155 |

The added sentences in `ARCHITECTURE.md` §10.2 are rows 139–142. Not changed: the
"independent" in `bump_greeks.hpp` (a difference quotient of the price, against the
analytic Greeks) and in `tests/test_monte_carlo.cpp` ("shares no line of code with the
engine's accumulator or its pairing"). Each is scoped to what it says and holds as worded.

## 3. The tollgate's figures, reproduced

The tollgate measured the figures behind defects 4 and 5. This program measures them again
at the library's defaults. It links the library sources and the tests' golden-file loader,
and is not part of the build. Command, from the repository root (PowerShell):

```text
g++ -std=c++20 -O3 -DNDEBUG -DDOCTEST_CONFIG_DISABLE -Iinclude -Itests -Ithird_party
    '-DTOUCHSTONE_GOLDEN_PATH="golden/bs_vanilla.json"' src/*.cpp tests/golden_file.cpp
    tests/json_file.cpp at_defaults.cpp -o at_defaults.exe
```

g++ 15.2.0 (MinGW-Builds), the machine in `timing.txt`; 50 s for the run. Output:

```text
base case (call K=100 T=1; S=100 vol=0.2 r=0.05 q=0.02), MonteCarloSettings{}:
    price 9.265446  standard error 0.076610  closed form 9.227006
main block, 7200 rows, PdeSettings{}: worst price error scaled by max(|ref|, S) 2.232e-05
    at call S=80 K=100 vol=0.6 r=-0.005 q=0.05 T=5.0027
main block, MonteCarloSettings{}: price standard error
    10th percentile 0.0002  median 0.0625  90th percentile 0.2594
```

Every figure the tollgate gave reproduces. The standard error is 0.0766 on §7's option. The
worst row at the defaults is 2.232e-5, at the same row the tollgate named. Over the main
block, the median standard error is 0.0625, the 10th percentile 0.0002 and the 90th 0.26.
None of these is asserted; `ARCHITECTURE.md` §10.2 quotes only the first, as 0.077.

```cpp
// Measures, at the library's default settings, the two figures the tollgate
// raised: the grid's worst price error over the golden file's 7,200-row main
// block (scaled as tests/test_pde.cpp scales it), and the Monte Carlo's
// standard error, on bench/timing.cpp's base case and over the same rows.
#include "errors.hpp"
#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/pde.hpp>

#include <algorithm>
#include <cstdio>
#include <vector>

int main()
{
    using namespace touchstone;
    const auto& file = touchstone::testing::golden_file();

    const EuropeanVanilla base_option{100.0, 1.0, OptionType::Call};
    const BlackScholesMarket base_market{100.0, 0.2, 0.05, 0.02};
    const MonteCarloResult base = monte_carlo(base_option, base_market, MonteCarloSettings{});
    std::printf("base case (call K=100 T=1; S=100 vol=0.2 r=0.05 q=0.02), MonteCarloSettings{}:\n"
                "    price %.6f  standard error %.6f  closed form %.6f\n",
                base.price, base.price_standard_error, price(base_option, base_market));

    double worst = 0.0;
    const touchstone::testing::GoldenCase* at = nullptr;
    std::vector<double> errors;
    for (const auto& row : file.cases) {
        const PdeResult grid = crank_nicolson(row.option, row.market, PdeSettings{});
        const double e = touchstone::testing::scaled_error(grid.price, row.reference.price,
                                                           row.market.spot);
        if (e > worst) {
            worst = e;
            at = &row;
        }
        errors.push_back(monte_carlo(row.option, row.market, MonteCarloSettings{})
                             .price_standard_error);
    }
    std::printf("main block, %zu rows, PdeSettings{}: worst price error scaled by max(|ref|, S) "
                "%.3e\n    at %s S=%g K=%g vol=%g r=%g q=%g T=%.4f\n",
                file.cases.size(), worst, at->option.type == OptionType::Call ? "call" : "put",
                at->market.spot, at->option.strike, at->market.vol, at->market.rate,
                at->market.dividend_yield, at->option.expiry_years);

    std::sort(errors.begin(), errors.end());
    const auto q = [&](double p) { return errors[static_cast<std::size_t>(p * (errors.size() - 1))]; };
    std::printf("main block, MonteCarloSettings{}: price standard error\n"
                "    10th percentile %.4f  median %.4f  90th percentile %.4f\n",
                q(0.10), q(0.50), q(0.90));
}
```

## 4. Every number unchanged

The same checks as `tests.txt` §2, against the same build of main (`74987c7`), on the
working tree that became this commit:

- **Object code.** Release (-O3 -DNDEBUG), g++ 15.2.0: the seven library object files are
  byte-identical to main's, with the same SHA-256 values as `tests.txt` §2(a). Six were
  rebuilt from the edited headers. `tridiagonal.cpp` includes none of them, so it was not
  rebuilt.
- **Native suite.** RelWithDebInfo, `-Werror`, 0 warnings. ctest 18 of 18 (202 s);
  `touchstone_tests -s` 120 cases, 4,140,490 assertions, 14,407,953 lines.
- **Every assertion's values.** That run, normalised with `tests.txt` §2(b)'s sed and
  diffed against main's: the same three lines as before, which are the three renames. The
  diff is identical to the one in `tests.txt`.
- **Smoke test.** No file it builds from changed except header comments. CI's wasm job
  builds and runs it (§5).

## 5. CI

Run 43580715829 on 5a28eb8, the commit with every change above; ubuntu-24.04; all six jobs
green. The commit after it adds only this section and diff.txt.

| Job | Result | Time |
| --- | --- | --- |
| gcc | g++ 13.3.0, `-Werror`; 18/18 ctest entries (192.66 s of tests) | 231 s |
| clang | clang 18.1.3, `-Werror`; 18/18 (111.07 s) | 139 s |
| asan + ubsan | g++, Debug, sweep scale 16; 18/18 (378.83 s) | 412 s |
| golden file | every row re-derived; the generators reproduce both reference files and the path fixture byte for byte | 85 s |
| wasm / build and smoke test | Emscripten 6.0.13; smoke test 17/17; release files assembled | 54 s |
| wasm / the release's files, downloaded | `touchstone.mjs`: OK, `touchstone.wasm`: OK | 6 s |

The artifact as CI built it: 144,256 + 28,784 = 173,040 bytes (56,190 gzipped), the same
as at `7110c84` (`tests.txt` §5): the comments changed nothing it is built from.
