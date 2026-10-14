# Official Icons & Assets

Lazy Earth & Maps now features official icons for Google Maps, Google Earth, and Google Street View:

- `img/icon.png`: Composite plugin icon combining the official Google Earth globe and Google Maps pin.
- `img/icon_maps.png` & `img/icon_maps.svg`: Official Google Maps 2020 4-color pin.
- `img/icon_earth.png` & `img/icon_earth.svg`: Official Google Earth 3D ribbon origami globe.
- `img/icon_streetview.png` & `img/icon_streetview.svg`: Official Google Street View logo.
- `img/icon_pegman.png`: Official Google Maps Pegman sprite.
- `img/icon_coverage.png`: Street View coverage route layer toggle icon.
- `img/icon_send.png`: Official Google Earth globe with styled export badge.

## Regenerating Icons

To rebuild or re-render icons from source at any resolution:

```bash
python create_png_icons.py
```

Dependencies: `PyQt5` (or `PyQt6`) and `Pillow` (both included standard in QGIS Python).
