// The closed form against QuantLib's answers, on all 7234 rows of the golden
// file, at the tolerances the file itself carries.

#include "golden_file.hpp"
#include "greek_fields.hpp"

#include <touchstone/black_scholes.hpp>

#include <doctest/doctest.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;
using touchstone::testing::Worst;

constexpr const auto& fields = touchstone::testing::greek_fields;

/// Price every row, track the worst scaled error per field, then assert once
/// per field. Seven assertions rather than fifty thousand: a run that passes
/// still reports the numbers, and a run that fails names the row.
void sweep(const std::vector<GoldenCase>& rows, double tolerance, const char* what)
{
    REQUIRE_FALSE(rows.empty());

    std::array<Worst, fields.size()> worst{};
    for (const GoldenCase& row : rows) {
        const PriceAndGreeks computed = touchstone::price_and_greeks(row.option, row.market);
        for (std::size_t f = 0; f < fields.size(); ++f) {
            worst[f].observe(computed.*(fields[f].value), row.reference.*(fields[f].value), row);
        }
    }

    std::ostringstream report;
    report << what << ": " << rows.size() << " rows at tolerance " << tolerance
           << "; worst scaled error per field";
    for (std::size_t f = 0; f < fields.size(); ++f) {
        report << "\n    " << std::left << std::setw(14) << fields[f].name << std::right
               << std::scientific << std::setprecision(3) << worst[f].error();
    }
    MESSAGE(report.str());

    for (std::size_t f = 0; f < fields.size(); ++f) {
        CHECK_MESSAGE(worst[f].error() <= tolerance, worst[f].describe(fields[f].name));
    }
}

}  // namespace

TEST_SUITE("closed-form")
{
    TEST_CASE("the golden file is the one these tests were written against")
    {
        const auto& file = touchstone::testing::golden_file();
        MESSAGE("golden file " << file.path << "\n    schema  " << file.schema
                               << "\n    oracle  QuantLib " << file.oracle_version);

        CHECK(file.schema == "touchstone/golden/bs_vanilla@1");
        CHECK(file.cases.size() == file.declared_cases);
        CHECK(file.edge_cases.size() == file.declared_edge_cases);
        CHECK(file.cases.size() == 7200u);
        CHECK(file.edge_cases.size() == 34u);
        CHECK(file.tolerance_cases == 1e-10);   // the roadmap's stated T1 figure
        CHECK(file.tolerance_edge_cases == 1e-8);
    }

    TEST_CASE("main grid: price and all six Greeks")
    {
        const auto& file = touchstone::testing::golden_file();
        sweep(file.cases, file.tolerance_cases, "main grid");
    }

    TEST_CASE("edge block: near-degenerate corners")
    {
        const auto& file = touchstone::testing::golden_file();
        sweep(file.edge_cases, file.tolerance_edge_cases, "edge block");
    }

    TEST_CASE("the single-value accessors agree with price_and_greeks")
    {
        // Seven entry points computing seven expressions is seven chances for a
        // copy-paste error that the golden sweep above would never see, because
        // it only ever calls the aggregate.
        const auto& file = touchstone::testing::golden_file();
        constexpr double tolerance = 1e-15;

        Worst worst_of_all{};
        for (const GoldenCase& row : file.cases) {
            const PriceAndGreeks all = touchstone::price_and_greeks(row.option, row.market);
            const std::array<double, 7> one_at_a_time{
                touchstone::price(row.option, row.market),
                touchstone::delta(row.option, row.market),
                touchstone::gamma(row.option, row.market),
                touchstone::vega(row.option, row.market),
                touchstone::theta(row.option, row.market),
                touchstone::rho(row.option, row.market),
                touchstone::dividend_rho(row.option, row.market),
            };
            for (std::size_t f = 0; f < fields.size(); ++f) {
                worst_of_all.observe(one_at_a_time[f], all.*(fields[f].value), row);
            }
        }

        std::ostringstream report;
        report << "accessors vs price_and_greeks: worst scaled difference over " << file.cases.size()
               << " rows x 7 values: " << std::scientific << std::setprecision(3)
               << worst_of_all.error();
        MESSAGE(report.str());
        CHECK_MESSAGE(worst_of_all.error() <= tolerance, worst_of_all.describe("accessor"));
    }
}

