# Experimental FL27 special-title sorter

The optional DLL accelerates the ranking call at `0x140fd457a` on the
supported FL27 executable. The call at `0x140fd4626` and the original
sorter and RNG entry points remain native. The DLL is disabled by
default and can be used independently of the other performance modules.

## Build and enable

Build with a Windows x64 GNU toolchain using
`sh tools/native/build-candidate.sh /path/to/fl26candidate.dll`.
The script uses Zig and accepts a `ZIG` executable override.

To opt in on an isolated installation, copy the DLL and
`sider/experimental/fl26candidate.lua` into the Sider modules directory,
enable LuaJIT FFI, add `lua.module = "fl26candidate.lua"` to its Sider
configuration, and set `FL27_CANDIDATE_SORT=blocked` in the game process
environment. Restart the game when changing the mode.

At Sider startup the installer validates the mapped image, call-site
signature, native sorter and RNG before changing the site's relative
call target. On a mismatch it makes no redirect. The replacement uses
invocation-local scratch space. It keeps the original path for fewer
than 64 records, unsupported layouts or ranges, and allocation failure.
Fallback is decided before record mutation or RNG consumption. The DLL
logs startup status through the loader and has no per-call diagnostics.

The sort skips a block only when its minimum score is strictly greater
than the current winner's score. It preserves the left-to-right order
of potential winners and ties, including all native tie draws. Each swap
moves the first 14 bytes of the 16-byte record. The last two bytes stay
in their original slots. With many ties, worst-case work stays quadratic.

## Evidence

One isolated GigaPack comparison from the Arsenal August 21, 2026
checkpoint measured the instrumented prototype on site 1:

| Mode | Candidate count | Sorter time |
| --- | ---: | ---: |
| Native | 102,246 | 7.075 s |
| Block minimum | 102,245 | 2.765 s |

This was a **60.9% reduction in sorter time** (2.56x). The two reloads
differed by one candidate. No end-to-end calendar speedup was measured.
The earlier two-site release-shaped build initialized and completed the
same advance. This is prior live evidence for the shared sorting path.
The final site-1-only installer has been verified in a mapped image.

Run the offline tests from PowerShell with a local, supported executable:

```powershell
./tools/native/test-candidate-sort.ps1 -GameExecutable 'C:\isolated\FL_2027.exe' -OutputDirectory 'C:\scratch\fl27-candidate-test'
```

The tests cover 4,000 deterministic cases, native parity on small and
102,245-record vectors, ordinary and null-state RNG branches, fallback,
and byte-for-byte preservation of site 2. The null-state test uses
a deterministic substitute for the platform RNG import. The game is
not launched by the test.

The exact site-1-only DLL initialized with `mode=blocked status=0` in
the isolated GigaPack clone and completed the verified Arsenal
August 21–27, 2026 advance. The slot 1 hash stayed unchanged. The release
build has no per-call counters, so this is a live compatibility check.
The original comparison supplies the sorter timing. No new timing was
taken. Site 2 remains native.
