#include "json_file.hpp"

#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string_view>

namespace touchstone::testing {

std::string fixture_path(const char* variable, const char* compiled_in)
{
    if (const char* from_environment = std::getenv(variable)) {
        return from_environment;
    }
    return compiled_in;
}

namespace {

[[nodiscard]] std::string read_text(const std::string& path, const char* what)
{
    std::ifstream stream(path);
    if (!stream) {
        throw std::runtime_error(std::string(what) + ": cannot open '" + path + "'");
    }
    std::ostringstream text;
    text << stream.rdbuf();
    return text.str();
}

}  // namespace

nlohmann::json read_json(const std::string& path, const char* what)
{
    return nlohmann::json::parse(read_text(path, what));
}

nlohmann::json read_python_json(const std::string& path, const char* what)
{
    const std::string text = read_text(path, what);

    std::string json;
    json.reserve(text.size());
    bool in_string = false;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char c = text[i];
        if (in_string) {
            json += c;
            if (c == '\\' && i + 1 < text.size()) {
                json += text[++i];
            } else if (c == '"') {
                in_string = false;
            }
            continue;
        }
        if (c == '"') {
            in_string = true;
            json += c;
            continue;
        }
        bool replaced = false;
        for (const std::string_view literal : {"NaN", "Infinity", "-Infinity"}) {
            if (text.compare(i, literal.size(), literal) == 0) {
                json += "null";
                i += literal.size() - 1;
                replaced = true;
                break;
            }
        }
        if (!replaced) {
            json += c;
        }
    }
    return nlohmann::json::parse(json);
}

std::string require_schema(const nlohmann::json& document, const char* expected, const char* what)
{
    std::string schema = document.at("schema").get<std::string>();
    if (schema != expected) {
        throw std::runtime_error(std::string(what) + ": schema is '" + schema
                                 + "', these tests were written against '" + expected + "'");
    }
    return schema;
}

OptionType read_option_type(const nlohmann::json& row, const char* what)
{
    const std::string type = row.at("type").get<std::string>();
    if (type != "call" && type != "put") {
        throw std::runtime_error(std::string(what) + ": unknown option type '" + type + "'");
    }
    return (type == "call") ? OptionType::Call : OptionType::Put;
}

std::string describe_inputs(OptionType type,
                            double strike,
                            const BlackScholesMarket& market,
                            int expiry_days)
{
    std::ostringstream out;
    out << std::setprecision(17);
    out << (type == OptionType::Call ? "call" : "put") << " S=" << market.spot << " K=" << strike
        << " vol=" << market.vol << " r=" << market.rate << " q=" << market.dividend_yield
        << " days=" << expiry_days;
    return out.str();
}

}  // namespace touchstone::testing
