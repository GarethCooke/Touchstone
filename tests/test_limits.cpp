// The two limits the roadmap names for T1: sigma -> 0 and T -> 0.
//
// `golden/SCHEMA.md` is explicit that these are not the edge block's job:
// "They are not limits. sigma -> 0 and T -> 0 are exact limits with closed-form
// answers, and T1 tests them directly rather than against this file." So this
// suite compares the library against those closed forms, re-derived here from
// the discounted forward rather than borrowed from the implementation, and then
// checks that the limits are approached as well as returned.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/normal.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <initializer_list>
#include <limits>
#include <string>
#include <vector>
#include <stdexcept>

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::OptionType;
using touchstone::PriceAndGreeks;
using touchstone::testing::scaled_error;

constexpr double infinity = std::numeric_limits<double>::infinity();

/// What the closed form must return once the terminal distribution has
/// collapsed to a point at the forward — that is, whenever sigma * sqrt(T) is
/// zero and the forward is not exactly at the strike.
///
/// The option is then a forward contract that is exercised or not, decided now:
/// worth the discounted difference if it finishes in the money and nothing
/// otherwise. Written out from that statement, not from `black_scholes.cpp`.
PriceAndGreeks collapsed(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const double w = touchstone::option_sign(option.type);
    const double t = option.expiry_years;
    const double discounted_spot = market.spot * std::exp(-market.dividend_yield * t);
    const double discounted_strike = option.strike * std::exp(-market.rate * t);
    const double exercised = (w * (discounted_spot - discounted_strike) > 0.0) ? 1.0 : 0.0;

    PriceAndGreeks expected{};
    expected.price = exercised * w * (discounted_spot - discounted_strike);
    expected.delta = exercised * w * std::exp(-market.dividend_yield * t);
    expected.gamma = 0.0;
    expected.vega = 0.0;
    expected.theta = exercised * w
                     * (market.dividend_yield * discounted_spot - market.rate * discounted_strike);
    expected.rho = exercised * w * t * discounted_strike;
    expected.dividend_rho = -exercised * w * t * discounted_spot;
    return expected;
}

void check_collapsed(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const PriceAndGreeks actual = touchstone::price_and_greeks(option, market);
    const PriceAndGreeks expected = collapsed(option, market);

    CAPTURE(market.spot);
    CAPTURE(option.strike);
    CAPTURE(market.vol);
    CAPTURE(option.expiry_years);
    CAPTURE(option.type == OptionType::Call);

    CHECK(scaled_error(actual.price, expected.price) <= 1e-15);
    CHECK(scaled_error(actual.delta, expected.delta) <= 1e-15);
    CHECK(actual.gamma == expected.gamma);
    CHECK(actual.vega == expected.vega);
    CHECK(scaled_error(actual.theta, expected.theta) <= 1e-15);
    CHECK(scaled_error(actual.rho, expected.rho) <= 1e-15);
    CHECK(scaled_error(actual.dividend_rho, expected.dividend_rho) <= 1e-15);
}

}  // namespace

