# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
"""Pure-Python URL / camera maths. No QGIS imports, so it is unit-testable."""
import math

EARTH_FOV = 35.0
_Z0_RES = 156543.03392  # metres per pixel at zoom 0, equator, 256px tiles
_CSS_DPI = 96.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def zoom_from_scale(scale, lat=0.0, dpi=_CSS_DPI):
    """Web-Mercator zoom matching a QGIS map scale at a given latitude.

    The original plugin ignored latitude; ground resolution of a web tile shrinks
    by cos(lat), so ignoring it under-zooms at high latitudes.
    """
    if not scale or scale <= 0:
        return 2.0
    c = max(0.05, math.cos(math.radians(clamp(lat, -85, 85))))
    z = math.log2(_Z0_RES * c * dpi / (0.0254 * scale))
    return clamp(z, 0.0, 21.0)


def _merc_y(lat):
    lat = clamp(lat, -85.0, 85.0)
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def zoom_for_bbox(west, south, east, north, px_w=1100, px_h=700, margin=1.15):
    """Largest web-Mercator zoom that fits a lon/lat bbox in a px_w x px_h viewport."""
    dlon = max(abs(east - west), 1e-7) * margin
    frac_x = dlon / 360.0
    frac_y = max(abs(_merc_y(north) - _merc_y(south)), 1e-9) * margin / (2 * math.pi)
    zx = math.log2(px_w / (256.0 * frac_x))
    zy = math.log2(px_h / (256.0 * frac_y))
    return clamp(min(zx, zy), 0.0, 21.0)


def bbox_size_m(west, south, east, north):
    lat = (south + north) / 2.0
    w = abs(east - west) * 111320.0 * max(0.05, math.cos(math.radians(lat)))
    h = abs(north - south) * 110540.0
    return w, h


def earth_range_for_height(height_m, fov=EARTH_FOV):
    """Camera distance so a top-down view spans height_m of ground (vertical FOV)."""
    return max(50.0, height_m / (2.0 * math.tan(math.radians(fov) / 2.0)))


def earth_range_for_bbox(west, south, east, north, fov=EARTH_FOV, margin=1.25):
    w, h = bbox_size_m(west, south, east, north)
    return earth_range_for_height(max(w * 0.65, h) * margin, fov)  # ~16:10 viewport


def _f(v, n=7):
    return f"{v:.{n}f}"


def google_maps_url(lat, lon, zoom, basemap="roadmap"):
    """roadmap keeps the fractional-zoom @ form; satellite/terrain use the documented
    api=1 form (integer zoom only)."""
    if basemap in ("satellite", "terrain"):
        return ("https://www.google.com/maps/@?api=1&map_action=map"
                f"&center={_f(lat)}%2C{_f(lon)}&zoom={int(round(clamp(zoom, 0, 21)))}"
                f"&basemap={basemap}")
    return f"https://www.google.com/maps/@{_f(lat)},{_f(lon)},{clamp(zoom, 0, 21):.2f}z"


def google_streetview_url(lat, lon, heading=None):
    url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={_f(lat)}%2C{_f(lon)}"
    if heading is not None:
        h = ((heading + 180.0) % 360.0) - 180.0
        url += f"&heading={h:.0f}"
    return url


def google_pin_url(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={_f(lat)}%2C{_f(lon)}"


def google_earth_web_url(lat, lon, range_m, tilt=0.0, heading=0.0, fov=EARTH_FOV):
    return (f"https://earth.google.com/web/@{_f(lat)},{_f(lon)},0a,"
            f"{int(range_m)}d,{fov:g}y,{heading % 360.0:.1f}h,{clamp(tilt, 0, 80):.0f}t,0r")


def google_streetview_coverage_xyz_uri():
    """Returns the QGIS XYZ layer URI for Google Street View coverage tiles."""
    return ("type=xyz&url=https://mts1.google.com/mapslt?lyrs=svv%26x={x}%26y={y}%26z={z}"
            "%26w=256%26h=256%26hl=en%26style=40,18&zmax=19&zmin=0")

