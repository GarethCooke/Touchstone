#!/usr/bin/env bash
# Build the WebAssembly artifact with exception catching on, as it ships, and
# off, to measure what catching costs; write the sizes of both to
# build-wasm/size.txt; fail if the shipped one is over budget.
#
# Needs Emscripten's environment: `source <emsdk>/emsdk_env.sh` first. The
# generator is CMake's default, or $CMAKE_GENERATOR if set — passed as -G,
# because emcmake on Windows otherwise names one of its own.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
budget=500000  # Bytes, .wasm and .mjs together, uncompressed: 500 KB at 1000 bytes to the KB.

build() {
    emcmake cmake ${CMAKE_GENERATOR:+-G "$CMAKE_GENERATOR"} -S "$root" -B "$root/$1" \
        -DCMAKE_BUILD_TYPE=Release -DTOUCHSTONE_WASM_EXCEPTIONS="$2"
    cmake --build "$root/$1"
}

build build-wasm ON
build build-wasm-noexcept OFF

bytes() { wc -c < "$1" | tr -d ' '; }
gzipped() { gzip -9 -c "$1" | wc -c | tr -d ' '; }

row() {
    local label=$1 dir=$root/$2/wasm
    local wasm mjs
    wasm=$(bytes "$dir/touchstone.wasm")
    mjs=$(bytes "$dir/touchstone.mjs")
    printf '%-26s %9d %9d %9d %13d\n' "$label" "$wasm" "$mjs" $((wasm + mjs)) \
        $(($(gzipped "$dir/touchstone.wasm") + $(gzipped "$dir/touchstone.mjs")))
}

shipped=$(( $(bytes "$root/build-wasm/wasm/touchstone.wasm") + $(bytes "$root/build-wasm/wasm/touchstone.mjs") ))

{
    printf '%s, -O3; bytes\n\n' "$(emcc --version | head -n 1)"
    printf '%-26s %9s %9s %9s %13s\n' "" ".wasm" ".mjs" "total" "gzip -9 total"
    row "catching on (shipped)" build-wasm
    row "catching off" build-wasm-noexcept
    printf '\n%-26s %9s %9s %9d\n' "budget" "" "" "$budget"
} | tee "$root/build-wasm/size.txt"

if (( shipped > budget )); then
    echo "The artifact is $shipped bytes, over the $budget-byte budget." >&2
    exit 1
fi
