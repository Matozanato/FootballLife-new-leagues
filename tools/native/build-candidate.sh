#!/bin/sh
# Build the source-only FL27 candidate sorter with Zig.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
zig="${ZIG:-zig}"
out="${1:?usage: build-candidate.sh <output DLL>}"
"$zig" cc -shared -target x86_64-windows-gnu -O2 -Wall -Wextra -Werror \
  -o "$out" "$here/fl26candidate.c" -lkernel32
