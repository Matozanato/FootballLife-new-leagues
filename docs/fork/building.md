# Building

How to go from a checkout to the release zip people download: the DLLs, the module pack,
the frozen program, the version number, and the updater.

## What you need

- Windows, Python 3.11 or newer, and Git for Windows (its `sh` runs the build scripts).
- `pip install PySide6 Pillow capstone markdown pyinstaller`.
  - `markdown` turns the guides into HTML.
  - `pyinstaller` freezes the program.
  - `py7zr` is optional (7z kit and face packs), but install it before a release: mszip
    names it as a hidden import, and a frozen program without it cannot open `.7z` files.
- **zig 0.16.0** for the DLLs. Download it for Windows x86_64 from ziglang.org and unpack it
  anywhere. It needs no Visual Studio and no SDK.

## The DLLs: zig and `build-*.sh`

Each DLL has a one-line build script in `tools/native/`:

| script | source | output |
|---|---|---|
| `build-join.sh` | `fl26join.c` | `fl26join.dll` |
| `build-chain.sh` | `fl26chain.c` | `fl26chain.dll` |
| `build-clubs.sh` | `fl26clubs.c` | `fl26clubs.dll` |
| `build-swiss.sh` | `fl26swiss.c` (after `python tools/mkswiss.py` writes `fl26swiss_table.h`) | `fl26swiss.dll` |
| `build-regen.sh` | `fl26regen.c` | `fl26regen.dll` |
| `build-edit.sh` | `fl26edit.c` | `fl26edit.dll` |

Each script runs `$ZIG cc -shared -target x86_64-windows-gnu -O2 -s -o <out> <source>.c
-lkernel32`. `ZIG` is the path to `zig.exe`, or plain `zig` when it is on `PATH`. The first
argument is the output path. Without one, the DLL lands next to the source.

```sh
ZIG=/c/tools/zig-x86_64-windows-0.16.0/zig.exe sh tools/native/build-join.sh out/fl26join.dll
```

- **Other compilers.** Any compiler for x86-64 Windows that understands GCC-style inline
  assembly (`__attribute__((naked))`, AT&T syntax) works: clang does. MSVC does not, because
  it has no inline assembly on x86-64.
- **The older patch set.** The constants that depend on the patch set are `#ifndef` blocks.
  To build for the older `-fixtures` set, add
  `-DREG_ARRAY_OFF=0x1c84230` (fl26join, fl26chain) and the `TODAY_OFF` of that set (fl26join,
  fl26swiss) to the `zig cc` line ([modules.md](modules.md)).
- **How `lbpack.py` finds zig.** It looks at `$ZIG` first, then a
  `tools/zig-x86_64-windows-0.16.0/zig.exe` in the folder that holds the repository, then
  `zig` on `PATH`. It builds all six DLLs into the pack and removes the `.lib` / `.pdb` files
  zig leaves.

Do not commit the `.dll` / `.lib` files that a build leaves in `tools/native/`. They are build
output.

## Deterministic builds and checksums

The same source built with the same zig gives the same code, but the files are **not**
byte-identical. Two builds of `fl26join.c` a second apart differ in nine bytes: the PE
header's time stamp (4), the `.buildid` section (4) and one byte in `.rdata`. `.text`, the
code, is the same. zig 0.16 has no switch that turns this off (`-Wl,/Brepro` is ignored,
`-Wl,--no-insert-timestamp` is refused). So:

- A SHA-256 says which file a person has. It does not prove which source a file came from.
  Publish the checksums of the DLLs you ship (`tools/native/README.md` has a table for that,
  and GitHub shows a sha256 for every release asset).
- To check a shipped DLL against its source, build it yourself and compare with
  `cmp -l a.dll b.dll`. Only those nine bytes may differ.

Pin the zig version, here 0.16.0. Another version gives different code.

## The module pack: `lbpack.py`

```
python tools/lbpack.py out/lbpack
```

This writes `out/lbpack/modules/` (the Lua modules, the two bundles and the six DLLs),
`modules.txt` (load order), `retired.txt` and, if there is one, the regen face pack. A checkout
run of Mod Studio finds the pack in `out/lbpack` (`leaguebuilder.pack_dir`). See
[modules.md](modules.md) for what is in it.

