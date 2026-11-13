// The library, bound for JavaScript.
//
// Everything here is translation: plain JavaScript objects in, the library's
// value types across, plain JavaScript objects and `Float64Array`s back. No
// arithmetic is done on the way through. A number the tutorial shows is a number
// the library computed, which is the point of putting the library in the browser
// at all.
//
// The names and shapes are the tutorial's `PricingBackend` interface where it
// has one — camelCase fields, `'call'` and `'put'`, partial settings filled from
// the library's defaults — so that the site's backend is a thin wrapper around
// this module rather than a second translation. Beyond that interface: the Monte
// Carlo, the grid with its whole solution surface, and bump-and-revalue Greeks
// over any of the three pricers, which the demos that are not yet written will
// need and which the site cannot add itself.
//
// ## Errors
//
// The library refuses an input by throwing `std::invalid_argument`, and nothing
// may be thrown out of the module: an exception of either language that unwinds
// WebAssembly frames leaves the module's stack pointer where those frames had
// moved it, and enough refusals in a row exhaust the stack. So every bound
// function catches every C++ exception inside the module and *returns* a
// JavaScript error in its place — a `RangeError` for an input the library
// rejects, which is what the tutorial's TypeScript throws for the same inputs; a
// `TypeError` for an argument of the wrong shape, which the library never sees;
// a plain `Error` for anything else — and `errors.post.js` throws it once the
// call has returned. The functions are registered under `raw_` names and that
// file puts the throwing ones in their place.

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/contract.hpp>
#include <touchstone/detail/grid_solver.hpp>
#include <touchstone/implied_vol.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/paths.hpp>
#include <touchstone/pde.hpp>
#include <touchstone/rng.hpp>

#include <emscripten/bind.h>
#include <emscripten/val.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

using emscripten::val;
using namespace touchstone;

// --- Errors ----------------------------------------------------------------

/// An argument JavaScript passed that is the wrong kind of thing: not an
/// object, a field that is not a number, a name that is not one of the allowed
/// strings. Raised as a `TypeError`.
struct ArgumentError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

/// `compute()`, or, if it throws, the JavaScript error the exception becomes.
///
/// The error is built inside the handler from the exception's own message,
/// without a C++ allocation that could itself throw, and returned: the
/// module's frames are left the ordinary way whatever happened in them.
template <class Compute>
val guarded(Compute&& compute)
{
    const auto error = [](const char* kind, const char* message) {
        return val::global(kind).new_(val::u8string(message));
    };
    try {
        return compute();
    } catch (const ArgumentError& thrown) {
        return error("TypeError", thrown.what());
    } catch (const std::invalid_argument& thrown) {
        return error("RangeError", thrown.what());
    } catch (const std::exception& thrown) {
        return error("Error", thrown.what());
    } catch (...) {
        return error("Error", "a C++ exception that is not a std::exception");
    }
}

// --- Names -----------------------------------------------------------------
//
// Each enumeration's JavaScript names, written once and read in both
// directions.

template <class E>
using NameTable = std::span<const std::pair<E, std::string_view>>;

constexpr std::array option_types{
    std::pair{OptionType::Call, std::string_view{"call"}},
    std::pair{OptionType::Put, std::string_view{"put"}},
};

constexpr std::array schemes{
    std::pair{Scheme::ExactTerminal, std::string_view{"exact"}},
    std::pair{Scheme::EulerMaruyama, std::string_view{"euler"}},
};

/// What `bumpGreeks` revalues with.
enum class Pricer { ClosedForm, CrankNicolson, MonteCarlo };

constexpr std::array pricers{
    std::pair{Pricer::ClosedForm, std::string_view{"closedForm"}},
    std::pair{Pricer::CrankNicolson, std::string_view{"crankNicolson"}},
    std::pair{Pricer::MonteCarlo, std::string_view{"monteCarlo"}},
};

constexpr std::array exercises{
    std::pair{Exercise::European, std::string_view{"european"}},
    std::pair{Exercise::American, std::string_view{"american"}},
};

