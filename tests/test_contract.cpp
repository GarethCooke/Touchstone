// The exercise style is part of the contract's type, so a method that cannot
// price an American option refuses one before the program runs.
//
// The refusals are compile-time facts, and they are asserted as compile-time
// facts: each concept below asks whether one family of entry points accepts a
// contract, and the `static_assert`s say which contracts each accepts. A change
// that let an American contract through to the closed form — a converting
// constructor, a template where an overload was — fails to compile this file,
// which is the failure that matters: the alternative is a program that compiles
// and prices an American option as a European one.

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/contract.hpp>
#include <touchstone/implied_vol.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/pde.hpp>

#include <doctest/doctest.h>

#include <concepts>
#include <type_traits>

namespace {

using touchstone::AmericanVanilla;
using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::Exercise;
using touchstone::OptionType;
using touchstone::QuotedMarket;

template <class Contract>
concept validated_by_closed_form = requires(const Contract& c, const BlackScholesMarket& m) {
    touchstone::require_valid(c, m);
};

template <class Contract>
concept priced_by_closed_form = requires(const Contract& c, const BlackScholesMarket& m) {
    touchstone::price(c, m);
    touchstone::delta(c, m);
    touchstone::gamma(c, m);
    touchstone::vega(c, m);
    touchstone::theta(c, m);
    touchstone::rho(c, m);
    touchstone::dividend_rho(c, m);
    touchstone::price_and_greeks(c, m);
};

template <class Contract>
concept evaluated_by_closed_form =
    std::constructible_from<touchstone::ClosedForm, const Contract&, const BlackScholesMarket&>
    || std::constructible_from<touchstone::ClosedFormQuote, const Contract&, const QuotedMarket&>;

template <class Contract>
concept priced_by_monte_carlo = requires(const Contract& c, const BlackScholesMarket& m) {
    touchstone::monte_carlo(c, m);
    touchstone::monte_carlo(c, m, touchstone::MonteCarloSettings{});
    touchstone::pathwise_payoff_delta(c, 1.0, 1.0);
};

template <class Contract>
concept inverted_by_implied_vol = requires(const Contract& c, const QuotedMarket& q) {
    touchstone::implied_vol(c, q, 1.0);
    touchstone::implied_vol_safeguarded(c, q, 1.0);
    touchstone::price_scale(c, q);
    touchstone::lowest_price(c, q);
    touchstone::highest_price(c, q);
};

template <class Contract>
concept bumped = requires(const Contract& c,
                          const BlackScholesMarket& m,
                          double (*pricer)(const EuropeanVanilla&, const BlackScholesMarket&)) {
    touchstone::bump_greeks(c, m);
    touchstone::bump_greeks(c, m, touchstone::BumpSizes{}, pricer);
};

template <class Contract>
concept priced_by_grid = requires(const Contract& c, const BlackScholesMarket& m) {
    touchstone::crank_nicolson(c, m);
    touchstone::require_valid(c, m, touchstone::PdeSettings{});
};

template <class Contract>
concept has_payoff = requires(const Contract& c) { touchstone::payoff(c, 1.0); };

// The European contract: every method in the library prices it.
static_assert(validated_by_closed_form<EuropeanVanilla>);
static_assert(priced_by_closed_form<EuropeanVanilla>);
static_assert(evaluated_by_closed_form<EuropeanVanilla>);
static_assert(priced_by_monte_carlo<EuropeanVanilla>);
static_assert(inverted_by_implied_vol<EuropeanVanilla>);
static_assert(bumped<EuropeanVanilla>);
static_assert(priced_by_grid<EuropeanVanilla>);
static_assert(has_payoff<EuropeanVanilla>);

// The American contract: the grid prices it, it has a payoff, and every other
// method refuses it at compile time.
static_assert(!validated_by_closed_form<AmericanVanilla>);
static_assert(!priced_by_closed_form<AmericanVanilla>);
static_assert(!evaluated_by_closed_form<AmericanVanilla>);
static_assert(!priced_by_monte_carlo<AmericanVanilla>);
static_assert(!inverted_by_implied_vol<AmericanVanilla>);
static_assert(!bumped<AmericanVanilla>);
static_assert(priced_by_grid<AmericanVanilla>);
static_assert(has_payoff<AmericanVanilla>);

// Neither converts to the other, in either direction: `with_exercise` is the only
// way across, and it is spelled out.
static_assert(!std::is_convertible_v<AmericanVanilla, EuropeanVanilla>);
static_assert(!std::is_convertible_v<EuropeanVanilla, AmericanVanilla>);
static_assert(!std::is_constructible_v<EuropeanVanilla, AmericanVanilla>);

// One definition of the fields: the two are the same template, so they are the
// same aggregate and the same size.
static_assert(std::is_same_v<EuropeanVanilla, touchstone::Vanilla<Exercise::European>>);
static_assert(std::is_same_v<AmericanVanilla, touchstone::Vanilla<Exercise::American>>);
static_assert(sizeof(EuropeanVanilla) == sizeof(AmericanVanilla));
static_assert(std::is_aggregate_v<EuropeanVanilla> && std::is_aggregate_v<AmericanVanilla>);

}  // namespace

TEST_SUITE("contract")
{
    TEST_CASE("the refusals above are compile-time facts")
    {
        // Everything in this file that matters was decided when it compiled. This
        // case exists so that the suite has a name in the test report, and says
        // what was checked.
        MESSAGE("American contracts refused at compile time by: require_valid (closed form), "
                "price and the six Greeks, price_and_greeks, ClosedForm, ClosedFormQuote, "
                "monte_carlo, pathwise_payoff_delta, implied_vol, implied_vol_safeguarded, "
                "price_scale, lowest_price, highest_price, bump_greeks (both); accepted by "
                "crank_nicolson, the grid's require_valid, and payoff");
        CHECK(priced_by_grid<AmericanVanilla>);
        CHECK_FALSE(priced_by_closed_form<AmericanVanilla>);
    }

    TEST_CASE("with_exercise keeps every field and changes only the type")
    {
        constexpr EuropeanVanilla european{97.5, 0.75, OptionType::Put};
        constexpr AmericanVanilla american = touchstone::with_exercise<Exercise::American>(european);
        static_assert(american.strike == european.strike);
        static_assert(american.expiry_years == european.expiry_years);
        static_assert(american.type == european.type);

        constexpr EuropeanVanilla back = touchstone::with_exercise<Exercise::European>(american);
        static_assert(back.strike == european.strike && back.expiry_years == european.expiry_years
                      && back.type == european.type);
        CHECK(back.strike == 97.5);
    }

    TEST_CASE("one payoff for both exercise styles")
    {
        // The Monte Carlo reads it at expiry and the grid at every node and every
        // step; the formula is written once and the exercise style plays no part.
        constexpr EuropeanVanilla call{100.0, 1.0, OptionType::Call};
        constexpr AmericanVanilla put{100.0, 1.0, OptionType::Put};
        static_assert(touchstone::payoff(call, 120.0) == 20.0);
        static_assert(touchstone::payoff(call, 80.0) == 0.0);
        static_assert(touchstone::payoff(put, 80.0) == 20.0);
        static_assert(touchstone::payoff(put, 120.0) == 0.0);
        // An Euler path can end below zero, and a put there pays more than K.
        static_assert(touchstone::payoff(put, -5.0) == 105.0);

        for (const double spot : {0.0, 50.0, 99.999, 100.0, 100.001, 250.0}) {
            CAPTURE(spot);
            CHECK(touchstone::payoff(touchstone::with_exercise<Exercise::American>(call), spot)
                  == touchstone::payoff(call, spot));
        }
    }
}
