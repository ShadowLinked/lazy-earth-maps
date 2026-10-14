# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.


def classFactory(iface):
    from .plugin import LazyEarthMapsPlugin
    return LazyEarthMapsPlugin(iface)
