#!/bin/sh
# Build fl26compcache.dll with `zig cc`. Set ZIG to the zig.exe path (or have it on PATH).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIG="${ZIG:-zig}"
OUT="${1:-$HERE/fl26compcache.dll}"
"$ZIG" cc -shared -target x86_64-windows-gnu -O2 -s \
  -o "$OUT" "$HERE/fl26compcache.c" -lkernel32
echo "built: $OUT"
