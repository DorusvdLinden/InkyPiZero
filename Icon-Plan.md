# Plan: Icon fixes

Status: **items 1-3 implemented** (`feature/icon-plan-cleanup`, see
`docs/changes.md` entry 35). **Item 4 accepted as-is, closed, no code
change.** **Item 5 still pending.** Covers every item found while writing
`docs/icons.md`. See `docs/icons.md` for the current icon system this plan
builds on, and `scripts/generate_icons.py` for the actual generation
pipeline referenced throughout.

## Context

The icon set is generated once, offline, from `erikflowers/weather-icons`
SVGs (`scripts/generate_icons.py`, dev-only - not run at app runtime) into
flat PNGs under `assets/icons/`, loaded at runtime by `widgets/icons.py`'s
`AssetStore`. All six open items are either leftover gaps from that
generation pipeline or unverified assumptions in the weather-code mapping
- nothing here touches the runtime rendering path itself
(`canvas.py`/`widgets/chart.py`/`widgets/forecast.py`), only
`generate_icons.py`, `weather_data.map_weather_code_to_icon`, and their
generated/mapped output.

Recommended order below is priority order: item 1 is a pure cleanup with
no visual effect, item 2 is the most-requested-feeling gap (a real WMO
code family with no distinct icon), item 3 is a correctness question with
no code change guaranteed, items 4-5 are cosmetic/lower priority.

---

## Item 1: `02d`/`02n` are dead icon keys - DONE (option A, as recommended)

**Problem**: `scripts/generate_icons.py`'s `_icon_map()` still generates
`02d.png`/`02n.png` (`wi-day-cloudy`/`wi-night-alt-cloudy`), and
`map_weather_code_to_icon`'s night-remap dict (`weather_data.py:118`)
still has a `"02d": "02n"` entry - but the day-mapping half of that same
function (`weather_data.py:84-115`) never actually assigns `icon = "02d"`
anywhere. WMO codes 1/2 ("mainly clear"/"partly cloudy") map straight to
the `022d`/`022n` half-cloudy composite instead. Confirmed by reading the
full `if`/`elif` chain - there's no code path left over for a plain
"light cloud" icon distinct from the composite.

**Options**:
- **A) Remove the dead code.** Delete the `"02d"`/`"02n"` entries from
  `_icon_map()`, delete `"02d": "02n"` from the night-remap dict, delete
  `assets/icons/02d.png`/`02n.png`, update `docs/icons.md`'s file table
  and "Known gaps" section. Matches the app's actual current design (no
  WMO code wants a plain-cloud icon distinct from the composite) - the
  composite already covers "partly cloudy" better than a flat cloud icon
  would.
- **B) Find a real use for them.** Would need a WMO code currently mapped
  elsewhere that's actually a better fit for plain `wi-day-cloudy` than
  its current icon. Checked the full code table (`docs/icons.md`) for a
  candidate - none: code 3 ("overcast") already has its own `04d`
  (`wi-cloudy`, no sun/moon visible at all), and 1/2 are correctly the
  composite's job (partial sun/moon visibility is exactly what the
  composite exists to show). No genuine gap for a third "cloudy" tier
  was found.

**Recommendation**: Option A. This is pure dead-code removal with zero
behavior or visual change - lowest-risk item in this plan, good first
step.

**Implementation**: delete the two `_icon_map()` entries, the
`"02d": "02n"` night-remap dict entry, the two PNG files, and their
`docs/icons.md` table rows/Known-gaps bullet. No `weather_data.py` change
needed beyond confirming (already true) that nothing else references
`"02d"`/`"02n"` - `grep -rn '"02d"\|"02n"' --include=*.py` should come back
empty afterward except the icon-key literal itself being gone entirely.

---

## Item 2: No hail-specific icon - DONE

**Problem**: WMO thunderstorm-with-hail codes (96, 99) share the plain
`11d` icon with ordinary thunderstorm (95) - `map_weather_code_to_icon`
(`weather_data.py:114`) maps all three to `"11d"`. Only the chart's
precipitation axis label (`weather_data.py`'s hail classification,
`docs/changes.md` entry 20) distinguishes hail from an ordinary storm;
the current-conditions icon, hourly icon strip, and forecast cards do
not.

