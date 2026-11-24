# Fewer and calmer display refreshes

Status: draft, not confirmed. Asked 2026-11-24: the screen flashes too
often, and each refresh flashes a lot. Can it update instead of doing a
full refresh?

## What the hardware is (checked on the Pi, 2026-11-24)

- Panel: **Inky Impression 7.3" Spectra 6, E673** (800×480, from the
  HAT EEPROM), driven by Pimoroni `inky` 2.3.0.
- The driver (`inky/inky_e673.py`) has a single update path: send the
  whole frame (`DTM1`), power on, `DRF` (display refresh), wait up to
  32 s, power off. It has no partial-window command, no fast mode and
  no waveform (LUT) upload. The flashing sequence is the waveform stored
  in the panel itself.

## Can we do a partial/fast update instead of a full refresh?

**Not reliably on this panel.**
- Pimoroni doesn't offer partial updates for the Spectra 6 Impression.
  Seeed's documentation for the same 7.3" Spectra 6 says it doesn't
  support partial refresh.
- One user who forced partial refresh on a comparable 7.3" Spectra 6
  panel (GoodDisplay GDEP073E01) reported whites turning more blue with
  every partial update, and advised full refresh only.
- Writing our own controller commands or waveforms is undocumented. A
  wrong waveform can leave lasting ghosting, and DC imbalance can damage
  e-paper permanently.
- So the number of flashes per refresh can't safely be reduced in
  software. The only real change there is a different panel type
  (black/white or greyscale panels support partial refresh but lose the
  colours). Out of scope unless you want to explore it.

What we *can* control is how often a refresh happens.

## How often it refreshes now (journal on the Pi, last 48 h)

- **66 refreshes in 48 h** (~33 a day), including 2-5 an hour between
  00:00 and 05:00 when nobody is looking.
- Triggers (`display_freshness.should_update_display`): any change of the
  main icon, **any 1-degree change** in the current temperature, or 60
  minutes since the last refresh (`force_refresh_max_stale_minutes`).
- Near a rounding boundary (e.g. 2.4 / 2.6 degC) the rounded current
  temperature flips back and forth, so each flip costs a refresh.

## Plan

Decisions (2026-11-24): keep the full refresh (no partial-refresh
experiment, no panel change); use smart thresholds (items 1, 2 and 4);
no quiet hours.

1. **Temperature hysteresis**: refresh only when the current temperature
   differs by **2 degrees or more** from what's on screen (new setting
   `refresh_temp_delta`, default 2). Smaller drift is caught by the
   stale timer.
2. **Icon changes**: refresh only when the icon's *weather group*
   changes (clear / partly cloudy / cloudy / fog / rain / snow /
   thunder), not on day/night or minor code changes. The stale timer
   catches the rest.
3. ~~Quiet hours~~: **rejected 2026-11-24**. The screen keeps
   refreshing at night under the same rules as during the day.
4. **Longer stale timer**: `force_refresh_max_stale_minutes` default
   60 -> **120**.
5. Expected effect: roughly 33 -> 10-14 refreshes a day (no quiet hours, so night ticks still count). I'll measure it
   from the journal for a few days after deploying.

All of these are settings in `config.py` / `settings_store.py` / the web UI,
so you can tune them without a code change.

## Documentation updates

- `docs/settings.md`: the new settings and the changed default.
- `docs/troubleshooting.md`: why the screen flashes (full-refresh-only
  panel) and which settings to change.
- `docs/changes.md`: new entry (next free number).
- `TODO.md`: check off once deployed and measured.

## Testing

- Extend `scripts/test_display_freshness.py`: tests for the temperature
  threshold (1-degree change doesn't refresh, 2-degree change does), icon
  group changes,
  a forced refresh, and the stale
  timer.
- Restart the button and web services on the Pi (they use
  `display_freshness`), then count refreshes per hour from the journal
  for a few days and compare against the 66 / 48 h baseline.

## Sources

- [Seeed forum: EE04 and Spectra 6 7.3 partial refresh](https://forum.seeedstudio.com/t/ee04-and-spectra-6-7-3-partial-refresh/295260)
- [Pimoroni: Inky Impression 7.3](https://shop.pimoroni.com/en-eu/products/inky-impression-7-3)
- [Core Electronics forum: 7.3" 6-colour EPD refresh rate](https://forum.core-electronics.com.au/t/7-3-6-color-epd-refresh-rate-ws-27875/23398)
