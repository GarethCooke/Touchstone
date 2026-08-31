// Reading `golden/american_vanilla.json`.
//
// A separate reader from `golden_file.hpp` rather than a parameter on it,
// because the two files answer different questions and carry different
// guarantees. `bs_vanilla.json` is a closed form evaluated to fifteen digits and
// compared at a fixed tolerance. This one is three lattices asked the same
// question, and what it carries is a value **and the amount they disagreed by**,
// per row. A test that compared against it at a fixed tolerance would either be
// asserting the lattices are better than they are, or letting the easy rows
// through on the hard rows' allowance.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cstddef>
#include <string>
#include <vector>

namespace touchstone::testing {

/// One row: the inputs, the lattice's answer, and its uncertainty about it.
struct AmericanCase {
    EuropeanVanilla option{};
    BlackScholesMarket market{};
    int expiry_days{};

    double price{};
    double delta{};
    double gamma{};

    /// The largest disagreement among Leisen-Reimer, Cox-Ross-Rubinstein and
    /// Tian at this row's inputs. Zero where all three agree exactly, which
    /// happens wherever immediate exercise is optimal at the spot and every tree
    /// returns the intrinsic value.
    double spread{};
    double delta_spread{};
    double gamma_spread{};

    /// American exercise is worth no more than European exercise here, exactly,
    /// and the reason is one of two theorems rather than a numerical accident.
    ///
    ///   - A **call** with no dividend yield and a non-negative rate: exercising
    ///     early pays `K` now instead of `K e^{-rT}` later and gains nothing for
    ///     it.
    ///   - A **put** with a non-positive rate and a non-negative yield: the
    ///     mirror image.
    ///
    /// Where this is true the row can be checked against the closed form's
    /// fifteen digits rather than against another lattice's four, which is the
    /// strongest statement available about an American price.
    [[nodiscard]] bool equals_european() const noexcept;
};

struct AmericanFile {
    std::string path;
    std::string schema;
    std::string oracle_version;
    std::string engine;
    double worst_spread{};
    std::size_t declared_cases{};
    std::vector<AmericanCase> cases;
};

/// Parsed once, on first use. Throws `std::runtime_error` if the file is
/// missing, malformed, or carries a different schema id.
const AmericanFile& american_file();

/// The row's inputs on one line, at full precision.
[[nodiscard]] std::string describe(const AmericanCase& row);

}  // namespace touchstone::testing
