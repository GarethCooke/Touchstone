// Standard normal density, distribution, and inverse distribution.
//
// Shared by everything that follows: the closed form here at T1, the inverse
// transform the Monte Carlo will need at T2, the implied-vol solver at T3.

#pragma once

#include <cmath>
#include <cstddef>

namespace touchstone {

/// phi(x) — the standard normal probability density.
[[nodiscard]] inline double norm_pdf(double x) noexcept
{
    constexpr double inv_sqrt_two_pi = 0.3989422804014326779399460599344;  // 1/sqrt(2*pi)
    return inv_sqrt_two_pi * std::exp(-0.5 * x * x);
}

/// N(x) — the standard normal cumulative distribution, as 0.5 * erfc(-x/sqrt(2)).
///
/// The route is `std::erfc` by decision B3, and the reason is the left tail.
/// Computing N(-x) as 1 - N(x) subtracts two numbers that agree in every digit
/// that matters: at x = -10 the true value is 7.6e-24 and the subtraction
/// returns exactly zero. erfc exists precisely to keep that tail, so a deep
/// out-of-the-money option gets a small number rather than nothing at all.
/// `golden/SCHEMA.md` states the same thing about reproducing the golden file.
[[nodiscard]] inline double norm_cdf(double x) noexcept
{
    constexpr double inv_sqrt_two = 0.7071067811865475244008443621048;  // 1/sqrt(2)
    return 0.5 * std::erfc(-x * inv_sqrt_two);
}

namespace detail {

/// Horner from the highest coefficient down, over the eight-coefficient
/// polynomials `docs/rng.md` writes lowest-order first. The evaluation order is
/// part of what makes the C++ and the TypeScript agree: a different association
/// of the same sum is a different rounding, and this is the one they share.
[[nodiscard]] inline double as241_horner(const double (&c)[8], double x) noexcept
{
    double result = c[7];
    for (std::size_t i = 7; i-- > 0;) {
        result = result * x + c[i];
    }
    return result;
}

}  // namespace detail

/// N^-1(p) — the inverse standard normal CDF, by Wichura's AS241 (PPND16).
///
/// `docs/rng.md` §4 freezes this route, and the reason is cross-language
/// agreement rather than accuracy. AS241 is pure rational arithmetic, so the
/// only library functions it reaches for are `sqrt` and `log`; the C++, the
/// TypeScript and the Python then land on the same value to within a few ulps.
/// Inverting `erfc` instead would put a libm function at the centre of the
/// shared generator, and libm is exactly where V8 and glibc part company.
/// Accurate to about 1e-16 relative over the whole range, which
/// `tests/test_rng.cpp` re-establishes here by round-tripping through
/// `norm_cdf` — the check `docs/rng.md` §7 asks the C++ port to repeat.
///
/// The domain is `[0, 1)`, which is exactly the range of
/// `Xoshiro128SS::next_uniform`.
///
///   - `p <= 0` is clamped to 2^-53, the smallest uniform above zero the
///     generator can draw. `docs/rng.md` §4 puts the clamp inside this function
///     rather than in the caller so that both languages do it in the same
///     place; without it, the one draw in 2^53 that is exactly zero would
///     return -infinity and take a whole Monte Carlo path with it.
///   - `p >= 1` is outside the domain and outside the generator's range. It is
///     not rejected, because the TypeScript does not reject it and a check the
///     two implementations did not share would be a divergence the fixture
///     cannot see. Both return a NaN: `1 - p` is zero or negative, so
///     `sqrt(-log(.))` is infinite or a NaN and the ratio of two polynomials in
///     it is a NaN. That is worth knowing before a caller relies on it, so
///     `tests/test_rng.cpp` pins it rather than leaving it to be discovered.
///     It is the one place in this library where an input is accepted and a NaN
///     comes back; the domain is stated, and every caller inside the library is
///     the generator, which cannot produce a `p` outside it.
[[nodiscard]] inline double norm_inv(double p) noexcept
{
    // The AS241 coefficient blocks, lowest-order first, transcribed from
    // `docs/rng.md` section 4. A, B for the central branch; C, D for the
    // moderate tail; E, F beyond it.
    static constexpr double a[8] = {
        3.3871328727963666080e+0, 1.3314166789178437745e+2, 1.9715909503065514427e+3,
        1.3731693765509461125e+4, 4.5921953931549871457e+4, 6.7265770927008700853e+4,
        3.3430575583588128105e+4, 2.5090809287301226727e+3};
    static constexpr double b[8] = {
        1.0,                      4.2313330701600911252e+1, 6.8718700749205790830e+2,
        5.3941960214247511077e+3, 2.1213794301586595867e+4, 3.9307895800092710610e+4,
        2.8729085735721942674e+4, 5.2264952788528545610e+3};
    static constexpr double c[8] = {
        1.42343711074968357734e+0, 4.63033784615654529590e+0, 5.76949722146069140550e+0,
        3.64784832476320460504e+0, 1.27045825245236838258e+0, 2.41780725177450611770e-1,
        2.27238449892691845833e-2, 7.74545014278341407640e-4};
    static constexpr double d[8] = {
        1.0,                       2.05319162663775882187e+0, 1.67638483018380384940e+0,
        6.89767334985100004550e-1, 1.48103976427480074590e-1, 1.51986665636164571966e-2,
        5.47593808499534494600e-4, 1.05075007164441684324e-9};
    static constexpr double e[8] = {
        6.65790464350110377720e+0, 5.46378491116411436990e+0, 1.78482653991729133580e+0,
        2.96560571828504891230e-1, 2.65321895265761230930e-2, 1.24266094738807843860e-3,
        2.71155556874348757815e-5, 2.01033439929228813265e-7};
    static constexpr double f[8] = {
        1.0,                       5.99832206555887937690e-1, 1.36929880922735805310e-1,
        1.48753612908506148525e-2, 7.86869131145613259100e-4, 1.84631831751005468180e-5,
        1.42151175831644588870e-7, 2.04426310338993978564e-15};

    /// The smallest uniform `Xoshiro128SS::next_uniform` can return above zero.
    constexpr double min_uniform = 0x1p-53;

    if (p <= 0.0) {
        p = min_uniform;
    }

    const double q = p - 0.5;

    if (std::abs(q) <= 0.425) {
        const double r = 0.180625 - q * q;
        return q * detail::as241_horner(a, r) / detail::as241_horner(b, r);
    }

    double r = (q < 0.0) ? p : 1.0 - p;
    r = std::sqrt(-std::log(r));

    double value{};
    if (r <= 5.0) {
        r -= 1.6;
        value = detail::as241_horner(c, r) / detail::as241_horner(d, r);
    } else {
        r -= 5.0;
        value = detail::as241_horner(e, r) / detail::as241_horner(f, r);
    }

    return (q < 0.0) ? -value : value;
}

}  // namespace touchstone
