// Reading `golden/rng-known-answers.json` — the known answers the browser's
// implementation produced at L0, which this library must reproduce.

#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace touchstone::testing {

/// One seed's worth of known answers.
struct RngVector {
    std::uint32_t seed{};
    std::vector<double> uniforms;
    std::vector<double> normals;
};

struct RngFixture {
    std::string path;
    std::string generator;
    std::string seed_expansion;
    std::string uniform_rule;
    std::string normal_rule;
    std::string spec;
    std::size_t count{};
    std::vector<RngVector> vectors;
};

/// Parsed once, on first use. Throws `std::runtime_error` if the file is
/// missing or malformed, or if any of its five description fields differs from
/// what `docs/rng.md` specifies.
///
/// The description check is the point. This file is not generated here and
/// cannot be regenerated here: `docs/rng.md` section 5 says regenerating it is
/// an amendment rather than maintenance, because it is what the two
/// implementations agree *on*. A fixture swapped for one describing a different
/// generator, a different seed expansion or a different bit layout must
/// therefore stop the tests, not be compared against as though nothing had
/// changed and pass or fail on the numbers alone.
const RngFixture& rng_fixture();

/// The seed a sweep gives its `index`-th row.
///
/// Not `index` itself, and the reason is the seed expansion. `Xoshiro128SS`
/// takes `fmix32(seed + i)` for i in 0..3, so seeds `s` and `s + 1` produce
/// states built from the same four numbers shifted by one position. Those are
/// different states and the generator will not repeat itself, but they are not
/// obviously *unrelated* either, and a sweep whose aggregate statistics assume
/// its rows are independent samples should not have to hope. A large odd stride
/// puts consecutive rows billions apart in seed space, where no such overlap
/// exists at all. `tests/test_rng.cpp` checks that no two seeds a sweep uses
/// come within three of each other, and that streams from them do not
/// correlate.
[[nodiscard]] constexpr std::uint32_t stream_seed(std::size_t index) noexcept
{
    return static_cast<std::uint32_t>(index) * 2654435761u + 1u;
}

}  // namespace touchstone::testing