[[nodiscard]] NameTable<OptionType> names_of(OptionType) { return option_types; }
[[nodiscard]] NameTable<Scheme> names_of(Scheme) { return schemes; }
[[nodiscard]] NameTable<Exercise> names_of(Exercise) { return exercises; }
[[nodiscard]] NameTable<Pricer> names_of(Pricer) { return pricers; }

template <class E>
[[nodiscard]] std::string_view name(E value)
{
    for (const auto& [candidate, text] : names_of(value)) {
        if (candidate == value) {
            return text;
        }
    }
    return {};
}

template <class E>
[[nodiscard]] std::string allowed_names()
{
    std::string list;
    for (const auto& [candidate, text] : names_of(E{})) {
        list += list.empty() ? "'" : ", '";
        list += text;
        list += "'";
    }
    return list;
}

// --- Reading one JavaScript value ------------------------------------------
//
// `path` is the argument's name as the caller would write it — `option.strike`
// — so that a refusal says which field it was.

void read_value(const val& value, const std::string& path, double& out)
{
    if (value.typeOf().as<std::string>() != "number") {
        throw ArgumentError(path + " must be a number");
    }
    out = value.as<double>();
}

void read_value(const val& value, const std::string& path, bool& out)
{
    if (value.typeOf().as<std::string>() != "boolean") {
        throw ArgumentError(path + " must be a boolean");
    }
    out = value.as<bool>();
}

/// An integer in `[0, max]`, exactly: no rounding, no wrapping.
template <class Integer>
void read_integer(const val& value, const std::string& path, Integer& out)
{
    double number{};
    read_value(value, path, number);
    constexpr double max = static_cast<double>(std::numeric_limits<Integer>::max());
    if (!(number >= 0.0 && number <= max && std::floor(number) == number)) {
        throw std::invalid_argument(path + " must be an integer from 0 to "
                                    + std::to_string(std::numeric_limits<Integer>::max()));
    }
    out = static_cast<Integer>(number);
}

void read_value(const val& value, const std::string& path, std::uint32_t& out)
{
    read_integer(value, path, out);
}

void read_value(const val& value, const std::string& path, std::size_t& out)
{
    read_integer(value, path, out);
}

template <class E>
    requires std::is_enum_v<E>
void read_value(const val& value, const std::string& path, E& out)
{
    if (value.typeOf().as<std::string>() == "string") {
        const std::string text = value.as<std::string>();
        for (const auto& [candidate, candidate_name] : names_of(E{})) {
            if (candidate_name == text) {
                out = candidate;
                return;
            }
        }
    }
    throw ArgumentError(path + " must be one of " + allowed_names<E>());
}

[[nodiscard]] val to_js(double value) { return val(value); }
[[nodiscard]] val to_js(bool value) { return val(value); }
[[nodiscard]] val to_js(std::uint32_t value) { return val(static_cast<double>(value)); }
[[nodiscard]] val to_js(std::size_t value) { return val(static_cast<double>(value)); }

template <class E>
    requires std::is_enum_v<E>
[[nodiscard]] val to_js(E value)
{
    return val(std::string(name(value)));
}

[[nodiscard]] val to_js(SafeguardedStatus status) { return val(std::string(to_string(status))); }

[[nodiscard]] val float64_array(std::span<const double> values)
{
    // A copy, not a view: a view into the module's memory is invalidated the
    // next time that memory grows.
    return val::global("Float64Array").new_(emscripten::typed_memory_view(values.size(), values.data()));
}

// --- Reading and writing whole objects -------------------------------------
//
// Each value type's JavaScript fields, written once as a table of names and
// members, and used both to read the type from an object and to write it to
// one.

template <class S, class M>
struct Field {
    const char* name;
    M S::*member;
};

template <class S>
struct Fields;

template <>
struct Fields<EuropeanVanilla> {
    static constexpr auto list = std::tuple{
        Field{"strike", &EuropeanVanilla::strike},
        Field{"expiryYears", &EuropeanVanilla::expiry_years},
        Field{"type", &EuropeanVanilla::type},
    };
};

