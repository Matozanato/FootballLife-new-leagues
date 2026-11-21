#!/bin/sh
# Build fl27playoff.dll with zig for the Mod Studio module pack.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIG="${ZIG:-zig}"
OUT="${1:-$HERE/fl27playoff.dll}"
"$ZIG" cc -shared -target x86_64-windows-gnu -O2 -s \
  -o "$OUT" "$HERE/fl27playoff.c" -lkernel32 -lbcrypt
