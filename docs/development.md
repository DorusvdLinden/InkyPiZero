# Development Quick Start

## Development Without Hardware

This app needs no Raspberry Pi, no physical display, and no root access to
develop against - it's a plain Python script that renders to a PNG file.
Works on **Windows**, **macOS**, and **Linux**.

## Setup

```bash
# 1. Clone and set up a virtual environment
git clone git@github.com:DorusvdLinden/InkyPiZero.git
cd InkyPiZero
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies (the minimal set - no inky needed for local testing)
pip install pillow requests pytz astral

# 3. Render to a file instead of a real display
python main.py --mock-output output.png
```

**That's it!** Open `output.png` to see the result.

## What You Can Do

- **Iterate on layout/widgets** - edit `layout.py` or anything under
  `widgets/`, rerun the command above, check the PNG
- **Test different locations/conditions** - edit the `DisplayConfig`
  defaults in `config.py` (or construct one with different
  `latitude`/`longitude` in a throwaway script) and rerun
- **Try a different screen mode locally** - `--screen-mode
  {original,gridlines,compact}` overrides the button-persisted choice for
  one render, e.g. `python main.py --mock-output output.png
  --screen-mode compact`. See [settings.md](./settings.md) for every
  option, and what the physical buttons do.
- **Debug data parsing** - `weather_data.fetch_snapshot()` hits the live
  Open-Meteo API directly; add a `print()`/breakpoint and rerun

## Regression testing

- `python scripts/test_locations.py` - renders 14 diverse real locations
  (hot/cold/rain/snow/night/zero-crossing temps/etc.) in all three screen
  modes via the real fetch -> render pipeline. Run after any change to
  `widgets/`, `canvas.py`, `layout.py`, or `weather_data.py`.
- `python scripts/test_precip_scenarios.py` - covers the chart's
  precipitation axis label (rain/hail/snow/dry) via crafted fixtures,
  since live weather can't reliably guarantee all four (a hailstorm
  especially) on any given run.
- `python scripts/test_pollen_scenarios.py` - covers the combined "Kwaliteit
  & Pollen" data point's tiers (which input wins, tie-breaking, the no-data
  fallback) via crafted air-quality fixtures, since live weather can't
  reliably guarantee season/hemisphere coverage or a specific AQI+pollen
  combination on any given run.
- `python scripts/test_display_freshness.py` - covers `display_freshness.py`'s
  skip/force decision (see [settings.md](./settings.md)'s "Display refresh
  cadence") against a temp state directory - no network/hardware needed.
- `python scripts/test_palette_sync.py` - covers `widgets.palette.PALETTE`
  staying synced to whatever `inky_saturation` the current render's config
  specifies (see [settings.md](./settings.md)'s "Color palette" section) -
  no network/hardware needed.

The first three save their renders to `mock_display_output/` for visual
review - see [icons.md](./icons.md) and [changes.md](./changes.md) for the
rest of the project's reference docs.

## Development Tips

1. Save preview renders to `mock_display_output/` with a descriptive
   filename, and leave them there - it's a kept record of iterations for
   comparison, not a scratch folder. Render one after every update, not
   just when a visual change was intended.
2. Check `TODO.md` before starting on something - it may already be a
   known issue.
3. There's no hot reload - it's a one-shot script, just rerun it.

## Testing Against Real Hardware

Once you have access to a Raspberry Pi with an Inky Impression display, see
the root [README.md](../README.md) for the full install
(`install/install.sh`), which additionally installs the `inky` package and
sets up the systemd timer. Local mock-driver testing should still be your
first pass before deploying to real hardware.

See [manual_test_checklist.md](../manual_test_checklist.md) for a
human-followable checklist covering things the automated suite above
can't reach on its own - real e-paper appearance, physical button
presses, WiFi AP behavior, and phone QR scanning.
