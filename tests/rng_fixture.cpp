#include "rng_fixture.hpp"

#include <nlohmann/json.hpp>

#include <cstdlib>
#include <fstream>
#include <stdexcept>

#ifndef TOUCHSTONE_RNG_FIXTURE_PATH
#error "TOUCHSTONE_RNG_FIXTURE_PATH must name golden/rng-known-answers.json; the tests CMakeLists defines it."
#endif

namespace touchstone::testing {
namespace {

/// What `docs/rng.md` specifies, field by field, in the fixture's own words.
struct Expected {
    const char* key;
    const char* value;
};

constexpr Expected expected_description[] = {
    {"generator", "xoshiro128**"},
    {"seedExpansion", "fmix32(seed + i), i = 0..3"},
    {"uniform", "((hi >>> 5) * 2^26 + (lo >>> 6)) * 2^-53, hi drawn first"},
    {"normal", "AS241 (Wichura PPND16) inverse CDF of the i-th uniform of the same stream"},
    {"spec", "docs/rng.md"},
};

std::string fixture_path()
{
    if (const char* from_environment = std::getenv("TOUCHSTONE_RNG_FIXTURE_PATH")) {
        return from_environment;
    }
    return TOUCHSTONE_RNG_FIXTURE_PATH;
}

RngFixture load()
{
    RngFixture fixture{};
    fixture.path = fixture_path();

    std::ifstream stream(fixture.path);
    if (!stream) {
        throw std::runtime_error("rng fixture: cannot open '" + fixture.path + "'");
    }

    const nlohmann::json document = nlohmann::json::parse(stream);

    for (const Expected& field : expected_description) {
        const std::string found = document.at(field.key).get<std::string>();
        if (found != field.value) {
            throw std::runtime_error("rng fixture: '" + std::string(field.key) + "' is \"" + found
                                     + "\", these tests were written against \""
                                     + std::string(field.value)
                                     + "\" — the fixture describes a different generator than "
                                       "docs/rng.md specifies");
        }
    }

    fixture.generator = document.at("generator").get<std::string>();
    fixture.seed_expansion = document.at("seedExpansion").get<std::string>();
    fixture.uniform_rule = document.at("uniform").get<std::string>();
    fixture.normal_rule = document.at("normal").get<std::string>();
    fixture.spec = document.at("spec").get<std::string>();
    fixture.count = document.at("count").get<std::size_t>();

    for (const auto& entry : document.at("vectors")) {
        RngVector vector{};
        vector.seed = entry.at("seed").get<std::uint32_t>();
        vector.uniforms = entry.at("uniforms").get<std::vector<double>>();
        vector.normals = entry.at("normals").get<std::vector<double>>();

        if (vector.uniforms.size() != fixture.count || vector.normals.size() != fixture.count) {
            throw std::runtime_error("rng fixture: seed " + std::to_string(vector.seed)
                                     + " does not carry the declared count of values");
        }
        fixture.vectors.push_back(std::move(vector));
    }

    if (fixture.vectors.empty()) {
        throw std::runtime_error("rng fixture: no vectors");
    }
    return fixture;
}

}  // namespace

const RngFixture& rng_fixture()
{
    static const RngFixture fixture = load();
    return fixture;
}

}  // namespace touchstone::testing
