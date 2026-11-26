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

**The regen face pack** is `fl26regen_faces.bin` plus a content root `FL26 Regen Faces`: the
face pool below. lbpack builds it from the repository (`tools/facepool.py`,
`tools/facepool_stats.json`) into every pack, checks it against `facepool.POOL_MD5` and logs
`pack: face pool built from tools/facepool.py: 32760 faces, md5 ...`. `$FL26_REGEN_FACES` is only
for the pool with portraits (`facemini.py pack`): a pack there that is not the pool -- the 30.09.
pack of 103 game faces (`FL26RF01`), a pool of fewer than 20,000 faces, an older map, other faces
-- stops the build (`facepool.pool_problems`). Until 17.11.2026 lbpack took the pack from
`fl26-modding-research/out/regenfaces`, which still held the 30.09. pack, and every release
candidate shipped that one instead of the pool.

**The face pool** is a face pack of our own: `python tools/facepool.py build` writes
`out/facepool/fl26regen_faces.bin` (version 2) and an empty `FL26 Regen Faces` root. Its 32,760
faces are made from numbers -- every slider, type, hair style and colour drawn from how often the
game's players of that part of the world have it (`tools/facepool_stats.json`, made once by
`facepool.py stats` from the game's PlayerAppearance.bin and Player.bin) -- so no face is a real
player's and there are no renders in it. They have no portraits. `python tools/facepool.py check
<pack>` says whether a pack is the pool.
The pool is made in blocks (`BLOCKS`): the first 20,000 faces (06.11.) stay the same bytes in the
same place when a block is added, the second block's 12,000 went to the groups with the most new
players per face (the Megapack's Africa, Eastern Europe, north-west Europe, Latin America ...).
**The groups** (`tools/facegroups.py`): nweu seu eeu afr mena lat bra eas sas nord sea. On 17.11.
South-East Asia and Polynesia left sas for the new group sea, Pakistan moved to sas, Melanesia
to afr, Kazakhstan and Kyrgyzstan to eas, Uzbekistan, Tajikistan and Turkmenistan to mena, Belize
to lat (`facegroups.REGIONS_1711`). `facepool.py regroup <PlayerAppearance.bin> <tables>` counts
sas and sea again with that map (`REDRAWN`) and leaves every other group's counts, so their faces
stay byte for byte: a player of a nation that kept its group keeps his face. sas (590) and sea
(1,570) share the room the DLL has left (32,767).
`python tools/facepool.py near <PlayerAppearance.bin>...` (numpy, about 3 minutes) measures how
many of the 77 face fields each face is from the nearest real face of the game's files and from
the nearest pool face; a face of block 2 nearer than `MIN_APART` (28) to a real one is a draw for
`SKIP`, which keeps the pack the same without the game's files; two faces of block 1 that were
25 fields from a real one are made again in place (`REPLACE`). Each face's second byte in the
pack is its block, so fl26regen keeps a career's faces when the pool grows: a player keeps his
face of block 1 with the share block 1 has of his group (nweu 71%, eeu 34%, afr 38% ...; all of a
group that did not grow), the others get one of the added faces.

**The face pool's portraits** come from the game's own render of each face: fl26regen's capture
mode (only when `modules\fl26regen_capture.txt` is there at the start; `player <id> face <k>` in
it draws that player with pool face k, the DLL answers in `fl26regen_capture.ack`) shows face k
on Edit's player screen, a screenshot is taken per face (`mini_<k>.png`), and
`python tools/facemini.py convert <shots> <out>` cuts the head off the red menu into the game's
portrait format (128 x 128 DXT5, the header of the game's own portraits, transparent around the
player, the shirt grey) as `<out>/FL26 Regen Faces/common/render/symbol/player/regen/<k>.dds`.
`python tools/facemini.py pack <pool fl26regen_faces.bin> <out>` gives every face with a picture
its portrait number k; `FL26_REGEN_FACES=<out>` then builds the module pack with both (only
when its faces are the pool's). Never ship the capture file.

Until the whole pool is captured, the pictures are shared (18.11.2026): `python tools/facemini.py
rank <list.txt> --n 1000` orders the faces to capture, best first (the first ~100 cover every
group and the common looks, the later ones the rarer looks), and `python tools/facecap.py run
--faces <list.txt> ...` captures them in that order and can stop anywhere (it resumes from
`progress.tsv`). `python tools/facemini.py share <out>` then gives every face the portrait number
of the captured face that looks most like it -- the same group, then the skin, the hair's colour,
length and shape, the beard, the age (`facemini.distance`); a captured face keeps its own, a face
whose group has no picture yet takes another group's only when it looks close, else none -- and
writes `<out>/fl26regen_faces.bin` and `<out>/share.tsv`. Run it again after every capture. The
DLL never checks a portrait number (it is only the name of `regen\<number>.dds`), so any number
of faces can share one; lbpack and mszip stop a pack with a number that has no 128 x 128 DXT5
`.dds` (`facepool.portrait_problems`).

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
python tools/mszip.py --untested --no-faces   # a fork's build: no game to compare with, no face pack
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
   **Pack check** (`check_pack`, since 0.2.1; 0.2.0 went out with an old `fl26caps.lua`): the
   release stops when a module holds a site from `KNOWN_BAD` (one that crashed a release
   once), when `pack/modules/fl26caps.lua` is not the set `patchset.py` generated last
   (`sider/fl26caps.<set>.lua`, copy it over `sider/fl26caps.lua`), when it is not the
   `fl26caps.lua` installed in the game `FL26_DIR` names, when `FL26_DIR` is not set at all
   (since 0.2.2; `--untested` lets a fork's build through), and when the pack has no regen
   face pack (since 0.2.2; `--no-faces` for a fork without one) or one that is not the face
   pool (17.11.2026, `facepool.pool_problems`). Other modules that differ
   from the game's copy are printed as "NOT PLAYED in the game in this form": install the
   package's modules and play them before the release.
4. **Guides.** `guides/en/mod-studio-guide.md` -> `README.html`, and `guides/<code>/mod-studio-guide.md`
   for `hr`, `es`, `fr`, `pt` -> `README.<code>.html` (the `markdown` package).
5. **Check.** Every staged source inside the exe, the guides and `pack/modules.txt` is
   searched for drive paths and user names (`PRIVATE`). Any match stops the release.
6. **Zip.** `out/FL26ModStudio-<VERSION>.zip`, with everything inside a folder called
   `FL26 Mod Studio`.

**The face pack in a release** is built by lbpack from the repository, so mszip needs no
`FL26_REGEN_FACES` (`mszip_stamped.py` neither). Since 0.2.2 the release stops instead of going
out without regen faces, and since 17.11.2026 instead of going out with any pack but the pool.

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
