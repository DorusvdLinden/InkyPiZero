# Plan: wire `PALETTE` to `config.inky_saturation`

Status: **implemented** (2026-08-11). Fixed TODO.md's "Color palette &
quantization" item - see `docs/changes.md` for the current-state entry.

## Context

TODO.md's first item (Color palette & quantization):

> `widgets/palette.py`'s `PALETTE` singleton isn't wired to `config.py`:
> `PALETTE = Palette(saturation=0.0)` is a module-level constant that must
> be hand-edited any time `DisplayConfig.inky_saturation` changes, or
> every authored color silently stops being an exact panel-palette match
> and starts dithering again - nothing asserts or warns on a mismatch.

**Confirmed real, not hypothetical**: `inky_saturation` is a genuinely
user-changeable field - `config.py:21` defines it, `settings_store.py`'s
`FIELD_VALIDATORS`/`web/routes.py:64` expose and persist it via the web
UI's settings form. The *final* display step already reads it correctly
and dynamically (`main.py`/`web_app.py` both do
`InkyDriver(saturation=config.inky_saturation).show(image)`). But every
individual widget color (`PALETTE.uv_low`, `PALETTE.aqi_band_high`, wind
compass colors, etc.) comes from the module-level `PALETTE =
Palette(saturation=0.0)` singleton (`widgets/palette.py:112`), computed
once at import time and never touched again. If a user ever changes
`inky_saturation` away from `0.0` via the web UI, `PALETTE`'s colors stay
computed for `0.0` while the final quantization step snaps to whatever
saturation is now configured - every "exact panel match" color silently
stops being exact, reintroducing the dithered-speckle problem this whole
`PALETTE` system exists to prevent (see `docs/changes.md`'s
`color_palette_decision`/`quantization_pipeline_decision` history).

**The fix mechanism already exists, just isn't called anywhere real**:
`Palette.set_saturation()` (`widgets/palette.py:105-109`) already mutates
the shared singleton in place - its own docstring says exactly this is
the intent ("the shared `PALETTE` singleton stays the same object").
Currently it's only ever called from `scripts/color_options.py`, a
dev-only side-by-side comparison tool - never from the real app.

## Design

Rather than scattering `PALETTE.set_saturation(config.inky_saturation)`
across every current *and future* render entry point (fragile - easy to
add a new render call site later and forget it), bake the sync into the
two actual rendering entry functions themselves, so every caller gets it
automatically:

1. **`canvas.py`'s `WeatherCanvas.__init__`** - add
   `PALETTE.set_saturation(config.inky_saturation)` as the first line
   (`PALETTE` is already imported there). Covers `main.py` (both
   `--mock-output` and real-hardware paths) and all three standing test
   scripts (`test_locations.py`/`test_precip_scenarios.py`/
   `test_pollen_scenarios.py`), which all construct `WeatherCanvas`
   directly - zero changes needed in any of them.
2. **`setup_screen.py`'s `render_setup_screen`** - same one-line addition
   at the top (`PALETTE` already imported there too). Covers
   `web_app.py`'s `_show_setup_screen()` - the WiFi-AP setup screen,
   which matters *especially* here since `web_app.py` is a long-running
   process (unlike `main.py`'s one-shot-per-tick model where a fresh
   `Palette(saturation=0.0)` gets rebuilt every process start anyway) -
   without this, a user could change `inky_saturation` via the settings
   form, then have the device later host its setup AP (e.g. after moving
   WiFi routers) and get a setup screen with mismatched colors, in the
   same still-running process.
3. **Fix the stale docstring while in there**: `widgets/palette.py:12`
   says `inky_saturation` is "currently 0.5" - the actual singleton
   default is `0.0` (line 112), already a small drift. Reword to not
   hardcode a specific number that can go stale again (e.g. "must match
   whatever `DisplayConfig.inky_saturation` is currently configured as").

No changes needed to `config.py`, `settings_store.py`, or the web UI
itself - the setting is already correctly exposed/validated/persisted,
this is purely about the palette-color side actually reading it.

**Reminder from a related deploy gotcha found the same day** (see
`CLAUDE.md`'s Git workflow / `docs/troubleshooting.md`): `web_app.py` is
a persistent service (`pi-weather-web.service`) - after deploying this
fix, that service needs an explicit `sudo systemctl restart
pi-weather-web.service` to actually pick it up, a `git pull` alone isn't
enough. `main.py`/`pi-weather-display.service` (one-shot) doesn't have
this issue.

## Testing

- New `scripts/test_palette_sync.py`: construct a `DisplayConfig` with a
  non-default `inky_saturation` (e.g. `0.7`), build a `WeatherCanvas`
  with it, assert `PALETTE.saturation == 0.7` afterward; same for
  `render_setup_screen`. Restore `PALETTE` to the `0.0` default at the
  end (matching `scripts/color_options.py:67`'s own existing "restore
  the default for anything imported after this runs" precedent) so this
  test doesn't leak mutated global state into whatever runs after it in
  the same process/CI run.
- Rerun the standing regression suite (`test_locations.py`,
  `test_precip_scenarios.py`, `test_pollen_scenarios.py`) - all three use
  `DisplayConfig()`'s default `inky_saturation=0.0`, matching `PALETTE`'s
  existing hardcoded default, so the sync call is a no-op for them
  (mutating to the same value) - expect zero visual diff, this is just
  the standard "touched canvas.py" regression safety net.
- Real-hardware check: temporarily set a non-zero `inky_saturation` via
  the web UI, force a render, confirm colors still look flat/on-palette
  (not speckled) via `scripts/panel_sim.py` locally first, then on the
  real panel - this is the actual bug scenario, worth seeing it
  genuinely fixed rather than trusting the unit test alone.

## Docs

- `TODO.md` - check off this item once fixed (don't delete, per the
  standing convention).
- `docs/settings.md` - the `inky_saturation` field's description should
  note that changing it now correctly re-syncs every widget color, not
  just the final quantization step.
- `docs/changes.md` - new numbered entry.

## Critical files

- `widgets/palette.py` - `set_saturation()` (already exists, just needs
  a real caller), the stale docstring at line 12
- `canvas.py` - `WeatherCanvas.__init__`
- `setup_screen.py` - `render_setup_screen`
- New `scripts/test_palette_sync.py`
