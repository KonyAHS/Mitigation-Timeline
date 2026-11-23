## Download

Grab **`MitigationTimeline-*-windows.zip`**, unzip it anywhere and run `MitigationOverlay.exe`.
No Python install needed. Put your plans in the `plans` folder next to the exe.

Windows SmartScreen may warn about an unsigned app the first time: click *More info → Run anyway*.

## What's new in 1.0.0

- **Redesigned overlay:** a dark, compact card layout with a big countdown to the next
  mechanic, the mitigation to press, a progress bar, and a preview of the mechanic after it.
  The countdown turns yellow at 10s and red at 5s.
- **Accurate timing:** the overlay redraws 10× per second and uses a monotonic clock, and the
  global hotkeys no longer touch the UI from a background thread.
- **Stepping fixed:** `Shift+→` marks the upcoming mechanic as happening now and re-syncs the
  clock. `Shift+←` undoes exactly one step.
- **Plan folder:** plans are read from a `plans/` folder (old plans sitting next to the app
  still work), and an *Open…* button loads a plan from anywhere. Unrelated `.txt` files are ignored.
- **Plan Designer rewrite:** add and edit mechanics in a dialog with validation, sort by time,
  warn about unsaved changes, plus New/Open/Save/Save As shortcuts.
- **Clear errors:** a broken plan file reports which line is wrong instead of crashing.
- **Standalone exes with an icon**, built automatically by GitHub Actions.