template <>
struct Fields<BlackScholesMarket> {
    static constexpr auto list = std::tuple{
        Field{"spot", &BlackScholesMarket::spot},
        Field{"vol", &BlackScholesMarket::vol},
        Field{"rate", &BlackScholesMarket::rate},
        Field{"dividendYield", &BlackScholesMarket::dividend_yield},
    };
};

template <>
struct Fields<QuotedMarket> {
    static constexpr auto list = std::tuple{
        Field{"spot", &QuotedMarket::spot},
        Field{"rate", &QuotedMarket::rate},
        Field{"dividendYield", &QuotedMarket::dividend_yield},
    };
};

template <>
struct Fields<PriceAndGreeks> {
    static constexpr auto list = std::tuple{
        Field{"price", &PriceAndGreeks::price},
        Field{"delta", &PriceAndGreeks::delta},
        Field{"gamma", &PriceAndGreeks::gamma},
        Field{"vega", &PriceAndGreeks::vega},
        Field{"theta", &PriceAndGreeks::theta},
        Field{"rho", &PriceAndGreeks::rho},
        Field{"dividendRho", &PriceAndGreeks::dividend_rho},
    };
};

template <>
struct Fields<PathGrid> {
    static constexpr auto list = std::tuple{
        Field{"seed", &PathGrid::seed},
        Field{"horizon", &PathGrid::horizon},
    };
};

template <>
struct Fields<GbmDynamics> {
    static constexpr auto list = std::tuple{
        Field{"spot", &GbmDynamics::spot},
        Field{"drift", &GbmDynamics::drift},
        Field{"vol", &GbmDynamics::vol},
    };
};

template <>
struct Fields<SafeguardedSettings> {
    static constexpr auto list = std::tuple{
        Field{"initialVol", &SafeguardedSettings::initial_vol},
        Field{"minVol", &SafeguardedSettings::min_vol},
        Field{"maxVol", &SafeguardedSettings::max_vol},
        Field{"priceTolerance", &SafeguardedSettings::price_tolerance},
        Field{"volTolerance", &SafeguardedSettings::vol_tolerance},
        Field{"maxIterations", &SafeguardedSettings::max_iterations},
        Field{"trace", &SafeguardedSettings::record_steps},
    };
};

template <>
struct Fields<SafeguardedStep> {
    static constexpr auto list = std::tuple{
        Field{"iteration", &SafeguardedStep::iteration},
        Field{"vol", &SafeguardedStep::vol},
        Field{"price", &SafeguardedStep::price},
        Field{"priceError", &SafeguardedStep::price_error},
    };
};

template <>
struct Fields<SafeguardedResult> {
    static constexpr auto list = std::tuple{
        Field{"vol", &SafeguardedResult::vol},
        Field{"status", &SafeguardedResult::status},
        Field{"converged", &SafeguardedResult::converged},
        Field{"iterations", &SafeguardedResult::iterations},
        Field{"bisections", &SafeguardedResult::bisections},
        Field{"priceResidual", &SafeguardedResult::price_residual},
        Field{"vega", &SafeguardedResult::vega},
    };
};

template <>
struct Fields<MonteCarloSettings> {
    static constexpr auto list = std::tuple{
        Field{"seed", &MonteCarloSettings::seed},
        Field{"paths", &MonteCarloSettings::paths},
        Field{"scheme", &MonteCarloSettings::scheme},
        Field{"steps", &MonteCarloSettings::steps},
        Field{"antithetic", &MonteCarloSettings::antithetic},
    };
};

template <>
struct Fields<MonteCarloResult> {
    static constexpr auto list = std::tuple{
        Field{"price", &MonteCarloResult::price},
        Field{"priceStandardError", &MonteCarloResult::price_standard_error},
        Field{"delta", &MonteCarloResult::delta},
        Field{"deltaStandardError", &MonteCarloResult::delta_standard_error},
        Field{"paths", &MonteCarloResult::paths},
        Field{"samples", &MonteCarloResult::samples},
        Field{"inTheMoney", &MonteCarloResult::in_the_money},
    };
};