**What's available**: `erikflowers/weather-icons` ships
`wi-hail`/`wi-day-hail`/`wi-night-alt-hail` source SVGs - confirmed
present in the source repo, not yet referenced by
`scripts/generate_icons.py`.

**Design questions to settle before implementing**:
1. **Color role.** Every existing entry in `_icon_map()` reuses one of
   `PALETTE`'s existing role colors (`orange`, `moon_yellow`,
   `cloud_blue`, `fog`, `storm`). Hail should almost certainly reuse
   `storm` (same severe-weather-family color as `11d`, keeps the
   "this is still a thunderstorm" visual link) rather than introducing a
   new palette role for one icon - recommend `storm`, no `palette.py`
   change needed.
2. **Day/night variant.** `11d` itself has **no** night remap entry
   today (`weather_data.py:118`'s dict only covers `01d`/`022d`/`02d`/
   `10d`) - a thunderstorm at night already renders the identical `11d`
   icon. For consistency, hail should probably follow the same pattern:
   generate `96d` only (via `wi-day-hail`), skip a `96n`/`wi-night-alt-hail`
   variant, and don't add a night-remap entry - matching how its sibling
   `11d` already behaves rather than introducing an inconsistency where
   hail gets day/night distinction but plain thunderstorms don't. (If a
   future item revisits `11d` for a night variant, hail should get one
   at the same time, not before.)
3. **Icon key naming.** `96d` (matching the primary WMO code, same
   convention `71d`/`73d`/`77d` etc. already use - the *first* WMO code
   in the group, not every code that maps to it) fits the existing
   naming scheme.

