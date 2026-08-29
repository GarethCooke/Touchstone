#include "golden_file.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

#ifndef TOUCHSTONE_GOLDEN_PATH
#error "TOUCHSTONE_GOLDEN_PATH must name golden/bs_vanilla.json; the tests CMakeLists defines it."
#endif

namespace touchstone::testing {
namespace {

/// The schema these tests were written against. `golden/SCHEMA.md`: "A change
/// to the meaning of any field, or to the units below, is a new schema id."
constexpr const char* expected_schema = "touchstone/golden/bs_vanilla@1";

std::string golden_path()
{
    if (const char* from_environment = std::getenv("TOUCHSTONE_GOLDEN_PATH")) {
        return from_environment;
    }
    return TOUCHSTONE_GOLDEN_PATH;
}

GoldenCase parse_case(const nlohmann::json& row)
{
    const std::string type = row.at("type").get<std::string>();
    if (type != "call" && type != "put") {
        throw std::runtime_error("golden file: unknown option type '" + type + "'");
    }

    GoldenCase parsed{};
    parsed.option.strike = row.at("strike").get<double>();
    parsed.option.expiry_years = row.at("expiry_years").get<double>();
    parsed.option.type = (type == "call") ? OptionType::Call : OptionType::Put;

    parsed.market.spot = row.at("spot").get<double>();
    parsed.market.vol = row.at("vol").get<double>();
    parsed.market.rate = row.at("rate").get<double>();
    parsed.market.dividend_yield = row.at("dividend_yield").get<double>();

    parsed.reference.price = row.at("price").get<double>();
    parsed.reference.delta = row.at("delta").get<double>();
    parsed.reference.gamma = row.at("gamma").get<double>();
    parsed.reference.vega = row.at("vega").get<double>();
    parsed.reference.theta = row.at("theta").get<double>();
    parsed.reference.rho = row.at("rho").get<double>();
    parsed.reference.dividend_rho = row.at("dividend_rho").get<double>();

    parsed.expiry_days = row.at("expiry_days").get<int>();
    if (row.contains("label")) {
        parsed.label = row.at("label").get<std::string>();
    }
    return parsed;
}

GoldenFile load()
{
    GoldenFile file{};
    file.path = golden_path();

    std::ifstream stream(file.path);
    if (!stream) {
        throw std::runtime_error("golden file: cannot open '" + file.path + "'");
    }

    nlohmann::json document = nlohmann::json::parse(stream);

    file.schema = document.at("schema").get<std::string>();
    if (file.schema != expected_schema) {
        throw std::runtime_error("golden file: schema is '" + file.schema + "', these tests were "
                                 "written against '" + std::string(expected_schema) + "'");
    }

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
    out << (row.option.type == OptionType::Call ? "call" : "put") << " S=" << row.market.spot
        << " K=" << row.option.strike << " vol=" << row.market.vol << " r=" << row.market.rate
        << " q=" << row.market.dividend_yield << " days=" << row.expiry_days
        << " T=" << row.option.expiry_years;
    return out.str();
}

}  // namespace touchstone::testing