template <>
struct Fields<PdeSettings> {
    static constexpr auto list = std::tuple{
        Field{"spaceIntervals", &PdeSettings::space_intervals},
        Field{"timeSteps", &PdeSettings::time_steps},
        Field{"halfWidthSigmas", &PdeSettings::half_width_sigmas},
        Field{"rannacherSteps", &PdeSettings::rannacher_steps},
        Field{"smoothPayoff", &PdeSettings::smooth_payoff},
    };
};

template <>
struct Fields<PdeResult> {
    static constexpr auto list = std::tuple{
        Field{"price", &PdeResult::price},
        Field{"delta", &PdeResult::delta},
        Field{"gamma", &PdeResult::gamma},
        Field{"spaceIntervals", &PdeResult::space_intervals},
        Field{"timeSteps", &PdeResult::time_steps},
        Field{"spotIndex", &PdeResult::spot_index},
        Field{"logSpotStep", &PdeResult::log_spot_step},
        Field{"timeStep", &PdeResult::time_step},
        Field{"lowerLogSpot", &PdeResult::lower_log_spot},
        Field{"upperLogSpot", &PdeResult::upper_log_spot},
        Field{"meshPeclet", &PdeResult::mesh_peclet},
        Field{"resolutionInSigmas", &PdeResult::resolution_in_sigmas},
        Field{"dominanceMargin", &PdeResult::dominance_margin},
    };
};

template <>
struct Fields<BumpSizes> {
    static constexpr auto list = std::tuple{
        Field{"spotRelative", &BumpSizes::spot_relative},
        Field{"spotRelativeForGamma", &BumpSizes::spot_relative_for_gamma},
        Field{"volAbsolute", &BumpSizes::vol_absolute},
        Field{"rateAbsolute", &BumpSizes::rate_absolute},
        Field{"dividendYieldAbsolute", &BumpSizes::dividend_yield_absolute},
        Field{"expiryAbsolute", &BumpSizes::expiry_absolute},
    };
};

/// Whether a field may be left out, and the library's default used for it.
enum class Presence { Required, Optional };

[[nodiscard]] bool is_absent(const val& value) { return value.isUndefined() || value.isNull(); }

/// The object `arguments[name]`, which must be an object unless it is optional
/// and absent.
void require_object(const val& object, const std::string& path, Presence presence)
{
    if (is_absent(object) && presence == Presence::Optional) {
        return;
    }
    if (object.typeOf().as<std::string>() != "object" || object.isNull()) {
        throw ArgumentError(path + " must be an object");
    }
}

/// `S` read from `object`, starting from `S{}`: the library's defaults, which a
/// field left out keeps when `presence` allows it.
template <class S>
[[nodiscard]] S read(const val& object, const std::string& path, Presence presence)
{
    require_object(object, path, presence);
    S out{};
    if (is_absent(object)) {
        return out;
    }
    std::apply(
        [&](const auto&... field) {
            (
                [&] {
                    const val value = object[field.name];
                    const std::string field_path = path + "." + field.name;
                    if (is_absent(value)) {
                        if (presence == Presence::Required) {
                            throw ArgumentError(field_path + " is required");
                        }
                        return;
                    }
                    read_value(value, field_path, out.*(field.member));
                }(),
                ...);
        },
        Fields<S>::list);
    return out;
}

/// `in` as a new JavaScript object.
template <class S>
[[nodiscard]] val write(const S& in)
{
    val out = val::object();
    std::apply([&](const auto&... field) { (out.set(field.name, to_js(in.*(field.member))), ...); },
               Fields<S>::list);
    return out;
}

// --- Contracts --------------------------------------------------------------

/// An option object: the three fields every vanilla has, and the exercise style
/// it asks for — `'european'` when it does not say.
struct OptionArgument {
    EuropeanVanilla fields;
    Exercise exercise{Exercise::European};
};

[[nodiscard]] OptionArgument option_argument(const val& option)
{
    OptionArgument out{read<EuropeanVanilla>(option, "option", Presence::Required)};
    const val exercise = option["exercise"];
    if (!is_absent(exercise)) {
        read_value(exercise, "option.exercise", out.exercise);
    }
    return out;
}