TEST_SUITE("limits")
{
    TEST_CASE("sigma = 0: the option is a forward contract, exercised or not")
    {
        for (double expiry : {0.25, 1.0, 2.0, 10.0}) {
            for (double strike : {50.0, 90.0, 110.0, 250.0}) {
                for (double rate : {-0.005, 0.0, 0.05}) {
                    for (double yield : {0.0, 0.02, 0.07}) {
                        const BlackScholesMarket market{100.0, 0.0, rate, yield};
                        check_collapsed({strike, expiry, OptionType::Call}, market);
                        check_collapsed({strike, expiry, OptionType::Put}, market);
                    }
                }
            }
        }
    }

    TEST_CASE("T = 0: the option is its payoff")
    {
        for (double vol : {0.0, 0.05, 0.3, 1.5}) {
            for (double strike : {50.0, 90.0, 110.0, 250.0}) {
                const BlackScholesMarket market{100.0, vol, 0.04, 0.01};
                check_collapsed({strike, 0.0, OptionType::Call}, market);
                check_collapsed({strike, 0.0, OptionType::Put}, market);

                // The payoff, stated as a payoff.
                CHECK(touchstone::price({strike, 0.0, OptionType::Call}, market)
                      == std::max(market.spot - strike, 0.0));
                CHECK(touchstone::price({strike, 0.0, OptionType::Put}, market)
                      == std::max(strike - market.spot, 0.0));
            }
        }
    }

    TEST_CASE("at the forward, the density concentrates and two Greeks diverge")
    {
        // r == q and S == K puts the forward exactly on the strike, and does so
        // in floating point too: both discount factors are the same double, so
        // S e^{-qT} - K e^{-rT} is exactly zero rather than nearly zero.
        constexpr double carry = 0.03;
        constexpr double expiry = 1.0;
        const BlackScholesMarket market{100.0, 0.0, carry, carry};
        const EuropeanVanilla call{100.0, expiry, OptionType::Call};
        const EuropeanVanilla put{100.0, expiry, OptionType::Put};

        const PriceAndGreeks at_forward = touchstone::price_and_greeks(call, market);
        const double discounted_spot = 100.0 * std::exp(-carry * expiry);

        // N(w d1) and N(w d2) both tend to one half here, not to an indicator:
        // d1 -> v/2 -> 0. Everything below follows from that.
        CHECK(at_forward.price == 0.0);
        CHECK(scaled_error(at_forward.delta, 0.5 * std::exp(-carry * expiry)) <= 1e-15);
        CHECK(at_forward.theta == 0.0);
        CHECK(scaled_error(at_forward.rho, 0.5 * expiry * discounted_spot) <= 1e-15);

        // gamma diverges: all the mass is at one point.
        CHECK(std::isinf(at_forward.gamma));
        CHECK(at_forward.gamma > 0.0);
        CHECK(std::isinf(touchstone::gamma(put, market)));

        // vega does not. This is the one that is easy to get wrong by treating
        // "sigma = 0" and "T = 0" as the same degenerate case: with T still
        // positive, a first unit of volatility buys S e^{-qT} sqrt(T) phi(0) of
        // option value, and the limit is that number rather than zero.
        const double expected_vega = discounted_spot * std::sqrt(expiry) * touchstone::norm_pdf(0.0);
        CHECK(scaled_error(at_forward.vega, expected_vega) <= 1e-15);
        CHECK(expected_vega > 38.0);  // Emphatically not zero.

        // At expiry, at the strike, theta diverges too: the remaining time value
        // is going to zero over no remaining time.
        const BlackScholesMarket expiring{100.0, 0.3, carry, carry};
        const PriceAndGreeks now = touchstone::price_and_greeks({100.0, 0.0, OptionType::Call},
                                                                expiring);
        CHECK(std::isinf(now.gamma));
        CHECK(now.gamma > 0.0);
        CHECK(std::isinf(now.theta));
        CHECK(now.theta < 0.0);
        CHECK(now.vega == 0.0);  // No time left to be volatile in.
        CHECK(now.price == 0.0);
    }

    TEST_CASE("the limits are approached, not merely returned")
    {
        // A limit that is only ever evaluated at the limit point proves nothing
        // about the formula either side of it. Each sweep below has to converge
        // monotonically to the value the degenerate branch returns.
        SUBCASE("sigma -> 0, in the money")
        {
            const EuropeanVanilla call{90.0, 2.0, OptionType::Call};
            const double limit = touchstone::price(call, {100.0, 0.0, 0.05, 0.02});

            double previous = infinity;
            for (double vol : {0.5, 0.2, 0.1, 0.05, 0.02, 0.01}) {
                const double gap = std::abs(touchstone::price(call, {100.0, vol, 0.05, 0.02})
                                            - limit);
                CAPTURE(vol);
                CHECK(gap <= previous);
                previous = gap;
            }
            CHECK(previous <= 1e-9);
        }

        SUBCASE("sigma -> 0, at the forward: vega tends to a positive number")
        {
            const EuropeanVanilla call{100.0, 1.0, OptionType::Call};
            const double limit = touchstone::vega(call, {100.0, 0.0, 0.03, 0.03});

            double previous = infinity;
            for (double vol : {0.5, 0.2, 0.1, 0.05, 0.02, 0.01}) {
                const double gap = std::abs(touchstone::vega(call, {100.0, vol, 0.03, 0.03})
                                            - limit);
                CAPTURE(vol);
                CHECK(gap <= previous);
                previous = gap;
            }
            CHECK(previous <= 1e-3);
            CHECK(limit > 0.0);
        }

        SUBCASE("T -> 0, in the money")
        {
            const BlackScholesMarket market{100.0, 0.25, 0.04, 0.01};
            const double limit = touchstone::price({90.0, 0.0, OptionType::Call}, market);
            CHECK(limit == 10.0);

            double previous = infinity;
            for (double expiry : {0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6}) {
                const double gap =
                    std::abs(touchstone::price({90.0, expiry, OptionType::Call}, market) - limit);
                CAPTURE(expiry);
                CHECK(gap <= previous);
                previous = gap;
            }
            CHECK(previous <= 1e-4);
        }

        SUBCASE("T -> 0, out of the money")
        {
            const BlackScholesMarket market{100.0, 0.25, 0.04, 0.01};
            double previous = infinity;
            for (double expiry : {0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6}) {
                const double value =
                    touchstone::price({110.0, expiry, OptionType::Call}, market);
                CAPTURE(expiry);
                CHECK(value >= 0.0);
                CHECK(value <= previous);
                previous = value;
            }
            CHECK(previous <= 1e-8);
        }
    }


    TEST_CASE("the at-the-forward limits, with r different from q")
    {
        // The exact at-the-forward case above needs r == q, because that is the
        // only way S exp(-qT) and K exp(-rT) are the same double. With r == q
        // the discount factors coincide too, so an implementation that used
        // K exp(-rT) where it should use S exp(-qT) — in vega, in delta, in the
        // decay term — would pass it unnoticed.
        //
        // So approach the forward instead, with r != q, and check the general
        // branch tends to the limits the degenerate branch returns. K is the
        // double nearest S exp((r-q)T), which leaves a log-moneyness of order
        // 1e-16: near enough for the limits, not equal, so this runs through the
        // v > 0 branch throughout.
        constexpr double spot = 100.0;
        constexpr double rate = 0.05;
        constexpr double yield = 0.02;
        constexpr double expiry = 2.0;
        const double strike = spot * std::exp((rate - yield) * expiry);

        const double discounted_spot = spot * std::exp(-yield * expiry);
        const double expected_vega = discounted_spot * std::sqrt(expiry) * touchstone::norm_pdf(0.0);
        const double expected_delta = 0.5 * std::exp(-yield * expiry);
        // gamma diverges like 1 / (S sigma sqrt(T)), so the product converges —
        // to exp(-qT) phi(0), which is a statement about the coefficient rather
        // than about the fact of blowing up.
        const double expected_gamma_scaled = std::exp(-yield * expiry) * touchstone::norm_pdf(0.0);

        double previous_vega = infinity;
        double previous_delta = infinity;
        double previous_gamma = infinity;

        for (double vol : {0.05, 0.02, 0.01, 1e-3, 1e-4}) {
            const BlackScholesMarket market{spot, vol, rate, yield};
            const EuropeanVanilla call{strike, expiry, OptionType::Call};
            const PriceAndGreeks near = touchstone::price_and_greeks(call, market);

            const double vega_gap = std::abs(near.vega - expected_vega);
            const double delta_gap = std::abs(near.delta - expected_delta);
            const double gamma_gap =
                std::abs(near.gamma * spot * vol * std::sqrt(expiry) - expected_gamma_scaled);

            CAPTURE(vol);
            CHECK(vega_gap <= previous_vega);
            CHECK(delta_gap <= previous_delta);
            CHECK(gamma_gap <= previous_gamma);
            previous_vega = vega_gap;
            previous_delta = delta_gap;
            previous_gamma = gamma_gap;
        }

        CHECK(previous_vega / expected_vega <= 1e-8);
        CHECK(previous_delta / expected_delta <= 1e-4);
        CHECK(previous_gamma / expected_gamma_scaled <= 1e-8);

        // What this does and does not pin down, stated rather than implied.
        // delta is discounted at q here and would be 0.4524 rather than 0.4804 if
        // it were discounted at r, which the 1e-4 above separates comfortably.
        CHECK(std::abs(expected_delta - 0.5 * std::exp(-rate * expiry)) > 0.02);
        // vega cannot be pinned the same way, and no test at the forward can:
        // K = S exp((r-q)T) is exactly the statement that S exp(-qT) and
        // K exp(-rT) are the same number, so the two spellings of vega's leading
        // factor coincide there by construction rather than by luck.
        CHECK(std::abs(discounted_spot - strike * std::exp(-rate * expiry)) < 1e-12);
    }

    TEST_CASE("theta's divergence at expiry has the rate the formula says")
    {
        // Asserting isinf catches "forgot to diverge" and nothing else. The
        // decay term goes as -S phi(0) sigma / (2 sqrt(T)), so theta sqrt(T)
        // converges, and that is a statement about the coefficient rather than
        // about the fact of blowing up.
        constexpr double spot = 100.0;
        constexpr double vol = 0.3;
        const BlackScholesMarket market{spot, vol, 0.04, 0.01};
        const double expected = -spot * touchstone::norm_pdf(0.0) * vol / 2.0;

        double previous = infinity;
        for (double expiry : {1e-2, 1e-4, 1e-6, 1e-8}) {
            const double scaled =
                touchstone::theta({spot, expiry, OptionType::Call}, market) * std::sqrt(expiry);
            const double gap = std::abs(scaled - expected);
            CAPTURE(expiry);
            CHECK(gap <= previous);
            previous = gap;
        }
        CHECK(previous / std::abs(expected) <= 1e-4);
    }

    TEST_CASE("no volatility and no time at once: no diffusion wins")
    {
        // sigma -> 0 then T -> 0 gives a decay term of zero; T -> 0 then
        // sigma -> 0 gives minus infinity. The double limit does not exist, so
        // the order is a decision rather than a derivation. It is made here, in
        // the open: with no volatility there is no time value to lose, whatever
        // the expiry.
        const BlackScholesMarket still{100.0, 0.0, 0.04, 0.01};
        const PriceAndGreeks at_once =
            touchstone::price_and_greeks({100.0, 0.0, OptionType::Call}, still);

        // The decay term is zero, but theta is not: the carry terms survive, and
        // with r != q they are not zero either. Half of (qS - rK), because the
        // indicator is one half at the strike.
        const double carry = 0.5 * (0.01 * 100.0 - 0.04 * 100.0);
        CHECK(carry == -1.5);  // Not a tautology: it is what the next line must equal.
        CHECK(at_once.theta == carry);
        CHECK(at_once.price == 0.0);
        CHECK(at_once.vega == 0.0);
        CHECK(std::isinf(at_once.gamma));  // gamma's limit is infinite either way round.

        // The other order, one step away from it, for contrast.
        CHECK(std::isinf(touchstone::theta({100.0, 0.0, OptionType::Call},
                                           {100.0, 0.3, 0.04, 0.01})));
    }

    TEST_CASE("nothing in the accepted domain produces a NaN")
    {
        // require_valid's promise, checked rather than asserted: over a sweep
        // that includes the boundary of the domain it accepts, every output is
        // finite except gamma and theta exactly at the strike.
        const std::vector<double> spots{0.0,   1e-300, 1e-8, 0.5,   100.0,
                                        1e12,  1e150,  1e300, 1.7e308};
        const std::vector<double> strikes{0.0, 1e-300, 1e-8, 0.5, 100.0, 1e12, 1e150, 1e300};
        const std::vector<double> vols{0.0, 1e-300, 1e-8, 0.2, 5.0, 1e100};
        const std::vector<double> rates{-2.0, -0.005, 0.0, 0.05, 700.0};
        const std::vector<double> expiries{0.0, 1e-300, 1e-8, 1.0, 1e5, 1e300};

        std::uint64_t priced = 0;
        std::uint64_t rejected = 0;
        std::uint64_t infinite = 0;

        for (double spot : spots) {
            for (double strike : strikes) {
                for (double vol : vols) {
                    for (double rate : rates) {
                        for (double expiry : expiries) {
                            for (OptionType type : {OptionType::Call, OptionType::Put}) {
                                const BlackScholesMarket market{spot, vol, rate, -rate / 3.0};
                                const EuropeanVanilla option{strike, expiry, type};

                                PriceAndGreeks out{};
                                try {
                                    out = touchstone::price_and_greeks(option, market);
                                } catch (const std::invalid_argument&) {
                                    ++rejected;
                                    continue;
                                }
                                ++priced;

                                CAPTURE(spot);
                                CAPTURE(strike);
                                CAPTURE(vol);
                                CAPTURE(rate);
                                CAPTURE(expiry);

                                CHECK_FALSE(std::isnan(out.price));
                                CHECK_FALSE(std::isnan(out.delta));
                                CHECK_FALSE(std::isnan(out.gamma));
                                CHECK_FALSE(std::isnan(out.vega));
                                CHECK_FALSE(std::isnan(out.theta));
                                CHECK_FALSE(std::isnan(out.rho));
                                CHECK_FALSE(std::isnan(out.dividend_rho));

                                CHECK(std::isfinite(out.price));
                                CHECK(std::isfinite(out.delta));
                                CHECK(std::isfinite(out.vega));
                                CHECK(std::isfinite(out.rho));
                                CHECK(std::isfinite(out.dividend_rho));

                                // gamma and theta are the two that may diverge,
                                // and each has only one direction to diverge in:
                                // gamma is a density over a positive scale, and
                                // theta's unbounded term is a decay.
                                CHECK(out.gamma >= 0.0);
                                if (!std::isfinite(out.gamma)) {
                                    ++infinite;
                                    CHECK(out.gamma > 0.0);
                                }
                                if (!std::isfinite(out.theta)) {
                                    CHECK(out.theta < 0.0);
                                }

                                // A price is bounded by the discounted spot for a
                                // call and the discounted strike for a put, and is
                                // never negative. The closed form has no way to
                                // return a number outside that, and if it did, no
                                // tolerance test would notice.
                                CHECK(out.price >= 0.0);
                                const double bound = (type == OptionType::Call)
                                                         ? spot * std::exp(-market.dividend_yield
                                                                           * expiry)
                                                         : strike * std::exp(-rate * expiry);
                                CHECK(out.price <= bound * (1.0 + 1e-12) + 1e-300);
                            }
                        }
                    }
                }
            }
        }

        MESSAGE("domain sweep: " << priced << " priced, " << rejected
                                 << " rejected as unrepresentable, " << infinite
                                 << " with an infinite gamma");
        CHECK(priced > 4000);
        CHECK(rejected > 0);
        CHECK(infinite > 0);
    }

    TEST_CASE("a worthless underlying, and a strike of nothing")
    {
        // ln(S/K) is not finite at either end. The arithmetic carries it
        // correctly in every output but gamma, which is 0/0 at S = 0.
        const BlackScholesMarket dead{0.0, 0.3, 0.05, 0.01};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};
        const EuropeanVanilla put{100.0, 1.0, OptionType::Put};

        CHECK(touchstone::price(call, dead) == 0.0);
        CHECK(scaled_error(touchstone::price(put, dead), 100.0 * std::exp(-0.05)) <= 1e-15);
        CHECK(touchstone::gamma(call, dead) == 0.0);
        CHECK(touchstone::vega(call, dead) == 0.0);
        CHECK(std::isfinite(touchstone::theta(put, dead)));

        const BlackScholesMarket alive{100.0, 0.3, 0.05, 0.01};
        const EuropeanVanilla free_call{0.0, 1.0, OptionType::Call};
        const EuropeanVanilla free_put{0.0, 1.0, OptionType::Put};
        CHECK(scaled_error(touchstone::price(free_call, alive), 100.0 * std::exp(-0.01)) <= 1e-15);
        CHECK(touchstone::price(free_put, alive) == 0.0);
        CHECK(touchstone::gamma(free_call, alive) == 0.0);

        // Nothing against nothing.
        const PriceAndGreeks nothing =
            touchstone::price_and_greeks(free_call, {0.0, 0.3, 0.05, 0.01});
        CHECK(nothing.price == 0.0);
        CHECK(nothing.delta == 0.0);
        CHECK(nothing.gamma == 0.0);
        CHECK(nothing.vega == 0.0);
        CHECK(nothing.theta == 0.0);
    }


    TEST_CASE("inputs that used to be wrong, kept as regressions")
    {
        // Each of these came from an adversarial review of this library's first
        // version, and each returned a NaN, an infinity, or a wrong number. The
        // expected values are re-derived here from the formulas rather than
        // copied from what the fixed code now returns.

        SUBCASE("sigma sqrt(T) underflows although neither sigma nor T is zero")
        {
            // The decay term used to be read as "T is zero" and returned minus
            // infinity. It is -S phi(0) sigma / (2 sqrt(T)), a very small number.
            constexpr double vol = 1e-300;
            constexpr double expiry = 1e-100;
            const BlackScholesMarket market{100.0, vol, 0.0, 0.0};
            const double expected =
                -100.0 * touchstone::norm_pdf(0.0) * vol / (2.0 * std::sqrt(expiry));

            const double got = touchstone::theta({100.0, expiry, OptionType::Call}, market);
            CHECK(std::isfinite(got));
            CHECK(scaled_error(got, expected) <= 1e-15);
            CHECK(got < 0.0);
        }

        SUBCASE("a long expiry underflows the discounted strike to zero")
        {
            // With the spot already zero, S e^{-qT} - K e^{-rT} is then 0 - 0,
            // which used to be read as "the forward is at the strike" and gave
            // both sides a delta of one half. The put is certain to be
            // exercised and the call certain not to be.
            const BlackScholesMarket market{0.0, 0.0, 0.05, 0.0};
            CHECK(touchstone::delta({100.0, 20000.0, OptionType::Put}, market) == -1.0);
            CHECK(touchstone::delta({100.0, 20000.0, OptionType::Call}, market) == 0.0);
            CHECK(touchstone::price({100.0, 20000.0, OptionType::Call}, market) == 0.0);
        }

        SUBCASE("S times the total volatility underflows although neither does")
        {
            // gamma used to form S v and divide by it, so a denominator of
            // 1e-330 became zero and the quotient became infinity — or, where
            // the density had also underflowed, 0/0.
            constexpr double spot = 1e-300;
            constexpr double vol = 1e-30;
            const EuropeanVanilla call{spot, 1.0, OptionType::Call};

            // d1 = (r - q + sigma^2/2) T / v = 30 here, so the density is
            // phi(30) = 1.47e-196 and gamma is that over S over v.
            const double got = touchstone::gamma(call, {spot, vol, 3e-29, 0.0});
            CHECK(std::isfinite(got));
            CHECK(got > 1e130);
            CHECK(got < 1e140);
            CHECK(scaled_error(got, touchstone::norm_pdf(30.0) / spot / vol) <= 1e-15);

            // One rate further out the density really is zero, and so is gamma.
            CHECK(touchstone::gamma(call, {spot, vol, 1e-27, 0.0}) == 0.0);
        }

        SUBCASE("rho carries a factor of T, and T times the discounted strike can overflow")
        {
            // K e^{-rT} fits; T K e^{-rT} does not, and inf * 0 in the call's
            // rho was a NaN. Rejected on the way in instead.
            CHECK_THROWS_AS(touchstone::price_and_greeks({1e12, 1e300, OptionType::Put},
                                                         {0.0, 0.0, 0.0, 0.0}),
                            std::invalid_argument);
            CHECK_THROWS_AS(touchstone::price_and_greeks({1e6, 14000.0, OptionType::Call},
                                                         {1.0, 0.3, -0.05, 0.0}),
                            std::invalid_argument);
            CHECK_THROWS_AS(touchstone::price_and_greeks({100.0, 1.0, OptionType::Call},
                                                         {0.0, 1e200, 0.05, 0.01}),
                            std::invalid_argument);
        }
    }

    TEST_CASE("inputs outside the domain are rejected, not priced")
    {
        const BlackScholesMarket market{100.0, 0.2, 0.03, 0.01};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};

        const auto rejected = [&](EuropeanVanilla option, BlackScholesMarket state) {
            CHECK_THROWS_AS(touchstone::require_valid(option, state), std::invalid_argument);
            CHECK_THROWS_AS(touchstone::price(option, state), std::invalid_argument);
            CHECK_THROWS_AS(touchstone::price_and_greeks(option, state), std::invalid_argument);
        };

        rejected(call, {-1.0, 0.2, 0.03, 0.01});                       // negative spot
        rejected({-100.0, 1.0, OptionType::Call}, market);             // negative strike
        rejected(call, {100.0, -0.2, 0.03, 0.01});                     // negative vol
        rejected({100.0, -1.0, OptionType::Call}, market);             // negative expiry
        rejected(call, {std::nan(""), 0.2, 0.03, 0.01});               // NaN spot
        rejected(call, {100.0, 0.2, infinity, 0.01});                  // infinite rate
        rejected(call, {100.0, 0.2, 0.03, -infinity});                 // infinite yield
        rejected({infinity, 1.0, OptionType::Call}, market);           // infinite strike

        // A negative rate or yield is a market state, not an error: the golden
        // grid contains one.
        CHECK_NOTHROW(touchstone::require_valid(call, {100.0, 0.2, -0.005, -0.01}));
    }
}
