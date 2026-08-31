// Brent's method, on any function of one variable with a bracketed sign change.
//
// It is here because the implied-volatility solver needs a fallback that cannot
// fail — Newton is fast and Newton is not that — and because a root finder is
// worth being able to test on functions whose roots are known, rather than only
// through the one caller that uses it.

#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <utility>

namespace touchstone {

/// When to stop.
struct RootSearch {
    /// Stop once the bracket is narrower than `x_tolerance + 2 eps |x|`. The
    /// relative term is not optional: a root at 1e-8 and a root at 1e8 cannot
    /// share an absolute tolerance, and Brent's own formulation carries both.
    double x_tolerance{1e-14};

    /// Stop early if the function value reaches this. Zero means "only the
    /// bracket decides", which is the safe default for a function whose scale
    /// the search does not know.
    double f_tolerance{0.0};

    std::size_t max_iterations{100};
};

struct RootResult {
    double root{};
    double value{};  ///< `f(root)`.
    std::size_t iterations{};
    bool converged{};
};

/// Brent (1973): inverse quadratic interpolation where it behaves, the secant
/// where it does not, and bisection whenever either would step outside the
/// bracket or fail to halve it often enough.
///
/// The bracket must contain a sign change — `f(lower)` and `f(upper)` of
/// opposite signs — and the method keeps one. That is what makes it the right
/// fallback for Newton: superlinear when the function is smooth, and never worse
/// than bisection when it is not, so it converges on every input it is given
/// rather than on the inputs it likes.
///
/// A bracket whose ends do not straddle a root returns `converged = false` and
/// whichever end is closer to zero, rather than throwing: the caller that
/// bracketed it knows what a failure to bracket means, and this function does
/// not.
template <class Function>
[[nodiscard]] RootResult brent(Function&& f, double lower, double upper, const RootSearch& search)
{
    RootResult result{};

    double a = lower;
    double b = upper;
    double fa = f(a);
    double fb = f(b);
    result.iterations = 2;

    if (fa == 0.0) {
        return RootResult{a, fa, result.iterations, true};
    }
    if (fb == 0.0) {
        return RootResult{b, fb, result.iterations, true};
    }
    if ((fa > 0.0) == (fb > 0.0)) {
        const bool a_closer = std::abs(fa) < std::abs(fb);
        return RootResult{a_closer ? a : b, a_closer ? fa : fb, result.iterations, false};
    }

    // b is the best estimate; a is the contrapoint, on the other side of the
    // root; c is the previous b.
    if (std::abs(fa) < std::abs(fb)) {
        std::swap(a, b);
        std::swap(fa, fb);
    }
    double c = a;
    double fc = fa;
    double previous_step = b - a;
    double step_before_that = previous_step;

    constexpr double eps = std::numeric_limits<double>::epsilon();

    for (std::size_t i = 0; i < search.max_iterations; ++i) {
        if (search.f_tolerance > 0.0 && std::abs(fb) <= search.f_tolerance) {
            return RootResult{b, fb, result.iterations, true};
        }

        // Keep the contrapoint on the far side of the root, and b the better of
        // the two.
        if ((fb > 0.0) == (fc > 0.0)) {
            c = a;
            fc = fa;
            previous_step = b - a;
            step_before_that = previous_step;
        }
        if (std::abs(fc) < std::abs(fb)) {
            a = b;
            b = c;
            c = a;
            fa = fb;
            fb = fc;
            fc = fa;
        }

        const double tolerance = 2.0 * eps * std::abs(b) + 0.5 * search.x_tolerance;
        const double bisection = 0.5 * (c - b);

        if (std::abs(bisection) <= tolerance || fb == 0.0) {
            return RootResult{b, fb, result.iterations, true};
        }

        double step = bisection;
        if (std::abs(step_before_that) >= tolerance && std::abs(fa) > std::abs(fb)) {
            // Interpolate: the secant through two points, inverse quadratic
            // through three. `p / q` is the step, kept as a ratio so that its
            // size can be tested before it is taken.
            const double ratio = fb / fa;
            double p{};
            double q{};
            if (a == c) {
                p = 2.0 * bisection * ratio;
                q = 1.0 - ratio;
            } else {
                const double qa = fa / fc;
                const double rb = fb / fc;
                p = ratio * (2.0 * bisection * qa * (qa - rb) - (b - a) * (rb - 1.0));
                q = (qa - 1.0) * (rb - 1.0) * (ratio - 1.0);
            }
            if (p > 0.0) {
                q = -q;
            }
            p = std::abs(p);

            // Take the interpolated step only if it lands inside the bracket and
            // is smaller than half the step before last — Brent's guard against
            // an interpolation that creeps rather than converges.
            const double limit = std::min(3.0 * bisection * q - std::abs(tolerance * q),
                                          std::abs(step_before_that * q));
            if (2.0 * p < limit) {
                step_before_that = previous_step;
                previous_step = p / q;
                step = previous_step;
            } else {
                previous_step = bisection;
                step_before_that = previous_step;
            }
        } else {
            previous_step = bisection;
            step_before_that = previous_step;
        }

        a = b;
        fa = fb;
        b += (std::abs(step) > tolerance) ? step : (bisection > 0.0 ? tolerance : -tolerance);
        fb = f(b);
        ++result.iterations;
    }

    return RootResult{b, fb, result.iterations, false};
}

}  // namespace touchstone