/// A European vanilla. An option object that says it is American is refused
/// rather than read as European, for the reason the library refuses one at
/// compile time: the two are different contracts, and pricing one as the other
/// gives a number for the wrong thing.
[[nodiscard]] EuropeanVanilla european(const val& option)
{
    const OptionArgument argument = option_argument(option);
    if (argument.exercise != Exercise::European) {
        throw ArgumentError(
            "this function prices a European vanilla only; option.exercise is 'american', "
            "which only the finite-difference grid prices");
    }
    return argument.fields;
}

/// `price(contract)` called with the option as the contract its `exercise`
/// field names: the grid's entry points, which take either.
template <class Price>
[[nodiscard]] val with_contract(const val& option, Price&& price)
{
    const OptionArgument argument = option_argument(option);
    if (argument.exercise == Exercise::American) {
        return price(with_exercise<Exercise::American>(argument.fields));
    }
    return price(argument.fields);
}

[[nodiscard]] BlackScholesMarket market(const val& object)
{
    return read<BlackScholesMarket>(object, "market", Presence::Required);
}

[[nodiscard]] QuotedMarket quoted_market(const val& object)
{
    return read<QuotedMarket>(object, "market", Presence::Required);
}

/// A count from JavaScript plus one, refused where the sum does not fit.
[[nodiscard]] std::size_t plus_one(std::size_t count, const std::string& path)
{
    if (count == std::numeric_limits<std::size_t>::max()) {
        throw std::invalid_argument(path + " is too large");
    }
    return count + 1;
}

// --- The tutorial's PricingBackend ------------------------------------------

/// `n` draws from the shared generator: uniforms or normals.
template <auto Draw>
[[nodiscard]] val draws(const val& seed, const val& n)
{
    return guarded([&] {
        std::uint32_t seed_value{};
        std::size_t count{};
        read_value(seed, "seed", seed_value);
        read_value(n, "n", count);
        Xoshiro128SS rng(seed_value);
        std::vector<double> out(count);
        for (double& value : out) {
            value = (rng.*Draw)();
        }
        return float64_array(out);
    });
}

/// The grid a path spec describes, and the number of values on it.
struct PathSpec {
    PathGrid grid;
    std::size_t values{};
};

[[nodiscard]] PathSpec path_spec(const val& spec)
{
    PathSpec out{read<PathGrid>(spec, "spec", Presence::Required), 0};
    std::size_t steps{};
    read_value(spec["steps"], "spec.steps", steps);
    out.values = plus_one(steps, "spec.steps");
    return out;
}

[[nodiscard]] val brownian(const val& spec)
{
    return guarded([&] {
        const PathSpec path = path_spec(spec);
        require_valid(path.grid, path.values);
        std::vector<double> out(path.values);
        brownian_path(path.grid, out);
        return float64_array(out);
    });
}

[[nodiscard]] val gbm(const val& spec)
{
    return guarded([&] {
        const PathSpec path = path_spec(spec);
        const GbmDynamics dynamics = read<GbmDynamics>(spec, "spec", Presence::Required);
        Scheme scheme{};
        read_value(spec["scheme"], "spec.scheme", scheme);
        require_valid(path.grid, dynamics, path.values);
        std::vector<double> out(path.values);
        gbm_path(path.grid, dynamics, scheme, out);
        return float64_array(out);
    });
}

[[nodiscard]] val closed_form(const val& option, const val& market_object)
{
    return guarded([&] { return write(price_and_greeks(european(option), market(market_object))); });
}

/// `{lower, upper}`: the price's range as the volatility runs from zero to
/// infinity.
[[nodiscard]] val bounds_of(const EuropeanVanilla& option, const QuotedMarket& quoted)
{
    val out = val::object();
    out.set("lower", lowest_price(option, quoted));
    out.set("upper", highest_price(option, quoted));
    return out;
}

[[nodiscard]] val bounds(const val& option, const val& market_object)
{
    return guarded([&] { return bounds_of(european(option), quoted_market(market_object)); });
}