**The regen face pack** is `fl26regen_faces.bin` plus a content root `FL26 Regen Faces`.
It holds renders made from game faces, so it is never in a repository. lbpack takes it from
`$FL26_REGEN_FACES`, else from `../fl26-modding-research/out/regenfaces` beside the
repository. Without it the pack is still built, and the log says
`NO regen face pack -- regens will keep the generic face`. A fork that wants regen faces makes
its own face pack and points `FL26_REGEN_FACES` at it.

**The sources.** When the repository is a checkout of the public repository (its `origin`
contains `FootballLife-new-leagues`), the Lua comes from it. Otherwise a `../fl26-public`
beside it wins if it has a `sider/` folder. A fork with another repository name and no
`fl26-public` beside it simply uses its own `sider/`. If you keep a second checkout beside
yours, change `is_public()` / `PUBLIC` so an old copy can never win. That happened once:
GitHub #69.

## The release: `mszip.py`

```
python tools/mszip.py            # freeze + pack + guides + zip
python tools/mszip.py --no-exe   # reuse the last frozen program (out/msexe/dist)
```

1. **Stage.** `tools/` is copied to `out/msexe/src` without any `sys.path.insert(0, r"<drive>:\...")`
   lines.
2. **Freeze.** PyInstaller `--onedir --windowed` (a folder, not one file: a one-file exe
   unpacks about 150 MB on every start and antivirus scans all of it), `--contents-directory
   _internal`, the icon, `lang/`, `modstudio/lang` and `modstudio/assets` as data.
   - The builder's modules are imported by name at run time, so each one is listed in
     `HIDDEN`, along with every `modstudio` module.
   - **A new `tools/*.py` that Build imports must be added to `HIDDEN`**, or the frozen
     program fails where the checkout works.
3. **Pack.** `lbpack.build(out/mszip/pack)`.
4. **Guides.** `docs/mod-studio-guide.md` -> `README.html`, and the `hr`, `es`, `fr` copies
   -> `README.<code>.html` (the `markdown` package).
5. **Check.** Every staged source inside the exe, the guides and `pack/modules.txt` is
   searched for drive paths and user names (`PRIVATE`). Any match stops the release.
6. **Zip.** `out/FL26ModStudio-<VERSION>.zip`, with everything inside a folder called
   `FL26 Mod Studio`.

**When mszip runs outside a checkout that has the face pack beside it** (a clean worktree, a
temporary folder), set `FL26_REGEN_FACES` first. Otherwise the zip goes out without regen
faces.

## The version

`VERSION` in `tools/modstudio/__init__.py` (a string like `"0.2.0"`). It names the zip, it is
shown in the window, and the updater compares it with the newest release. Change it before
`mszip.py`, in the same commit as the changelog.

## Pointing the updater at your releases

`tools/modstudio/updater.py`:

- **`REPO`.** It is `"Matozanato/FootballLife-new-leagues"`. Change it to your
  `owner/repository`, or your users get our updates and never yours.
- **Releases.** It reads `https://api.github.com/repos/<REPO>/releases` and takes the
  releases tagged `modstudio-<version>` (`TAG`). Any other tag is ignored. Drafts and
  pre-releases are skipped, and it picks the first `.zip` asset of the newest release.
- **Download check.** It checks the download against the sha256 GitHub publishes for the
  asset (the `digest` field). A wrong file is never installed.
- **Install.** It unpacks the zip next to the program and swaps in the `FL26 Mod Studio`
  folder (`FOLDER`). If you rename the folder in `mszip.py`, rename it in `updater.py` too.
- **Release notes.** The release notes become the "what changed" text of the update banner.
  Someone who skipped versions gets the notes of every newer one, newest first.

So a release of a fork is: bump `VERSION`, run `mszip.py`, create a GitHub release tagged
`modstudio-<VERSION>` in the repository `REPO` names, and attach the zip.

If your fork should keep its own settings next to an installed Mod Studio, change the
`FL26ModStudio` folder name under `%APPDATA%`: `APPDIR` in `app.py` (settings, and through
it the tables and recipe copies of `project.py`) and `CACHE` in `newlife.py` (the NewLife
cache).
