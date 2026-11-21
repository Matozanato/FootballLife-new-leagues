# FL27 promotion playoff indicators

The FL27 27.1.1 DLL keeps the original AP2 movie and adds the orange image as a separate atlas picture. It verifies the executable hash before reading fixed addresses, then verifies the asset and patch signatures. During installation it suspends other process threads and checks their instruction pointers. It leaves the game unpatched if it cannot safely stop those threads or if one is inside a patch site.

Stock FL27 uses the Championship, LaLiga 2 and Serie BKT league regulations 79, 80 and 82 and their respective playoff regulations 83, 84 and 85. The native seeding path at `0x141347160` routes England and Spain to a four-club bracket after skipping the two highest eligible clubs. The same routine sends Serie BKT to `0x141347590`, which skips two eligible clubs and permits two to six playoff participants. A gap of at least 10 points between the first potential entrant and the next club cancels the playoff. Subsequent entrants must be within 14 points of the first potential entrant. A club with a parent club is ineligible at the stock checks. The display uses the latest standings as a projection, so Italy can show places 3–8 early in a season and fewer as gaps develop.

The Lua module reads existing `poff` entrants and gives custom records precedence. Through `hold=` it identifies the contested automatic place. For a cross-tier tie it marks only the lower-division challenger. Parallel groups are marked per configured entrant and use the existing `gset` quotas to protect direct places. The `flZone` strips use their own zone rules. For example, the parallel-group setup around regulations 252 and 955 can display a green strip alongside a playoff arrow. The module leaves those strips to their existing renderer.

The DLL wraps the native row pass at `0x140aee370` and its caller's visibility branch at `0x140aee044`. The wrapper calls the original arrow pass under its original condition, then shows the existing promotion state on eligible rows where required. The picture binder at `0x140048fd0` handles widgets whose bitmap is created after the row pass. The render handle and bitmap leaf identify each row for rebinding and green restoration. Promotion totals, results and movement continue through the original game and world modules.

In Mod Studio, Install the modules and Build's Switch on prepare and prioritize the generated LiveCPK root. The module pack ships only Lua and DLL files. The asset comes from the installed game archive. FL26, unrecognized FL27 executables, malformed archives and conflicting LiveCPK icon parts leave the feature off.

For the isolated package, close FL27 and exit Sider from its tray icon. From the repository root run:

```powershell
& ".\out\playoff-icon-reviewed\Launch-Final.ps1"
```

Use the full Master League standings in the isolated installation. It continues to use save ID `20271120`. If the existing career was left open without a save, start a career within the isolated installation.

| Competition | Expected arrows |
| --- | --- |
| Custom EFL League Two, 366 | Green 1–3, orange 4–7 |
| Custom Kategoria e Parë, 348 | Green 1–2 where its native layout shows direct arrows, orange 3–6 |
| Stock Championship or LaLiga 2 | Green 1–2 and orange 3–6 with eligible clubs in those positions |
| Stock Serie BKT | Green 1–2 and orange 3–8 on a table with no point gaps or ineligible clubs |
| Custom parallel groups, 252 and 955 | Orange at rank 2 in each group, including 955 without a native promotion link |
| Custom cross-tier tie, 100 and 253 | Orange at rank 3 of 253. The existing indicators on 100 should look the same |
| League without promotion playoffs | Original indicators |

On each screen, also check the red relegation arrows and any continental qualification strips. Scroll down and back, refresh the table, switch competitions and return. The orange positions should stay attached to ranks through all four actions. No date advancement is required for this visual check. The log should show install status 0. Open the Sider overlay with Space and check that its other module pages still respond.

```powershell
Select-String -Path ".\out\playoff-icon-probe\sider.log" -Pattern "FL27 playoff arrows", "FL27 Playoff Indicators"
& ".\out\playoff-icon-reviewed\Launch-Final.ps1" -Restore
```

Run the restore command after closing the game and Sider. It restores the isolated Sider configuration that preceded the final test. For normal play, use the usual installed GigaPack launcher. The isolated launcher uses its own Sider directory and save ID.