[[nodiscard]] val implied(const val& option, const val& market_object, const val& price, const val& settings)
{
    return guarded([&] {
        const EuropeanVanilla contract = european(option);
        const QuotedMarket quoted = quoted_market(market_object);
        double target{};
        read_value(price, "price", target);
        const auto solve = read<SafeguardedSettings>(settings, "settings", Presence::Optional);

        const SafeguardedResult result = implied_vol_safeguarded(contract, quoted, target, solve);
        val out = write(result);
        out.set("bounds", bounds_of(contract, quoted));
        if (solve.record_steps) {
            val trace = val::array();
            for (const SafeguardedStep& step : result.steps) {
                trace.call<void>("push", write(step));
            }
            out.set("trace", trace);
        }
        return out;
    });
}

// --- What D7, D8 and D10 will need ------------------------------------------

[[nodiscard]] val monte(const val& option, const val& market_object, const val& settings)
{
    return guarded([&] {
        return write(monte_carlo(european(option), market(market_object),
                                 read<MonteCarloSettings>(settings, "settings", Presence::Optional)));
    });
}

[[nodiscard]] val grid(const val& option, const val& market_object, const val& settings)
{
    return guarded([&] {
        const BlackScholesMarket state = market(market_object);
        const auto pde = read<PdeSettings>(settings, "settings", Presence::Optional);
        return with_contract(option, [&](const auto& contract) {
            return write(crank_nicolson(contract, state, pde));
        });
    });
}

/// The grid's solution at every node, at expiry and after every `everySteps`
/// time steps back to today — today always included — for a heatmap.
///
/// `values` holds the levels one after another, expiry first, each `x(0)`
/// first: the value at level `l`, node `i` is `values[l * nodes + i]`.
[[nodiscard]] val surface(const val& option, const val& market_object, const val& settings, const val& sampling)
{
    return guarded([&] {
        const BlackScholesMarket state = market(market_object);
        const auto pde = read<PdeSettings>(settings, "settings", Presence::Optional);
        require_object(sampling, "sampling", Presence::Optional);
        std::size_t every = 1;
        if (!is_absent(sampling) && !is_absent(sampling["everySteps"])) {
            read_value(sampling["everySteps"], "sampling.everySteps", every);
        }
        if (every == 0) {
            throw std::invalid_argument("sampling.everySteps must be at least 1");
        }

        return with_contract(option, [&](const auto& contract) {
            detail::GridSolver solver(contract, state, pde);
            const detail::LogSpotGrid& nodes = solver.grid();
            const std::size_t node_count = plus_one(nodes.intervals, "settings.spaceIntervals");

            std::vector<double> log_spots(node_count);
            for (std::size_t i = 0; i < node_count; ++i) {
                log_spots[i] = nodes.x(i);
            }

            std::vector<double> times;
            std::vector<double> values;
            const auto record = [&] {
                times.push_back(solver.time_to_expiry());
                const auto level = solver.values();
                values.insert(values.end(), level.begin(), level.end());
            };
            record();
            while (solver.advance()) {
                if (solver.steps_taken() % every == 0) {
                    record();
                }
            }
            if (solver.steps_taken() % every != 0) {
                record();  // Today, which the stride stepped past.
            }

            val out = val::object();
            out.set("logSpots", float64_array(log_spots));
            out.set("timesToExpiry", float64_array(times));
            out.set("values", float64_array(values));
            out.set("nodes", to_js(node_count));
            out.set("levels", to_js(times.size()));
            out.set("result", write(solver.result()));
            return out;
        });
    });
}

