# Consistent temperature rounding (chart vs header vs cards)

Status: draft, not confirmed. Reported 2026-11-24 from a photo of the
live panel (Sittard, Sunday 22 November 20:36). The header said
"-1° / 5° / -1°", but the chart's temperature line never went below 0
and showed flat steps.

## Root cause (from the code, `weather_data.py`)

The same Open-Meteo floats are turned into whole numbers three
different ways:

| Where | Code | Rule | -0.6 becomes |
|---|---|---|---|
| Chart hourly temps | `HourPoint(temperature=int(...))` ~line 1052 | truncate toward zero | 0 |
| Header night lows | `_min_in_window` -> `round(min(values))` ~line 977 | round (banker's) | -1 |
| Header day high, forecast cards | `DayForecast(high=int(...), low=int(...))` ~line 919 | truncate toward zero | 0 |

So a night hovering around -0.5 to -0.9 degC shows as -1 in the header
but as a flat 0 on the chart. Truncation also produces the staircase
look: the line jumps in whole degrees, with plateaus between. Truncation
also shifts values toward zero on both sides (2.9 shows as 2, -1.9 as
-1), which makes the forecast cards slightly wrong too.

The "5°" in the header is not a bug: it's today's daily high (the middle
of last-night-low / day-high / tonight-low), which happened earlier in
the day. The chart starts at the current hour (20:00), so it isn't in
the line.

## Plan

1. **One rounding helper** in `weather_data.py`:
   `round_temp(x: float) -> int`, round half up
   (`math.floor(x + 0.5)`), so -0.6 becomes -1 and 2.5 becomes 3. It
   never produces "-0". Use it for `day_high`, the `DayForecast`
   high/low, the night lows and the current temperature / feels-like
   (check how those are rounded today and move them to the helper if
   they differ).
2. **The chart plots the real floats**: `HourPoint.temperature` becomes
   `float`, so the line is smooth and dips below 0 wherever the data
   does. Everything in `widgets/chart.py` that *prints* a temperature
   (axis min/max labels, the dashed actual-min/max lines and their
   "equals the axis extreme" skip check) goes through `round_temp`. The
   axis range itself (`min_temp`/`max_temp`, the gridline choice, and
   the rain-zero snap from `plans/rain-zero-at-chart-bottom.md`) works
   on the floats.
3. Leave `_quality_tier_and_color`'s use of the raw float as it is
   (already correct). Remove its comment about `int()` truncation, which
   becomes stale.

## Documentation updates

- `docs/changes.md`: new entry (next free number) describing the single
  rounding rule and the float chart line.
- `docs/settings.md` / README: sweep for claims about integer temps or
  "truncated" values.
- `TODO.md`: add this bug and check it off when fixed.

## Testing

- New `scripts/test_temperature_rounding.py` (no network): checks
  `round_temp` on -1.5, -0.6, -0.5, -0.4, 0.4, 0.5, 2.5 and 2.9; and on
  a crafted fixture with a night at -0.7 degC, checks that the header's
  night low and the chart's plotted minimum agree, and that the chart's
  `min_temp` is below 0.
- `scripts/test_chart_axis_labels.py` and `test_precip_scenarios.py`
  (the chart now gets floats); the 14 locations × 3 modes.
- Before/after renders of the fixture into
  `mock_display_output/temperature_rounding/`.
- Deploy to the Pi and force a refresh on a night near 0 degC.

## Order with the other plans

Build this one **before** `rain-zero-at-chart-bottom.md`: both change
how `widgets/chart.py` computes `min_temp`, and the snap should work on
the real floats.
