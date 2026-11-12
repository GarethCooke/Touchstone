#include "american_file.hpp"

#include "json_file.hpp"

#ifndef TOUCHSTONE_AMERICAN_PATH
#error "TOUCHSTONE_AMERICAN_PATH must name golden/american_vanilla.json; tests/CMakeLists defines it."
#endif

namespace touchstone::testing {
namespace {

constexpr const char* expected_schema = "touchstone/golden/american_vanilla@1";

AmericanCase parse_case(const nlohmann::json& row)
{
    const RowInputs<Exercise::American> inputs =
        read_inputs<Exercise::American>(row, "american file");

    AmericanCase parsed{};
    parsed.option = inputs.option;
    parsed.market = inputs.market;
    parsed.expiry_days = inputs.expiry_days;

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
    file.path = fixture_path("TOUCHSTONE_AMERICAN_PATH", TOUCHSTONE_AMERICAN_PATH);

    const nlohmann::json document = read_json(file.path, "american file");
    file.schema = require_schema(document, expected_schema, "american file");

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
    return describe_inputs(row.option.type, row.option.strike, row.market, row.expiry_days);
}

}  // namespace touchstone::testing
