# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Forecast cards

- [ ] With `show_moon_phase=True` and a wide rain amount (e.g. a 2-digit
  mm value), the moon-phase percentage row at the bottom of the card can
  visually overlap the day-name/high-low-temp text above it. Confirmed
  pre-existing (not a regression from the 2026-08-15 mm-stacking change
  that found it - reproduced against the pre-change code too via
  `git stash`), found during that change's fresh-context review, unrelated
  to it. Neither `temps_y`'s two text lines nor `moon_y` account for each
  other's actual height when both are shown.
- [ ] The mm-rain text's bold size (`widgets/forecast.py`'s `bold_size`,
  shared with the day-label/temps font since 2026-08-15) only actually
  *matches* the day-label/temps size at `forecast_days` 5 through 10 -
  below 5, `icon_size` caps out independently of card width
  (`region.h`-bound, not `region.w`-bound) while `bold_size` keeps
  growing with the wider card, so the mm-text's fixed vertical budget
  above `temps_y` stops growing with it and the text shrinks below
  `bold_size` well before running out of horizontal room; above 10,
  `available_width` becomes the binding constraint instead and the text
  shrinks or omits itself, same as it always has. Not fixed as part of
  that change (would need reworking the card's vertical budget, a bigger
  scope than a font-size/style match) - found via fresh-context review,
  confirmed via direct measurement across `forecast_days` 1-17. (A
  related formula bug - the height check was off by half a line-height,
  needlessly shrinking text even within `icon_size`'s real vertical
  budget - *was* fixed as part of that change, since it was a
  self-contained arithmetic error rather than the architectural gap this
  item describes; it's what widened the matching band from 7-10 to 5-10.)
- [ ] Related, pre-existing, unrelated to any 2026-08-15 change: the
  day-label/high-low-temp text itself (`font_bold` in
  `widgets/forecast.py`, `bold_size = max(10, int(region.w * 0.15))`) has
  no shrink-to-fit at all, unlike every other piece of forecast-card
  text - at a very low `forecast_days` (e.g. `1`, unbounded by
  `settings_store` validation), `region.w` approaches `FORECAST_ROW.w`
  (800px) and `bold_size` grows to ~120px inside a fixed 95px-tall card
  row, overflowing badly. Found via fresh-context review while auditing
  the mm-rain sizing change above, not caused by it.
