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

