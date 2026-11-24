# Hourly chart: dimensions, ticks and lines (as built today)

Extracted 2026-11-24 from `widgets/chart.py`, `layout.py` and
`canvas.py` (on `main` at `39c38cd`), for review. It describes the
**current** behaviour. Rules that an open plan will change are marked
**[changes: plan name]**.

## 1. Dimensions (pixels, 800x480 panel)

| Item | Value | Source |
|---|---|---|
| Chart area | x 0-800, y 217-377 (800 × 160) | `layout.CHART_AREA` |
| Left margin (temperature labels) | 58 | `LEFT_MARGIN` |
| Right margin (rain labels + "Regen [mm]") | 82 | `RIGHT_MARGIN` |
| Top margin | 12 | `TOP_MARGIN` |
| Bottom margin (hour labels + icons) | 44 | `BOTTOM_MARGIN` |
| **Plot box** | x 58-718, y 229-333 (**660 × 104**) | derived |
| Hours shown | 24, starting at the current hour | `weather_data._parse_hourly` |
| Column per hour | 27.5 px (660 / 24) | derived |
| Rain bar width | 85% of a column = ~23 px | `render_chart` |
| Hour icons | 30 × 30 px, top at plot bottom + 18 (y 351) | `ICON_SIZE` |
| Forecast cards start at | y 385 (8 px below the chart area) | `layout.FORECAST_ROW` |

Fonts: axis numbers bold 18 px; hour labels normal 13 px.

## 2. Axes and frame (all screen modes)

- Solid 2 px lines: left axis, right axis, bottom axis. No top line.
- Day boundary: vertical dotted line at the first hour of the next day
  (on that hour's centre, so it lines up with "00:00").
- Hour ticks: a 4 px tick below the bottom axis, with the time label
  under it, every `graph_icon_step` hours (default **2**). The hour
  icons use the same step, so each icon sits under its label.
- Sunrise/sunset icons replace the hour icon in their hour's slot, even
  between the regular steps.

## 3. Temperature (left side)

**Range**
- Bottom = the lowest hourly temperature, but never above 0.
- Top = the highest hourly temperature, but never below 0.
  So 0 degC is always inside the chart.
- Hourly temperatures are currently cut to whole degrees toward zero
  (-0.7 becomes 0). **[changes: consistent-temperature-rounding:
  the line plots real values, labels use one rounding rule]**
- **[changes: rain-zero-at-chart-bottom: in gridlines/compact mode the
  bottom snaps down to the next gridline, e.g. -2 becomes -5]**

**Line**: 5 px. Orange where the average of two neighbouring hours is
>= 0, blue where it's below 0.

**Labels at the ends of the axis**: the top and bottom values, written
with the unit ("7°C", "-2°C"), right-aligned 6 px left of the axis.
In gridlines mode an end label is hidden when a gridline label is
within 1.2 × the text height of it (the gridline label wins).

**Original mode** (screen mode "original"):
- A dotted line at the real daily max and min, each labelled in the
  middle of the chart, 14 px above or below the line. They are left out
  when they equal the axis end anyway (e.g. min clamped to 0).
- If the day goes below freezing: a black dotted 0° line, labelled "0°"
  in the middle.

**Gridlines and compact modes**:
- Dotted gridlines at every multiple of **10°** inside the range.
- If that gives 0 or 1 gridlines, use multiples of **5°** instead.
  A day within one 5° band (e.g. -3 to +4) still gets only one.
- Each gridline is labelled at the left ("0°", "5°", without the "C"),
  aligned in a column with the end labels.

## 4. Rain / snow (right side)

**Which label**: rotated text, centred vertically, to the right of
the numbers: "Regen [mm]", "Hagel [mm]", "Sneeuw [cm]" or "Droog",
based on the weather codes in the 24-hour window.

**Bars**: drawn from the plot bottom up to the hour's value, with a
darker 3 px strip on top. Bars shorter than 3% of the plot height
(~3 px) are skipped.

There are two scales:

### 4a. Ceiling scale: original mode, category format, snow, dry

- Top of the plot = the day's max rain rounded **up** to a whole number,
  at least 1.
- Bottom of the plot = 0.
- Labels: the top value at the top (left out when the label is "Droog")
  and "0" at the bottom.
- With `rain_axis_format = "category"` (rain/hail only), the top and
  bottom labels are words instead of numbers: droog < 0.01, motrgn < 1,
  licht < 2.5, matig < 10, zwaar < 50, else hevig (mm/h), and the
  rotated "Regen" label is left out.
- In gridlines mode + category format, each temperature gridline also
  gets the intensity word for the rain value at that height.

### 4b. Exact lattice: gridlines/compact mode, rain or hail, "mm" format

- The **lowest temperature gridline is 0 mm** (today that is *not*
  always the plot bottom; see the bug below).
- Every gridline above it adds one fixed `rain_step`, so labels read
  e.g. 0, 3, 6. Nothing is rounded.
- `rain_step` is the smallest of 0.5, 1, 2, 3, 5, 10, 20, 50, 100, ...
  for which the value at the top of the plot is at least **3 mm** and at
  least the day's max rain (so no bar is cut off).
- Steps below 1 show one decimal (0.5, 1.0, 1.5); steps of 1 or more
  show whole numbers.
- No separate top or bottom rain labels.
- Fallback: if the lowest gridline is at the very top of the plot (a
  day squeezed inside one gridline band), use the ceiling scale (4a)
  instead.
- **Bug** (photo, 10 Nov): rain 0 sits on the lowest gridline but bars
  start at the plot bottom, so dry hours draw bars up to that line.
  **[changes: rain-zero-at-chart-bottom]**

## 5. Things you may want to decide while reviewing

1. The 3 mm minimum top of the rain scale (4b) versus the 1 mm minimum
   (4a). Should they be the same?
2. The 10°/5° gridline steps: is one gridline on a narrow day enough?
   The second photo (0-2 degC) shows only a "0°" line.
3. In original mode the bars use a different scale (4a) from gridlines
   mode (4b), so the same day looks different between modes.
4. The hour step of 2 (labels + icons every 2 hours) is a setting
   (`graph_icon_step`); the plot always shows 24 hours.
