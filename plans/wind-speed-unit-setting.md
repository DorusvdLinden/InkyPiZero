# Wind speed unit setting: m/s vs Beaufort

## Context

The "Wind" data point (compass gauge + numeric readout) always shows raw
m/s today. The user wants a setting - m/s or Beaufort - that controls how
that number is displayed everywhere it appears.

Important precedent found during exploration: this repo already tried and
**reverted** a full imperial/standard unit-system toggle
(`docs/changes.md` entry 25, 2026-08-11) because it broke the chart's
temperature-axis scaling logic. That risk doesn't apply here: wind speed
is **never charted** (`widgets/chart.py` has zero wind-related code) - it
only appears as one gauge + one text data point, both driven by a single
generic dict-based renderer. So this is a much smaller, lower-risk change,
but the plan explicitly updates the "metric-only by design" doc note so
it doesn't read as contradicted.

The repo also already has Beaufort-scale *description* logic
(`weather_data.get_beaufort_description_nl`, using the standard m/s
breakpoints) - just no numeric 0-12 conversion and no unit-toggle
infrastructure. This plan adds the missing numeric conversion and wires
up a new setting following the existing `rain_axis_format` setting's
pattern exactly (same kind of enum, web-UI-only, no physical button).

## Implementation

**1. `weather_data.py`** - add the numeric conversion, reusing the
existing thresholds instead of duplicating them:

- Refactor the inline threshold list in `get_beaufort_description_nl`
  (lines 171-181) into two module-level lists shared by both functions:
  `_BEAUFORT_UPPER_BOUNDS_MS` (the 12 numbers) and
  `_BEAUFORT_DESCRIPTIONS_NL` (the 12 Dutch labels).
- Add `get_beaufort_number(speed_ms: float) -> int`, returning the index
  of the first bound `speed_ms` is under (0-11), or `12` past the last
  bound - same logic/shape as the existing description function.
- `_parse_data_points` (line 1094): add a `wind_speed_unit: str = "ms"`
  parameter. In the wind block (lines 1100-1108), branch on it:
  - `"ms"` (current behavior): `measurement = wind_speed`,
    `unit = SPEED_UNIT` ("m/s").
  - `"beaufort"`: `measurement = get_beaufort_number(wind_speed)`,
    `unit = "bft"`.
  - `label` (the Dutch description) is unaffected either way.
- `fetch_snapshot` (line 1292): pass `config.wind_speed_unit` through,
  the same way `config.inky_saturation` is already threaded in:
  `_parse_data_points(weather_data, aqi_data, current_lki, tz, config.inky_saturation, config.wind_speed_unit)`.

No changes needed in `canvas.py` (`_data_point_value_text` just
stringifies whatever `measurement`/`unit` it's handed) or
`widgets/gauge.py` (the compass is direction-only, never speed-scaled).

**2. `config.py`** - add the field right after `rain_axis_format` (line
29), with a comment following the same style as its neighbors, noting it
only affects this one data point and involves no chart axis:

```python
wind_speed_unit: str = "ms"   # "ms" | "beaufort"
```

**3. `settings_store.py`** - mirror `rain_axis_format` exactly:

- Add `_valid_wind_speed_unit(v): return v in ("ms", "beaufort")` next to
  `_valid_rain_axis_format` (line 71).
- Register it in `FIELD_VALIDATORS` (line 96): `"wind_speed_unit": _valid_wind_speed_unit,`.

**4. `web/routes.py`** - add `_set("wind_speed_unit", str)` in
`_config_from_form` (line 66, right after `_set("rain_axis_format", str)`).

**5. `web/templates/settings.html`** - add a `<select>` in the
"Weergave" fieldset, right after the `rain_axis_format` select (line 41),
same structure:

```html
<label>Windsnelheid eenheid
  <select name="wind_speed_unit">
    {% for value, label in [("ms", "Meters per seconde (m/s)"), ("beaufort", "Beaufort")] %}
      <option value="{{ value }}" {{ "selected" if config.wind_speed_unit == value }}>{{ label }}</option>
    {% endfor %}
  </select>
</label>
```

## Documentation updates

- **`docs/settings.md`**: add a `wind_speed_unit` row to the `config.py`
  fields table (after the `rain_axis_format` row, ~line 585), describing
  both values and pointing at `get_beaufort_number`/
  `get_beaufort_description_nl`. Update the "metric-only by design"
  paragraph (lines 568-571) to note `wind_speed_unit` as a scoped
  exception: it's a display-scale choice for one already-metric value
  (the panel still only ever fetches/stores m/s from Open-Meteo), not a
  reintroduction of the reverted imperial/standard system, and - unlike
  that one - touches no chart axis.
- **`docs/changes.md`**: append entry `57` describing the new setting,
  the numeric-Beaufort addition, and why this is lower-risk than entry
  25's reverted attempt (no chart involvement).

## Testing

- Add `scripts/test_wind_scenarios.py` (crafted-fixture style, matching
  `test_precip_scenarios.py`/`test_pollen_scenarios.py`): asserts
  `get_beaufort_number` against known sample speeds (e.g. 0.0->0, 5.0->3,
  15.0->7, 35.0->12) and asserts `_parse_data_points`/`fetch_snapshot`
  produce the right `measurement`/`unit` for both `wind_speed_unit`
  values from one fixed mock `current` payload. This is needed because,
  like precipitation/pollen scenarios, live data can't reliably hit every
  Beaufort band on a given run.
- Run the standing regression suite per `CLAUDE.md`: `python
  scripts/test_locations.py` (all 14 locations x 3 screen modes) and the
  existing precip/pollen/palette/freshness scripts, to confirm no
  rendering regressions.
- Render fresh mock previews for both settings values (e.g.
  `--mock-output mock_display_output/wind_speed_unit/ms.png` and
  `.../beaufort.png`) to visually confirm the wind data point reads
  correctly in both modes, per the repo's screenshot-after-every-change
  rule.

## Files touched

`weather_data.py`, `config.py`, `settings_store.py`, `web/routes.py`,
`web/templates/settings.html`, `docs/settings.md`, `docs/changes.md`,
new `scripts/test_wind_scenarios.py`.
