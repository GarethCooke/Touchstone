# Vendored third-party headers

Two single headers, used by the test executable only. Neither is reachable from
`include/touchstone/`: the library links nothing, and the WASM artifact at T4
will link nothing.

They are committed rather than fetched at configure time so that a build is
reproducible offline and byte-pinned — the constitution forbids submodules
(I17), and a `FetchContent` pull would put the network on the critical path of
every CI run.

| File | Project | Version | Licence | SHA-256 |
|---|---|---|---|---|
| `doctest/doctest.h` | [doctest](https://github.com/doctest/doctest) | v2.4.12 | MIT | `94029a7d32da24a56249658147dbd2b33ff0b9ed665295cbbaf19aafff5b0ced` |
| `nlohmann/json.hpp` | [nlohmann/json](https://github.com/nlohmann/json) | v3.12.0 | MIT | `aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63` |

Fetched from:

```
https://raw.githubusercontent.com/doctest/doctest/v2.4.12/doctest/doctest.h
https://raw.githubusercontent.com/nlohmann/json/v3.12.0/single_include/nlohmann/json.hpp
```

Verify with `sha256sum doctest/doctest.h nlohmann/json.hpp`.

**Why these two.** doctest follows Anvil and DepthCharge, which is what
tech-decision B1 asks for ("whatever Anvil uses, for consistency"). nlohmann/json
reads `golden/bs_vanilla.json` as written, so `golden/SCHEMA.md` stays the
contract and the tolerances are read from the file rather than restated in the
tests. Both are MIT, single-header, and confined to the test target.
