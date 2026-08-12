# Attribution
This project uses various fonts and icons, each with specific licensing terms. Below is a breakdown of the sources and their respective licenses. Please ensure compliance with these licenses when using or redistributing the assets.

## Font Faces
| Name | License |
|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
[Bitter by Sol Matas](https://github.com/solmatas/BitterPro) | [SIL OFL v1.1](https://github.com/solmatas/BitterPro/blob/master/OFL.txt) - default font (`config.font_family`, since 2026-08-11) |
[Jost by Owen Earl](https://fonts.google.com/specimen/Jost) | [SIL OFL v1.1](https://fonts.google.com/specimen/Jost/license) - alternate font, selectable via `config.font_family`/the web UI |
[Noto Sans JP by Google/Adobe](https://fonts.google.com/noto/specimen/Noto+Sans+JP) | [SIL OFL v1.1](https://github.com/google/fonts/blob/main/ofl/notosansjp/OFL.txt) - fallback font for characters Bitter/Jost can't render (broad Latin/Cyrillic/Greek/CJK coverage), `widgets/icons.py`'s `AssetStore.draw_text_with_fallback()` |

## Icons

Weather condition icons, moon phases, and sunrise/sunset icons are recolored PNGs
rendered from [erikflowers/weather-icons](https://github.com/erikflowers/weather-icons)
SVG source (`svg/wi-*.svg`), converted at build time - see `TODO.md` for how to
regenerate them. Icons: [SIL OFL 1.1](https://github.com/erikflowers/weather-icons/blob/master/SIL%20OFL.txt).
Covers: `01d`, `01n`, `022d`, `022n`, `02d`, `02n`, `04d`, `50d`, `48d`, `51d`,
`53d`, `09d`, `56d`, `57d`, `71d`, `73d`, `13d`, `77d`, `11d`, `newmoon`,
`waxingcrescent`, `firstquarter`, `waxinggibbous`, `fullmoon`, `waninggibbous`,
`lastquarter`, `waningcrescent`, `sunrise`, `sunset`.

The remaining icons are individually-sourced from Flaticon:

| Name | Attribution |
|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| <img src="../assets/icons/visibility.png" width="32" height="32"> |<a href="https://www.flaticon.com/free-icons/observe" title="observe icons">Observe icons created by meaicon - Flaticon</a>|

Humidity drop icons (`humidity_drop_filled.png` / `humidity_drop_empty.png`) were
cropped from a screenshot of this project's own earlier Chromium/CSS-rendered
version (same underlying SVG teardrop shape, no external source).
