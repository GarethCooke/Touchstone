// Appended inside the module factory by --post-js, after the runtime has started
// and before the factory returns the module.
//
// Nothing may be thrown through WebAssembly frames — not a C++ exception and not
// a JavaScript one — because an exception that unwinds them leaves the module's
// stack pointer where they had moved it, and enough of them exhaust the stack
// (see the note at the top of `binding.cpp`). Two things keep every throw out:
//
//   - Every function `binding.cpp` registers comes in as `raw_<name>` and
//     *returns* a JavaScript error rather than throwing one. Here each is given
//     a `<name>` that makes the call, lets the module's frames return normally,
//     and then throws the error if that is what came back. No result the module
//     returns is an `Error` except a refusal, so the test is unambiguous.
//
//   - The arguments are handed over as a structured clone: plain data, every
//     getter already run and every proxy already read, here, in JavaScript. An
//     object whose getter throws then throws before the module is entered,
//     rather than from a property read inside it. The clone keeps NaN and the
//     infinities, which the library must see in order to refuse them.
//
// The `raw_` functions stay on the module, hidden from enumeration rather than
// deleted: embind's dispatch between overloads of different arity looks the
// function up on the module by its registered name at every call.
for (const key of Object.keys(Module)) {
  if (!key.startsWith('raw_')) continue
  const raw = Module[key]
  const name = key.slice('raw_'.length)
  const throwing = function (...args) {
    const result = raw(...structuredClone(args))
    if (result instanceof Error) throw result
    return result
  }
  Object.defineProperty(throwing, 'name', { value: name })
  Module[name] = throwing
  Object.defineProperty(Module, key, { enumerable: false })
}
