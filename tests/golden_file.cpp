#include "golden_file.hpp"

#include "json_file.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>

#ifndef TOUCHSTONE_GOLDEN_PATH
#error "TOUCHSTONE_GOLDEN_PATH must name golden/bs_vanilla.json; the tests CMakeLists defines it."
#endif

namespace touchstone::testing {
namespace {

/// The schema these tests were written against. `golden/SCHEMA.md`: "A change
/// to the meaning of any field, or to the units below, is a new schema id."
constexpr const char* expected_schema = "touchstone/golden/bs_vanilla@1";

GoldenCase parse_case(const nlohmann::json& row)
{
    const RowInputs<Exercise::European> inputs = read_inputs<Exercise::European>(row, "golden file");

    GoldenCase parsed{};
    parsed.option = inputs.option;
    parsed.market = inputs.market;
    parsed.expiry_days = inputs.expiry_days;

    parsed.reference.price = row.at("price").get<double>();
    parsed.reference.delta = row.at("delta").get<double>();
    parsed.reference.gamma = row.at("gamma").get<double>();
    parsed.reference.vega = row.at("vega").get<double>();
    parsed.reference.theta = row.at("theta").get<double>();
    parsed.reference.rho = row.at("rho").get<double>();
    parsed.reference.dividend_rho = row.at("dividend_rho").get<double>();

    if (row.contains("label")) {
        parsed.label = row.at("label").get<std::string>();
    }
    return parsed;
}

GoldenFile load()
{
    GoldenFile file{};
    file.path = fixture_path("TOUCHSTONE_GOLDEN_PATH", TOUCHSTONE_GOLDEN_PATH);

    const nlohmann::json document = read_json(file.path, "golden file");
    file.schema = require_schema(document, expected_schema, "golden file");

    file.oracle_version = document.at("oracle").at("version").get<std::string>();
    file.tolerance_cases = document.at("tolerances").at("cases").get<double>();
    file.tolerance_edge_cases = document.at("tolerances").at("edge_cases").get<double>();
    file.declared_cases = document.at("counts").at("cases").get<std::size_t>();
    file.declared_edge_cases = document.at("counts").at("edge_cases").get<std::size_t>();

    for (const auto& row : document.at("cases")) {
        file.cases.push_back(parse_case(row));
    }
    for (const auto& row : document.at("edge_cases")) {
        file.edge_cases.push_back(parse_case(row));
    }
    return file;
}

}  // namespace

const GoldenFile& golden_file()
{
    static const GoldenFile file = load();
    return file;
}

double scaled_error(double actual, double reference) noexcept
{
    if (actual == reference) {
        return 0.0;  // Also the only way two infinities of the same sign agree.
    }
    if (std::isnan(actual) || std::isnan(reference) || std::isinf(actual) || std::isinf(reference)) {
        return std::numeric_limits<double>::infinity();
    }
    const double scale = std::max(std::abs(reference), 1.0);
    return std::abs(actual - reference) / scale;
}

void Worst::observe(double actual, double reference, const GoldenCase& source)
{
    const double error = scaled_error(actual, reference);
    if (!seen_ || error > error_) {
        seen_ = true;
        error_ = error;
        actual_ = actual;
        reference_ = reference;
        source_ = source;
    }
}

std::string Worst::describe(const char* field) const
{
    std::ostringstream out;
    out << std::setprecision(17);
    out << "worst " << field << " error " << error_;
    if (seen_) {
        out << "\n    computed  " << actual_ << "\n    reference " << reference_ << "\n    at        "
            << touchstone::testing::describe(source_);
    }
    return out.str();
}

std::string describe(const GoldenCase& row)
{
    std::ostringstream out;
    out << std::setprecision(17);
    if (!row.label.empty()) {
        out << '[' << row.label << "] ";
    }
    out << describe_inputs(row.option.type, row.option.strike, row.market, row.expiry_days)
        << " T=" << row.option.expiry_years;
    return out.str();
}

}  // namespace touchstone::testing
