# Project workflow & standing rules

This file documents the standing workflow rules for working on this repo. Follow these
automatically, without being asked each time.

## Dev environment

- The renderer itself has no dev server - `main.py` is a one-shot script. Test locally by
  rendering to a file: `python main.py --mock-output <path>` (Windows:
  `.\venv\Scripts\python.exe main.py --mock-output <path>`).
- This runs the real fetch -> render pipeline against live Open-Meteo data; no mocking of
  the interesting logic, only the final display step is swapped out.
- The settings/WiFi-management web UI (`web_app.py`) is a separate, persistent Flask app -
  test it locally with `python web_app.py` (works cross-platform; `wifi_manager.py`'s
  `nmcli`/`hostapd`/`systemctl` calls degrade gracefully with a logged warning on machines
  without NetworkManager, e.g. Windows dev). See [docs/networking.md](./docs/networking.md).

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
- **Always test the pollen scenarios**: `python scripts/test_pollen_scenarios.py`
  covers the pollen/hay-fever data point's tiers (Laag/Matig/Hoog/Zeer hoog) and the
  visibility fallback via crafted Open-Meteo air-quality fixtures rather than live
  weather, since live data can't reliably guarantee season/hemisphere coverage on any
  given run. Saves to `mock_display_output/pollen_scenario_test/`. Run this after any
  change to `weather_data.py`'s pollen classification or to `canvas.py`'s/`layout.py`'s
  compact-grid code, alongside the two tests above.

## Documentation maintenance

All of this repo's documentation is maintained, not a one-off snapshot -
**update whatever the change you're making touches, automatically, without being
asked each time.** This applies to every change, not just large ones - if a commit
renames a field, adds a flag, or changes a default, the docs describing that thing
change in the same commit/session, not "later."

