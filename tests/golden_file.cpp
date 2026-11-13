#include "golden_file.hpp"

#include "greek_fields.hpp"
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
    GoldenCase parsed{};
    static_cast<RowInputs<Exercise::European>&>(parsed) =
        read_inputs<Exercise::European>(row, "golden file");

    for (const GreekField& field : greek_fields) {
        parsed.reference.*(field.value) = row.at(field.name).get<double>();
    }

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

void Worst::observe(double actual, double reference, const GoldenCase& source)
{
    if (largest_.observe(scaled_error(actual, reference), source)) {
        actual_ = actual;
        reference_ = reference;
    }
}

std::string Worst::describe(const char* field) const
{
    std::ostringstream out;
    out << std::setprecision(17);
    out << "worst " << field << " error " << largest_.value();
    const std::string at = largest_.at();
    if (!at.empty()) {
        out << "\n    computed  " << actual_ << "\n    reference " << reference_
            << "\n    at        " << at;
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
