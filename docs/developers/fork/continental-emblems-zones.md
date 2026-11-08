# Continental emblems and CONMEBOL standings zones

## Final validation scope

The maintainer visually verified the modern CONMEBOL strips in Football Life
2027: Bolivia's domestic standings show three blue and four orange positions.
This is an actual in-game check, separate from the automated native tests below.
FL26 in-game behavior has not been independently verified. Dark/Light emblems
pass automated asset/UI tests, but their in-game rendering is not fully verified.

Edit the variants in MY WORLD > CUPS > CONTINENTAL > COMPETITIONS or in
LEAGUES > MORE > Competition names. Both locations share the optional
`continental_emblems` recipe data; older worlds retain their single-logo behavior.

## Standings

`zone_fill()` still uses the existing `flZone` cell, palette and precedence. The
additional lookup in `zone_access()` reads the active world's existing native
configuration, not UI quotas or country names:

- `g_access`: Libertadores groups / classic qualifying (blue 70), existing UEFA
  blue/orange/teal and AFC blue access.
- `g_lpre`: Libertadores alias phases F1/F2 (blue 70), and the single-match
  first stage feeding the modern Sudamericana (orange 3).
- `g_ccup`: domestic entries into modern Sudamericana groups (orange 3). Its
  identity uses the existing `modern_suda_ccup()` signature, not generated IDs.

Winner entries (rank 0), loser feeds (255) and synthetic association ranks do not
identify numbered domestic table positions. No speculative cup-winner fallback
position is coloured. Scheduling, allocation resolution, split rules, relegation,
promotion, cell dimensions, executable offsets and DLL exports are unchanged.
There is no new world-file record or zone cache. The existing loader owns these
arrays and replaces them with the world's configuration.

Classic mode in this working tree deliberately does not generate Sudamericana
or Recopa. Historical stored Sudamericana rows remain inactive; this change
does not restore that retired generation path or pretend they are active zones.

`python tools/test_zone_conmebol.py` builds and executes the real native lookup
with the project's no-game harness. It needs Windows x86-64 GCC or zig. This
does not test the live FL26/FL27 hooks or visible in-game rendering. The native
module can be built with the documented GCC-compatible toolchain as well as
`build-swiss.sh`; distribute matching binaries in `tools/native/` and
`sider/experimental/`.

### FL27 Bolivia regression / deployment check

The reported installed world uses domestic regulation **94**. Its `uefa` records
contain only positions 1/2 in Libertadores; F1 master 267 contains `94:3` and
Sudamericana first-stage master 262 contains `94:4` through `94:7`. F2 master
268 contains the domestic cup `258:0`, with fallback `alt=10:94:1`; that does not
specify an extra numbered table row. The loader log confirmed all four lpre
records, flags and the one-match flag were accepted, after loading ccup 263/264.

The installed DLL was older and differed from both rebuilt repository copies.
The repository implementation, loaded through the native configuration APIs with
the actual installed world records, returned exactly three blue and four orange
rows. A successful world Build therefore did not demonstrate that the updated
DLL was running: `install_modules()` copies from the application's **module pack**,
not `tools/native/`; an old executable/pack can keep reinstalling an old DLL.

Refresh the distributed module pack as well as the installed `modules/fl26swiss.dll`,
and restart Sider/FL27 before checking. This deployment was subsequently completed
for the successful FL27 check above. The rebuilt DLL emits this marker when
its standings hook is installed:

```
fl26swiss: standings zones v2 -- modern CONMEBOL domestic access from lpre/ccup
```

The CONMEBOL extension explicitly rejects native continental stages and world-built
cup/pre-round master/group/tie regulations. Domestic source matching still uses
the real positive-rank entries, not cup-winner fallback guesses. Existing UEFA
league-phase highlighting and the existing split/promotion/relegation path remain
unchanged.

`tools/testdata/zone_conmebol_bolivia.txt` preserves the relevant reported records.
`python tools/test_zone_conmebol.py [path/to/fl26world.txt]` marshals the relevant
records into the existing loader ABI and tests the full `zone_of()` path with only
the game competition-object lookup stubbed. It checks the exact Bolivia result,
an alternative manually changed distribution, removal of stale zones, and empty
qualification zones in domestic/continental cup screens. It also checks that both
repository DLL copies contain the runtime marker. This is offline native testing,
not execution of Sider's Lua parser or actual in-game visual verification.

## Optional background emblems

Existing default logo fields and aliases retain their meaning. The only recipe
extension is optional:

```json
{
  "continental_emblems": {
    "game:2": {"dark": "ucl-dark.png", "light": "ucl-light.png"},
    "generated:9": {"dark": "sudamericana-dark.png"},
    "uecl": {"light": "conference-light.png"}
  }
}
```

`game:` uses a native **Competition.bin ID**; `generated:` uses the existing
**logical generated cup number**, never a regulation or allocated competition
ID. Eligibility comes from the continental catalog / native table metadata;
FIFA's world cup and domestic competitions are excluded. Generated numbers are
resolved to the actual built `ccups[].cid`. Sudamericana's helper stages and
Libertadores' qualifying helper receive their parent competition's variants.

`continental_emblems.py` shares the key and filename mapping. CUPS uses the
catalog identity adapter and its normal per-field drafts/conflicts. Competition
Names uses the same adapter with its existing explicit OK/Cancel lifecycle;
only changed fields are applied, with atomic conflict detection. Changing a
different field in the other editor cannot overwrite an unedited emblem.
Both selectors reuse `CompetitionLogoVariant` / `PictureField`.

Build first performs the previous default emblem jobs, then overlays only the
selected background pair using the same Pillow `square()` sizing:

| UI variant | Game suffixes | Sizes |
|---|---|---|
| Dark Mode Logo | `_w_l`, `_w_ll` | 256, 512 |
| Light Mode Logo | `_b_l`, `_b_ll` | 256, 512 |
| Existing default logo | existing six variants | unchanged |

This follows the existing documented game convention: `_b` is for a light
background and `_w` for a dark background; these need not be monochrome images.
Files remain `common/render/symbol/emblemLc/emb_<CID:04d><suffix>.png`.
An absent variant emits no overlay, retaining the game's original variant or
the existing custom/generated default. Missing external images use
`have_picture()` and the exact affected file pair in `gone`, preserving assets
carried by an imported world. No blank emblem is emitted as a replacement.

The extension is kept both in the plan and in `RECIPE_SETTINGS` for editable-world
round-trips. Existing export/import carries the plan and generated assets; it
does not require the author's external source-image paths to exist on the
recipient PC. `PIC_ARG` includes the overlay job for incremental asset signatures.

`python tools/test_continental_emblems.py` checks real asset output, default and
missing-file fallback, export, editor synchronization/conflicts, Cancel, drafts,
history, world isolation, serialization and responsive controls. Native metadata
is mocked in these unit tests; plan round-trips can additionally be checked
against local tables without a full Build. Visual appearance in the actual
game's different emblem contexts still requires FL26/FL27 manual verification.
