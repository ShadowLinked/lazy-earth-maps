# Lazy Earth & Maps - QGIS Plugin

[![QGIS](https://img.shields.io/badge/QGIS-3.16+-brightgreen.svg)](https://qgis.org)
[![Author](https://img.shields.io/badge/Author-Lazy%20by%20Design%20(Sheldon%20Willie)-blue.svg)](https://github.com/ShadowLinked)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-orange.svg)](NOTICE.txt)

Seamlessly open your QGIS view, clicked points, and vector layers in **Google Maps**, **Google Street View**, and **Google Earth** — featuring live Street View coverage lines and an integrated settings menu.

Developed by **Lazy by Design (Sheldon Willie)**.

---

## 🌟 Key Features

### 📍 Google Maps
- **One-click sync**: Open your current QGIS extent in Roadmap, Satellite, or Terrain view.
- **Selection-aware**: Automatically zooms and fits to your selected features.
- **Latitude-corrected zoom**: Accurately computes Web-Mercator scale across all latitudes.
- **Drop pin & copy link**: Quickly generate shareable Google Maps links.

### 🚶 Google Street View
- **Map Picker**: Click anywhere on the map canvas to open the nearest 360° panorama in Street View.
- **Official Icons**: Uses authentic Google Street View branding and the official Google Pegman icon.

### 🌐 Live Street View Coverage Layer (Free & Public)
- **Visual indication**: Toggle an instant XYZ overlay showing real Google Street View coverage (blue lines) directly on your QGIS map canvas.
- **Zero API keys required**: Completely free, public, and powered by QGIS's multi-threaded raster engine.
- **Auto-show option**: Optionally illuminates coverage automatically when the Street View point picker tool is active.

### 🌍 Google Earth Integration
- **Fly-to view**: Instantly fly to the QGIS canvas view in Google Earth Pro or Google Earth Web with rotation, heading, and tilt.
- **Smart layer export**: Export the active layer, selected features, or all visible vector layers as styled KMZ/KML.
- **Attribute pop-ups**: Preserves feature attributes for inspection in Google Earth.
- **Auto-detection**: Automatically finds Google Earth Pro on Windows, macOS, and Linux.

### ⚙️ Direct Plugin Settings
- Accessible anytime from **Plugins > Lazy Earth & Maps > Settings...** or **Web > Lazy Earth & Maps > Settings...**.
- Configure toolbar button toggles, default basemap, Street View icon style, Earth tilt, and export formats without any setup wizard hassle.

---

## 📦 Installation in QGIS

### Method 1: Add as a Custom QGIS Plugin Repository (Recommended)
This enables automatic updates directly through QGIS's Plugin Manager!

1. In QGIS, navigate to **Plugins** > **Manage and Install Plugins...**
2. Click on the **Settings** tab on the left.
3. Under **Plugin Repositories**, click **Add...**
4. Enter:
   - **Name**: `Lazy Earth & Maps Repository`
   - **URL**: `https://raw.githubusercontent.com/ShadowLinked/lazy-earth-maps/main/plugins.xml`
5. Click **OK**, then switch to the **All** tab.
6. Search for `Lazy Earth & Maps` and click **Install Plugin**.

---

### Method 2: Install from ZIP
1. Download `lazy_earth_maps.zip` from the latest [GitHub Release](https://github.com/ShadowLinked/lazy-earth-maps/releases).
2. In QGIS, go to **Plugins** > **Manage and Install Plugins...**
3. Select **Install from ZIP**, browse to the downloaded file, and click **Install Plugin**.

---

## 🚀 Release & Publishing Pipeline

A fully automated release script [`publish.py`](publish.py) is included to handle packaging, updating `plugins.xml`, committing to Git, and creating GitHub releases:

```bash
# Package and publish current version to GitHub
python publish.py

# Or bump version and publish in one command
python publish.py --version 3.2.1

# Dry-run (creates local ZIP and tests without pushing)
python publish.py --dry-run
```

---

## 📄 License & Attribution

- **Author**: Lazy by Design (Sheldon Willie)
- **License**: GNU General Public License v2 or later (GPL-2.0-or-later). See [NOTICE.txt](NOTICE.txt).
- Derived from "Open Google Maps" by Harry King (GPL).
- Google, Google Maps, Google Street View, and Google Earth are trademarks of Google LLC. This project is an independent tool for QGIS.
