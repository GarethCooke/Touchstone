// The Thomas sweep and its projected form, on systems whose answers are known
// independently of them.
//
// A linear solver is the one component here that can be tested without any
// finance in the way: build a matrix, multiply it by a vector, hand back the
// product, and require the vector. Everything the Crank-Nicolson scheme claims
// rests on this, so it is tested on its own before it is tested through anything
// else.

#include <touchstone/tridiagonal.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace {

using touchstone::ExerciseRegion;
using touchstone::Tridiagonal;

/// A tiny deterministic generator, so the "random" systems are the same on every
/// machine and a failure is reproducible from the test name alone. Numerical
/// Recipes' LCG; nothing here needs the shared RNG's guarantees.
class Lcg {
public:
    explicit Lcg(std::uint32_t seed) noexcept : state_(seed) {}

    /// A double in [-1, 1).
    [[nodiscard]] double next() noexcept
    {
        state_ = state_ * 1664525u + 1013904223u;
        return static_cast<double>(state_) / 2147483648.0 - 1.0;
    }

private:
    std::uint32_t state_;
};

/// `A u`, computed directly from the bands, which is the definition the solver
/// has to invert.
[[nodiscard]] std::vector<double> multiply(const Tridiagonal& matrix, const std::vector<double>& u)
{
    const std::size_t n = matrix.size();
    std::vector<double> out(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) {
        out[i] = matrix.diag[i] * u[i];
        if (i > 0) {
            out[i] += matrix.sub[i] * u[i - 1];
        }
        if (i + 1 < n) {
            out[i] += matrix.sup[i] * u[i + 1];
        }
    }
    return out;
}

struct Bands {
    std::vector<double> sub, diag, sup;
    [[nodiscard]] Tridiagonal view() const { return Tridiagonal{sub, diag, sup}; }
};

/// A strictly diagonally dominant system with `margin` to spare on every row.
[[nodiscard]] Bands dominant_bands(std::size_t n, Lcg& rng, double margin)
{
    Bands bands{std::vector<double>(n, 0.0), std::vector<double>(n, 0.0),
                std::vector<double>(n, 0.0)};
    for (std::size_t i = 0; i < n; ++i) {
        bands.sub[i] = (i == 0) ? 0.0 : rng.next();
        bands.sup[i] = (i + 1 == n) ? 0.0 : rng.next();
        const double off = std::abs(bands.sub[i]) + std::abs(bands.sup[i]);
        // Sign alternating, so the matrix is not quietly symmetric or positive.
        bands.diag[i] = ((i % 2 == 0) ? 1.0 : -1.0) * (off + margin);
    }
    return bands;
}

/// Projected successive over-relaxation on the same complementarity problem.
///
/// Iterative where Brennan and Schwartz is direct, and it makes no assumption
/// about *where* the constraint binds — it will find a two-sided exercise region,
/// or none, or one at either end. That independence is the point: it is the only
/// thing in this repository that can tell the direct sweep it has the right
/// answer without sharing its reasoning.
[[nodiscard]] std::vector<double> psor(const Tridiagonal& matrix,
                                       const std::vector<double>& rhs,
                                       const std::vector<double>& constraint,
                                       double omega,
                                       double tolerance,
                                       std::size_t max_sweeps,
                                       std::size_t* sweeps_taken = nullptr)
{
    const std::size_t n = matrix.size();
    std::vector<double> u = constraint;
    double scale = 1.0;
    for (const double value : constraint) {
        scale = std::max(scale, std::abs(value));
    }
    for (std::size_t sweep = 0; sweep < max_sweeps; ++sweep) {
        double change = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            double residual = rhs[i];
            if (i > 0) {
                residual -= matrix.sub[i] * u[i - 1];
            }
            if (i + 1 < n) {
                residual -= matrix.sup[i] * u[i + 1];
            }
            const double gauss_seidel = residual / matrix.diag[i];
            const double relaxed = u[i] + omega * (gauss_seidel - u[i]);
            const double projected = std::max(relaxed, constraint[i]);
            change = std::max(change, std::abs(projected - u[i]));
            u[i] = projected;
        }
        // Relative to the problem's own scale. An absolute floor of 1e-15 on
        // values of order ten is below the round-off the iteration settles into,
        // and the sweep would run for ever without ever being wrong.
        if (change <= tolerance * scale) {
            if (sweeps_taken != nullptr) {
                *sweeps_taken = sweep + 1;
            }
            return u;
        }
    }
    if (sweeps_taken != nullptr) {
        *sweeps_taken = max_sweeps;
    }
    return u;
}

}  // namespace

