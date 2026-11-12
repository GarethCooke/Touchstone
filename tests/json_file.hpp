// Reading the committed JSON files the tests compare against: where each one is,
// the checks every one of them gets before a number is read, and the inputs of
// a row of either golden file.

#pragma once

#include <touchstone/black_scholes.hpp>
#include <touchstone/contract.hpp>

#include <nlohmann/json.hpp>

#include <stdexcept>
#include <string>

namespace touchstone::testing {

/// The file's path: the environment variable `variable` if it is set — which is
/// how CI points the same tests at a regenerated file — and the path
/// `tests/CMakeLists.txt` compiled in otherwise.
[[nodiscard]] std::string fixture_path(const char* variable, const char* compiled_in);

/// Open and parse `path`. Throws `std::runtime_error`, naming `what`, if the
/// file is missing or is not JSON.
[[nodiscard]] nlohmann::json read_json(const std::string& path, const char* what);

/// The same, for a file written by Python's `json` module, which writes `NaN`,
/// `Infinity` and `-Infinity` as bare literals that JSON does not have. Each is
/// read as `null` — outside strings only, since the experiments' prose uses the
/// same words — so a test that reaches for one finds a null where it expected a
/// number and fails rather than reading a number that was never there.
[[nodiscard]] nlohmann::json read_python_json(const std::string& path, const char* what);

/// The document's `schema` field, which must be `expected`. Throws otherwise: a
/// file that has changed its meaning must stop the tests rather than be compared
/// against as though it had not.
std::string require_schema(const nlohmann::json& document, const char* expected, const char* what);

/// `"call"` or `"put"`; anything else throws.
[[nodiscard]] OptionType read_option_type(const nlohmann::json& row, const char* what);

/// A row's contract, its market and its expiry in days, as both golden files
/// write them.
template <Exercise E>
struct RowInputs {
    Vanilla<E> option{};
    BlackScholesMarket market{};
    int expiry_days{};
};

template <Exercise E>
[[nodiscard]] RowInputs<E> read_inputs(const nlohmann::json& row, const char* what)
{
    RowInputs<E> inputs{};
    inputs.option.strike = row.at("strike").get<double>();
    inputs.option.expiry_years = row.at("expiry_years").get<double>();
    inputs.option.type = read_option_type(row, what);
    inputs.market.spot = row.at("spot").get<double>();
    inputs.market.vol = row.at("vol").get<double>();
    inputs.market.rate = row.at("rate").get<double>();
    inputs.market.dividend_yield = row.at("dividend_yield").get<double>();
    inputs.expiry_days = row.at("expiry_days").get<int>();
    return inputs;
}

/// A row's inputs on one line, at full precision:
/// `call S=... K=... vol=... r=... q=... days=...`.
[[nodiscard]] std::string describe_inputs(OptionType type,
                                          double strike,
                                          const BlackScholesMarket& market,
                                          int expiry_days);

}  // namespace touchstone::testing
