#!/bin/sh
# Build fl26swiss.dll with `zig cc`. Set ZIG to the zig.exe path (or have it on PATH).
# The draw table is generated first, so the DLL can never drift from tools/mkswiss.py.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIG="${ZIG:-zig}"
OUT="${1:-$HERE/fl26swiss.dll}"
python "$HERE/../mkswiss.py" "$HERE/fl26swiss_table.h"
"$ZIG" cc -shared -target x86_64-windows-gnu -O2 -s \
  -o "$OUT" "$HERE/fl26swiss.c" -lkernel32
echo "built: $OUT"
