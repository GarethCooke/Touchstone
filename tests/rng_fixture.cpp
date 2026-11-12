#include "rng_fixture.hpp"

#include "json_file.hpp"

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
    std::string RngFixture::* field;
};

const Expected expected_description[] = {
    {"generator", "xoshiro128**", &RngFixture::generator},
    {"seedExpansion", "fmix32(seed + i), i = 0..3", &RngFixture::seed_expansion},
    {"uniform", "((hi >>> 5) * 2^26 + (lo >>> 6)) * 2^-53, hi drawn first", &RngFixture::uniform_rule},
    {"normal", "AS241 (Wichura PPND16) inverse CDF of the i-th uniform of the same stream",
     &RngFixture::normal_rule},
    {"spec", "docs/rng.md", &RngFixture::spec},
};

RngFixture load()
{
    RngFixture fixture{};
    fixture.path = fixture_path("TOUCHSTONE_RNG_FIXTURE_PATH", TOUCHSTONE_RNG_FIXTURE_PATH);

    const nlohmann::json document = read_json(fixture.path, "rng fixture");

    for (const Expected& field : expected_description) {
        const std::string found = document.at(field.key).get<std::string>();
        if (found != field.value) {
            throw std::runtime_error("rng fixture: '" + std::string(field.key) + "' is \"" + found
                                     + "\", these tests were written against \""
                                     + std::string(field.value)
                                     + "\" — the fixture describes a different generator than "
                                       "docs/rng.md specifies");
        }
        fixture.*(field.field) = found;
    }

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
