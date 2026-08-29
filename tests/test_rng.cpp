// The shared generator against the browser's answers, and the inverse normal
// CDF against everything that can check it.
//
// The fixture in `golden/rng-known-answers.json` is what makes the tutorial's
// demos and this library one thing rather than two: it was produced by
// `touchstone-learn`'s TypeScript at L0, and if the numbers below stop matching
// it, a check on the page and a test here have stopped being the same check.

#include "rng_fixture.hpp"

#include <touchstone/normal.hpp>
#include <touchstone/rng.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

namespace {

using touchstone::Xoshiro128SS;
using touchstone::fmix32;
using touchstone::norm_cdf;
using touchstone::norm_inv;
using touchstone::testing::rng_fixture;
using touchstone::testing::stream_seed;

constexpr double eps = std::numeric_limits<double>::epsilon();

/// `docs/rng.md` section 6. The generator and the uniforms are integer
/// arithmetic and agree exactly; only the normals can differ between languages,
/// and only in the last few units in the last place, because `sqrt` and `log`
/// are allowed half an ulp of freedom by IEEE 754.
constexpr double normal_tolerance = 1e-12;

/// Correctly rounded doubles for the inverse normal CDF, computed at 80
/// decimal digits with mpmath by inverting erfc, and rounded once. Reference
/// values, not the output of the code under test. The three groups are AS241's
/// three branches: |p - 1/2| <= 0.425, then sqrt(-log(.)) <= 5, then above it.
struct Reference {
    double p;
    double x;
    const char* branch;
};

constexpr Reference references[] = {
    {0.6, 0.2533471031357998, "central"},
    {0.9, 1.2815515655446004, "central"},
    {0.075, -1.439531470938456, "central"},
    {0.925, 1.439531470938456, "central"},
    {0.975, 1.9599639845400543, "moderate tail"},
    {0.01, -2.326347874040841, "moderate tail"},
    {1e-5, -4.264890793922825, "moderate tail"},
    {1e-10, -6.361340902404057, "moderate tail"},
    {1e-12, -7.034483825301132, "far tail"},
    {1e-15, -7.941345326170997, "far tail"},
    {1e-100, -21.273453560965326, "far tail"},
    {1e-300, -37.0470962993612, "far tail"},
};

/// How accurately `p` can be recovered from `N(N^-1(p))`, in relative terms.
///
/// Conditioning, not sloppiness. An error in x arrives in p amplified by the
/// relative sensitivity |d ln N / dx| = phi/N, which grows like |x| in the left
/// tail; so a relative error of c ulps in x becomes c eps x^2 in p, and that
/// term is the whole story once |x| is above about 3. The 4 is the floor near
/// the centre, where erfc's own couple of ulps dominate instead.
///
/// What c is, is a measurement rather than a citation. `docs/rng.md` calls
/// AS241 "accurate to about 1e-16 over the whole range", which reads as under
/// an ulp; over the sweep below the implied error in x reaches 3.1 ulps, in the
/// tail beyond p = 1e-150 where the dominant term is `log`'s own half-ulp
/// arriving through `r = sqrt(-log p)`. Four is that measurement rounded up,
/// and the sweep reports how much of the bound it actually used.
double round_trip_tolerance(double x)
{
    return (4.0 + 4.0 * x * x) * eps;
}

/// The inverse of `fmix32`, which exists because every step of `fmix32` is a
/// bijection on the 32-bit words: an xor with a right shift is undone by
/// repeating it (twice, when the shift is under half the width), and a multiply
/// by an odd constant is undone by a multiply by its inverse modulo 2^32.
///
/// It is here to make one claim of `docs/rng.md` section 2 checkable rather
/// than asserted: because `fmix32` is a bijection with `fmix32(0) = 0`, and the
/// four seed inputs differ, at most one state word can be zero, so the all-zero
/// rejection is unreachable.
std::uint32_t unfmix32(std::uint32_t h)
{
    h ^= h >> 16;
    h *= 0x7ed1b41du;  // inverse of 0xc2b2ae35 modulo 2^32
    h ^= (h >> 13) ^ (h >> 26);
    h *= 0xa5cb9243u;  // inverse of 0x85ebca6b modulo 2^32
    h ^= h >> 16;
    return h;
}

std::vector<double> normals_from(std::uint32_t seed, std::size_t n)
{
    Xoshiro128SS rng(seed);
    std::vector<double> out(n, 0.0);
    for (double& value : out) {
        value = rng.next_normal();
    }
    return out;
}

double correlation(const std::vector<double>& a, const std::vector<double>& b)
{
    const double n = static_cast<double>(a.size());
    double mean_a = 0.0;
    double mean_b = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        mean_a += a[i] / n;
        mean_b += b[i] / n;
    }
    double covariance = 0.0;
    double variance_a = 0.0;
    double variance_b = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        const double da = a[i] - mean_a;
        const double db = b[i] - mean_b;
        covariance += da * db;
        variance_a += da * da;
        variance_b += db * db;
    }
    return covariance / std::sqrt(variance_a * variance_b);
}

}  // namespace