/// Bump-and-revalue Greeks over the pricer `pricer.method` names: the closed
/// form (the default), the grid, or the Monte Carlo, each with its settings.
/// The grid takes an American option; the other two do not.
[[nodiscard]] val bumped(const val& option, const val& market_object, const val& sizes_object, const val& pricer)
{
    return guarded([&] {
        const BlackScholesMarket state = market(market_object);
        const auto sizes = read<BumpSizes>(sizes_object, "sizes", Presence::Optional);
        require_object(pricer, "pricer", Presence::Optional);

        Pricer method = Pricer::ClosedForm;
        const val settings = is_absent(pricer) ? val::undefined() : pricer["settings"];
        if (!is_absent(pricer) && !is_absent(pricer["method"])) {
            read_value(pricer["method"], "pricer.method", method);
        }

        switch (method) {
            case Pricer::ClosedForm:
                return write(bump_greeks(european(option), state, sizes));
            case Pricer::CrankNicolson: {
                const auto pde = read<PdeSettings>(settings, "pricer.settings", Presence::Optional);
                return with_contract(option, [&]<Exercise E>(const Vanilla<E>& contract) {
                    // Bumped as the European contract it shares every field with,
                    // and priced as the one it is.
                    const auto price_on_grid = [&](const EuropeanVanilla& point, const BlackScholesMarket& at) {
                        return crank_nicolson(with_exercise<E>(point), at, pde).price;
                    };
                    return write(bump_greeks(with_exercise<Exercise::European>(contract), state, sizes, price_on_grid));
                });
            }
            case Pricer::MonteCarlo: {
                const auto mc = read<MonteCarloSettings>(settings, "pricer.settings", Presence::Optional);
                // The same seed at every bumped point: common random numbers,
                // without which the difference of two prices is mostly the
                // difference of two samples.
                const auto price_by_paths = [&](const EuropeanVanilla& point, const BlackScholesMarket& at) {
                    return monte_carlo(point, at, mc).price;
                };
                return write(bump_greeks(european(option), state, sizes, price_by_paths));
            }
        }
        throw std::logic_error("a pricer with no case");
    });
}

/// The library's default settings for every entry point that takes them, so
/// that a caller can show them without writing them down a second time.
[[nodiscard]] val defaults()
{
    return guarded([] {
        val out = val::object();
        out.set("impliedVol", write(SafeguardedSettings{}));
        out.set("monteCarlo", write(MonteCarloSettings{}));
        out.set("crankNicolson", write(PdeSettings{}));
        out.set("bumpSizes", write(BumpSizes{}));
        return out;
    });
}

// Trailing arguments may be left out, as the TypeScript's optional parameters
// may: embind chooses an overload by the number of arguments, so each shorter
// form is registered as the longest with `undefined` in the missing places.

[[nodiscard]] val implied_3(const val& o, const val& m, const val& p) { return implied(o, m, p, val::undefined()); }
[[nodiscard]] val monte_2(const val& o, const val& m) { return monte(o, m, val::undefined()); }
[[nodiscard]] val grid_2(const val& o, const val& m) { return grid(o, m, val::undefined()); }
[[nodiscard]] val surface_2(const val& o, const val& m) { return surface(o, m, val::undefined(), val::undefined()); }
[[nodiscard]] val surface_3(const val& o, const val& m, const val& s) { return surface(o, m, s, val::undefined()); }
[[nodiscard]] val bumped_2(const val& o, const val& m) { return bumped(o, m, val::undefined(), val::undefined()); }
[[nodiscard]] val bumped_3(const val& o, const val& m, const val& s) { return bumped(o, m, s, val::undefined()); }

}  // namespace

/// `fn` as `raw_<name>`: the error-returning form, which `errors.post.js`
/// replaces with `<name>`, the error-throwing one.
template <class Fn>
void bind(const std::string& name, Fn fn)
{
    emscripten::function(("raw_" + name).c_str(), fn);
}

EMSCRIPTEN_BINDINGS(touchstone)
{
    emscripten::constant("version", std::string(TOUCHSTONE_VERSION));

    bind("uniforms", &draws<&Xoshiro128SS::next_uniform>);
    bind("normals", &draws<&Xoshiro128SS::next_normal>);
    bind("brownianPath", &brownian);
    bind("gbmPath", &gbm);
    bind("priceAndGreeks", &closed_form);
    bind("noArbitrageBounds", &bounds);
    bind("impliedVol", &implied);
    bind("impliedVol", &implied_3);

    bind("monteCarlo", &monte);
    bind("monteCarlo", &monte_2);
    bind("crankNicolson", &grid);
    bind("crankNicolson", &grid_2);
    bind("crankNicolsonSurface", &surface);
    bind("crankNicolsonSurface", &surface_3);
    bind("crankNicolsonSurface", &surface_2);
    bind("bumpGreeks", &bumped);
    bind("bumpGreeks", &bumped_3);
    bind("bumpGreeks", &bumped_2);

    bind("defaults", &defaults);
}
