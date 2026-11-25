#!/bin/sh
# Build fl26cwc.dll (the Club World Cup ranking, ../cwcrank/fl26cwc.c) with `zig cc`.
# Set ZIG to the zig.exe path (or have it on PATH).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIG="${ZIG:-zig}"
OUT="${1:-$HERE/fl26cwc.dll}"
"$ZIG" cc -shared -target x86_64-windows-gnu -O2 -s \
  -o "$OUT" "$HERE/../cwcrank/fl26cwc.c" -lkernel32
echo "built: $OUT"
