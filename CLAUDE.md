# Project workflow & standing rules

This file documents the standing workflow rules for working on this repo. Follow these
automatically, without being asked each time.

## Dev environment

- No dev server, no web UI. Test locally by rendering to a file:
  `python main.py --mock-output <path>` (Windows: `.\venv\Scripts\python.exe main.py
  --mock-output <path>`).
- This runs the real fetch -> render pipeline against live Open-Meteo data; no mocking of
  the interesting logic, only the final display step is swapped out.

## Visual/icon mockups

- **Render a fresh screenshot after every update to this app** (not just when a visual
  change was intended) - `--mock-output` to `mock_display_output/` with a descriptive or
  timestamped filename. Do this automatically, without being asked each time.
- When generating a preview image of a new icon or visual change, save it to
  `mock_display_output/` in the repo root with a descriptive filename, and **leave it
  there** — don't clean these up. They're a kept record of each iteration for comparison.

## Testing

- **Always test the 14 locations**: `python scripts/test_locations.py` renders 14
  diverse real locations (hot/cold/rain/snow/night/zero-crossing temps/etc.) via the
  real fetch -> render pipeline, in **all three screen modes**
  (original/gridlines/compact), saving each to
  `mock_display_output/location_consistency_test/`. Run this after every change to the
  rendering pipeline (`widgets/`, `canvas.py`, `layout.py`, `weather_data.py`) to check
  for regressions before considering the change done. Do this automatically, without
  being asked each time.
- **Always test the precipitation scenarios**: `python scripts/test_precip_scenarios.py`
  covers the chart's precipitation axis label (rain/hail/snow/dry) via crafted
  Open-Meteo fixtures rather than live weather, since live data can't reliably
  guarantee all four on any given run (a hailstorm especially). Saves to
  `mock_display_output/precip_scenario_test/`. Run this after any change to
  `weather_data.py`'s precipitation classification or `widgets/chart.py`'s axis-label
  rendering, alongside the 14-location test above.

## Bugs / ideas tracking

- `TODO.md` tracks known bugs and polish items. Add to it when something rough turns up;
  check items off (don't delete them) once fixed.
- `docs/settings.md`, `docs/icons.md`, and `docs/changes.md` are maintained
  documentation, not one-off snapshots - **update them whenever the change you're making
  touches what they cover**, do this automatically without being asked:
  - `docs/settings.md` - any new/renamed/removed option or changed default, whether
    exposed via the physical buttons or via `config.py`/CLI flags.
  - `docs/icons.md` - any new icon, changed call-site size, or changed weather-code
    mapping.
  - `docs/changes.md` - append a new numbered entry for each major change (not minor
    tweaks/fixes); when a change supersedes an earlier one, go back and mark the
    earlier entry outdated (pointing at the new entry number) rather than leaving it
    looking current.

## Install procedure

- `install/install.sh` / `install/uninstall.sh`, using `install/requirements.txt` /
  `install/debian-requirements.txt`. Installs to `/usr/local/pi-weather-display`, runs
  periodically via `pi-weather-display.timer` (not a long-running service — a systemd
  timer firing every 10 minutes by default).
- See [README.md](./README.md) for full details.

## Raspberry Pi compatibility

- Target hardware is a Raspberry Pi (Zero W and up) driving a Pimoroni Inky Impression
  panel via the `inky` Python library — not the Windows dev environment, which is a local
  convenience only (rendering works cross-platform via `--mock-output`; only the real
  `display/inky_driver.py` path needs actual Pi/Inky hardware).
- No Chromium/browser dependency at all.

## Git workflow

For each major change:

1. Implement and test locally first (`--mock-output` above).
2. **Commit the change** — one commit per major change, with a descriptive message.
3. Push to `origin`, then on the target Pi: `git pull`. Since this is a one-shot job (not
   a long-running process), the *next* scheduled timer tick picks up changed code
   automatically — no service restart needed for plain code changes. Only rerun
   `sudo bash install/install.sh` if dependencies or the systemd unit files themselves
   changed (safe to rerun any time).
4. Final test = let a real timer tick happen (or force one with `sudo systemctl start
   pi-weather-display.service`) and confirm the physical display updated correctly.
