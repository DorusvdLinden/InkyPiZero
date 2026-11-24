# Rain axis: 0 mm always at the chart bottom

Status: draft, not confirmed. Reported 2026-11-24 from a photo of the
live panel (Sittard, Tuesday 10 November, gridlines screen mode, temps
-2 to 7 degC).

## What's wrong

In the photo, the right-hand rain axis puts "0" partway up the chart
(on the 0 degC gridline). Every hour, including dry ones, draws a solid
bar from the chart bottom up to that line, so the dry morning looks
like it has rain.

## Root cause (from the code, `widgets/chart.py`)

This only happens in gridlines mode (`show_temp_gridlines`) on rain/hail
days, which is the exact-lattice path from `docs/changes.md` entry 57:

- `y_rain(0)` is anchored to the lowest temperature gridline,
  `y_temp(grid_start)` (chart.py ~line 264-274).
- The temperature axis bottom is the real `min_temp` (-2 here), but
  `grid_start` is the first gridline multiple at or above it (0 here),
  so rain 0 sits above the chart bottom whenever `min_temp` isn't
  exactly a gridline value. That happens on most days below freezing.
- The bars are drawn from `plot_y1` (the chart bottom) up to
  `y_rain(rain)` (~line 287). For 0 mm that's a bar from the bottom to
  the 0 line. The "too small to draw" check measures from `plot_y1`, so
  it doesn't suppress these bars.

Entry 57 recorded the bars staying grounded at the chart bottom as a
deliberate choice, but didn't consider that this draws dry hours as
bars. Original and compact modes use the ceiling scale with 0 at
`plot_y1` and are not affected.

## Options

- **A. Snap the temperature axis bottom down to a gridline**
  (recommended). In gridlines mode, use
  `min_temp = floor(min_temp / grid_step) * grid_step`, so the chart
  bottom is a gridline: -2 degC becomes a -5 degC bottom with the 5-degree
  grid. Then `grid_start` is the chart bottom, rain 0 is the bottom, and
  every gridline keeps its exact rain value (entry 57's
  no-rounding rule holds). Cost: on cold days the temperature line uses
  less of the height (here the axis spans -5..7 instead of -2..7). The
  zero-headroom fallback (`max_temp > grid_start`) almost never fires
  any more.
- **B. Give rain its own ticks**: 0 at the chart bottom, rain labels at
  their own heights instead of on the temperature gridlines. The
  temperature axis is unchanged, but this undoes entries 54-57's "rain
  number on each gridline" design and brings back two sets of marks on
  the right side.
- **C. Start bars at the rain 0 line** instead of the chart bottom. Dry
  hours draw nothing, but rain 0 still floats above the bottom. Entry 57
  rejected this because it leaves a gap under the bars.

Decision (2026-11-24): option A, snap the axis to the grid.

## Plan (option A)

1. `widgets/chart.py`: after the gridline-step choice and only when
   `show_temp_gridlines`, snap `min_temp` down to `grid_step` (and
   recompute `temp_span` and `grid_start`). Keep the 10/5-degree
   step-choice logic as it is, computed from the real temps before the
   snap.
2. Check that the bottom temperature label shows the snapped value
   (e.g. "-5°C") without colliding with the gridline label, and that the
   rain "0" sits on the chart bottom.
3. Add a guard for safety: in the lattice path, skip any bar whose
   rain is 0 (or whose top is at or below the zero line), so a
   dry hour can never draw a bar again even if the anchors drift apart.
4. Re-check the zero-headroom fallback comment and the entry-57
   "grounding" note. Both become largely moot, so update the comments
   rather than leave stale reasoning behind.

## Documentation updates

- `docs/changes.md`: new entry (next free number) that fixes entry 57's
  floating zero. Mark the affected parts of entry 57 as superseded,
  pointing at the new entry.
- `docs/settings.md`: the gridlines-mode chart description (axis range
  now snapped to the grid).
- `TODO.md`: add this bug and check it off when fixed.

## Testing

- Extend `scripts/test_chart_axis_labels.py`: a crafted day at -2..7
  degC with dry morning hours. Assert that `y_rain(0) == plot_y1`, that
  0 mm hours draw no bar, and that every gridline rain label is still
  exactly `steps * rain_step`.
- `test_precip_scenarios.py` (rain/hail/snow/dry axis labels) and the
  14 locations × 3 modes.
- Before/after renders of a fixture matching the photo's day, into
  `mock_display_output/rain_zero_bottom/`.
- Deploy to the Pi in gridlines mode and force a refresh.
