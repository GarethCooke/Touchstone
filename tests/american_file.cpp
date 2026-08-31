#include "american_file.hpp"

#include <nlohmann/json.hpp>

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#ifndef TOUCHSTONE_AMERICAN_PATH
#error "TOUCHSTONE_AMERICAN_PATH must name golden/american_vanilla.json; tests/CMakeLists defines it."
#endif

namespace touchstone::testing {
namespace {

constexpr const char* expected_schema = "touchstone/golden/american_vanilla@1";

std::string american_path()
{
    if (const char* from_environment = std::getenv("TOUCHSTONE_AMERICAN_PATH")) {
        return from_environment;
    }
    return TOUCHSTONE_AMERICAN_PATH;
}

AmericanCase parse_case(const nlohmann::json& row)
{
    const std::string type = row.at("type").get<std::string>();
    if (type != "call" && type != "put") {
        throw std::runtime_error("american file: unknown option type '" + type + "'");
    }

    AmericanCase parsed{};
    parsed.option.strike = row.at("strike").get<double>();
    parsed.option.expiry_years = row.at("expiry_years").get<double>();
    parsed.option.type = (type == "call") ? OptionType::Call : OptionType::Put;

    parsed.market.spot = row.at("spot").get<double>();
    parsed.market.vol = row.at("vol").get<double>();
    parsed.market.rate = row.at("rate").get<double>();
    parsed.market.dividend_yield = row.at("dividend_yield").get<double>();
    parsed.expiry_days = row.at("expiry_days").get<int>();

    parsed.price = row.at("price").get<double>();
    parsed.delta = row.at("delta").get<double>();
    parsed.gamma = row.at("gamma").get<double>();
    parsed.spread = row.at("spread").get<double>();
    parsed.delta_spread = row.at("delta_spread").get<double>();
    parsed.gamma_spread = row.at("gamma_spread").get<double>();
    return parsed;
}

AmericanFile load()
{
    AmericanFile file{};
    file.path = american_path();

    std::ifstream stream(file.path);
    if (!stream) {
        throw std::runtime_error("american file: cannot open '" + file.path + "'");
    }

    nlohmann::json document = nlohmann::json::parse(stream);

    file.schema = document.at("schema").get<std::string>();
    if (file.schema != expected_schema) {
        throw std::runtime_error("american file: schema is '" + file.schema
                                 + "', these tests were written against '"
                                 + std::string(expected_schema) + "'");
    }

    file.oracle_version = document.at("oracle").at("version").get<std::string>();
    file.engine = document.at("oracle").at("engine").get<std::string>();
    file.worst_spread = document.at("tolerances").at("worst_spread").get<double>();
    file.declared_cases = document.at("counts").at("cases").get<std::size_t>();

    for (const auto& row : document.at("cases")) {
        file.cases.push_back(parse_case(row));
    }
    return file;
}

}  // namespace

bool AmericanCase::equals_european() const noexcept
{
    if (option.type == OptionType::Call) {
        return market.dividend_yield == 0.0 && market.rate >= 0.0;
    }
    return market.rate <= 0.0 && market.dividend_yield >= 0.0;
}

const AmericanFile& american_file()
{
    static const AmericanFile file = load();
    return file;
}

std::string describe(const AmericanCase& row)
{
    std::ostringstream out;
    out << std::setprecision(17);
    out << (row.option.type == OptionType::Call ? "call" : "put") << " S=" << row.market.spot
        << " K=" << row.option.strike << " vol=" << row.market.vol << " r=" << row.market.rate
        << " q=" << row.market.dividend_yield << " days=" << row.expiry_days;
    return out.str();
}

}  // namespace touchstone::testing
