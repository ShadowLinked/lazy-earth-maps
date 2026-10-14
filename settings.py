# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
from qgis.core import QgsSettings

PREFIX = "LazyEarthMaps/"
DEFAULTS = {
    "first_run_done": True,
    "show_maps": True,
    "show_earth_fly": True,
    "show_earth_send": True,
    "show_streetview": True,
    "show_coverage": True,
    "auto_show_coverage": True,
    "sv_icon_style": "streetview",
    "maps_basemap": "roadmap",
    "earth_target": "auto",
    "earth_pro_path": "",
    "earth_tilt": 0,
    "export_format": "kmz",
    "export_dir": "",
    "feature_cap": 20000,
    "include_attrs": True,
    "open_folder_on_web": True,
    "label_fields": "name,title,label,id",
}


class Settings:
    def __init__(self):
        self._s = QgsSettings()

    def get(self, key):
        if key not in DEFAULTS:
            return self._s.value(PREFIX + key)
        d = DEFAULTS[key]
        return self._s.value(PREFIX + key, d, type=type(d))

    def set(self, key, value):
        self._s.setValue(PREFIX + key, value)

    def reset_defaults(self):
        for k, v in DEFAULTS.items():
            self._s.setValue(PREFIX + k, v)
