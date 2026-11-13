// A row's inputs, as both golden files write them: the contract, the market,
// and the expiry in days the expiry in years was computed from.

#pragma once

#include <touchstone/black_scholes.hpp>
#include <touchstone/contract.hpp>

namespace touchstone::testing {

template <Exercise E>
struct RowInputs {
    Vanilla<E> option{};
    BlackScholesMarket market{};
    int expiry_days{};
};

}  // namespace touchstone::testing
