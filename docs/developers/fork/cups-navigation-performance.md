# CUPS navigation profiling

Measured on Windows with Python 3.14 / PySide6 using the actual `Main.open_page`
route, the normal theme, and Qt's offscreen platform. The fixture has 86 custom
top divisions (three cup logo selectors each), 21 original game league rows and
real, unpacked competition tables. Settings, logos and autosave destinations are
temporary; source tables are read only. Timings include navigation and Qt event
processing/painting/deferred deletion, not just the Python `shown()` call.

## Reproduce

```
python tools/profile_cups_navigation.py --tables <pesdb-folder> --repeat 7
python tools/profile_cups_navigation.py --tables <pesdb-folder> --section 1
python tools/profile_cups_navigation.py --tables <pesdb-folder> --section 2
```

An optional `--recipe <json>` uses an existing recipe without modifying it.
`--json <path>` exports measurements; each run also prints a cumulative cProfile
report. `--section` selects Game Countries (0), Our Countries (1) or Continental
(2) for repeated visits. Initial construction is reported separately.

## Cause and measurements

Before the change, every `Cups.shown()` called `refresh()`, which replaced every
clean editor, including the two hidden tabs. Profiling one repeated visit:

| Work | Cumulative time with profiler |
| --- | ---: |
| `Cups.refresh()` | 1085 ms |
| Three `replace_editor()` calls | 1082 ms |
| `OurCupsEditor.__init__()` | 895 ms |
| `GameCupsEditor.__init__()` | 148 ms |
| `ContinentalEditor.__init__()` | 31 ms |
| Picture preview loading, nested in construction | 29 ms |

The principal cost is constructing/styling/inserting hundreds of cell widgets
and their picture controls on the main thread. Catalog loading is secondary;
background competition planning is not invoked by navigation.

Seven unprofiled visits, alternating Settings and CUPS:

| Measurement | Before | After |
| --- | ---: | ---: |
| Game Countries median | 1048.393 ms | 19.411 ms |
| Game Countries range | 1011.921–1088.026 ms | 18.539–21.143 ms |
| Settings median, same respective runs | 23.123 ms | 24.435 ms |
| First CUPS construction | 1327.830 ms | 1248.847 ms |

Separate final runs with the other CUPS tabs active measured medians of
45.890 ms (Our Countries) and 9.750 ms (Continental). Those tabs were not measured
separately before the change. The optimized profiled `Cups.refresh()` itself is
about 2 ms; remaining navigation time is mostly Qt visibility/paint/style events.
These are reproducible local measurements on the fixture, not promises for every
machine or the user's particular recipe.

## Changes and invalidation

- Keep widgets when a section's input projection has not changed. Snapshots
  contain only cup identities, flags, league context and qualification fields;
  player databases and club rosters are neither copied nor compared.
- Rebuild only changed clean sections. Dirty sections retain their conflict
  baseline; Continental reconciles unedited fields using its existing logic.
- Project ownership changes still isolate and restore drafts. Existing explicit
  Apply/Discard and Undo/Redo paths remain in use.
- Table reload signals invalidate all section inputs. Competition table file
  stamps additionally detect replacement at the same path without a signal.
- Check image file stamps once per distinct path and update only changed
  previews, including a file overwritten without changing its recipe path.
- Keep valid plans across unchanged navigation, but invalidate cached/in-flight
  results on every project change, including while the page is hidden.
- Planning remains on demand and off the main thread. No engine changes.

`tools/test_cups_performance.py` uses deterministic work-count assertions instead
of timing thresholds: no reconstructions, catalog reads, image decodes or plan
jobs on unchanged navigation; changed inputs still refresh correctly. It also
covers draft retention, targeted refreshes, Undo/Redo, project switching, table
reloads, image replacement and stale asynchronous plan callbacks.

The first visit, project replacement and actual clean-table changes can still
construct a large table on the main thread. This fix removes repeated work on
ordinary navigation; it does not replace QTableWidget with a different model or
defer initial tab construction.
