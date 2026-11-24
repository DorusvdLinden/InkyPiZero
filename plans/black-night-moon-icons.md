# Night moon icons in black

Status: draft, not confirmed. Asked 2026-11-24: the moon icons that
stay after the moon phase is removed from the forecast cards (see
`forecast-card-vertical-budget.md`) become black instead of yellow.

## Scope

- `01n` (clear night, moon outline) and `022n` (moon behind a cloud).
  They appear in the icon strip under the chart, in the large
  current-conditions icon at night, and on forecast cards if a night
  code ever reaches them.
- The cloud in `022n` stays blue. Only the moon turns black.
- The moon-phase icons are unused after the forecast-card change, so
  they're left as they are.

Preview (in-memory recolour, 30 / 42 / 102 px, the real sizes):
`mock_display_output/night_icons_black/01n_022n_yellow_vs_black.png`.

## Plan

1. `widgets/palette.py`: `self.moon = c["black"]` (nothing else reads
   `PALETTE.moon`; only `scripts/generate_icons.py` uses it, at build
   time).
2. Before regenerating, copy the current files to `01n-yellow.png` and
   `022n-yellow.png` (old versions are kept, same convention as
   `022d-new.png`).
3. Regenerate `01n` and `022n` with `scripts/generate_icons.py` (only
   those two; check that the other PNGs come out byte-identical, or
   restore them).
4. Check the outline weight in black: `EXTRA_THICKEN` for `01n` was
   tuned for yellow, which needed extra weight to show up on the panel.
   Black may look heavier, so compare at 30 px in a render and lower it
   if it looks too heavy.

## Documentation updates

- `docs/icons.md`: moon colour is black; the `-yellow` copies.
- `docs/changes.md`: new entry.
- Color palette memory / `docs/settings.md` if they list the moon
  colour.

## Testing

- 14 locations × 3 modes (several are at night), plus a crafted
  night render into `mock_display_output/night_icons_black/`.
- On the Pi: force a refresh after dark and check that the moon reads
  clearly in black on the panel.