// The evaluation behind the free functions: its volatility-free half is what an
// implied-volatility search builds once and reuses at every step, so it has to
// be the same arithmetic as the one-shot evaluation, and between them the two
// halves have to guard exactly the domain `require_valid` does.
TEST_SUITE("closed-form")
{
    TEST_CASE("the volatility-free half, built once, is the closed form at any volatility")
    {
        const auto& file = touchstone::testing::golden_file();
        std::size_t rows = 0;
        std::size_t differing = 0;
        for (const auto* block : {&file.cases, &file.edge_cases}) {
            for (const GoldenCase& row : *block) {
                const touchstone::QuotedMarket quoted{row.market.spot, row.market.rate,
                                                      row.market.dividend_yield};
                const touchstone::ClosedFormQuote quote(row.option, quoted);
                const PriceAndGreeks reused = quote.at(row.market.vol).price_and_greeks();
                const PriceAndGreeks direct = touchstone::price_and_greeks(row.option, row.market);
                ++rows;
                for (const auto& field : fields) {
                    differing += (reused.*(field.value) == direct.*(field.value)) ? 0u : 1u;
                }
            }
        }
        MESSAGE("quote reused at the row's volatility against the one-shot evaluation: "
                << rows << " rows, " << differing << " values not identical to the bit");
        CHECK(differing == 0u);
    }

    TEST_CASE("the two halves refuse exactly what require_valid refuses")
    {
        using touchstone::BlackScholesMarket;
        using touchstone::ClosedForm;
        using touchstone::ClosedFormQuote;
        using touchstone::EuropeanVanilla;
        using touchstone::OptionType;
        using touchstone::QuotedMarket;
        const double inf = std::numeric_limits<double>::infinity();
        const double nan = std::numeric_limits<double>::quiet_NaN();

        struct Input {
            const char* what;
            EuropeanVanilla option;
            BlackScholesMarket market;
            bool volatility_is_the_fault;
        };
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};
        const Input inputs[] = {
            {"negative spot", call, {-1.0, 0.2, 0.05, 0.0}, false},
            {"NaN strike", {nan, 1.0, OptionType::Call}, {100.0, 0.2, 0.05, 0.0}, false},
            {"negative expiry", {100.0, -1.0, OptionType::Put}, {100.0, 0.2, 0.05, 0.0}, false},
            {"infinite rate", call, {100.0, 0.2, inf, 0.0}, false},
            {"NaN dividend yield", call, {100.0, 0.2, 0.05, nan}, false},
            {"discount factor overflows", call, {100.0, 0.2, -800.0, 0.0}, false},
            {"carry overflows", {100.0, 1e10, OptionType::Call}, {100.0, 0.0, 0.0, 1e300}, false},
            {"negative volatility", call, {100.0, -0.2, 0.05, 0.0}, true},
            {"NaN volatility", call, {100.0, nan, 0.05, 0.0}, true},
            {"half the variance overflows", call, {100.0, 1e200, 0.05, 0.0}, true},
            {"the escaped NaN, refused by its carry", {100.0, 1e10, OptionType::Call},
             {100.0, std::sqrt(2e300), 0.0, 1e300}, false},
        };

        for (const Input& input : inputs) {
            CAPTURE(input.what);
            CHECK_THROWS_AS(touchstone::require_valid(input.option, input.market),
                            std::invalid_argument);
            CHECK_THROWS_AS(ClosedForm(input.option, input.market), std::invalid_argument);
            const QuotedMarket quoted{input.market.spot, input.market.rate,
                                      input.market.dividend_yield};
            if (input.volatility_is_the_fault) {
                const ClosedFormQuote quote(input.option, quoted);
                CHECK_THROWS_AS(static_cast<void>(quote.at(input.market.vol)),
                                std::invalid_argument);
            } else {
                CHECK_THROWS_AS(ClosedFormQuote(input.option, quoted), std::invalid_argument);
            }
        }
    }
}
