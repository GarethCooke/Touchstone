// The seven outputs of `PriceAndGreeks`, by name and by member, in the order
// the struct declares them — and the worst error per field over a sweep that
// compares all seven at once.

#pragma once

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>

#include <doctest/doctest.h>

#include <array>
#include <cstddef>
#include <iomanip>
#include <sstream>
#include <string>

namespace touchstone::testing {

struct GreekField {
    const char* name;
    double PriceAndGreeks::* value;
};

inline constexpr std::array<GreekField, 7> greek_fields{{
    {"price", &PriceAndGreeks::price},
    {"delta", &PriceAndGreeks::delta},
    {"gamma", &PriceAndGreeks::gamma},
    {"vega", &PriceAndGreeks::vega},
    {"theta", &PriceAndGreeks::theta},
    {"rho", &PriceAndGreeks::rho},
    {"dividend_rho", &PriceAndGreeks::dividend_rho},
}};

using GreekTolerances = std::array<double, greek_fields.size()>;

/// The worst scaled error of each field over a sweep, reported one line per
/// field and checked against a tolerance per field.
class WorstPerField {
public:
    void observe(std::size_t field, double actual, double expected, const GoldenCase& row)
    {
        worst_[field].observe(actual, expected, row);
    }

    void observe(const PriceAndGreeks& actual, const PriceAndGreeks& expected, const GoldenCase& row)
    {
        for (std::size_t f = 0; f < greek_fields.size(); ++f) {
            observe(f, actual.*(greek_fields[f].value), expected.*(greek_fields[f].value), row);
        }
    }

    [[nodiscard]] double error(std::size_t field) const noexcept { return worst_[field].error(); }

    /// `header`, then each field's name and worst error, and its tolerance if
    /// `tolerances` is given.
    [[nodiscard]] std::string report(const std::string& header,
                                     const GreekTolerances* tolerances = nullptr) const
    {
        std::ostringstream out;
        out << header;
        for (std::size_t f = 0; f < greek_fields.size(); ++f) {
            out << "\n    " << std::left << std::setw(14) << greek_fields[f].name << std::right
                << std::scientific << std::setprecision(3) << worst_[f].error();
            if (tolerances != nullptr) {
                out << "   tolerance " << (*tolerances)[f];
            }
        }
        return out.str();
    }

    void check(const GreekTolerances& tolerances) const
    {
        for (std::size_t f = 0; f < greek_fields.size(); ++f) {
            CAPTURE(greek_fields[f].name);
            CHECK_MESSAGE(worst_[f].error() <= tolerances[f],
                          worst_[f].describe(greek_fields[f].name));
        }
    }

    void check(double tolerance) const
    {
        GreekTolerances all{};
        all.fill(tolerance);
        check(all);
    }

private:
    std::array<Worst, greek_fields.size()> worst_{};
};

}  // namespace touchstone::testing
