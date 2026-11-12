// The one shape both of the library's callable parameters take: a function
// whose result is a number.

#pragma once

#include <concepts>
#include <type_traits>

namespace touchstone::detail {

/// Callable as an lvalue with `Args`, returning something that converts to
/// `double`.
template <class F, class... Args>
concept returns_double =
    std::invocable<F&, Args...> && std::convertible_to<std::invoke_result_t<F&, Args...>, double>;

}  // namespace touchstone::detail
