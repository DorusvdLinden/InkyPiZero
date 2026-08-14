# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Icons
See Icon-Plan.md


## General polish

- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
- [ ] `docs/settings.md`'s pollen section says "a real, permanent data-source gap (see `TODO.md`)" (Open-Meteo/CAMS only modeling 6 pollen species vs. Dutch services like pollennieuws.nl grouping mugwort+ragweed+other weeds under a broader "Kruiden" category) but no matching entry exists here - either add one, or drop the cross-reference. Found while working on the RIVM AQI swap (2026-08-14), unrelated to it.
