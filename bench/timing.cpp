// Times the library's five entry points, each at its default settings, on one
// option in one market, and prints every measurement it takes.
//
//   touchstone_timing [rounds]
//
// The option is a call struck at 100 with a year to run; the market is a spot of
// 100, a volatility of 0.2, a rate of 0.05 and a dividend yield of 0.02.
// `implied_vol` inverts the closed-form price of that option at that volatility.
// `bump_greeks` is the overload over the closed form. Nothing else is set:
// `monte_carlo` runs `MonteCarloSettings{}` and `crank_nicolson` runs
// `PdeSettings{}`.
//
// The fastest of the five takes less time than a clock read resolves, so calls
// are timed in batches: as many calls in a row as take at least
// `batch_target_ms`, timed as a whole and divided by the count. Each entry point
// is calibrated once and warmed up, then a round times `batches_per_round`
// batches of each and keeps their median. The rounds rotate the order of the
// five, so that none always runs straight after the same neighbour. The summary
// is the median over the rounds, with the smallest and largest round beside it.
//
// Every round's median is printed as it is taken, and so is the value each
// entry point returned, so that the output says what was computed as well as
// how long it took. A time from this program describes the machine, compiler
// and flags it was built with and nothing else.

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/implied_vol.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/pde.hpp>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <vector>

namespace {

constexpr double batch_target_ms = 20.0;
constexpr std::size_t batches_per_round = 5;
constexpr std::size_t warm_up_batches = 3;
constexpr std::size_t default_rounds = 25;

/// Read and written after every call, so that no call's result is unused and
/// the compiler cannot drop the call. It costs a load and a store per call, which
/// the times include.
volatile double sink = 0.0;

/// `calls` calls in a row, in milliseconds. A template, so that the loop is
/// compiled around a direct call to the entry point: the only indirection the
/// harness adds is once per batch, in `EntryPoint::batch`.
template <class Call>
[[nodiscard]] double batch_ms(const Call& call, std::size_t calls)
{
    const auto start = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < calls; ++i) {
        sink = sink + call();
    }
    const auto stop = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(stop - start).count();
}

struct EntryPoint {
    const char* name;
    std::function<double()> once;              ///< One call, for the value printed as a check.
    std::function<double(std::size_t)> batch;  ///< `batch_ms` around that call.
    std::size_t calls_per_batch{1};
    std::vector<double> round_ns;  ///< One per round: the median of its batches, per call.
};

template <class Call>
[[nodiscard]] EntryPoint entry_point(const char* name, Call call)
{
    return EntryPoint{name, call, [call](std::size_t calls) { return batch_ms(call, calls); }, 1, {}};
}

[[nodiscard]] double median(std::vector<double> values)
{
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
}

/// Doubles the batch until one takes at least `batch_target_ms`.
void calibrate(EntryPoint& entry)
{
    std::size_t calls = 1;
    while (entry.batch(calls) < batch_target_ms) {
        calls *= 2;
    }
    entry.calls_per_batch = calls;
}

/// The median time of one call, in nanoseconds, over one round's batches.
[[nodiscard]] double time_round(const EntryPoint& entry)
{
    std::vector<double> per_call_ns;
    per_call_ns.reserve(batches_per_round);
    for (std::size_t b = 0; b < batches_per_round; ++b) {
        const double ms = entry.batch(entry.calls_per_batch);
        per_call_ns.push_back(ms * 1e6 / static_cast<double>(entry.calls_per_batch));
    }
    return median(per_call_ns);
}

}  // namespace

int main(int argc, char** argv)
{
    std::size_t rounds = default_rounds;
    if (argc == 2) {
        const long requested = std::atol(argv[1]);
        if (requested < 1) {
            std::fprintf(stderr, "usage: touchstone_timing [rounds >= 1]\n");
            return 2;
        }
        rounds = static_cast<std::size_t>(requested);
    } else if (argc > 2) {
        std::fprintf(stderr, "usage: touchstone_timing [rounds >= 1]\n");
        return 2;
    }

    const touchstone::EuropeanVanilla option{100.0, 1.0, touchstone::OptionType::Call};
    const touchstone::BlackScholesMarket market{100.0, 0.2, 0.05, 0.02};
    const touchstone::QuotedMarket quoted = touchstone::QuotedMarket::of(market);
    const double target = touchstone::price(option, market);

    std::array<EntryPoint, 5> entries{
        entry_point("price_and_greeks",
                    [&] { return touchstone::price_and_greeks(option, market).price; }),
        entry_point("implied_vol",
                    [&] { return touchstone::implied_vol(option, quoted, target).vol; }),
        entry_point("bump_greeks", [&] { return touchstone::bump_greeks(option, market).delta; }),
        entry_point("monte_carlo", [&] { return touchstone::monte_carlo(option, market).price; }),
        entry_point("crank_nicolson",
                    [&] { return touchstone::crank_nicolson(option, market).price; }),
    };

    std::printf("touchstone_timing: %zu rounds of %zu batches, each batch at least %.0f ms\n",
                rounds, batches_per_round, batch_target_ms);
    std::printf("call K=100 T=1; S=100 sigma=0.2 r=0.05 q=0.02; implied_vol target %.17g\n\n",
                target);

    for (EntryPoint& entry : entries) {
        calibrate(entry);
        for (std::size_t w = 0; w < warm_up_batches; ++w) {
            static_cast<void>(entry.batch(entry.calls_per_batch));
        }
        std::printf("%-17s returned %.17g; %zu calls per batch\n", entry.name, entry.once(),
                    entry.calls_per_batch);
    }
    std::printf("\nround entry_point ns_per_call\n");

    for (std::size_t r = 0; r < rounds; ++r) {
        for (std::size_t k = 0; k < entries.size(); ++k) {
            EntryPoint& entry = entries[(r + k) % entries.size()];
            const double ns = time_round(entry);
            entry.round_ns.push_back(ns);
            std::printf("%zu %s %.1f\n", r, entry.name, ns);
        }
    }

    std::printf("\n%-17s %14s %14s %14s\n", "entry point", "median", "min round", "max round");
    for (const EntryPoint& entry : entries) {
        const auto [low, high] = std::minmax_element(entry.round_ns.begin(), entry.round_ns.end());
        std::printf("%-17s %11.1f ns %11.1f ns %11.1f ns\n", entry.name, median(entry.round_ns),
                    *low, *high);
    }
    return 0;
}
