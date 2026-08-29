// The closed form against QuantLib's answers, on all 7234 rows of the golden
// file, at the tolerances the file itself carries.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>

#include <doctest/doctest.h>

#include <array>
#include <cstddef>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

namespace {

using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;
using touchstone::testing::Worst;

struct Field {
    const char* name;
    double PriceAndGreeks::* value;
};

constexpr std::array<Field, 7> fields{{
    {"price", &PriceAndGreeks::price},
    {"delta", &PriceAndGreeks::delta},
    {"gamma", &PriceAndGreeks::gamma},
    {"vega", &PriceAndGreeks::vega},
    {"theta", &PriceAndGreeks::theta},
    {"rho", &PriceAndGreeks::rho},
    {"dividend_rho", &PriceAndGreeks::dividend_rho},
}};

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