**Recommendation**: add one new icon key, `96d` (`wi-day-hail`, `storm`
color, default-strength thickening like every other single-color icon -
no special-case needed, `11d` doesn't get extra thickening either), no
night variant, no new palette role.

**Implementation**:
1. `scripts/generate_icons.py`: add `"96d": ("wi-day-hail", storm)` to
   `_icon_map()`'s `weather_icons` dict.
2. Regenerate: `python scripts/generate_icons.py` (needs a local
   `erikflowers/weather-icons` clone, see `docs/icons.md`'s
   "Regenerating icons" section), confirm `assets/icons/96d.png` looks
   right via `scripts/icon_overview.py`.
3. `weather_data.py:114`: split the existing `elif weather_code in [95,
   96, 99]: icon = "11d"` into `elif weather_code in [95]: icon = "11d"`
   and `elif weather_code in [96, 99]: icon = "96d"`.
4. `docs/icons.md`: add `96d.png` to the file table, add a row to the
   weather-code table, remove the "Known gaps" bullet about missing hail
   icons, regenerate `docs/images/icon_overview.png`
   (`scripts/icon_overview.py`).
5. `TODO.md`: check off both the "No hail-specific icon" and "Create
   dedicated hail icons" items (they resolve together).
6. `docs/changes.md`: new entry.

**Verification**: `scripts/test_precip_scenarios.py`'s existing `hail`
scenario already crafts a fixture that hits WMO 96/99 for the axis-label
test - extend that same scenario's assertions (or add a sibling check) to
also confirm the rendered hourly-icon-strip/current-conditions icon for
that fixture is `96d`, not `11d`, so this doesn't silently regress later.
Also run the full 14-location suite - real weather is unlikely to
reliably produce a live 96/99 code on any given run (same reasoning the
precip-scenario script's own docstring already gives for hail), so the
crafted fixture is the real coverage here, the location suite is just
the standard no-regressions pass.

---

## Item 3: Verify forecast-card moon phase isn't off by one day - DONE (offset confirmed correct)

**Problem**: `weather_data.py`'s `_parse_forecast()` computes each
forecast card's moon phase for `target_date = dt.date() +
timedelta(days=1)` - one day ahead of the card's own date. The `+1` looks
deliberate (matching "the phase for the night that day's forecast
covers", i.e. the night *following* daytime `dt`), but has never been
checked against a real reference. This item doesn't necessarily need a
code change - it needs an answer.

**How to verify without guessing**: `astral.moon` (already a project
dependency, used by this exact function) has its own phase computation
that can be spot-checked against known public dates rather than trusting
either interpretation blind. Recommend a small one-off verification
script (not a permanent addition to the standing test suite - this is a
correctness check to run once, document the answer, then delete, similar
in spirit to this session's throwaway location-name verification):

1. Pick 2-3 unambiguous, publicly-documented reference dates (a known
   full moon and new moon date in the near future relative to whenever
   this is run - full/new moon dates are widely published and easy to
   confirm independently).
2. Call `get_moon_phase_name`/`get_moon_phase_icon_key` for both
   `target_date = <reference date>` and `target_date = <reference date +
   1>`, print both, compare against which one actually matches the
   public reference date.
3. If the *unshifted* date matches the public reference better than the
   `+1` version, the offset is a genuine bug - remove it. If the `+1`
   version matches better, the existing comment's reasoning was right -
   just upgrade the TODO item to a confirming code comment (e.g. "the +1
   offset was verified against <dates> on <verification date>") so this
   doesn't get re-flagged as unverified again later.

**Recommendation**: do this verification in isolation, before touching
any other icon item - it's cheap (no rendering pipeline involved) and
resolves a real ambiguity rather than proposing an actual code change
here.

**Implementation**: `weather_data.py:_parse_forecast()`'s `target_date`
line, only if step 3 above concludes the offset is wrong. Otherwise,
just a `TODO.md` checkbox + comment update, no functional change.

---

## Item 4: Low icon differentiation (71d/73d/77d, 51d/53d/09d) - SKIPPED, accepted as-is

**Problem**: `71d`/`73d`/`77d` (light snow / moderate snow / snow
grains) all render as the identical `wi-day-snow` icon -
`erikflowers/weather-icons` doesn't ship graduated snow-intensity
variants the way the old per-condition Flaticon set implied it should.
`51d`/`53d`/`09d` (light/moderate/heavy rain) use three genuinely
different source SVGs (`wi-day-sprinkle`/`wi-day-rain`/`wi-day-showers`)
but look very similar at the ~30px chart-strip render size. TODO.md's own
framing already calls this "not wrong, just less differentiated than
before" - a real but low-severity regression from the old icon set, not
a bug.

**Options**:
- **A) Accept as-is.** No source-SVG alternative exists for graduated
  snow intensity in this icon library; chasing exact parity with the old
  Flaticon set isn't worth a new icon source or a hand-drawn addition for
  a cosmetic, non-misleading difference (the *data* - precip amount,
  axis label - is still correct, only the icon itself doesn't visually
  scale with intensity).
- **B) Encode intensity as a secondary visual cue** (e.g. a small
  filled-dot count next to the icon, similar to how AQI/UV already show
  a color band) rather than swapping icons. Real design + layout work
  (new call sites in `canvas.py`/`widgets/chart.py`, a new `layout.py`
  region), disproportionate to a "not wrong, just less differentiated"
  cosmetic gap.
- **C) Look for a different source icon set with graduated variants**
  just for these keys. Adds a second icon provenance to
  `docs/attribution.md` for a handful of icons, inconsistent style risk
  (a different artist's line weight/proportions next to
  `erikflowers/weather-icons` everywhere else).

**Recommendation**: Option A - leave as-is. Revisit only if this becomes
an actual reported point of confusion (e.g. a user genuinely can't tell
light vs. heavy rain from the icon alone), not preemptively. Keep the
TODO.md item open but unworked, matching how it already reads.

---

## Item 5: `wi-night-clear` (`01n`) renders thinner than the `wi-moon-*` family

**Problem**: `01n` (night-clear condition icon, `wi-night-clear` source
SVG) and the 8 `wi-moon-*` moon-phase icons share the same
`PALETTE.moon` fill color but come from different source SVGs with
different path stroke weights - `wi-night-clear`'s crescent reads
noticeably thinner/paler next to a moon-phase icon at the same render
size. Purely cosmetic (same color, same silhouette family, just weight).

**Precedent already in this codebase**: the `022d`/`022n` composite's
back layer (sun/moon) is thickened at *generation* time with a boosted
strength (`thicken_icon(..., strength=1.0)`, vs. every other icon's
runtime-applied default `strength=0.5` from `widgets/chart.py`/
`widgets/forecast.py`'s call sites) specifically to fight this exact
class of dithering/weight problem (`scripts/generate_icons.py:132`,
documented in `docs/icons.md`). `01n` can use the same already-proven
technique instead of a new approach.

**Options**:
- **A) Boost `01n`'s generation-time thickening**, same pattern as the
  `022d`/`022n` composite's back layer - call `thicken_icon(icon,
  strength=1.0)` (or tune a value between 0.5-1.0 empirically) on `01n`
  specifically in `scripts/generate_icons.py`, baked into the generated
  PNG rather than a runtime special-case. Zero new dependencies, reuses
  an already-shipped, already-proven function.
- **B) Find a different `wi-night-*` source SVG** with a heavier stroke
  closer to the `wi-moon-*` family's weight. Requires browsing
  `erikflowers/weather-icons`' full night-icon set for a visually closer
  match, more speculative than A (no guarantee a better-weighted
  alternative exists), and a source-icon swap changes `01n`'s silhouette
  slightly, not just its weight - a bigger visual change than intended
  for what's a subtle weight mismatch.

**Recommendation**: Option A - reuse `thicken_icon()` at generation time,
matching the exact pattern already established for `022d`/`022n`. Lowest
risk, no new source-icon research needed, consistent with existing
precedent in the same file.

**Implementation**: in `scripts/generate_icons.py`'s `01n` generation
step (wherever the single-color icons are rendered/saved - check whether
that's a shared loop over `_icon_map()` or per-icon, since `01n` isn't
currently special-cased the way the composites are), add a post-render
`thicken_icon(img, strength=<tuned value>)` call. Regenerate just `01n`,
compare side-by-side against a `waningcrescent`/`newmoon` render at the
same size (`scripts/icon_overview.py` or a targeted crop) before
committing to a specific strength value - start at `0.75` as a
middle-ground guess between the runtime default and the composite's full
strength, adjust from there by eye.

---

## Common implementation steps (all items)

1. Confirm a local `erikflowers/weather-icons` clone exists (see
   `docs/icons.md`'s "Regenerating icons" section) - every item above
   except item 3 needs `scripts/generate_icons.py` to actually run.
2. After any icon regeneration: `python scripts/icon_overview.py`, copy
   the result over `docs/images/icon_overview.png`, commit it alongside
   the code change (standing rule, `docs/icons.md`'s own header).
3. Run the full standing regression suite
   (`scripts/test_locations.py`, `scripts/test_precip_scenarios.py`,
   `scripts/test_pollen_scenarios.py`) after any `weather_data.py` or
   icon-asset change - per `CLAUDE.md`.
4. Update `docs/icons.md` (file table, weather-code table, "Known gaps"
   section) and `TODO.md` (check off resolved items, don't delete) for
   whichever items actually get implemented.
5. `docs/changes.md` - one new entry per item actually implemented, or
   one combined entry if done together in one session/branch.

## Critical files

- `scripts/generate_icons.py` - `_icon_map()` (items 1, 2), `01n`'s
  generation step (item 5)
- `weather_data.py` - `map_weather_code_to_icon` (items 1, 2),
  `_parse_forecast()`'s `target_date` computation (item 3, only if the
  verification concludes it's wrong)
- `docs/icons.md` - file table, weather-code table, "Known gaps" section
  (items 1, 2)
- `assets/icons/` - `02d.png`/`02n.png` removed (item 1), `96d.png`
  added (item 2), `01n.png` regenerated (item 5)
- `docs/images/icon_overview.png` - regenerate after any asset change

## Suggested sequencing

Items are independent of each other - no ordering dependency - but item
3 (verification only, no icon pipeline involved) is the cheapest to
close out first, and item 1 (pure dead-code removal) is the lowest-risk
code change. Items 2 and 5 both touch `scripts/generate_icons.py` and
could reasonably be done in the same session/branch. Item 4 is a
"leave as-is" recommendation, not scoped work - closing it out is really
just a TODO.md decision (accept and leave open, or accept and note the
decision), not an implementation task.
