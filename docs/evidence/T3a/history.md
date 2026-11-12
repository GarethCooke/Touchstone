# T3a — history removed from comments, kept for `ARCHITECTURE.md`

Ruling 8 (`docs/briefs/T3a-design-rulings.md`) moves the milestone, review and governance
history in `include/` and `src/` to `ARCHITECTURE.md` at T5, and the standing rules say new and
changed comments name no milestone, tollgate, review or governance id. Where T3a had to change a
comment that carried such history, the history is recorded here verbatim, with where it was, so
that T5 has it to move. Comments T3a did not change still carry theirs; T5's grep finds those.

| Was in | Text removed | Why the comment changed |
|---|---|---|
| `include/touchstone/scales.hpp` (now `detail/scales.hpp`), file comment | "T2's review found exactly that gap and left it for T3; the file below is the repair, and `tests/test_associations.cpp` is what holds it shut." | The file moved under `detail/` (ruling 5) and gained the quantities R3 names. The sentence now reads "`tests/test_associations.cpp` is what holds the check and the formulas together." |
| same file, same comment | "**Three methods must agree (I20).**" — the governance id | As above. |
| `src/black_scholes.cpp`, `require_valid` | "T1 checked their sum instead — `(r - q + 0.5 sigma^2) T` — and that is a different domain, by more than an ulp." and "T1 accepted it and returned a NaN price for it, which is the one outcome this function exists to rule out." | The check moved into the volatility's half of the closed-form evaluation (ruling 6). The numerical reasoning stays, as "Checking their sum instead … is a different domain". |
| `src/monte_carlo.cpp`, `Accumulator::add` | "which is the failure mode T1 ruled out for the closed form" | Now "the failure mode the closed form rules out too". |
| `src/monte_carlo.cpp`, `monte_carlo` | "Rejected rather than returned, for T1's reason:" | Now "Rejected rather than returned:". |
| `src/monte_carlo.cpp`, `total_volatility(const BlackScholesMarket&, double)` | "T3 moved the expression itself into `scales.hpp`; this signature stays because the callers below read better with it." | The function is gone (F2); its callers use `detail::total_variance` and the path generator. |
| `include/touchstone/monte_carlo.hpp`, `Scheme::EulerMaruyama` | "…and claims need tests (I1)." — the governance id | `Scheme` moved to `paths.hpp` and its rationale to `MonteCarloSettings::scheme`. |
| `include/touchstone/pde.hpp`, `Exercise::American` | "v1 has no closed form for this and QuantLib is the oracle for it" | `Exercise` moved to `contract.hpp` (ruling 4); now "There is no closed form for this". |
| `CMakeLists.txt`, header self-containment | "which at T4 is the Emscripten binding" | The check now covers `detail/` too; now "which is the WebAssembly binding". |