TEST_SUITE("tridiagonal")
{
    TEST_CASE("the second-difference matrix, whose inverse is known")
    {
        // -u'' = f on [0, 1] with u(0) = u(1) = 0, discretised. For
        // f = pi^2 sin(pi x) the solution is sin(pi x) itself, so this checks the
        // solver against a function rather than against another linear algebra
        // routine. The discretisation is second order, so the agreement improves
        // as h^2 and the test says so rather than fixing one tolerance.
        double previous_error = 0.0;
        for (std::size_t n : {31u, 63u, 127u, 255u}) {
            const double h = 1.0 / static_cast<double>(n + 1);
            Bands bands{std::vector<double>(n, -1.0 / (h * h)),
                        std::vector<double>(n, 2.0 / (h * h)),
                        std::vector<double>(n, -1.0 / (h * h))};
            bands.sub[0] = 0.0;
            bands.sup[n - 1] = 0.0;

            std::vector<double> rhs(n, 0.0);
            std::vector<double> exact(n, 0.0);
            for (std::size_t i = 0; i < n; ++i) {
                const double x = static_cast<double>(i + 1) * h;
                exact[i] = std::sin(std::numbers::pi * x);
                rhs[i] = std::numbers::pi * std::numbers::pi * exact[i];
            }

            std::vector<double> got(n, 0.0);
            std::vector<double> scratch(n, 0.0);
            touchstone::solve_tridiagonal(bands.view(), rhs, got, scratch);

            double worst = 0.0;
            for (std::size_t i = 0; i < n; ++i) {
                worst = std::max(worst, std::abs(got[i] - exact[i]));
            }
            if (previous_error > 0.0) {
                // Halving h should quarter the error. Anything between three and
                // five says second order without pretending the constant is known.
                const double ratio = previous_error / worst;
                CAPTURE(n);
                CHECK(ratio > 3.0);
                CHECK(ratio < 5.0);
            }
            previous_error = worst;
        }
        MESSAGE("Poisson on 255 interior nodes: worst |u - sin(pi x)| = " << previous_error);
    }

    TEST_CASE("the solution solves the system it came from")
    {
        // Round trip, at a scale no closed form covers: build a dominant matrix,
        // pick a vector, form A u, solve, and require the vector back. Doing it
        // over a range of dominance margins is the part that matters — the
        // algorithm's stability is a statement about that margin, so the test
        // walks it down to where the statement stops being comfortable.
        Lcg rng(20260831u);
        std::ostringstream table;
        table << "round trip on dominant systems, worst |u - u| per margin";
        for (const double margin : {1.0, 0.1, 0.01, 1e-3}) {
            double worst = 0.0;
            double worst_margin = 0.0;
            for (std::size_t n : {2u, 3u, 17u, 200u, 1001u}) {
                const Bands bands = dominant_bands(n, rng, margin);
                std::vector<double> wanted(n, 0.0);
                for (double& value : wanted) {
                    value = rng.next() * 100.0;
                }
                const std::vector<double> rhs = multiply(bands.view(), wanted);

                std::vector<double> got(n, 0.0);
                std::vector<double> scratch(n, 0.0);
                touchstone::solve_tridiagonal(bands.view(), rhs, got, scratch);

                for (std::size_t i = 0; i < n; ++i) {
                    worst = std::max(worst, std::abs(got[i] - wanted[i]));
                }
                worst_margin = touchstone::dominance_margin(bands.view());
            }
            table << "\n    margin " << std::setw(6) << margin << "  (measured "
                  << worst_margin << ")  worst error " << std::scientific
                  << std::setprecision(3) << worst << std::defaultfloat;
            // The bound is the condition number, which grows as the margin
            // shrinks; a hundredth of the margin is generous and still fails
            // loudly if the sweep is wrong rather than merely ill-conditioned.
            CAPTURE(margin);
            CHECK(worst < 1e-6 / margin);
        }
        MESSAGE(table.str());
    }

    TEST_CASE("dominance_margin measures what it says")
    {
        const std::vector<double> sub{0.0, -1.0, -2.0};
        const std::vector<double> diag{5.0, 4.0, 9.0};
        const std::vector<double> sup{-3.0, -1.0, 0.0};
        // Row 0: 5 - 3 = 2. Row 1: 4 - 1 - 1 = 2. Row 2: 9 - 2 = 7. Minimum 2.
        CHECK(touchstone::dominance_margin(Tridiagonal{sub, diag, sup}) == doctest::Approx(2.0));

        // The two entries outside the matrix are ignored, however they are set.
        const std::vector<double> noisy_sub{1e9, -1.0, -2.0};
        const std::vector<double> noisy_sup{-3.0, -1.0, 1e9};
        CHECK(touchstone::dominance_margin(Tridiagonal{noisy_sub, diag, noisy_sup})
              == doctest::Approx(2.0));

        // A matrix that is not dominant reports a negative margin rather than
        // pretending otherwise.
        const std::vector<double> weak{1.0, 1.0, 1.0};
        CHECK(touchstone::dominance_margin(Tridiagonal{sub, weak, sup}) < 0.0);

        const std::vector<double> empty{};
        CHECK(std::isnan(touchstone::dominance_margin(Tridiagonal{empty, empty, empty})));
    }

    TEST_CASE("mismatched spans are refused rather than read past")
    {
        const std::vector<double> three(3, 1.0);
        const std::vector<double> two(2, 1.0);
        std::vector<double> out(3, 0.0);
        std::vector<double> scratch(3, 0.0);

        CHECK_THROWS_AS(touchstone::solve_tridiagonal(Tridiagonal{three, two, three}, three, out,
                                                      scratch),
                        std::invalid_argument);
        CHECK_THROWS_AS(
            touchstone::solve_tridiagonal(Tridiagonal{three, three, three}, two, out, scratch),
            std::invalid_argument);
        const std::vector<double> empty{};
        std::vector<double> no_out{};
        CHECK_THROWS_AS(
            touchstone::solve_tridiagonal(Tridiagonal{empty, empty, empty}, empty, no_out, no_out),
            std::invalid_argument);
    }

    TEST_CASE("the projected sweep is the plain sweep when nothing binds")
    {
        Lcg rng(7u);
        for (std::size_t n : {5u, 64u, 513u}) {
            const Bands bands = dominant_bands(n, rng, 1.0);
            std::vector<double> rhs(n, 0.0);
            for (double& value : rhs) {
                value = rng.next() * 10.0;
            }
            const std::vector<double> far_below(n, -1e6);

            std::vector<double> plain(n, 0.0);
            std::vector<double> projected(n, 0.0);
            std::vector<double> scratch(n, 0.0);
            touchstone::solve_tridiagonal(bands.view(), rhs, plain, scratch);

            for (const ExerciseRegion region : {ExerciseRegion::Lower, ExerciseRegion::Upper}) {
                touchstone::solve_tridiagonal_projected(bands.view(), rhs, far_below, region,
                                                        projected, scratch);
                for (std::size_t i = 0; i < n; ++i) {
                    CAPTURE(n);
                    CAPTURE(i);
                    CHECK(std::abs(projected[i] - plain[i]) <= 1e-9 * (1.0 + std::abs(plain[i])));
                }
            }
        }
    }

    TEST_CASE("the projected sweep solves the complementarity problem")
    {
        // Three statements about the same answer.
        //
        // First, that the problem really is the one Brennan and Schwartz's result
        // is about: the nodes where the constraint binds form a single run at the
        // `region` end of the range. That is a precondition, not a conclusion, and
        // a test that did not check it would be handing the sweep a problem it
        // never promised to solve. (It was: an earlier version of this test used a
        // random right-hand side, whose solution binds in scattered patches, and
        // the sweep answered it wrongly — correctly, since the precondition was
        // broken. The check below is what caught that the fault was the test's.)
        //
        // Second, complementarity itself, which is the definition: at every node
        // either the equation holds or the constraint does, and never neither.
        //
        // Third, agreement with projected SOR, which finds the same solution by
        // iterating rather than by sweeping and which assumes nothing at all about
        // where the exercise region is. That independence is the point: it is the
        // only thing in this repository that can tell the direct sweep it has the
        // right answer without sharing its reasoning.
        //
        // The systems are built the way Crank-Nicolson builds them — an M-matrix
        // with a positive diagonal and negative off-diagonals — and the data the
        // way a time step supplies it: a smooth previous value on the right-hand
        // side, and a payoff-shaped constraint that falls away from one end.
        Lcg rng(1990u);
        std::ostringstream table;
        table << "projected sweep vs PSOR";

        for (const ExerciseRegion region : {ExerciseRegion::Lower, ExerciseRegion::Upper}) {
            double worst = 0.0;
            double worst_complementarity = 0.0;
            std::size_t binding_total = 0;
            std::size_t nodes_total = 0;
            std::size_t worst_sweeps = 0;
            std::size_t skipped = 0;
            std::size_t trials = 0;

            // Sixteen nodes and up: on eight, a ramp is too coarse a thing for the
            // exercise region to be an interval at all, and every trial would be
            // skipped for a reason that says nothing about the solver.
            for (std::size_t n : {17u, 65u, 400u}) {
                for (int trial = 0; trial < 12; ++trial) {
                    Bands bands{std::vector<double>(n, 0.0), std::vector<double>(n, 0.0),
                                std::vector<double>(n, 0.0)};
                    for (std::size_t i = 0; i < n; ++i) {
                        bands.sub[i] = (i == 0) ? 0.0 : -(0.5 + 0.5 * std::abs(rng.next()));
                        bands.sup[i] = (i + 1 == n) ? 0.0 : -(0.5 + 0.5 * std::abs(rng.next()));
                        bands.diag[i] = std::abs(bands.sub[i]) + std::abs(bands.sup[i]) + 0.25;
                    }

                    // A payoff-shaped constraint: a ramp that rises towards the
                    // `region` end and is flat at zero over the rest, like
                    // max(K - S, 0) on a grid whose index increases with the spot.
                    //
                    // The right-hand side is built backwards from the answer. Pick
                    // the *unconstrained* solution first — a constant — and set
                    // `rhs = A v`. Then the constraint and the unconstrained
                    // solution cross exactly once, because one is monotone and the
                    // other is flat, and the exercise region is guaranteed to be
                    // the single interval at the end that the sweep's precondition
                    // is about. Choosing the right-hand side and hoping does not
                    // guarantee it: a quadratic right-hand side crosses a linear
                    // ramp twice, and half the trials came out two-sided.
                    const double kink = 0.3 + 0.4 * std::abs(rng.next());
                    const double height = 2.0 + 8.0 * std::abs(rng.next());
                    const double base = (0.1 + 0.5 * std::abs(rng.next())) * height * kink;
                    std::vector<double> constraint(n, 0.0);
                    const std::vector<double> unconstrained(n, base);
                    for (std::size_t i = 0; i < n; ++i) {
                        const double along =
                            (n == 1) ? 0.0 : static_cast<double>(i) / static_cast<double>(n - 1);
                        const double from_edge =
                            (region == ExerciseRegion::Lower) ? (1.0 - along) : along;
                        constraint[i] = height * std::max(from_edge - (1.0 - kink), 0.0);
                    }
                    const std::vector<double> rhs = multiply(bands.view(), unconstrained);

                    ++trials;
                    std::vector<double> got(n, 0.0);
                    std::vector<double> scratch(n, 0.0);
                    touchstone::solve_tridiagonal_projected(bands.view(), rhs, constraint, region,
                                                            got, scratch);

                    std::size_t sweeps = 0;
                    const std::vector<double> reference =
                        psor(bands.view(), rhs, constraint, 1.4, 1e-15, 200000, &sweeps);
                    worst_sweeps = std::max(worst_sweeps, sweeps);
                    const std::vector<double> residual = multiply(bands.view(), got);

                    // The precondition: the binding nodes are one run, at the
                    // `region` end. Counted on PSOR's answer, which owes the sweep
                    // nothing.
                    std::size_t binding_here = 0;
                    bool contiguous = true;
                    bool left_the_region = false;
                    for (std::size_t k = 0; k < n; ++k) {
                        const std::size_t i =
                            (region == ExerciseRegion::Lower) ? k : (n - 1 - k);
                        const bool binds = reference[i] <= constraint[i] + 1e-12;
                        if (binds) {
                            ++binding_here;
                            if (left_the_region) {
                                contiguous = false;
                            }
                        } else {
                            left_the_region = true;
                        }
                    }
                    CAPTURE(n);
                    CAPTURE(trial);
                    if (!contiguous) {
                        // The sweep promises nothing here, so nothing is asserted.
                        // The odd trial still comes out two-sided; the count is
                        // reported so that a change which made most trials
                        // unusable would show rather than quietly emptying the
                        // test.
                        ++skipped;
                        continue;
                    }
                    binding_total += binding_here;
                    nodes_total += n;

                    for (std::size_t i = 0; i < n; ++i) {
                        worst = std::max(worst, std::abs(got[i] - reference[i]));

                        // u >= constraint, always.
                        CHECK(got[i] >= constraint[i] - 1e-12);

                        const double slack = got[i] - constraint[i];
                        const double equation = residual[i] - rhs[i];
                        if (slack > 1e-9) {
                            // Strictly above the constraint: the equation holds.
                            worst_complementarity =
                                std::max(worst_complementarity, std::abs(equation));
                        } else {
                            // On the constraint: the equation may only err upward.
                            CHECK(equation > -1e-9);
                        }
                    }
                }
            }

            table << "\n    " << (region == ExerciseRegion::Lower ? "lower" : "upper")
                  << " region: " << binding_total << " of " << nodes_total
                  << " nodes binding, in one run each time; worst |sweep - PSOR| "
                  << std::scientific << std::setprecision(3) << worst
                  << ", worst residual off the constraint " << worst_complementarity
                  << std::defaultfloat << "; PSOR needed up to " << worst_sweeps
                  << " sweeps; " << skipped << " of " << trials
                  << " trials skipped as not one-sided";

            // The constraint must actually bite somewhere, or this test is
            // measuring the unconstrained solver again.
            CHECK(binding_total > nodes_total / 20);
            CHECK(binding_total < nodes_total * 9 / 10);
            CHECK(worst_sweeps < 200000u);  // PSOR converged rather than ran out
            CHECK(skipped * 8 < trials);
            CHECK(worst < 1e-9);
            CHECK(worst_complementarity < 1e-9);
        }
        MESSAGE(table.str());
    }

    TEST_CASE("the one-sided precondition is load-bearing, not defensive")
    {
        // `solve_tridiagonal_projected` documents a condition rather than
        // checking one: the binding set must be a single run at the `region` end.
        // A condition stated and never exercised is a condition nobody knows the
        // cost of, so here is the cost. The constraint below is a tent — high in
        // the middle, zero at both ends — so the exercise region is an interval
        // in the *middle* of the range and neither direction of sweep can find
        // it. PSOR, which assumes nothing, does.
        //
        // Nothing in the bands or the vectors distinguishes this problem from a
        // well-posed one, which is exactly why the sweep cannot detect it and why
        // `pde.cpp` chooses the direction from the option type instead.
        constexpr std::size_t n = 200;
        Bands bands{std::vector<double>(n, 0.0), std::vector<double>(n, 0.0),
                    std::vector<double>(n, 0.0)};
        std::vector<double> rhs(n, 0.0);
        std::vector<double> constraint(n, 0.0);
        for (std::size_t i = 0; i < n; ++i) {
            bands.sub[i] = (i == 0) ? 0.0 : -1.0;
            bands.sup[i] = (i + 1 == n) ? 0.0 : -1.0;
            bands.diag[i] = 2.4;
            const double along = static_cast<double>(i) / static_cast<double>(n - 1);
            constraint[i] = 10.0 * std::max(0.25 - std::abs(along - 0.5), 0.0);
            rhs[i] = 0.2 * bands.diag[i];
        }

        std::vector<double> got(n, 0.0);
        std::vector<double> scratch(n, 0.0);
        touchstone::solve_tridiagonal_projected(bands.view(), rhs, constraint, ExerciseRegion::Lower,
                                                got, scratch);
        const std::vector<double> reference = psor(bands.view(), rhs, constraint, 1.4, 1e-15, 200000);

        double worst = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            worst = std::max(worst, std::abs(got[i] - reference[i]));
        }
        MESSAGE("two-sided exercise region: the direct sweep differs from PSOR by "
                << std::scientific << std::setprecision(3) << worst
                << " — the documented precondition, priced");

        // Both still satisfy the constraint; only one solves the problem.
        for (std::size_t i = 0; i < n; ++i) {
            CHECK(got[i] >= constraint[i] - 1e-12);
        }
        // Well posed, the two agree to 6e-15. Here they differ by ten orders of
        // magnitude more than that, which is the whole point.
        CHECK(worst > 1e-6);
    }

    TEST_CASE("a constraint of the wrong length is refused")
    {
        const std::vector<double> three(3, 1.0);
        const std::vector<double> two(2, 1.0);
        std::vector<double> out(3, 0.0);
        std::vector<double> scratch(3, 0.0);
        CHECK_THROWS_AS(touchstone::solve_tridiagonal_projected(Tridiagonal{three, three, three},
                                                                three, two, ExerciseRegion::Lower,
                                                                out, scratch),
                        std::invalid_argument);
    }
}