- `TODO.md` - known bugs and polish items. Add an entry when something rough turns
  up; check items off (don't delete them) once fixed - see
  `feedback_todo_no_delete_default` memory (only delete a specific completed entry
  when explicitly asked for that one, not as general cleanup).
- `README.md` - features list, install steps, and the Architecture section (one
  bullet per major file/module) - update when a module is added/removed/renamed or
  its role changes, and when install-time behavior changes.
- `docs/installation.md` - the detailed install walkthrough; keep in sync with what
  `install/install.sh` actually does (services it installs, prompts it prints) and
  what a fresh setup actually needs to configure.
- `docs/settings.md` - any new/renamed/removed option or changed default, whether
  exposed via the physical buttons, the web UI, `config.py`, or CLI flags.
- `docs/icons.md` - any new icon, changed call-site size, or changed weather-code
  mapping.
- `docs/changes.md` - append a new numbered entry for each major change (not minor
  tweaks/fixes); when a change supersedes an earlier one, go back and mark the
  earlier entry outdated (pointing at the new entry number) rather than leaving it
  looking current.
- Other `docs/*.md` files (`troubleshooting.md`, `networking.md`, `development.md`,
  `attribution.md`) - same standard whenever a change touches what they describe,
  even though they aren't individually named above.

Before considering a change "done," do a quick sweep for stale claims the change
just invalidated (e.g. searching for old field/flag names, or phrases like "no web
UI" that a new feature just made false) rather than only adding new content - this
repo's history has repeatedly found docs that were correct when written but never
revisited when something later contradicted them.

## Verification & decision-making

- **Verify before asserting.** Before recommending an action based on a remembered
  fact (a file path, a function name, a config value, an SSH/access detail), check
  it's still true by reading the current file/state rather than trusting memory or
  an earlier read from this conversation.
- **Root-cause with evidence before proposing a fix.** When something fails (a
  render bug, a deploy failure, a hardware quirk), gather direct evidence (logs,
  actual device state, a minimal reproduction) before deciding why - and be
  willing to discard the first hypothesis and pivot the whole approach if the
  evidence contradicts it (e.g. the WiFi setup-AP NetworkManager-to-hostapd
  pivot, root-caused via live `journalctl` evidence rather than assumed from
  docs).
- **Ask when it's a genuine fork** — an architecture choice with real tradeoffs,
  an ambiguous requirement, or "should I proceed even though this might disrupt
  the live device" — a structured question beats guessing wrong and redoing
  work. Don't ask when there's a reasonable default; make the call and let the
  user redirect.
- **Confirm before anything destructive or hard-to-reverse** — force-push,
  `reset --hard`, discarding uncommitted work, deleting a branch that isn't
  fully merged, or disrupting the live Pi's network/power state — scoped to
  exactly what's being discarded. A prior approval doesn't extend to a new
  instance of the same category of action.

## Working modes

Three explicit modes govern how much I act before checking in - see
[Dorus-Claude-Collaboration](https://github.com/DorusvdLinden/Dorus-Claude-Collaboration)
for the full portable version this is adapted from. Default is Mode 2 unless
told otherwise or the task calls for a different one; the modes change *when*
confirmation happens, not whether this file's other rules (destructive-action
confirmation, documentation maintenance, testing) apply - those hold in all
three.

### Mode 1 - Plan (deliberate)

Trigger: "let's plan this," or automatically for architecturally significant /
ambiguous / hard-to-reverse work (e.g. the WiFi provisioning + settings web UI
feature).

- Break the problem into steps out loud before touching anything; surface real
  options with tradeoffs instead of silently picking one.
- No edits, no side-effecting commands, until the plan is explicitly confirmed.
- Ask clarifying questions freely.
- Once confirmed, create a new feature branch before making any changes, then
  move into Mode 2 to execute.

### Mode 2 - Build (default)

Trigger: everyday tasks by default.

- Create/switch to a feature branch before the first edit, unless already on
  one suited to this task - never build directly on `main`.
- Make reasonable, reversible changes without asking step-by-step permission;
  still ask on a genuine fork, still confirm before anything destructive.
- Narrate briefly at key moments (findings, direction changes, blockers), not a
  play-by-play.
- Commit/push as part of the standard Git workflow loop below once a change is
  tested and working - this file's Git workflow section is itself the standing
  authorization for that, not something to ask about each time.

### Mode 3 - Away (autonomous)

Trigger: "I'll be away," "go do X while I'm out," scheduled/overnight runs.

- Start by creating a dedicated branch - everything happens there; `main` and
  the deployed Pi stay untouched until reviewed.
- Push as far as possible without stopping; use judgment + memory + reasonable
  defaults for anything that would normally be a quick check-in.
- When a genuine fork has multiple good options, build each as its own branch
  rather than silently picking one (keep it to 2-3, only when worth the build
  time).
- Never merge to `main`, deploy to the Pi, or take any irreversible action
  unilaterally - queue the go/no-go for the end.
- Keep a running decision log while working; on return, give one consolidated
  summary with a short list of decisions needing a yes/no before anything ships
  further (including the merge itself).

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

Branch before editing, in every working mode (see Working modes above) —
create/switch to a feature branch before the first edit unless already on one
suited to the task, never build directly on `main`. For each major change from
there:

1. Implement and test locally first (`--mock-output` above).
2. **Commit the change** — one commit per major change, with a descriptive message.
3. Push to `origin`, then on the target Pi: `git pull`. Since this is a one-shot job (not
   a long-running process), the *next* scheduled timer tick picks up changed code
   automatically — no service restart needed for plain code changes. Only rerun
   `sudo bash install/install.sh` if dependencies or the systemd unit files themselves
   changed (safe to rerun any time).
4. Final test = let a real timer tick happen (or force one with `sudo systemctl start
   pi-weather-display.service`) and confirm the physical display updated correctly.
5. Merge to `main` only when explicitly asked; clean up (delete, locally and on
   the remote) the branch once merged.