TEST_SUITE("rng")
{
    TEST_CASE("the fixture describes the generator docs/rng.md specifies")
    {
        const auto& fixture = rng_fixture();
        MESSAGE("fixture " << fixture.path << ": " << fixture.vectors.size() << " seeds x "
                           << fixture.count << " values, spec " << fixture.spec);
        REQUIRE(fixture.vectors.size() >= 3u);
        REQUIRE(fixture.count >= 10u);
    }

    TEST_CASE("the fixture's uniforms are reproduced bit for bit")
    {
        // Not to a tolerance. A uniform is an integer expression times a power
        // of two, so two correct implementations return the same double or one
        // of them is wrong. This is the assertion that catches a swapped high
        // and low word, an off-by-one shift, or a multiply that lost its low
        // bits — none of which a tolerance of 1e-12 would notice.
        for (const auto& vector : rng_fixture().vectors) {
            Xoshiro128SS rng(vector.seed);
            for (std::size_t i = 0; i < vector.uniforms.size(); ++i) {
                CAPTURE(vector.seed);
                CAPTURE(i);
                CHECK(rng.next_uniform() == vector.uniforms[i]);
            }
        }
    }

    TEST_CASE("the fixture's normals are reproduced within the specified tolerance")
    {
        double worst = 0.0;
        std::size_t exact = 0;
        std::size_t total = 0;

        for (const auto& vector : rng_fixture().vectors) {
            Xoshiro128SS rng(vector.seed);
            for (std::size_t i = 0; i < vector.normals.size(); ++i) {
                const double computed = rng.next_normal();
                const double error = std::abs(computed - vector.normals[i]);
                worst = std::max(worst, error);
                ++total;
                if (computed == vector.normals[i]) {
                    ++exact;
                }
                CAPTURE(vector.seed);
                CAPTURE(i);
                CHECK(error <= normal_tolerance);
            }
        }

        std::ostringstream report;
        report << std::scientific << std::setprecision(3);
        report << "normals: worst absolute error " << worst << " against a tolerance of "
               << normal_tolerance << "; " << exact << " of " << total
               << " agree bit for bit with the TypeScript";
        MESSAGE(report.str());
    }

    TEST_CASE("the i-th normal is the inverse CDF of the i-th uniform")
    {
        // `docs/rng.md` section 4 makes this a promise rather than an accident:
        // a demo may switch between uniforms and normals without the seed
        // coming to mean something different, which requires the normal stream
        // to consume exactly the draws the uniform stream would.
        Xoshiro128SS as_uniforms(12345u);
        Xoshiro128SS as_normals(12345u);
        for (int i = 0; i < 1000; ++i) {
            CAPTURE(i);
            CHECK(as_normals.next_normal() == norm_inv(as_uniforms.next_uniform()));
        }
    }

    TEST_CASE("same seed, same numbers")
    {
        // Constitution I6, in its simplest form.
        for (std::uint32_t seed : {0u, 1u, 42u, 2147483647u, 4294967295u}) {
            Xoshiro128SS first(seed);
            Xoshiro128SS second(seed);
            for (int i = 0; i < 500; ++i) {
                CAPTURE(seed);
                CAPTURE(i);
                CHECK(first.next_u32() == second.next_u32());
            }
        }
    }

    TEST_CASE("uniforms are 53-bit values in [0, 1)")
    {
        Xoshiro128SS rng(7u);
        double smallest = 1.0;
        double largest = 0.0;

        for (int i = 0; i < 200000; ++i) {
            const double u = rng.next_uniform();
            REQUIRE(u >= 0.0);
            REQUIRE(u < 1.0);
            // 53 bits, uniformly spaced: u * 2^53 is an integer exactly.
            const double scaled = u * 9007199254740992.0;  // 2^53
            REQUIRE(scaled == std::floor(scaled));
            smallest = std::min(smallest, u);
            largest = std::max(largest, u);
        }

        MESSAGE("200000 uniforms in [" << smallest << ", " << largest << "]");
        CHECK(smallest < 0.001);   // the low end is reached
        CHECK(largest > 0.999);    // and the high end
    }

    TEST_CASE("the all-zero state cannot be seeded")
    {
        // fmix32 is a bijection with fmix32(0) = 0, so a state word is zero only
        // when its input is, and the four inputs are seed, seed+1, seed+2,
        // seed+3, which differ. At most one word can be zero and the rejection
        // branch is unreachable. The claim rests on bijectivity; here it is.
        CHECK(fmix32(0u) == 0u);
        CHECK((0x85ebca6bu & 1u) == 1u);  // odd, so invertible modulo 2^32
        CHECK((0xc2b2ae35u & 1u) == 1u);

        for (std::uint32_t i = 0; i < (1u << 20); ++i) {
            const std::uint32_t h = i * 2654435761u + 12345u;
            REQUIRE(unfmix32(fmix32(h)) == h);
            REQUIRE((fmix32(h) == 0u) == (h == 0u));
        }

        // And the property itself, over a sweep of seeds: never all four.
        for (std::uint32_t seed = 0; seed < (1u << 20); ++seed) {
            const std::uint32_t s0 = fmix32(seed + 0u);
            const std::uint32_t s1 = fmix32(seed + 1u);
            const std::uint32_t s2 = fmix32(seed + 2u);
            const std::uint32_t s3 = fmix32(seed + 3u);
            REQUIRE((s0 | s1 | s2 | s3) != 0u);
        }
    }

    TEST_CASE("AS241 matches high-precision reference values in all three branches")
    {
        double worst = 0.0;
        for (const Reference& reference : references) {
            const double computed = norm_inv(reference.p);
            const double relative = std::abs(computed - reference.x) / std::abs(reference.x);
            worst = std::max(worst, relative);
            CAPTURE(reference.p);
            CAPTURE(reference.branch);
            // Wichura's published accuracy is about 1e-16 relative, which is
            // under an ulp; a few ulps is what an implementation of it should
            // cost, and what this bound allows.
            CHECK(relative <= 8.0 * eps);
        }
        MESSAGE(std::scientific << std::setprecision(3) << "AS241 worst relative error "
                                << worst << " over " << std::size(references)
                                << " reference values");
    }

    TEST_CASE("AS241 round-trips through N(x)")
    {
        // `docs/rng.md` section 7: the check the C++ port should repeat. Nothing
        // in `norm_inv` shares a line with `norm_cdf` — one is a pair of
        // rational approximations, the other is erfc — so agreement between
        // them is agreement between two independent routes to the same
        // function.
        //
        // Only p <= 1/2 is round-tripped. Above it the approximation reads
        // 1 - p, and a p within an ulp of 1 loses its digits to that
        // subtraction rather than to anything under test. The symmetry case
        // below covers the upper half instead.
        double worst_ratio = 0.0;
        double worst_at = 0.0;
        std::size_t checked = 0;

        for (int step = 0; step <= 1200; ++step) {
            const double p = std::pow(10.0, -static_cast<double>(step) * 0.25);
            if (p > 0.5) {
                continue;
            }
            const double x = norm_inv(p);
            const double recovered = norm_cdf(x);
            const double relative = std::abs(recovered - p) / p;
            const double ratio = relative / round_trip_tolerance(x);
            if (ratio > worst_ratio) {
                worst_ratio = ratio;
                worst_at = p;
            }
            ++checked;
            CAPTURE(p);
            CAPTURE(x);
            CHECK(relative <= round_trip_tolerance(x));
        }

        MESSAGE(std::scientific << std::setprecision(3) << "round trip over " << checked
                                << " values of p from 1e-300 to 0.5: worst error is "
                                << worst_ratio << " of its bound, at p = " << worst_at);
    }

    TEST_CASE("AS241 is monotone, odd, and clamped where docs/rng.md says")
    {
        CHECK(norm_inv(0.5) == 0.0);

        double previous = -std::numeric_limits<double>::infinity();
        for (int step = 1; step < 10000; ++step) {
            const double p = static_cast<double>(step) / 10000.0;
            const double x = norm_inv(p);
            CAPTURE(p);
            REQUIRE(x > previous);
            previous = x;
        }

        // Odd about 1/2, to the accuracy 1 - p has.
        for (double p : {0.001, 0.01, 0.1, 0.25, 0.4}) {
            CAPTURE(p);
            CHECK(std::abs(norm_inv(p) + norm_inv(1.0 - p)) <= 1e-14);
        }

        // The zero draw. A uniform of exactly zero arrives once in 2^53 and
        // would otherwise return -infinity, taking a whole path with it. The
        // clamp sends it to N^-1(2^-53) instead, which is -8.2095..., the same
        // mpmath reference as the values above.
        const double clamped = norm_inv(0x1p-53);
        CHECK(norm_inv(0.0) == clamped);
        CHECK(norm_inv(-1.0) == clamped);
        CHECK(std::isfinite(clamped));
        CHECK(std::abs(clamped - (-8.209536151601387)) <= 8.0 * eps * 8.21);

        // Above the domain, which is [0, 1). Not rejected: the TypeScript does
        // not reject it either, and a check the two implementations did not
        // share would be a divergence the fixture cannot see. What happens is
        // pinned here rather than left to be discovered — 1 - p is zero or
        // negative, so `sqrt(-log(.))` is infinite or a NaN and the ratio of
        // two polynomials in it is a NaN.
        CHECK(std::isnan(norm_inv(1.0)));
        CHECK(std::isnan(norm_inv(1.5)));
    }

    TEST_CASE("the seeds a sweep uses are far apart and their streams do not correlate")
    {
        // The sweeps in `test_monte_carlo.cpp` treat their rows as independent
        // samples and test aggregate statistics on that basis. Two things have
        // to hold for that: no two rows may draw seeds within three of each
        // other, where the seed expansion would overlap, and streams from the
        // seeds actually used must not correlate.
        constexpr std::size_t rows = 8000;
        std::vector<std::uint32_t> seeds(rows, 0u);
        for (std::size_t i = 0; i < rows; ++i) {
            seeds[i] = stream_seed(i);
        }
        std::sort(seeds.begin(), seeds.end());
        std::uint32_t closest = 0xffffffffu;
        for (std::size_t i = 1; i < rows; ++i) {
            closest = std::min(closest, seeds[i] - seeds[i - 1]);
        }
        // Including the pair that wraps around 2^32.
        closest = std::min(closest, 0xffffffffu - (seeds.back() - seeds.front()) + 1u);
        MESSAGE("closest pair among " << rows << " sweep seeds: " << closest << " apart");
        CHECK(closest > 3u);

        constexpr std::size_t draws = 4096;
        constexpr std::size_t streams = 64;
        std::vector<std::vector<double>> samples;
        samples.reserve(streams);
        for (std::size_t i = 0; i < streams; ++i) {
            // Consecutive indices, which is what the sweeps use. Spreading the
            // sample over the seed space instead would test a property the
            // sweeps do not rely on and skip the one they do.
            samples.push_back(normals_from(stream_seed(i), draws));
        }

        const std::size_t pairs = streams * (streams - 1) / 2;
        // The bound is computed, not chosen: a sample correlation of two
        // independent standard normal streams has standard deviation
        // 1/sqrt(n), and this is the two-sided normal quantile that leaves a
        // one-in-a-million chance of any of the pairs exceeding it.
        const double bound =
            -norm_inv(1e-6 / (2.0 * static_cast<double>(pairs))) / std::sqrt(static_cast<double>(draws));

        double worst = 0.0;
        for (std::size_t i = 0; i < streams; ++i) {
            for (std::size_t j = i + 1; j < streams; ++j) {
                worst = std::max(worst, std::abs(correlation(samples[i], samples[j])));
            }
        }
        MESSAGE(std::scientific << std::setprecision(3) << "worst |correlation| over " << pairs
                                << " stream pairs: " << worst << ", bound " << bound);
        CHECK(worst <= bound);
    }
}
